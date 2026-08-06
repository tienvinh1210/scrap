"""
Audit script: recomputes and persists every number that appears on Slides 11-13
of the deck (Financial Synthesis / Recommendation Roadmap / Expected Impact),
so each figure is traceable to a saved, reproducible calculation rather than an
ad-hoc/unsaved shell computation. Output feeds Proofs.md.

Some of these numbers were originally computed via inline shell one-liners
during analysis and were correct, but never written to a persisted txt file.
This script closes that gap by recomputing them from the same source data and
saving results here.
"""
import pandas as pd
import numpy as np
from scipy import stats

pd.set_option("display.width", 160)

SUPER = 0.12
REPL_MULT = 1.5
BACKFILL = 0.85
LOSS_RATE = 0.15
AGENCY_FEE = 0.18
DIRECT_COST = 5500
WINDOW_YEARS = 2.0

def loaded(s):
    return s * (1 + SUPER)

m = pd.read_csv("output/tables/employee_master.csv", low_memory=False, parse_dates=["hire_date", "exit_date"])
active = m[m.status == "active"].copy()

out = open("output/tables/06_slide11_13_audit.txt", "w")
def w(*a):
    s = " ".join(str(x) for x in a)
    print(s); out.write(s + "\n")

w("=" * 90)
w("AUDIT OF SLIDE 11 — FINANCIAL SYNTHESIS TABLE")
w("=" * 90)
w("All 5 rows of this table are taken directly from output/tables/04_financial_model_results.txt")
w("(component sections 1-3 and the summary block). Re-verified here from source data:\n")

regret = m[m.is_regrettable]
regret_cost_annual = (loaded(regret["salary_at_exit"]) * REPL_MULT * BACKFILL).sum() / WINDOW_YEARS
w(f"Row 1 - Regrettable attrition (HR-flagged, strict): n={len(regret)}, annualised=${regret_cost_annual:,.0f}"
  f"  -> deck shows $14.3M  [MATCH]" if abs(regret_cost_annual/1e6-14.3) < 0.05 else " [CHECK]")

hv_vol = m[(m.is_high_value) & (m.is_voluntary == True)]
hv_cost_annual = (loaded(hv_vol["salary_at_exit"]) * REPL_MULT * BACKFILL).sum() / WINDOW_YEARS
w(f"Row 2 - Regrettable attrition (all high-value voluntary): n={len(hv_vol)}, annualised=${hv_cost_annual:,.0f}"
  f"  -> deck shows $30.6M")

elig = active[active.n_responses.fillna(0) >= 2]
w(f"\nDisengagement population base (active, >=2 completed survey waves): n={len(elig)} of {len(active)} active")
threshs = [2.5, 2.75, 3.0, 3.25]
sens_rows = []
for t in threshs:
    seg = elig[elig.avg_engagement < t]
    cost = (loaded(seg.salary) * LOSS_RATE).sum()
    sens_rows.append((t, len(seg), len(seg)/len(active)*100, cost))
    w(f"  threshold <{t}: headcount={len(seg):5d} ({len(seg)/len(active)*100:4.1f}% of active)  annualised cost=${cost:,.0f}  (${cost/1e6:.2f}M)")

w(f"\nRow 3 - Disengagement loss (severe, <2.5): ${sens_rows[0][3]:,.0f} -> deck shows $15.4M "
  f"[{'MATCH' if abs(sens_rows[0][3]/1e6-15.4)<0.1 else 'CHECK'}]")
w(f"Row 4 - Disengagement loss (sustained, <3.0): ${sens_rows[2][3]:,.0f} -> deck shows 'up to $59.3M' "
  f"[{'MATCH' if abs(sens_rows[2][3]/1e6-59.3)<0.1 else 'CHECK'}]")
w(f"  (For completeness, <3.25 threshold: ${sens_rows[3][3]:,.0f} = ${sens_rows[3][3]/1e6:.1f}M, n={sens_rows[3][1]} -- NOT used on slide 11, shown only on slide 9's chart)")

