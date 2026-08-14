"""Checkbox helpers for chart unit visibility."""

from __future__ import annotations

import streamlit as st


def unit_checkboxes(
    units: dict,
    key_prefix: str,
    default: list[str] | None = None,
    label: str = "Show units",
) -> list[str]:
    """Render checkboxes for each unit; return list of selected unit ids."""

    st.sidebar.markdown(f"**{label}**")
    selected: list[str] = []
    defaults = set(default or list(units.keys()))
    for unit_id, meta in units.items():
        unit_label = meta.get("label", unit_id) if isinstance(meta, dict) else unit_id
        checked = st.sidebar.checkbox(
            unit_label,
            value=unit_id in defaults,
            key=f"{key_prefix}_{unit_id}",
        )
        if checked:
            selected.append(unit_id)
    return selected
