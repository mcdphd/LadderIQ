## 3.60.22 — Growth Candidate OPS-band upside ranking

- Growth Candidates remain primarily ranked by News-Refined/Actionable OPS.
- Candidates within the same 5-point OPS band are secondarily ranked by Expected Upside (highest first).
- Exact OPS is the next tie-breaker, followed by the existing trend/leadership/rank tie-breakers.
- No eligibility, OPS, news, ladder, portfolio, or capital-allocation logic changed.

## 3.60.21 — Confirmed-first News-Refined OPS

- Fixes the v3.60.20 scoring-order defect.
- Actionable / sidebar OPS is now Confirmed OPS + News Impact.
- Example: NVDA Confirmed OPS 43 + News Impact -8.1 = News-Refined OPS 34.9.
- Positive news may improve ranking above 100 but cannot create buy eligibility; negative news can remove eligibility.
- Sidebar and dashboard ranking continue to use the actionable News-Refined OPS.

## 3.60.21 — News-refined OPS ranking
- Allows positive News-Refined OPS to exceed 100 for transparent tie-breaking.
- Sidebar badges and within-category sorting use News-Refined OPS.
- Positive news cannot create buy eligibility; negative news can reduce/remove eligibility.
- Base OPS remains normalized to 0–100 and Confirmed OPS remains the execution gate.

## 3.60.20
- UI consistency fix: render the News Refinement callout for all displayed securities, including Special Situations.
- If no material event is present, display: "No material recent company-news event detected."
- No scoring, news adjustment, OPS, recommendation, ladder, or market-regime logic changed.

# Changelog

## 3.60.11 — 2026-08-04
- Classifies Fidelity money-market holdings such as FDRXX, PDRXX, SPAXX, and SPRXX as cash equivalents.
- Includes cash-equivalent market value in effective cash and buying power.
- Excludes cash equivalents from OPS candidate discovery, buy/sell ladder generation, and sell-ladder validation.
- Prevents the `$1.00 is not above current price $1.00` generation failure.

## v3.55.2 — Dynamic Allocation Rebalancing (2026-07-22)
- Added BR-021 to recalculate NVDA target allocation from the latest Opportunity Score after every imported trade.
- Rebuilds the sell ladder from the current post-transaction position rather than carrying forward fixed 3/4/5-share rungs.
- At a 90 Opportunity Score, NVDA uses a 30% target allocation; only the remaining excess above that target is laddered for sale.
- Sell-ladder Trim percentages now reflect each rung's actual percentage of the current position.
- Improved same-day Fidelity positions-file selection so the newest numbered export is used.

## v3.55.1 — Dynamic Growth Candidates (2026-07-22)
- Section 5 now refreshes automatically from the opportunity universe.
- Shows every non-owned watch candidate scoring 60 or higher.
- Sections 1–4 and their ordering remain unchanged.
- Growth Candidates displays Candidate/Candidates instead of Holdings.

# Changelog

## v3.55.0 — 2026-07-20

### Added
- Portfolio Classification Engine v1.0 for non-owned candidate placement.
- `Growth Candidates` portfolio group for qualifying names with opportunity scores of 60 or higher.
- Dynamic within-category sidebar sorting by Opportunity Score, trend, leadership, and existing rank.
- OPS label on sidebar score badges to distinguish Opportunity Score from Business Quality.

### Changed
- ARM is now classified as a Growth Candidate rather than a passive Watch List name.
- Decision Center and the initial stock detail panel now open on the same highest-priority buy candidate.
- Decision Center date, sidebar date, and footer date now consume one shared Ladder Date value.
- Version advanced to 3.55.0.

### Business Rules
- BR-018 — Unified Ladder Date: all ladder-facing date labels use the generator's single Eastern-time date. Runs on weekends roll forward to Monday.
- BR-019 — Candidate Classification: a non-owned, visible symbol with Opportunity Score >= 60 is a Growth Candidate; lower-scoring names remain Watch List.
- BR-020 — Dynamic Sidebar Ranking: stocks are ordered inside each group by Opportunity Score, trend, leadership, then prior rank.

## 3.54.0 — Position Lifecycle Manager (2026-07-16)
- Added explicit lifecycle states: owned, active candidate, watchlist, recently exited, and archived.
- Archived zero-share harvest-only positions are removed from the active dashboard while history is preserved.
- Removed AMZN from active holdings, sidebar, decision cards, and rotation decisions after full liquidation.
- Replaced hard-coded AMZN Decision Center logic with dynamic candidate selection.
- Added `position_lifecycle.json` as the lifecycle source of truth.

# V3.53.2 — Dynamic QQQ benchmark refresh

- Refreshes QQQ daily history directly from Yahoo Finance whenever the build runs.
- Uses today as Yahoo's exclusive end date, so the benchmark slider ends on the latest completed trading session (T-1).
- Falls back to yfinance, then to embedded history, if Yahoo is unavailable.
- Removes the hard-coded 2026-07-10 benchmark endpoint.

