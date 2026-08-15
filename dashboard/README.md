# NovaCorp dashboards

Two Streamlit apps, each with its own data pipeline. They share nothing but the
guardrail banner and can be run at the same time.

| App | Command | What it is |
|-----|---------|------------|
| Pitch dashboard | `streamlit run dashboard/app.py` | The deck companion — 12 chart pages behind a two-tier nav. Reads `outputs/dashboard/dashboard_states.json`. |
| Monitoring cockpit | `streamlit run dashboard/cockpit/nova_app.py` | One screen: wave timeline, live KPI tiles, department × entity heat matrix, attrition trend, cost buckets, flagged cohorts. Reads `outputs/monitor/monitor_mart.json`. |

## Monitoring cockpit

Built from the source CSVs rather than pre-baked chart data, so it can be rebuilt
from a fresh clone:

```bash
python -m src.monitor.build_mart --verify   # writes outputs/monitor/monitor_mart.json
streamlit run dashboard/cockpit/nova_app.py
```

`--verify` asserts the company-wide cost buckets still reconcile with
`analysis/04_financial_model.py`'s published totals, so a definition can't drift
without the build failing.

**Scenarios.** The header toggle switches the whole screen between the observed
data (waves 1–5) and the two simulated futures in `scenarios/` (waves 6–8, through
Jul 2026). Those rows are a simulation for exercising the monitoring loop, not a
forecast — the app says so in a banner whenever a scenario is active.

**Guardrails.** Aggregate-only, no individual risk scores; cohorts under 30 people
are withheld from the flagged table and the count of withheld cohorts is disclosed.

**Theme.** `dashboard/cockpit/.streamlit/config.toml`. Streamlit resolves config from
the directory of the main script, so this styles the cockpit only and leaves the pitch
dashboard on its defaults — that is why the cockpit lives in its own folder.

---

## Pitch dashboard

**Every section is a chart.** Use sidebar **checkboxes** to show or hide units (entities, departments, rate types, scenarios).

## Prerequisites

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Build chart catalog

```bash
python3 -m src.dashboard.build_cache
python3 -m src.dashboard.build_cache --verify
```

Writes `outputs/dashboard/dashboard_states.json` with:
- **24 charts** (series data for all units)
- **874 precomputed checkbox combinations** (archived in JSON)

## Run

```bash
source .venv/bin/activate
streamlit run dashboard/app.py
```

## Deploy on Streamlit Community Cloud

1. Commit and push **`requirements.txt`** (repo root), **`dashboard/`**, and **`outputs/dashboard/dashboard_states.json`**.
2. Set **Main file path** to `dashboard/app.py`.
3. Streamlit Cloud installs from root **`requirements.txt`** only — it must include `plotly`.

If you see `ModuleNotFoundError: No module named 'plotly'`, add plotly to root `requirements.txt` and redeploy (Reboot app).

## Sections (all charts)

| Section | Charts | Checkbox units |
|---------|--------|----------------|
| Headline Correction | Published vs voluntary bars | Populations · rate types |
| Attrition by Entity | Overview rates + event-time lines | Entities · exit types |
| Attrition by Department | Voluntary rate · all-departure rate | Departments |
| Engagement Wave Scores | 8 dimensions (picker) | Entities |
| Survey Response Rate | Response by wave | Entities |
| Disengagement Flags | Repeated-low share | Entities |
| Cost Pool Scenarios | Scenario bars · pilot headcount | Pilots · scenario % |
| Hiring Efficiency | Hire volume · days to fill | Hire sources |
| Prediction | Decile lift · calibration | Observed / predicted series |
| Senior R&C Hotspot | L4+ voluntary by department | Departments |
| Entity C Early Warning | C vs A/B indicators | Indicators · entities |
| Solution Value & Profit | Recommendation value · $42M comparison · hiring split · dept exposure | Recommendations · cost buckets · departments |

## Example

On **Attrition by Entity**, uncheck **Entity A** to hide that line from the event-time chart—same pattern as toggling series in a presentation deck.

## Guardrails

Aggregate-only · no individual risk scores · do not sum scenario dollars.
