"""Plotly chart helpers — series filtered by checkbox selection."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

NAVY = "#0d2630"
TEAL = "#0d817b"
MINT = "#89e0d5"
CORAL = "#e66a50"
AMBER = "#e7a743"
PILOT_COLORS = [TEAL, CORAL, AMBER]


def _format_value(val: float | None, fmt: str) -> str | None:
    if val is None:
        return None
    if fmt == "percent":
        return f"{100 * val:.1f}%"
    if fmt == "money":
        return f"${val / 1e6:.2f}M" if val >= 1e6 else f"${val:,.0f}"
    return f"{val:.2f}"


def _layout(title: str, y_title: str, height: int = 420) -> dict:
    return dict(
        title=dict(text=title, font=dict(size=15, color=NAVY)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=NAVY, size=11),
        margin=dict(l=48, r=24, t=56, b=48),
        xaxis=dict(showgrid=False, title=""),
        yaxis=dict(showgrid=True, gridcolor="#e5e9e7", title=y_title),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        height=height,
    )


def render_multi_line(
    chart: dict,
    visible_units: list[str],
) -> None:
    units = chart["units"]
    fig = go.Figure()
    for unit_id in visible_units:
        if unit_id not in units:
            continue
        s = units[unit_id]
        fig.add_trace(
            go.Scatter(
                x=s["x"],
                y=s["y"],
                mode="lines+markers",
                name=s.get("label", unit_id),
                line=dict(color=s.get("color", TEAL), width=2.5),
                connectgaps=False,
            )
        )
    if not visible_units:
        st.warning("Select at least one unit to display.")
        return
    fig.update_layout(**_layout(chart.get("title", ""), chart.get("y_label", "")))
    if chart.get("x_label"):
        fig.update_xaxes(title=chart["x_label"])
    st.plotly_chart(fig, use_container_width=True)


def render_grouped_bar(
    chart: dict,
    visible_units: list[str],
    visible_series: list[str] | None = None,
) -> None:
    units = chart["units"]
    series_keys = visible_series or chart.get("series_keys", [])
    fig = go.Figure()
    colors = chart.get("series_colors", [TEAL, MINT, CORAL, AMBER])
    for i, series_key in enumerate(series_keys):
        x_vals = []
        y_vals = []
        text = []
        for unit_id in visible_units:
            if unit_id not in units:
                continue
            u = units[unit_id]
            if series_key not in u.get("series", {}):
                continue
            val = u["series"][series_key]
            if val is None:
                continue
            x_vals.append(u.get("label", unit_id))
            y_vals.append(val)
            text.append(_format_value(val, chart.get("y_format", "number")))
        if x_vals:
            fig.add_bar(
                name=chart["series_labels"].get(series_key, series_key),
                x=x_vals,
                y=y_vals,
                text=text,
                textposition="outside",
                marker_color=colors[i % len(colors)],
            )
    if not visible_units or not series_keys:
        st.warning("Select at least one unit and one series to display.")
        return
    fig.update_layout(**_layout(chart.get("title", ""), chart.get("y_label", "")), barmode="group")
    st.plotly_chart(fig, use_container_width=True)


def render_simple_bar(
    chart: dict,
    visible_units: list[str],
) -> None:
    units = chart["units"]
    x_vals, y_vals, colors, text = [], [], [], []
    for unit_id in visible_units:
        if unit_id not in units:
            continue
        u = units[unit_id]
        val = u["value"]
        if val is None:
            continue
        x_vals.append(u.get("label", unit_id))
        y_vals.append(val)
        colors.append(u.get("color", TEAL))
        text.append(_format_value(val, chart.get("y_format", "number")))
    if not x_vals:
        st.warning("Select at least one unit to display.")
        return
    fig = go.Figure(go.Bar(x=x_vals, y=y_vals, marker_color=colors, text=text, textposition="outside"))
    fig.update_layout(**_layout(chart.get("title", ""), chart.get("y_label", "")))
    st.plotly_chart(fig, use_container_width=True)


def render_stacked_bar(
    chart: dict,
    visible_units: list[str],
    visible_series: list[str],
) -> None:
    units = chart["units"]
    fig = go.Figure()
    colors = chart.get("series_colors", [TEAL, MINT, CORAL])
    for i, series_key in enumerate(visible_series):
        x_vals, y_vals = [], []
        for unit_id in visible_units:
            if unit_id not in units:
                continue
            u = units[unit_id]
            if series_key not in u.get("series", {}):
                continue
            x_vals.append(u.get("label", unit_id))
            y_vals.append(u["series"][series_key])
        if x_vals:
            fig.add_bar(
                name=chart["series_labels"].get(series_key, series_key),
                x=x_vals,
                y=y_vals,
                marker_color=colors[i % len(colors)],
            )
    if not visible_units:
        st.warning("Select at least one unit to display.")
        return
    fig.update_layout(**_layout(chart.get("title", ""), chart.get("y_label", "")), barmode="stack")
    st.plotly_chart(fig, use_container_width=True)


def render_calibration(
    chart: dict,
    visible_series: list[str],
) -> None:
    fig = go.Figure()
    if "observed" in visible_series:
        fig.add_trace(
            go.Scatter(
                x=chart["predicted"],
                y=chart["observed"],
                mode="lines+markers",
                name="Observed",
                line=dict(color=TEAL, width=2),
            )
        )
    if "perfect" in visible_series:
        max_val = max(max(chart["predicted"]), max(chart["observed"])) * 1.1
        fig.add_trace(
            go.Scatter(
                x=[0, max_val],
                y=[0, max_val],
                mode="lines",
                name="Perfect calibration",
                line=dict(dash="dash", color="#64747a"),
            )
        )
    fig.update_layout(**_layout(chart.get("title", ""), "Observed exit rate"))
    fig.update_xaxes(title="Predicted risk")
    st.plotly_chart(fig, use_container_width=True)


def render_decile_bars(
    chart: dict,
    visible_series: list[str],
) -> None:
    deciles = chart["deciles"]
    fig = go.Figure()
    if "observed" in visible_series:
        fig.add_bar(name="Observed", x=deciles, y=chart["observed"], marker_color=TEAL)
    if "predicted" in visible_series:
        fig.add_bar(name="Predicted", x=deciles, y=chart["predicted"], marker_color=MINT)
    fig.update_layout(**_layout(chart.get("title", ""), "Exit rate"), barmode="group")
    fig.update_xaxes(title="Risk decile")
    st.plotly_chart(fig, use_container_width=True)
