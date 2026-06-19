# NRL Totals Model — Methodology Spec v2.0

**Status:** DRAFT — awaiting Ben's approval before implementation  
**Version:** 2.0  
**Effective from:** Round 17, 2026  
**Last updated:** 19 Jun 2026

---

## Purpose

This document defines exactly how the NRL Totals Model works. Every pick on the page should be traceable back to this spec. When someone asks "why did the model call that?", this document is the answer. It is also the locked reference for anyone building or regenerating the report — changes to the model logic must be made here first and approved before the HTML is updated.

---

## 1. Data Scope

**Years included:** 2025 and 2026 season data only.

**Recency weighting:**
- 2026 data: full weight
- 2025 data: 60% weight (used to inform trends but not override current season signals)

**Why two years?** One year alone may not have enough H2H matchups to establish a pattern. Two years with recency weighting gives sample depth while keeping the model anchored to how teams are actually performing now.

**Data sources:**
- Market lines and historical results: ausSportsBetting.com
- Current round fixtures and lines: Bet365 / Sportsbet
- Team form and results: NRL.com
- Team sheets: NRL.com (confirmed Thursday/Friday)

---

## 2. Signal Hierarchy

Signals are combined contextually — no fixed percentage weights. When signals align, confidence increases. When they conflict, confidence decreases or the pick defaults to WATCH. The hierarchy below describes which signals carry more authority when they conflict.

### 2.1 Primary — Current Season Form (2026)
The most important signal. What are these teams doing *right now* in 2026?

For each team, last 5 games:
- Average points scored
- Average points conceded
- Over/under rate against their own 2026 season scoring average
- Home/away split, if a meaningful trend exists (e.g. a team that defends well at home but leaks points away)

Blowouts (combined score 30+ above the line) are flagged as outliers and excluded from averages unless the team is producing or conceding them consistently (3+ times in a season = a pattern, not an outlier).

### 2.2 Secondary — H2H Record vs Market Line (2025–26)
How have these two specific teams performed against the bookmaker's line when they've played each other?

Tracked as:
- O/U record (e.g. 3U/2O)
- Average actual combined score vs average market line for that matchup
- The gap between the two (persistent gap of 3+ points in either direction strengthens the signal)

**Sample size matters:** If H2H games in the 2025–26 window are fewer than 3, this signal is flagged as low-confidence and team form (Section 2.1) carries proportionally more weight. A note is shown on the page explaining this.

### 2.3 Tertiary — Line Level vs 2026 Season Baseline
Is the bookmaker's line for this game elevated or depressed compared to what similar games have been priced at this season?

This is not compared to the historical average for that specific matchup (because line levels shift year to year across the competition). It is compared to the 2026 season average line for games involving similar team types.

- Line significantly above season baseline → strengthens under case
- Line significantly below season baseline → strengthens over case

### 2.4 Conflict Resolution
When signals disagree, the following rules apply:

1. **Recent form beats historical H2H.** If two teams were low-scoring matchups in 2025 but both are averaging 10 more points per game in 2026, current form wins. The H2H history is noted but not the basis for the call.

2. **Conflicting signals of similar weight → WATCH.** If form says under but H2H says over and neither is dominant, the pick is WATCH with a clear explanation of both sides.

3. **Single strong signal + weak contradicting signals = directional pick, lower confidence.** Shown as LEAN rather than BET.

---

## 3. Overlays

Overlays do not override the primary signals. They adjust confidence up or down, or flag uncertainty.

### 3.1 Origin / Representative Football
Players backing up from representative games (State of Origin, Test matches) in the prior week:
- Flag shown on the game note
- Reduces confidence by one tier if 3+ players per team are backing up (e.g. BET → LEAN)
- Only relevant for approximately the first two rounds post-Origin

### 3.2 Injuries
Significant player absences (first-choice halfback, fullback, or forward who has started 80%+ of games) are noted on the game analysis. No manual capture required — flag if publicly confirmed. Add a standard disclaimer to check team lists before betting.

### 3.3 Venue
Included if a meaningful scoring pattern exists at the venue (e.g. a ground known for poor surfaces or low-scoring conditions). Noted as supporting context, not a primary signal.

### 3.4 Weather
Flagged if heavy rain is forecast. Reduces confidence in over picks. Does not generate a pick change on its own — noted as a risk to monitor.

### 3.5 Blowout Flags
Any result 30+ combined points above the match line in recent history is flagged. If a team has produced or conceded 3+ blowouts in 2026, this is noted as a pattern rather than an outlier.

---

## 4. Confidence & Verdict System

### 4.1 Confidence Score
Each pick is assigned a composite confidence score (expressed as a percentage) based on how many signals align, signal strength, and sample size. This percentage is shown on the page next to every verdict.

### 4.2 Verdict Tiers

| Verdict | Confidence | What it means |
|---|---|---|
| **STRONG BET UNDER / OVER** | 75%+ | Multiple strong signals aligned. Highest conviction pick. Standard bookmaker line. |
| **BET UNDER / OVER** | 65–74% | Clear directional signal with supporting evidence. Standard bookmaker line. |
| **LEAN UNDER / OVER** | 55–64% | Moderate signal. One or more factors support the direction but not without risk. Standard line. |
| **ADJUSTED UNDER / OVER** | 65%+ | The directional signal is strong but the standard line is too tight. Pick is on an alternate/adjusted line with reasoning for why that line is the better play. |
| **WATCH** | 45–54%, or conflicting signals | No confident direction. Noted with explanation — useful for people who want context but not a bet. |
| **PASS** | Below 45%, or well-calibrated line | No meaningful edge. Skip this game. |

