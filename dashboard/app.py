"""NovaCorp People Assurance Dashboard — chart-first, checkbox-driven."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dashboard.components.guardrails import render_guardrail_banner
from dashboard.components.state_loader import DEFAULT_CACHE, load_dashboard_cache
from dashboard.pages.views import build_page_renderers

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
    /* Engagement dimension selectbox: black default text on white control */
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
def _load_catalog(path: str) -> dict:
    return load_dashboard_cache(path)


def main() -> None:
    try:
        catalog = _load_catalog(str(DEFAULT_CACHE))
    except FileNotFoundError as exc:
        st.error(str(exc))
        st.code("python3 -m src.dashboard.build_cache")
        st.stop()

    pages = catalog["pages"]
    page_titles = [p["title"] for p in pages]
    renderers = build_page_renderers(catalog)

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

    renderers[page]()


if __name__ == "__main__":
    main()
