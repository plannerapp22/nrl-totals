# NRL Totals Pipeline

Run this before every report. Never type numbers into the HTML by hand.

## Workflow

```bash
# 1. Compute — reads spreadsheet, outputs JSON
python pipeline/compute.py --round 17 --xlsx path/to/nrl.xlsx

# 2. Validate — asserts JSON integrity
python pipeline/validate.py --json data/r17.json

# 3. Generate — renders HTML from JSON (optional, or edit narrative manually)
python pipeline/generate.py --json data/r17.json --template index_r17.html --out index_r17.html
```

## Adding a new round

Edit `MATCHUPS` in `compute.py`:
```python
17: [
    {"home": "Team A", "away": "Team B", "line": 48.5,
     "venue": "Stadium Name", "kickoff": "2026-06-27 20:00"},
    ...
]
```

That's it. Every number in the report is derived from the spreadsheet.

## What the pipeline checks (validate.py)

- H2H row count matches `h2h_n`
- H2H average matches computed average  
- Standard-line hit counts match computed counts
- Combined scores are plausible (10–120)
- Confidence curves are monotonically non-decreasing
- Model expected is plausible (20–100)
- Verdict direction is consistent with majority signal
- H2H dates are in chronological order

## Files

| File | Purpose |
|------|---------|
| `pipeline/compute.py` | Reads xlsx → outputs `data/r{round}.json` |
| `pipeline/validate.py` | Asserts JSON integrity before HTML generation |
| `pipeline/generate.py` | Renders HTML from JSON |
| `data/r{round}.json` | Source of truth for each round |
