## 3.54.0 — Position Lifecycle Manager (2026-07-16)
- Added explicit lifecycle states: owned, active candidate, watchlist, recently exited, and archived.
- Archived zero-share harvest-only positions are removed from the active dashboard while history is preserved.
- Removed AMZN from active holdings, sidebar, decision cards, and rotation decisions after full liquidation.
- Replaced hard-coded AMZN Decision Center logic with dynamic candidate selection.
- Added `position_lifecycle.json` as the lifecycle source of truth.

# LadderIQ 3.53.1

## Purpose

Move the authoritative generated report to `reports/latestladder.html` without breaking existing root-level shortcuts.

## Verification

Run `python .\build_ladder.py`, then open `reports\latestladder.html`. Root-level `index.html` and `latestladder.html` should contain the same generated dashboard.

## Version 3.53.3
Closed positions no longer generate sell ladders. Legitimate fractional-share positions remain supported; only positions with effectively zero quantity or less than $1 market value are treated as closed. The UI now identifies these positions as closed and explains that no sell ladder is required.
