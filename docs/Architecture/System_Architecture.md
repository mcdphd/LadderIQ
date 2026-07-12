# System Architecture

## Inputs
- Fidelity account-history CSV exports.
- Fidelity portfolio-position CSV exports.
- Market price history.
- Watchlist and leadership-state files.
- Strategy profile and user overrides.

## Processing layers
1. Import and normalize transactions.
2. Import positions and cash.
3. Retrieve or read market data.
4. Calculate market mode and leadership.
5. Calculate opportunity and capital priority.
6. Generate candidate ladders.
7. Run ladder QA.
8. Calculate performance and benchmarks.
9. Render dashboard and reports.

## Outputs
- `reports/latestladder.html` (authoritative)
- `reports/archive/YYYY-MM-DD.html` (dated snapshots)
- `index.html` and `latestladder.html` (temporary compatibility copies)
- state JSON files
- QA reports
- release ZIP

## Architectural rule
Generated HTML should come from one authoritative build path. Hand-edited output must not become the source template.
