# LadderIQ 3.53.1

## Purpose

Move the authoritative generated report to `reports/latestladder.html` without breaking existing root-level shortcuts.

## Verification

Run `python .\build_ladder.py`, then open `reports\latestladder.html`. Root-level `index.html` and `latestladder.html` should contain the same generated dashboard.
