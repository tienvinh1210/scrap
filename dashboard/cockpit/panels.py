"""The cockpit's panels, drawn to match the mockup.

Each function takes already-filtered data and returns a figure. Chart chrome follows
``nova_dashboard_mockup_1786762464223.jpg``: dotted gridlines, no axis frames, grey
tick labels, solid saturated fills, and value labels sitting directly above bars.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from . import theme

FONT = "Roboto, sans-serif"

#: Bars take the mockup's colour run: the two largest blue, then teal, then salmon.
BAR_RUN = [theme.BLUE, theme.BLUE, theme.TEAL, theme.SALMON]


def _cell_fill(values: list[float]) -> str:
    """The mockup's heat cells are binary — improving or not."""

    if len(values) < 2:
        return theme.NEUTRAL
    return theme.TEAL if values[-1] >= values[0] else theme.SALMON


def wave_track(waves: pd.DataFrame, active: int | None, synthetic: bool, improving: bool) -> go.Figure:
    """The header timeline: blue through the selected wave, grey after, forking into
    the two futures at the end — the mockup's stepper.
    """

    fig = go.Figure()
    real = waves[~waves["simulated"]]
    sim = waves[waves["simulated"]]
    last_real = len(real) - 1

    selected_index = 0
    if active is not None and active in list(waves["wave_number"]):
        selected_index = list(waves["wave_number"]).index(active)
    selected_index = min(selected_index, last_real)

    # Progress line: blue up to the selected node, grey beyond it.
    fig.add_shape(
        type="line", x0=0, x1=max(selected_index, 0.001), y0=0, y1=0,
        line=dict(color=theme.BLUE, width=5),
    )
    fig.add_shape(
        type="line", x0=selected_index, x1=last_real, y0=0, y1=0,
        line=dict(color=theme.TRACK_GREY, width=3),
    )

    branch_y = 0.5 if improving else -0.5
    if len(sim):
        x_sim = list(range(len(real), len(waves)))
        fig.add_shape(
            type="line", x0=last_real, x1=x_sim[0], y0=0, y1=branch_y,
            line=dict(color=theme.TRACK_GREY, width=3),
        )
        fig.add_shape(
            type="line", x0=x_sim[0], x1=x_sim[-1], y0=branch_y, y1=branch_y,
            line=dict(color=theme.TRACK_GREY, width=3),
        )
        # The road not taken, drawn faint on the opposite side.
        fig.add_shape(
            type="line", x0=last_real, x1=last_real + 1.4, y0=0, y1=-branch_y,
            line=dict(color="#4a5766", width=2),
        )
    else:
        for direction in (0.5, -0.5):
            fig.add_shape(
                type="line", x0=last_real, x1=last_real + 1.6, y0=0, y1=direction,
                line=dict(color=theme.TRACK_GREY, width=3),
            )
            fig.add_trace(
                go.Scatter(
                    x=[last_real + 1.6], y=[direction], mode="markers",
                    marker=dict(size=13, color=theme.HEADER,
                                line=dict(color=theme.TRACK_GREY, width=3)),
                    hoverinfo="skip", showlegend=False,
                )
            )

    xs, ys, sizes, rings, fills, labels, custom = [], [], [], [], [], [], []
    for i, row in enumerate(waves.itertuples()):
        simulated = bool(row.simulated)
        is_active = active == row.wave_number
        xs.append(i)
        ys.append(branch_y if simulated else 0)
        sizes.append(21 if is_active else 13)
        rings.append(theme.BLUE if (is_active or i <= selected_index) else theme.TRACK_GREY)
        fills.append("#ffffff" if not simulated or is_active else theme.HEADER)
        labels.append(f"Wave {row.wave_number}")
        custom.append(row.wave_number)

    fig.add_trace(
        go.Scatter(
            x=xs, y=ys, mode="markers",
            marker=dict(size=sizes, color=fills, line=dict(color=rings, width=4)),
            customdata=custom, hovertemplate="Wave %{customdata}<extra>click to filter</extra>",
            showlegend=False,
        )
    )

    for x, y, label, sim_flag in zip(xs, ys, labels, waves["simulated"]):
        fig.add_annotation(
            x=x, y=y - 0.42, text=label, showarrow=False,
            font=dict(family=FONT, size=15,
                      color=theme.HEADER_MUTED if sim_flag else theme.HEADER_TEXT),
        )

    span = max(len(waves), len(real) + 2) + 0.4
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=8, r=8, t=14, b=4), height=104,
        xaxis=dict(visible=False, range=[-0.5, span], fixedrange=True),
        yaxis=dict(visible=False, range=[-1.15, 1.05], fixedrange=True),
        dragmode=False, showlegend=False,
        hoverlabel=dict(bgcolor="#ffffff", bordercolor=theme.BORDER,
                        font=dict(family=FONT, size=13, color=theme.INK)),
    )
    return fig


