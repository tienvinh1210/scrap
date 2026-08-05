# NovaCorp People Analytics Challenge — Findings Summary

## Headline

NovaCorp's $42M people-cost problem is not evenly spread. It is concentrated in three
specific, identifiable, and addressable pockets — and two of the three biggest levers
have nothing to do with pay.

## Root Cause 1 — Entity_B integration has broken trust in senior leadership, not pay

- Entity_B (1,884 people, acquired FY2023) has the highest attrition of any cohort:
  **15.0%** vs NovaCorp-Origin 10.3%, Entity_C 9.3%, Entity_A 7.5%.
- Among high-value staff (L3+/HiPo), Entity_B attrition is **15.5%**, regrettable-flag
  rate **5.1%** — both the highest of any legacy entity.
- **This is not a pay problem.** Entity_B's average compa-ratio (0.961) is *higher* than
  NovaCorp-Origin's (0.937), and only 4.3% of Entity_B staff are underpaid (<0.85 compa)
  vs 11.6% of NovaCorp-Origin staff.
- **It is a trust/purpose problem.** Entity_B scores dramatically lower on
  `senior_leadership_trust` (3.05 vs 3.38 company average, a 10% gap) and
  `purpose_meaning` (3.06 vs 3.38). Every other engagement dimension — manager
  effectiveness, recognition, psychological safety, wellbeing — is in line with or better
  than the rest of the company. The problem sits specifically with senior leadership
  connection, not local management.
- Corroborating signal: Entity_B's engagement survey response rate is 62.6%, vs 83.6%
  for NovaCorp-Origin — Entity_B employees are disengaging from the HR process itself.
- **Cost**: 48 Entity_B high-value voluntary departures over 2 years, avg salary
  $163,848 → **~$5.6M/year** in replacement cost.

## Root Cause 2 — Risk & Compliance is losing veteran Director-level talent to the external market

- Among NovaCorp-Origin staff at Director level and above (L4+) in Risk & Compliance:
  **27.3% attrition** (12 of 44) — more than double the next-highest department/level
  combination (Wealth Management L4+, 13.6%), and far above the R&C department average
  (11.8%).
- **Not pay-driven**: departed staff's compa-ratio (0.966) is statistically identical to
  those who stayed (0.969).
- **Not engagement-driven**: departed staff's final engagement score (3.33) was actually
  *higher* than those who stayed (3.13).
- **External market pull**: 8 of 12 departures cite "Career advancement" or "Better
  opportunity"; these are long-tenured veterans (avg tenure 24 years) being recruited
  away. This directly corroborates the Annual Report's statement that the Financial
  Accountability Regime (FAR) has "intensified competition for senior regulatory talent."
- **Cost**: 12 departures, avg salary $302,492 → **~$2.6M/year** in replacement cost,
  plus an unquantified but material loss of institutional/regulatory knowledge.

## Root Cause 3 — A large, largely invisible population is staying but disengaged

- 2,699 active employees (**22.5%** of the active workforce) show sustained
  disengagement (composite score <3.0 across 2+ survey waves), concentrated in
  Corporate Operations (36.7% of dept), Risk & Compliance (31.3%), and Insurance (30.9%)
  — vs Technology (8.4%) and Wealth Management (10.4%).
- **This is a different population from the one that's leaving.** Voluntary leavers'
  average engagement (3.30) is barely distinguishable from those who stay (3.36).
  Attrition data alone would completely miss this problem.
- **Early-warning signal**: survey *non-response* predicts voluntary exit better than the
  score itself — employees who complete under 60% of issued surveys leave voluntarily at
  **21.2%**, vs **6.8%** for high responders (a 3x gap), and this is data NovaCorp
  already collects at zero additional cost.
- **Financial exposure is highly threshold-sensitive**: the most severely disengaged
  segment (bottom ~6%, composite <2.5, n=697) costs ~$15.4M/year at Finance's 15% flat
  rate — closely matching Finance's own $12-15M estimate. But that severe band is only
  the tip: the full sustained-disengagement population (22.5%) implies exposure up to
  **$59M/year** if it continues to widen. We recommend the bottom decile (n=1,156,
  ~$25M/year exposure) as the actionable near-term intervention cohort.
- **Limitation, stated explicitly**: `goal_achievement_score` does not differ
  significantly between disengaged and engaged active staff (t-test p=0.16). This cost
  figure is a population-based estimate using Finance's flat-rate assumption, not an
  empirically observed productivity deficit — we cannot prove disengagement is currently
  suppressing measured output, only that Finance's own methodology, applied consistently,
  implies this scale of exposure and that the at-risk population is large and growing.

## Secondary / quick win — Hiring inefficiency (agency channel overuse)

- In the 2-year window, 274 hires were agency-sourced vs 93 direct and 88 referral.
- Agency fees (18% of salary) cost $6.07M over 2 years vs a $1.51M direct-hire benchmark
  for the same volume — a **$4.57M excess cost** (~$2.3M/year).
- No speed benefit: days-to-fill is ~51-53 days across all channels, no meaningful
  difference.
- Slightly worse retention: agency-sourced hires show an 8.4% early-exit (<=12mo) rate in
  this window.
- Total modeled hiring inefficiency ≈ **$4.6M/year** — this closely matches Finance's own
  $4-6M estimate, meaning this bucket is reasonably well understood already, with a clear
  lever: shift discretionary hires from agency to direct/referral pipelines.

## Recomputed $42M breakdown vs Finance's estimate

| Component | Finance estimate | Data-derived (annualised) |
|---|---|---|
| Regrettable attrition (HR-flagged, strict) | $22-25M | $14.3M |
| Regrettable attrition (all high-value voluntary, broad) | — | $30.6M |
| Disengagement productivity loss (severe, <2.5) | $12-15M | $15.4M |
| Disengagement productivity loss (sustained, <3.0) | — | $59.3M |
| Hiring inefficiency | $4-6M | $4.6M |

**Key insight for the CHRO**: HR's own `regrettable_flag` likely *undercounts* true
regrettable-attrition cost (only 153 of 255 high-value voluntary leavers get flagged),
while the disengagement bucket has a much larger long tail than currently budgeted. The
hiring-inefficiency estimate is the one bucket that is already well-calibrated.

## Ethics / equity checks performed (no red flags found)

- No material gender pay gap: compa-ratio is flat across gender within the same role
  level (e.g. L3: Female 0.947 vs Male 0.946).
- No material gender attrition gap (Female 10.6% vs Male 10.2% overall).
- Female representation at L5+ in this dataset is 59.2% (differs from the Annual
  Report's 34.1% figure — a documented data/report discrepancy, not evidence of bias in
  either direction).

## Explicit limitations

1. Dataset-derived voluntary attrition rate (~5%/year) is materially lower than the
   Annual Report's headline figure (10.4% FY2025). Per the Case Brief, the CSV datasets
   are treated as the analytical ground truth; the Annual Report is used only for
   qualitative narrative context.
2. `stated_exit_reason`, `regrettable_flag`, and `performance_band_at_exit` are
   retrospective HR judgements, not verified ground truth — used as one signal among
   several, not taken at face value.
3. Disengagement's link to measured productivity (goal achievement score) is not
   statistically significant in this data — the $ cost of disengagement is a
   population-size estimate under Finance's assumption, not a proven output deficit.
4. Manager-level clustering of attrition was tested and found weak (correlation ≈ 0
   between team engagement and team attrition) — we did not pursue a "bad manager"
   narrative because the data does not support one.
5. 2025-H2 performance reviews are absent from the data; no conclusions drawn about the
   most recent half-year of performance.
