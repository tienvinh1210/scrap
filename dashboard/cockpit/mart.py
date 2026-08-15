"""Load the monitoring mart and turn a filter selection into numbers.

The mart holds additive cells (sums and counts, never pre-divided means), so every
figure here is "filter the cells, then divide" — which keeps a rate correct for any
combination of entity, department and wave.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.monitor.metrics import ADDRESSABLE_BAND, COST_BUCKETS, median_from_bins

REPO_ROOT = Path(__file__).resolve().parents[2]
MART_PATH = REPO_ROOT / "outputs" / "monitor" / "monitor_mart.json"

ALL = "All"

CELL_TABLES = (
    "engagement_cells",
    "attrition_cells",
    "cost_cells",
    "lead_time_cells",
    "flagged_cohorts",
    "waves",
)


@st.cache_data(show_spinner="Loading monitoring mart…")
def load_mart(path: str, version: str) -> dict:
    del version  # cache key only
    import json

    file = Path(path)
    if not file.exists():
        raise FileNotFoundError(
            f"Monitoring mart not found at {file}. Run: python -m src.monitor.build_mart"
        )
    with file.open(encoding="utf-8") as handle:
        return json.load(handle)


@st.cache_data(show_spinner=False)
def dataset_frames(path: str, version: str, dataset_key: str) -> dict[str, pd.DataFrame]:
    """One dataset's cell tables as DataFrames."""

    block = load_mart(path, version)["datasets"][dataset_key]
    frames = {name: pd.DataFrame(block[name]) for name in CELL_TABLES}
    frames["meta"] = pd.DataFrame([{k: v for k, v in block.items() if not isinstance(v, (list, dict))}])
    return frames


def mart_version() -> str:
    return str(MART_PATH.stat().st_mtime) if MART_PATH.exists() else "missing"


def filter_cells(
    frame: pd.DataFrame, entity: str = ALL, department: str = ALL, wave: int | None = None
) -> pd.DataFrame:
    """Apply the three filters, skipping any that the table has no column for."""

    out = frame
    if entity != ALL and "entity" in out.columns:
        out = out[out["entity"] == entity]
    if department != ALL and "department" in out.columns:
        out = out[out["department"] == department]
    if wave is not None and "wave" in out.columns:
        out = out[out["wave"] == wave]
    return out


def _rate(numerator: float, person_months: float) -> float | None:
    if not person_months:
        return None
    return numerator / (person_months / 12)


def response_rates(
    engagement: pd.DataFrame, entity: str, department: str, wave: int | None
) -> tuple[float | None, float | None, int]:
    """(selection rate, company rate, wave used) at a single wave.

    Coverage is only comparable within a wave, so with no wave selected this reads
    the latest one rather than pooling the whole history.
    """

    if engagement.empty:
        return None, None, 0
    target = wave if wave is not None else int(engagement["wave"].max())

    def rate(frame: pd.DataFrame) -> float | None:
        at_wave = frame[frame["wave"] == target]
        eligible = at_wave["eligible"].sum()
        return float(at_wave["respondents"].sum() / eligible) if eligible else None

    return rate(filter_cells(engagement, entity, department)), rate(engagement), target


def kpis(frames: dict[str, pd.DataFrame], entity: str, department: str, wave: int | None) -> dict:
    """The four header tiles for the current selection."""

    cost = filter_cells(frames["cost_cells"], entity, department)
    total_cost = float(cost["amount"].sum()) if not cost.empty else 0.0

    lead = filter_cells(frames["lead_time_cells"], entity, department)
    median_lead = median_from_bins(lead["months"], lead["n"]) if not lead.empty else None

    selection_rate, company_rate, wave_used = response_rates(
        frames["engagement_cells"], entity, department, wave
    )

    attrition = filter_cells(frames["attrition_cells"], entity, department, wave)

    return {
        "total_cost": total_cost,
        "addressable": (total_cost * ADDRESSABLE_BAND[0], total_cost * ADDRESSABLE_BAND[1]),
        "response_selection": selection_rate,
        "response_company": company_rate,
        "response_wave": wave_used,
        "lead_time_months": median_lead,
        "lead_time_n": int(lead["n"].sum()) if not lead.empty else 0,
        "voluntary_rate": _rate(
            attrition["exits_voluntary"].sum(), attrition["person_months"].sum()
        ),
        "exits_voluntary": int(attrition["exits_voluntary"].sum()) if not attrition.empty else 0,
    }


def cost_bucket_totals(frames: dict[str, pd.DataFrame], entity: str, department: str) -> pd.DataFrame:
    """Cost buckets for the selection, in the mart's declared bucket order."""

    cost = filter_cells(frames["cost_cells"], entity, department)
    totals = cost.groupby("bucket")["amount"].sum()
    return pd.DataFrame(
        [
            {"bucket": key, "label": label, "amount": float(totals.get(key, 0.0))}
            for key, label in COST_BUCKETS.items()
        ]
    )


def engagement_series(frames: dict[str, pd.DataFrame], entity: str, department: str) -> pd.DataFrame:
    """Mean composite per wave for the selection (respondent-weighted)."""

    eng = filter_cells(frames["engagement_cells"], entity, department)
    rolled = eng.groupby("wave").agg(
        respondents=("respondents", "sum"),
        composite_sum=("composite_sum", "sum"),
        eligible=("eligible", "sum"),
        disengaged=("disengaged_respondents", "sum"),
    )
    rolled = rolled[rolled["respondents"] > 0]
    rolled["composite"] = rolled["composite_sum"] / rolled["respondents"]
    rolled["response_rate"] = rolled["respondents"] / rolled["eligible"]
    rolled["disengaged_share"] = rolled["disengaged"] / rolled["respondents"]
    return rolled.reset_index()


def attrition_series(frames: dict[str, pd.DataFrame], entity: str, department: str) -> pd.DataFrame:
    """Annualised voluntary exit rate per wave for the selection."""

    attr = filter_cells(frames["attrition_cells"], entity, department)
    rolled = attr.groupby("wave").agg(
        exits_voluntary=("exits_voluntary", "sum"),
        exits_total=("exits_total", "sum"),
        person_months=("person_months", "sum"),
    )
    rolled["voluntary_rate"] = rolled["exits_voluntary"] / (rolled["person_months"] / 12)
    return rolled.reset_index()


def matrix_cells(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Composite per department x entity x wave — the heat matrix's sparklines."""

    eng = frames["engagement_cells"]
    rolled = eng.groupby(["department", "entity", "wave"]).agg(
        respondents=("respondents", "sum"), composite_sum=("composite_sum", "sum")
    )
    rolled = rolled[rolled["respondents"] > 0].reset_index()
    rolled["composite"] = rolled["composite_sum"] / rolled["respondents"]
    return rolled