def heat_matrix(cells: pd.DataFrame, departments: list[str], entities: list[str]) -> go.Figure:
    """Solid colour blocks with a black sparkline in each, as in the mockup.

    Rows are departments, columns entities; each block traces that cohort's
    engagement composite across every wave.
    """

    rows, cols = len(departments), len(entities)
    fig = make_subplots(
        rows=rows, cols=cols, shared_xaxes=True, shared_yaxes=True,
        horizontal_spacing=0.006, vertical_spacing=0.012,
        column_titles=[theme.entity_label(e) for e in entities],
    )
    fig.update_annotations(font=dict(family=FONT, size=17, color=theme.INK))

    waves = sorted(cells["wave"].unique())
    y_low = max(cells["composite"].min() - 0.1, 1.0)
    y_high = min(cells["composite"].max() + 0.1, 5.0)

    for r, department in enumerate(departments, start=1):
        for c, entity in enumerate(entities, start=1):
            cell = cells[(cells["department"] == department) & (cells["entity"] == entity)]
            cell = cell.sort_values("wave")
            values = cell["composite"].tolist()
            index = (r - 1) * cols + c
            axis = "" if index == 1 else str(index)

            fig.add_shape(
                type="rect", xref=f"x{axis} domain", yref=f"y{axis} domain",
                x0=0, x1=1, y0=0, y1=1, fillcolor=_cell_fill(values),
                line_width=0, layer="below",
            )

            if not values:
                continue

            for part, dash in ((cell[cell["wave"] <= 5], "solid"), (cell[cell["wave"] >= 5], "dot")):
                if len(part) < 2:
                    continue
                fig.add_trace(
                    go.Scatter(
                        x=part["wave"], y=part["composite"], mode="lines",
                        line=dict(color="#111418", width=2.2, dash=dash),
                        hovertemplate=(
                            f"{theme.entity_label(entity)} · {department}<br>"
                            "Wave %{x}: %{y:.2f}<extra></extra>"
                        ),
                        showlegend=False,
                    ),
                    row=r, col=c,
                )
            if len(values) == 1:
                fig.add_trace(
                    go.Scatter(
                        x=[cell["wave"].iloc[0]], y=values, mode="markers",
                        marker=dict(size=6, color="#111418"), showlegend=False,
                        hovertemplate=f"{department}: %{{y:.2f}}<extra></extra>",
                    ),
                    row=r, col=c,
                )

    fig.update_xaxes(visible=False, range=[min(waves) - 0.2, max(waves) + 0.2])
    fig.update_yaxes(visible=False, range=[y_low, y_high])

    for r, department in enumerate(departments, start=1):
        axis_key = "yaxis" if (r - 1) * cols + 1 == 1 else f"yaxis{(r - 1) * cols + 1}"
        domain = fig.layout[axis_key].domain
        fig.add_annotation(
            xref="paper", yref="paper", x=-0.012, y=(domain[0] + domain[1]) / 2,
            text=department, showarrow=False, xanchor="right",
            font=dict(family=FONT, size=16, color=theme.INK),
        )

    fig.add_annotation(
        xref="paper", yref="paper", x=-0.175, y=0.5, text="Department vs Entity",
        showarrow=False, textangle=-90,
        font=dict(family=FONT, size=13, color=theme.INK),
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=210, r=8, t=30, b=8), height=44 + 48 * rows,
        font=dict(family=FONT, color=theme.INK, size=13), showlegend=False,
        hoverlabel=dict(bgcolor="#ffffff", bordercolor=theme.BORDER,
                        font=dict(family=FONT, size=13, color=theme.INK)),
    )
    return fig