# Implied Finance population size (back-solve from $13.5M midpoint)
avg_loaded_active = loaded(active.salary).mean()
implied_hc = 13.5e6 / (avg_loaded_active * LOSS_RATE)
w(f"\nBack-solved: Finance's $13.5M midpoint / (avg loaded active salary ${avg_loaded_active:,.0f} x 15%) "
  f"implies a population of {implied_hc:,.0f} people ({implied_hc/len(active)*100:.1f}% of active) "
  f"-- consistent with the <2.5 'severe' band (n={sens_rows[0][1]}, {sens_rows[0][2]:.1f}%). Used only as narrative "
  f"support on slide 9, not a formal statistical test.")

win_start = pd.Timestamp("2024-01-01")
hires_window = m[m.hire_date >= win_start]
agency_hires = hires_window[hires_window.hire_source == "agency"]
agency_cost = (agency_hires.salary * AGENCY_FEE).sum()
direct_bench = len(agency_hires) * DIRECT_COST
excess_fee_annual = (agency_cost - direct_bench) / WINDOW_YEARS
agency_early = agency_hires[agency_hires.early_exit_12mo]
poor_match_annual = (loaded(agency_early.salary) * REPL_MULT * BACKFILL).sum() / WINDOW_YEARS
total_hiring_annual = excess_fee_annual + poor_match_annual
w(f"\nRow 5 - Hiring inefficiency: excess fee (annual)=${excess_fee_annual:,.0f} + poor-match backfill (annual)=${poor_match_annual:,.0f} "
  f"= ${total_hiring_annual:,.0f} -> deck shows $4.6M [{'MATCH' if abs(total_hiring_annual/1e6-4.6)<0.1 else 'CHECK'}]")

w("\n" + "=" * 90)
w("AUDIT OF SLIDE 12 — RECOMMENDATION ROADMAP")
w("=" * 90)
w("'Protects ~$5.6M/yr' (Entity_B) and 'Protects ~$2.6M/yr' (R&C Director+) are the same two")
w("sub-cohort figures from 04_financial_model_results.txt, re-verified below:\n")

eb_hv_dep = m[(m.legacy_entity_code == "Entity_B") & (m.is_high_value) & (m.is_voluntary == True)]
eb_cost_annual = (loaded(eb_hv_dep["salary_at_exit"]) * REPL_MULT * BACKFILL).sum() / WINDOW_YEARS
w(f"Entity_B high-value voluntary departures: n={len(eb_hv_dep)}, annualised replacement cost=${eb_cost_annual:,.0f} "
  f"-> deck shows ~$5.6M/yr [{'MATCH' if abs(eb_cost_annual/1e6-5.6)<0.05 else 'CHECK'}]")

rc_dir_dep = m[(m.department == "Risk & Compliance") & (m.role_level >= 4) & (m.legacy_entity_code == "NovaCorp-Origin") & (m.is_departed)]
rc_cost_annual = (loaded(rc_dir_dep["salary_at_exit"]) * REPL_MULT * BACKFILL).sum() / WINDOW_YEARS
w(f"R&C Director+ (L4+) NovaCorp-Origin departures: n={len(rc_dir_dep)}, annualised replacement cost=${rc_cost_annual:,.0f} "
  f"-> deck shows ~$2.6M/yr [{'MATCH' if abs(rc_cost_annual/1e6-2.6)<0.05 else 'CHECK'}]")

w("\n'This signal predicts voluntary exit 3x better than the score itself (21.2% vs 6.8%)':")
m["low_response_rate"] = m["response_rate"] < 0.6
ct = pd.crosstab(m["low_response_rate"], m["is_voluntary"], normalize="index")
w(ct)
w(f"-> low_response_rate=True voluntary-exit rate = {ct.loc[True, True]*100:.1f}%, "
  f"low_response_rate=False rate = {ct.loc[False, True]*100:.1f}% "
  f"[{'MATCH' if abs(ct.loc[True,True]*100-21.2)<0.2 and abs(ct.loc[False,True]*100-6.8)<0.2 else 'CHECK'}] "
  f"(source: 02_eda_results.txt, section 4)")

w("\n'354 high-value staff' (Entity_B):")
eb_hv_all = m[(m.legacy_entity_code == "Entity_B") & (m.is_high_value)]
w(f"  Entity_B high-value headcount = {len(eb_hv_all)} [{'MATCH' if len(eb_hv_all)==354 else 'CHECK'}] (source: 02_eda_results.txt, section 2)")

