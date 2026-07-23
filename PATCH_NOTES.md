# LadderIQ Patch Notes — v3.55.2

## Business Rule Added
**BR-021 — Dynamic Allocation Rebalancing**

After every imported trade, LadderIQ now:
1. Reads the latest post-transaction position.
2. Recalculates the target allocation from the current Opportunity Score.
3. Measures only the remaining excess above target.
4. Regenerates the sell ladder from that remaining excess.

## NVDA Result for the Current Data
- 28.306 shares at 32.03% of the portfolio
- Opportunity Score 90
- Target allocation 30.00%
- Remaining sell quantity approximately 1.792 shares
- Three recalculated rungs: 0.717, 0.627, and 0.448 shares

## Files Changed
- `build_ladder.py`
- `generate_ladder.py`
- `index.html`
- `latestladder.html`
- `reports/latestladder.html`
- `README.md`
- `version.json`
- `CHANGELOG.md`
- `RELEASE_NOTES.md`
- `PATCH_NOTES.md`

No `__pycache__` files are included.
