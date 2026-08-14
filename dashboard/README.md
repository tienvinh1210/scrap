# NovaCorp People Assurance Dashboard

Streamlit dashboard for the NovaCorp presentation. **Every section is a chart.** Use sidebar **checkboxes** to show or hide units (entities, departments, rate types, scenarios).

## Prerequisites

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dashboard.txt
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

## Example

On **Attrition by Entity**, uncheck **Entity A** to hide that line from the event-time chart—same pattern as toggling series in a presentation deck.

## Guardrails

Aggregate-only · no individual risk scores · do not sum scenario dollars.
