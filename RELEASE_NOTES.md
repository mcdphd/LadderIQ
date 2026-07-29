# LadderIQ 3.60.0 — Intelligent Opportunity Engine

- Broad, liquid opportunity universe spanning all major market sectors.
- Growth Candidates now require a confirmed Opportunity Score of 100.
- Two-trading-day confirmation replaces the prior long persistence rule.
- Severe deterioration can trigger an immediate risk override.
- Every actionable recommendation connects directly to one ladder.
- Owned securities generate sell/management ladders only.
- Unowned confirmed opportunities generate buy ladders only.
- Position states added: Harvest, Hold, Recovery, and Defensive.
- Sell ladders are state-driven from current market structure rather than rigidly anchored to cost basis or automatically lowered after a dip.
- Mission pace compares current return with the compounded pace required for the aggressive 100% annual ROI objective.
- BAT and PowerShell launch paths are portable outside OneDrive.

## v3.60.1 — Automatic Broad-Market Discovery

- Removed `watchlist.json` from candidate discovery, scoring, ranking, and Growth Candidate population.
- Added official Nasdaq Trader universe acquisition with a seven-day local cache.
- Added price, history, liquidity, market-cap, security-type, and data-quality eligibility gates.
- Added staged technical scanning across the broad market and fundamental review of the strongest names.
- Added business-quality, sector-leadership, reward/risk, expected-upside, and return-velocity measures.
- Added composite OPS weighting: 45% technical, 30% business quality, 15% sector leadership, and 10% risk-adjusted return.
- Defined 100 OPS as a qualification tier rather than simple score saturation.
- Growth Candidates now include all non-owned, eligible, confirmed 100-OPS stocks found by the scanner.
- Added volatility-adjusted buy-ladder spacing and ranked candidate capital allocation.
- Added automatic management coverage for brokerage holdings outside the historical fixed groups.
- Added `strategy_rules.json` for auditable runtime thresholds.


## 3.60.5 — Automatic Candidate Visibility
Removed the obsolete Watch List UI, added automatic confirmed/emerging Growth Candidates, practical 95+ confirmation threshold, 90–94 emerging tier, scan diagnostics, and consistent version display.
