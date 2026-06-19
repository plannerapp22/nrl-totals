# NRL Totals Model — SKILL.md
# Model v2.0 | Effective Round 17, 2026
# See METHODOLOGY.md for full spec. This file is the operational build guide.

## What This Skill Does
Generates the weekly NRL totals model report (index.html) for plannerapp22/nrl-totals → Netlify.
Analyses combined scoring totals for each game and produces verdicts with confidence scores.
Output is read by people betting real money — accuracy and clarity are the priority over volume of picks.

---

## Data Sources (load in this order)

### Persistent (load from /data — do NOT re-pull if already current)
- /data/h2h.json         — H2H records vs market line, 2025–26
- /data/season_averages.json — Per-team 2026 averages (scored, conceded, home/away, O/U rate)
- /data/venues.json      — Venue scoring tendencies
- /data/track_record.json — Pick history from v2.0 onwards

### Weekly pulls (fresh each round)
- Current round fixtures, times, venues
- Market lines (Bet365 / Sportsbet)
- Confirmed team lists (NRL.com, Thursday/Friday)
- Last round results → use to UPDATE persistent data files before generating report
- Origin / injury flags

### Data update order
1. Add last round results to h2h.json (relevant matchup only)
2. Add last round results to season_averages.json (incremental — do not recalculate from scratch)
3. Flag any Origin or injury news
4. THEN generate the report

---

## Signal Hierarchy (contextual — not fixed weights)

### Primary: Current 2026 Form (last 5 games each team)
- Avg points scored / conceded
- O/U rate vs own season average
- Home/away split if trend exists
- Blowouts (combined 30+ above line): flag as outlier unless 3+ times this season

### Secondary: H2H Record vs Market Line (2025–26)
- O/U record expressed as "X unders, Y overs from Z games"
- Avg actual combined vs avg market line — gap of 3+ pts strengthens signal
- If fewer than 3 H2H games in 2025–26: flag low confidence, lean on team form

### Tertiary: Line Level vs 2026 Season Baseline
- Is today's line elevated or depressed vs 2026 season average for similar matchups?
- Elevated line → strengthens under. Depressed → strengthens over.
- Compare to 2026 season average (NOT historical matchup average — lines shift year to year)

### Recency Weighting
- 2026 data: 1.0x weight
- 2025 data: 0.6x weight

### Conflict Resolution
- Recent 2026 form beats historical H2H — always
- Conflicting signals of similar weight → WATCH with explanation
- Single strong signal + weak contradicting signals → LEAN (not BET)

---

## Confidence Scoring

Assign a composite % score based on signal alignment, strength, and sample size.

| Verdict           | Threshold | Line type         |
|-------------------|-----------|-------------------|
| STRONG BET UNDER/OVER | 75%+  | Standard bookie line |
| BET UNDER/OVER    | 65–74%    | Standard bookie line |
| LEAN UNDER/OVER   | 55–64%    | Standard bookie line |
| ADJUSTED UNDER/OVER | 65%+   | Alternate/adjusted line |
| WATCH             | 45–54% or conflicting | — |
| PASS              | <45%      | No edge           |

Show confidence % next to every verdict.

---

## Overlays

- **Origin**: Flag if 3+ players per team backing up. Reduce confidence one tier.
- **Injuries**: Note significant absences (starting halfback, fullback, or 80%+ starter). Flag only — no manual capture.
- **Venue**: Include if pattern exists. Skip otherwise.
- **Weather**: Flag heavy rain for over picks.
- **Blowouts**: Flag individual outliers. If 3+ this season = pattern, include in signal.

---

## Multi Section (NOT parlay — Australian terminology)

Auto-select multi legs at 80%+ confidence, aiming for 90s.
Almost always means adjusted lines — standard lines rarely reach 80%.
LEAN picks never go in a multi. BET picks noted as singles only.

### Adjusted Line Derivation
Do NOT choose adjusted lines arbitrarily. Derive from historical distribution:
1. Collect all 2025–26 results for the matchup or team signal being used
2. Find the line where 85–90% of results would have landed on the correct side
3. That is the adjusted line — show the reasoning explicitly
   Example: "Adjusted to Under 60.5 — 9 of 10 games (90%) in 2025–26 finished below this total"

### Multi Display
For each leg: game + direction, adjusted line + reasoning, approx odds, confidence score.
Show approx combined multi odds (guide only — verify with bookmaker).
Show standard line odds separately for comparison — not as a multi recommendation.

---

## Data Display Rules

- O/U record: "4 unders, 3 overs from 7 games" — NEVER "4U/3O" (reads as "4U/30")
- Confidence: always show as a percentage (e.g. 72%)
- Verdict labels: use exactly as defined above — no variations
- Sample size: always show how many games the signal is based on

---

## Writing Standard

Every analysis must be readable by someone who did not build the model.
- Every verdict has a plain-English rationale
- PASS and WATCH include reasons — explain what you'd be betting against
- Do not force picks. Two clean picks beats seven questionable ones.
- People are betting real money. Only put forward a call if the data supports it.

---

## Staging Workflow

1. Generate HTML → write to local outputs folder for preview
2. Ben reviews in browser → approves
3. Push to GitHub → Netlify auto-deploys
4. Update data/track_record.json with the round's picks

---

## Repo Structure

plannerapp22/nrl-totals/
├── index.html          ← Current round report (main page)
├── history.html        ← Track record and past rounds
├── tryscorers.html     ← Try scorer picks (separate model)
├── METHODOLOGY.md      ← Full methodology spec (human-readable)
├── SKILL.md            ← This file (operational build guide)
├── CHANGELOG.md        ← Version history
└── data/
    ├── h2h.json            ← H2H records 2025–26
    ├── season_averages.json ← Per-team 2026 averages
    ├── venues.json          ← Venue tendencies
    └── track_record.json    ← Pick history v2.0+

---

## Version
Model: v2.0
Effective: Round 17, 2026
