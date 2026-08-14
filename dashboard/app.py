"""NovaCorp People Assurance Dashboard — chart-first, checkbox-driven."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dashboard.components.charts import (
    render_calibration,
    render_decile_bars,
    render_grouped_bar,
    render_multi_line,
    render_simple_bar,
)
from dashboard.components.checkboxes import unit_checkboxes
from dashboard.components.guardrails import render_guardrail_banner
from dashboard.components.state_loader import DEFAULT_CACHE, load_dashboard_cache

DIMENSION_LABELS = {
    "manager_effectiveness": "Manager effectiveness",
    "psychological_safety": "Psychological safety",
    "recognition": "Recognition",
    "career_development": "Career development",
    "senior_leadership_trust": "Senior leadership trust",
    "purpose_meaning": "Purpose & meaning",
    "wellbeing": "Wellbeing",
    "confidence_in_role_future": "Confidence in role future",
}

st.set_page_config(
    page_title="NovaCorp · People Assurance",
    page_icon="N",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp { background-color: #f5f4ef; }
    [data-testid="stSidebar"] {
        background-color: #0d2630;
        color: #d8e4e7;
        overflow-y: auto;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] {
        max-height: 62vh;
        overflow-y: auto;
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] small,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
    [data-testid="stSidebar"] [data-testid="stRadio"] label,
    [data-testid="stSidebar"] [data-testid="stRadio"] div,
    [data-testid="stSidebar"] [data-testid="stRadio"] span,
    [data-testid="stSidebar"] [data-testid="stCheckbox"] label,
    [data-testid="stSidebar"] [data-testid="stCheckbox"] span,
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] {
        color: #d8e4e7 !important;
    }
    [data-testid="stSidebar"] [data-testid="stSelectbox"] [data-testid="stWidgetLabel"],
    [data-testid="stSidebar"] [data-testid="stSelectbox"] label {
        color: #89e0d5 !important;
    }
    [data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] {
        background-color: #ffffff !important;
        color: #000000 !important;
    }
    [data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] *,
    [data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] input,
    [data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    [data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] > div > div,
    [data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] span,
    [data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] div[value] {
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        caret-color: #000000 !important;
    }
    [data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] input {
        background-color: #ffffff !important;
    }
    div[data-baseweb="popover"] li,
    div[data-baseweb="popover"] li * {
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
    }
    h1, h2, h3, h4 { color: #102b36; letter-spacing: -0.02em; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner="Loading chart catalog…")
def _load_catalog(path: str, cache_version: str) -> dict:
    del cache_version
    return load_dashboard_cache(path)


def _series_checkboxes(
    chart: dict,
    key_prefix: str,
    label: str = "Show series",
) -> list[str]:
    st.sidebar.markdown(f"**{label}**")
    selected = []
    keys = chart.get("series_keys", [])
    labels = chart.get("series_labels", {})
    defaults = set(chart.get("default_series", keys))
    for sk in keys:
        if st.sidebar.checkbox(labels.get(sk, sk), value=sk in defaults, key=f"{key_prefix}_series_{sk}"):
            selected.append(sk)
    return selected


def _render_chart(chart: dict, visible_units: list[str], visible_series: list[str] | None = None) -> None:
    ctype = chart["type"]
    if ctype == "multi_line":
        render_multi_line(chart, visible_units)
    elif ctype == "grouped_bar":
        render_grouped_bar(chart, visible_units, visible_series)
    elif ctype == "bar":
        render_simple_bar(chart, visible_units)
    elif ctype == "decile_bar":
        render_decile_bars(chart, visible_series or chart.get("default_series", []))
    elif ctype == "calibration":
        render_calibration(chart, visible_series or chart.get("default_series", []))
    if chart.get("footnote"):
        st.caption(chart["footnote"])


def render_page(catalog: dict, page_def: dict) -> None:
    charts = catalog["charts"]
    page_id = page_def["id"]

    st.subheader(page_def["title"])

    if page_def.get("dimension_picker"):
        dim = st.sidebar.selectbox(
            "Engagement dimension",
            [c.replace("engagement_", "") for c in page_def["charts"]],
            format_func=lambda d: DIMENSION_LABELS.get(d, d),
            key=f"{page_id}_dimension",
        )
        chart_ids = [f"engagement_{dim}"]
    else:
        chart_ids = page_def["charts"]

    for chart_id in chart_ids:
        chart = charts[chart_id]

        if len(chart_ids) > 1 or not page_def.get("dimension_picker"):
            st.markdown(f"#### {chart['title']}")

        if chart.get("units"):
            unit_meta = {
                uid: {"label": u.get("label", uid) if isinstance(u, dict) else uid}
                for uid, u in chart["units"].items()
            }
            visible_units = unit_checkboxes(
                unit_meta,
                key_prefix=f"{page_id}_{chart_id}",
                default=chart.get("default_units"),
                label="Show in chart",
            )
        else:
            visible_units = []

        visible_series = None
        if page_def.get("has_series_checkboxes"):
            target = page_def.get("series_chart") or page_def.get("overview_chart") or chart_id
            if chart_id == target or (not page_def.get("series_chart") and chart.get("series_keys")):
                visible_series = _series_checkboxes(
                    chart,
                    key_prefix=f"{page_id}_{chart_id}",
                    label=page_def.get("series_checkbox_label", "Show series"),
                )

        _render_chart(chart, visible_units, visible_series)


def main() -> None:
    cache_path = DEFAULT_CACHE
    cache_version = str(cache_path.stat().st_mtime) if cache_path.exists() else "missing"
    try:
        catalog = _load_catalog(str(cache_path), cache_version)
    except FileNotFoundError as exc:
        st.error(str(exc))
        st.code("python3 -m src.dashboard.build_cache")
        st.stop()

    pages = catalog["pages"]
    page_titles = [p["title"] for p in pages]
    page_by_title = {p["title"]: p for p in pages}

    with st.sidebar:
        st.markdown("## NovaCorp")
        st.caption("Toggle units on/off to build each chart")
        page = st.radio("Section", page_titles, label_visibility="collapsed")
        st.divider()
        meta = catalog.get("meta", {})
        st.caption(f"{meta.get('chart_count', '?')} charts · 2024–2025")

    st.title("NovaCorp People Analytics")
    st.caption("Use checkboxes in the sidebar to show or hide lines, bars, and cohorts")
    render_guardrail_banner()

    render_page(catalog, page_by_title[page])


if __name__ == "__main__":
    main()
