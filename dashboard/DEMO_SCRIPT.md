# Monitoring cockpit — 90-second demo script

**App:** `dashboard/cockpit/nova_app.py` (Observed scenario only — the A/B toggle is not used)
**Claim on trial:** *"The $42M is not one problem. It's three, and we know where they live."* (Deck slides 2 and 15)
**Runtime:** 1:34 · single unbroken take · voiceover recorded separately

The proof is the un-cut filter interaction. Every number spoken is visible on
screen at the moment it is spoken, under a filter the audience just watched
being set. Nothing is quoted from the deck that the app does not render.

---

## Pre-flight

```bash
python -m src.monitor.build_mart          # writes outputs/monitor/monitor_mart.json
streamlit run dashboard/cockpit/nova_app.py
```

- Browser at **1920×1080, zoom 100%**, Streamlit sidebar collapsed (it already
  defaults to collapsed).
- Scenario control must read **Observed**. If it doesn't, click it before
  recording — a scenario switch mid-take puts a yellow simulation banner on
  screen and breaks the claim.
- All three filters must read their placeholders (`Entity`, `Department`,
  `Wave`). Reload the page to reset.
- Do a silent dry run first: the two scrolls in Beat 4 are the only place the
  take can look clumsy.

---

## Shot list

| Time | Action | On screen |
|---|---|---|
| 0:00–0:14 | Static. Cursor rests on the **Cost Buckets** panel. | Total Cost `$78.1M` · Cost Buckets: `$59.3M` disengagement bar dominating `$14.2M` / `$2.3M` / `$2.3M` |
| 0:14–0:38 | Open **Entity** → select **Entity B**. Let it rerun. Cursor traces the four KPI cards left to right. | Total Cost `$10.3M` · Response Gap `62.4%/80.3%` · Attrition Lead Time `~5 months` · caption `224 voluntary exits in scope · 8.6% annualised` |
| 0:38–0:56 | **Entity** → back to placeholder. **Department** → **Risk & Compliance**. | Total Cost `$16.4M` · caption `195 voluntary exits in scope · 5.7% annualised` |
| 0:56–1:20 | **Department** → back to placeholder. Scroll to **Flagged Cohorts** (bottom right). Cursor down the first three rows. | Row 1 `NovaCorp-Origin · Risk & Compliance / 1,117 / 35.2% / $11.9M` · Row 2 `NovaCorp-Origin · Corporate Operations / 863 / 43.1% / $9.9M` · Row 3 `Entity B · Retail Banking / 400 / 36.9% / $2.7M` |
| 1:20–1:34 | Scroll to the footer. Hold on the guardrail banner. Fade. | `1 cohort under 30 people withheld` · blue **Responsible use** banner |

---

## Voiceover

Read at roughly 130 words per minute. Full stops are pauses, not punctuation.

**0:00–0:14** *(30 words)*

> This is NovaCorp's people cost, live — seventy-eight million, not the
> forty-two Finance quoted. One bar explains the whole gap: disengagement,
> priced on the sustained threshold instead of the severe one.

**0:14–0:38** *(54 words)*

> Problem one. Filter to Entity B — every tile moves at once. Ten point three
> million. Voluntary attrition eight point six percent, against five
> company-wide. Survey response sixty-two percent, where the rest of the
> company runs eighty. And the warning window shortens from eight months to
> five. That's a trust problem, not a pay problem.

**0:38–0:56** *(41 words)*

> Problem two lives here. Clear the entity, filter Risk and Compliance: sixteen
> point four million, a hundred and ninety-five voluntary exits. The
> Director-plus cut — twelve veterans of forty-four — is on slide six. The
> cockpit tracks the department they walked out of.

**0:56–1:20** *(48 words)*

> Now clear everything and look at what's flagged, worst first. The top cohort
> isn't Entity B. It's NovaCorp-Origin, Risk and Compliance — eleven hundred
> people, thirty-five percent disengaged, eleven point nine million. Problem
> three sits in the original business, and exit data never shows it, because
> these people stay.

**1:20–1:34** *(23 words)*

> Aggregate only. No individual scores. One cohort under thirty people
> withheld. Three problems, three addresses, one screen — and it refreshes
> every survey wave.

---

## Why the script says $78.1M and not $42M

The Total Cost tile sums all four buckets with disengagement priced at the
**sustained** threshold (`<3.0` composite), which is the `$59.3M` figure on deck
slide 11. Finance's `$42M` prices the same bucket at the **severe** threshold
(`$12–15M`). Same four buckets, one different line — which is precisely the
re-calibration slide 11 argues for. Opening on the gap and naming it in the
first sentence is stronger than hoping nobody does the arithmetic.

## Do not say

These appear in the deck but **not** on the cockpit screen. Speaking them over
this footage would be claiming the app shows something it doesn't.

| Number | Where it actually lives | Why it isn't on screen |
|---|---|---|
| `$5.6M/yr` Entity_B | Slide 5 | Cockpit shows Entity B total exposure `$10.3M` and an addressable band `$2.6M–$5.2M`. Different basis. |
| `$2.6M/yr` R&C | Slide 7 | That is the Director+ replacement cost. Cockpit has no seniority dimension. |
| `27.3%`, `12 of 44` | Slide 6 | Same reason — entity × department × wave only. |
| `62.6% vs 83.6%` | Slide 5 | Cockpit compares Entity B against the **whole** company including itself, at wave 5: `62.4%/80.3%`. Read the screen. |
| `22.5%` disengaged | Slide 8 | Cockpit's company-wide share on its own eligibility basis is `26.5%`. |
| `$42M` | Slide 11 | See above — say the `$78.1M` on the tile and explain the one-line difference. |

## Deliberately left out

The **Scenario A / Scenario B** toggle is the best thing in the app, but it
proves the plan is *measurable*, not that the cost is *three problems*. Putting
it in these 90 seconds would split the claim across two arguments and land
neither. If a second clip is wanted, it is a clean 45 seconds on its own:
toggle A, toggle B, same tiles moving in opposite directions.
