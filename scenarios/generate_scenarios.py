"""Synthesise two forward-looking NovaCorp scenario datasets for the monitoring demo.

Extends the real observation window (ends 2025-12-31) forward to 2026-07-31 and
writes two complete, alternative futures in the *exact same schema* as the four
source CSVs, so every existing chart, risk-scoring function and notebook cell
renders against either one by changing a single directory path:

    scenarios/scenario_a_deteriorating/{employees,attrition_log,engagement,performance}.csv
    scenarios/scenario_b_improving/{employees,attrition_log,engagement,performance}.csv

Each output file contains the full history *plus* the extension — the original
rows are copied through byte-for-byte in value, and new rows are appended. The
real data in ``0_case/Accenture_Case_Comp_Data`` is opened read-only and is never
written to.

    THE GENERATED ROWS ARE SYNTHETIC AND ILLUSTRATIVE. They are a simulation
    built for a monitoring demo, not a forecast, and no number taken from a
    2026 row is evidence about NovaCorp. See SCENARIO_NOTES.md.

Every behavioural parameter is either measured from the source data at run time
(hazards, distributions, the engagement covariance structure) or set as a named
constant in the CONFIGURATION block below. There are no command-line arguments:
edit the constants in place and re-run.

Usage:  python generate_scenarios.py
"""
from __future__ import annotations

import pathlib
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

# =============================================================================
# CONFIGURATION — edit in place. No sys.argv, no CLI flags.
# =============================================================================

#: Fixed seed. Both scenarios are drawn from independent child streams of this
#: seed, so either can be regenerated without touching the other, and the whole
#: run is byte-reproducible.
RANDOM_SEED = 20260814

#: Output root, relative to this file. Never points at the source folder.
OUTPUT_ROOT = pathlib.Path(__file__).resolve().parent
SCENARIO_A_DIR = "scenario_a_deteriorating"
SCENARIO_B_DIR = "scenario_b_improving"

# ------------------------------------------------------------------- calendar
WINDOW_END_ORIGINAL = pd.Timestamp("2025-12-31")  # last day of the real data
WINDOW_END_EXTENDED = pd.Timestamp("2026-07-31")  # last day after extension

#: First month simulated. The real extract's final month (Dec 2025) is
#: right-censored — 4 exits against an expected ~55 — so the simulation starts
#: clean at the following month boundary rather than trying to complete it.
SIM_FIRST_MONTH = pd.Period("2026-01", freq="M")
SIM_LAST_MONTH = pd.Period("2026-07", freq="M")

#: New engagement waves on a ~60-day cadence. This is Recommendation 1's own
#: proposal to accelerate the survey cycle, so the simulated future is
#: consistent with the deck's recommended actions rather than arbitrary.
#: Three waves, not one, so the dashboard draws a trend rather than a jump.
#: Each wave is fielded over a 15-day window centred on the anchor, matching
#: waves 1/2/4/5 in the real data.
NEW_WAVES: tuple[tuple[int, str], ...] = (
    (6, "2026-03-01"),
    (7, "2026-05-01"),
    (8, "2026-07-01"),
)
WAVE_FIELD_HALF_WIDTH_DAYS = 7

#: One new review cycle, on the observed H1 cadence (2025-H1 ran 15 May – 29 Jun).
NEW_REVIEW_CYCLE = "2026-H1"
REVIEW_WINDOW = ("2026-05-15", "2026-06-29")

# ------------------------------------------------------------ base hazard fit
#: The baseline monthly departure hazard per entity is *measured* from this
#: window rather than hardcoded, using exposure-correct person-month
#: denominators. Jun–Nov 2025 is the most recent stretch in which all four
#: entities are simultaneously at risk and none of it is right-censored.
HAZARD_CALIBRATION_START = pd.Period("2025-06", freq="M")
HAZARD_CALIBRATION_END = pd.Period("2025-11", freq="M")

# ------------------------------------------------------ individual risk model
#: Relative departure risk multipliers, all measured from the source data and
#: reproduced by the simulation. Weights are normalised to mean 1 within each
#: entity-month, so they set *who* leaves; the entity hazard sets *how many*.

#: Non-response at the most recent wave. Measured: wave-4 non-responders exited
#: within the following 6 months at 5.64% vs 2.41% for responders (RR 2.34).
NONRESPONSE_RISK_MULTIPLIER = 2.34

#: Low organisation-sentiment (mean of senior_leadership_trust, purpose_meaning,
#: confidence_in_role_future) at the most recent responded wave, as a continuous
#: tilt exp(-BETA * z). Measured: bottom vs top quartile 3.01% vs 1.98%.
ORG_SENTIMENT_BETA = 0.22

#: Tenure-band multipliers for organically hired staff (replacement hires are
#: organic by construction). Measured on NovaCorp-Origin person-months; the
#: 0–3 month spike is the early-tenure hazard the analysis documented.
TENURE_BAND_MULTIPLIERS: tuple[tuple[int, int, float], ...] = (
    (0, 3, 2.54),
    (3, 6, 0.60),
    (6, 12, 1.08),
    (12, 10_000, 1.00),
)

#: Potential–performance divergence cohort (Evidence 5): hipo_flag AND goal
#: achievement at or below the 40th percentile *within role level*, measured on
#: the most recent review at least DIVERGENCE_LOOKBACK_DAYS before the month
#: being simulated. Measured departure share 17.5% vs 10.0% for non-HiPos.
DIVERGENCE_PERCENTILE_CUTOFF = 0.40
DIVERGENCE_LOOKBACK_DAYS = 180

# ------------------------------------------------------ engagement covariance
ENGAGEMENT_DIMENSIONS: tuple[str, ...] = (
    "manager_effectiveness",
    "psychological_safety",
    "recognition",
    "career_development",
    "senior_leadership_trust",
    "purpose_meaning",
    "wellbeing",
    "confidence_in_role_future",
)

#: The two dimensions the deck's Evidence 2/3 finding is about. Only these move
#: with the scenario; the other six stay at their wave-5 level, because the
#: finding is precisely that the depression is dimension-specific.
SCENARIO_DIMENSIONS: tuple[str, ...] = ("senior_leadership_trust", "purpose_meaning")

#: Dimensions making up the disengagement composite used in the risk model.
ORG_SENTIMENT_DIMENSIONS: tuple[str, ...] = (
    "senior_leadership_trust",
    "purpose_meaning",
    "confidence_in_role_future",
)

#: Variance decomposition of an individual theme score, solved from the observed
#: within-person lag correlations (.787 / .680 / .612 / .577 at lags 1–4):
#: a permanent person effect, an AR(1) mood component, and measurement noise.
SCORE_SD = 0.95
VAR_SHARE_PERMANENT = 0.538
VAR_SHARE_AR = 0.437
VAR_SHARE_NOISE = 0.025
AR_RHO = 0.57

#: Person-level response propensity spread (logit-free, applied additively to
#: the cohort target and clipped). Sized to reproduce the weak but non-zero
#: within-person response persistence in the real data (r ≈ .02–.05).
RESPONSE_PROPENSITY_SD = 0.07

#: Each cohort's realised theme mean is pinned to its configured target, then
#: nudged by N(0, this) so the trend line is not implausibly smooth at the
#: aggregate. Sized from the real between-wave wobble in the mature cohorts
#: (NovaCorp-Origin sd ≈ .004, Entity_A sd ≈ .017 across waves 1–5). Without
#: the pin, per-person sampling noise of ±.03 swamps a ±.08 scenario signal and
#: the "trend" comes out non-monotone.
COHORT_WOBBLE_SD = 0.010

#: Iterations of the pin. Clipping to [1, 5] pulls the mean down, so the shift
#: is reapplied until the post-clip mean sits on the target.
COHORT_PIN_ITERATIONS = 3

#: The same idea on the response-rate scale, which is a proportion rather than a
#: 1-5 score and therefore needs its own magnitude. Sized from the real
#: between-wave wobble (Entity_A sd ~0.8pp, NovaCorp-Origin sd ~0.5pp).
RESPONSE_WOBBLE_SD = 0.005

#: Departure counts are pinned per entity-month the same way, then given this
#: much multiplicative wobble. Left unpinned, Entity_C's ~12 expected exits a
#: month carry Poisson noise of +/-29%, which is larger than the whole scenario
#: effect and routinely inverts the trend by luck. This keeps month-to-month
#: texture while making the trajectory the configured one.
#: At 0.15 a two-sigma run of low draws flattened Entity_C's whole trajectory,
#: which is the failure this pin exists to prevent; 0.10 keeps the texture and
#: leaves the +45% scenario move dominant.
MONTHLY_HAZARD_WOBBLE_SD = 0.10

SCORE_MIN, SCORE_MAX = 1.0, 5.0

