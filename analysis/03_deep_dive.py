"""
Deep-dive to cross-validate and sharpen the top candidate root causes:
  1. Entity_B integration + Risk & Compliance concentration of high-value attrition
  2. Compensation (compa_ratio) as a compounding accelerant within Entity_B / Risk & Compliance
  3. The "stay but disengaged" population (disengagement productivity loss)
  4. Hiring channel efficiency (agency overuse)
  5. Quick equity/ethics sanity checks (gender pay & attrition, to pre-empt Q&A)
"""
import pandas as pd
import numpy as np

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 50)

m = pd.read_csv("output/tables/employee_master.csv", parse_dates=["hire_date", "exit_date"])
out = open("output/tables/03_deep_dive_results.txt", "w")
def w(*a):
    s = " ".join(str(x) for x in a)
    print(s); out.write(s + "\n")

hv = m[m.is_high_value].copy()

w("=" * 90)
w("A. COMPENSATION HARMONISATION GAP: is Entity_B underpaid relative to NovaCorp-Origin at same level?")
w("=" * 90)
comp_by_entity_level = m.groupby(["role_level", "legacy_entity_code"])["compa_ratio"].mean().unstack()
w(comp_by_entity_level.round(3))
w("\nOverall mean compa_ratio by entity:")
w(m.groupby("legacy_entity_code")["compa_ratio"].mean().round(3))
w("\nShare of employees with compa_ratio < 0.85 by entity:")
w((m.groupby("legacy_entity_code")["compa_ratio"].apply(lambda s: (s < 0.85).mean()) * 100).round(1))
w("\nHigh-value population only - underpaid share by entity:")
w((hv.groupby("legacy_entity_code")["compa_ratio"].apply(lambda s: (s < 0.85).mean()) * 100).round(1))

w("\n" + "=" * 90)
w("B. TRIPLE INTERSECTION: Entity_B x Risk & Compliance x underpaid -> regrettable attrition")
w("=" * 90)
rb_e = m[(m.department == "Risk & Compliance")]
w("Risk & Compliance headcount by entity:")
w(rb_e.legacy_entity_code.value_counts())
w("\nRisk & Compliance attrition rate by entity (all levels):")
g = rb_e.groupby("legacy_entity_code").agg(headcount=("employee_id","count"), departed=("is_departed","sum"), regrettable=("is_regrettable","sum"))
g["attr_%"] = (g.departed/g.headcount*100).round(1)
g["regret_%"] = (g.regrettable/g.headcount*100).round(1)
w(g)

rb_e_hv = hv[hv.department == "Risk & Compliance"]
w("\nRisk & Compliance HIGH-VALUE headcount & attrition by entity:")
g2 = rb_e_hv.groupby("legacy_entity_code").agg(headcount=("employee_id","count"), departed=("is_departed","sum"), regrettable=("is_regrettable","sum"), avg_compa=("compa_ratio","mean"))
g2["attr_%"] = (g2.departed/g2.headcount*100).round(1)
w(g2.round(2))

w("\nRisk & Compliance high-value role_level>=4 (Director+) specifically (annual report flags L4 Director attrition):")
rb_dir = hv[(hv.department == "Risk & Compliance") & (hv.role_level >= 4)]
w(f"  headcount={len(rb_dir)}, departed={rb_dir.is_departed.sum()}, rate={rb_dir.is_departed.mean()*100:.1f}%")
w(rb_dir.groupby("legacy_entity_code")["is_departed"].agg(["count","sum","mean"]))

w("\n" + "=" * 90)
w("C. DISENGAGEMENT: career_development dimension for stalled vs promoted; disengaged-but-staying detail")
w("=" * 90)
active = m[m.status == "active"].copy()
stalled = active[(active.promotion_eligible == True) & (active.any_promo_recommended == False)]
promoted_elig = active[(active.promotion_eligible == True) & (active.any_promo_recommended == True)]
w("avg_career_dev: stalled vs promoted-eligible:")
w(f"  stalled: {stalled.avg_career_dev.mean():.3f}   promoted: {promoted_elig.avg_career_dev.mean():.3f}")
w("avg_confidence_future: stalled vs promoted-eligible:")
w(f"  stalled: {stalled.avg_confidence_future.mean():.3f}   promoted: {promoted_elig.avg_confidence_future.mean():.3f}")

