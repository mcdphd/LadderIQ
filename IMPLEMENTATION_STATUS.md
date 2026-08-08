# LadderIQ v3.60.1 Implementation Status

This release implements the executable core of the updated rulebook:

- watchlist-independent broad-market discovery
- exchange/security eligibility and liquidity screens
- technical, fundamental, sector-leadership and risk/return scoring
- composite OPS and 100-OPS qualification tier
- two-session confirmation and immediate risk override
- automatic Growth Candidate population
- buy-only ladders for non-owned candidates
- sell/management-only ladders for owned stocks
- volatility-adjusted buy spacing
- ranked candidate allocation with sector-concentration adjustment
- 100% annual ROI pace controls

The scanner uses official Nasdaq Trader symbol directories and Yahoo Finance.
A full scan can take several minutes and requires internet access. The first
qualifying observation is marked Emerging; the stock becomes a displayed Growth
Candidate after a second distinct market session at the qualifying level.

### 3.60.16 News Refinement
Implemented targeted Finnhub news refinement after Base OPS calculation and before opportunity confirmation/ladders. Audit fields: base_ops, news_adjustment, final_ops, news_risk_level, news_reason, news_sources, news_checked_at. Missing/unavailable news access retains Base OPS.