# ----------------------------------------------------------------- population
#: No net headcount growth: exactly one replacement hire per departure.
#: The gap is drawn from the source days_to_fill distribution, which is uniform
#: on [14, 90] days (mean 51.8, sd 22.3 — uniform(14,90) gives 52.0 / 22.0).
REPLACEMENT_GAP_DAYS = (14, 90)

#: Replacement hires are hired by NovaCorp directly, not acquired.
REPLACEMENT_ENTITY = "NovaCorp-Origin"
REPLACEMENT_SOURCE_SYSTEM = "WorkdayHR"

#: Non-acquisition hire sources, sampled at their observed relative frequencies.
#: 'graduate' is restricted to role_level 1.
REPLACEMENT_HIRE_SOURCES: tuple[str, ...] = ("agency", "direct", "referral", "graduate")

#: First serial number for new employee_ids. The source uses E00001–E14500 with
#: gaps; starting above the maximum guarantees no collision in either scenario.
#: Both scenarios start here, so an id means different people in A and B.
NEW_ID_START = 14_501

#: Employees this new or newer supply the base rates for a replacement hire's
#: hipo_flag / promotion_eligible / acting_appointment.
NEW_HIRE_REFERENCE_TENURE_MONTHS = 6

# ------------------------------------------------------------------ scenarios


@dataclass(frozen=True)
class Scenario:
    """Everything that distinguishes one simulated future from the other."""

    key: str
    label: str
    out_dir: str

    #: Target response rate per entity per new wave. Entities absent from a dict
    #: hold their wave-5 rate.
    response_rate: dict[str, dict[int, float]]

    #: Target mean for senior_leadership_trust / purpose_meaning per entity per
    #: wave. Absent entries hold the wave-5 mean.
    theme_targets: dict[str, dict[str, dict[int, float]]]

    #: Multiplier on the measured baseline monthly hazard, one value per
    #: simulated month (Jan…Jul 2026).
    hazard_multipliers: dict[str, tuple[float, ...]]

    #: (first_month, last_month) relative risk of the divergence cohort and of
    #: non-divergent HiPos, versus the non-HiPo baseline. Linearly interpolated.
    divergence_rr: tuple[float, float]
    hipo_rr: tuple[float, float]

    #: Multiplier on the push-pathway sampling weight when drawing a departure's
    #: exit_type / stated_exit_reason / pathway tuple.
    push_tilt: dict[str, float] = field(default_factory=dict)


# Observed wave-5 anchors, for reference when reading the targets below:
#   response rate   Entity_A 83.1%  Entity_B 62.4%  Entity_C 68.6%  Origin 84.8%
#   trust           Entity_A 3.339  Entity_B 3.075  Entity_C 3.264  Origin 3.386
#   purpose         Entity_A 3.332  Entity_B 3.067  Entity_C 3.205  Origin 3.363
#   monthly hazard  Entity_A 0.311% Entity_B 0.682% Entity_C 1.093% Origin 0.449%
# The mature benchmark used throughout the deck is ~3.38 on the theme scale and
# ~84% response.

SCENARIO_A = Scenario(
    key="A",
    label="DETERIORATING - Entity_C's warning signature persists and worsens",
    out_dir=SCENARIO_A_DIR,
    response_rate={
        # Entity_C drifts from 68.6% down toward Entity_B's ~63%.
        "Entity_C": {6: 0.665, 7: 0.648, 8: 0.630},
        # Entity_B stays flat and low.
        "Entity_B": {6: 0.620, 7: 0.617, 8: 0.613},
        # Mature cohorts hold ~84%.
        "Entity_A": {6: 0.830, 7: 0.829, 8: 0.828},
        "NovaCorp-Origin": {6: 0.847, 7: 0.846, 8: 0.845},
    },
    theme_targets={
        "Entity_C": {
            "senior_leadership_trust": {6: 3.19, 7: 3.11, 8: 3.03},
            "purpose_meaning": {6: 3.13, 7: 3.05, 8: 2.97},
        },
        "Entity_B": {
            "senior_leadership_trust": {6: 3.06, 7: 3.04, 8: 3.02},
            "purpose_meaning": {6: 3.05, 7: 3.03, 8: 3.01},
        },
        "Entity_A": {
            "senior_leadership_trust": {6: 3.34, 7: 3.34, 8: 3.33},
            "purpose_meaning": {6: 3.33, 7: 3.33, 8: 3.32},
        },
        "NovaCorp-Origin": {
            "senior_leadership_trust": {6: 3.386, 7: 3.384, 8: 3.382},
            "purpose_meaning": {6: 3.362, 7: 3.360, 8: 3.358},
        },
    },
    # Rising attrition with roughly the ~6-month lag the analysis established:
    # the wave-5 signal (Aug 2025) is already in the pipeline, so Entity_C is
    # elevated from January and keeps climbing as the wave 6/7 deterioration
    # feeds through.
    hazard_multipliers={
        "Entity_C": (1.10, 1.18, 1.26, 1.35, 1.44, 1.52, 1.60),
        "Entity_B": (1.02, 1.05, 1.08, 1.11, 1.14, 1.17, 1.20),
        "Entity_A": (1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00),
        "NovaCorp-Origin": (1.00, 1.01, 1.02, 1.03, 1.04, 1.05, 1.06),
    },
    divergence_rr=(1.75, 2.30),
    hipo_rr=(1.40, 1.55),
    push_tilt={"Entity_C": 1.25, "Entity_B": 1.10},
)

SCENARIO_B = Scenario(
    key="B",
    label="IMPROVING - Recommendations 1-3 implemented from Q4 2025",
    out_dir=SCENARIO_B_DIR,
    response_rate={
        # Entity_C recovers past Recommendation 3's stated 75% floor and then
        # toward the mature benchmark.
        "Entity_C": {6: 0.720, 7: 0.757, 8: 0.795},
        # Entity_B climbs meaningfully off 63%.
        "Entity_B": {6: 0.660, 7: 0.700, 8: 0.735},
        "Entity_A": {6: 0.832, 7: 0.834, 8: 0.836},
        "NovaCorp-Origin": {6: 0.849, 7: 0.850, 8: 0.851},
    },
    theme_targets={
        "Entity_C": {
            "senior_leadership_trust": {6: 3.30, 7: 3.34, 8: 3.38},
            "purpose_meaning": {6: 3.26, 7: 3.32, 8: 3.38},
        },
        "Entity_B": {
            "senior_leadership_trust": {6: 3.13, 7: 3.20, 8: 3.27},
            "purpose_meaning": {6: 3.12, 7: 3.19, 8: 3.26},
        },
        "Entity_A": {
            "senior_leadership_trust": {6: 3.35, 7: 3.36, 8: 3.37},
            "purpose_meaning": {6: 3.34, 7: 3.35, 8: 3.36},
        },
        "NovaCorp-Origin": {
            "senior_leadership_trust": {6: 3.388, 7: 3.390, 8: 3.392},
            "purpose_meaning": {6: 3.366, 7: 3.370, 8: 3.374},
        },
    },
    # The interventions land in Q4 2025, so with the ~6-month lag the attrition
    # response is flat through Q1 2026 and only bends down from April. That lag
    # is the point: engagement moves first, attrition follows.
    hazard_multipliers={
        "Entity_C": (1.00, 0.97, 0.92, 0.84, 0.74, 0.64, 0.56),
        "Entity_B": (1.00, 0.99, 0.96, 0.91, 0.85, 0.79, 0.74),
        "Entity_A": (1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00),
        "NovaCorp-Origin": (1.00, 1.00, 0.99, 0.98, 0.97, 0.96, 0.95),
    },
    divergence_rr=(1.75, 1.05),
    hipo_rr=(1.40, 1.15),
    push_tilt={"Entity_C": 0.85, "Entity_B": 0.90},
)

SCENARIOS: tuple[Scenario, ...] = (SCENARIO_A, SCENARIO_B)

# Column order of each output file, taken from the source headers.
EMPLOYEE_COLUMNS = [
    "employee_id", "name", "hire_date", "exit_date", "status", "department",
    "role_family", "role_level", "job_title", "salary", "compa_ratio", "gender",
    "age_band", "cultural_background", "contract_type", "hipo_flag",
    "promotion_eligible", "manager_id", "hire_source", "legacy_entity_code",
    "data_source_system", "days_to_fill", "tenure_months", "acting_appointment",
]
ATTRITION_COLUMNS = [
    "employee_id", "exit_date", "exit_type", "stated_exit_reason",
    "notice_period_served", "regrettable_flag", "performance_band_at_exit",
    "salary_at_exit", "manager_id_at_exit", "pathway",
]
ENGAGEMENT_COLUMNS = [
    "employee_id", "wave_number", "survey_date", "response_flag",
    *ENGAGEMENT_DIMENSIONS,
]
PERFORMANCE_COLUMNS = [
    "employee_id", "review_date", "performance_rating", "review_cycle",
    "promotion_recommendation", "goal_achievement_score", "reviewer_id",
]

