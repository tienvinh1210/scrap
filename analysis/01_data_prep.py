"""
Data preparation for the NovaCorp People Analytics Challenge.

POPULATION DECISIONS (documented per the brief's explicit instruction to justify
population choices):

1. ORG SNAPSHOT population = active employees only (n=12,003). Used whenever we
   describe "who works at NovaCorp today" (headcount mix, department composition,
   compa-ratio, promotion pipeline).

2. ATTRITION-RISK population = full roster (active + departed, n=13,403), i.e.
   everyone on payroll at any point in the Jan-2024 to Dec-2025 observation window.
   Used as the denominator for attrition rates, since departed employees were part
   of the workforce-at-risk before they left. We compute an average-headcount
   denominator (mean of month-start headcounts) rather than dividing by the
   end-of-window active count, which would overstate attrition rates.

3. EARLY-TENURE / HIRING population = employees hired during the window
   (2024-01-01 onward), regardless of current status. Used for hiring-channel and
   days-to-fill analysis, since pre-window hires have no comparable "days_to_fill"
   context for the window's hiring practices.

4. ENGAGEMENT-TREND population = employees with >=2 engagement waves (responded or
   issued) so a trend/trajectory can be computed. Employees with 0-1 waves (new
   joiners, near-window-edge leavers) are excluded from trend analysis but retained
   in point-in-time (single-wave) analysis.

5. Fields treated as retrospective HR judgement, not ground truth (per brief):
   stated_exit_reason, regrettable_flag, performance_band_at_exit. These are used
   as one input signal, always triangulated against engagement/performance
   trajectories rather than taken at face value.

6. response_flag == False rows in engagement.csv are RETAINED (not dropped). Non-
   response is treated as a potential disengagement signal in its own right.
"""
import pandas as pd
import numpy as np

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 50)

WINDOW_START = pd.Timestamp("2024-01-01")
WINDOW_END = pd.Timestamp("2025-12-31")

# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------
emp = pd.read_csv("employees.csv", parse_dates=["hire_date", "exit_date"])
attr = pd.read_csv("attrition_log.csv", parse_dates=["exit_date"])
eng = pd.read_csv("engagement.csv", parse_dates=["survey_date"])
perf = pd.read_csv("performance.csv", parse_dates=["review_date"])

# ---------------------------------------------------------------------------
# Merge attrition_log detail onto employees (1:1 for departed employees)
# ---------------------------------------------------------------------------
attr_cols = attr.drop(columns=["exit_date"]).rename(
    columns={"employee_id": "employee_id"}
)
master = emp.merge(attr_cols, on="employee_id", how="left")

master["is_departed"] = master["status"] == "departed"
master["is_voluntary"] = master["exit_type"] == "voluntary"
master["is_involuntary"] = master["exit_type"] == "involuntary"
master["is_regrettable"] = master["regrettable_flag"] == True  # noqa: E712 (NaN-safe bool coercion)
master["is_pull"] = master["pathway"] == "pull"
master["is_push"] = master["pathway"] == "push"

# Early-tenure exit: departed within 12 months of hire -> hiring-inefficiency signal
master["early_exit_12mo"] = master["is_departed"] & (master["tenure_months"] <= 12)

# Hired during the observation window (for hiring-channel effectiveness analysis)
master["hired_in_window"] = master["hire_date"] >= WINDOW_START

# Senior / high-value flag used for "regrettable attrition" cost targeting:
# role_level >= 3 (Senior Manager and above) OR hipo_flag True
master["is_high_value"] = (master["role_level"] >= 3) | (master["hipo_flag"])

# ---------------------------------------------------------------------------
# Engagement: employee-level summary (mean scores, trend, non-response)
# ---------------------------------------------------------------------------
score_cols = [
    "manager_effectiveness", "psychological_safety", "recognition",
    "career_development", "senior_leadership_trust", "purpose_meaning",
    "wellbeing", "confidence_in_role_future",
]
eng["engagement_composite"] = eng[score_cols].mean(axis=1)

