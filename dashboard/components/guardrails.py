"""Evidence badges, footnotes, and ethics banners."""

from __future__ import annotations

import streamlit as st

EVIDENCE_COLORS = {
    "descriptive": "#18776e",
    "predictive": "#876014",
    "observational": "#526970",
    "speculative": "#a74330",
    "governance": "#0d817b",
    "mixed": "#526970",
    "review register": "#526970",
}


def render_guardrail_banner() -> None:
    st.info(
        "**Responsible use:** Aggregate-only views. No employee IDs or individual risk scores. "
        "Financial scenarios are not forecasts—do not sum across pilots."
    )


def render_evidence_badge(evidence_type: str | None, reviewer_status: str | None) -> None:
    if not evidence_type:
        return
    color = EVIDENCE_COLORS.get(evidence_type.split()[0], "#526970")
    status = reviewer_status or "unknown"
    st.markdown(
        f"<span style='background:#eef8f6;color:{color};padding:4px 10px;border-radius:999px;"
        f"font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px'>"
        f"{evidence_type}</span> "
        f"<span style='background:#f5f4ef;color:#64747a;padding:4px 10px;border-radius:999px;"
        f"font-size:11px;font-weight:700'>Review: {status}</span>",
        unsafe_allow_html=True,
    )


def render_footnote(state: dict) -> None:
    parts = []
    kpis = state.get("kpis") or {}
    if "numerator" in kpis and "denominator" in kpis:
        parts.append(f"n={kpis['numerator']:,} / N={kpis['denominator']:,}")
    if state.get("interpretation"):
        parts.append(state["interpretation"])
    if parts:
        st.caption(" · ".join(parts))


def render_warning(text: str) -> None:
    st.error(text)