w("\nPersistently disengaged ACTIVE employees: avg tenure, avg goal_achievement_score vs engaged actives")
engaged_active = active[~active.is_persistently_disengaged]
disengaged_active = active[active.is_persistently_disengaged]
w(f"  Disengaged active (n={len(disengaged_active)}): avg tenure_months={disengaged_active.tenure_months.mean():.1f}, avg_goal_score={disengaged_active.avg_goal_score.mean():.1f}, avg salary=${disengaged_active.salary.mean():,.0f}")
w(f"  Engaged active   (n={len(engaged_active)}): avg tenure_months={engaged_active.tenure_months.mean():.1f}, avg_goal_score={engaged_active.avg_goal_score.mean():.1f}, avg salary=${engaged_active.salary.mean():,.0f}")

w("\nGoal achievement score gap (productivity proxy) disengaged vs engaged, t-test:")
from scipy import stats
t, p = stats.ttest_ind(disengaged_active.avg_goal_score.dropna(), engaged_active.avg_goal_score.dropna(), equal_var=False)
w(f"  t={t:.2f}, p={p:.4f}, mean diff = {engaged_active.avg_goal_score.mean() - disengaged_active.avg_goal_score.mean():.2f} pts")

w("\nNon-response rate as early-warning signal - logistic-style simple check (voluntary exit rate by response_rate quartile):")
active_and_departed_with_resp = m[m.response_rate.notnull()].copy()
active_and_departed_with_resp["resp_quartile"] = pd.qcut(active_and_departed_with_resp.response_rate, 4, duplicates="drop")
w(active_and_departed_with_resp.groupby("resp_quartile")["is_voluntary"].mean().round(3) * 100)

w("\n" + "=" * 90)
w("D. HIRING CHANNEL: full-population (not just in-window) comparison, and graduate channel")
w("=" * 90)
w("\nFull-population early exit (<=12mo tenure among ALL hires, not just in-window) by hire_source:")
g3 = m.groupby("hire_source").agg(headcount=("employee_id","count"), early_exit=("early_exit_12mo","sum"))
g3["early_exit_rate_%"] = (g3.early_exit/g3.headcount*100).round(2)
w(g3)
w("\nGraduate channel profile: role_level distribution, avg tenure, attrition rate")
grad = m[m.hire_source == "graduate"]
w(grad.role_level.value_counts())
w(f"avg tenure_months: {grad.tenure_months.mean():.1f}, attrition rate: {grad.is_departed.mean()*100:.1f}%")
w("\nAgency vs Direct vs Referral: avg salary at hire (proxy = salary), avg days_to_fill, early_exit_rate - all non-acquisition")
non_acq = m[m.hire_source.isin(["agency","direct","referral","graduate"])]
g4 = non_acq.groupby("hire_source").agg(headcount=("employee_id","count"), avg_salary=("salary","mean"), avg_days_to_fill=("days_to_fill","mean"), early_exit_rate=("early_exit_12mo","mean"))
w(g4.round(1))

w("\n" + "=" * 90)
w("E. EQUITY / ETHICS SANITY CHECKS (gender pay & attrition, to pre-empt Q&A)")
w("=" * 90)
w("\nHeadcount and compa_ratio by gender:")
w(m.groupby("gender").agg(headcount=("employee_id","count"), avg_salary=("salary","mean"), avg_compa=("compa_ratio","mean")).round(2))
w("\nRepresentation by gender at role_level >= 5 (senior exec):")
w(m[m.role_level>=5].gender.value_counts(normalize=True).round(3)*100)
w("\nAttrition rate by gender:")
w(m.groupby("gender")["is_departed"].mean().round(3)*100)
w("\nHigh-value attrition by gender:")
w(hv.groupby("gender")["is_departed"].mean().round(3)*100)
w("\ncompa_ratio by gender within same role_level (checking like-for-like pay gap):")
w(m.groupby(["role_level","gender"])["compa_ratio"].mean().unstack().round(3))

out.close()
print("\nSaved output/tables/03_deep_dive_results.txt")
