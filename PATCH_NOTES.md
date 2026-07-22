# LadderIQ Patch Notes

## Fix
Restored the pre-v3.55.1 sidebar ordering behavior for Sections 1–4.

- Core Compounders now sorts by Opportunity Score, so PANW appears before TSM.
- Tactical Compounders, Growth Engine, and Special Situations use the same prior score-driven ordering.
- Dynamic Growth Candidates logic remains unchanged.
- No category membership or business rules were changed.
- No `__pycache__` files are included.

## Files Changed
- `build_ladder.py`
- `generate_ladder.py`
- `index.html`
- `latestladder.html`
- `reports/latestladder.html`
