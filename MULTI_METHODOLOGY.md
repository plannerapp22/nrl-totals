# NRL Totals Model — Multi Construction Methodology

## Purpose

This document captures all thinking behind multi (parlay) construction so it does not need to be rebuilt each week. It is a standing reference, not a round-by-round output.

Multi construction is a **separate process** from the directional model. The directional model answers: *which way, and how confident?* This methodology answers: *given that direction, how do you build adjusted lines and select legs?*

---

## Core concept: confidence curves with NRL scoring increments

For any game with a directional verdict, you move the bookmaker line to create a buffer. That buffer is measured in NRL scoring increments, which gives punters a natural reference point.

| Buffer | Points | NRL scoring equivalent |
|--------|--------|------------------------|
| +0  | 0  | Standard line — no buffer |
| +2  | 2  | One conversion (kick after try) |
| +4  | 4  | One unconverted try |
| +6  | 6  | One converted try (try + conversion) |
| +8  | 8  | One converted try + one conversion |
| +10 | 10 | One converted try + one unconverted try |
| +12 | 12 | Two converted tries |
| +14 | 14 | Two converted tries + one conversion |
| +18 | 18 | Three converted tries |
| +24 | 24 | Four converted tries |

Calculate the hit rate at each buffer level. Go as far as needed to show where thresholds are met and where the curve flattens. There is no upper limit — if a game needs +18 to reach 90%, show that. It may be impractical to bet, but the information matters.

**Direction rule — non-negotiable:**
- **UNDER bet**: adjusted line moves **UP** from standard (more room below = more conservative)
- **OVER bet**: adjusted line moves **DOWN** from standard (lower threshold to clear = more conservative)

Moving an UNDER line down makes it harder. Moving an OVER line up makes it harder. Both are errors.

---

## Confidence curve calculation

For each qualifying game, compute:

```
For UNDER bet with standard line S:
  For each buffer B in [0, 2, 4, 6, 8, 10, 12, 14, 18, 24, ...]:
    adjusted_line = S + B
    hit_rate = count(H2H results < adjusted_line) / total_H2H_games

For OVER bet with standard line S:
  For each buffer B in [0, 2, 4, 6, 8, 10, 12, 14, 18, 24, ...]:
    adjusted_line = S - B
    hit_rate = count(H2H results > adjusted_line) / total_H2H_games
```

Continue until the curve reaches 100% (or it becomes clear it won't at any reasonable line). Present as a table in the output. The punter matches the adjusted line to what their bookmaker prices at their target odds.

### Example (Storm v Raiders, UNDER, standard line 50.5, H2H: 22, 36, 38, 46, 48, 48, 50):

| Buffer | Adj Line | Hits | % | Equiv |
|--------|----------|------|---|-------|
| +0  | 50.5 | 7/7 | 100% | Standard |
| +2  | 52.5 | 7/7 | 100% | +1 conversion |
| +4  | 54.5 | 7/7 | 100% | +1 try |
| +6  | 56.5 | 7/7 | 100% | +1 converted try |
| +8  | 58.5 | 7/7 | 100% | +1 converted try + conversion |
| +12 | 62.5 | 7/7 | 100% | +2 converted tries |

Curve is flat from the start — any adjusted line above 50.5 is 100%. Pick the line your bookmaker prices at $1.15–$1.25.

### Example (Knights v Dragons, UNDER, standard line 48.5, H2H: 26, 35, 37, 40, 44, 54, 60):

| Buffer | Adj Line | Hits | % | Equiv |
|--------|----------|------|---|-------|
| +0  | 48.5 | 5/7 | 71% | Standard |
| +2  | 50.5 | 5/7 | 71% | +1 conversion |
| +4  | 52.5 | 5/7 | 71% | +1 try |
| +6  | 54.5 | 6/7 | 86% | +1 converted try ← 85% threshold |
| +8  | 56.5 | 6/7 | 86% | +1 converted try + conversion |
| +12 | 60.5 | 7/7 | 100% | +2 converted tries ← 90% threshold |

Need +6 for 85%, +12 for 90%. Two converted tries of buffer to reach near-certainty.

---

## Multi tiers

### Regular multi (~$1.10–$1.35 per leg, target 85%+)
- Minimum hit rate per leg: **85%**
- Find the smallest buffer that achieves 85% — that is the recommended adjusted line
- Aim for buffers in the +2 to +12 range; beyond that, odds typically become negligible
- Include 3–6 legs, no minimum — never pad to hit a number

### Hyperconservative multi (~$1.05–$1.20 per leg, target 90%+)
- Minimum hit rate per leg: **90%** (effectively 100% from small samples)
- Accept lower odds in exchange for near-certainty per leg
- Go to +12 and beyond if needed to reach threshold
- If a game requires +18 or more to reach 90%, note it but don't include it — odds will be negligible
- Typically 3–4 legs available per round; some rounds may only support 2 or 3

---

## Leg selection rules

1. **Only BET or STRONG BET verdict games** qualify as primary multi legs
2. **LEAN games** can extend the multi (legs 4–6) if H2H data supports 85%+ at a reasonable buffer
3. **WATCH games are never multi legs** regardless of how far you move the line
4. **Warriors v Cowboys pattern**: if the confidence curve is flat across all reasonable buffers (e.g., 60% at +0 through +12), exclude the game entirely — no adjusted line makes it viable
5. **Mixed directions are fine** — UNDER and OVER legs can coexist in the same multi
6. **Never include the same game in both the regular and hyperconservative multi** — they serve different purposes

---

## Caveats to flag in output

- **Small sample (n < 5)**: note explicitly, confidence % is indicative not statistical
- **Bimodal results** (e.g., Titans v Panthers: 22, 30 in one cluster, 54, 56 in another): the +6 jump to 100% looks clean but is sitting right at the cluster boundary — note the pattern
- **Recency-only calls**: if the confidence is driven by 1–2 recent games overriding the broader average, label it as a recency signal, not a statistical pattern
- **Finals exclusion**: semis and grand finals are excluded from regular-season H2H analysis — different scoring context

---

## What this methodology does NOT cover

- **Try scorers**: completely different market. Needs player-level scoring rates, team sheets, positional tendencies. Not in scope for this model.
- **Line shopping**: identifying which bookmaker offers the best adjusted line price. The methodology identifies confidence at each line level; the punter matches to available prices.
- **In-play adjustments**: pre-game model only.
- **Line movement**: if the market line moves significantly before game time, re-run the confidence curve against the new line.

---

## Changelog

| Version | Change |
|---------|--------|
| v1.0 | Initial methodology — fixed adjusted lines, direction error (under lines moved down) |
| v2.0 | Corrected direction rule. Confidence curves introduced. NRL scoring increments as benchmarks. Buffer range extended to +12 and beyond. Methodology separated from directional model. |
