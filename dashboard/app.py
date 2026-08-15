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
    render_overlay_bar,
    render_simple_bar,
)
from dashboard.components.checkboxes import unit_checkboxes
from dashboard.components.guardrails import render_guardrail_banner
from dashboard.components.state_loader import DEFAULT_CACHE, load_dashboard_cache

# Tier 1 — the pitch. Ordered problem → evidence → cost → solution → simulation.
TIER1_TITLES = {
    "headline": "The number is wrong",
    "entity_c": "The evidence",
    "cost_pilots": "What it costs",
    "solution_profit": "What we'd do",
    "prediction": "Simulate it",
}
TIER1_ORDER = list(TIER1_TITLES)

# Qualifiers pulled out of renamed titles so the caveat survives without blunting the headline.
PAGE_SUBTITLES = {
    "prediction": "Aggregate only — no individual risk scores.",
}

# Charts whose footnote is the finding: promote it to a callout above the chart.
CALLOUT_CHARTS = {"headline_attrition"}

# Charts drawn as an overlay (published label traced on top of the actual bar).
OVERLAY_CHARTS = {"headline_attrition"}

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

# PowerBI‑style theme toggle
theme = st.sidebar.selectbox("Theme", ["Light", "Dark"], index=0)

# Inject CSS for PowerBI‑style cards and theming
if theme == "Light":
    bg_color = "#f5f4ef"
    card_bg = "#ffffff"
    text_color = "#102b36"
else:
    bg_color = "#202020"
    card_bg = "#2b2b2b"
    text_color = "#ffffff"

TEXT_COLOR = text_color

