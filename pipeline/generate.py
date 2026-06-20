"""
NRL Totals Pipeline — generate.py
===================================
Reads a round JSON and produces the full HTML report.
No numbers are typed by hand — everything comes from the JSON.

Usage:
    python pipeline/generate.py --json data/r16.json --out index_r16_v2.html
    
    # Or pipe into the existing template (preserving header/footer):
    python pipeline/generate.py --json data/r16.json --template index_r16_v2.html --out index_r16_v2.html
"""

import argparse
import json
import sys
from pathlib import Path


# ── Helpers ────────────────────────────────────────────────────────────────────
VERDICT_CSS = {
    "STRONG BET": {"pill": "v-strong-bar", "color": "var(--tl-strong)", "fw": "700"},
    "BET":        {"pill": "v-bet-bar",    "color": "var(--tl-bet)",    "fw": "600"},
    "LEAN":       {"pill": "v-lean-bar",   "color": "var(--tl-lean)",   "fw": ""},
    "WATCH":      {"pill": "v-watch-bar",  "color": "var(--waste)",     "fw": ""},
}
OVER_VERDICT_CSS = {
    "LEAN":  {"pill": "v-lean-over-bar", "color": "var(--blue)", "fw": ""},
    "BET":   {"pill": "v-lean-over-bar", "color": "var(--blue)", "fw": "600"},
    "WATCH": {"pill": "v-watch-bar",     "color": "var(--waste)","fw": ""},
}

def verdict_css(tier, direction):
    if direction == "OVER":
        return OVER_VERDICT_CSS.get(tier, OVER_VERDICT_CSS["LEAN"])
    return VERDICT_CSS.get(tier, VERDICT_CSS["LEAN"])

def chip(val, line, direction):
    if direction == "UNDER":
        c = "under" if val < line else "over"
    else:
        c = "over" if val > line else "under"
    label = "UNDER" if c == "under" else "OVER"
    return f'<span class="{c}-chip">{label}</span>'

def fmt_result(game):
    return f"{game['home_team']} {game['home_score']}–{game['away_score']} {game['away_team']}"

def tag_class(pct):
    if pct >= 1.0:  return "tag-100"
    if pct >= 0.85: return "tag-85"
    return "tag-flat"

def tag_label(multi_buffer, direction):
    if multi_buffer is None:
        return "Does not qualify"
    b = multi_buffer["buffer"]
    pct = multi_buffer["pct"]
    return f"{pct:.0%} at +{b}"

def curve_row_class(point, recommended_buffer):
    if point["buffer"] == recommended_buffer:
        return ' class="curve-pick"'
    return ""

def pct_class(pct):
    if pct >= 1.0:  return "curve-100"
    if pct >= 0.90: return "curve-90"
    if pct >= 0.85: return "curve-85"
    if pct > 0:     return "curve-85"
    return "curve-muted"


