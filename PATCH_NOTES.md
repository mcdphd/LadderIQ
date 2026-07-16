# LadderIQ Patch Notes

**Patch:** Position Lifecycle Manager  
**Version:** 3.54.0  
**Date:** 2026-07-16

## Issue
Closed positions could remain visible in the dashboard because stock membership, watchlist state, rotation state, and current holdings were maintained separately.

## Changes
- Added explicit lifecycle states: `owned`, `active_candidate`, `watchlist`, `recently_exited`, and `archived`.
- Added `position_lifecycle.json` as the lifecycle source of truth.
- Archived AMZN after full liquidation.
- Removed AMZN from active holdings, sidebar navigation, Decision Center, and active rotation logic.
- Preserved AMZN history in archived lifecycle and rotation records.
- Replaced hard-coded AMZN Decision Center logic with dynamic selection.
- Updated generated `index.html` and `latestladder.html`.

## Files Included
- `build_ladder.py`
- `generate_ladder.py`
- `index.html`
- `latestladder.html`
- `position_lifecycle.json`
- `watchlist.json`
- `rotation_state.json`
- `portfolio_state.json`
- `version.json`
- `CHANGELOG.md`
- `RELEASE_NOTES.md`
- `PATCH_NOTES.md`

## Installation
Copy these files into the live Development folder and overwrite the existing files. Do not replace `__pycache__`, `reports`, or any other folders. Then run the existing BAT file.
