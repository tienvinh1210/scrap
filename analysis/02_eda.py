"""
Exploratory analysis across the merged employee master table.
Surfaces attrition, engagement, performance and hiring patterns by
department / role / tenure / legacy entity / manager, to identify
candidate root causes for the $42M cost estimate.
"""
import pandas as pd
import numpy as np

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 50)

m = pd.read_csv("output/tables/employee_master.csv", parse_dates=["hire_date", "exit_date"])

out = open("output/tables/02_eda_results.txt", "w")
def w(*args):
    s = " ".join(str(a) for a in args)
    print(s)
    out.write(s + "\n")

w("=" * 90)
w("1. ATTRITION BY SEGMENT (rate = departed / (departed+active) within segment, 2yr window)")
w("=" * 90)

def attrition_rate_table(df, groupcol):
    g = df.groupby(groupcol).agg(
        headcount=("employee_id", "count"),
        departed=("is_departed", "sum"),
        voluntary=("is_voluntary", "sum"),
        regrettable=("is_regrettable", "sum"),
    )
    g["attrition_rate_%"] = (g["departed"] / g["headcount"] * 100).round(1)
    g["voluntary_rate_%"] = (g["voluntary"] / g["headcount"] * 100).round(1)
    g["regrettable_rate_%"] = (g["regrettable"] / g["headcount"] * 100).round(1)
    return g.sort_values("attrition_rate_%", ascending=False)

for col in ["department", "role_family", "legacy_entity_code", "contract_type", "hire_source"]:
    w(f"\n--- by {col} ---")
    w(attrition_rate_table(m, col))

w("\n--- by role_level ---")
w(attrition_rate_table(m, "role_level"))

w("\n--- department x legacy_entity_code (headcount) ---")
w(pd.crosstab(m.department, m.legacy_entity_code))

w("\n--- department x legacy_entity_code (attrition rate %) ---")
ct_hc = pd.crosstab(m.department, m.legacy_entity_code)
ct_dep = pd.crosstab(m.department, m.legacy_entity_code, values=m.is_departed, aggfunc="sum")
w((ct_dep / ct_hc * 100).round(1))

w("\n" + "=" * 90)
w("2. HIGH-VALUE (senior L3+/HiPo) ATTRITION - the 'regrettable attrition' cost driver")
w("=" * 90)
hv = m[m.is_high_value]
w(f"High-value population: {len(hv)} ({len(hv)/len(m)*100:.1f}% of workforce)")
w(f"High-value departed: {hv.is_departed.sum()} ({hv.is_departed.mean()*100:.1f}% attrition rate)")
w(f"vs overall attrition rate: {m.is_departed.mean()*100:.1f}%")
w("\nHigh-value attrition by department:")
w(attrition_rate_table(hv, "department"))
w("\nHigh-value attrition by legacy_entity_code:")
w(attrition_rate_table(hv, "legacy_entity_code"))
w("\nHigh-value voluntary departed -> pathway split (push vs pull):")
hv_dep = hv[hv.is_departed]
w(hv_dep["pathway"].value_counts())
w("\nHigh-value voluntary departed -> performance_band_at_exit:")
w(hv_dep[hv_dep.is_voluntary]["performance_band_at_exit"].value_counts())
w("\nHigh-value voluntary departed -> avg engagement score (final) vs stayed high-value:")
w(f"  Departed (voluntary) avg final_engagement_score: {hv_dep[hv_dep.is_voluntary]['final_engagement_score'].mean():.2f}")
w(f"  Stayed (active) avg avg_engagement: {hv[hv.status=='active']['avg_engagement'].mean():.2f}")

w("\n" + "=" * 90)
w("3. COMPENSATION - compa_ratio vs attrition (pay-driven regrettable attrition?)")
w("=" * 90)
m["compa_band"] = pd.cut(m.compa_ratio, bins=[0, 0.85, 0.95, 1.05, 2], labels=["<0.85 (underpaid)", "0.85-0.95", "0.95-1.05", ">1.05"])
w(attrition_rate_table(m, "compa_band"))
hv = m[m.is_high_value]  # refresh view to pick up compa_band column
w("\nHigh-value only:")
w(attrition_rate_table(hv, "compa_band"))
w("\nCorrelation compa_ratio vs is_voluntary (high-value pop):")
w(hv[["compa_ratio", "is_voluntary"]].corr())

w("\n" + "=" * 90)
w("4. ENGAGEMENT vs ATTRITION - does engagement predict voluntary exit?")
w("=" * 90)
w("\nAvg engagement score: active vs voluntary-departed vs involuntary-departed")
for grp, label in [("active", "active"), (None, "voluntary departed"), (None, "involuntary departed")]:
    pass
active_eng = m.loc[m.status == "active", "avg_engagement"].mean()
vol_eng = m.loc[m.is_voluntary == True, "final_engagement_score"].mean()
invol_eng = m.loc[m.is_involuntary == True, "final_engagement_score"].mean()
w(f"  Active employees avg_engagement (all waves): {active_eng:.2f}")
w(f"  Voluntary leavers final_engagement_score (last completed survey): {vol_eng:.2f}")
w(f"  Involuntary leavers final_engagement_score: {invol_eng:.2f}")

w("\nEngagement trend (last-first wave) for voluntary leavers vs active:")
w(f"  Active mean trend: {m.loc[m.status=='active','engagement_trend'].mean():.3f}")
w(f"  Voluntary leavers mean trend: {m.loc[m.is_voluntary==True,'engagement_trend'].mean():.3f}")