# Changelog

## 3.53.1 — Report Path Compatibility

### Changed
- Made `reports/latestladder.html` the authoritative generated report.
- Added automatic dated report snapshots under `reports/archive/`.
- Updated all supported workflow instructions to open the report from `reports`.

### Compatibility
- Retained root-level `index.html` and `latestladder.html` copies temporarily.
- Updated QA validation to verify all three report outputs.
- Made project-root resolution independent of the PowerShell working directory.

# LadderIQ Changelog

> Historical entries before 3.53.0 are reconstructed from design sessions and release artifacts rather than a formal source-control history.

## 3.53.0 — Adaptive Foundations (2026-07-10)

### Added
- Official `major.minor.patch` versioning and `version.json`.
- Clean documentation, data, report, template, and archive structure.
- Capital ledger for the original contribution and the $5,055.52 external contribution.
- Cash-flow-segmented time-weighted return alongside personal ROI.
- Legacy Holdings framework for employer equity such as BAH.
- Adaptive override and strategy-profile scaffolding.

### Improved
- Consolidated the build command under `build_ladder.py`.
- Preserved automatic detection of numbered Fidelity exports.
- Separated Opportunity Score from Business Quality.
- Preserved interactive QQQ comparison and benchmark slider.
- Added sell-ladder QA so the first harvest level cannot sit at or below current market price.

### Fixed
- Corrected Amazon's first sell rung so it begins above market.
- Reflected the two-share NVDA harvest and retained higher sell layers.
- Restored benchmark/replay metrics after earlier dashboard regressions.

### Migration note
- Root-level compatibility files remain for a safe daily workflow; canonical organized copies now live under `data/`.

> **Historical note:** Versions before the semantic-versioning baseline were reconstructed from design sessions, generated releases, and project files. Exact internal build-to-feature mapping may be imperfect.

## Planned 3.53.0 — Documentation and semantic-versioning baseline

### Added
- `Major.Minor.Build` versioning standard.
- `/docs` knowledge-base structure.
- `PROJECT_STATUS.md`.
- Reconstructed project history, decisions, architecture, algorithms, guides, and roadmap.

### Improved
- Defined release criteria for major, minor, and build increments.
- Established one permanent build script: `build_ladder.py`.

## 3.53.0 — Ladder QA correction

### Fixed
- Prevented AMZN first sell rung from being generated below the latest market price.
- Added validation requiring first sell levels to sit above current price by a configurable minimum distance.

### Improved
- Strengthened sell-ladder QA checks.

## V55 — Monday ladder and cash-flow-aware performance

### Added
- Capital event for the $5,055.52 contribution.
- Personal ROI and time-weighted return concepts.
- Adaptive override records.
- BAH legacy transition treatment.

### Updated
- Reflected NVDA sale of 2 shares at $210.085.
- Preserved remaining NVDA sell ladder beginning at 3 shares near $214.
- Reflected BAH reduction and updated cash.
- Adjusted AMZN first exit behavior based on user override.

## V54 — Benchmark-card restoration

### Fixed
- Restored the full Benchmark vs. QQQ section after a template regression.
- Reconnected portfolio, QQQ, buy-and-hold, ladder-alpha, and value-added fields to the slider layout.

## V53 — Latest positions and transactions

### Updated
- Imported July 9 portfolio positions and account history.
- Rebuilt ladders and dashboard from the latest Fidelity exports.

## V52b/V52c — File detection and workflow hardening

### Added
- Automatic detection of the newest `Accounts_History*.csv` file.
- Automatic detection of the newest `Portfolio_Positions*.csv` file.

### Improved
- Updated README workflow to remove filename-renaming steps.
- Preserved raw Fidelity filenames while normalizing internal data.

## V52/V52a — Replay and build cleanup

### Added
- Portfolio replay inputs.
- QQQ benchmark history support.
- Slider-driven comparison framework.

### Changed
- Renamed `build_v41.py` to `build_ladder.py`.
- Removed remaining version-specific build-script naming.

## V51 — Expanded benchmark metrics

### Added
- Buy-and-hold ROI placeholder.
- Ladder alpha placeholder.
- Value-added placeholder.

### Known limitation
- Portfolio ROI remained static while QQQ moved with the slider; this exposed the need for a full daily replay engine.

## V50/V49 — Interactive benchmark comparison

### Added
- QQQ comparison card without adding a new dashboard row.
- Slider with a minimum date of April 7, 2026.
- Date-range selection for benchmark comparison.

### Improved
- Compressed existing dashboard cards to preserve layout density.

## V48 — QQQ benchmark integration

### Added
- Portfolio ROI vs. QQQ comparison.
- Alpha display.

## V47 — Legacy Holdings architecture

### Added
- Active Holdings, Approved Universe, and Legacy Holdings concepts.
- `Reason I Own This` field.
- BAH treatment as employer-stock/legacy capital rather than a normal LadderIQ selection.

## V46 — Score-label correction

