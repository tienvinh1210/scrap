"""Chart-only dashboard pages with checkbox unit toggles."""

from __future__ import annotations

import streamlit as st

from dashboard.components.charts import (
    render_calibration,
    render_decile_bars,
    render_grouped_bar,
    render_multi_line,
    render_simple_bar,
)
from dashboard.components.checkboxes import unit_checkboxes

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

    # Engagement page: pick dimension (which chart), then entity checkboxes
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

        # Unit checkboxes (entities, departments, pilots, etc.)
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

        # Series checkboxes (rate types, scenario %, observed/predicted)
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


def build_page_renderers(catalog: dict) -> dict[str, callable]:
    return {
        page["title"]: (lambda c=catalog, p=page: render_page(c, p))
        for page in catalog["pages"]
    }
