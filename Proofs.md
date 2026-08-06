# Proofs — Slides 11-13 Number Audit

This document traces every number shown on **Slide 11 (Putting It Together)**,
**Slide 12 (Our Recommendation)**, and **Slide 13 (Expected Impact)** of
`deck/NovaCorp_CHRO_Deck.pdf` back to a specific calculation and a specific
source file. Where a number checks out, the source line is cited. Where it
does **not** check out, that is stated plainly below, not glossed over.

All figures were re-derived independently in
[`analysis/06_slide_audit.py`](analysis/06_slide_audit.py), which writes its
full output to
[`output/tables/06_slide11_13_audit.txt`](output/tables/06_slide11_13_audit.txt).
That script re-reads `output/tables/employee_master.csv` from scratch and
recomputes every figure below using only the four source CSVs — nothing here
is asserted without being re-derivable by running that script.

**Verdict key**: ✅ MATCH (reproduces exactly) · ⚠️ MATCH WITH CAVEAT
(reproduces, but on a basis not fully consistent with the rest of the deck) ·
❌ ERROR (does not reconcile with any documented calculation) · ℹ️ NOT
STATISTICAL (a logical/definitional claim, not a data estimate).

---

## Slide 11 — "Putting It Together" (Financial Synthesis table)

| # | Deck value | Verdict | Derivation | Source |
|---|---|---|---|---|
| 1 | Regrettable attrition (HR-flagged, strict): **$14.3M** | ✅ | 153 HR-flagged "regrettable" departures × loaded salary (×1.12 super) × 1.5 replacement multiplier × 0.85 backfill rate, ÷2 years = $14,258,723 | `output/tables/04_financial_model_results.txt`, lines 4-8 |
| 2 | Regrettable attrition (all high-value voluntary): **$30.6M** | ✅ | 255 high-value (L3+/HiPo) voluntary leavers, same formula = $30,635,170/yr | `output/tables/04_financial_model_results.txt`, line 20 |
| 3 | Disengagement loss (severe, <2.5): **$15.4M** | ✅ | Active staff with ≥2 survey responses and avg composite score <2.5 (n=697, 5.8% of active) × loaded salary × 15% = $15,365,129 | `output/tables/06_slide11_13_audit.txt`, threshold table (this specific number was **not** in any file before this audit — see "Gaps closed" below) |
| 4 | Disengagement loss (sustained, <3.0): **up to $59.3M** | ✅ | Same population definition, threshold <3.0 (n=2,699, 22.5% of active) = $59,293,114 | `output/tables/04_financial_model_results.txt`, line 30 |
| 5 | Hiring inefficiency: **$4.6M** | ✅ | Excess agency-fee cost ($2,282,587/yr) + poor-match early-exit backfill cost ($2,270,020/yr) = $4,552,607/yr | `output/tables/04_financial_model_results.txt`, lines 55-61 |

**Every number on Slide 11 checks out.** Row 3 ($15.4M) was genuinely
calculated the same way as the rest of the model, but — as detailed below —
it had never been written to a saved output file before this audit; it
existed only as a number I read off an ad-hoc terminal calculation during the
original analysis. That gap is now closed.

---

## Slide 12 — "Our Recommendation" (roadmap cards)

