"""Design tokens and the markup Streamlit has no native element for.

Everything here is measured off ``nova_dashboard_mockup_1786762464223.jpg``: the
dark full-bleed header band, the four centred KPI cards, the panel titles, and the
striped cohort table. Colour, fonts and radius come from ``.streamlit/config.toml``
next to the app; this module covers the pieces the theme file cannot express.
"""

from __future__ import annotations

import streamlit as st

# Surfaces
HEADER = "#16202c"  # the dark band across the top
GROUND = "#f0f0f0"  # page grey
PANEL = "#ffffff"
BORDER = "#dadce0"
INK = "#202124"
MUTED = "#5f6368"
HEADER_TEXT = "#ffffff"
HEADER_MUTED = "#c3ccd6"

# Accents
BLUE = "#1a73e8"
TEAL = "#2ec4a6"  # heat matrix: improving
SALMON = "#f4756a"  # heat matrix: deteriorating
NEUTRAL = "#e3e7ea"  # heat matrix: not enough survey history
TRACK_GREY = "#8b98a5"  # stepper line beyond the selected wave

ENTITY_LABELS = {
    "Entity_A": "Entity A",
    "Entity_B": "Entity B",
    "Entity_C": "Entity C",
    "NovaCorp-Origin": "NovaCorp-Origin",
}

CSS = f"""
<style>
/* Full-bleed layout: the header band runs edge to edge like the mockup, so the
   main block loses its padding and the body container puts it back. */
[data-testid="stMainBlockContainer"] {{
    padding: 0 !important; max-width: 100% !important;
}}
.st-key-nc-header {{ background: {HEADER}; padding: 14px 26px 10px; }}
.st-key-nc-body {{ padding: 14px 22px 26px; }}

/* Masthead */
.nc-mark {{
    display: flex; align-items: center; gap: 12px;
    font-size: 31px; font-weight: 500; color: {HEADER_TEXT}; letter-spacing: -0.5px;
}}
.nc-mark svg {{ flex: none; }}
.nc-toggle-label {{ color: {HEADER_TEXT}; font-size: 15px; margin-bottom: 6px; }}

/* Segmented control styled as the scenario toggle inside the dark band */
.st-key-nc-header [data-testid="stSegmentedControl"] button {{
    background: rgba(255,255,255,0.08) !important; border-color: rgba(255,255,255,0.22) !important;
    color: {HEADER_TEXT} !important;
}}
.st-key-nc-header [data-testid="stSegmentedControl"] button[aria-checked="true"],
.st-key-nc-header [data-testid="stSegmentedControl"] button[aria-selected="true"] {{
    background: {BLUE} !important; border-color: {BLUE} !important; color: #ffffff !important;
}}

/* Filter row: three wide dropdowns, label hidden, large text */
.st-key-nc-filters [data-baseweb="select"] > div {{
    min-height: 46px; font-size: 19px; background: {PANEL} !important;
}}

/* KPI cards */
.nc-kpis {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }}
.nc-kpi {{
    background: {PANEL}; border: 1px solid {BORDER}; border-radius: 8px;
    padding: 16px 12px 20px; text-align: center;
    box-shadow: 0 1px 2px rgba(60,64,67,0.10);
}}
.nc-kpi-label {{ font-size: 21px; color: {INK}; font-weight: 400; }}
.nc-kpi-value {{ font-size: 42px; font-weight: 700; color: #111418; line-height: 1.15; margin-top: 2px; }}
.nc-kpi-note {{ font-size: 11px; color: {MUTED}; margin-top: 6px; }}

/* Panels */
.nc-panel-title {{ font-size: 20px; font-weight: 700; color: {INK}; margin: 0 0 2px; }}
.nc-panel-note {{ font-size: 11px; color: {MUTED}; margin: 0 0 6px; }}

/* Flagged cohorts — plain HTML so it never inherits the viewer's OS theme */
.nc-table-wrap {{ max-height: 300px; overflow-y: auto; }}
table.nc-table {{ width: 100%; border-collapse: collapse; font-size: 14px; color: {INK}; }}
table.nc-table th {{
    font-size: 15px; font-weight: 400; color: {INK}; text-align: left;
    padding: 6px 10px; background: {PANEL}; position: sticky; top: 0;
    border-bottom: 1px solid {BORDER};
}}
table.nc-table td {{ padding: 6px 10px; border-right: 1px solid #ececec; }}
table.nc-table td:last-child, table.nc-table th:last-child {{ border-right: none; }}
table.nc-table tbody tr:nth-child(even) {{ background: #f2f2f2; }}
table.nc-table td.num {{ text-align: right; }}
</style>
"""

LOGO = (
    "<svg width='34' height='34' viewBox='0 0 34 34' fill='none'>"
    "<path d='M4 29V5h6l14 18V5h6v24h-6L10 11v18H4z' fill='#1a73e8'/></svg>"
)


def inject() -> None:
    st.html(CSS)


def kpi_cards(cards: list[tuple[str, str, str]]) -> str:
    """The four-up KPI row: label above, large value below."""

    blocks = "".join(
        f"<div class='nc-kpi'><div class='nc-kpi-label'>{label}</div>"
        f"<div class='nc-kpi-value'>{value}</div>"
        f"<div class='nc-kpi-note'>{note}</div></div>"
        for label, value, note in cards
    )
    return f"<div class='nc-kpis'>{blocks}</div>"


def heading(title: str, note: str = "") -> str:
    note_html = f"<p class='nc-panel-note'>{note}</p>" if note else ""
    return f"<p class='nc-panel-title'>{title}</p>{note_html}"


def plot_layout(height: int, **kwargs) -> dict:
    """Chart chrome from the mockup: no frame, dotted gridlines, grey tick labels."""

    layout = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Roboto, sans-serif", color=INK, size=13),
        margin=dict(l=58, r=20, t=14, b=42),
        height=height,
        xaxis=dict(
            showgrid=False, showline=False, ticks="",
            tickfont=dict(size=14, color=MUTED),
            title_font=dict(size=14, color=MUTED),
        ),
        yaxis=dict(
            showgrid=True, gridcolor="#c9ced3", griddash="dot", zeroline=False,
            showline=False, ticks="",
            tickfont=dict(size=14, color=MUTED),
            title_font=dict(size=14, color=MUTED),
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0,
                    font=dict(size=12, color=MUTED)),
        hoverlabel=dict(bgcolor=HEADER, bordercolor=HEADER,
                        font=dict(family="Roboto, sans-serif", size=13, color="#ffffff")),
    )
    layout.update(kwargs)
    return layout


def money(value: float | None) -> str:
    if value is None:
        return "—"
    if abs(value) >= 1e6:
        return f"${value / 1e6:,.1f}M"
    if abs(value) >= 1e3:
        return f"${value / 1e3:,.0f}K"
    return f"${value:,.0f}"


def entity_label(entity: str) -> str:
    return ENTITY_LABELS.get(entity, entity)