RATING_TO_NUM = {
    "Unsatisfactory": 1,
    "Below Expectations": 2,
    "Meets Expectations": 3,
    "High Performer": 4,
    "Outstanding": 5,
}
NUM_TO_RATING = {v: k for k, v in RATING_TO_NUM.items()}


# =============================================================================
# SOURCE LOADING
# =============================================================================

def find_data_dir() -> pathlib.Path:
    """Locate the read-only case data by walking up from this file.

    Same discovery rule as ``dashboard/data_loader.py`` and the notebooks, so
    the script runs from any working directory with no absolute paths.
    """
    here = pathlib.Path(__file__).resolve().parent
    for base in [here, *here.parents]:
        hit = base / "0_case" / "Accenture_Case_Comp_Data"
        if hit.is_dir():
            return hit
    raise FileNotFoundError(
        "Could not find 0_case/Accenture_Case_Comp_Data by walking up from "
        f"{here}. Run this script from inside the NovaCorp repo."
    )


def load_source(data_dir: pathlib.Path) -> dict[str, pd.DataFrame]:
    """Read the four source CSVs. Read-only — nothing here writes to data_dir."""
    return {
        "employees": pd.read_csv(
            data_dir / "employees.csv", parse_dates=["hire_date", "exit_date"]
        ),
        "attrition": pd.read_csv(
            data_dir / "attrition_log.csv", parse_dates=["exit_date"]
        ),
        "engagement": pd.read_csv(
            data_dir / "engagement.csv", parse_dates=["survey_date"]
        ),
        "performance": pd.read_csv(
            data_dir / "performance.csv", parse_dates=["review_date"]
        ),
    }


# =============================================================================
# EMPIRICAL MODEL — every distribution the simulation draws from is fitted here
# from the real data, so the synthetic rows are statistically indistinguishable
# from the real ones except in the scenario direction being simulated.
# =============================================================================

@dataclass
class EmpiricalModel:
    base_hazard: dict[str, float]
    wave5_response: dict[str, float]
    wave5_theme_mean: dict[str, dict[str, float]]
    hist_theme_mean: dict[tuple[str, int, str], float]
    org_composite_mean: float
    org_composite_sd: float
    exit_tuples: dict[str, pd.DataFrame]
    notice_prob: dict[str, float]
    band_delta_pmf: dict[str, tuple[np.ndarray, np.ndarray]]
    band_marginal: tuple[np.ndarray, np.ndarray]
    regrettable_rate: dict[tuple, float]
    rating_pmf_by_hipo: dict[bool, tuple[np.ndarray, np.ndarray]]
    goal_pool: dict[tuple[str, bool], np.ndarray]
    promo_rate_by_rating: dict[str, float]
    reviewer_is_manager_rate: float
    salary_pool: dict[str, pd.DataFrame]
    salary_pool_by_level: dict[int, pd.DataFrame]
    hire_source_pmf: tuple[np.ndarray, np.ndarray]
    contract_pmf: tuple[np.ndarray, np.ndarray]
    gender_pmf: tuple[np.ndarray, np.ndarray]
    age_band_pmf: tuple[np.ndarray, np.ndarray]
    culture_pmf: tuple[np.ndarray, np.ndarray]
    new_hire_hipo_rate: float
    new_hire_promo_eligible_rate: float
    new_hire_acting_rate: float
    first_names: np.ndarray
    last_names: np.ndarray


