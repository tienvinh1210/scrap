"""
Financial quantification of the three cost buckets using Finance's benchmark
constants, applied bottom-up to the datasets, and specifically to the three
root-cause cohorts identified in the deep-dive:

  1. Entity_B integration failure (leadership trust / purpose collapse) -> regrettable attrition
  2. Risk & Compliance senior/director talent poaching (NovaCorp-Origin veterans) -> regrettable attrition
  3. Persistent disengagement among ACTIVE staff (stay-but-disengaged) -> productivity loss
  (4. Agency hiring channel overuse -> hiring inefficiency, secondary/quick-win)

Benchmark constants (from Case Brief Section 6):
  Replacement cost multiplier   = 1.5x annual base salary
  Backfill rate                 = 85% of vacated positions filled
  Disengagement productivity loss = 15% of base salary per year
  Superannuation on-cost        = 12.0% of base salary
  Agency fee rate               = 18% of first-year base salary
  Direct hire benchmark         = $5,500 per hire (fully loaded)
"""
import pandas as pd
import numpy as np

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 50)

REPL_MULT = 1.5
BACKFILL_RATE = 0.85
DISENGAGEMENT_LOSS_RATE = 0.15
SUPER_ONCOST = 0.12
AGENCY_FEE_RATE = 0.18
DIRECT_HIRE_COST = 5500

m = pd.read_csv("output/tables/employee_master.csv", low_memory=False, parse_dates=["hire_date", "exit_date"])
attr = pd.read_csv("attrition_log.csv", parse_dates=["exit_date"])

out = open("output/tables/04_financial_model_results.txt", "w")
def w(*a):
    s = " ".join(str(x) for x in a)
    print(s); out.write(s + "\n")

def loaded(salary):
    return salary * (1 + SUPER_ONCOST)

WINDOW_YEARS = 2.0

w("=" * 90)
w("COMPONENT 1: REGRETTABLE ATTRITION (Finance estimate: $22-25M/yr)")
w("=" * 90)

# HR's own regrettable flag, annualised (window = 2 years)
regret = m[m.is_regrettable]
regret_cost_total_2yr = (loaded(regret["salary_at_exit"]) * REPL_MULT * BACKFILL_RATE).sum()
regret_cost_annual = regret_cost_total_2yr / WINDOW_YEARS
w(f"HR-flagged regrettable departures: {len(regret)} over {WINDOW_YEARS:.0f} years")
w(f"  Total loaded salary at exit: ${loaded(regret['salary_at_exit']).sum():,.0f}")
w(f"  Replacement cost (x{REPL_MULT}, backfill {BACKFILL_RATE:.0%}), 2yr total: ${regret_cost_total_2yr:,.0f}")
w(f"  ANNUALISED regrettable attrition cost: ${regret_cost_annual:,.0f}")
w(f"  vs Finance estimate range: $22-25M")

w("\n--- Sub-cohort A: Entity_B voluntary high-value departures (leadership-trust driven) ---")
eb_hv_dep = m[(m.legacy_entity_code == "Entity_B") & (m.is_high_value) & (m.is_voluntary == True)]
eb_cost_2yr = (loaded(eb_hv_dep["salary_at_exit"]) * REPL_MULT * BACKFILL_RATE).sum()
w(f"  Headcount: {len(eb_hv_dep)}  |  Avg salary: ${eb_hv_dep['salary_at_exit'].mean():,.0f}")
w(f"  2yr replacement cost: ${eb_cost_2yr:,.0f}  |  Annualised: ${eb_cost_2yr/WINDOW_YEARS:,.0f}")
w(f"  Of which HR-flagged 'regrettable': {eb_hv_dep.is_regrettable.sum()}")

w("\n--- Sub-cohort B: Risk & Compliance Director+(L4+) NovaCorp-Origin departures (talent poaching) ---")
rc_dir = m[(m.department == "Risk & Compliance") & (m.role_level >= 4) & (m.legacy_entity_code == "NovaCorp-Origin") & (m.is_departed)]
rc_cost_2yr = (loaded(rc_dir["salary_at_exit"]) * REPL_MULT * BACKFILL_RATE).sum()
w(f"  Headcount: {len(rc_dir)}  |  Avg salary: ${rc_dir['salary_at_exit'].mean():,.0f}")
w(f"  2yr replacement cost: ${rc_cost_2yr:,.0f}  |  Annualised: ${rc_cost_2yr/WINDOW_YEARS:,.0f}")

w("\n--- All high-value (L3+/HiPo) voluntary departures, company-wide, for reference ---")
hv_vol = m[(m.is_high_value) & (m.is_voluntary == True)]
hv_cost_2yr = (loaded(hv_vol["salary_at_exit"]) * REPL_MULT * BACKFILL_RATE).sum()
w(f"  Headcount: {len(hv_vol)}  |  2yr cost: ${hv_cost_2yr:,.0f}  |  Annualised: ${hv_cost_2yr/WINDOW_YEARS:,.0f}")

w("\n--- All voluntary departures, company-wide (upper bound reference) ---")
all_vol = m[m.is_voluntary == True]
allvol_cost_2yr = (loaded(all_vol["salary_at_exit"]) * REPL_MULT * BACKFILL_RATE).sum()
w(f"  Headcount: {len(all_vol)}  |  2yr cost: ${allvol_cost_2yr:,.0f}  |  Annualised: ${allvol_cost_2yr/WINDOW_YEARS:,.0f}")