def attrition_trend(series: pd.DataFrame, first_simulated: int | None) -> go.Figure:
    """A single blue line over dotted gridlines, as in the mockup."""

    fig = go.Figure()
    if series.empty:
        return fig.update_layout(**theme.plot_layout(300))

    frame = series.assign(pct=series["voluntary_rate"] * 100)
    boundary = first_simulated if first_simulated else frame["wave"].max() + 1
    real = frame[frame["wave"] <= boundary - 1]
    simulated = frame[frame["wave"] >= boundary - 1]

    fig.add_trace(
        go.Scatter(
            x=real["wave"], y=real["pct"], mode="lines", name="Observed",
            line=dict(color=theme.BLUE, width=3),
            hovertemplate="Wave %{x}: %{y:.2f}%<extra></extra>",
        )
    )
    if len(simulated) > 1:
        fig.add_trace(
            go.Scatter(
                x=simulated["wave"], y=simulated["pct"], mode="lines", name="Simulated",
                line=dict(color=theme.SALMON, width=3, dash="dot"),
                hovertemplate="Wave %{x}: %{y:.2f}% simulated<extra></extra>",
            )
        )

    fig.update_layout(**theme.plot_layout(300))
    fig.update_xaxes(
        tickmode="array", tickvals=frame["wave"], ticktext=[f"Wave {w}" for w in frame["wave"]]
    )
    fig.update_yaxes(rangemode="tozero", ticksuffix="%")
    return fig


def cost_bucket_chart(totals: pd.DataFrame) -> go.Figure:
    """Vertical bars, largest first, with the amount printed above each — the mockup's
    Cost Buckets panel."""

    ordered = totals.sort_values("amount", ascending=False).reset_index(drop=True)
    fig = go.Figure(
        go.Bar(
            x=ordered["label"], y=ordered["amount"],
            marker_color=[BAR_RUN[i % len(BAR_RUN)] for i in range(len(ordered))],
            width=0.55,
            text=[theme.money(v) for v in ordered["amount"]],
            textposition="outside",
            textfont=dict(family=FONT, size=15, color=theme.INK),
            hovertemplate="%{x}<br>%{text} per year<extra></extra>",
        )
    )
    fig.update_layout(**theme.plot_layout(300, margin=dict(l=64, r=20, t=26, b=64)))
    fig.update_yaxes(tickprefix="$", rangemode="tozero")
    fig.update_xaxes(title="Cost bucket", tickfont=dict(size=13, color=theme.MUTED))
    return fig


def cohort_table(flagged: pd.DataFrame, context: dict) -> None:
    """The flagged-cohort table: striped rows, column rules, scrolls in place.

    Plain HTML rather than st.dataframe so it renders identically whatever theme the
    viewer's browser is in.
    """

    if flagged.empty:
        st.info("No cohort crosses a monitoring threshold in this selection.")
        return

    def pct(value) -> str:
        return "—" if pd.isna(value) else f"{value * 100:.1f}%"

    def signed(value) -> str:
        if pd.isna(value):
            return "—"
        color = theme.TEAL if value > 0 else theme.SALMON
        return f"<span style='color:{color}'>{value:+.2f}</span>"

    rows = "".join(
        "<tr>"
        f"<td>{theme.entity_label(row.entity)} · {row.department}</td>"
        f"<td class='num'>{int(row.headcount):,}</td>"
        f"<td class='num'>{pct(row.disengaged_share)}</td>"
        f"<td class='num'>{signed(row.trend)}</td>"
        f"<td class='num'>{pct(row.voluntary_rate)}</td>"
        f"<td class='num'>{theme.money(row.exposure)}</td>"
        f"<td>{row.driver}</td>"
        "</tr>"
        for row in flagged.itertuples()
    )

    st.html(
        "<div class='nc-table-wrap'><table class='nc-table'><thead><tr>"
        "<th>Cohort</th><th class='num'>People</th><th class='num'>Disengaged</th>"
        "<th class='num'>Trend</th><th class='num'>Voluntary</th>"
        "<th class='num'>Exposure</th><th>Flagged for</th>"
        f"</tr></thead><tbody>{rows}</tbody></table></div>"
    )

    suppressed = context.get("suppressed", 0)
    if suppressed:
        st.caption(
            f"{suppressed} cohort under {context['min_cohort_n']} people withheld — "
            "aggregate-only reporting."
        )