def _pmf(series: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    """(values, probabilities) for an empirical categorical distribution."""
    vc = series.value_counts(normalize=True)
    return vc.index.to_numpy(), vc.to_numpy()


def _measure_base_hazard(emp: pd.DataFrame, att: pd.DataFrame) -> dict[str, float]:
    """Exposure-correct monthly departure hazard per entity over the fit window.

    Person-month denominators, not headcount ratios — Entity_C joined in April
    2025 and a crude rate would understate its hazard by more than half.
    """
    exits = att.merge(
        emp[["employee_id", "legacy_entity_code"]], on="employee_id", how="left"
    )
    months = pd.period_range(HAZARD_CALIBRATION_START, HAZARD_CALIBRATION_END, freq="M")
    at_risk: dict[str, int] = {}
    departed: dict[str, int] = {}
    for month in months:
        anchor = month.to_timestamp()
        live = emp[
            (emp["hire_date"] <= anchor)
            & (emp["exit_date"].isna() | (emp["exit_date"] > anchor))
        ]
        left = exits[exits["exit_date"].dt.to_period("M") == month]
        for entity, n in live["legacy_entity_code"].value_counts().items():
            at_risk[entity] = at_risk.get(entity, 0) + int(n)
        for entity, n in left["legacy_entity_code"].value_counts().items():
            departed[entity] = departed.get(entity, 0) + int(n)
    return {e: departed.get(e, 0) / n for e, n in at_risk.items() if n}


def _measure_band_deltas(
    att: pd.DataFrame, perf: pd.DataFrame
) -> tuple[dict[str, tuple[np.ndarray, np.ndarray]], tuple[np.ndarray, np.ndarray]]:
    """How ``performance_band_at_exit`` is written relative to the real review.

    The documented quirk: the exit band agrees with the employee's nearest real
    review only ~28% of the time, written down for push exits and up for pull
    ones. Reproduced as the empirical PMF of that signed step, per pathway.
    """
    perf = perf[["employee_id", "review_date", "performance_rating"]].copy()
    perf["rating_num"] = perf["performance_rating"].map(RATING_TO_NUM)
    merged = att[["employee_id", "exit_date", "pathway", "performance_band_at_exit"]].merge(
        perf, on="employee_id", how="inner"
    )
    merged["gap"] = (merged["review_date"] - merged["exit_date"]).abs()
    nearest = merged.sort_values("gap").drop_duplicates("employee_id", keep="first")
    nearest = nearest.assign(
        delta=nearest["performance_band_at_exit"].map(RATING_TO_NUM)
        - nearest["rating_num"]
    )
    pmfs = {
        pathway: _pmf(group["delta"])
        for pathway, group in nearest.groupby("pathway", observed=True)
    }
    return pmfs, _pmf(att["performance_band_at_exit"])


def _measure_regrettable(att: pd.DataFrame, emp: pd.DataFrame) -> dict[tuple, float]:
    """P(regrettable_flag) keyed on (pathway, hipo_flag, band), with fallbacks.

    The flag is endogenous to the talent-review process — HiPo status carries
    most of it — so it is reproduced as a conditional rate rather than a rule.
    """
    merged = att.merge(emp[["employee_id", "hipo_flag"]], on="employee_id", how="left")
    rates: dict[tuple, float] = {("*",): float(merged["regrettable_flag"].mean())}
    for keys in (
        ["pathway"],
        ["pathway", "hipo_flag"],
        ["pathway", "hipo_flag", "performance_band_at_exit"],
    ):
        grouped = merged.groupby(keys, observed=True)["regrettable_flag"].agg(["mean", "size"])
        for key, row in grouped.iterrows():
            parts = key if isinstance(key, tuple) else (key,)
            # numpy bool_ keys would still hash-match, but cast so the lookup
            # tuples built at draw time are literally the same objects' values.
            clean = tuple(bool(p) if isinstance(p, (bool, np.bool_)) else p for p in parts)
            if row["size"] >= 5:
                rates[clean] = float(row["mean"])
    return rates


def build_model(src: dict[str, pd.DataFrame]) -> EmpiricalModel:
    """Fit every distribution the simulation needs from the source data."""
    emp, att = src["employees"], src["attrition"]
    eng, perf = src["engagement"], src["performance"]

    eng_ent = eng.merge(
        emp[["employee_id", "legacy_entity_code"]], on="employee_id", how="left"
    )
    responded = eng_ent[eng_ent["response_flag"]]
    wave5 = eng_ent[eng_ent["wave_number"] == 5]
    wave5_resp = wave5[wave5["response_flag"]]

    wave5_response = wave5.groupby("legacy_entity_code")["response_flag"].mean().to_dict()
    wave5_theme_mean = {
        entity: {dim: float(group[dim].mean()) for dim in ENGAGEMENT_DIMENSIONS}
        for entity, group in wave5_resp.groupby("legacy_entity_code", observed=True)
    }
    hist_theme_mean = {
        (entity, int(wave), dim): float(value)
        for dim in ENGAGEMENT_DIMENSIONS
        for (entity, wave), value in
        responded.groupby(["legacy_entity_code", "wave_number"], observed=True)[dim].mean().items()
    }

    org = responded[list(ORG_SENTIMENT_DIMENSIONS)].mean(axis=1)

    # Departure composition: sample (exit_type, reason, pathway) as a joint
    # tuple per entity, so impossible combinations can never be produced.
    att_ent = att.merge(
        emp[["employee_id", "legacy_entity_code"]], on="employee_id", how="left"
    )
    exit_tuples: dict[str, pd.DataFrame] = {}
    for entity, group in att_ent.groupby("legacy_entity_code", observed=True):
        counts = (
            group.groupby(["exit_type", "stated_exit_reason", "pathway"], observed=True)
            .size()
            .reset_index(name="weight")
        )
        exit_tuples[entity] = counts
    pooled = (
        att_ent.groupby(["exit_type", "stated_exit_reason", "pathway"], observed=True)
        .size()
        .reset_index(name="weight")
    )
    exit_tuples["*"] = pooled

    band_delta_pmf, band_marginal = _measure_band_deltas(att, perf)

    perf_hipo = perf.merge(emp[["employee_id", "hipo_flag"]], on="employee_id", how="left")
    rating_pmf_by_hipo = {
        bool(flag): _pmf(group["performance_rating"])
        for flag, group in perf_hipo.groupby("hipo_flag", observed=True)
    }
    goal_pool = {
        (str(rating), bool(flag)): group["goal_achievement_score"].to_numpy()
        for (rating, flag), group in perf_hipo.groupby(
            ["performance_rating", "hipo_flag"], observed=True
        )
    }
    for rating, group in perf.groupby("performance_rating", observed=True):
        goal_pool[(str(rating), "*")] = group["goal_achievement_score"].to_numpy()

    emp_mgr = perf.merge(emp[["employee_id", "manager_id"]], on="employee_id", how="left")

    # Salary / compa_ratio for a replacement are taken from a donor incumbent in
    # the same job title, so the joint distribution is preserved exactly rather
    # than reconstructed from a band midpoint that does not exist in this data.
    active = emp[emp["status"] == "active"]
    salary_pool = {
        str(title): group[["salary", "compa_ratio"]]
        for title, group in active.groupby("job_title", observed=True)
    }
    salary_pool_by_level = {
        int(level): group[["salary", "compa_ratio"]]
        for level, group in active.groupby("role_level", observed=True)
    }

    non_acq = emp[emp["hire_source"].isin(REPLACEMENT_HIRE_SOURCES)]
    fresh = emp[emp["tenure_months"] <= NEW_HIRE_REFERENCE_TENURE_MONTHS]
    if fresh.empty:
        fresh = emp

    names = emp["name"].astype(str).str.split()
    first_names = names.str[0].dropna().unique()
    last_names = names.str[-1].dropna().unique()

    return EmpiricalModel(
        base_hazard=_measure_base_hazard(emp, att),
        wave5_response={str(k): float(v) for k, v in wave5_response.items()},
        wave5_theme_mean=wave5_theme_mean,
        hist_theme_mean=hist_theme_mean,
        org_composite_mean=float(org.mean()),
        org_composite_sd=float(org.std()),
        exit_tuples=exit_tuples,
        notice_prob=att.groupby("exit_type", observed=True)["notice_period_served"].mean().to_dict(),
        band_delta_pmf=band_delta_pmf,
        band_marginal=band_marginal,
        regrettable_rate=_measure_regrettable(att, emp),
        rating_pmf_by_hipo=rating_pmf_by_hipo,
        goal_pool=goal_pool,
        promo_rate_by_rating=perf.groupby("performance_rating", observed=True)[
            "promotion_recommendation"
        ].mean().to_dict(),
        reviewer_is_manager_rate=float((emp_mgr["reviewer_id"] == emp_mgr["manager_id"]).mean()),
        salary_pool=salary_pool,
        salary_pool_by_level=salary_pool_by_level,
        hire_source_pmf=_pmf(non_acq["hire_source"]),
        contract_pmf=_pmf(emp["contract_type"]),
        gender_pmf=_pmf(emp["gender"]),
        age_band_pmf=_pmf(emp["age_band"]),
        culture_pmf=_pmf(emp["cultural_background"]),
        new_hire_hipo_rate=float(fresh["hipo_flag"].mean()),
        new_hire_promo_eligible_rate=float(fresh["promotion_eligible"].mean()),
        new_hire_acting_rate=float(emp["acting_appointment"].mean()),
        first_names=first_names,
        last_names=last_names,
    )


# =============================================================================
# ENGAGEMENT LATENT STATE
# =============================================================================

class LatentEngagement:
    """Per-person latent theme state, carried forward across the new waves.

    A score is modelled as ``cohort mean + permanent person effect + AR(1) mood
    + noise``, with the variance shares solved from the observed within-person
    lag correlations. The permanent effect is estimated from each person's own
    wave 1–5 answers (shrunk toward zero by how often they answered), so an
    employee who has been consistently negative stays consistently negative into
    2026 instead of being redrawn from scratch.
    """

    def __init__(self, src: dict[str, pd.DataFrame], model: EmpiricalModel, rng: np.random.Generator):
        self.rng = rng
        self.model = model
        self.var_perm = VAR_SHARE_PERMANENT * SCORE_SD ** 2
        self.var_ar = VAR_SHARE_AR * SCORE_SD ** 2
        self.var_noise = VAR_SHARE_NOISE * SCORE_SD ** 2
        self.n_dim = len(ENGAGEMENT_DIMENSIONS)
        self.permanent: dict[str, np.ndarray] = {}
        self.mood: dict[str, np.ndarray] = {}
        self.propensity: dict[str, float] = {}
        self._seed_from_history(src, model)

    def _seed_from_history(self, src: dict[str, pd.DataFrame], model: EmpiricalModel) -> None:
        eng = src["engagement"]
        emp = src["employees"]
        hist = eng[eng["response_flag"]].merge(
            emp[["employee_id", "legacy_entity_code"]], on="employee_id", how="left"
        )
        if hist.empty:
            return

        # Deviation of each answer from its own cohort-wave mean.
        dev = pd.DataFrame({"employee_id": hist["employee_id"].to_numpy()})
        for dim in ENGAGEMENT_DIMENSIONS:
            cohort_mean = np.array([
                model.hist_theme_mean.get((entity, int(wave), dim), np.nan)
                for entity, wave in zip(hist["legacy_entity_code"], hist["wave_number"])
            ])
            dev[dim] = hist[dim].to_numpy() - cohort_mean
        dev["wave_number"] = hist["wave_number"].to_numpy()

        dims = list(ENGAGEMENT_DIMENSIONS)
        grouped = dev.groupby("employee_id", observed=True)
        counts = grouped.size()
        means = grouped[dims].mean().reindex(counts.index)
        last_rows = (
            dev.sort_values("wave_number")
            .drop_duplicates("employee_id", keep="last")
            .set_index("employee_id")
            .reindex(counts.index)
        )

        # Vectorised across all employees at once — a per-employee .loc here
        # costs minutes on 13k people for no benefit.
        emp_ids = counts.index.to_numpy()
        n_obs = counts.to_numpy(dtype=float)[:, None]
        var_resid = self.var_ar + self.var_noise
        shrink = (n_obs * self.var_perm) / (n_obs * self.var_perm + var_resid)
        perm = np.nan_to_num(means.to_numpy(dtype=float)) * shrink
        last_dev = np.nan_to_num(last_rows[dims].to_numpy(dtype=float))
        mood = last_dev - perm

        # Carry each person's mood forward from their last answered wave to
        # wave 5, so every seeded state is on the same footing.
        steps = np.clip(5 - last_rows["wave_number"].to_numpy(dtype=float), 0, None)[:, None]
        decay = AR_RHO ** steps
        spread = np.sqrt(np.maximum(self.var_ar * (1 - decay ** 2), 0.0))
        mood = decay * mood + spread * self.rng.standard_normal(mood.shape)

        for i, emp_id in enumerate(emp_ids):
            self.permanent[emp_id] = perm[i]
            self.mood[emp_id] = mood[i]

    def _ensure(self, emp_id: str) -> None:
        """Create latent state for someone with no survey history (a new hire)."""
        if emp_id in self.permanent:
            return
        self.permanent[emp_id] = np.sqrt(self.var_perm) * self.rng.standard_normal(self.n_dim)
        self.mood[emp_id] = np.sqrt(self.var_ar) * self.rng.standard_normal(self.n_dim)

    def response_propensity(self, emp_id: str) -> float:
        if emp_id not in self.propensity:
            self.propensity[emp_id] = float(
                RESPONSE_PROPENSITY_SD * self.rng.standard_normal()
            )
        return self.propensity[emp_id]

    def advance(self, emp_ids: list[str]) -> np.ndarray:
        """Step the AR(1) mood one wave and return the deviation matrix."""
        out = np.empty((len(emp_ids), self.n_dim))
        spread = np.sqrt(self.var_ar * (1 - AR_RHO ** 2))
        noise_sd = np.sqrt(self.var_noise)
        for i, emp_id in enumerate(emp_ids):
            self._ensure(emp_id)
            mood = AR_RHO * self.mood[emp_id] + spread * self.rng.standard_normal(self.n_dim)
            self.mood[emp_id] = mood
            out[i] = self.permanent[emp_id] + mood + noise_sd * self.rng.standard_normal(self.n_dim)
        return out


# =============================================================================
# SIMULATION
# =============================================================================

class Simulator:
    """Runs one scenario forward from 2026-01 to 2026-07."""

    def __init__(
        self,
        scenario: Scenario,
        src: dict[str, pd.DataFrame],
        model: EmpiricalModel,
        seed_sequence: np.random.SeedSequence,
    ):
        self.scenario = scenario
        self.model = model
        self.rng = np.random.default_rng(seed_sequence)
        self.src = src

        self.emp = src["employees"].copy()
        self.emp["employee_id"] = self.emp["employee_id"].astype(str)
        self.perf = src["performance"].copy()

        self.new_engagement: list[dict] = []
        self.new_attrition: list[dict] = []
        self.new_performance: list[dict] = []
        self.new_hires: list[dict] = []

        self.latent = LatentEngagement(src, model, self.rng)
        self.next_id = NEW_ID_START
        self.unfilled_vacancies = 0
        self.pending_hires: list[dict] = []

        self._seed_response_state()
        self._index_reviews()

        self.months = list(pd.period_range(SIM_FIRST_MONTH, SIM_LAST_MONTH, freq="M"))
        self.wave_by_month = {
            pd.Timestamp(date).to_period("M"): (wave, pd.Timestamp(date))
            for wave, date in NEW_WAVES
        }

    # ------------------------------------------------------------- seeding
    def _seed_response_state(self) -> None:
        """Latest response flag and organisation-sentiment z per employee.

        These drive the individual risk model, reproducing the ~2x
        non-responder exit relationship (Evidence 4) rather than drawing
        departures at random.
        """
        eng = self.src["engagement"]
        latest = eng.sort_values("wave_number").drop_duplicates("employee_id", keep="last")
        self.last_response: dict[str, bool] = dict(
            zip(latest["employee_id"].astype(str), latest["response_flag"].astype(bool))
        )
        answered = eng[eng["response_flag"]].sort_values("wave_number")
        answered = answered.drop_duplicates("employee_id", keep="last")
        composite = answered[list(ORG_SENTIMENT_DIMENSIONS)].mean(axis=1)
        z = (composite - self.model.org_composite_mean) / self.model.org_composite_sd
        self.last_org_z: dict[str, float] = dict(
            zip(answered["employee_id"].astype(str), z.astype(float))
        )

    def _index_reviews(self) -> None:
        """Reviews sorted by date, for the divergence cohort and exit bands."""
        self.review_index = self.perf[
            ["employee_id", "review_date", "performance_rating", "goal_achievement_score"]
        ].copy()
        self.review_index["employee_id"] = self.review_index["employee_id"].astype(str)

    # --------------------------------------------------------------- helpers
    def _active(self, anchor: pd.Timestamp) -> pd.DataFrame:
        return self.emp[
            (self.emp["hire_date"] <= anchor)
            & (self.emp["exit_date"].isna() | (self.emp["exit_date"] > anchor))
        ]

    def _new_employee_id(self) -> str:
        emp_id = f"E{self.next_id:05d}"
        self.next_id += 1
        return emp_id

    @staticmethod
    def _tenure_months(hire: pd.Timestamp, end: pd.Timestamp) -> int:
        """Observed convention: floor of elapsed days over 30 (verified 100%)."""
        return int(max((end - hire).days, 0) // 30)

    def _sample(self, values: np.ndarray, probs: np.ndarray):
        return values[self.rng.choice(len(values), p=probs)]

    # ---------------------------------------------------------- engagement
    def _theme_target(self, entity: str, dim: str, wave: int) -> float:
        targets = self.scenario.theme_targets.get(entity, {})
        if dim in targets and wave in targets[dim]:
            return targets[dim][wave]
        fallback = self.model.wave5_theme_mean.get(entity, {})
        return fallback.get(dim, 3.37)

    def _response_target(self, entity: str, wave: int) -> float:
        per_entity = self.scenario.response_rate.get(entity, {})
        if wave in per_entity:
            return per_entity[wave]
        return self.model.wave5_response.get(entity, 0.80)

    def _run_wave(self, wave: int, anchor: pd.Timestamp) -> None:
        """Issue a survey to everyone active at the wave anchor.

        Non-response rows are kept with null scores — non-response is the key
        signal in this product, not missing data.
        """
        population = self._active(anchor)
        if population.empty:
            return
        emp_ids = population["employee_id"].tolist()
        entities = population["legacy_entity_code"].to_numpy()
        n = len(emp_ids)

        deviations = self.latent.advance(emp_ids)

        offsets = self.rng.integers(
            -WAVE_FIELD_HALF_WIDTH_DAYS, WAVE_FIELD_HALF_WIDTH_DAYS + 1, size=n
        )
        # Response is drawn per person from their own propensity, but the count
        # per cohort is pinned to the target: at Entity_C's ~900 respondents the
        # binomial standard error is 1.6pp, which is larger than a wave-to-wave
        # scenario step and would render the trend non-monotone by luck alone.
        propensity = np.array([self.latent.response_propensity(e) for e in emp_ids])
        responded = np.zeros(n, dtype=bool)
        for entity in np.unique(entities):
            mask = entities == entity
            size = int(mask.sum())
            if not size:
                continue
            target = self._response_target(str(entity), wave)
            target += float(self.rng.normal(0.0, RESPONSE_WOBBLE_SD))
            target = float(np.clip(target, 0.02, 0.99))
            k = int(round(size * target))
            if k <= 0:
                continue
            margin = np.clip(target + propensity[mask], 0.02, 0.99) - self.rng.random(size)
            chosen = np.argsort(-margin)[:k]
            idx = np.flatnonzero(mask)[chosen]
            responded[idx] = True

        # Pin each cohort's realised mean to its configured target. The
        # per-person deviation carries all the individual variation and the
        # within-person persistence; the pin only removes the cohort-level
        # sampling noise, which at n ~ 900 is +/-.03 and would otherwise swamp
        # a scenario signal of .08 per wave.
        scores = np.full((n, len(ENGAGEMENT_DIMENSIONS)), np.nan)
        for entity in np.unique(entities):
            mask = (entities == entity) & responded
            if not mask.any():
                continue
            for j, dim in enumerate(ENGAGEMENT_DIMENSIONS):
                target = self._theme_target(str(entity), dim, wave)
                target += float(self.rng.normal(0.0, COHORT_WOBBLE_SD))
                dev = deviations[mask, j]
                values = np.clip(target + dev - dev.mean(), SCORE_MIN, SCORE_MAX)
                for _ in range(COHORT_PIN_ITERATIONS):
                    values = np.clip(
                        values + (target - values.mean()), SCORE_MIN, SCORE_MAX
                    )
                scores[mask, j] = np.round(values, 2)

        org_cols = [ENGAGEMENT_DIMENSIONS.index(d) for d in ORG_SENTIMENT_DIMENSIONS]
        for i, emp_id in enumerate(emp_ids):
            answered = bool(responded[i])
            row = {
                "employee_id": emp_id,
                "wave_number": wave,
                "survey_date": anchor + pd.Timedelta(days=int(offsets[i])),
                "response_flag": answered,
            }
            for j, dim in enumerate(ENGAGEMENT_DIMENSIONS):
                row[dim] = float(scores[i, j]) if answered else np.nan
            if answered:
                org = float(np.mean(scores[i, org_cols]))
                self.last_org_z[emp_id] = (
                    org - self.model.org_composite_mean
                ) / self.model.org_composite_sd
            self.last_response[emp_id] = answered
            self.new_engagement.append(row)

    # ----------------------------------------------------------- attrition
    def _divergence_flags(self, population: pd.DataFrame, anchor: pd.Timestamp) -> pd.Series:
        """Evidence 5's cohort: HiPo with lagged goal achievement in the
        bottom 40% *within role level*.

        The lag matters — performance measured after the departure decision has
        already been made would be reverse causation, so only reviews at least
        DIVERGENCE_LOOKBACK_DAYS old are eligible.
        """
        cutoff = anchor - pd.Timedelta(days=DIVERGENCE_LOOKBACK_DAYS)
        eligible = self.review_index[self.review_index["review_date"] <= cutoff]
        if eligible.empty:
            return pd.Series(False, index=population.index)
        latest = eligible.sort_values("review_date").drop_duplicates(
            "employee_id", keep="last"
        )
        merged = population[["employee_id", "role_level", "hipo_flag"]].merge(
            latest[["employee_id", "goal_achievement_score"]], on="employee_id", how="left"
        )
        pct = merged.groupby("role_level", observed=True)["goal_achievement_score"].rank(pct=True)
        flags = merged["hipo_flag"].to_numpy() & (pct <= DIVERGENCE_PERCENTILE_CUTOFF).to_numpy(
            na_value=False
        )
        return pd.Series(flags, index=population.index)

    def _risk_weights(
        self, population: pd.DataFrame, anchor: pd.Timestamp, progress: float
    ) -> np.ndarray:
        """Relative departure risk. Normalised to mean 1 within entity later, so
        these set who leaves; the entity hazard multiplier sets how many."""
        n = len(population)
        weights = np.ones(n)

        emp_ids = population["employee_id"].to_numpy()

        silent = np.array([not self.last_response.get(e, True) for e in emp_ids])
        weights *= np.where(silent, NONRESPONSE_RISK_MULTIPLIER, 1.0)

        z = np.array([self.last_org_z.get(e, 0.0) for e in emp_ids])
        weights *= np.exp(-ORG_SENTIMENT_BETA * z)

        tenure = ((anchor - population["hire_date"]).dt.days // 30).to_numpy()
        band = np.ones(n)
        for low, high, mult in TENURE_BAND_MULTIPLIERS:
            band = np.where((tenure >= low) & (tenure < high), mult, band)
        weights *= band

        divergent = self._divergence_flags(population, anchor).to_numpy()
        hipo = population["hipo_flag"].to_numpy(dtype=bool)
        div_rr = self.scenario.divergence_rr[0] + progress * (
            self.scenario.divergence_rr[1] - self.scenario.divergence_rr[0]
        )
        hipo_rr = self.scenario.hipo_rr[0] + progress * (
            self.scenario.hipo_rr[1] - self.scenario.hipo_rr[0]
        )
        weights *= np.where(divergent, div_rr, np.where(hipo, hipo_rr, 1.0))

        return weights

    def _draw_departures(self, month: pd.Period, month_index: int) -> list[str]:
        anchor = month.to_timestamp()
        population = self._active(anchor)
        if population.empty:
            return []
        progress = month_index / max(len(self.months) - 1, 1)
        weights = self._risk_weights(population, anchor, progress)

        leavers: list[str] = []
        for entity, group_idx in population.groupby("legacy_entity_code", observed=True).groups.items():
            idx = population.index.get_indexer(group_idx)
            w = weights[idx]
            if w.sum() <= 0:
                continue
            base = self.model.base_hazard.get(str(entity), 0.0)
            mult_series = self.scenario.hazard_multipliers.get(str(entity))
            mult = mult_series[month_index] if mult_series else 1.0

            # How many leave is the scenario's parameter, wobbled a little.
            # Who leaves is the risk model, sampled without replacement with
            # probability proportional to the individual weights.
            wobble = float(np.exp(self.rng.normal(0.0, MONTHLY_HAZARD_WOBBLE_SD)))
            k = int(round(len(w) * base * mult * wobble))
            k = min(max(k, 0), len(w))
            if k == 0:
                continue
            picked = self.rng.choice(len(w), size=k, replace=False, p=w / w.sum())
            leavers.extend(population.loc[group_idx[picked]]["employee_id"].tolist())
        return leavers

    def _exit_tuple(self, entity: str) -> tuple[str, str, str]:
        table = self.model.exit_tuples.get(entity, self.model.exit_tuples["*"])
        weights = table["weight"].to_numpy(dtype=float).copy()
        tilt = self.scenario.push_tilt.get(entity, 1.0)
        if tilt != 1.0:
            weights = np.where(table["pathway"].to_numpy() == "push", weights * tilt, weights)
        weights = weights / weights.sum()
        row = table.iloc[self.rng.choice(len(table), p=weights)]
        return str(row["exit_type"]), str(row["stated_exit_reason"]), str(row["pathway"])

    def _exit_band(self, emp_id: str, exit_date: pd.Timestamp, pathway: str) -> str:
        """Reproduce the exit-band quirk: agrees with the nearest real review
        only ~28% of the time, written down for push and up for pull."""
        reviews = self.review_index[self.review_index["employee_id"] == emp_id]
        if reviews.empty:
            values, probs = self.model.band_marginal
            return str(self._sample(values, probs))
        nearest = reviews.iloc[(reviews["review_date"] - exit_date).abs().to_numpy().argmin()]
        base = RATING_TO_NUM[str(nearest["performance_rating"])]
        values, probs = self.model.band_delta_pmf.get(
            pathway, self.model.band_delta_pmf[next(iter(self.model.band_delta_pmf))]
        )
        delta = int(self._sample(values, probs))
        return NUM_TO_RATING[int(np.clip(base + delta, 1, 5))]

    def _regrettable(self, pathway: str, hipo: bool, band: str) -> bool:
        rates = self.model.regrettable_rate
        for key in ((pathway, hipo, band), (pathway, hipo), (pathway,), ("*",)):
            if key in rates:
                return bool(self.rng.random() < rates[key])
        return False

    def _record_departure(self, emp_id: str, exit_date: pd.Timestamp) -> dict:
        row = self.emp.loc[self.emp["employee_id"] == emp_id].iloc[0]
        entity = str(row["legacy_entity_code"])
        exit_type, reason, pathway = self._exit_tuple(entity)
        band = self._exit_band(emp_id, exit_date, pathway)
        notice_p = self.model.notice_prob.get(exit_type, 0.8)
        record = {
            "employee_id": emp_id,
            "exit_date": exit_date,
            "exit_type": exit_type,
            "stated_exit_reason": reason,
            "notice_period_served": bool(self.rng.random() < notice_p),
            "regrettable_flag": self._regrettable(pathway, bool(row["hipo_flag"]), band),
            "performance_band_at_exit": band,
            # Verified identities in the source: both fields are exact copies.
            "salary_at_exit": float(row["salary"]),
            "manager_id_at_exit": row["manager_id"],
            "pathway": pathway,
        }
        self.new_attrition.append(record)
        return dict(row)

    # -------------------------------------------------------------- hiring
    def _make_replacement(self, vacated: dict, exit_date: pd.Timestamp) -> None:
        """One replacement per departure — no net headcount growth.

        The replacement inherits the vacated role (department, role_family,
        role_level, job_title) and is hired by NovaCorp directly, so its
        legacy_entity_code is NovaCorp-Origin and its hire_source is drawn from
        the non-acquisition distribution.
        """
        gap = int(self.rng.integers(REPLACEMENT_GAP_DAYS[0], REPLACEMENT_GAP_DAYS[1] + 1))
        hire_date = exit_date + pd.Timedelta(days=gap)
        if hire_date > WINDOW_END_EXTENDED:
            self.unfilled_vacancies += 1
            return

        title = str(vacated["job_title"])
        pool = self.model.salary_pool.get(title)
        if pool is None or pool.empty:
            pool = self.model.salary_pool_by_level.get(int(vacated["role_level"]))
        if pool is None or pool.empty:
            salary, compa = float(vacated["salary"]), float(vacated["compa_ratio"])
        else:
            donor = pool.iloc[self.rng.integers(len(pool))]
            salary = float(donor["salary"]) * float(self.rng.normal(1.0, 0.02))
            compa = float(donor["compa_ratio"]) * float(self.rng.normal(1.0, 0.02))

        values, probs = self.model.hire_source_pmf
        source = str(self._sample(values, probs))
        if source == "graduate" and int(vacated["role_level"]) != 1:
            source = str(self._sample(*self._without_graduate()))

        emp_id = self._new_employee_id()
        self.pending_hires.append({
            "employee_id": emp_id,
            "name": f"{self._sample(self.model.first_names, self._uniform(self.model.first_names))} "
                    f"{self._sample(self.model.last_names, self._uniform(self.model.last_names))}",
            "hire_date": hire_date,
            "exit_date": pd.NaT,
            "status": "active",
            "department": vacated["department"],
            "role_family": vacated["role_family"],
            "role_level": int(vacated["role_level"]),
            "job_title": title,
            "salary": float(round(salary / 100.0) * 100),
            "compa_ratio": float(np.clip(round(compa, 2), 0.66, 1.19)),
            "gender": str(self._sample(*self.model.gender_pmf)),
            "age_band": str(self._sample(*self.model.age_band_pmf)),
            "cultural_background": str(self._sample(*self.model.culture_pmf)),
            "contract_type": str(self._sample(*self.model.contract_pmf)),
            "hipo_flag": bool(self.rng.random() < self.model.new_hire_hipo_rate),
            "promotion_eligible": bool(
                self.rng.random() < self.model.new_hire_promo_eligible_rate
            ),
            "manager_id": self._pick_manager(vacated, hire_date),
            "hire_source": source,
            "legacy_entity_code": REPLACEMENT_ENTITY,
            "data_source_system": REPLACEMENT_SOURCE_SYSTEM,
            "days_to_fill": float(gap),
            "tenure_months": 0,
            "acting_appointment": bool(self.rng.random() < self.model.new_hire_acting_rate),
        })

    def _uniform(self, values: np.ndarray) -> np.ndarray:
        return np.full(len(values), 1.0 / len(values))

    def _without_graduate(self) -> tuple[np.ndarray, np.ndarray]:
        values, probs = self.model.hire_source_pmf
        keep = values != "graduate"
        kept = probs[keep]
        return values[keep], kept / kept.sum()

    def _pick_manager(self, vacated: dict, hire_date: pd.Timestamp):
        """Keep the vacated role's manager if they are still here, else find a
        more senior colleague in the same department."""
        manager = vacated.get("manager_id")
        if isinstance(manager, str):
            match = self.emp.loc[self.emp["employee_id"] == manager]
            if not match.empty:
                row = match.iloc[0]
                if pd.isna(row["exit_date"]) or row["exit_date"] > hire_date:
                    return manager
        candidates = self._active(hire_date)
        candidates = candidates[
            (candidates["department"] == vacated["department"])
            & (candidates["role_level"] > int(vacated["role_level"]))
        ]
        if candidates.empty:
            candidates = self._active(hire_date)
            candidates = candidates[candidates["role_level"] > int(vacated["role_level"])]
        if candidates.empty:
            return manager
        return str(candidates.iloc[self.rng.integers(len(candidates))]["employee_id"])

    def _admit_pending_hires(self, month: pd.Period) -> None:
        """Move replacements whose start date has arrived onto the roster."""
        due = [h for h in self.pending_hires if h["hire_date"].to_period("M") <= month]
        if not due:
            return
        self.pending_hires = [
            h for h in self.pending_hires if h["hire_date"].to_period("M") > month
        ]
        self.new_hires.extend(due)
        self.emp = pd.concat(
            [self.emp, pd.DataFrame(due)[EMPLOYEE_COLUMNS]], ignore_index=True
        )

    # --------------------------------------------------------- performance
    def _run_review_cycle(self) -> None:
        """One new cycle on the observed cadence.

        Ratings are drawn conditional on hipo_flag only. That is deliberate:
        the source data's between-cycle rating correlation is ~.03, so a review
        is essentially an independent draw with hipo_flag as its only real
        input, and the analysis explicitly ruled out a performance divergence
        between these cohorts. The scenario difference belongs in engagement and
        attrition, not in a manufactured shift in ratings.
        """
        start, end = pd.Timestamp(REVIEW_WINDOW[0]), pd.Timestamp(REVIEW_WINDOW[1])
        population = self._active(start)
        if population.empty:
            return
        span = int((end - start).days)
        offsets = self.rng.integers(0, span + 1, size=len(population))

        for i, (_, row) in enumerate(population.iterrows()):
            hipo = bool(row["hipo_flag"])
            values, probs = self.model.rating_pmf_by_hipo.get(
                hipo, self.model.rating_pmf_by_hipo[False]
            )
            rating = str(self._sample(values, probs))
            pool = self.model.goal_pool.get(
                (rating, hipo), self.model.goal_pool.get((rating, "*"))
            )
            goal = float(pool[self.rng.integers(len(pool))])
            goal = float(np.clip(round(goal + self.rng.normal(0, 0.4), 1), 0.0, 100.0))
            promo_rate = self.model.promo_rate_by_rating.get(rating, 0.0)
            reviewer = row["manager_id"]
            if not isinstance(reviewer, str) or self.rng.random() >= self.model.reviewer_is_manager_rate:
                reviewer = self._pick_manager(dict(row), start) or reviewer
            self.new_performance.append({
                "employee_id": row["employee_id"],
                "review_date": start + pd.Timedelta(days=int(offsets[i])),
                "performance_rating": rating,
                "review_cycle": NEW_REVIEW_CYCLE,
                "promotion_recommendation": bool(self.rng.random() < promo_rate),
                "goal_achievement_score": goal,
                "reviewer_id": reviewer,
            })

        # A July departure's "nearest real review" is now this cycle, so the
        # exit-band quirk has to be able to see it.
        self.review_index = pd.concat(
            [
                self.review_index,
                pd.DataFrame(self.new_performance)[
                    ["employee_id", "review_date", "performance_rating",
                     "goal_achievement_score"]
                ],
            ],
            ignore_index=True,
        )

    # ------------------------------------------------------------- run loop
    def run(self) -> dict[str, pd.DataFrame]:
        for month_index, month in enumerate(self.months):
            self._admit_pending_hires(month)

            wave = self.wave_by_month.get(month)
            if wave is not None:
                self._run_wave(wave[0], wave[1])

            if pd.Timestamp(REVIEW_WINDOW[0]).to_period("M") == month:
                self._run_review_cycle()

            leavers = self._draw_departures(month, month_index)
            if leavers:
                month_start = month.to_timestamp()
                days_in_month = month.days_in_month
                for emp_id in leavers:
                    day = int(self.rng.integers(0, days_in_month))
                    exit_date = min(month_start + pd.Timedelta(days=day), WINDOW_END_EXTENDED)
                    vacated = self._record_departure(emp_id, exit_date)
                    mask = self.emp["employee_id"] == emp_id
                    self.emp.loc[mask, "exit_date"] = exit_date
                    self.emp.loc[mask, "status"] = "departed"
                    self._make_replacement(vacated, exit_date)

        self._admit_pending_hires(SIM_LAST_MONTH)
        return self._assemble()

    def _assemble(self) -> dict[str, pd.DataFrame]:
        emp = self.emp.copy()
        end = emp["exit_date"].fillna(WINDOW_END_EXTENDED)
        emp["tenure_months"] = [
            self._tenure_months(h, e) for h, e in zip(emp["hire_date"], end)
        ]
        emp = emp[EMPLOYEE_COLUMNS]

        attrition = pd.concat(
            [
                self.src["attrition"],
                pd.DataFrame(self.new_attrition, columns=ATTRITION_COLUMNS),
            ],
            ignore_index=True,
        )[ATTRITION_COLUMNS]  # source rows keep their original order; new rows append

        engagement = pd.concat(
            [
                self.src["engagement"],
                pd.DataFrame(self.new_engagement, columns=ENGAGEMENT_COLUMNS),
            ],
            ignore_index=True,
        )[ENGAGEMENT_COLUMNS]

        performance = pd.concat(
            [
                self.src["performance"],
                pd.DataFrame(self.new_performance, columns=PERFORMANCE_COLUMNS),
            ],
            ignore_index=True,
        )[PERFORMANCE_COLUMNS]

        for frame, cols in (
            (attrition, ["notice_period_served", "regrettable_flag"]),
            (engagement, ["response_flag"]),
            (performance, ["promotion_recommendation"]),
        ):
            for col in cols:
                frame[col] = frame[col].astype(bool)
        for col in ("hipo_flag", "promotion_eligible", "acting_appointment"):
            emp[col] = emp[col].astype(bool)
        emp["role_level"] = emp["role_level"].astype(int)
        emp["tenure_months"] = emp["tenure_months"].astype(int)

        return {
            "employees": emp,
            "attrition_log": attrition,
            "engagement": engagement,
            "performance": performance,
        }


# =============================================================================
# OUTPUT AND VALIDATION
# =============================================================================

DATE_COLUMNS = {
    "employees": ["hire_date", "exit_date"],
    "attrition_log": ["exit_date"],
    "engagement": ["survey_date"],
    "performance": ["review_date"],
}


def write_scenario(frames: dict[str, pd.DataFrame], out_dir: pathlib.Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, frame in frames.items():
        frame = frame.copy()
        for col in DATE_COLUMNS[name]:
            frame[col] = pd.to_datetime(frame[col]).dt.strftime("%Y-%m-%d")
        frame.to_csv(out_dir / f"{name}.csv", index=False)


def report(
    scenario: Scenario,
    frames: dict[str, pd.DataFrame],
    src: dict[str, pd.DataFrame],
    sim: Simulator,
    out_dir: pathlib.Path,
) -> None:
    """Print a summary so the output can be eyeballed. Reports, never exits."""
    rule = "=" * 78
    print(f"\n{rule}\nSCENARIO {scenario.key}: {scenario.label}\n  -> {out_dir}\n{rule}")

    print("\n[1] Row counts (original -> scenario)")
    original = {
        "employees": len(src["employees"]),
        "attrition_log": len(src["attrition"]),
        "engagement": len(src["engagement"]),
        "performance": len(src["performance"]),
    }
    for name, frame in frames.items():
        before = original[name]
        print(f"    {name+'.csv':<20} {before:>7,} -> {len(frame):>7,}  (+{len(frame)-before:,})")

    emp = frames["employees"]
    eng = frames["engagement"].merge(
        emp[["employee_id", "legacy_entity_code"]], on="employee_id", how="left"
    )

    print("\n[2] Response rate by entity by wave (%)")
    rr = eng.pivot_table(
        index="legacy_entity_code", columns="wave_number",
        values="response_flag", aggfunc="mean",
    ) * 100
    print(rr.round(1).to_string(na_rep="  -  "))

    answered = eng[eng["response_flag"]]
    for dim in SCENARIO_DIMENSIONS:
        print(f"\n[3] {dim} mean by entity by wave")
        table = answered.pivot_table(
            index="legacy_entity_code", columns="wave_number", values=dim, aggfunc="mean"
        )
        print(table.round(3).to_string(na_rep="  -  "))

    print("\n[4] Departures in the extended window (2026-01 .. 2026-07)")
    new_exits = frames["attrition_log"][
        frames["attrition_log"]["exit_date"] > WINDOW_END_ORIGINAL
    ].merge(emp[["employee_id", "legacy_entity_code"]], on="employee_id", how="left")
    by_month = new_exits.groupby(
        [new_exits["exit_date"].dt.to_period("M"), "legacy_entity_code"], observed=True
    ).size().unstack(fill_value=0)
    print(by_month.to_string() if not by_month.empty else "    none")
    print(f"    total new departures: {len(new_exits):,}")
    print(f"    replacement hires:    {len(sim.new_hires):,}")
    print(f"    vacancies still open at window end: {sim.unfilled_vacancies:,}")

    # Month-level counts are genuinely Poisson-noisy at these cohort sizes -
    # Entity_C expects ~12 exits a month - so the scenario direction is only
    # legible in the exposure-correct rate over a few months at a time.
    print("\n    Exposure-correct monthly hazard (%), first vs last quarter of the window")
    halves = {
        "2026-01..03": pd.period_range("2026-01", "2026-03", freq="M"),
        "2026-05..07": pd.period_range("2026-05", "2026-07", freq="M"),
    }
    rates: dict[str, dict[str, float]] = {}
    for label, months in halves.items():
        at_risk: dict[str, int] = {}
        left: dict[str, int] = {}
        for month in months:
            when = month.to_timestamp()
            live = emp[
                (emp["hire_date"] <= when)
                & (emp["exit_date"].isna() | (emp["exit_date"] > when))
            ]
            gone = new_exits[new_exits["exit_date"].dt.to_period("M") == month]
            for entity, count in live["legacy_entity_code"].value_counts().items():
                at_risk[entity] = at_risk.get(entity, 0) + int(count)
            for entity, count in gone["legacy_entity_code"].value_counts().items():
                left[entity] = left.get(entity, 0) + int(count)
        rates[label] = {
            entity: left.get(entity, 0) / total * 100
            for entity, total in at_risk.items() if total
        }
    for entity in sorted(set().union(*(r.keys() for r in rates.values()))):
        first = rates["2026-01..03"].get(entity, float("nan"))
        last = rates["2026-05..07"].get(entity, float("nan"))
        base = sim.model.base_hazard.get(entity, float("nan")) * 100
        print(
            f"        {entity:<18} baseline {base:5.3f}  ->  "
            f"Q1 {first:5.3f}  ->  Q3 {last:5.3f}"
        )

    print("\n[5] Attrition rate over the extended window, by cohort")
    anchor = SIM_FIRST_MONTH.to_timestamp()
    at_risk = emp[
        (emp["hire_date"] <= anchor)
        & (emp["exit_date"].isna() | (emp["exit_date"] > anchor))
    ].copy()
    divergent = sim._divergence_flags(at_risk, anchor)
    at_risk = at_risk.assign(
        divergent=divergent.to_numpy(),
        left=at_risk["employee_id"].isin(new_exits["employee_id"]),
    )
    groups = {
        "non-HiPo baseline": ~at_risk["hipo_flag"],
        "HiPo, not divergent": at_risk["hipo_flag"] & ~at_risk["divergent"],
        "HiPo x bottom-40% (divergence cohort)": at_risk["divergent"],
    }
    baseline = at_risk.loc[~at_risk["hipo_flag"], "left"].mean()
    for label, mask in groups.items():
        subset = at_risk.loc[mask]
        if subset.empty:
            continue
        rate = subset["left"].mean()
        rr_value = rate / baseline if baseline else float("nan")
        print(f"    {label:<40} {rate*100:5.2f}%  (n={len(subset):>5,}, RR {rr_value:.2f})")

    print("\n[6] Integrity checks")
    source_ids = set(src["employees"]["employee_id"].astype(str))
    new_ids = {h["employee_id"] for h in sim.new_hires}
    collisions = source_ids & new_ids
    print(f"    new employee_ids: {len(new_ids):,}; collisions with source: {len(collisions)}")
    print(f"    employee_id unique across roster: {emp['employee_id'].is_unique}")

    start_head = len(src["employees"][src["employees"]["status"] == "active"])
    end_head = int((emp["status"] == "active").sum())
    drift = (end_head - start_head) / start_head * 100 if start_head else 0.0
    print(f"    headcount {start_head:,} -> {end_head:,}  ({drift:+.2f}%)")

    orphan_att = ~frames["attrition_log"]["employee_id"].isin(emp["employee_id"])
    orphan_eng = ~frames["engagement"]["employee_id"].isin(emp["employee_id"])
    orphan_perf = ~frames["performance"]["employee_id"].isin(emp["employee_id"])
    print(
        f"    orphan rows: attrition {int(orphan_att.sum())}, "
        f"engagement {int(orphan_eng.sum())}, performance {int(orphan_perf.sum())}"
    )

    departed = emp[emp["status"] == "departed"]
    logged = set(frames["attrition_log"]["employee_id"])
    print(
        f"    departed employees without an attrition row: "
        f"{int((~departed['employee_id'].isin(logged)).sum())}"
    )

    salary_check = frames["attrition_log"].merge(
        emp[["employee_id", "salary"]], on="employee_id", how="left"
    )
    agree = np.isclose(salary_check["salary_at_exit"], salary_check["salary"]).mean()
    print(f"    salary_at_exit == employees.salary: {agree*100:.1f}%")

    new_reviews = frames["performance"][frames["performance"]["review_cycle"] == NEW_REVIEW_CYCLE]
    print(f"    {NEW_REVIEW_CYCLE} reviews written: {len(new_reviews):,}")
    dist = new_reviews["performance_rating"].value_counts(normalize=True)
    base_dist = src["performance"]["performance_rating"].value_counts(normalize=True)
    print("    rating distribution (new vs source):")
    for rating in base_dist.index:
        print(f"        {rating:<20} {dist.get(rating, 0)*100:5.1f}%  vs {base_dist[rating]*100:5.1f}%")


def main() -> None:
    data_dir = find_data_dir()
    print(f"Source (read-only): {data_dir}")
    src = load_source(data_dir)
    model = build_model(src)

    print("\nMeasured baseline monthly hazard "
          f"({HAZARD_CALIBRATION_START} .. {HAZARD_CALIBRATION_END}, exposure-correct):")
    for entity, hazard in sorted(model.base_hazard.items()):
        print(f"    {entity:<18} {hazard*100:.3f}% / month")

    children = np.random.SeedSequence(RANDOM_SEED).spawn(len(SCENARIOS))
    for scenario, child in zip(SCENARIOS, children):
        sim = Simulator(scenario, src, model, child)
        frames = sim.run()
        out_dir = OUTPUT_ROOT / scenario.out_dir
        write_scenario(frames, out_dir)
        report(scenario, frames, src, sim, out_dir)

    print(
        "\n"
        + "=" * 78
        + "\nSYNTHETIC DATA - illustrative only, generated for the monitoring demo."
        "\nRows dated after "
        f"{WINDOW_END_ORIGINAL:%Y-%m-%d} are simulated and are not evidence about"
        "\nNovaCorp. Any dashboard view built on these folders must say so on screen."
        "\nSee SCENARIO_NOTES.md for assumptions, parameters and the random seed.\n"
        + "=" * 78
    )


if __name__ == "__main__":
    main()