w("\n'44 people' (R&C Director+ NovaCorp-Origin):")
rc_dir_all = m[(m.department == "Risk & Compliance") & (m.role_level >= 4) & (m.legacy_entity_code == "NovaCorp-Origin")]
w(f"  R&C Director+ NovaCorp-Origin headcount = {len(rc_dir_all)} [{'MATCH' if len(rc_dir_all)==44 else 'CHECK'}] (source: 03_deep_dive_results.txt, section B)")

w("\n'leadership trust (3.05->3.38)' and 'purpose (3.06->3.38)' — Entity_B vs REST OF COMPANY (active only):")
cols = ["avg_leadership_trust", "avg_purpose"]
eb_active = active[active.legacy_entity_code == "Entity_B"][cols].mean()
rest_active = active[active.legacy_entity_code != "Entity_B"][cols].mean()
w(f"  Entity_B:          leadership_trust={eb_active['avg_leadership_trust']:.3f}   purpose={eb_active['avg_purpose']:.3f}")
w(f"  Rest of company:    leadership_trust={rest_active['avg_leadership_trust']:.3f}   purpose={rest_active['avg_purpose']:.3f}")
w(f"  -> deck shows 3.05 -> 3.38 and 3.06 -> 3.38. NOTE: 'rest of company' here is NOT the same base as the")
w(f"  earlier NovaCorp-Origin-only figures reported in 03_deep_dive_results.txt (3.383/3.383 for NovaCorp-Origin")
w(f"  alone); it is Entity_A + Entity_C + NovaCorp-Origin combined (active only). Both bases round to 3.38.")
w(f"  This computation was previously only embedded in the deck's chart code (Slide 4), not logged separately")
w(f"  until now — it is reproducible but was NOT in a saved txt file prior to this audit.")

w("\n" + "=" * 90)
w("AUDIT OF SLIDE 13 — EXPECTED IMPACT")
w("=" * 90)

combined_protected = eb_cost_annual + rc_cost_annual
w(f"'~$10.5M/yr Protected replacement cost: Entity_B + R&C Director+ cohorts normalised to company-average")
w(f"attrition' (as currently printed on Slide 13):")
w(f"  Entity_B annualised cost:        ${eb_cost_annual:,.0f}")
w(f"  R&C Director+ annualised cost:   ${rc_cost_annual:,.0f}")
w(f"  SUM:                             ${combined_protected:,.0f}  =  ${combined_protected/1e6:.2f}M")
w(f"  *** DISCREPANCY: the deck currently shows ~$10.5M/yr. The correct sum of the two cited sub-cohort")
w(f"  figures is ${combined_protected/1e6:.1f}M, not $10.5M. There is no alternative documented calculation")
w(f"  (e.g. a 'normalise to company-average attrition rate' delta) that produces $10.5M either -- see below.")
w(f"  This number was NOT derived from a saved computation; it does not reconcile with any underlying figure")
w(f"  in this analysis. It should be treated as an ERROR in the deck, not a legitimate estimate.")

w(f"\n  For reference, an actual 'normalise to average attrition' delta calculation (a DIFFERENT and smaller")
w(f"  quantity than 'eliminate all cited departures') would be:")
company_hv_rate_ex_eb = m[(m.is_high_value) & (m.legacy_entity_code != "Entity_B")]["is_departed"].mean()
eb_hv_rate = m[(m.legacy_entity_code == "Entity_B") & (m.is_high_value)]["is_departed"].mean()
excess_headcount_eb = len(eb_hv_all) * (eb_hv_rate - company_hv_rate_ex_eb)
excess_cost_eb_normalized = excess_headcount_eb * loaded(eb_hv_dep["salary_at_exit"].mean()) * REPL_MULT * BACKFILL / WINDOW_YEARS
w(f"  Entity_B high-value attrition rate: {eb_hv_rate*100:.1f}%  |  rest-of-company high-value rate: {company_hv_rate_ex_eb*100:.1f}%")
w(f"  'Excess' departures above the rest-of-company rate: {excess_headcount_eb:.1f} people (of 354)")
w(f"  Annualised cost of just the EXCESS (normalised) departures: ${excess_cost_eb_normalized:,.0f} = ${excess_cost_eb_normalized/1e6:.2f}M")
w(f"  This is smaller than the $5.6M full-cohort figure, and even smaller than $10.5M -- confirming $10.5M")
w(f"  cannot be justified under a 'normalise to average' framing either. RECOMMENDATION: correct slide 13 to")
w(f"  ${combined_protected/1e6:.1f}M/yr (sum of the two cited, verified sub-cohort figures) and change the label")
w(f"  from 'normalised to company-average attrition' to 'if fully addressed' to match the actual calculation.")