### Changed
- Reframed the sidebar score as an Opportunity Score rather than a long-term business-quality score.
- Separated current technical leadership from business quality and capital-allocation priority.

## V45 and earlier — Portfolio command center evolution

### Added over multiple releases
- Portfolio Command Center dashboard.
- Buy Today / Sell Today / Watch Closely decision center.
- Portfolio hierarchy and one-stock focus view.
- Simultaneous buy and sell ladders.
- Leadership scanner and external-leadership tracker.
- Rotation engine and strategic-core demotion guard.
- Market modes: Bull, Neutral, Bear.
- Core, Tactical, Growth Engine, Special Situation, and legacy/exit concepts.
- Fidelity transaction and position importers.
- QQQ market-mode benchmark.
- QA validation reports.

### Key strategy decisions
- TSM and PANW treated as strategic P1 leaders.
- ANET and NVDA treated as tactical P2 holdings during the relevant period.
- SPCX governed separately as a strategic special situation.
- META removed after the position was fully exited.
- AMZN transitioned away from routine accumulation when leadership weakened.

## Project inception — Ladder system foundations

### Initial capabilities
- Manual buy and sell ladders.
- Position sizing by shares and dollars.
- Cash reserve management.
- Daily and weekly review cadence.
- Discipline-first execution rules.
- Initial focus on AI infrastructure and high-conviction technology leaders.

## 3.53.3 — Closed-position ladder cleanup
- Added BR-017 Active Position Rule: sell ladders are generated only for imported positions with a meaningful positive quantity and market value.
- Suppressed stale zero-share sell ladders for fully liquidated securities such as AMZN.
- Added explicit `has_active_position` and `position_status` fields to generated stock data.
- Replaced empty sell-ladder rows with a clear "Position Closed" message.
- Applied the same logic to both `build_ladder.py` and `generate_ladder.py`.

### 3.60.1
- Broad-market scanner replaces watchlist-driven candidate discovery.
- Composite opportunity scoring and automatic cross-sector candidate population.
- Volatility-adjusted entry ladders and ranked candidate budgets.


## 3.60.5 — Automatic Candidate Visibility
Removed the obsolete Watch List UI, added automatic confirmed/emerging Growth Candidates, practical 95+ confirmation threshold, 90–94 emerging tier, scan diagnostics, and consistent version display.


### Phase 1 Capital Efficiency Engine
* Added fixed-weight capital allocation framework.
* Added Hold Cash / No Trade rule.
* Added infrastructure for future adaptive learning.

## 3.60.8 — Dual-Ladder Position Management
- Restored buy ladders for owned positions with confirmed OPS of 75 or higher, an Up trend, and no Defensive/Recovery risk state.
- Kept sell/management ladders visible at the same time; ownership no longer forces a sell-only view.
- Added conservative accumulation budgets for newly imported approved holdings.
- Updated the position detail layout to display buy and sell ladders together.
- Preserved sell-only behavior for weak, recovery, defensive, harvest-ineligible, and special-situation positions.


## 3.60.10 — All-Section Ladder Hover
- Extended the existing mobile/hover insight popup from Growth Candidates to every portfolio section.
- Displays compact active buy and sell ladder rows using only limit price and shares.
- Preserved all Phase 1 scoring, recommendation, allocation, and ladder-generation logic.

## 3.60.13 — Maximum Harvest Sizing
- Removed the NVDA-only excess-weight sell cap that produced undersized ladders.
- Standardized maximum sell-ladder coverage by recommendation state: Hold 60%, Harvest 80%, Recovery 60%, Defensive 100%.
- Preserved cost-basis protection for ordinary Hold and Harvest ladders.
- Preserved AMZN exit and SPCX special-situation rules.

## 3.60.14 — Sidebar Sell Coverage Label
- Added a compact `(Sell: X%)` label immediately after each owned stock symbol.
- Percentage is calculated from the shares currently included across all active sell-ladder rungs.
- No scoring, classification, price, sizing, or recommendation logic changed.

## 3.60.16 — Targeted News-Refined OPS
- Added a targeted Finnhub company-news refinement layer after the quantitative broad-market scan.
- News scans only owned positions plus non-owned names with Base OPS >= 75.
- Preserves Base OPS, News Adjustment, News-Refined OPS, and Confirmed OPS separately for auditability.
- Material-event adjustment is bounded to -15 / +10 points and does not replace the quantitative model.
- Uses event-oriented rules for guidance, major customers/demand, earnings, contracts, regulatory/legal, management, product/operations, and financing/liquidity developments.
- Deduplicates syndicated headlines and prevents one story from being counted multiple times for the same event.
- Uses a 30-minute local news cache and safely respects Finnhub's free-tier request rate.
- Fails open: if Finnhub or FINNHUB_API_KEY is unavailable, Base OPS remains unchanged and LadderIQ still builds.
- Dashboard Recommendation State now exposes Base OPS, News Impact, News-Refined OPS, and the material-news rationale.
