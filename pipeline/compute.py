"""
NRL Totals Pipeline — compute.py
=================================
Reads the master spreadsheet, computes all model inputs and H2H data
for a given round's matchups, and writes structured JSON to data/r{round}.json.

Usage:
    python pipeline/compute.py --round 16 --xlsx path/to/nrl.xlsx

Update MATCHUPS at the bottom each week. Everything else is derived from source data.
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd


# ── Team name normalisation ────────────────────────────────────────────────────
NORM_RULES = [
    ("st. george illawarra", "dragons"),
    ("st george illawarra", "dragons"),
    ("st george dragons", "dragons"),
    ("newcastle", "knights"),
    ("wests tigers", "tigers"),
    ("gold coast", "titans"),
    ("penrith", "panthers"),
    ("canterbury", "bulldogs"),
    ("manly", "sea eagles"),
    ("new zealand", "warriors"),
    ("north queensland", "cowboys"),
    ("north qld", "cowboys"),
    ("melbourne", "storm"),
    ("canberra", "raiders"),
    ("sydney roosters", "roosters"),
    ("cronulla", "sharks"),
    ("dolphins", "dolphins"),
    ("brisbane", "broncos"),
    ("parramatta", "eels"),
    ("south sydney", "rabbitohs"),
]

def normalise(name):
    s = str(name).lower().strip()
    for pattern, replacement in NORM_RULES:
        if pattern in s:
            return replacement
    return s


# ── Load spreadsheet ───────────────────────────────────────────────────────────
def load_spreadsheet(path):
    raw = pd.read_excel(path, header=0)
    raw.columns = raw.iloc[0]
    df = raw.iloc[1:].reset_index(drop=True)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).copy()
    df["Home Score"] = pd.to_numeric(df["Home Score"], errors="coerce")
    df["Away Score"] = pd.to_numeric(df["Away Score"], errors="coerce")
    df["Total Score Close"] = pd.to_numeric(df["Total Score Close"], errors="coerce")
    df["Total"] = df["Home Score"] + df["Away Score"]
    df["Year"] = df["Date"].dt.year
    df["home_n"] = df["Home Team"].apply(normalise)
    df["away_n"] = df["Away Team"].apply(normalise)
    return df


# ── Form model — venue-split ───────────────────────────────────────────────────
# Uses home stats for home team and away stats for away team in model_expected.
# Falls back to flat average if a venue split has < MIN_VENUE_GP games.
MIN_VENUE_GP = 3

def compute_form(df, team, current_year=2026, weight_prev=0.6):
    """
    Returns flat and venue-split weighted averages.
    Weighting: current year full weight, prior year × weight_prev.
    Venue split used in model when home_gp / away_gp >= MIN_VENUE_GP.
    """
    def season_venue_stats(year):
        home_mask = (df["Year"] == year) & (df["home_n"] == team)
        away_mask = (df["Year"] == year) & (df["away_n"] == team)
        return {
            "home_scored":    df[home_mask]["Home Score"].dropna().tolist(),
            "home_conceded":  df[home_mask]["Away Score"].dropna().tolist(),
            "away_scored":    df[away_mask]["Away Score"].dropna().tolist(),
            "away_conceded":  df[away_mask]["Home Score"].dropna().tolist(),
        }

    curr = season_venue_stats(current_year)
    prev = season_venue_stats(current_year - 1)

    def wavg(curr_vals, prev_vals):
        """Weighted average: curr full, prev × weight_prev."""
        if not curr_vals and not prev_vals:
            return 0.0
        if not curr_vals:
            return float(np.mean(prev_vals))
        if not prev_vals:
            return float(np.mean(curr_vals))
        wc = len(curr_vals)
        wp = len(prev_vals) * weight_prev
        return (np.mean(curr_vals) * wc + np.mean(prev_vals) * wp) / (wc + wp)

    # Flat averages (all games regardless of venue)
    all_sc_c = curr["home_scored"]   + curr["away_scored"]
    all_cn_c = curr["home_conceded"] + curr["away_conceded"]
    all_sc_p = prev["home_scored"]   + prev["away_scored"]
    all_cn_p = prev["home_conceded"] + prev["away_conceded"]
    scored_avg   = wavg(all_sc_c, all_sc_p)
    conceded_avg = wavg(all_cn_c, all_cn_p)

    # Venue-split averages
    home_scored_avg   = wavg(curr["home_scored"],   prev["home_scored"])
    home_conceded_avg = wavg(curr["home_conceded"], prev["home_conceded"])
    away_scored_avg   = wavg(curr["away_scored"],   prev["away_scored"])
    away_conceded_avg = wavg(curr["away_conceded"], prev["away_conceded"])

    return {
        "scored_avg":         round(float(scored_avg),         1),
        "conceded_avg":       round(float(conceded_avg),       1),
        "home_scored_avg":    round(float(home_scored_avg),    1),
        "home_conceded_avg":  round(float(home_conceded_avg),  1),
        "away_scored_avg":    round(float(away_scored_avg),    1),
        "away_conceded_avg":  round(float(away_conceded_avg),  1),
        "gp":        len(all_sc_c),
        "gp_prev":   len(all_sc_p),
        "home_gp":   len(curr["home_scored"]),
        "away_gp":   len(curr["away_scored"]),
    }


# ── H2H data ───────────────────────────────────────────────────────────────────
def compute_h2h(df, t1, t2, since_year=2022):
    mask = (df["Year"] >= since_year) & (
        ((df["home_n"] == t1) & (df["away_n"] == t2))
        | ((df["home_n"] == t2) & (df["away_n"] == t1))
    )
    result = []
    for _, r in df[mask].sort_values("Date").iterrows():
        result.append({
            "date":       r["Date"].strftime("%Y-%m-%d"),
            "home_team":  str(r["Home Team"]),
            "away_team":  str(r["Away Team"]),
            "home_score": int(r["Home Score"]),
            "away_score": int(r["Away Score"]),
            "combined":   int(r["Total"]),
            "book_line":  float(r["Total Score Close"]) if pd.notna(r["Total Score Close"]) else None,
        })
    return result


# ── Confidence curve ───────────────────────────────────────────────────────────
BUFFERS = [0, 2, 4, 6, 8, 10, 12, 14, 18, 24]

def confidence_curve(h2h_games, standard_line, direction):
    totals = [g["combined"] for g in h2h_games]
    n = len(totals)
    curve = []
    for b in BUFFERS:
        adj = standard_line + b if direction == "UNDER" else standard_line - b
        hits = sum(1 for x in totals if (x < adj if direction == "UNDER" else x > adj))
        curve.append({
            "buffer": b, "adj_line": round(adj, 1),
            "hits": hits, "n": n,
            "pct": round(hits / n, 4) if n else 0.0,
        })
    return curve


# ── Verdict derivation v3 — SE-anchored scoring ────────────────────────────────
# σ = 13.5 pts  (NRL combined score std dev, 953 games 2022–2026)
# Form SE fixed at σ/√21 ≈ 2.94 pts (effective n≈21 from current season + 0.6×prev)
# H2H SE scales with actual n:  σ/√n
# Hit rate capped at score 1 (r=0.50 with H2H avg — not independent)
# Laplace α=1 smoothing on hit rate: (hits+1)/(n+2)
# Conflict penalty −1 between the two independent signals (form & H2H avg)
#
# Scoring:  sf 0–3 | sh 0–3 | sr 0–1 | cp 0–(−1)   max = 7
# Tiers:    6-7 STRONG BET 80% | 4-5 BET 70% | 3 LEAN 62% | 2 LEAN 55% | 0-1 WATCH 50%

SIGMA   = 13.5
SE_FORM = SIGMA / np.sqrt(21)   # ≈ 2.94 pts

def derive_verdict(model_expected, line, h2h_avg, h2h_under_std, n):
    fg = model_expected - line
    hg = h2h_avg - line
    form_under = fg < 0
    h2h_under  = hg < 0
    rate_under = (h2h_under_std / n > 0.5) if n else True
    direction  = "UNDER" if sum([form_under, h2h_under, rate_under]) >= 2 else "OVER"

    # Form score — thresholds at 0.5, 1.0, 1.5 × SE_FORM (≈ 1.5, 2.9, 4.4 pts)
    af = abs(fg)
    if   af >= 1.5 * SE_FORM: sf = 3
    elif af >= 1.0 * SE_FORM: sf = 2
    elif af >= 0.5 * SE_FORM: sf = 1
    else:                      sf = 0

    # H2H avg score — SE scales with n
    if n:
        se_h2h = SIGMA / np.sqrt(n)
        ah = abs(hg)
        if   ah >= 1.5 * se_h2h: sh = 3
        elif ah >= 1.0 * se_h2h: sh = 2
        elif ah >= 0.5 * se_h2h: sh = 1
        else:                     sh = 0
    else:
        sh = 0

    # Hit rate — Laplace-smoothed α=1, capped at score 1
    hits = h2h_under_std if direction == "UNDER" else (n - h2h_under_std)
    smoothed = (hits + 1) / (n + 2) if n else 0.5
    sr = 1 if smoothed >= 0.80 else 0

    # Conflict penalty between the two independent signals only
    cp = 1 if form_under != h2h_under else 0

    total = sf + sh + sr - cp

    if   total >= 6: tier, conf = "STRONG BET", 80
    elif total >= 4: tier, conf = "BET", 70
    elif total == 3: tier, conf = "LEAN", 62
    elif total == 2: tier, conf = "LEAN", 55
    else:            tier, conf = "WATCH", 50

    return {
        "direction":       direction,
        "tier":            tier,
        "confidence_pct":  conf,
        "form_gap":        round(fg, 1),
        "h2h_gap":         round(hg, 1),
        "signal_conflict": form_under != h2h_under,
        "score":           total,
        "score_breakdown": {"sf": sf, "sh": sh, "sr": sr, "cp": cp},
    }


# ── Main compute ───────────────────────────────────────────────────────────────
def compute_round(xlsx_path, round_num, matchups, output_dir="data"):
    print(f"Loading: {xlsx_path}")
    df = load_spreadsheet(xlsx_path)
    print(f"  {len(df)} rows, {int(df['Year'].min())}–{int(df['Year'].max())}")

    games_output = []
    for m in matchups:
        t1 = normalise(m["home"]); t2 = normalise(m["away"])
        line = m["line"]
        print(f"\n  {t1} v {t2} (line {line})")

        form1 = compute_form(df, t1)
        form2 = compute_form(df, t2)

        # Venue-split model: home team's home stats vs away team's away stats.
        # Falls back to flat average if venue split is thin (< MIN_VENUE_GP games).
        use_home1 = form1["home_gp"] >= MIN_VENUE_GP
        use_away2 = form2["away_gp"] >= MIN_VENUE_GP
        home_scored   = form1["home_scored_avg"]   if use_home1 else form1["scored_avg"]
        home_conceded = form1["home_conceded_avg"] if use_home1 else form1["conceded_avg"]
        away_scored   = form2["away_scored_avg"]   if use_away2 else form2["scored_avg"]
        away_conceded = form2["away_conceded_avg"] if use_away2 else form2["conceded_avg"]
        model = round((home_scored + away_conceded + away_scored + home_conceded) / 2, 1)
        venue_split_used = use_home1 or use_away2

        h2h = compute_h2h(df, t1, t2)
        n = len(h2h)
        totals = [g["combined"] for g in h2h]
        h2h_avg = round(float(np.mean(totals)), 1) if totals else 0.0
        h2h_under_std = sum(1 for x in totals if x < line)
        h2h_over_std  = sum(1 for x in totals if x > line)

        verdict = derive_verdict(model, line, h2h_avg, h2h_under_std, n)
        if m.get("direction_override"):
            verdict["direction"] = m["direction_override"]
            verdict["direction_overridden"] = True

        curve_under = confidence_curve(h2h, line, "UNDER")
        curve_over  = confidence_curve(h2h, line, "OVER")

        primary_curve = curve_under if verdict["direction"] == "UNDER" else curve_over
        # First buffer where Laplace-smoothed rate ≥ 80%, excluding +24
        # Minimum verdict tier: LEAN (WATCH excluded from multis)
        multi_buffer = next(
            (c for c in primary_curve
             if (c["hits"] + 1) / (c["n"] + 2) >= 0.80 and c["buffer"] <= 18), None
        ) if verdict["tier"] != "WATCH" else None

        game = {
            "home": m["home"], "away": m["away"],
            "home_n": t1, "away_n": t2,
            "venue": m.get("venue", ""), "kickoff": m.get("kickoff", ""),
            "line": line,
            "form": {t1: form1, t2: form2},
            "model_expected": model,
            "venue_split_used": venue_split_used,
            "h2h": h2h, "h2h_n": n, "h2h_avg": h2h_avg,
            "h2h_under_std": h2h_under_std, "h2h_over_std": h2h_over_std,
            "curve_under": curve_under, "curve_over": curve_over,
            "verdict": verdict,
            "multi_qualifies": multi_buffer is not None,
            "multi_first_buffer": multi_buffer,
        }
        games_output.append(game)

        vsplit_note = f" (venue-split: home {form1['home_scored_avg']}/{form1['home_conceded_avg']}, away {form2['away_scored_avg']}/{form2['away_conceded_avg']})" if venue_split_used else " (flat avg — thin venue data)"
        print(f"    Form: {t1} {form1['scored_avg']}/{form1['conceded_avg']} | "
              f"{t2} {form2['scored_avg']}/{form2['conceded_avg']}")
        print(f"    Model: {model}{vsplit_note}")
        print(f"    H2H: n={n} avg={h2h_avg}  under_std={h2h_under_std}/{n}")
        print(f"    Verdict: {verdict['tier']} {verdict['direction']} "
              f"{verdict['confidence_pct']}%  score={verdict['score']}  gap={verdict['form_gap']}")
        if multi_buffer:
            print(f"    Multi: +{multi_buffer['buffer']} → adj {multi_buffer['adj_line']} "
                  f"({multi_buffer['hits']}/{multi_buffer['n']} = {multi_buffer['pct']:.0%})")

    output = {
        "round": round_num,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "xlsx_source": Path(xlsx_path).name,
        "games": games_output,
    }

    out_path = Path(output_dir) / f"r{round_num}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n✓ Wrote {out_path}  ({out_path.stat().st_size:,} bytes)")
    return output


# ── Round definitions — update each week ──────────────────────────────────────
MATCHUPS = {
    16: [
        {"home": "Newcastle Knights",       "away": "St George Dragons",
         "line": 48.5, "venue": "McDonald Jones Stadium",  "kickoff": "2026-06-20 20:00"},
        {"home": "Wests Tigers",            "away": "Dolphins",
         "line": 51.5, "venue": "CommBank Stadium",         "kickoff": "2026-06-21 15:00"},
        {"home": "Gold Coast Titans",       "away": "Penrith Panthers",
         "line": 50.5, "venue": "Cbus Super Stadium",       "kickoff": "2026-06-21 17:30"},
        {"home": "Canterbury Bulldogs",     "away": "Manly Sea Eagles",
         "line": 48.5, "venue": "Accor Stadium",            "kickoff": "2026-06-22 14:00"},
        {"home": "New Zealand Warriors",    "away": "North Queensland Cowboys",
         "line": 49.5, "venue": "Go Media Stadium",         "kickoff": "2026-06-22 16:05"},
        {"home": "Melbourne Storm",         "away": "Canberra Raiders",
         "line": 50.5, "venue": "AAMI Park",                "kickoff": "2026-06-23 18:00"},
        {"home": "Sydney Roosters",         "away": "Cronulla Sharks",
         "line": 50.5, "venue": "Allianz Stadium",          "kickoff": "2026-06-23 20:00"},
    ],
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--round", type=int, required=True)
    parser.add_argument("--xlsx",  type=str, required=True)
    parser.add_argument("--output-dir", type=str, default="data")
    args = parser.parse_args()
    if args.round not in MATCHUPS:
        print(f"Round {args.round} not in MATCHUPS."); sys.exit(1)
    compute_round(args.xlsx, args.round, MATCHUPS[args.round], args.output_dir)