w("\nDisengagement rate (avg_engagement < 3.0) by status:")
w(m.groupby("status")["is_disengaged"].mean())
w("\nPersistent disengagement (>=2 responses, avg<3.0) headcount & rate among ACTIVE employees:")
active = m[m.status == "active"]
w(f"  Persistently disengaged active headcount: {active.is_persistently_disengaged.sum()}")
w(f"  Rate: {active.is_persistently_disengaged.mean()*100:.1f}%")
w("\nPersistently disengaged ACTIVE employees by department:")
w(active.groupby("department")["is_persistently_disengaged"].agg(["sum", "mean"]))

w("\nNon-response rate (waves issued but not completed) vs voluntary attrition:")
m["low_response_rate"] = m["response_rate"] < 0.6
w(pd.crosstab(m["low_response_rate"], m["is_voluntary"], normalize="index"))

w("\nEngagement dimension breakdown - active vs voluntary leavers (mean of each dimension):")
dims = ["avg_manager_effectiveness", "avg_psych_safety", "avg_recognition", "avg_career_dev",
        "avg_leadership_trust", "avg_purpose", "avg_wellbeing", "avg_confidence_future"]
comp = pd.DataFrame({
    "active": m.loc[m.status == "active", dims].mean(),
    "voluntary_leavers": m.loc[m.is_voluntary == True, dims].mean(),
})
comp["gap"] = comp["active"] - comp["voluntary_leavers"]
w(comp.sort_values("gap", ascending=False))

w("\n" + "=" * 90)
w("5. PERFORMANCE vs ATTRITION - are we losing high performers?")
w("=" * 90)
w("\nLatest performance rating distribution: active vs voluntary leavers")
w(pd.crosstab(m["status"], m["latest_rating"], normalize="index").round(3) * 100)
w("\nAmong voluntary leavers, performance_band_at_exit distribution:")
w(m.loc[m.is_voluntary == True, "performance_band_at_exit"].value_counts(normalize=True).round(3) * 100)
w("\nTop-performer (Outstanding/High Performer at latest review) attrition rate vs others:")
m["is_top_performer"] = m["latest_rating"].isin(["Outstanding", "High Performer"])
w(attrition_rate_table(m.dropna(subset=["latest_rating"]), "is_top_performer"))

w("\nPromotion pipeline: promotion_eligible vs actually promoted (any_promo_recommended) among ACTIVE:")
w(active.groupby("promotion_eligible")["any_promo_recommended"].mean())
w("\nEligible-but-never-recommended (stalled) active headcount:")
stalled = active[(active.promotion_eligible == True) & (active.any_promo_recommended == False)]
w(f"  {len(stalled)} of {active.promotion_eligible.sum()} eligible ({len(stalled)/max(active.promotion_eligible.sum(),1)*100:.1f}%)")
w("\nStalled-eligible avg_engagement vs promoted-eligible avg_engagement:")
promoted_elig = active[(active.promotion_eligible == True) & (active.any_promo_recommended == True)]
w(f"  Stalled: {stalled.avg_engagement.mean():.2f}   Promoted: {promoted_elig.avg_engagement.mean():.2f}")

w("\n" + "=" * 90)
w("6. HIRING INEFFICIENCY - agency vs other channels")
w("=" * 90)
w("\ndays_to_fill by hire_source:")
w(m.groupby("hire_source")["days_to_fill"].agg(["mean", "median", "count"]))
w("\nEarly exit (<=12mo tenure) rate by hire_source (hired in window only):")
hired_window = m[m.hired_in_window]
w(attrition_rate_table(hired_window, "hire_source")[["headcount", "departed"]])
early_by_source = hired_window.groupby("hire_source")["early_exit_12mo"].agg(["sum", "count", "mean"])
w(early_by_source)
w("\nAgency hires as % of total hires (in window) by department:")
w(pd.crosstab(hired_window.department, hired_window.hire_source, normalize="index").round(3) * 100)

w("\n" + "=" * 90)
w("7. MANAGER-LEVEL ATTRITION CLUSTERING")
w("=" * 90)
mgr_stats = m.groupby("manager_id").agg(
    team_size=("employee_id", "count"),
    departed=("is_departed", "sum"),
    voluntary=("is_voluntary", "sum"),
    avg_team_engagement=("avg_engagement", "mean"),
).reset_index()
mgr_stats = mgr_stats[mgr_stats.team_size >= 5]
mgr_stats["attrition_rate"] = mgr_stats["departed"] / mgr_stats["team_size"]
w(f"Managers with >=5 reports: {len(mgr_stats)}")
w(f"Managers with 0 attrition: {(mgr_stats.attrition_rate==0).sum()} ({(mgr_stats.attrition_rate==0).mean()*100:.1f}%)")
w(f"Median team attrition rate: {mgr_stats.attrition_rate.median()*100:.1f}%")
w(f"90th pctile team attrition rate: {mgr_stats.attrition_rate.quantile(0.9)*100:.1f}%")
high_attr_mgrs = mgr_stats[mgr_stats.attrition_rate >= mgr_stats.attrition_rate.quantile(0.9)]
w(f"\nTop-decile-attrition managers (n={len(high_attr_mgrs)}): avg team engagement = {high_attr_mgrs.avg_team_engagement.mean():.2f}")
low_attr_mgrs = mgr_stats[mgr_stats.attrition_rate == 0]
w(f"Zero-attrition managers (n={len(low_attr_mgrs)}): avg team engagement = {low_attr_mgrs.avg_team_engagement.mean():.2f}")
w("\nCorrelation: manager avg_team_engagement vs attrition_rate")
w(mgr_stats[["avg_team_engagement", "attrition_rate"]].corr())

out.close()
print("\nSaved output/tables/02_eda_results.txt")
