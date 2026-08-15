"""NovaCorp monitoring cockpit — one screen, live aggregates, two simulated futures.

Run:  streamlit run dashboard/cockpit/nova_app.py
Data: outputs/monitor/monitor_mart.json  (python -m src.monitor.build_mart)

Layout follows nova_dashboard_mockup_1786762464223.jpg: dark header band with the
wave stepper and scenario toggle, a row of three filters, four KPI cards, then the
heat matrix / attrition trend over cost buckets / flagged cohorts.

Theme lives in .streamlit/config.toml next to this file, which is why it can be
styled without affecting dashboard/app.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dashboard.components.guardrails import render_guardrail_banner  # noqa: E402
from dashboard.cockpit import mart, panels, theme  # noqa: E402

st.set_page_config(
    page_title="NovaCorp · Monitoring",
    page_icon=":material/monitoring:",
    layout="wide",
    initial_sidebar_state="collapsed",
)
theme.inject()

version = mart.mart_version()
try:
    catalog = mart.load_mart(str(mart.MART_PATH), version)
except FileNotFoundError as exc:
    st.error(str(exc))
    st.code("python -m src.monitor.build_mart --verify")
    st.stop()

DATASETS = catalog["datasets"]
SCENARIO_ORDER = ["observed", "scenario_a", "scenario_b"]
SCENARIO_LABELS = {
    "observed": "Observed",
    "scenario_a": "Future Scenario A",
    "scenario_b": "Future Scenario B",
}

# ---------------------------------------------------------- header band -----
with st.container(key="nc-header"):
    head = st.columns([2.6, 6.2, 3.4], vertical_alignment="center")

    head[0].html(f"<div class='nc-mark'>{theme.LOGO}<span>NovaCorp</span></div>")

    head[2].html("<div class='nc-toggle-label'>Select the scenario to toggle between:</div>")
    scenario = head[2].segmented_control(
        "Future scenario",
        SCENARIO_ORDER,
        default="observed",
        format_func=lambda key: SCENARIO_LABELS[key],
        key="scenario",
        label_visibility="collapsed",
    ) or "observed"

    frames = mart.dataset_frames(str(mart.MART_PATH), version, scenario)
    block = DATASETS[scenario]
    waves = frames["waves"]
    wave_numbers = waves["wave_number"].tolist()
    first_simulated = next((w["wave_number"] for w in block["waves"] if w["simulated"]), None)

    # Wave options change with the scenario; drop a stale selection rather than crash.
    if st.session_state.get("wave_choice") not in [mart.ALL, *wave_numbers, None]:
        st.session_state["wave_choice"] = mart.ALL

    active_wave = st.session_state.get("wave_choice")
    active_wave = None if active_wave in (None, mart.ALL) else int(active_wave)

    event = head[1].plotly_chart(
        panels.wave_track(waves, active_wave, block["synthetic"], scenario == "scenario_b"),
        key="track",
        on_select="rerun",
        selection_mode="points",
        config={"displayModeBar": False},
    )

# Clicking a node on the stepper drives the same state as the Wave dropdown.
points = getattr(getattr(event, "selection", None), "points", []) if event else []
signature = tuple(p.get("point_index") for p in points)
if signature != st.session_state.get("_track_signature"):
    st.session_state["_track_signature"] = signature
    if points:
        clicked = points[0].get("customdata")
        clicked = clicked[0] if isinstance(clicked, list) else clicked
        if clicked is not None and clicked != active_wave:
            st.session_state["wave_choice"] = int(clicked)
            st.rerun()

with st.container(key="nc-body"):
    # ----------------------------------------------------------- filters ----
    entities = sorted(frames["engagement_cells"]["entity"].unique())
    departments = sorted(frames["engagement_cells"]["department"].unique())

    with st.container(key="nc-filters"):
        filters = st.columns(3, gap="medium")
        entity = filters[0].selectbox(
            "Entity",
            [mart.ALL, *entities],
            format_func=lambda v: "Entity" if v == mart.ALL else theme.entity_label(v),
            key="entity_choice",
            label_visibility="collapsed",
        )
        department = filters[1].selectbox(
            "Department",
            [mart.ALL, *departments],
            format_func=lambda v: "Department" if v == mart.ALL else v,
            key="department_choice",
            label_visibility="collapsed",
        )
        wave_choice = filters[2].selectbox(
            "Wave",
            [mart.ALL, *wave_numbers],
            format_func=lambda v: "Wave" if v == mart.ALL else f"Wave {v}",
            key="wave_choice",
            label_visibility="collapsed",
        )
    wave = None if wave_choice == mart.ALL else int(wave_choice)

    if block["synthetic"]:
        st.warning(
            f"**{block['label']}** — waves {first_simulated}+ are a **simulation**, not a "
            "forecast. They exist to exercise the monitoring loop; no 2026 figure here is "
            "evidence about NovaCorp. Waves 1–5 are the real observed history.",
            icon=":material/science:",
        )

    # -------------------------------------------------------------- KPIs ----
    kpi = mart.kpis(frames, entity, department, wave)
    low, high = kpi["addressable"]
    selection_rate, company_rate = kpi["response_selection"], kpi["response_company"]
    lead = kpi["lead_time_months"]

    st.html(
        theme.kpi_cards(
            [
                ("Total Cost", theme.money(kpi["total_cost"]), "annual exposure, all four buckets"),
                (
                    "Addressed",
                    f"{theme.money(low)}–{theme.money(high)}",
                    "25–50% of exposure reached — a sizing assumption, not a forecast",
                ),
                (
                    "Response Gap",
                    (
                        f"{selection_rate:.1%}/{company_rate:.1%}"
                        if selection_rate is not None and company_rate is not None
                        else "—"
                    ),
                    f"selection vs company at wave {kpi['response_wave']}",
                ),
                (
                    "Attrition Lead Time",
                    f"~{lead:.0f} months" if lead is not None else "—",
                    f"median first low survey to exit · n={kpi['lead_time_n']:,}",
                ),
            ]
        )
    )

    # ------------------------------------------------------------ panels ----
    st.html("<div style='height:10px'></div>")
    top = st.columns([1.06, 1], gap="small")

    with top[0].container(border=True):
        st.html(
            theme.heading(
                "Heat Matrix",
                "Engagement composite per department × entity across every wave. "
                "Teal is improving, salmon is falling.",
            )
        )
        rows = [department] if department != mart.ALL else departments
        cols = [entity] if entity != mart.ALL else entities
        st.plotly_chart(
            panels.heat_matrix(mart.matrix_cells(frames), rows, cols),
            width="stretch",
            theme=None,
            config={"displayModeBar": False},
        )

    with top[1].container(border=True):
        st.html(
            theme.heading(
                "Attrition trend",
                "Voluntary exits per wave period, annualised against person-months at risk.",
            )
        )
        st.plotly_chart(
            panels.attrition_trend(
                mart.attrition_series(frames, entity, department), first_simulated
            ),
            width="stretch",
            theme=None,
            config={"displayModeBar": False},
        )
        st.caption(
            f"{kpi['exits_voluntary']:,} voluntary exits in scope"
            + (f" · {kpi['voluntary_rate']:.1%} annualised" if kpi["voluntary_rate"] else "")
        )

    bottom = st.columns([1.06, 1], gap="small")

    with bottom[0].container(border=True):
        st.html(
            theme.heading(
                "Cost Buckets",
                "Annualised exposure on Finance's benchmarks: 1.5× replacement, 85% backfill, "
                "15% disengagement loss, 12% on-cost.",
            )
        )
        st.plotly_chart(
            panels.cost_bucket_chart(mart.cost_bucket_totals(frames, entity, department)),
            width="stretch",
            theme=None,
            config={"displayModeBar": False},
        )

    with bottom[1].container(border=True):
        st.html(
            theme.heading(
                "Flagged Cohorts",
                "Entity × department groups crossing a monitoring threshold, worst first.",
            )
        )
        panels.cohort_table(
            mart.filter_cells(frames["flagged_cohorts"], entity, department),
            block["cohort_context"],
        )

    # ------------------------------------------------------------ footer ----
    render_guardrail_banner()
    st.caption(
        f"{block['label']} · window {block['window_start']} to {block['window_end']} · "
        f"mart built {catalog['meta']['generated_at'][:10]}"
    )
