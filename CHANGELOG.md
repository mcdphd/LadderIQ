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
