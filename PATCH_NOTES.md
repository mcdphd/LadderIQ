# Patch Notes — v3.55.0

**Date:** 2026-07-20  
**Patch:** Classification and Date Synchronization

## Issues Addressed
1. ARM displayed as Watch List despite a qualifying Opportunity Score of 65.
2. Stocks inside portfolio groups retained static ordering.
3. Decision Center Buy Today could differ from the stock detail initially displayed.
4. Ladder-facing date labels were calculated independently.

## Files Updated
- `build_ladder.py`
- `generate_ladder.py`
- `index.html`
- `latestladder.html`
- `position_lifecycle.json`
- `version.json`
- `README.md`
- `CHANGELOG.md`
- `RELEASE_NOTES.md`
- `PATCH_NOTES.md`

## Validation
- Python compilation passed.
- Generator completed successfully using the July 20 Fidelity positions export.
- Generated output reports version 3.55.0.
- ARM renders as a Growth Candidate.
- All ladder date labels read from `metrics.ladder_for`.
- Decision Center and initial stock detail share the same highest-priority buy symbol.
