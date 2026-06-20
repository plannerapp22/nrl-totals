"""
NRL Totals Pipeline — log_results.py
======================================
Appends actual game results to data/track_record.json after a round completes.
Run after all games in the round have been played.

Usage:
    python pipeline/log_results.py --round 16 --json data/r16.json

For each game it will prompt you to enter the actual combined score.
Hit Enter to skip a game (e.g. not yet played).
"""

import argparse
import json
from pathlib import Path
from datetime import date


TRACK_RECORD_PATH = Path("data/track_record.json")


def load_track_record():
    if TRACK_RECORD_PATH.exists():
        with open(TRACK_RECORD_PATH) as f:
            return json.load(f)
    return {
        "_meta": {
            "description": "Pick track record from v3.0 (R16 onward). SE-anchored formula.",
            "model_version": "3.0",
            "from_round": 16,
            "formula": "SE-anchored scoring: sf(0-3) + sh(0-3) + sr(0-1) - cp. Sigma=13.5.",
        },
        "picks": [],
        "summary": {}
    }


def compute_summary(picks):
    by_tier = {}
    for p in picks:
        if p.get("actual_combined") is None:
            continue
        tier = p["tier"]
        hit  = p["hit"]
        if tier not in by_tier:
            by_tier[tier] = {"picks": 0, "hits": 0}
        by_tier[tier]["picks"] += 1
        by_tier[tier]["hits"]  += int(hit)
    summary = {}
    for tier, d in by_tier.items():
        summary[tier] = {
            "picks": d["picks"],
            "hits":  d["hits"],
            "hit_rate": round(d["hits"] / d["picks"], 3) if d["picks"] else None,
        }
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--round", type=int, required=True)
    parser.add_argument("--json",  type=str, required=True)
    args = parser.parse_args()

    with open(args.json) as f:
        round_data = json.load(f)

    tr = load_track_record()
    existing_keys = {(p["round"], p["home"], p["away"]) for p in tr["picks"]}

    added = 0
    for g in round_data["games"]:
        key = (args.round, g["home"], g["away"])
        if key in existing_keys:
            print(f"  Skip (already logged): {g['home']} v {g['away']}")
            continue

        v = g["verdict"]
        print(f"\n{g['home']} v {g['away']}  [{g['kickoff']}]")
        print(f"  Model: {g['model_expected']}  Line: {g['line']}  Verdict: {v['tier']} {v['direction']} {v['confidence_pct']}%")
        raw = input("  Actual combined score (Enter to skip): ").strip()
        if not raw:
            continue

        actual = int(raw)
        direction = v["direction"]
        hit = (actual < g["line"]) if direction == "UNDER" else (actual > g["line"])

        record = {
            "round":            args.round,
            "date_logged":      date.today().isoformat(),
            "kickoff":          g["kickoff"],
            "home":             g["home"],
            "away":             g["away"],
            "line":             g["line"],
            "model_expected":   g["model_expected"],
            "direction":        direction,
            "tier":             v["tier"],
            "confidence_pct":   v["confidence_pct"],
            "score":            v.get("score"),
            "score_breakdown":  v.get("score_breakdown"),
            "actual_combined":  actual,
            "hit":              hit,
            "margin_vs_line":   round(actual - g["line"], 1),
        }
        tr["picks"].append(record)
        existing_keys.add(key)
        added += 1
        print(f"  → {'HIT ✓' if hit else 'MISS ✗'}  (actual {actual}, needed {'<' if direction == 'UNDER' else '>'} {g['line']})")

    tr["summary"] = compute_summary(tr["picks"])

    with open(TRACK_RECORD_PATH, "w") as f:
        json.dump(tr, f, indent=2)
    print(f"\n✓ Logged {added} result(s). Track record: {TRACK_RECORD_PATH}")
    if tr["summary"]:
        print("\nOverall calibration:")
        for tier, s in sorted(tr["summary"].items()):
            print(f"  {tier:12s} {s['hits']}/{s['picks']} = {s['hit_rate']:.0%}")


if __name__ == "__main__":
    main()