# ── Game card HTML ─────────────────────────────────────────────────────────────
def render_game_card(g):
    v = g["verdict"]
    tier = v["tier"]
    direction = v["direction"]
    conf = v["confidence_pct"]
    css = verdict_css(tier, direction)
    line = g["line"]
    t1, t2 = g["home_n"], g["away_n"]
    f1, f2 = g["form"][t1], g["form"][t2]
    signal_arrow = "↓" if direction == "UNDER" else "↑"
    signal_class = "signal-under" if direction == "UNDER" else "signal-over"

    # H2H table rows
    h2h_rows = ""
    for game in reversed(g["h2h"]):  # newest first
        c = game["combined"]
        yr = game["date"][:4]
        h2h_rows += (
            f'      <tr><td>{yr}</td>'
            f'<td>{fmt_result(game)}</td>'
            f'<td>{c}</td>'
            f'<td>{chip(c, line, direction)}</td></tr>\n'
        )

    std_hits = g["h2h_under_std"] if direction == "UNDER" else g["h2h_over_std"]
    n = g["h2h_n"]
    multi_note = ""
    if g["multi_qualifies"] and g["multi_first_buffer"]:
        mb = g["multi_first_buffer"]
        multi_note = (f'Multi qualified: {mb["hits"]}/{mb["n"]} = {mb["pct"]:.0%} '
                      f'at +{mb["buffer"]} (adj {mb["adj_line"]}).')
    elif not g["multi_qualifies"]:
        primary_max = max(
            (c["pct"] for c in (g["curve_under"] if direction=="UNDER" else g["curve_over"])
             if c["buffer"] <= 18), default=0
        )
        multi_note = f'Does not qualify for multi (max {primary_max:.0%} at practical buffer).'

    conflict_note = " Signal conflict: form and H2H avg disagree on direction." if v.get("signal_conflict") else ""

    return f"""<!-- {g['home'].upper()} v {g['away'].upper()} -->
<div class="game-card">
  <div class="card-header">
    <div>
      <div class="card-matchup">{g['home']} <span class="card-v">v</span> {g['away']}</div>
      <div class="card-meta">{g['kickoff']} &nbsp;·&nbsp; {g['venue']}</div>
    </div>
    <div class="card-line"><div class="card-line-label">O/U Line</div><div class="card-line-value">{line}</div></div>
  </div>
  <div class="card-verdict-bar">
    <div class="verdict-pill {css['pill']}">{tier} {direction} <span class="conf">{conf}%</span></div>
    <div class="model-signal">
      <span class="{signal_class}">{signal_arrow}</span>
      Model: {g['model_expected']} &nbsp;|&nbsp; H2H avg: {g['h2h_avg']} &nbsp;|&nbsp; {std_hits}/{n} H2H {direction} {line}{(' · ' + conflict_note.strip()) if conflict_note else ''}
    </div>
  </div>
  <div class="card-body">
    <div class="note-box">
      <strong>Model gap: {v['form_gap']:+.1f} &nbsp;·&nbsp; H2H gap: {v['h2h_gap']:+.1f}</strong><br>
      {multi_note}
    </div>
  </div>
  <button class="card-data-toggle" onclick="toggleData(this)"><span>Show data</span><span>↓</span></button>
  <div class="card-data">
    <div class="data-grid">
      <div class="data-block">
        <div class="data-block-label">{g['home']} — 2026</div>
        <div class="data-block-value">{f1['scored_avg']}</div>
        <div class="data-block-sub">Avg scored &nbsp;·&nbsp; {f1['conceded_avg']} conceded &nbsp;·&nbsp; {f1['gp']} GP</div>
      </div>
      <div class="data-block">
        <div class="data-block-label">{g['away']} — 2026</div>
        <div class="data-block-value">{f2['scored_avg']}</div>
        <div class="data-block-sub">Avg scored &nbsp;·&nbsp; {f2['conceded_avg']} conceded &nbsp;·&nbsp; {f2['gp']} GP</div>
      </div>
    </div>
    <table class="h2h-table">
      <tr><th>Year</th><th>Result</th><th>Combined</th><th>vs {line}</th></tr>
{h2h_rows}    </table>
    <p style="font-size:12px;color:var(--waste);margin-top:8px;">
      n={n} (2022–26). Avg {g['h2h_avg']}. {std_hits}/{n} {direction} {line} at standard.
    </p>
  </div>
</div>
"""


# ── Confidence curve table ─────────────────────────────────────────────────────
def render_curve_table(curve, recommended_buffer, show_odds=True):
    rows = ""
    shown_buffers = [0, 2, 4, 6, 8, 12, 18]  # skip 10,14,24 for brevity
    for point in curve:
        if point["buffer"] not in shown_buffers:
            continue
        rc = curve_row_class(point, recommended_buffer)
        pc = pct_class(point["pct"])
        arrow = " ← pick" if point["buffer"] == recommended_buffer else ""
        rows += (
            f'          <tr{rc}>'
            f'<td>+{point["buffer"]}{arrow}</td>'
            f'<td>{point["adj_line"]}</td>'
            f'<td>{point["hits"]}/{point["n"]}</td>'
            f'<td class="{pc}">{point["pct"]:.0%}</td>'
            f'</tr>\n'
        )
    return f"""        <table class="curve-table">
          <thead><tr><th>Buffer</th><th>Adj Line</th><th>H2H</th><th>Conf</th></tr></thead>
          <tbody>
{rows}          </tbody>
        </table>"""


