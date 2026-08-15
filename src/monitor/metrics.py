"""Aggregations for the monitoring cockpit.

Everything here is emitted at ``entity x department x wave`` grain (or coarser) in
*additive* form — sums and counts, never pre-divided means — so the app can filter
to any entity, department or wave and still compute a correct rate by summing the
surviving cells.

Financial constants are Finance's benchmarks as applied in
``analysis/04_financial_model.py:26-31``. That file is the source of truth; the
company-wide totals produced here are asserted against its output in
``build_mart.py --verify``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .prep import DISENGAGED_THRESHOLD, SCORE_COLS, Dataset

REPL_MULT = 1.5
BACKFILL_RATE = 0.85
DISENGAGEMENT_LOSS_RATE = 0.15
SUPER_ONCOST = 0.12
AGENCY_FEE_RATE = 0.18
DIRECT_HIRE_COST = 5500

#: Share of the exposure the recommended interventions are assumed to reach. An
#: assumption for sizing a pilot, not a forecast — the cockpit labels it as such.
ADDRESSABLE_BAND = (0.25, 0.50)

#: Response rate below which non-response is treated as a disengagement signal.
#: Proofs.md:51 — voluntary exit rate is 21.2% below this line vs 6.8% above it.
RESPONSE_FLOOR = 0.60

#: Cohorts smaller than this are never shown. The dashboard promises aggregate-only
#: views with no individual risk scores; small cells leak individuals.
MIN_COHORT_N = 30

GROUP = ["legacy_entity_code", "department"]

COST_BUCKETS = {
    "regrettable_attrition": "Regrettable attrition",
    "disengagement_productivity": "Disengagement productivity loss",
    "agency_excess": "Agency channel excess",
    "agency_early_exit": "Agency early-exit backfill",
}


def loaded(salary: pd.Series | float) -> pd.Series | float:
    """Salary including the 12% superannuation on-cost."""

    return salary * (1 + SUPER_ONCOST)


def engagement_cells(ds: Dataset) -> pd.DataFrame:
    """Survey coverage and scores per entity x department x wave.

    Sums, not means: ``composite_sum / respondents`` reconstructs the mean over any
    filtered subset. Non-responses stay in ``eligible`` so the response rate is
    computed against everyone the survey was issued to.
    """

    eng = ds.engagement
    responded = eng[eng["response_flag"]]

    issued = (
        eng.groupby(GROUP + ["wave_number"]).size().reset_index(name="eligible")
    )

    agg = {"respondents": ("engagement_composite", "size"), "composite_sum": ("engagement_composite", "sum")}
    agg.update({f"sum_{col}": (col, "sum") for col in SCORE_COLS})
    scores = responded.groupby(GROUP + ["wave_number"]).agg(**agg).reset_index()

    low = responded[responded["engagement_composite"] < DISENGAGED_THRESHOLD]
    disengaged = (
        low.groupby(GROUP + ["wave_number"]).size().reset_index(name="disengaged_respondents")
    )

    cells = issued.merge(scores, on=GROUP + ["wave_number"], how="left").merge(
        disengaged, on=GROUP + ["wave_number"], how="left"
    )
    fill = ["respondents", "composite_sum", "disengaged_respondents"] + [f"sum_{c}" for c in SCORE_COLS]
    cells[fill] = cells[fill].fillna(0.0)
    return cells.rename(columns={"legacy_entity_code": "entity", "wave_number": "wave"})


def _month_to_wave(ds: Dataset) -> pd.DataFrame:
    """Map each panel month to the wave period that contains it."""

    months = ds.headcount[["month"]].drop_duplicates().sort_values("month")
    waves = ds.waves
    assigned = pd.cut(
        months["month"],
        bins=[waves["period_start"].iloc[0] - pd.Timedelta(days=1)] + list(waves["period_end"]),
        labels=waves["wave_number"],
    )
    months["wave"] = assigned.astype("float").astype("Int64")
    return months


def attrition_cells(ds: Dataset) -> pd.DataFrame:
    """Exits and person-month exposure per entity x department x wave.

    Exposure is carried as person-months so any subset of cells can be summed and
    divided into exits to give an annualised rate — the average-headcount
    denominator the analysis insists on, expressed additively.
    """

    master = ds.master
    waves = ds.waves
    exits = master[master["is_departed"] & master["exit_date"].notna()].copy()

    bins = [waves["period_start"].iloc[0] - pd.Timedelta(days=1)] + list(waves["period_end"])
    exits["wave"] = (
        pd.cut(exits["exit_date"], bins=bins, labels=waves["wave_number"]).astype("float").astype("Int64")
    )
    exits = exits[exits["wave"].notna()]

    counts = (
        exits.groupby(GROUP + ["wave"])
        .agg(
            exits_total=("employee_id", "size"),
            exits_voluntary=("is_voluntary", "sum"),
            exits_involuntary=("is_involuntary", "sum"),
            exits_regrettable=("is_regrettable", "sum"),
        )
        .reset_index()
    )

    panel = ds.headcount.merge(_month_to_wave(ds), on="month", how="left")
    exposure = (
        panel[panel["wave"].notna()]
        .groupby(GROUP + ["wave"])
        .agg(person_months=("headcount", "sum"), n_months=("month", "nunique"))
        .reset_index()
    )

    cells = exposure.merge(counts, on=GROUP + ["wave"], how="left")
    count_cols = ["exits_total", "exits_voluntary", "exits_involuntary", "exits_regrettable"]
    cells[count_cols] = cells[count_cols].fillna(0).astype(int)
    return cells.rename(columns={"legacy_entity_code": "entity"})


def cost_cells(ds: Dataset) -> pd.DataFrame:
    """Annualised dollar exposure per entity x department, split by cost bucket.

    The four buckets reproduce the three components of
    ``analysis/04_financial_model.py`` (its hiring component is split into its two
    named halves so the cockpit can show them separately).
    """

    master = ds.master
    years = ds.window_years

    regret = master[master["is_regrettable"]].copy()
    regret["amount"] = loaded(regret["salary_at_exit"]) * REPL_MULT * BACKFILL_RATE / years

    disengaged = master[master["is_persistently_disengaged"] & ~master["is_departed"]].copy()
    disengaged["amount"] = loaded(disengaged["salary"]) * DISENGAGEMENT_LOSS_RATE

    agency = master[master["hired_in_window"] & (master["hire_source"] == "agency")].copy()
    agency["amount"] = (agency["salary"] * AGENCY_FEE_RATE - DIRECT_HIRE_COST) / years

    agency_early = agency[agency["early_exit_12mo"]].copy()
    agency_early["amount"] = (
        loaded(agency_early["salary"]) * REPL_MULT * BACKFILL_RATE / years
    )

    frames = []
    for bucket, frame in (
        ("regrettable_attrition", regret),
        ("disengagement_productivity", disengaged),
        ("agency_excess", agency),
        ("agency_early_exit", agency_early),
    ):
        rolled = frame.groupby(GROUP).agg(amount=("amount", "sum"), headcount=("employee_id", "size"))
        rolled = rolled.reset_index()
        rolled["bucket"] = bucket
        frames.append(rolled)

    return pd.concat(frames, ignore_index=True).rename(columns={"legacy_entity_code": "entity"})


def lead_time_cells(ds: Dataset) -> pd.DataFrame:
    """Histogram of warning-to-exit lead times per entity x department.

    Lead time is the gap between an employee's first responded survey below the
    disengagement threshold and their voluntary exit — how long the organisation
    had the signal before it lost the person. Stored as whole-month bin counts so a
    median can be recovered over any filtered subset without keeping per-person rows.
    """

    leavers = ds.master[ds.master["is_voluntary"] & ds.master["lead_time_months"].notna()].copy()
    leavers["months"] = leavers["lead_time_months"].round().clip(upper=36).astype(int)
    return (
        leavers.groupby(GROUP + ["months"])
        .size()
        .reset_index(name="n")
        .rename(columns={"legacy_entity_code": "entity"})
    )


def median_from_bins(months: pd.Series, counts: pd.Series) -> float | None:
    """Median of a whole-month histogram."""

    total = int(counts.sum())
    if total == 0:
        return None
    order = np.argsort(months.to_numpy())
    m = months.to_numpy()[order]
    c = counts.to_numpy()[order]
    cumulative = np.cumsum(c)
    idx = int(np.searchsorted(cumulative, total / 2))
    return float(m[min(idx, len(m) - 1)])


def flagged_cohorts(ds: Dataset, eng: pd.DataFrame, attr: pd.DataFrame, cost: pd.DataFrame) -> pd.DataFrame:
    """Entity x department cohorts crossing a monitoring threshold.

    A cohort is flagged when its disengagement is materially worse than the company
    (+5pp), its engagement trajectory is falling (<= -0.20 composite across waves),
    or its voluntary exit rate exceeds the company rate. Cohorts below
    ``MIN_COHORT_N`` are dropped entirely — the counts are returned to the caller so
    the suppression can be disclosed rather than hidden.
    """

    latest_wave = int(eng["wave"].max())

    scores = (
        eng.groupby(["entity", "department"])
        .agg(respondents=("respondents", "sum"), composite_sum=("composite_sum", "sum"),
             disengaged=("disengaged_respondents", "sum"), eligible=("eligible", "sum"))
        .reset_index()
    )
    scores["composite"] = scores["composite_sum"] / scores["respondents"].replace(0, np.nan)
    scores["disengaged_share"] = scores["disengaged"] / scores["respondents"].replace(0, np.nan)
    scores["response_rate"] = scores["respondents"] / scores["eligible"].replace(0, np.nan)

    # Trend runs between each cohort's own first and last wave with respondents —
    # the acquired entities only enter the survey partway through, so a fixed
    # first wave would leave them with no trajectory at all.
    observed = eng[eng["respondents"] > 0].copy()
    observed["mean"] = observed["composite_sum"] / observed["respondents"]
    observed = observed.sort_values("wave")
    trend = (
        observed.groupby(["entity", "department"])
        .agg(first_mean=("mean", "first"), last_mean=("mean", "last"), waves_seen=("wave", "nunique"))
        .reset_index()
    )
    trend["trend"] = np.where(
        trend["waves_seen"] >= 2, trend["last_mean"] - trend["first_mean"], np.nan
    )
    trend = trend[["entity", "department", "trend", "waves_seen"]]

    rates = (
        attr.groupby(["entity", "department"])
        .agg(exits_voluntary=("exits_voluntary", "sum"), person_months=("person_months", "sum"))
        .reset_index()
    )
    rates["voluntary_rate"] = rates["exits_voluntary"] / (rates["person_months"] / 12)

    exposure = cost.groupby(["entity", "department"]).agg(exposure=("amount", "sum")).reset_index()
    headcount = (
        ds.master[~ds.master["is_departed"]]
        .groupby(["legacy_entity_code", "department"])
        .size()
        .reset_index(name="headcount")
        .rename(columns={"legacy_entity_code": "entity"})
    )

    cohorts = (
        scores.merge(trend, on=["entity", "department"], how="left")
        .merge(rates, on=["entity", "department"], how="left")
        .merge(exposure, on=["entity", "department"], how="left")
        .merge(headcount, on=["entity", "department"], how="left")
    )
    cohorts[["exposure", "exits_voluntary", "person_months", "headcount"]] = cohorts[
        ["exposure", "exits_voluntary", "person_months", "headcount"]
    ].fillna(0)

    company_disengaged = scores["disengaged"].sum() / scores["respondents"].sum()
    company_rate = rates["exits_voluntary"].sum() / (rates["person_months"].sum() / 12)

    cohorts["flag_disengagement"] = cohorts["disengaged_share"] > company_disengaged + 0.05
    cohorts["flag_trend"] = cohorts["trend"] <= -0.20
    cohorts["flag_attrition"] = cohorts["voluntary_rate"] > company_rate
    cohorts["flag_response"] = cohorts["response_rate"] < RESPONSE_FLOOR
    flag_cols = ["flag_disengagement", "flag_trend", "flag_attrition", "flag_response"]
    cohorts["flags"] = cohorts[flag_cols].sum(axis=1)

    drivers = {
        "flag_disengagement": "Disengagement above company",
        "flag_trend": "Engagement falling",
        "flag_attrition": "Voluntary exits above company",
        "flag_response": "Survey coverage below 60%",
    }
    cohorts["driver"] = cohorts[flag_cols].apply(
        lambda row: " · ".join(drivers[c] for c in flag_cols if row[c]) or "—", axis=1
    )

    flagged = cohorts[cohorts["flags"] > 0].copy()
    suppressed = int((flagged["headcount"].fillna(0) < MIN_COHORT_N).sum())
    flagged = flagged[flagged["headcount"].fillna(0) >= MIN_COHORT_N]
    flagged = flagged.sort_values(["flags", "exposure"], ascending=False)
    flagged.attrs["suppressed"] = suppressed
    flagged.attrs["company_disengaged_share"] = float(company_disengaged)
    flagged.attrs["company_voluntary_rate"] = float(company_rate)
    return flagged
