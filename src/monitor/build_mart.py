"""Build the monitoring mart consumed by dashboard/nova_app.py.

Reads the three dataset directories (observed plus the two simulated scenarios),
computes every aggregate the cockpit needs, and writes a single JSON artifact.

    python -m src.monitor.build_mart
    python -m src.monitor.build_mart --verify

``--verify`` re-reads the artifact and asserts the observed company totals still
reconcile with ``output/tables/04_financial_model_results.txt`` — the deck's own
numbers — so a definition can never drift silently.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from . import metrics as M
from .prep import DATASETS, REPO_ROOT, Dataset, load_dataset

MART_DIR = REPO_ROOT / "outputs" / "monitor"
MART_PATH = MART_DIR / "monitor_mart.json"

#: Company-wide annual figures from analysis/04_financial_model.py, as recorded in
#: output/tables/04_financial_model_results.txt. Reproduced to within TOLERANCE.
#: The small gap is a known convention difference: the analysis annualises on a flat
#: WINDOW_YEARS = 2.0, the mart on the exact 731-day window (2.0014 years).
DECK_TOTALS = {
    "regrettable_attrition": 14_258_723,
    "disengagement_productivity": 59_293_114,
    "hiring_inefficiency": 4_552_607,
}
TOLERANCE = 0.01


def _records(frame: pd.DataFrame) -> list[dict]:
    """DataFrame to JSON-safe records (NaN -> None, numpy scalars -> Python)."""

    return json.loads(frame.to_json(orient="records", date_format="iso"))


def build_dataset_block(key: str) -> tuple[dict, Dataset]:
    dataset = load_dataset(key)
    eng = M.engagement_cells(dataset)
    attr = M.attrition_cells(dataset)
    cost = M.cost_cells(dataset)
    lead = M.lead_time_cells(dataset)
    cohorts = M.flagged_cohorts(dataset, eng, attr, cost)

    waves = dataset.waves.copy()
    waves["period_start"] = waves["period_start"].dt.strftime("%Y-%m-%d")
    waves["period_end"] = waves["period_end"].dt.strftime("%Y-%m-%d")
    waves["survey_start"] = waves["survey_start"].dt.strftime("%Y-%m-%d")
    waves["survey_end"] = waves["survey_end"].dt.strftime("%Y-%m-%d")
    waves = waves.drop(columns=["midpoint"])

    block = {
        "key": key,
        "label": dataset.label,
        "synthetic": dataset.synthetic,
        "window_start": dataset.window_start.strftime("%Y-%m-%d"),
        "window_end": dataset.window_end.strftime("%Y-%m-%d"),
        "window_years": round(dataset.window_years, 4),
        "waves": _records(waves),
        "engagement_cells": _records(eng),
        "attrition_cells": _records(attr),
        "cost_cells": _records(cost),
        "lead_time_cells": _records(lead),
        "flagged_cohorts": _records(
            cohorts.drop(columns=[c for c in cohorts.columns if c.startswith("flag_")])
        ),
        "cohort_context": {
            "suppressed": cohorts.attrs["suppressed"],
            "min_cohort_n": M.MIN_COHORT_N,
            "company_disengaged_share": cohorts.attrs["company_disengaged_share"],
            "company_voluntary_rate": cohorts.attrs["company_voluntary_rate"],
        },
        "totals": {
            bucket: float(cost.loc[cost["bucket"] == bucket, "amount"].sum())
            for bucket in M.COST_BUCKETS
        },
    }
    return block, dataset


def build_mart() -> dict:
    datasets = {}
    for key in DATASETS:
        block, _ = build_dataset_block(key)
        datasets[key] = block
        print(f"  {key:<12} {len(block['engagement_cells']):>4} engagement cells · "
              f"{len(block['waves'])} waves · ${sum(block['totals'].values()) / 1e6:,.1f}M exposure")

    return {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": "0_case/Accenture_Case_Comp_Data + scenarios/*",
            "financial_constants": {
                "replacement_multiplier": M.REPL_MULT,
                "backfill_rate": M.BACKFILL_RATE,
                "disengagement_loss_rate": M.DISENGAGEMENT_LOSS_RATE,
                "super_oncost": M.SUPER_ONCOST,
                "agency_fee_rate": M.AGENCY_FEE_RATE,
                "direct_hire_cost": M.DIRECT_HIRE_COST,
                "addressable_band": list(M.ADDRESSABLE_BAND),
            },
            "guardrails": ["aggregate_only", "no_individual_scores", f"min_cohort_n={M.MIN_COHORT_N}"],
        },
        "cost_buckets": M.COST_BUCKETS,
        "datasets": datasets,
    }


def write_mart(mart: dict) -> Path:
    MART_DIR.mkdir(parents=True, exist_ok=True)
    with MART_PATH.open("w", encoding="utf-8") as handle:
        json.dump(mart, handle, separators=(",", ":"))
    return MART_PATH


def verify(mart: dict) -> None:
    """Assert the observed totals still reconcile with the deck's financial model."""

    totals = mart["datasets"]["observed"]["totals"]
    hiring = totals["agency_excess"] + totals["agency_early_exit"]
    checks = {
        "regrettable_attrition": totals["regrettable_attrition"],
        "disengagement_productivity": totals["disengagement_productivity"],
        "hiring_inefficiency": hiring,
    }
    failures = []
    for name, actual in checks.items():
        expected = DECK_TOTALS[name]
        drift = abs(actual - expected) / expected
        status = "ok" if drift <= TOLERANCE else "DRIFT"
        print(f"  {name:<28} ${actual:>13,.0f}  vs deck ${expected:>12,.0f}  {drift:6.3%}  {status}")
        if drift > TOLERANCE:
            failures.append(name)

    for key, block in mart["datasets"].items():
        waves = [w["wave_number"] for w in block["waves"]]
        simulated = [w["wave_number"] for w in block["waves"] if w["simulated"]]
        expected_sim = [] if key == "observed" else [6, 7, 8]
        print(f"  {key:<28} waves {waves} simulated {simulated}")
        if simulated != expected_sim:
            failures.append(f"{key}: unexpected simulated waves {simulated}")
        for cohort in block["flagged_cohorts"]:
            if cohort["headcount"] < M.MIN_COHORT_N:
                failures.append(f"{key}: cohort below min size leaked into the mart")

    if failures:
        raise SystemExit(f"VERIFY FAILED: {failures}")
    print("  verify ok")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="reconcile totals after building")
    args = parser.parse_args()

    print("Building monitoring mart…")
    mart = build_mart()
    path = write_mart(mart)
    print(f"Wrote {path} ({path.stat().st_size / 1024:,.0f} KB)")

    if args.verify:
        print("Verifying…")
        verify(mart)


if __name__ == "__main__":
    main()