# ── Multi section ──────────────────────────────────────────────────────────────
def render_multi_section(games):
    qualifying = [g for g in games if g["multi_qualifies"]]
    non_qualifying = [g for g in games if not g["multi_qualifies"]]

    legs_html = ""
    for i, g in enumerate(qualifying, 1):
        mb = g["multi_first_buffer"]
        direction = g["verdict"]["direction"]
        curve = g["curve_under"] if direction == "UNDER" else g["curve_over"]
        rec_buf = mb["buffer"] if mb else 0
        tc = tag_class(mb["pct"] if mb else 0)
        tl = tag_label(mb, direction)
        curve_html = render_curve_table(curve, rec_buf)

        legs_html += f"""
    <div class="multi-leg">
      <div class="multi-leg-label">Leg {i} · {direction} <span class="multi-leg-tag {tc}">{tl}</span></div>
      <div class="multi-leg-pick">{g['home']} v {g['away']}</div>
      <div class="multi-leg-detail" style="margin-bottom:8px">
        Standard line {g['line']}. H2H avg {g['h2h_avg']} (n={g['h2h_n']}). 
        Model {g['model_expected']}. First 85%+ at +{rec_buf} (adj {mb['adj_line'] if mb else 'N/A'}).
        {'<strong>Signal conflict — H2H-driven leg.</strong>' if g['verdict'].get('signal_conflict') else ''}
      </div>
{curve_html}
    </div>
"""

    # Non-qualifying cards
    non_qual_html = ""
    for g in non_qualifying:
        direction = g["verdict"]["direction"]
        curve = g["curve_under"] if direction == "UNDER" else g["curve_over"]
        max_pct = max((c["pct"] for c in curve if c["buffer"] <= 18), default=0)
        non_qual_html += f"""
    <div class="multi-leg multi-leg-weak" style="border-color:rgba(220,38,38,0.25);background:rgba(220,38,38,0.05)">
      <div class="multi-leg-label" style="color:var(--cherry)">{g['home']} v {g['away']} — Does not qualify ({max_pct:.0%} max at practical buffer)</div>
      <div class="multi-leg-pick" style="color:rgba(241,231,206,0.6)">
        {g['h2h_under_std']}/{g['h2h_n']} UNDER / {g['h2h_over_std']}/{g['h2h_n']} OVER at standard line {g['line']}. Neither direction clears 85%.
      </div>
    </div>
"""

    return f"""<!-- MULTI SECTION -->
<div class="multi-section">
  <div class="multi-header">
    <div class="multi-title">Multi Recommendations — Round {games[0].get('round', '')}</div>
    <div class="multi-subtitle">Each leg shows the confidence curve across NRL scoring increments. Verify all adjusted line prices with your bookmaker before placing.</div>
  </div>
  <div class="multi-body">

    <div class="multi-legs-label">Adjusted Line Multi — {len(qualifying)} qualifying legs (≥85% per leg)</div>
    <div style="font-size:13px;color:rgba(241,231,206,0.65);margin-bottom:16px;line-height:1.6;">
      UNDER: line moves UP (more room). OVER: line moves DOWN (lower threshold). Highlighted row = recommended pick.
    </div>
{legs_html}
{non_qual_html}
    <div class="multi-caveat">
      <strong style="font-family:'Roboto Mono',monospace;font-size:10px;text-transform:uppercase;letter-spacing:1px;color:var(--butter);">Before placing</strong><br>
      Alternate totals markets are not available at all bookmakers. H2H samples are small (4–7 games). 
      100% from a small sample is not statistical certainty. Check team lists Thursday/Friday. Never bet more than you're comfortable losing.
    </div>
  </div>
</div>
"""