eng_summary = eng.groupby("employee_id").agg(
    waves_issued=("wave_number", "count"),
    waves_responded=("response_flag", "sum"),
    avg_engagement=("engagement_composite", "mean"),
    avg_manager_effectiveness=("manager_effectiveness", "mean"),
    avg_psych_safety=("psychological_safety", "mean"),
    avg_recognition=("recognition", "mean"),
    avg_career_dev=("career_development", "mean"),
    avg_leadership_trust=("senior_leadership_trust", "mean"),
    avg_purpose=("purpose_meaning", "mean"),
    avg_wellbeing=("wellbeing", "mean"),
    avg_confidence_future=("confidence_in_role_future", "mean"),
).reset_index()
eng_summary["response_rate"] = eng_summary["waves_responded"] / eng_summary["waves_issued"]

# Trend: last responded wave composite minus first responded wave composite
responded = eng[eng["response_flag"]].sort_values(["employee_id", "wave_number"])
first_last = responded.groupby("employee_id").agg(
    first_wave=("wave_number", "first"),
    first_score=("engagement_composite", "first"),
    last_wave=("wave_number", "last"),
    last_score=("engagement_composite", "last"),
    n_responses=("wave_number", "count"),
).reset_index()
first_last["engagement_trend"] = np.where(
    first_last["n_responses"] >= 2,
    first_last["last_score"] - first_last["first_score"],
    np.nan,
)
eng_summary = eng_summary.merge(
    first_last[["employee_id", "engagement_trend", "n_responses"]], on="employee_id", how="left"
)

# Most-recent-wave-before-exit composite (for departed employees) — signal of
# state of mind close to departure, using only responded surveys
eng_resp_sorted = eng[eng["response_flag"]].sort_values(["employee_id", "survey_date"])
last_score_overall = eng_resp_sorted.groupby("employee_id").last()[["engagement_composite", "survey_date"]]
last_score_overall = last_score_overall.rename(
    columns={"engagement_composite": "final_engagement_score", "survey_date": "final_engagement_date"}
).reset_index()
eng_summary = eng_summary.merge(last_score_overall, on="employee_id", how="left")

# ---------------------------------------------------------------------------
# Performance: employee-level summary (most recent rating, trend, promo signal)
# ---------------------------------------------------------------------------
rating_order = {
    "Unsatisfactory": 1, "Below Expectations": 2, "Meets Expectations": 3,
    "High Performer": 4, "Outstanding": 5,
}
perf["rating_score"] = perf["performance_rating"].map(rating_order)
perf_sorted = perf.sort_values(["employee_id", "review_date"])

perf_summary = perf_sorted.groupby("employee_id").agg(
    n_reviews=("review_date", "count"),
    avg_rating_score=("rating_score", "mean"),
    avg_goal_score=("goal_achievement_score", "mean"),
    any_promo_recommended=("promotion_recommendation", "any"),
    n_promo_recommended=("promotion_recommendation", "sum"),
).reset_index()

latest_perf = perf_sorted.groupby("employee_id").last()[["performance_rating", "rating_score", "review_cycle"]]
latest_perf = latest_perf.rename(
    columns={"performance_rating": "latest_rating", "rating_score": "latest_rating_score", "review_cycle": "latest_review_cycle"}
).reset_index()
perf_summary = perf_summary.merge(latest_perf, on="employee_id", how="left")

first_perf = perf_sorted.groupby("employee_id").first()[["rating_score"]].rename(
    columns={"rating_score": "first_rating_score"}
).reset_index()
perf_summary = perf_summary.merge(first_perf, on="employee_id", how="left")
perf_summary["rating_trend"] = np.where(
    perf_summary["n_reviews"] >= 2,
    perf_summary["latest_rating_score"] - perf_summary["first_rating_score"],
    np.nan,
)

