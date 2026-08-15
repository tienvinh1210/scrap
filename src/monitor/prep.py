"""Load a NovaCorp dataset directory into the tables the monitoring mart needs.

This is a parameterised re-implementation of ``analysis/01_data_prep.py`` so the
same derivations can be run over the observed data *and* over each simulated
scenario directory. The analysis script itself is left alone — other scripts in
``analysis/`` depend on the files it writes.

Every definition below is carried over deliberately and must not drift, because
the cockpit's money figures are reconciled against the deck:

* ``engagement_composite`` = mean of the eight dimension columns (01_data_prep.py:81-86)
* ``is_high_value`` = role_level >= 3 or hipo_flag (01_data_prep.py:76)
* disengaged threshold 3.0, and "persistent" additionally requires >= 2 responses
  (01_data_prep.py:170-175) — Proofs.md:72 documents an audit that turns on exactly
  this distinction
* attrition denominators use average monthly headcount, not end-of-window actives
  (01_data_prep.py:180-187)
* ``response_flag == False`` rows are retained; non-response is itself a signal
  (01_data_prep.py:33-34)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]

#: Dataset directories. The root-level CSVs are md5-identical to the 0_case copies;
#: 0_case is used because that is what scenarios/generate_scenarios.py reads from.
DATASETS = {
    "observed": {
        "label": "Observed",
        "dir": REPO_ROOT / "0_case" / "Accenture_Case_Comp_Data",
        "synthetic": False,
    },
    "scenario_a": {
        "label": "Scenario A — deteriorating",
        "dir": REPO_ROOT / "scenarios" / "scenario_a_deteriorating",
        "synthetic": True,
    },
    "scenario_b": {
        "label": "Scenario B — improving",
        "dir": REPO_ROOT / "scenarios" / "scenario_b_improving",
        "synthetic": True,
    },
}

#: Waves at or beyond this number exist only in the simulated extensions.
FIRST_SIMULATED_WAVE = 6

WINDOW_START = pd.Timestamp("2024-01-01")

SCORE_COLS = [
    "manager_effectiveness",
    "psychological_safety",
    "recognition",
    "career_development",
    "senior_leadership_trust",
    "purpose_meaning",
    "wellbeing",
    "confidence_in_role_future",
]

DISENGAGED_THRESHOLD = 3.0

ENTITIES = ["Entity_A", "Entity_B", "Entity_C", "NovaCorp-Origin"]
DEPARTMENTS = [
    "Retail Banking",
    "Technology",
    "Risk & Compliance",
    "Insurance",
    "Wealth Management",
    "Corporate Operations",
    "Executive Leadership",
]


@dataclass
class Dataset:
    """Everything the metrics layer needs from one dataset directory."""

    key: str
    label: str
    synthetic: bool
    master: pd.DataFrame  # one row per employee
    engagement: pd.DataFrame  # one row per employee-wave, entity/department joined
    waves: pd.DataFrame  # one row per wave: bounds, midpoint, simulated flag
    headcount: pd.DataFrame  # month x entity x department average-headcount panel
    window_start: pd.Timestamp
    window_end: pd.Timestamp

    @property
    def window_years(self) -> float:
        return (self.window_end - self.window_start + pd.Timedelta(days=1)).days / 365.25


def _read(data_dir: Path, name: str, dates: list[str]) -> pd.DataFrame:
    path = data_dir / name
    if not path.exists():
        raise FileNotFoundError(f"Missing {name} in {data_dir}")
    return pd.read_csv(path, parse_dates=dates, low_memory=False)


def _wave_table(eng: pd.DataFrame) -> pd.DataFrame:
    """Wave bounds plus the exit-attribution period for each wave.

    A wave's *period* runs from the end of the previous wave's survey window to the
    end of its own, so every exit in the observation window lands in exactly one
    wave. Exits before wave 1 closes are attributed to wave 1; exits after the last
    wave closes are attributed to the last wave (the caller clips the tail).
    """

    waves = (
        eng.groupby("wave_number")
        .agg(survey_start=("survey_date", "min"), survey_end=("survey_date", "max"))
        .reset_index()
        .sort_values("wave_number")
    )
    waves["midpoint"] = waves["survey_start"] + (waves["survey_end"] - waves["survey_start"]) / 2
    waves["period_start"] = waves["survey_end"].shift(1) + pd.Timedelta(days=1)
    waves.loc[waves.index[0], "period_start"] = WINDOW_START
    waves["period_end"] = waves["survey_end"]
    waves["simulated"] = waves["wave_number"] >= FIRST_SIMULATED_WAVE
    waves["label"] = "Wave " + waves["wave_number"].astype(str)
    return waves.reset_index(drop=True)


def _headcount_panel(emp: pd.DataFrame, window_end: pd.Timestamp) -> pd.DataFrame:
    """Month x entity x department active headcount.

    Averaging this panel over a period gives the average-headcount denominator the
    analysis uses; dividing by end-of-window actives would overstate every rate.
    """

    months = pd.date_range(WINDOW_START, window_end, freq="MS")
    keep = emp[["legacy_entity_code", "department", "hire_date", "exit_date"]]
    frames = []
    for month in months:
        month_end = month + pd.offsets.MonthEnd(0)
        active = keep[
            (keep["hire_date"] <= month_end)
            & (keep["exit_date"].isna() | (keep["exit_date"] >= month))
        ]
        counts = (
            active.groupby(["legacy_entity_code", "department"]).size().reset_index(name="headcount")
        )
        counts["month"] = month
        frames.append(counts)
    return pd.concat(frames, ignore_index=True)


def build_master(data_dir: Path | str) -> Dataset:
    """Build the employee-grain master table and its companions for one dataset."""

    data_dir = Path(data_dir)
    emp = _read(data_dir, "employees.csv", ["hire_date", "exit_date"])
    attr = _read(data_dir, "attrition_log.csv", ["exit_date"])
    eng = _read(data_dir, "engagement.csv", ["survey_date"])

    # --- employee master ---------------------------------------------------
    master = emp.merge(attr.drop(columns=["exit_date"]), on="employee_id", how="left")

    master["is_departed"] = master["status"] == "departed"
    master["is_voluntary"] = master["exit_type"] == "voluntary"
    master["is_involuntary"] = master["exit_type"] == "involuntary"
    master["is_regrettable"] = master["regrettable_flag"] == True  # noqa: E712 — NaN-safe
    master["early_exit_12mo"] = master["is_departed"] & (master["tenure_months"] <= 12)
    master["hired_in_window"] = master["hire_date"] >= WINDOW_START
    master["is_high_value"] = (master["role_level"] >= 3) | (master["hipo_flag"])

    # --- engagement, employee-wave grain -----------------------------------
    eng["engagement_composite"] = eng[SCORE_COLS].mean(axis=1)
    eng = eng.merge(
        emp[["employee_id", "legacy_entity_code", "department", "role_level", "salary"]],
        on="employee_id",
        how="left",
    )

    responded = eng[eng["response_flag"]].sort_values(["employee_id", "wave_number"])

    summary = eng.groupby("employee_id").agg(
        waves_issued=("wave_number", "count"),
        waves_responded=("response_flag", "sum"),
        avg_engagement=("engagement_composite", "mean"),
    )
    summary["response_rate"] = summary["waves_responded"] / summary["waves_issued"]

    first_last = responded.groupby("employee_id").agg(
        first_score=("engagement_composite", "first"),
        last_score=("engagement_composite", "last"),
        n_responses=("wave_number", "count"),
    )
    first_last["engagement_trend"] = np.where(
        first_last["n_responses"] >= 2,
        first_last["last_score"] - first_last["first_score"],
        np.nan,
    )

    # First responded wave below the disengagement threshold — the warning the
    # organisation could have acted on. Drives attrition lead time.
    low = responded[responded["engagement_composite"] < DISENGAGED_THRESHOLD]
    first_low = (
        low.groupby("employee_id")
        .agg(first_low_wave=("wave_number", "first"), first_low_date=("survey_date", "first"))
    )

    master = (
        master.merge(summary, on="employee_id", how="left")
        .merge(first_last[["n_responses", "engagement_trend"]], on="employee_id", how="left")
        .merge(first_low, on="employee_id", how="left")
    )

    master["is_disengaged"] = master["avg_engagement"] < DISENGAGED_THRESHOLD
    master["is_persistently_disengaged"] = master["is_disengaged"] & (
        master["n_responses"].fillna(0) >= 2
    )

    # Months from the first low-engagement wave to the exit. Negative values mean
    # the warning came after the exit date, so they are not lead time.
    lead = (master["exit_date"] - master["first_low_date"]).dt.days / 30.4375
    master["lead_time_months"] = lead.where(lead >= 0)

    waves = _wave_table(eng)
    window_end = max(
        pd.Timestamp(eng["survey_date"].max()),
        pd.Timestamp(attr["exit_date"].max()),
    ) + pd.offsets.MonthEnd(0)
    # The last wave closes months before the data does; stretch its period to the
    # window end so every exit is attributed to exactly one wave.
    waves.loc[waves.index[-1], "period_end"] = window_end
    waves["period_days"] = (waves["period_end"] - waves["period_start"]).dt.days + 1

    return Dataset(
        key=data_dir.name,
        label=data_dir.name,
        synthetic=False,
        master=master,
        engagement=eng,
        waves=waves,
        headcount=_headcount_panel(emp, window_end),
        window_start=WINDOW_START,
        window_end=window_end,
    )


def load_dataset(key: str) -> Dataset:
    """Load one of the three named datasets with its display metadata attached."""

    spec = DATASETS[key]
    dataset = build_master(spec["dir"])
    dataset.key = key
    dataset.label = spec["label"]
    dataset.synthetic = spec["synthetic"]
    return dataset