| Deck value | Verdict | Derivation | Source |
|---|---|---|---|
| "$0 incremental cost" | ℹ️ NOT STATISTICAL | This is a definitional claim, not a data estimate: `response_rate` already exists in `engagement.csv` for every employee, so *detecting* the at-risk population requires no new survey or instrumentation. It does **not** mean implementing manager check-ins is free — that labour cost is real and was never estimated. Stated explicitly so it isn't mistaken for a modelled figure. | — |
| "Protects ~$5.6M/yr" (Entity_B) | ✅ | 48 Entity_B high-value voluntary departures × loaded salary × 1.5 × 0.85 ÷ 2yr = $5,615,396 | `output/tables/04_financial_model_results.txt`, lines 11-12 |
| "Protects ~$2.6M/yr" (R&C Director+) | ✅ | 12 R&C Director+ (L4+) NovaCorp-Origin departures, same formula = $2,591,749 | `output/tables/04_financial_model_results.txt`, lines 16-17 |
| "354 high-value staff" (Entity_B) | ✅ | Entity_B headcount with role_level≥3 or hipo_flag=True | `output/tables/02_eda_results.txt`, section 2 ("High-value attrition by legacy_entity_code") |
| "44 people" (R&C Director+) | ✅ | R&C, role_level≥4, legacy_entity_code=NovaCorp-Origin, all statuses | `output/tables/03_deep_dive_results.txt`, section B |
| "3x better (21.2% vs 6.8%)" | ✅ | Voluntary-exit rate for employees with survey response_rate<60% (21.2%) vs ≥60% (6.8%) | `output/tables/02_eda_results.txt`, section 4 ("Non-response rate...vs voluntary attrition") |
| "leadership trust (3.05→3.38)" | ⚠️ MATCH WITH CAVEAT | Entity_B active-employee mean = 3.054 (matches). "3.38" is the mean for **all non-Entity_B active staff combined** (Entity_A+C+NovaCorp-Origin) = 3.375, which rounds to 3.38. This is a *different, slightly broader* base than the NovaCorp-Origin-only figure (3.383) quoted elsewhere in the deep-dive — both round to 3.38, so the number is not wrong, but this specific "rest of company" average had never been logged to a file; it existed only inside the chart-plotting code. Now logged. | `output/tables/06_slide11_13_audit.txt` (previously **uncited**) |
| "purpose (3.06→3.38)" | ⚠️ MATCH WITH CAVEAT | Same situation: Entity_B = 3.070 (rounds to 3.06? — see note below), rest-of-company = 3.368 (rounds to 3.38). See note. | `output/tables/06_slide11_13_audit.txt` |

**Note on 3.06 vs 3.070**: the deck text says "3.06" but the recomputed
Entity_B `avg_purpose` for the *active-only* population is 3.070, which
rounds to **3.07**, not 3.06. The all-status (active+departed) Entity_B
figure reported earlier in the deep-dive was 3.058, which does round to 3.06.
The deck's chart uses the active-only figure (3.070) but the slide 12 body
text carried over the all-status figure (3.058→"3.06") from an earlier slide.
This is a **minor rounding/consistency slip** (3.06 vs 3.07), not a
fabrication — both values are real, correctly-computed numbers, just for two
slightly different populations (active-only vs. active+departed) that got
mixed between slides. See "Corrections made" below.

---

## Slide 13 — "Expected Impact"

| Deck value | Verdict | Derivation | Source |
|---|---|---|---|
| "~$10.5M/yr Protected replacement cost: Entity_B + R&C Director+ ... normalised to company-average attrition" | ❌ **ERROR** | The two cited sub-cohorts sum to **$5,615,396 + $2,591,749 = $8,207,144 ≈ $8.2M**, not $10.5M. I also computed what a genuine "normalise to company-average attrition rate" delta would look like (i.e., only the *excess* departures above the rest-of-company rate, not the full cohort) — that calculation gives **$1.92M**, an even smaller number. **$10.5M matches neither interpretation.** There is no documented calculation behind this figure. **I am truthfully admitting this number was wrong** — most likely an arithmetic slip when I wrote the slide, not a deliberate fabrication, but it does not survive an audit and should not have been presented as-is. | `output/tables/06_slide11_13_audit.txt`, "AUDIT OF SLIDE 13" section |
| "~$25M/yr ... bottom-decile cohort (1,156 people)" | ⚠️ MATCH WITH CAVEAT (population-inconsistent) | Reproduces exactly (n=1,156, $25,315,063) — but **only** if "bottom decile" is computed over active staff with **at least 1** survey response. Every other "sustained/persistent disengagement" figure in this deck (the $59.3M headline, the Slide 9 chart, the department breakdown) requires **at least 2** responses to justify the word "sustained." Recomputed on that consistent basis, the bottom decile is **1,048 people / $23.3M/yr**, not 1,156/$25M. The number on the slide is genuinely reproducible — it is not made up — but it was built on a slightly looser population filter than the rest of the analysis uses, and that inconsistency was not visible until this audit. | `output/tables/06_slide11_13_audit.txt`, "bottom-decile cohort" section |
| "~$2.3M/yr ... Hiring-fee savings" | ✅ | This is specifically the excess-agency-fee component (not the poor-match backfill component) of hiring inefficiency = $2,282,587/yr | `output/tables/04_financial_model_results.txt`, line 56 |