### 4.3 Explaining the System to Readers
The page includes a short methodology box (visible on load, expandable for full detail) that explains:
- What the confidence percentage means
- The difference between BET and LEAN
- What ADJUSTED means and why the alternate line is being recommended
- That PASS and WATCH are valid outputs — the model does not force picks

---

## 5. Multi Section

### 5.1 What a multi is
A multi (known as a multi in American betting) combines multiple legs into a single bet — all legs must win for the bet to pay out. Because of this, only the highest-confidence picks belong in a multi. Lower-confidence picks should never be included just to inflate the odds.

### 5.2 Auto-selection threshold
Multi legs are auto-selected at **80% confidence minimum**, aiming for 90%+ where possible. This will almost always mean adjusted lines rather than standard bookmaker lines, because standard lines are rarely priced at a level where the model reaches 80%+ confidence.

LEAN picks (55–64%) are never included in multi recommendations. BET picks (65–74%) may be noted as optional single bets but are not included in the multi.

### 5.3 Adjusted Line Methodology
The adjusted line is not chosen arbitrarily. It is derived from the historical result distribution:

1. Collect all 2025–26 results for the matchup or team (whichever signal is being used)
2. Find the line at which 85–90% of historical results would have landed on the correct side
3. That line becomes the recommended adjusted line for the multi leg

**Example:** A team's last 10 combined scores in relevant games: [52, 48, 61, 44, 55, 49, 58, 46, 53, 50]. If targeting under, at what line do 9 of 10 (90%) land under? Answer: under 60.5. That's the adjusted line to recommend.

Show the reasoning explicitly: "Adjusted to Under 60.5 — 9 of 10 games (90%) in 2025–26 have finished below this total."

### 5.4 Multi display format
For each leg in the recommended multi:
- Game and direction (e.g. Storm v Raiders — Under)
- Adjusted line and why it was chosen (e.g. Under 52.5 — 88% of 2025–26 H2H results landed here)
- Approximate odds at the adjusted line
- Confidence score

Show approximate combined multi odds as a guide. Note that prices are estimates — verify with your bookmaker before placing.

Standard line odds are shown separately for comparison only, not as a recommendation for the multi.

---

## 6. Track Record

From Round 17 onwards, every pick is tracked:

| Field | Detail |
|---|---|
| Round | Which round |
| Game | Teams |
| Verdict | e.g. BET UNDER 51.5 (72%) |
| Result | Actual combined score |
| Line | Bookmaker line at time of pick |
| Outcome | WIN / LOSS |
| Margin | How far over/under the line the result landed |
| Notes | Why it was right or wrong |

ROI at standard odds and hit rate by tier (STRONG BET, BET, LEAN) are calculated and displayed on the history page.

---

## 7. Data Caching Strategy

Not all data needs to be pulled fresh each week. Separating static from dynamic data reduces weekly task complexity and makes each round's report faster to generate.

### 7.1 Persistent Data (store in repo, update incrementally)

| Data | How often it changes | Action |
|---|---|---|
| H2H records (2025–26) | Only when those two teams play each other | Store in `data/h2h.json`. Update only the relevant matchup after each round. |
| Season averages per team | Rolls forward each week | Store running totals in `data/season_averages.json`. Add last week's result, don't recalculate from scratch. |
| Venue scoring tendencies | Effectively static per season | Store in `data/venues.json`. Review once at start of season. |
| Home/away splits per team | Rolls forward | Store in `data/season_averages.json` alongside season averages. |
| 2025 full-season data | Static — season is complete | Store in `data/h2h_2025.json`. Never needs to be re-pulled. |

### 7.2 Weekly Pulls (fresh each round)

| Data | Why it needs to be fresh |
|---|---|
| Current round fixtures and lines | New each week |
| Confirmed team lists | Changes Thursday/Friday each week |
| Last round results | Needed to update the persistent store |
| Origin / injury flags | Situational, changes week to week |

### 7.3 Weekly Task Flow

1. Pull last round results → update `data/h2h.json` and `data/season_averages.json`
2. Pull current round fixtures and market lines
3. Pull confirmed team lists + flag Origin/injury
4. Load persistent data files
5. Generate report from combined dataset
6. Write HTML locally for preview
7. Ben approves → push to GitHub → Netlify deploys

This means the bulk of the historical computation happens once, not every week.

---

## 8. Staging and Version Control

### 8.1 Methodology changes
Any change to this spec must be drafted and shown to Ben for approval before HTML regeneration begins. No code is touched until the logic change is signed off.

### 8.2 HTML preview
After generating the HTML, it is written to the local outputs folder for review before pushing to GitHub. Ben opens it in a browser, approves, then push is executed.

### 8.3 Version display
The page shows the current model version and generation date prominently. Example: `Model v2.0 · Generated Thu 19 Jun 2026`

### 8.4 Changelog (internal)
Maintained in `CHANGELOG.md` in the repo. Records what changed and from which round.

---

## 9. Writing Standard

All analysis on the page is written to be understood by someone who did not build the model. Specifically:

- Every verdict includes a plain-English explanation of why the call was made
- Data references are written in plain language: "4 unders, 3 overs from 7 games" not "4U/3O" (which reads ambiguously as "4U/30")
- No jargon without explanation on first use
- PASS and WATCH verdicts include reasons — readers should understand what they'd be betting against, not just that there's no pick
- The model does not force picks. A round with two clean picks is better than a round with seven questionable ones. People are betting real money on these calls.

---

*This document is the source of truth for the NRL Totals Model. When in doubt, come back here.*
