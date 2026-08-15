"""Tests for the monitoring mart.

The point of these is drift protection: the cockpit's money figures are only
trustworthy while they still reproduce the analysis the deck was built on, so the
observed dataset is checked against the committed artifacts in ``output/tables/``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.monitor import metrics as M  # noqa: E402
from src.monitor.build_mart import DECK_TOTALS, MART_PATH, TOLERANCE  # noqa: E402
from src.monitor.prep import load_dataset  # noqa: E402

#: Written by analysis/01_data_prep.py. Optional: the deck's totals are also pinned
#: as constants in build_mart.DECK_TOTALS, so drift is still caught without it.
REFERENCE_MASTER = REPO_ROOT / "output" / "tables" / "employee_master.csv"

needs_reference = pytest.mark.skipif(
    not REFERENCE_MASTER.exists(),
    reason=f"{REFERENCE_MASTER.relative_to(REPO_ROOT)} not present in the working tree",
)


@pytest.fixture(scope="module")
def observed():
    return load_dataset("observed")


@pytest.fixture(scope="module")
def cells(observed):
    return {
        "engagement": M.engagement_cells(observed),
        "attrition": M.attrition_cells(observed),
        "cost": M.cost_cells(observed),
        "lead": M.lead_time_cells(observed),
    }


@pytest.fixture(scope="module")
def mart():
    if not MART_PATH.exists():
        pytest.skip("mart not built — run python -m src.monitor.build_mart")
    with MART_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


# --- prep reproduces the analysis pipeline ---------------------------------


@needs_reference
def test_master_matches_reference_population(observed):
    reference = pd.read_csv(REFERENCE_MASTER, low_memory=False)
    master = observed.master

    assert len(master) == len(reference) == 13_403
    assert master["is_voluntary"].sum() == reference["is_voluntary"].sum()
    assert master["is_regrettable"].sum() == reference["is_regrettable"].sum()
    assert master["is_departed"].sum() == reference["is_departed"].sum()
    assert master["is_high_value"].sum() == reference["is_high_value"].sum()


def test_persistent_disengagement_definition_holds(observed):
    """Persistent requires >= 2 responses — Proofs.md:72 audits exactly this."""

    master = observed.master

    if REFERENCE_MASTER.exists():
        reference = pd.read_csv(REFERENCE_MASTER, low_memory=False)
        active = master[~master["is_departed"]]
        ref_active = reference[reference["status"] == "active"]
        assert (
            active["is_persistently_disengaged"].sum()
            == ref_active["is_persistently_disengaged"].sum()
        )

    flagged = master[master["is_persistently_disengaged"]]
    assert (flagged["n_responses"] >= 2).all()
    assert (flagged["avg_engagement"] < M.DISENGAGED_THRESHOLD).all()


def test_window_is_derived_from_the_data(observed):
    assert str(observed.window_end.date()) == "2025-12-31"
    assert load_dataset("scenario_a").window_end.strftime("%Y-%m-%d") == "2026-07-31"


# --- cost buckets reconcile with the deck ----------------------------------


def test_cost_buckets_reconcile_with_financial_model(cells):
    totals = cells["cost"].groupby("bucket")["amount"].sum()
    hiring = totals["agency_excess"] + totals["agency_early_exit"]

    for name, actual in (
        ("regrettable_attrition", totals["regrettable_attrition"]),
        ("disengagement_productivity", totals["disengagement_productivity"]),
        ("hiring_inefficiency", hiring),
    ):
        expected = DECK_TOTALS[name]
        assert abs(actual - expected) / expected <= TOLERANCE, name


# --- cells are additive -----------------------------------------------------


def test_engagement_cells_sum_to_the_raw_totals(observed, cells):
    eng = cells["engagement"]
    raw = observed.engagement
    assert eng["eligible"].sum() == len(raw)
    assert eng["respondents"].sum() == raw["response_flag"].sum()
    company_mean = eng["composite_sum"].sum() / eng["respondents"].sum()
    assert company_mean == pytest.approx(
        raw.loc[raw["response_flag"], "engagement_composite"].mean()
    )


def test_attrition_cells_account_for_every_exit(observed, cells):
    attr = cells["attrition"]
    master = observed.master
    assert attr["exits_voluntary"].sum() == master["is_voluntary"].sum()
    assert attr["exits_total"].sum() == master["is_departed"].sum()


def test_rates_survive_being_filtered(cells):
    """A rate built from any subset of cells is the rate of that subset."""

    attr = cells["attrition"]
    for entity in attr["entity"].unique():
        subset = attr[attr["entity"] == entity]
        rate = subset["exits_voluntary"].sum() / (subset["person_months"].sum() / 12)
        assert 0 <= rate < 1


# --- guardrails -------------------------------------------------------------


def test_no_small_cohort_reaches_the_flagged_table(observed, cells):
    flagged = M.flagged_cohorts(observed, cells["engagement"], cells["attrition"], cells["cost"])
    assert (flagged["headcount"] >= M.MIN_COHORT_N).all()


def test_mart_carries_no_small_cohorts(mart):
    for key, block in mart["datasets"].items():
        for cohort in block["flagged_cohorts"]:
            assert cohort["headcount"] >= M.MIN_COHORT_N, key


def test_lead_time_median_is_recoverable_from_bins(observed, cells):
    lead = cells["lead"]
    binned = M.median_from_bins(lead["months"], lead["n"])
    raw = observed.master.loc[observed.master["is_voluntary"], "lead_time_months"].dropna()
    assert binned == pytest.approx(raw.median(), abs=1.0)


# --- scenarios --------------------------------------------------------------


def test_scenarios_extend_the_observed_history(mart):
    observed_waves = [w["wave_number"] for w in mart["datasets"]["observed"]["waves"]]
    assert observed_waves == [1, 2, 3, 4, 5]

    for key in ("scenario_a", "scenario_b"):
        block = mart["datasets"][key]
        assert [w["wave_number"] for w in block["waves"]] == [1, 2, 3, 4, 5, 6, 7, 8]
        assert [w["wave_number"] for w in block["waves"] if w["simulated"]] == [6, 7, 8]
        assert block["synthetic"] is True

    assert mart["datasets"]["observed"]["synthetic"] is False


def test_scenarios_share_the_observed_history(mart):
    """Waves 1-5 are copied through, so the real past must be identical."""

    def history(key):
        frame = pd.DataFrame(mart["datasets"][key]["engagement_cells"])
        frame = frame[frame["wave"] <= 5]
        return frame.groupby("wave")[["eligible", "respondents", "composite_sum"]].sum().round(6)

    baseline = history("observed")
    for key in ("scenario_a", "scenario_b"):
        pd.testing.assert_frame_equal(history(key), baseline)


def test_the_two_futures_actually_diverge(mart):
    """If the scenarios told the same story the toggle would be decoration."""

    def latest_voluntary_rate(key):
        attr = pd.DataFrame(mart["datasets"][key]["attrition_cells"])
        last = attr[attr["wave"] == attr["wave"].max()]
        return last["exits_voluntary"].sum() / (last["person_months"].sum() / 12)

    assert latest_voluntary_rate("scenario_a") > latest_voluntary_rate("scenario_b")