w(f"\n'~$25M/yr ... bottom-decile cohort (1,156 people)':")
elig_sorted = elig.dropna(subset=["avg_engagement"]).sort_values("avg_engagement")
decile_n = int(len(elig_sorted) * 0.10)
bottom_decile = elig_sorted.head(decile_n)
cost_decile = (loaded(bottom_decile.salary) * LOSS_RATE).sum()
w(f"  STRICT population (active, >=2 responses, consistent with 'persistent disengagement' used elsewhere):")
w(f"    n_total={len(elig_sorted)}, decile n={decile_n}, cutoff<{bottom_decile.avg_engagement.max():.2f}, "
  f"annualised cost=${cost_decile:,.0f} (${cost_decile/1e6:.2f}M)")

loose = active.dropna(subset=["avg_engagement"]).sort_values("avg_engagement")
n_loose = int(len(loose) * 0.10)
bd_loose = loose.head(n_loose)
cost_loose = (loaded(bd_loose.salary) * LOSS_RATE).sum()
w(f"  LOOSE population (active, ANY non-null avg_engagement, i.e. >=1 response, NOT >=2):")
w(f"    n_total={len(loose)}, decile n={n_loose}, cutoff<{bd_loose.avg_engagement.max():.2f}, "
  f"annualised cost=${cost_loose:,.0f} (${cost_loose/1e6:.2f}M)")
w(f"  -> deck shows 1,156 people / ~$25M/yr. This MATCHES the LOOSE population exactly (n={n_loose}, "
  f"${cost_loose/1e6:.2f}M), NOT the strict >=2-response population (n={decile_n}, ${cost_decile/1e6:.2f}M).")
w(f"  *** INCONSISTENCY: every other 'sustained/persistent disengagement' figure in this analysis (the")
w(f"  $59.3M headline figure, the Slide 9 sensitivity chart, and the department breakdown) uses the >=2-")
w(f"  response population to justify calling it 'sustained'. The bottom-decile figure on Slide 13 was")
w(f"  computed on a looser, single-response-eligible population and is therefore on a slightly different")
w(f"  basis than the rest of the deck. The number is genuinely reproducible (not fabricated) but the")
w(f"  population definition was not held constant. RECOMMENDATION: either (a) relabel Slide 13 to disclose")
w(f"  the >=1-response basis, or (b) switch to the strict basis and update to ${decile_n:,} people / "
  f"${cost_decile/1e6:.1f}M/yr for internal consistency.")
w(f"  Separately: this calculation was originally run as an ad-hoc shell one-liner during analysis and was")
w(f"  NOT saved to any output/tables/*.txt file until this audit script closed that gap.")

w(f"\n'~$2.3M/yr ... Hiring-fee savings from shifting discretionary agency hires':")
w(f"  This is the EXCESS FEE component only (not the poor-match backfill component):")
w(f"  Excess agency fee cost, annualised: ${excess_fee_annual:,.0f} = ${excess_fee_annual/1e6:.2f}M")
w(f"  -> deck shows ~$2.3M/yr [{'MATCH' if abs(excess_fee_annual/1e6-2.3)<0.05 else 'CHECK'}] "
  f"(source: 04_financial_model_results.txt, Component 3)")

w("\n" + "=" * 90)
w("'$0 incremental cost' (Slide 12, Recommendation 1) — CLASSIFICATION")
w("=" * 90)
w("This is NOT a statistically derived figure. It is a logical/definitional claim: the response_rate field")
w("already exists in engagement.csv for every employee, so DETECTING the at-risk population requires no new")
w("data collection or survey instrumentation. It does NOT mean the intervention (manager check-ins) has zero")
w("labour cost -- that cost is real but unestimated in this analysis and should be caveated if pressed on it.")

out.close()
print("\nSaved output/tables/06_slide11_13_audit.txt")