# ---------------------------------------------------------------------------
# Assemble full analytical master table
# ---------------------------------------------------------------------------
master = master.merge(eng_summary, on="employee_id", how="left")
master = master.merge(perf_summary, on="employee_id", how="left")

# High-value + disengaged flag (composite below 3.0 on a 1-5 scale = disengaged)
DISENGAGED_THRESHOLD = 3.0
master["is_disengaged"] = master["avg_engagement"] < DISENGAGED_THRESHOLD
master["is_persistently_disengaged"] = (
    (master["avg_engagement"] < DISENGAGED_THRESHOLD) & (master["n_responses"].fillna(0) >= 2)
)

# ---------------------------------------------------------------------------
# Monthly headcount panel -> average headcount denominator for attrition rates
# ---------------------------------------------------------------------------
months = pd.date_range(WINDOW_START, WINDOW_END, freq="MS")
headcounts = []
for m in months:
    month_end = m + pd.offsets.MonthEnd(0)
    active_at_month = ((emp["hire_date"] <= month_end) & (emp["exit_date"].isnull() | (emp["exit_date"] >= m)))
    headcounts.append({"month": m, "headcount": active_at_month.sum()})
hc_df = pd.DataFrame(headcounts)
avg_headcount = hc_df["headcount"].mean()

print(f"Average monthly headcount across window: {avg_headcount:,.0f}")
print(f"End-of-window active headcount: {(emp['status']=='active').sum():,}")

# ---------------------------------------------------------------------------
# Save outputs
# ---------------------------------------------------------------------------
master.to_csv("output/tables/employee_master.csv", index=False)
hc_df.to_csv("output/tables/monthly_headcount.csv", index=False)

attr["exit_year"] = attr["exit_date"].dt.year
yearly_vol = attr[attr.exit_type == "voluntary"].groupby("exit_year").size()
yearly_hc = hc_df.copy()
yearly_hc["year"] = yearly_hc["month"].dt.year
yearly_avg_hc = yearly_hc.groupby("year")["headcount"].mean()

with open("output/tables/population_summary.txt", "w") as f:
    f.write(f"Average monthly headcount (window): {avg_headcount:,.1f}\n")
    f.write(f"End-of-window active headcount: {(emp['status']=='active').sum():,}\n")
    f.write(f"Total roster in window (active+departed): {len(emp):,}\n")
    f.write(f"Total departures logged: {len(attr):,}\n")
    f.write(f"  Voluntary: {(attr.exit_type=='voluntary').sum():,}\n")
    f.write(f"  Involuntary: {(attr.exit_type=='involuntary').sum():,}\n")
    f.write(f"  Regrettable (HR flag): {(attr.regrettable_flag).sum():,}\n")
    f.write(f"Observation window: {WINDOW_START.date()} to {WINDOW_END.date()} ({(WINDOW_END-WINDOW_START).days/365.25:.2f} years)\n")
    f.write("\nYear-by-year voluntary attrition rate (dataset-derived):\n")
    for yr in sorted(yearly_avg_hc.index):
        vol = yearly_vol.get(yr, 0)
        avghc = yearly_avg_hc[yr]
        f.write(f"  {yr}: {vol} voluntary exits / {avghc:,.0f} avg headcount = {vol/avghc*100:.2f}%\n")
    f.write("\nNote: Annual Report FY2025 states voluntary attrition of 10.4% (FY2024: 10.9%).\n")
    f.write("The dataset-derived rate above may differ from the Annual Report headline figure.\n")
    f.write("Per the Case Brief, the CSV datasets (not the Annual Report) are the analytical\n")
    f.write("ground truth for this challenge; the Annual Report is used only for qualitative\n")
    f.write("narrative context (e.g. Entity_B risk, Risk & Compliance/FAR pressure). This\n")
    f.write("discrepancy is documented as an explicit limitation in the final deck.\n")

print("Saved output/tables/employee_master.csv, monthly_headcount.csv, population_summary.txt")
print("\nMaster shape:", master.shape)
print("\nColumns:", list(master.columns))
