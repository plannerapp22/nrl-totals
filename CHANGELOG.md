# Changelog

## v2.0 — Round 17, 2026
- New methodology spec published (see METHODOLOGY.md)
- Data scope limited to 2025–26 only (2026 full weight, 2025 at 60%)
- Primary signal shifted to current season form (last 5 games) — replaces raw H2H averages
- H2H data now measured against actual market line (not raw combined average)
- Conflict resolution: recent form beats historical H2H
- Verdict system updated: STRONG BET / BET / LEAN / ADJUSTED / WATCH / PASS + confidence %
- Multi section: auto-selection threshold raised to 80%+ (aiming 90s), adjusted lines derived from historical result distribution
- Terminology: parlay → multi throughout
- Data display: "4 unders, 3 overs from 7 games" replaces "4U/3O"
- Staging workflow introduced: HTML preview before push
- Data caching architecture introduced: persistent JSON store, weekly delta pulls only

## v1.0 — Rounds 1–16, 2026
- Initial model: H2H average combined score vs current market line
- Primary signal: H2H avg vs line gap
- Recency-weighted record (2022+)
- Under-bias identified R16 — corrected in v2.0
