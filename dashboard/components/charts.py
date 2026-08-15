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
        # Tick/legend colors are set explicitly: Streamlit's own chart template otherwise
        # overrides layout.font and renders them near-invisible on the light canvas.
        xaxis=dict(
            showgrid=False,
            title="",
            tickfont=dict(color=NAVY),
            title_font=dict(color=NAVY),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#e5e9e7",
            title=y_title,
            tickfont=dict(color=NAVY),
            title_font=dict(color=NAVY),
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(color=NAVY)),
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
    st.plotly_chart(fig, width="stretch", theme=None)


def _plot_value(val: float, fmt: str) -> float:
    if fmt == "percent":
        return val * 100
    return val


def render_grouped_bar(
    chart: dict,
    visible_units: list[str],
    visible_series: list[str] | None = None,
) -> None:
    units = chart["units"]
    series_keys = visible_series or chart.get("series_keys", [])
    fig = go.Figure()
    colors = chart.get("series_colors", [TEAL, MINT, CORAL, AMBER])
    y_format = chart.get("y_format", "number")
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
            y_vals.append(_plot_value(val, y_format))
            text.append(_format_value(val, y_format))
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
    st.plotly_chart(fig, width="stretch", theme=None)


def render_overlay_bar(
    chart: dict,
    visible_units: list[str],
    visible_series: list[str] | None = None,
) -> None:
    """Bars for the actual series with the published label traced on top as a dashed rule.

    The finding is that two of the series sit at the same height, so the published
    figure is drawn as an outline over its counterpart bar instead of beside it.
    """

    units = chart["units"]
    all_keys = chart.get("series_keys", [])
    series_keys = all_keys if visible_series is None else [k for k in all_keys if k in visible_series]
    labels = chart.get("series_labels", {})
    y_format = chart.get("y_format", "number")
    palette = chart.get("series_colors", [TEAL, MINT, CORAL, AMBER])
    colors = {key: palette[i % len(palette)] for i, key in enumerate(all_keys)}

    overlay_key = chart.get("overlay_series", "published")
    anchor_key = chart.get("overlay_anchor", "all_departures")

    unit_ids = [u for u in visible_units if u in units]
    if not unit_ids or not series_keys:
        st.warning("Select at least one unit and one rate type to display.")
        return

    bar_keys = [k for k in series_keys if k != overlay_key]
    positions = list(range(len(unit_ids)))
    tick_text = [units[u].get("label", u) for u in unit_ids]

    fig = go.Figure()

    slot = 0.72
    bar_width = slot / len(bar_keys) if bar_keys else slot
    offsets = {
        key: (i - (len(bar_keys) - 1) / 2) * bar_width
        for i, key in enumerate(bar_keys)
    }

    for key in bar_keys:
        x_vals, y_vals, text = [], [], []
        for pos, unit_id in zip(positions, unit_ids):
            val = units[unit_id].get("series", {}).get(key)
            if val is None:
                continue
            x_vals.append(pos + offsets[key])
            y_vals.append(_plot_value(val, y_format))
            text.append(_format_value(val, y_format))
        if not x_vals:
            continue
        fig.add_bar(
            name=labels.get(key, key),
            x=x_vals,
            y=y_vals,
            width=bar_width * 0.9,
            text=text,
            textposition="outside",
            marker_color=colors.get(key, TEAL),
            hovertemplate="%{text}<extra>" + labels.get(key, key) + "</extra>",
        )

    if overlay_key in series_keys:
        # One trace with None separators so the dashed rules share a single legend entry.
        line_x: list[float | None] = []
        line_y: list[float | None] = []
        anchor_offset = offsets.get(anchor_key, 0.0)
        half = (bar_width * 0.9) / 2 * 1.18
        hover_text: list[str | None] = []
        for pos, unit_id in zip(positions, unit_ids):
            val = units[unit_id].get("series", {}).get(overlay_key)
            if val is None:
                continue
            y = _plot_value(val, y_format)
            centre = pos + anchor_offset
            line_x += [centre - half, centre + half, None]
            line_y += [y, y, None]
            hover_text += [_format_value(val, y_format)] * 2 + [None]
        if line_x:
            fig.add_trace(
                go.Scatter(
                    x=line_x,
                    y=line_y,
                    mode="lines",
                    name=labels.get(overlay_key, overlay_key),
                    line=dict(color=colors.get(overlay_key, NAVY), width=3, dash="dash"),
                    text=hover_text,
                    hovertemplate="%{text}<extra>"
                    + labels.get(overlay_key, overlay_key)
                    + "</extra>",
                    connectgaps=False,
                )
            )

    # Title is rendered above the chart as the callout, so the plot keeps only the legend.
    fig.update_layout(**_layout("", chart.get("y_label", "")), barmode="overlay")
    fig.update_xaxes(
        tickmode="array",
        tickvals=positions,
        ticktext=tick_text,
        range=[-0.6, len(unit_ids) - 0.4],
    )
    fig.update_yaxes(rangemode="tozero")
    st.plotly_chart(fig, width="stretch", theme=None)


def render_simple_bar(
    chart: dict,
    visible_units: list[str],
) -> None:
    units = chart["units"]
    x_vals, y_vals, colors, text = [], [], [], []
    y_format = chart.get("y_format", "number")
    for unit_id in visible_units:
        if unit_id not in units:
            continue
        u = units[unit_id]
        val = u["value"]
        if val is None:
            continue
        x_vals.append(u.get("label", unit_id))
        y_vals.append(_plot_value(val, y_format))
        colors.append(u.get("color", TEAL))
        text.append(_format_value(val, y_format))
    if not x_vals:
        st.warning("Select at least one unit to display.")
        return
    fig = go.Figure(go.Bar(x=x_vals, y=y_vals, marker_color=colors, text=text, textposition="outside"))
    fig.update_layout(**_layout(chart.get("title", ""), chart.get("y_label", "")))
    st.plotly_chart(fig, width="stretch", theme=None)


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
    st.plotly_chart(fig, width="stretch", theme=None)


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
    st.plotly_chart(fig, width="stretch", theme=None)


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
    st.plotly_chart(fig, width="stretch", theme=None)