st.markdown(
    f"""
    <style>
    .stApp {{ background-color: {bg_color}; color: {text_color}; }}
    .card {{
        background-color: {card_bg};
        border-radius: 4px;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: transform 0.2s, box-shadow 0.2s;
    }}
    .card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }}
    /* Sidebar customizations */
    [data-testid="stSidebar"] {{
        background-color: #0d2630; color: #d8e4e7; overflow-y: auto;
    }}
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] small,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
    [data-testid="stSidebar"] [data-testid="stRadio"] label,
    [data-testid="stSidebar"] [data-testid="stRadio"] span,
    [data-testid="stSidebar"] [data-testid="stCheckbox"] label,
    [data-testid="stSidebar"] [data-testid="stCheckbox"] span,
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"],
    [data-testid="stSidebar"] summary,
    [data-testid="stSidebar"] summary p {{
        color: #d8e4e7 !important;
    }}
    [data-testid="stSidebar"] summary svg {{ fill: #d8e4e7 !important; }}
    /* Streamlit tints Plotly axis/legend text with its own base theme, which fights
       the canvas color set above; pin it to the selected theme's ink instead. */
    [data-testid="stPlotlyChart"] .xtick text,
    [data-testid="stPlotlyChart"] .ytick text,
    [data-testid="stPlotlyChart"] .legendtext,
    [data-testid="stPlotlyChart"] .xtitle,
    [data-testid="stPlotlyChart"] .ytitle,
    [data-testid="stPlotlyChart"] .gtitle {{
        fill: {text_color} !important;
    }}
    [data-testid="stSidebar"] details {{ border-color: rgba(216,228,231,0.25) !important; }}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner="Loading chart catalog…")
def _load_catalog(path: str, cache_version: str) -> dict:
    del cache_version
    return load_dashboard_cache(path)


def page_title(page_def: dict) -> str:
    """Pitch-voice title for Tier 1 pages; the catalog title everywhere else."""

    return TIER1_TITLES.get(page_def["id"], page_def["title"])


def _series_checkboxes(
    chart: dict,
    key_prefix: str,
    label: str = "Show series",
    container=None,
) -> list[str]:
    target = container if container is not None else st.sidebar
    target.markdown(f"**{label}**")
    selected = []
    keys = chart.get("series_keys", [])
    labels = chart.get("series_labels", {})
    defaults = set(chart.get("default_series", keys))
    for sk in keys:
        if target.checkbox(labels.get(sk, sk), value=sk in defaults, key=f"{key_prefix}_series_{sk}"):
            selected.append(sk)
    return selected


def _render_chart(
    chart: dict,
    visible_units: list[str],
    visible_series: list[str] | None = None,
    chart_id: str | None = None,
) -> None:
    ctype = chart["type"]
    if chart_id in OVERLAY_CHARTS:
        render_overlay_bar(chart, visible_units, visible_series)
    elif ctype == "multi_line":
        render_multi_line(chart, visible_units)
    elif ctype == "grouped_bar":
        render_grouped_bar(chart, visible_units, visible_series)
    elif ctype == "bar":
        render_simple_bar(chart, visible_units)
    elif ctype == "decile_bar":
        render_decile_bars(chart, visible_series or chart.get("default_series", []))
    elif ctype == "calibration":
        render_calibration(chart, visible_series or chart.get("default_series", []))
    if chart.get("footnote") and chart_id not in CALLOUT_CHARTS:
        st.caption(chart["footnote"])


def _render_callout(text: str, text_color: str) -> None:
    """Headline claim above the chart — the chart is the evidence underneath it."""

    with st.container(border=True):
        st.markdown(
            f"<p style='font-size:1.9rem;font-weight:700;line-height:1.3;margin:0;"
            f"color:{text_color}'>{text}</p>",
            unsafe_allow_html=True,
        )


def render_page(catalog: dict, page_def: dict, tier1: bool = False) -> None:
    charts = catalog["charts"]
    page_id = page_def["id"]

    st.subheader(page_title(page_def))
    if PAGE_SUBTITLES.get(page_id):
        st.caption(PAGE_SUBTITLES[page_id])

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

        wants_series = False
        if page_def.get("has_series_checkboxes"):
            target = page_def.get("series_chart") or page_def.get("overview_chart") or chart_id
            wants_series = chart_id == target or (
                not page_def.get("series_chart") and bool(chart.get("series_keys"))
            )

        if chart_id in CALLOUT_CHARTS and chart.get("footnote"):
            _render_callout(chart["footnote"], TEXT_COLOR)
            st.caption(chart["title"])
        elif len(chart_ids) > 1 or not page_def.get("dimension_picker"):
            st.markdown(f"#### {chart['title']}")

        # Tier 1 pages lead with the finding: controls live in a closed expander
        # under the chart heading instead of always-on sidebar checkboxes.
        controls = None
        if tier1 and (chart.get("units") or wants_series):
            controls = st.expander("Customize this chart", expanded=False)

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
                container=controls,
            )
        else:
            visible_units = []

        visible_series = None
        if wants_series:
            visible_series = _series_checkboxes(
                chart,
                key_prefix=f"{page_id}_{chart_id}",
                label=page_def.get("series_checkbox_label", "Show series"),
                container=controls,
            )

        _render_chart(chart, visible_units, visible_series, chart_id=chart_id)


def _select_pitch() -> None:
    if st.session_state.nav_pitch:
        st.session_state.active_page = st.session_state.nav_pitch
        st.session_state.nav_explore = None


def _select_explore() -> None:
    if st.session_state.nav_explore:
        st.session_state.active_page = st.session_state.nav_explore
        st.session_state.nav_pitch = None


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
    page_by_id = {p["id"]: p for p in pages}
    pitch_ids = [pid for pid in TIER1_ORDER if pid in page_by_id]
    explore_ids = [p["id"] for p in pages if p["id"] not in pitch_ids]

    if not pitch_ids:  # nothing renamed matched the catalog — fall back to a flat list
        pitch_ids, explore_ids = [p["id"] for p in pages], []

    if "active_page" not in st.session_state:
        st.session_state.active_page = pitch_ids[0]
        st.session_state.nav_pitch = pitch_ids[0]
        st.session_state.nav_explore = None

    def label_of(page_id: str) -> str:
        return page_title(page_by_id[page_id])

    with st.sidebar:
        st.markdown("## NovaCorp")
        st.caption("The pitch")
        st.radio(
            "The pitch",
            pitch_ids,
            index=None,
            format_func=label_of,
            key="nav_pitch",
            on_change=_select_pitch,
            label_visibility="collapsed",
        )
        if explore_ids:
            with st.expander("Explore the data", expanded=False):
                st.radio(
                    "Explore the data",
                    explore_ids,
                    index=None,
                    format_func=label_of,
                    key="nav_explore",
                    on_change=_select_explore,
                    label_visibility="collapsed",
                )
        st.divider()
        meta = catalog.get("meta", {})
        st.caption(f"{meta.get('chart_count', '?')} charts · 2024–2025")

    active_id = st.session_state.active_page
    if active_id not in page_by_id:
        active_id = pitch_ids[0]
        st.session_state.active_page = active_id
    is_tier1 = active_id in pitch_ids

    st.title("NovaCorp People Analytics")
    if is_tier1:
        st.caption("Open 'Customize this chart' to change what each chart shows")
    else:
        st.caption("Use checkboxes in the sidebar to show or hide lines, bars, and cohorts")
    render_guardrail_banner()

    render_page(catalog, page_by_id[active_id], tier1=is_tier1)


if __name__ == "__main__":
    main()