w("\n" + "=" * 90)
w("COMPONENT 2: DISENGAGEMENT-DRIVEN PRODUCTIVITY LOSS (Finance estimate: $12-15M/yr)")
w("=" * 90)
active = m[m.status == "active"]
disengaged_active = active[active.is_persistently_disengaged]
loss_annual = (loaded(disengaged_active["salary"]) * DISENGAGEMENT_LOSS_RATE).sum()
w(f"Persistently disengaged ACTIVE headcount: {len(disengaged_active)} ({len(disengaged_active)/len(active)*100:.1f}% of active workforce)")
w(f"  Avg loaded salary: ${loaded(disengaged_active['salary']).mean():,.0f}")
w(f"  ANNUAL productivity loss ({DISENGAGEMENT_LOSS_RATE:.0%} of loaded salary): ${loss_annual:,.0f}")
w(f"  vs Finance estimate range: $12-15M")

w("\nBreakdown by department (headcount, cost):")
dept_loss = disengaged_active.groupby("department").apply(
    lambda d: pd.Series({"headcount": len(d), "annual_cost": (loaded(d["salary"]) * DISENGAGEMENT_LOSS_RATE).sum()})
)
dept_loss["annual_cost"] = dept_loss["annual_cost"].round(0)
w(dept_loss.sort_values("annual_cost", ascending=False))

w("\nCAVEAT: goal_achievement_score does not differ significantly between disengaged and\n"
  "engaged active employees (t-test p=0.16, see 03_deep_dive). This cost is a SIZE-OF-\n"
  "POPULATION estimate applying Finance's flat 15% assumption, not an empirically measured\n"
  "productivity deficit. Documented as a limitation in the deck.")

w("\n" + "=" * 90)
w("COMPONENT 3: HIRING INEFFICIENCY (Finance estimate: $4-6M/yr)")
w("=" * 90)
win_start = pd.Timestamp("2024-01-01")
hires_window = m[m.hire_date >= win_start]
agency_hires = hires_window[hires_window.hire_source == "agency"]
direct_hires = hires_window[hires_window.hire_source == "direct"]
referral_hires = hires_window[hires_window.hire_source == "referral"]

agency_cost_2yr = (agency_hires["salary"] * AGENCY_FEE_RATE).sum()
agency_benchmark_2yr = len(agency_hires) * DIRECT_HIRE_COST
excess_agency_cost_2yr = agency_cost_2yr - agency_benchmark_2yr

w(f"In-window (2024-2025) new hires by channel: agency={len(agency_hires)}, direct={len(direct_hires)}, referral={len(referral_hires)}")
w(f"Agency fee cost (18% of first-yr salary), 2yr total: ${agency_cost_2yr:,.0f}")
w(f"Direct-hire benchmark cost for same volume, 2yr total: ${agency_benchmark_2yr:,.0f}")
w(f"EXCESS cost of routing these hires through agency vs direct/referral pipeline, 2yr: ${excess_agency_cost_2yr:,.0f}")
w(f"  Annualised: ${excess_agency_cost_2yr/WINDOW_YEARS:,.0f}")

# Poor-match early attrition among agency hires specifically
agency_early = agency_hires[agency_hires.early_exit_12mo]
agency_early_cost_2yr = (loaded(agency_early["salary"]) * REPL_MULT * BACKFILL_RATE).sum()
w(f"\nAgency-sourced early exits (<=12mo tenure) in window: {len(agency_early)} of {len(agency_hires)} agency hires ({len(agency_early)/max(len(agency_hires),1)*100:.1f}%)")
w(f"  Poor-match replacement cost, 2yr: ${agency_early_cost_2yr:,.0f}  |  Annualised: ${agency_early_cost_2yr/WINDOW_YEARS:,.0f}")

total_hiring_ineff_annual = excess_agency_cost_2yr/WINDOW_YEARS + agency_early_cost_2yr/WINDOW_YEARS
w(f"\nTOTAL hiring inefficiency (excess channel cost + poor-match backfill), annualised: ${total_hiring_ineff_annual:,.0f}")
w(f"  vs Finance estimate range: $4-6M")

w("\n" + "=" * 90)
w("SUMMARY: RECOMPUTED $42M BREAKDOWN vs FINANCE ESTIMATE")
w("=" * 90)
w(f"{'Component':<45}{'Finance Est.':<18}{'Data-derived (annual)':<22}")
w(f"{'Regrettable attrition (HR-flagged)':<45}{'$22-25M':<18}${regret_cost_annual/1e6:.1f}M")
w(f"{'  of which Entity_B high-value':<45}{'':<18}${eb_cost_2yr/WINDOW_YEARS/1e6:.2f}M")
w(f"{'  of which R&C Director+ (NovaCorp)':<45}{'':<18}${rc_cost_2yr/WINDOW_YEARS/1e6:.2f}M")
w(f"{'Disengagement productivity loss':<45}{'$12-15M':<18}${loss_annual/1e6:.1f}M")
w(f"{'Hiring inefficiency':<45}{'$4-6M':<18}${total_hiring_ineff_annual/1e6:.1f}M")
total_derived = regret_cost_annual + loss_annual + total_hiring_ineff_annual
w(f"{'TOTAL':<45}{'~$42M':<18}${total_derived/1e6:.1f}M")

out.close()
print("\nSaved output/tables/04_financial_model_results.txt")
