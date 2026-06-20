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


# ── Form model ─────────────────────────────────────────────────────────────────
def compute_form(df, team, current_year=2026, weight_prev=0.6):
    def season_stats(year):
        mask = (df["Year"] == year) & (
            (df["home_n"] == team) | (df["away_n"] == team)
        )
        scored, conceded = [], []
        for _, r in df[mask].iterrows():
            if r["home_n"] == team:
                scored.append(r["Home Score"]); conceded.append(r["Away Score"])
            else:
                scored.append(r["Away Score"]); conceded.append(r["Home Score"])
        return scored, conceded

    sc_curr, cn_curr = season_stats(current_year)
    sc_prev, cn_prev = season_stats(current_year - 1)

    if sc_curr:
        w_curr = len(sc_curr)
        w_prev = len(sc_prev) * weight_prev
        total_w = w_curr + w_prev
        if sc_prev:
            scored_avg   = (np.mean(sc_curr)*w_curr + np.mean(sc_prev)*w_prev) / total_w
            conceded_avg = (np.mean(cn_curr)*w_curr + np.mean(cn_prev)*w_prev) / total_w
        else:
            scored_avg = np.mean(sc_curr); conceded_avg = np.mean(cn_curr)
    elif sc_prev:
        scored_avg = np.mean(sc_prev); conceded_avg = np.mean(cn_prev)
    else:
        scored_avg = conceded_avg = 0.0

    return {
        "scored_avg":   round(float(scored_avg), 1),
        "conceded_avg": round(float(conceded_avg), 1),
        "gp":      len(sc_curr),
        "gp_prev": len(sc_prev),
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


# ── Verdict derivation ─────────────────────────────────────────────────────────
def derive_verdict(model_expected, line, h2h_avg, h2h_hit_rate_under, n):
    form_gap = model_expected - line
    h2h_gap  = h2h_avg - line
    form_under    = form_gap < 0
    h2h_avg_under = h2h_gap < 0
    h2h_rate_under = h2h_hit_rate_under > 0.5
    under_votes = sum([form_under, h2h_avg_under, h2h_rate_under])
    direction = "UNDER" if under_votes >= 2 else "OVER"

    abs_form = abs(form_gap)
    abs_h2h  = abs(h2h_gap)
    if abs_form >= 4.0 and abs_h2h >= 6.0:
        tier, conf = "STRONG BET", 80
    elif abs_form >= 3.0 or (abs_form >= 1.5 and abs_h2h >= 5.0):
        tier, conf = "BET", 70
    elif abs_form >= 1.0 or abs_h2h >= 2.0:
        tier, conf = "LEAN", 60 if abs_form >= 2.0 else 55
    else:
        tier, conf = "WATCH", 50

    if n <= 4 and tier == "STRONG BET":
        tier, conf = "BET", 70
    if form_under != h2h_avg_under:
        conf = max(conf - 5, 50)
        if tier == "STRONG BET": tier = "BET"

    return {
        "direction": direction,
        "tier": tier,
        "confidence_pct": conf,
        "form_gap": round(form_gap, 1),
        "h2h_gap":  round(h2h_gap, 1),
        "signal_conflict": form_under != h2h_avg_under,
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
        model = round((form1["scored_avg"] + form2["conceded_avg"] +
                       form2["scored_avg"] + form1["conceded_avg"]) / 2, 1)

        h2h = compute_h2h(df, t1, t2)
        n = len(h2h)
        totals = [g["combined"] for g in h2h]
        h2h_avg = round(float(np.mean(totals)), 1) if totals else 0.0
        h2h_under_std = sum(1 for x in totals if x < line)
        h2h_over_std  = sum(1 for x in totals if x > line)

        verdict = derive_verdict(model, line, h2h_avg,
                                 h2h_under_std/n if n else 0.5, n)
        if m.get("direction_override"):
            verdict["direction"] = m["direction_override"]
            verdict["direction_overridden"] = True

        curve_under = confidence_curve(h2h, line, "UNDER")
        curve_over  = confidence_curve(h2h, line, "OVER")

        primary_curve = curve_under if verdict["direction"] == "UNDER" else curve_over
        # First buffer >=85%, excluding +24 (negligible odds)
        multi_buffer = next(
            (c for c in primary_curve if c["pct"] >= 0.85 and c["buffer"] <= 18), None
        )

        game = {
            "home": m["home"], "away": m["away"],
            "home_n": t1, "away_n": t2,
            "venue": m.get("venue", ""), "kickoff": m.get("kickoff", ""),
            "line": line,
            "form": {t1: form1, t2: form2},
            "model_expected": model,
            "h2h": h2h, "h2h_n": n, "h2h_avg": h2h_avg,
            "h2h_under_std": h2h_under_std, "h2h_over_std": h2h_over_std,
            "curve_under": curve_under, "curve_over": curve_over,
            "verdict": verdict,
            "multi_qualifies": multi_buffer is not None,
            "multi_first_buffer": multi_buffer,
        }
        games_output.append(game)

        print(f"    Form: {t1} {form1['scored_avg']}/{form1['conceded_avg']} | "
              f"{t2} {form2['scored_avg']}/{form2['conceded_avg']}")
        print(f"    Model: {model}  H2H: n={n} avg={h2h_avg}  under_std={h2h_under_std}/{n}")
        print(f"    Verdict: {verdict['tier']} {verdict['direction']} "
              f"{verdict['confidence_pct']}%  gap={verdict['form_gap']}")
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