# ── Summary table ──────────────────────────────────────────────────────────────
def render_summary_table(games, round_num):
    rows = ""
    for g in games:
        v = g["verdict"]
        direction = v["direction"]
        tier = v["tier"]
        conf = v["confidence_pct"]
        css = verdict_css(tier, direction)
        fw = f';font-weight:{css["fw"]}' if css["fw"] else ""
        verdict_label = f'{tier} {direction} ({conf}%)'
        rows += f"""      <tr style="border-bottom:1px solid rgba(33,28,20,0.06)">
        <td style="padding:10px 14px;font-weight:500">{g['home']} v {g['away']}</td>
        <td style="text-align:center;padding:10px 8px;font-family:Roboto Mono,monospace;font-size:12px">{g['line']}</td>
        <td style="text-align:center;padding:10px 8px;font-family:Roboto Mono,monospace;font-size:12px;color:var(--waste)">{g['model_expected']}</td>
        <td style="text-align:center;padding:10px 8px;font-family:Roboto Mono,monospace;font-size:12px;color:var(--waste)">{g['h2h_avg']}</td>
        <td style="padding:10px 14px;color:{css['color']};font-family:Roboto Mono,monospace;font-size:12px{fw}">{verdict_label}</td>
      </tr>
"""
    return f"""<!-- ROUND SUMMARY TABLE -->
<p class="section-head">Round {round_num} Summary</p>
<div style="background:white;border-radius:6px;overflow:hidden;box-shadow:0 2px 8px rgba(33,28,20,0.06);margin-top:16px">
  <table style="width:100%;border-collapse:collapse;font-size:14px">
    <thead>
      <tr style="background:var(--ink)">
        <th style="text-align:left;padding:10px 14px;font-family:Roboto Mono,monospace;font-size:10px;text-transform:uppercase;letter-spacing:1px;color:var(--waste)">Game</th>
        <th style="text-align:center;padding:10px 8px;font-family:Roboto Mono,monospace;font-size:10px;text-transform:uppercase;letter-spacing:1px;color:var(--waste)">Line</th>
        <th style="text-align:center;padding:10px 8px;font-family:Roboto Mono,monospace;font-size:10px;text-transform:uppercase;letter-spacing:1px;color:var(--waste)">Model</th>
        <th style="text-align:center;padding:10px 8px;font-family:Roboto Mono,monospace;font-size:10px;text-transform:uppercase;letter-spacing:1px;color:var(--waste)">H2H Avg</th>
        <th style="text-align:left;padding:10px 14px;font-family:Roboto Mono,monospace;font-size:10px;text-transform:uppercase;letter-spacing:1px;color:var(--waste)">Verdict</th>
      </tr>
    </thead>
    <tbody>
{rows}    </tbody>
  </table>
</div>
"""


# ── Main ───────────────────────────────────────────────────────────────────────
def generate(json_path, template_path=None, out_path=None):
    with open(json_path) as f:
        data = json.load(f)

    round_num = data["round"]
    games = data["games"]

    # Tag games with round number for multi section
    for g in games:
        g["round"] = round_num

    cards_html = f'<p class="section-head">Round {round_num} — All Games</p>\n\n'
    cards_html += "\n".join(render_game_card(g) for g in games)

    multi_html = render_multi_section(games)
    summary_html = render_summary_table(games, round_num)

    if template_path:
        with open(template_path) as f:
            tmpl = f.read()
        # Replace game cards section
        gc_start = tmpl.find(f'<p class="section-head">Round {round_num} — All Games</p>')
        gc_end   = tmpl.find("<!-- MULTI SECTION -->")
        ms_end   = tmpl.find("<!-- ROUND SUMMARY TABLE -->")
        st_end   = tmpl.find("</div>", tmpl.find("</tbody>", ms_end)) + 6

        new_html = (tmpl[:gc_start] + cards_html + "\n" +
                    multi_html + "\n" +
                    summary_html + "\n" +
                    tmpl[st_end:])
    else:
        new_html = cards_html + "\n" + multi_html + "\n" + summary_html

    out = out_path or f"index_r{round_num}.html"
    with open(out, "w") as f:
        f.write(new_html)
    print(f"✓ Generated {out}  ({Path(out).stat().st_size:,} bytes)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json",     type=str, required=True)
    parser.add_argument("--template", type=str, default=None)
    parser.add_argument("--out",      type=str, default=None)
    args = parser.parse_args()
    generate(args.json, args.template, args.out)
