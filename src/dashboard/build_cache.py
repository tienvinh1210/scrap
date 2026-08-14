"""Build chart catalog JSON for checkbox-driven Streamlit dashboard."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUTS = REPO_ROOT / "outputs"
CACHE_DIR = OUTPUTS / "dashboard"

ENTITIES = ["Entity_A", "Entity_B", "Entity_C", "NovaCorp-Origin"]
ENTITY_LABELS = {
    "Entity_A": "Entity A (integrated FY2022)",
    "Entity_B": "Entity B (FY2023 — stabilisation)",
    "Entity_C": "Entity C (late FY2024)",
    "NovaCorp-Origin": "NovaCorp-Origin",
}
ENTITY_COLORS = {
    "Entity_A": "#0d817b",
    "Entity_B": "#e66a50",
    "Entity_C": "#e7a743",
    "NovaCorp-Origin": "#0d2630",
}

DEPARTMENTS = [
    "Retail Banking",
    "Technology",
    "Risk & Compliance",
    "Insurance",
    "Wealth Management",
    "Corporate Operations",
    "Executive Leadership",
]

ENGAGEMENT_DIMENSIONS = [
    "manager_effectiveness",
    "psychological_safety",
    "recognition",
    "career_development",
    "senior_leadership_trust",
    "purpose_meaning",
    "wellbeing",
    "confidence_in_role_future",
]

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

PILOTS = {
    "agency_sourcing": {"label": "Agency sourcing rebalance", "pool": 2_282_587.0},
    "disengagement_support": {"label": "Disengagement team support", "pool": 12_241_740.0},
    "acquisition_governance": {"label": "Acquisition governance", "pool": 2_399_550.0},
}

SCENARIOS = {"10": 0.10, "25": 0.25, "50": 0.50}


def _read_csv(path: str) -> pd.DataFrame:
    full = OUTPUTS / path
    if not full.exists():
        raise FileNotFoundError(f"Missing: {full}")
    return pd.read_csv(full)


def _event_time_units(df: pd.DataFrame, exit_type: str) -> dict:
    rate_col = (
        "voluntary_rate_per_100_employee_years"
        if exit_type == "voluntary"
        else "involuntary_rate_per_100_employee_years"
    )
    units = {}
    for entity in ENTITIES:
        sub = df[df["legacy_entity_code"] == entity]
        units[entity] = {
            "label": ENTITY_LABELS[entity],
            "color": ENTITY_COLORS[entity],
            "x": sub["months_since_payroll_entry"].tolist(),
            "y": [None if pd.isna(v) else float(v) for v in sub[rate_col]],
        }
    return units


def add_solution_profit_charts(charts: dict, pages: list) -> None:
    """Presentation solution value charts (from analysis/04_financial_model.py)."""

    charts["solution_recommendation_value"] = {
        "title": "Annual value protected or saved by each recommendation",
        "type": "bar",
        "y_label": "Annual value ($)",
        "y_format": "money",
        "units": {
            "entity_b_program": {
                "label": "Entity B leadership reconnection",
                "value": 5_615_396,
                "color": "#e66a50",
            },
            "rc_director_program": {
                "label": "R&C Director+ retention track",
                "value": 2_591_749,
                "color": "#e7a743",
            },
            "disengagement_trigger": {
                "label": "Disengagement early-warning (bottom decile)",
                "value": 23_000_000,
                "color": "#7b5ea7",
            },
            "agency_redirect": {
                "label": "Agency-to-direct hiring redirect",
                "value": 2_282_587,
                "color": "#0d817b",
            },
        },
        "default_units": [
            "entity_b_program",
            "rc_director_program",
            "disengagement_trigger",
            "agency_redirect",
        ],
        "footnote": "Values from deck financial model. Populations overlap — do not sum to a single profit figure.",
    }

    charts["solution_42m_comparison"] = {
        "title": "$42M problem: Finance estimate vs data-derived (annual)",
        "type": "grouped_bar",
        "y_label": "Annual cost ($)",
        "y_format": "money",
        "series_keys": ["finance_estimate", "data_derived"],
        "series_labels": {
            "finance_estimate": "Finance midpoint",
            "data_derived": "Data-derived",
        },
        "series_colors": ["#64747a", "#0d817b"],
        "units": {
            "regrettable_attrition": {
                "label": "Regrettable attrition",
                "series": {"finance_estimate": 23_500_000, "data_derived": 14_258_723},
            },
            "disengagement_severe": {
                "label": "Disengagement (severe <2.5)",
                "series": {"finance_estimate": 13_500_000, "data_derived": 15_400_000},
            },
            "disengagement_sustained": {
                "label": "Disengagement (sustained <3.0)",
                "series": {"finance_estimate": 13_500_000, "data_derived": 59_293_114},
            },
            "hiring_inefficiency": {
                "label": "Hiring inefficiency",
                "series": {"finance_estimate": 5_000_000, "data_derived": 4_552_607},
            },
        },
        "default_units": [
            "regrettable_attrition",
            "disengagement_severe",
            "hiring_inefficiency",
        ],
        "footnote": "Disengagement severe band (~6% of staff) aligns with Finance $12–15M; sustained population is larger.",
    }

    charts["solution_hiring_profit_split"] = {
        "title": "Hiring inefficiency — where the $4.6M/yr comes from",
        "type": "bar",
        "y_label": "Annual cost ($)",
        "y_format": "money",
        "units": {
            "agency_excess_fees": {
                "label": "Excess agency fees vs direct benchmark",
                "value": 2_282_587,
                "color": "#0d817b",
            },
            "poor_match_early_exit": {
                "label": "Poor-match agency early-exit backfill",
                "value": 2_270_020,
                "color": "#e66a50",
            },
        },
        "default_units": ["agency_excess_fees", "poor_match_early_exit"],
        "footnote": "Agency fee savings alone (~$2.3M/yr) can fund other programme costs per deck.",
    }

    charts["solution_disengagement_dept"] = {
        "title": "Disengagement productivity exposure by department",
        "type": "bar",
        "y_label": "Annual exposure ($)",
        "y_format": "money",
        "units": {
            "Retail Banking": {"label": "Retail Banking", "value": 16_154_645, "color": "#0d817b"},
            "Risk & Compliance": {"label": "Risk & Compliance", "value": 12_184_586, "color": "#e66a50"},
            "Insurance": {"label": "Insurance", "value": 11_207_935, "color": "#e7a743"},
            "Corporate Operations": {"label": "Corporate Operations", "value": 10_758_468, "color": "#64747a"},
            "Technology": {"label": "Technology", "value": 5_072_239, "color": "#89e0d5"},
            "Wealth Management": {"label": "Wealth Management", "value": 3_105_497, "color": "#0d2630"},
            "Executive Leadership": {"label": "Executive Leadership", "value": 809_743, "color": "#64747a"},
        },
        "default_units": DEPARTMENTS.copy(),
        "footnote": "Finance 15% productivity assumption on persistently disengaged active staff — not empirically measured loss.",
    }

    charts["solution_total_addressable"] = {
        "title": "Total addressable value if recommendations succeed",
        "type": "grouped_bar",
        "y_label": "Annual value ($)",
        "y_format": "money",
        "series_keys": ["addressable_value"],
        "series_labels": {"addressable_value": "Annual value"},
        "series_colors": ["#0d817b"],
        "units": {
            "protected_replacement": {
                "label": "Protected replacement\n(Entity B + R&C)",
                "series": {"addressable_value": 8_207_145},
            },
            "disengagement_cohort": {
                "label": "Disengagement cohort\n(bottom decile)",
                "series": {"addressable_value": 23_000_000},
            },
            "hiring_savings": {
                "label": "Hiring fee savings",
                "series": {"addressable_value": 2_282_587},
            },
        },
        "default_units": ["protected_replacement", "disengagement_cohort", "hiring_savings"],
        "footnote": "Deck headline: ~$8.2M protected replacement + ~$23M disengagement exposure + ~$2.3M hiring savings. Not additive.",
    }

    pages[:] = [p for p in pages if p.get("id") != "solution_profit"]
    solution_page = {
        "id": "solution_profit",
        "title": "Solution Value & Profit",
        "charts": [
            "solution_recommendation_value",
            "solution_total_addressable",
            "solution_42m_comparison",
            "solution_hiring_profit_split",
            "solution_disengagement_dept",
        ],
        "series_checkbox_label": "Compare series",
        "has_series_checkboxes": True,
        "series_chart": "solution_42m_comparison",
    }
    insert_at = 1
    for i, page in enumerate(pages):
        if page.get("id") == "headline":
            insert_at = i + 1
            break
    pages.insert(insert_at, solution_page)


def build_chart_catalog() -> dict:
    event_time = _read_csv("pass5_acquisition_event_time.csv")
    headline = _read_csv("headline_reconciliation.csv")
    baseline = _read_csv("baseline_metrics.csv")
    wave_df = _read_csv("pass5_engagement_by_wave.csv")
    entity_diseng = _read_csv("disengagement_entity_department_audit/entity_rates.csv")
    hiring = _read_csv("pass6_hiring_efficiency.csv")
    calibration = _read_csv("pass3_calibration.csv")
    senior_rc = _read_csv("pass4_senior_regulatory_rates.csv")
    early_warning = _read_csv("pass5_entity_c_early_warning.csv")
    recommendations = _read_csv("pass8_recommendations.csv")

    l2_cal = calibration[calibration["model"] == "L2 engineered logistic"]

    # --- Chart definitions ---
    charts = {}

    charts["headline_attrition"] = {
        "title": "Published vs voluntary attrition rate",
        "type": "grouped_bar",
        "y_label": "Rate (%)",
        "y_format": "percent",
        "series_keys": ["published", "all_departures", "voluntary"],
        "series_labels": {
            "published": "Published label (annual report)",
            "all_departures": "All departures (actual)",
            "voluntary": "Voluntary only",
        },
        "series_colors": ["#64747a", "#e66a50", "#0d817b"],
        "units": {
            row["population"]: {
                "label": row["population"].replace("_", " "),
                "series": {
                    "published": float(row["published_rate"]),
                    "all_departures": float(row["reproduced_all_departure_rate"]),
                    "voluntary": float(row["actual_voluntary_rate_same_denominator"]),
                },
            }
            for _, row in headline.iterrows()
        },
        "default_units": ["Overall", "Entity_A", "Entity_B", "Entity_C"],
        "footnote": "Annual report labels 10.4% as voluntary; it reproduces as all departures.",
    }

    charts["event_time_voluntary"] = {
        "title": "Voluntary attrition by months since payroll entry",
        "type": "multi_line",
        "x_label": "Months since payroll entry",
        "y_label": "Voluntary exits per 100 employee-years",
        "units": _event_time_units(event_time, "voluntary"),
        "default_units": ENTITIES.copy(),
        "footnote": "Entity B persistent voluntary excess not established at months 9–14 (RR 1.31, CI includes 1).",
    }

    charts["event_time_involuntary"] = {
        "title": "Involuntary attrition by months since payroll entry",
        "type": "multi_line",
        "x_label": "Months since payroll entry",
        "y_label": "Involuntary exits per 100 employee-years",
        "units": _event_time_units(event_time, "involuntary"),
        "default_units": ENTITIES.copy(),
        "footnote": "B vs A involuntary RR 5.10 (1.93–13.47) at months 9–14; mechanism unresolved.",
    }

    dept_vol = baseline[baseline["segment_dimension"] == "department"]
    charts["department_voluntary_rate"] = {
        "title": "Voluntary attrition rate by department",
        "type": "bar",
        "y_label": "Voluntary exits per 100 employee-years",
        "y_format": "number",
        "units": {
            row["segment"]: {
                "label": row["segment"],
                "value": float(row["voluntary_departures_per_100_employee_years"]),
                "color": "#e66a50" if row["segment"] == "Risk & Compliance" else "#0d817b",
            }
            for _, row in dept_vol.iterrows()
        },
        "default_units": DEPARTMENTS.copy(),
        "footnote": "Risk & Compliance 11.8% in annual report; Technology and Corporate Ops also above average.",
    }

    charts["department_all_departures"] = {
        "title": "All-departure cumulative incidence by department",
        "type": "bar",
        "y_label": "All departures / roster",
        "y_format": "percent",
        "units": {
            row["segment"]: {
                "label": row["segment"],
                "value": float(row["all_departure_cumulative_incidence"]),
                "color": "#64747a",
            }
            for _, row in dept_vol.iterrows()
        },
        "default_units": DEPARTMENTS.copy(),
        "footnote": "Matches annual report denominator methodology (historical roster).",
    }

    for dim in ENGAGEMENT_DIMENSIONS:
        units = {}
        for entity in ENTITIES:
            sub = wave_df[wave_df["legacy_entity_code"] == entity].sort_values("wave_number")
            if sub.empty:
                continue
            units[entity] = {
                "label": ENTITY_LABELS[entity],
                "color": ENTITY_COLORS[entity],
                "x": sub["wave_number"].astype(int).tolist(),
                "y": sub[dim].astype(float).tolist(),
            }
        charts[f"engagement_{dim}"] = {
            "title": f"{DIMENSION_LABELS[dim]} by survey wave",
            "type": "multi_line",
            "x_label": "Survey wave",
            "y_label": "Mean score (1–5)",
            "units": units,
            "default_units": ["Entity_B", "Entity_C", "NovaCorp-Origin"],
            "footnote": "Entity B leadership-trust and purpose scores trail Origin from Wave 2 onward.",
        }

    response_units = {}
    for entity in ENTITIES:
        sub = wave_df[wave_df["legacy_entity_code"] == entity].sort_values("wave_number")
        if sub.empty:
            continue
        response_units[entity] = {
            "label": ENTITY_LABELS[entity],
            "color": ENTITY_COLORS[entity],
            "x": sub["wave_number"].astype(int).tolist(),
            "y": (sub["response_rate"] * 100).astype(float).tolist(),
        }
    charts["survey_response_rate"] = {
        "title": "Survey response rate by wave",
        "type": "multi_line",
        "x_label": "Survey wave",
        "y_label": "Response rate (%)",
        "units": response_units,
        "default_units": ["Entity_B", "NovaCorp-Origin", "Entity_A"],
        "footnote": "Entity B ~62–64% vs Origin ~84%; repair access—do not label as flight risk.",
    }

    charts["disengagement_by_entity"] = {
        "title": "Repeated-low engagement share by entity",
        "type": "bar",
        "y_label": "% of active employees flagged",
        "y_format": "percent",
        "units": {
            row["legacy_entity_code"]: {
                "label": ENTITY_LABELS.get(row["legacy_entity_code"], row["legacy_entity_code"]),
                "value": float(row["flagged_share_all_active"]),
                "color": ENTITY_COLORS.get(row["legacy_entity_code"], "#0d817b"),
            }
            for _, row in entity_diseng.iterrows()
            if row["legacy_entity_code"] in ENTITIES
        },
        "default_units": ENTITIES.copy(),
        "footnote": "613 active employees firm-wide; $12.24M is a Finance scenario—not measured loss.",
    }

    pilot_units = {}
    for slug, meta in PILOTS.items():
        pilot_units[slug] = {
            "label": meta["label"],
            "series": {pct: meta["pool"] * frac for pct, frac in SCENARIOS.items()},
        }
    charts["pilot_cost_scenarios"] = {
        "title": "Addressable cost scenarios by pilot (do not sum)",
        "type": "grouped_bar",
        "y_label": "Annual scenario ($)",
        "y_format": "money",
        "series_keys": list(SCENARIOS.keys()),
        "series_labels": {k: f"{k}% scenario" for k in SCENARIOS},
        "series_colors": ["#89e0d5", "#0d817b", "#e66a50"],
        "units": pilot_units,
        "default_units": list(PILOTS.keys()),
        "footnote": "Separate sensitivity scenarios—not forecasts. Populations overlap; do not add.",
    }

    charts["hire_source_volume"] = {
        "title": "New hires by source (2024–2025)",
        "type": "bar",
        "y_label": "Hires",
        "y_format": "number",
        "units": {
            row["hire_source"]: {
                "label": row["hire_source"].title(),
                "value": float(row["hires_2024_2025"]),
                "color": "#e66a50" if row["hire_source"] == "agency" else "#0d817b",
            }
            for _, row in hiring.iterrows()
        },
        "default_units": hiring["hire_source"].tolist(),
        "footnote": "274 agency hires; $2.28M/yr estimated premium vs direct-hire benchmark.",
    }

    charts["hire_source_days_to_fill"] = {
        "title": "Mean days to fill by hire source",
        "type": "bar",
        "y_label": "Days",
        "y_format": "number",
        "units": {
            row["hire_source"]: {
                "label": row["hire_source"].title(),
                "value": float(row["mean_days_to_fill"]),
                "color": "#64747a",
            }
            for _, row in hiring.iterrows()
        },
        "default_units": hiring["hire_source"].tolist(),
        "footnote": "Agency and direct channels show similar time-to-fill; fee premium is the clearest pool.",
    }

    charts["prediction_deciles"] = {
        "title": "L2 logistic — observed vs predicted exit rate by decile",
        "type": "decile_bar",
        "deciles": l2_cal["risk_decile"].astype(int).tolist(),
        "observed": l2_cal["observed_risk"].astype(float).tolist(),
        "predicted": l2_cal["mean_predicted_risk"].astype(float).tolist(),
        "series_keys": ["observed", "predicted"],
        "series_labels": {"observed": "Observed", "predicted": "Predicted"},
        "default_series": ["observed", "predicted"],
        "footnote": "Top-decile lift 3.04 (CI 2.31–3.82). Not approved for individual employment use.",
    }

    charts["prediction_calibration"] = {
        "title": "L2 logistic — calibration curve",
        "type": "calibration",
        "predicted": l2_cal["mean_predicted_risk"].astype(float).tolist(),
        "observed": l2_cal["observed_risk"].astype(float).tolist(),
        "series_keys": ["observed", "perfect"],
        "series_labels": {"observed": "Observed", "perfect": "Perfect calibration"},
        "default_series": ["observed", "perfect"],
        "footnote": "96.5% of top-decile employees did not exit; 69.6% of exits were missed.",
    }

    l4_rc = senior_rc[(senior_rc["seniority_definition"] == "L4+") & (senior_rc["senior_group"] == False)]
    charts["senior_rc_l4_voluntary"] = {
        "title": "Risk & Compliance — voluntary rate at L4+ by department",
        "type": "bar",
        "y_label": "Voluntary exits per 100 employee-years",
        "y_format": "number",
        "units": {
            row["department"]: {
                "label": row["department"],
                "value": float(row["voluntary_rate_per_100_employee_years"]),
                "color": "#e66a50" if row["department"] == "Risk & Compliance" else "#64747a",
            }
            for _, row in l4_rc.iterrows()
        },
        "default_units": DEPARTMENTS.copy(),
        "footnote": "R&C L4+ OR 3.45 based on 11 exits; pilot/watchlist only—not definitive hotspot.",
    }

    ec_indicators = early_warning[
        early_warning["indicator"].str.contains("Wave 5|180 days", regex=True)
    ]
    indicator_units = {}
    for _, row in ec_indicators.iterrows():
        key = row["indicator"][:40]
        vals = {}
        for col in ["Entity_A", "Entity_B", "Entity_C"]:
            v = row[col]
            vals[col] = None if pd.isna(v) else float(v)
        indicator_units[key] = {
            "label": row["indicator"],
            "series": vals,
            "classification": row["classification"],
        }
    charts["entity_c_early_warning"] = {
        "title": "Entity C vs A/B — early-warning indicators",
        "type": "grouped_bar",
        "y_label": "Indicator value",
        "y_format": "number",
        "series_keys": ["Entity_A", "Entity_B", "Entity_C"],
        "series_labels": {
            "Entity_A": "Entity A",
            "Entity_B": "Entity B",
            "Entity_C": "Entity C",
        },
        "series_colors": [ENTITY_COLORS["Entity_A"], ENTITY_COLORS["Entity_B"], ENTITY_COLORS["Entity_C"]],
        "units": indicator_units,
        "default_units": list(indicator_units.keys()),
        "footnote": "Entity C overall classification unresolved; monitor indicators only.",
    }

    charts["pilot_headcount"] = {
        "title": "Three pilot target populations",
        "type": "bar",
        "y_label": "Headcount",
        "y_format": "number",
        "units": {
            f"pilot_{int(row['priority'])}": {
                "label": row["candidate"][:45],
                "value": float(row["target_headcount"]),
                "color": ["#0d817b", "#e66a50", "#e7a743"][int(row["priority"]) - 1],
            }
            for _, row in recommendations.iterrows()
        },
        "default_units": ["pilot_1", "pilot_2", "pilot_3"],
        "footnote": "Three bounded pilots from Pass 8 synthesis.",
    }

    charts["entity_overview_rates"] = {
        "title": "Entity attrition rates (2024–2025)",
        "type": "grouped_bar",
        "y_label": "Rate (%)",
        "y_format": "percent",
        "series_keys": ["all_departures", "voluntary", "involuntary"],
        "series_labels": {
            "all_departures": "All departures",
            "voluntary": "Voluntary",
            "involuntary": "Involuntary",
        },
        "series_colors": ["#64747a", "#0d817b", "#e66a50"],
        "units": {
            row["segment"]: {
                "label": ENTITY_LABELS.get(row["segment"], row["segment"]),
                "series": {
                    "all_departures": float(row["all_departure_cumulative_incidence"]),
                    "voluntary": float(row["voluntary_cumulative_incidence"]),
                    "involuntary": float(row["involuntary_cumulative_incidence"]),
                },
            }
            for _, row in baseline[baseline["segment_dimension"] == "legacy_entity_code"].iterrows()
        },
        "default_units": ENTITIES.copy(),
        "footnote": "Entity B 15.0% in annual report = all departures; voluntary = 11.9%.",
    }

    pages = [
        {
            "id": "headline",
            "title": "Headline Correction",
            "charts": ["headline_attrition"],
            "series_checkbox_label": "Rate types",
            "has_series_checkboxes": True,
        },
        {
            "id": "entity_attrition",
            "title": "Attrition by Entity",
            "charts": ["entity_overview_rates", "event_time_voluntary", "event_time_involuntary"],
            "series_checkbox_label": "Exit types (overview chart)",
            "has_series_checkboxes": True,
            "overview_chart": "entity_overview_rates",
        },
        {
            "id": "department_attrition",
            "title": "Attrition by Department",
            "charts": ["department_voluntary_rate", "department_all_departures"],
        },
        {
            "id": "engagement",
            "title": "Engagement Wave Scores",
            "charts": [f"engagement_{d}" for d in ENGAGEMENT_DIMENSIONS],
            "dimension_picker": True,
        },
        {
            "id": "survey_access",
            "title": "Survey Response Rate",
            "charts": ["survey_response_rate"],
        },
        {
            "id": "disengagement",
            "title": "Disengagement Flags",
            "charts": ["disengagement_by_entity"],
        },
        {
            "id": "cost_pilots",
            "title": "Cost Pool Scenarios",
            "charts": ["pilot_cost_scenarios", "pilot_headcount"],
            "series_checkbox_label": "Scenario %",
            "has_series_checkboxes": True,
            "series_chart": "pilot_cost_scenarios",
        },
        {
            "id": "hiring",
            "title": "Hiring Efficiency",
            "charts": ["hire_source_volume", "hire_source_days_to_fill"],
        },
        {
            "id": "prediction",
            "title": "Prediction (aggregate only)",
            "charts": ["prediction_deciles", "prediction_calibration"],
            "series_checkbox_label": "Series",
            "has_series_checkboxes": True,
        },
        {
            "id": "senior_rc",
            "title": "Senior R&C Hotspot",
            "charts": ["senior_rc_l4_voluntary"],
        },
        {
            "id": "entity_c",
            "title": "Entity C Early Warning",
            "charts": ["entity_c_early_warning"],
            "series_checkbox_label": "Compare entities",
            "has_series_checkboxes": True,
            "series_chart": "entity_c_early_warning",
        },
    ]

    add_solution_profit_charts(charts, pages)

    return {
        "meta": {
            "version": "2.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "observation_window": ["2024-01-01", "2025-12-31"],
            "chart_count": len(charts),
            "guardrails": ["aggregate_only", "no_individual_scores", "do_not_sum_scenarios"],
        },
        "charts": charts,
        "pages": pages,
    }


def _enumerate_checkbox_states(catalog: dict) -> dict:
    """Precompute every checkbox combination per page for JSON archival."""

    import itertools

    states: dict[str, dict] = {}
    for page in catalog["pages"]:
        page_id = page["id"]
        for chart_id in page["charts"]:
            chart = catalog["charts"][chart_id]
            unit_ids = list(chart.get("units", {}).keys())
            if not unit_ids:
                continue
            for r in range(1, len(unit_ids) + 1):
                for combo in itertools.combinations(unit_ids, r):
                    key = f"{page_id}|{chart_id}|units={','.join(sorted(combo))}"
                    states[key] = {
                        "page": page_id,
                        "chart_id": chart_id,
                        "visible_units": list(combo),
                    }
    return states


def write_catalog(catalog: dict) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    catalog_path = CACHE_DIR / "dashboard_states.json"
    checkbox_states = _enumerate_checkbox_states(catalog)
    catalog["checkbox_states"] = checkbox_states
    catalog["meta"]["checkbox_state_count"] = len(checkbox_states)

    with catalog_path.open("w", encoding="utf-8") as handle:
        json.dump(catalog, handle, indent=2)

    manifest = {
        "generated_at": catalog["meta"]["generated_at"],
        "chart_count": catalog["meta"]["chart_count"],
        "checkbox_state_count": catalog["meta"]["checkbox_state_count"],
        "pages": [p["title"] for p in catalog["pages"]],
    }
    with (CACHE_DIR / "state_manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)

    return catalog_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    if args.verify:
        path = CACHE_DIR / "dashboard_states.json"
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        assert "charts" in data and "pages" in data
        print(f"Verified {data['meta']['chart_count']} charts, {data['meta'].get('checkbox_state_count', 0)} checkbox states")
        return

    catalog_path = CACHE_DIR / "dashboard_states.json"
    try:
        catalog = build_chart_catalog()
    except FileNotFoundError as exc:
        print(f"Partial rebuild ({exc}); patching existing catalog.")
        if not catalog_path.exists():
            raise
        with catalog_path.open(encoding="utf-8") as handle:
            catalog = json.load(handle)
        add_solution_profit_charts(catalog["charts"], catalog["pages"])
        catalog["meta"]["chart_count"] = len(catalog["charts"])
        catalog["meta"]["generated_at"] = datetime.now(timezone.utc).isoformat()

    path = write_catalog(catalog)
    print(f"Wrote {catalog['meta']['chart_count']} charts to {path}")
    print(f"Checkbox states: {catalog['meta']['checkbox_state_count']}")


if __name__ == "__main__":
    main()
