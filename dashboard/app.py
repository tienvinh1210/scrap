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
    [data-testid="stSidebar"] { background-color: #0d2630; }
    [data-testid="stSidebar"] * { color: #d8e4e7 !important; }
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p, [data-testid="stSidebar"] small {
        color: #d8e4e7 !important;
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
