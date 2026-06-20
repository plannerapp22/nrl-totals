"""
NRL Totals Pipeline — validate.py
===================================
Runs assertions on a round JSON before HTML generation.
Raises SystemExit(1) with a clear error if any check fails.

Usage:
    python pipeline/validate.py --json data/r16.json
"""

import argparse
import json
import sys
import numpy as np


def validate(data):
    errors = []
    round_num = data.get("round")

    for i, g in enumerate(data["games"]):
        label = f"Game {i+1} ({g['home_n']} v {g['away_n']})"
        h2h = g["h2h"]
        n = g["h2h_n"]
        line = g["line"]

        # 1. n matches actual H2H row count
        if len(h2h) != n:
            errors.append(f"{label}: h2h_n={n} but len(h2h)={len(h2h)}")

        # 2. h2h_avg matches computed average
        if h2h:
            computed_avg = round(np.mean([x["combined"] for x in h2h]), 1)
            if abs(computed_avg - g["h2h_avg"]) > 0.15:
                errors.append(f"{label}: h2h_avg={g['h2h_avg']} but computed={computed_avg}")

        # 3. h2h_under_std matches count
        computed_under = sum(1 for x in h2h if x["combined"] < line)
        if computed_under != g["h2h_under_std"]:
            errors.append(f"{label}: h2h_under_std={g['h2h_under_std']} but computed={computed_under}")

        # 4. Combined scores are plausible (NRL range 10–120)
        for game in h2h:
            c = game["combined"]
            if not (10 <= c <= 120):
                errors.append(f"{label}: suspicious combined score {c} on {game['date']}")

        # 5. Confidence curves are non-decreasing for UNDER (more buffer = more room)
        prev_pct = -1
        for point in g["curve_under"]:
            if point["pct"] < prev_pct - 0.001:
                errors.append(f"{label}: UNDER curve not monotone at buffer +{point['buffer']}")
            prev_pct = point["pct"]

        # 6. Confidence curves are non-decreasing for OVER (more buffer = lower bar)
        prev_pct = -1
        for point in g["curve_over"]:
            if point["pct"] < prev_pct - 0.001:
                errors.append(f"{label}: OVER curve not monotone at buffer +{point['buffer']}")
            prev_pct = point["pct"]

        # 7. model_expected is plausible
        model = g["model_expected"]
        if not (20 <= model <= 100):
            errors.append(f"{label}: model_expected={model} is implausible")

        # 8. Verdict direction is consistent with majority signal
        v = g["verdict"]
        form_under = v["form_gap"] < 0
        h2h_under  = g["h2h_avg"] < line
        h2h_rate_under = g["h2h_under_std"] / n > 0.5 if n else True
        under_votes = sum([form_under, h2h_under, h2h_rate_under])
        majority_direction = "UNDER" if under_votes >= 2 else "OVER"
        if v["direction"] != majority_direction and not v.get("direction_overridden"):
            errors.append(
                f"{label}: verdict direction={v['direction']} but majority signal={majority_direction} "
                f"(form_under={form_under}, h2h_avg_under={h2h_under}, rate_under={h2h_rate_under})"
            )

        # 9. Required fields present
        for field in ["home", "away", "line", "model_expected", "h2h_n",
                      "h2h_avg", "verdict", "curve_under", "curve_over"]:
            if field not in g:
                errors.append(f"{label}: missing field '{field}'")

        # 10. H2H dates are in order
        dates = [x["date"] for x in h2h]
        if dates != sorted(dates):
            errors.append(f"{label}: H2H not sorted by date")

    if errors:
        print(f"\n✗ VALIDATION FAILED — Round {round_num}\n")
        for e in errors:
            print(f"  ERROR: {e}")
        print()
        sys.exit(1)
    else:
        print(f"✓ All checks passed — Round {round_num} ({len(data['games'])} games)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=str, required=True)
    args = parser.parse_args()
    with open(args.json) as f:
        data = json.load(f)
    validate(data)
