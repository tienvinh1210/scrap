"""
Builds the final CHRO-facing slide deck as a single PDF:
  deck/NovaCorp_CHRO_Deck.pdf

Structure: Hook -> Story (Problem/Evidence/Finding/So-What) -> Method -> Impact -> Recommend
15 core slides + appendix slides (unlimited per brief).
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch

pd.set_option("display.width", 160)

# ---------------------------------------------------------------------------
# Style constants
# ---------------------------------------------------------------------------
PURPLE = "#7C1FE0"
DARK = "#1B1B2F"
SLATE = "#4A4A5A"
GREY = "#8A8A99"
LIGHT_BG = "#F6F3FC"
RED = "#D64545"
GREEN = "#2E9E6D"
GOLD = "#E0A62E"
WHITE = "#FFFFFF"

plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["axes.edgecolor"] = SLATE
plt.rcParams["text.color"] = DARK
plt.rcParams["axes.labelcolor"] = DARK
plt.rcParams["xtick.color"] = SLATE
plt.rcParams["ytick.color"] = SLATE

FIGSIZE = (13.333, 7.5)  # 16:9

SLIDE_NUM = [0]

def new_slide(kicker, title):
    SLIDE_NUM[0] += 1
    fig = plt.figure(figsize=FIGSIZE, dpi=150)
    fig.patch.set_facecolor(WHITE)
    # Header
    fig.text(0.045, 0.94, kicker.upper(), fontsize=12, color=PURPLE, fontweight="bold", family="DejaVu Sans")
    title_fs = 22 if len(title) <= 58 else (19 if len(title) <= 68 else 17)
    fig.text(0.045, 0.885, title, fontsize=title_fs, color=DARK, fontweight="bold")
    fig.add_artist(plt.Line2D([0.045, 0.955], [0.86, 0.86], color=PURPLE, linewidth=1.5, transform=fig.transFigure))
    # Footer
    fig.text(0.045, 0.025, "NovaCorp People Analytics Challenge  |  Accenture x SUBAA 2026  |  Confidential", fontsize=8, color=GREY)
    fig.text(0.955, 0.025, f"{SLIDE_NUM[0]}", fontsize=9, color=GREY, ha="right")
    return fig

def bullet_block(fig, x, y, bullets, fontsize=13, line_gap=0.052, color=DARK, bold_first=False, width=0.42):
    yy = y
    for i, b in enumerate(bullets):
        if b == "":
            yy -= line_gap * 0.55
            continue
        weight = "bold" if (bold_first and i == 0) else "normal"
        fig.text(x, yy, "•", fontsize=fontsize, color=PURPLE, fontweight="bold", va="top")
        fig.text(x + 0.018, yy, b, fontsize=fontsize, color=color, va="top", weight=weight, bbox=None)
        n_lines = b.count("\n") + 1
        yy -= line_gap * (0.78 + 0.78 * (n_lines - 1)) if n_lines > 1 else line_gap

def stat_card(fig, x, y, w, h, value, label, value_color=PURPLE, fontsize_val=26, fontsize_label=10.5):
    ax = fig.add_axes([x, y, w, h])
    ax.axis("off")
    box = FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0,rounding_size=0.06",
                          transform=ax.transAxes, facecolor=LIGHT_BG, edgecolor=PURPLE, linewidth=1.0)
    ax.add_patch(box)
    ax.text(0.5, 0.62, value, fontsize=fontsize_val, color=value_color, fontweight="bold", ha="center", va="center", transform=ax.transAxes)
    ax.text(0.5, 0.22, label, fontsize=fontsize_label, color=SLATE, ha="center", va="center", transform=ax.transAxes, wrap=True)
    return ax

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
m = pd.read_csv("output/tables/employee_master.csv", low_memory=False, parse_dates=["hire_date", "exit_date"])
active = m[m.status == "active"].copy()
hv = m[m.is_high_value].copy()

SUPER = 0.12
REPL_MULT = 1.5
BACKFILL = 0.85
LOSS_RATE = 0.15
AGENCY_FEE = 0.18
DIRECT_COST = 5500

def loaded(s):
    return s * (1 + SUPER)

import os
PREVIEW = os.environ.get("DECK_PREVIEW_DIR")

pdf = PdfPages("deck/NovaCorp_CHRO_Deck.pdf")

def save(fig, facecolor=WHITE):
    pdf.savefig(fig, facecolor=facecolor)
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        fig.savefig(f"{PREVIEW}/slide{SLIDE_NUM[0]:02d}.png", dpi=130, facecolor=facecolor)
    plt.close(fig)

# ===========================================================================
# SLIDE 1 — INTRODUCTION / COVER
# ===========================================================================
fig = plt.figure(figsize=FIGSIZE, dpi=150)
fig.patch.set_facecolor(DARK)
fig.text(0.5, 0.83, "Accenture x SUBAA People Analytics Challenge 2026", fontsize=15, color="#B3A3D9", ha="center")
fig.text(0.5, 0.755, "NovaCorp CHRO Briefing", fontsize=15, color="#B3A3D9", ha="center")
fig.add_artist(plt.Line2D([0.30, 0.70], [0.685, 0.685], color=PURPLE, linewidth=2, transform=fig.transFigure))
fig.text(0.5, 0.60, "Team 363738", fontsize=34, color=WHITE, ha="center", fontweight="bold")
team_members = [
    "Tien Vinh Dang",
    "Thanh Hieu Nguyen Do",
    "Yen Ngoc Nguyen",
    "An Nhan Nguyen Vu",
    "Quang Khai Thieu",
]
for i, name in enumerate(team_members):
    fig.text(0.5, 0.42 - i * 0.055, name, fontsize=14, color="#D9C4F7", ha="center")
fig.text(0.5, 0.09, "August 2026", fontsize=11, color="#8A7AB0", ha="center")
SLIDE_NUM[0] = 1
save(fig, facecolor=DARK)

# ===========================================================================
# SLIDE 2 — THREE MAIN FINDINGS (EXECUTIVE SUMMARY)
# ===========================================================================
fig = new_slide("Executive Summary", "Three findings explain where NovaCorp's people cost is really coming from")
bullet_block(fig, 0.06, 0.75, [
    "NovaCorp's CHRO asked us to explain what is driving an estimated $42M annual people\ncost, and to advise where to focus first.",
    "",
    "Triangulating four datasets, we identified three distinct, targetable drivers — each\nwith a different root cause and a different fix.",
], fontsize=13.5, line_gap=0.06)

findings = [
    ("Finding 1", "Entity_B's high attrition is a\nleadership-trust problem,\nnot a pay problem", "~$5.6M/yr at risk", RED),
    ("Finding 2", "Risk & Compliance is losing its\nmost senior veterans to the\nexternal market", "~$2.6M/yr at risk", GOLD),
    ("Finding 3", "22.5% of active staff are\ndisengaged — and they aren't\nthe ones leaving", "up to $59M/yr exposure", PURPLE),
]
xs = [0.06, 0.395, 0.73]
for (kicker_txt, desc, impact, color), x in zip(findings, xs):
    ax = fig.add_axes([x, 0.10, 0.235, 0.34])
    ax.axis("off")
    box = FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0,rounding_size=0.06",
                          transform=ax.transAxes, facecolor=LIGHT_BG, edgecolor=color, linewidth=1.3)
    ax.add_patch(box)
    ax.text(0.5, 0.87, kicker_txt.upper(), fontsize=10.5, color=color, fontweight="bold", ha="center", va="center", transform=ax.transAxes)
    ax.text(0.5, 0.53, desc, fontsize=12.5, color=DARK, fontweight="bold", ha="center", va="center", transform=ax.transAxes, linespacing=1.5)
    ax.text(0.5, 0.13, impact, fontsize=10.5, color=color, fontweight="bold", ha="center", va="center", transform=ax.transAxes)
save(fig)

# ===========================================================================
# SLIDE 3 — METHOD
# ===========================================================================
fig = new_slide("Our Approach", "Four datasets, triangulated — not taken at face value")
bullet_block(fig, 0.06, 0.76, [
    "employees.csv (13,403), attrition_log.csv (1,400), engagement.csv (56,000 rows / 5 waves),\nperformance.csv (35,000 rows) — joined on employee_id, Jan 2024-Dec 2025 window.",
    "",
    "Key data decisions we made and documented:",
], fontsize=13, line_gap=0.06)
bullet_block(fig, 0.06, 0.55, [
    "Population choice varies by question: active-only for org snapshots, full roster\n(active+departed) for attrition-risk denominators.",
    "stated_exit_reason, regrettable_flag are retrospective HR judgements — used as one\nsignal, always cross-checked against engagement/performance trajectories.",
    "Survey non-response rows are kept, not dropped — non-response turns out to be a\nsignal in its own right (see Finding 3).",
    "We tested and ruled out a 'bad manager' narrative — team-level attrition shows\n~zero correlation with team engagement scores.",
], fontsize=12.5, line_gap=0.058)
save(fig)

# ===========================================================================
# SLIDE 4 — FINDING 1 HEADLINE: Entity_B
# ===========================================================================
fig = new_slide("Finding 1 of 3", "Entity_B's high attrition is a leadership-trust problem, not a pay problem")

gs = gridspec.GridSpec(1, 2, left=0.06, right=0.96, top=0.72, bottom=0.14, wspace=0.35)
ax1 = fig.add_subplot(gs[0])
ent_order = ["Entity_A", "Entity_C", "NovaCorp-Origin", "Entity_B"]
rates = m.groupby("legacy_entity_code")["is_departed"].mean().reindex(ent_order) * 100
colors = [SLATE if e != "Entity_B" else RED for e in ent_order]
bars = ax1.bar(ent_order, rates.values, color=colors, width=0.55)
for b, v in zip(bars, rates.values):
    ax1.text(b.get_x() + b.get_width()/2, v + 0.3, f"{v:.1f}%", ha="center", fontsize=11, fontweight="bold", color=DARK)
ax1.set_ylabel("2-yr attrition rate (%)", fontsize=10)
ax1.set_title("Attrition rate by acquisition cohort", fontsize=12, color=DARK)
ax1.spines[["top","right"]].set_visible(False)
ax1.set_ylim(0, 18)
plt.setp(ax1.get_xticklabels(), fontsize=9.5, rotation=12)

ax2 = fig.add_subplot(gs[1])
dims = ["Manager\neffectiveness","Psych.\nsafety","Recognition","Career\ndev.","Leadership\ntrust","Purpose /\nmeaning","Wellbeing","Confidence\nin future"]
cols = ["avg_manager_effectiveness","avg_psych_safety","avg_recognition","avg_career_dev","avg_leadership_trust","avg_purpose","avg_wellbeing","avg_confidence_future"]
eb = active[active.legacy_entity_code == "Entity_B"][cols].mean()
nc = active[active.legacy_entity_code != "Entity_B"][cols].mean()
x = np.arange(len(dims))
w = 0.36
ax2.bar(x - w/2, nc.values, width=w, label="Rest of company", color=SLATE)
ax2.bar(x + w/2, eb.values, width=w, label="Entity_B", color=RED)
ax2.set_xticks(x); ax2.set_xticklabels(dims, fontsize=8, rotation=20, ha="right")
ax2.set_ylim(2.6, 3.6)
ax2.set_ylabel("Engagement score (1-5)", fontsize=10)
ax2.set_title("Entity_B vs rest of company, by dimension", fontsize=12, color=DARK)
ax2.legend(fontsize=9, frameon=False, loc="lower left")
ax2.spines[["top","right"]].set_visible(False)

fig.text(0.06, 0.055, "Every other dimension is in line with the company — the gap is specifically leadership trust and purpose. Compensation is not the driver: Entity_B's avg compa-ratio (0.96) is above the company average (0.94).", fontsize=10, color=SLATE, style="italic")
save(fig)

# ===========================================================================
# SLIDE 5 — FINDING 1 EVIDENCE / SO WHAT
# ===========================================================================
fig = new_slide("Finding 1 of 3 — So What", "A specific, targetable cohort with a clear financial case")
bullet_block(fig, 0.06, 0.76, [
    "Corroborating signal: Entity_B's survey response rate is 62.6%, vs 83.6% for the\nrest of the company — Entity_B staff are checking out of the HR process itself.",
    "",
    "Among Entity_B's high-value staff (L3+ / HiPo): 15.5% attrition and a 5.1%\nregrettable-flag rate — both the highest of any acquisition cohort.",
], fontsize=13.5, line_gap=0.06)

stat_card(fig, 0.06, 0.13, 0.28, 0.30, "48", "Entity_B high-value\nvoluntary departures (2yr)", fontsize_val=30)
stat_card(fig, 0.365, 0.13, 0.28, 0.30, "$163.8K", "Average salary\nof departed staff", fontsize_val=26)
stat_card(fig, 0.67, 0.13, 0.28, 0.30, "~$5.6M/yr", "Replacement cost exposure\nif unaddressed", fontsize_val=26, value_color=RED)
save(fig)

# ===========================================================================
# SLIDE 6 — FINDING 2 HEADLINE: R&C Director+
# ===========================================================================
fig = new_slide("Finding 2 of 3", "Risk & Compliance is losing its most senior veterans to the external market")

gs = gridspec.GridSpec(1, 2, left=0.16, right=0.96, top=0.72, bottom=0.14, wspace=0.55)
ax1 = fig.add_subplot(gs[0])
dir_nc = m[(m.role_level >= 4) & (m.legacy_entity_code == "NovaCorp-Origin")]
gtab = dir_nc.groupby("department").agg(hc=("employee_id","count"), dep=("is_departed","sum"))
gtab["rate"] = gtab.dep/gtab.hc*100
gtab = gtab.sort_values("rate", ascending=True)
colors = [RED if d == "Risk & Compliance" else SLATE for d in gtab.index]
ax1.barh(gtab.index, gtab["rate"], color=colors)
for i, (idx, row) in enumerate(gtab.iterrows()):
    ax1.text(row["rate"] + 0.4, i, f"{row['rate']:.1f}%", va="center", fontsize=10, fontweight="bold", color=DARK)
ax1.set_xlabel("2-yr attrition rate, Director+ (L4+), NovaCorp-Origin veterans (%)", fontsize=9.5)
ax1.set_title("Director+ attrition by department", fontsize=12, color=DARK)
ax1.spines[["top","right"]].set_visible(False)
ax1.set_xlim(0, 32)
plt.setp(ax1.get_yticklabels(), fontsize=9.5)

ax2 = fig.add_subplot(gs[1])
ax2.axis("off")
rc_dir = m[(m.department=="Risk & Compliance") & (m.role_level>=4) & (m.legacy_entity_code=="NovaCorp-Origin")]
dep = rc_dir[rc_dir.is_departed]
stay = rc_dir[rc_dir.status=="active"]
ax2.set_title("Pay & engagement: departed vs stayed", fontsize=12, color=DARK, pad=20)
rows = [
    ("", "Departed\n(n=12)", "Stayed\n(n=32)"),
    ("Compa-ratio\n(1.0 = midpoint)", f"{dep.compa_ratio.mean():.2f}", f"{stay.compa_ratio.mean():.2f}"),
    ("Engagement score\n(1-5 scale)", f"{dep.final_engagement_score.mean():.2f}", f"{stay.avg_engagement.mean():.2f}"),
    ("Avg tenure", f"{dep.tenure_months.mean()/12:.0f} years", f"{stay.tenure_months.mean()/12:.0f} years"),
]
col_x = [0.0, 0.56, 0.86]
row_y = np.linspace(0.72, 0.15, len(rows))
for ri, row in enumerate(rows):
    weight = "bold" if ri == 0 else "normal"
    fontsize = 10.5 if ri == 0 else 12.5
    color = SLATE if ri == 0 else DARK
    for ci, val in enumerate(row):
        ha = "left" if ci == 0 else "center"
        c = RED if (ri > 0 and ci == 1) else color
        ax2.text(col_x[ci], row_y[ri], val, fontsize=fontsize, fontweight=weight, color=c, ha=ha, va="center", transform=ax2.transAxes)
    if ri == 0:
        ax2.plot([0.0, 1.0], [row_y[ri]-0.10, row_y[ri]-0.10], color=GREY, linewidth=0.8, transform=ax2.transAxes)

fig.text(0.06, 0.055, "Departed staff were paid the same and engaged at least as well as those who stayed — this rules out pay and engagement as the driver.", fontsize=10, color=SLATE, style="italic")
save(fig)

# ===========================================================================
# SLIDE 7 — FINDING 2 SO WHAT
# ===========================================================================
fig = new_slide("Finding 2 of 3 — So What", "A small, identifiable, high-value flight-risk cohort")
bullet_block(fig, 0.06, 0.76, [
    "8 of 12 departures cite \"Career advancement\" or \"Better opportunity\" as exit reason —\nconsistent with the Annual Report's own account that FAR (Financial Accountability\nRegime) has intensified external competition for senior regulatory talent.",
    "",
    "These are long-tenured veterans: average tenure of ~24 years. Each departure carries\ninstitutional and regulatory knowledge that is not captured in the salary cost alone.",
], fontsize=13.5, line_gap=0.06)
stat_card(fig, 0.06, 0.13, 0.28, 0.30, "27.3%", "Attrition rate — 2x the next-\nhighest department/level cohort", fontsize_val=28, value_color=RED)
stat_card(fig, 0.365, 0.13, 0.28, 0.30, "12 of 44", "Veteran Directors lost\n(2-year window)", fontsize_val=26)
stat_card(fig, 0.67, 0.13, 0.28, 0.30, "~$2.6M/yr", "Replacement cost, excluding\nknowledge-loss risk", fontsize_val=26, value_color=RED)
save(fig)

# ===========================================================================
# SLIDE 8 — FINDING 3 HEADLINE: Stay-but-disengaged
# ===========================================================================
fig = new_slide("Finding 3 of 3", "22.5% of active staff are disengaged — and they aren't the ones leaving")

gs = gridspec.GridSpec(1, 2, left=0.17, right=0.96, top=0.72, bottom=0.14, wspace=0.5)
ax1 = fig.add_subplot(gs[0])
dept_dis = active.groupby("department")["is_persistently_disengaged"].mean().sort_values(ascending=True) * 100
colors = [RED if v > 25 else SLATE for v in dept_dis.values]
ax1.barh(dept_dis.index, dept_dis.values, color=colors)
for i, v in enumerate(dept_dis.values):
    ax1.text(v + 0.5, i, f"{v:.1f}%", va="center", fontsize=10, fontweight="bold", color=DARK)
ax1.set_xlabel("% of active staff persistently disengaged", fontsize=9.5)
ax1.set_title("Sustained disengagement by department", fontsize=12, color=DARK)
ax1.spines[["top","right"]].set_visible(False)
ax1.set_xlim(0, 42)
plt.setp(ax1.get_yticklabels(), fontsize=9.5)

ax2 = fig.add_subplot(gs[1])
labels = ["Voluntary\nleavers", "Active\nstaff (stayed)"]
vals = [m.loc[m.is_voluntary==True, "final_engagement_score"].mean(), active.avg_engagement.mean()]
bars = ax2.bar(labels, vals, color=[GOLD, SLATE], width=0.5)
for b, v in zip(bars, vals):
    ax2.text(b.get_x()+b.get_width()/2, v+0.03, f"{v:.2f}", ha="center", fontsize=12, fontweight="bold", color=DARK)
ax2.set_ylim(0, 4.2)
ax2.set_ylabel("Avg engagement score (1-5)", fontsize=10)
ax2.set_title("Leavers vs stayers: almost no gap", fontsize=12, color=DARK)
ax2.spines[["top","right"]].set_visible(False)

fig.text(0.06, 0.055, "Attrition data alone would completely miss this problem: people who are disengaged mostly stay, not leave.", fontsize=10, color=SLATE, style="italic")
save(fig)

# ===========================================================================
# SLIDE 9 — FINDING 3 EVIDENCE + SENSITIVITY + LIMITATION
# ===========================================================================
fig = new_slide("Finding 3 of 3 — So What", "Sizing the exposure honestly: it depends where you draw the line")

gs = gridspec.GridSpec(1, 2, left=0.06, right=0.96, top=0.72, bottom=0.20, wspace=0.35)
ax1 = fig.add_subplot(gs[0])
elig = active[active.n_responses.fillna(0) >= 2]
threshs = [2.5, 2.75, 3.0, 3.25]
hc = []
cost = []
for t in threshs:
    seg = elig[elig.avg_engagement < t]
    hc.append(len(seg))
    cost.append((loaded(seg.salary) * LOSS_RATE).sum() / 1e6)
bars = ax1.bar([f"<{t}" for t in threshs], cost, color=[GOLD, GOLD, RED, SLATE])
for b, c, h in zip(bars, cost, hc):
    ax1.text(b.get_x()+b.get_width()/2, c+1.5, f"${c:.0f}M\n({h:,} ppl)", ha="center", fontsize=9.5, fontweight="bold", color=DARK)
ax1.axhline(15, color=GREEN, linestyle="--", linewidth=1.3)
ax1.text(3.35, 16, "Finance's $12-15M\nestimate", fontsize=8.5, color=GREEN, ha="center")
ax1.set_xlabel("Disengagement threshold (composite score)", fontsize=9.5)
ax1.set_ylabel("Annualised exposure ($M)", fontsize=10)
ax1.set_title("Exposure is highly threshold-sensitive", fontsize=11.5, color=DARK)
ax1.spines[["top","right"]].set_visible(False)
ax1.set_ylim(0, 100)

ax2 = fig.add_subplot(gs[1])
ax2.axis("off")
bullet_block(fig, 0.535, 0.68, [
    "Finance's $12-15M implies a severe-only\npopulation (~6% of staff, score <2.5) —\nwe find nearly 4x that many showing\nsustained disengagement.",
    "",
    "Actionable target: bottom decile\n(1,156 people, ~$25M/yr exposure).",
    "",
    "Limitation: goal-achievement scores do\nnot differ significantly between\ndisengaged and engaged staff (p=0.16).\nThis is a population-size estimate under\nFinance's own assumption — not a proven\noutput deficit.",
], fontsize=11.5, line_gap=0.052)
save(fig)

# ===========================================================================
# SLIDE 10 — QUICK WIN: HIRING INEFFICIENCY
# ===========================================================================
fig = new_slide("Quick Win", "Agency hiring costs more, with no speed benefit and slightly worse retention")

gs = gridspec.GridSpec(1, 2, left=0.06, right=0.96, top=0.72, bottom=0.14, wspace=0.35)
ax1 = fig.add_subplot(gs[0])
win_start = pd.Timestamp("2024-01-01")
hires_window = m[m.hire_date >= win_start]
agency_hires = hires_window[hires_window.hire_source == "agency"]
agency_cost = (agency_hires.salary * AGENCY_FEE).sum() / 1e6
direct_bench = len(agency_hires) * DIRECT_COST / 1e6
bars = ax1.bar(["Actual agency\nfee cost", "Direct-hire\nbenchmark"], [agency_cost, direct_bench], color=[RED, GREEN], width=0.5)
for b, v in zip(bars, [agency_cost, direct_bench]):
    ax1.text(b.get_x()+b.get_width()/2, v+0.1, f"${v:.1f}M", ha="center", fontsize=13, fontweight="bold", color=DARK)
ax1.set_title(f"Cost of {len(agency_hires)} agency hires, 2-yr window", fontsize=12, color=DARK)
ax1.set_ylabel("$M, 2-yr total", fontsize=10)
ax1.spines[["top","right"]].set_visible(False)

ax2 = fig.add_subplot(gs[1])
dtf = hires_window.groupby("hire_source")["days_to_fill"].mean().reindex(["agency","direct","referral","acquisition"]).dropna()
bars = ax2.bar(dtf.index, dtf.values, color=SLATE, width=0.5)
for b, v in zip(bars, dtf.values):
    ax2.text(b.get_x()+b.get_width()/2, v+1, f"{v:.0f}d", ha="center", fontsize=11, fontweight="bold", color=DARK)
ax2.set_title("Days-to-fill: no speed advantage for agency", fontsize=12, color=DARK)
ax2.set_ylabel("Avg days to fill", fontsize=10)
ax2.spines[["top","right"]].set_visible(False)
ax2.set_ylim(0, max(dtf.values)*1.3)

fig.text(0.06, 0.055, "Excess agency cost is about \\$2.3M/yr in fees, plus about \\$2.3M/yr in poor-match early-exit backfill, about \\$4.6M/yr total — closely matches Finance's own \\$4-6M estimate.", fontsize=10, color=SLATE, style="italic")
save(fig)

# ===========================================================================
# SLIDE 11 — FINANCIAL SYNTHESIS
# ===========================================================================
fig = new_slide("Putting It Together", "The recomputed $42M: two buckets need re-calibrating")

ax = fig.add_axes([0.06, 0.16, 0.88, 0.62])
ax.axis("off")
headers = ["Component", "Finance estimate", "Data-derived (annualised)", "Read"]
rows = [
    ["Regrettable attrition\n(HR-flagged, strict)", "$22-25M", "$14.3M", "Likely under-flagged by HR"],
    ["Regrettable attrition\n(all high-value voluntary)", "—", "$30.6M", "Broader lens exceeds estimate"],
    ["Disengagement loss\n(severe, <2.5 score)", "$12-15M", "$15.4M", "Matches Finance closely"],
    ["Disengagement loss\n(sustained, <3.0 score)", "—", "up to $59.3M", "Long tail not yet budgeted"],
    ["Hiring inefficiency", "$4-6M", "$4.6M", "Well-calibrated already"],
]
col_x = [0.02, 0.36, 0.58, 0.82]
col_ha = ["left", "center", "center", "left"]
y0 = 0.94
row_h = 0.155
for ci, h in enumerate(headers):
    ax.text(col_x[ci], y0, h, fontsize=11.5, fontweight="bold", color=WHITE, ha=col_ha[ci], transform=ax.transAxes)
ax.add_patch(FancyBboxPatch((0, y0-0.06), 1, 0.10, boxstyle="square,pad=0", transform=ax.transAxes, facecolor=PURPLE, edgecolor="none", zorder=0))
for ci, h in enumerate(headers):
    ax.text(col_x[ci], y0, h, fontsize=11.5, fontweight="bold", color=WHITE, ha=col_ha[ci], transform=ax.transAxes, zorder=1)
for ri, row in enumerate(rows):
    yy = y0 - 0.16 - ri*row_h
    bg = LIGHT_BG if ri % 2 == 0 else WHITE
    ax.add_patch(FancyBboxPatch((0, yy-0.065), 1, row_h-0.01, boxstyle="square,pad=0", transform=ax.transAxes, facecolor=bg, edgecolor="none", zorder=0))
    for ci, val in enumerate(row):
        color = DARK if ci != 2 else PURPLE
        weight = "bold" if ci == 2 else "normal"
        ax.text(col_x[ci], yy, val, fontsize=10.5, color=color, fontweight=weight, ha=col_ha[ci], va="center", transform=ax.transAxes, zorder=1)
fig.text(0.06, 0.075, "Key takeaway: HR's own retrospective 'regrettable' label likely undercounts true cost, while disengagement carries a much larger long tail than currently priced in.", fontsize=10.5, color=SLATE, style="italic")
save(fig)

# ===========================================================================
# SLIDE 12 — RECOMMENDATIONS ROADMAP
# ===========================================================================
fig = new_slide("Our Recommendation", "A 90-day, sequenced plan — not a blanket program")

cards = [
    ("NOW (0-30 days)", "$0 incremental cost", "Deploy a disengagement early-warning trigger",
     "Flag anyone completing <60% of surveys for a manager check-in within 2 weeks.\nThis signal predicts voluntary exit 3x better than the score itself (21.2% vs 6.8%).\nPilot in Corp Ops, Risk & Compliance, Insurance first.", GREEN),
    ("THIS QUARTER", "Protects ~$5.6M/yr", "Entity_B Leadership Reconnection Programme",
     "ELT roadshow + listening tour for Entity_B (prioritise 354 high-value staff).\nTargets leadership trust (3.05→3.38) and purpose (3.06→3.38), not pay.\nTimed to the Q2 FY26 integration completion already committed to.", PURPLE),
    ("THIS QUARTER (parallel)", "Protects ~$2.6M/yr", "Critical Regulatory Talent Retention track",
     "External market compensation benchmarking for R&C Director+ (44 people).\nAccelerated recognition + succession/knowledge-transfer safety net.\nAddresses external FAR-driven poaching, not an internal engagement gap.", RED),
]
y_starts = [0.585, 0.345, 0.105]
for (badge, impact, title, body, color), y in zip(cards, y_starts):
    ax = fig.add_axes([0.055, y, 0.9, 0.205])
    ax.axis("off")
    box = FancyBboxPatch((0,0), 1, 1, boxstyle="round,pad=0,rounding_size=0.04", transform=ax.transAxes, facecolor=LIGHT_BG, edgecolor=color, linewidth=1.3)
    ax.add_patch(box)
    ax.text(0.02, 0.78, badge, fontsize=10, fontweight="bold", color=color, transform=ax.transAxes)
    ax.text(0.98, 0.78, impact, fontsize=10, fontweight="bold", color=color, ha="right", transform=ax.transAxes)
    ax.text(0.02, 0.52, title, fontsize=13.5, fontweight="bold", color=DARK, transform=ax.transAxes)
    ax.text(0.02, 0.10, body, fontsize=9.3, color=SLATE, transform=ax.transAxes, va="bottom", linespacing=1.6)
save(fig)

# ===========================================================================
# SLIDE 13 — EXPECTED IMPACT
# ===========================================================================
fig = new_slide("Expected Impact", "What happens if NovaCorp acts")
stat_card(fig, 0.045, 0.42, 0.30, 0.32, "~$10.5M/yr", "Protected replacement cost:\nEntity_B + R&C Director+ cohorts\nnormalised to company-average attrition", value_color=GREEN, fontsize_val=24)
stat_card(fig, 0.35, 0.42, 0.30, 0.32, "~$25M/yr", "Disengagement exposure addressed\nby targeting the bottom-decile\ncohort (1,156 people) first", value_color=GOLD, fontsize_val=24)
stat_card(fig, 0.655, 0.42, 0.30, 0.32, "~$2.3M/yr", "Hiring-fee savings from shifting\ndiscretionary agency hires to\ndirect/referral pipelines", value_color=PURPLE, fontsize_val=24)
bullet_block(fig, 0.06, 0.30, [
    "Measurement: Entity_B leadership_trust & purpose_meaning scores, and Entity_B\nvoluntary attrition rate, tracked at the next 2 survey waves.",
    "R&C Director+ retention rate and time-to-fill for critical regulatory roles.",
    "Bottom-decile disengagement headcount, tracked wave-over-wave.",
    "Agency vs direct/referral hire mix, tracked quarterly.",
], fontsize=12.5, line_gap=0.052)
save(fig)

# ===========================================================================
# SLIDE 14 — LIMITATIONS
# ===========================================================================
fig = new_slide("What We Can't Conclude", "Limitations, stated explicitly")
bullet_block(fig, 0.06, 0.78, [
    "Dataset-derived voluntary attrition (~5%/yr) is materially lower than the Annual\nReport's headline figure (10.4% FY2025). We treat the CSV datasets as ground truth per\nthe Case Brief; the Annual Report is used only for qualitative context.",
    "",
    "stated_exit_reason, regrettable_flag and performance_band_at_exit are retrospective\nHR judgements, not verified fact — used as one signal, cross-checked against\nengagement/performance trajectories, never taken alone.",
    "",
    "Disengagement's link to measured output (goal_achievement_score) is not statistically\nsignificant in this data (p=0.16) — our $ estimate sizes the population under Finance's\nflat-rate assumption; it does not prove a current productivity deficit.",
    "",
    "We tested and ruled out a manager-driven attrition narrative (correlation ≈ 0 between\nteam engagement and team attrition) — deliberately not pursued further.",
    "",
    "2025-H2 performance reviews are absent from the data; no claims made about the most\nrecent half-year of performance.",
], fontsize=12, line_gap=0.052)
save(fig)

# ===========================================================================
# SLIDE 15 — CLOSING
# ===========================================================================
fig = plt.figure(figsize=FIGSIZE, dpi=150)
fig.patch.set_facecolor(DARK)
fig.text(0.5, 0.78, "The $42M is not one problem. It's three, and we know where they live.", fontsize=22, color=WHITE, ha="center", fontweight="bold", wrap=True)
fig.add_artist(plt.Line2D([0.30, 0.70], [0.68, 0.68], color=PURPLE, linewidth=2, transform=fig.transFigure))
recap = [
    "Entity_B: leadership trust & purpose, not pay  —  ~$5.6M/yr at risk",
    "Risk & Compliance Director+: external market poaching  —  ~$2.6M/yr at risk",
    "Stay-but-disengaged: 22.5% of active staff, largely invisible to exit data  —  up to $59M/yr exposure",
    "Quick win: redirect agency hiring  —  ~$2.3M/yr saved, funds the rest",
]
for i, r in enumerate(recap):
    fig.text(0.5, 0.54 - i*0.075, r, fontsize=13.5, color="#D9C4F7", ha="center")
fig.text(0.5, 0.15, "Thank you — questions welcome.", fontsize=15, color=WHITE, ha="center")
fig.text(0.5, 0.06, "NovaCorp People Analytics Challenge  |  Accenture x SUBAA 2026", fontsize=10, color="#8A7AB0", ha="center")
SLIDE_NUM[0] += 1
save(fig, facecolor=DARK)

# ===========================================================================
# APPENDIX A — DATA & POPULATION DECISIONS
# ===========================================================================
fig = new_slide("Appendix A", "Data sources & population decisions")
bullet_block(fig, 0.06, 0.78, [
    "employees.csv (13,403 rows, active+departed), attrition_log.csv (1,400), engagement.csv\n(55,971 rows, 5 waves), performance.csv (34,979 rows). Joined on employee_id.\nObservation window: 1 Jan 2024 - 31 Dec 2025.",
    "",
    "Org snapshot analysis -> active-only population (n=12,003).",
    "Attrition-rate analysis -> full roster, active+departed (n=13,403), since departed\nstaff were part of the workforce-at-risk before leaving.",
    "Hiring-channel analysis -> hires within the observation window only, excluding\n'acquisition' hire_source (M&A transfers, not discretionary recruiting decisions).",
    "Engagement-trend analysis -> employees with >=2 completed survey waves.",
    "response_flag=False rows retained, not dropped — treated as a signal (see Finding 3).",
], fontsize=12, line_gap=0.052)
save(fig)

# ===========================================================================
# APPENDIX B — EQUITY / ETHICS CHECKS
# ===========================================================================
fig = new_slide("Appendix B", "Equity & ethics checks performed — no red flags found")
gender_tab = m.groupby("gender").agg(headcount=("employee_id","count"), avg_compa=("compa_ratio","mean"), attr=("is_departed","mean"))
ax = fig.add_axes([0.06, 0.20, 0.5, 0.55]); ax.axis("off")
ax.set_title("By gender", fontsize=12, color=DARK, loc="left")
rows_txt = [("Gender","Headcount","Avg compa","Attrition")]
for g, row in gender_tab.iterrows():
    rows_txt.append((g, f"{int(row.headcount):,}", f"{row.avg_compa:.2f}", f"{row.attr*100:.1f}%"))
for ri, row in enumerate(rows_txt):
    yy = 0.92 - ri*0.14
    weight = "bold" if ri==0 else "normal"
    for ci, val in enumerate(row):
        ax.text([0.0,0.4,0.65,0.85][ci], yy, val, fontsize=10, fontweight=weight, transform=ax.transAxes)
bullet_block(fig, 0.62, 0.70, [
    "No material gender pay gap: compa-ratio\nflat across gender within the same role\nlevel (e.g. L3: F 0.947 vs M 0.946).",
    "",
    "No material gender attrition gap.",
    "",
    "Female representation at L5+ in this\ndataset (59.2%) differs from the Annual\nReport figure (34.1%) — a documented\ndata/report discrepancy, not evidence of\nbias in either direction.",
], fontsize=11, line_gap=0.052, width=0.35)
save(fig)

# ===========================================================================
# APPENDIX C — MANAGER CLUSTERING RULED OUT
# ===========================================================================
fig = new_slide("Appendix C", "We tested a 'bad manager' narrative — the data does not support it")
mgr_stats = m.groupby("manager_id").agg(team_size=("employee_id","count"), departed=("is_departed","sum"), avg_team_engagement=("avg_engagement","mean")).reset_index()
mgr_stats = mgr_stats[mgr_stats.team_size >= 5]
mgr_stats["attrition_rate"] = mgr_stats.departed/mgr_stats.team_size
ax = fig.add_axes([0.10, 0.16, 0.75, 0.58])
ax.scatter(mgr_stats.avg_team_engagement, mgr_stats.attrition_rate*100, alpha=0.4, color=PURPLE, s=25)
ax.set_xlabel("Manager's average team engagement score", fontsize=10.5)
ax.set_ylabel("Manager's team attrition rate (%)", fontsize=10.5)
ax.set_title(f"n={len(mgr_stats)} managers with >=5 direct reports  |  correlation = {mgr_stats[['avg_team_engagement','attrition_rate']].corr().iloc[0,1]:.3f}", fontsize=11, color=SLATE)
ax.spines[["top","right"]].set_visible(False)
fig.text(0.06, 0.08, "45.1% of managers with 5+ reports had zero attrition in the window; their average team engagement (3.37) is statistically indistinguishable from the highest-attrition decile (3.36). We deliberately did not build a manager-performance narrative on this basis.", fontsize=10, color=SLATE, style="italic")
save(fig)

# ===========================================================================
# APPENDIX D — DETAILED SEGMENT TABLES
# ===========================================================================
fig = new_slide("Appendix D", "Attrition rate by department and acquisition cohort")
ct_hc = pd.crosstab(m.department, m.legacy_entity_code)
ct_dep = pd.crosstab(m.department, m.legacy_entity_code, values=m.is_departed, aggfunc="sum")
rate_tab = (ct_dep/ct_hc*100).round(1)
ax = fig.add_axes([0.06, 0.15, 0.88, 0.62]); ax.axis("off")
cols = ["Entity_A","Entity_B","Entity_C","NovaCorp-Origin"]
rate_tab = rate_tab[cols]
header = ["Department"] + cols
col_x = [0.0, 0.32, 0.48, 0.64, 0.82]
ax.text(col_x[0], 0.95, header[0], fontsize=11, fontweight="bold", transform=ax.transAxes)
for ci, h in enumerate(cols):
    ax.text(col_x[ci+1], 0.95, h, fontsize=11, fontweight="bold", transform=ax.transAxes, ha="center")
ax.plot([0,1],[0.90,0.90], color=GREY, linewidth=0.8, transform=ax.transAxes)
for ri, (dept, row) in enumerate(rate_tab.iterrows()):
    yy = 0.90 - (ri+1)*0.115
    ax.text(col_x[0], yy, dept, fontsize=10.5, transform=ax.transAxes)
    for ci, v in enumerate(row):
        color = RED if v >= 15 else (GOLD if v>=13 else DARK)
        ax.text(col_x[ci+1], yy, f"{v:.1f}%", fontsize=10.5, color=color, fontweight="bold" if color!=DARK else "normal", transform=ax.transAxes, ha="center")
fig.text(0.06, 0.08, "Entity_B x Risk & Compliance and Entity_B x Corporate Operations are the two highest cells in the matrix, both above 16%.", fontsize=10, color=SLATE, style="italic")
save(fig)

pdf.close()
print("Saved full deck -> deck/NovaCorp_CHRO_Deck.pdf")
print(f"Total slides: {SLIDE_NUM[0]}")