---

## Corrections made to the deck as a result of this audit

Because two of the numbers above did not hold up, I corrected
`analysis/05_build_deck.py` and rebuilt `deck/NovaCorp_CHRO_Deck.pdf`:

1. **Slide 13, stat card 1**: changed from "~$10.5M/yr" to **"~$8.2M/yr"**
   (the correct sum of the two cited, verified sub-cohort figures), and
   relabeled from "normalised to company-average attrition" to "if both
   cohorts are fully addressed" so the label matches what is actually being
   calculated (full-cohort protection, not a rate-normalisation delta).
2. **Slide 13, stat card 2**: changed from "1,156 people, ~$25M/yr" to
   **"1,048 people, ~$23M/yr"**, switching to the population basis (≥2 survey
   responses) that is used consistently everywhere else in the deck.
3. **Slide 12, body text**: changed "purpose (3.06→3.38)" to **"purpose
   (3.07→3.38)"** to match the active-only population basis actually used in
   the Slide 4 chart it is drawn from.

No other numbers on slides 11-13 required correction.

Additionally, the two remaining ⚠️ MATCH WITH CAVEAT items (Slide 12's
leadership-trust/purpose deltas, and Slide 13's bottom-decile figure) are now
marked with a **`*`** directly on those slides, with a "See Appendix A for
methodology notes on starred figures" footnote. **Appendix A** (new, inserted
immediately after the closing slide) reproduces the same explanation given in
this document, so a reader of the deck alone — without this file — can still
see the caveat. The pre-existing appendices were renumbered B-E accordingly.

---

## Gaps closed by this audit (numbers that were correct but previously uncited)

Three figures were originally computed correctly during analysis but only as
ad-hoc terminal calculations that were never written to a persisted output
file — meaning they could not previously be cited or independently
re-verified from a saved artifact:

- Slide 11 row 3: the $15.4M "severe disengagement" figure
- Slide 12 / Slide 4 chart: the "rest of company" leadership-trust and
  purpose-meaning averages (3.375 / 3.368)
- Slide 13: the bottom-decile disengagement calculation

All three are now computed and saved by
[`analysis/06_slide_audit.py`](analysis/06_slide_audit.py) →
[`output/tables/06_slide11_13_audit.txt`](output/tables/06_slide11_13_audit.txt),
so every number on slides 11-13 is now traceable to a script that can be
re-run from the raw CSVs.

## What is genuinely an estimate, not a fact, on these three slides

Even where the arithmetic is correct, some of these numbers carry judgment
calls that are worth being upfront about if challenged in Q&A:

- **All disengagement $ figures** apply Finance's flat 15%-of-salary
  assumption to a population *size* we measured. We did not — and could not,
  from this data — prove that disengaged employees are currently producing
  15% less output; the goal-achievement-score gap between disengaged and
  engaged staff is not statistically significant (p=0.16, see
  `output/tables/03_deep_dive_results.txt`). These are population-based cost
  *exposures* under Finance's own assumption, not measured productivity
  losses.
- **All replacement-cost figures** (Entity_B, R&C Director+, hiring
  poor-match) assume Finance's 1.5× multiplier and 85% backfill rate apply
  uniformly to these specific cohorts. We have no cohort-specific evidence
  that senior regulatory or Entity_B replacement costs actually run at 1.5×
  salary — this is Finance's company-wide assumption, applied consistently,
  not independently validated for these sub-populations.
- **The "$0 incremental cost" framing** covers detection only, as noted
  above, not the cost of acting on what is detected.
