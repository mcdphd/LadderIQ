# Major Design Decisions

## D-001 — Use ladders instead of binary trades
**Decision:** Stage entries and exits across multiple prices and quantities.  
**Reason:** Reduce timing risk and emotional decision-making.

## D-002 — Separate business quality from opportunity
**Decision:** Business Quality changes slowly; Opportunity Score changes daily.  
**Reason:** A great company can be a poor destination for the next dollar.

## D-003 — Preserve strategic-core safeguards
**Decision:** One weak technical reading cannot automatically demote strategic core.  
**Reason:** Avoid strategy drift caused by short-term noise.

## D-004 — Maintain a cash reserve
**Decision:** Preserve dry powder instead of deploying all capital immediately.  
**Reason:** Optionality matters during pullbacks and leadership changes.

## D-005 — Create Legacy Holdings
**Decision:** Employer stock, inherited assets, and transferred positions use transition rules.  
**Reason:** Ownership source should not force an asset into the active strategy.

## D-006 — Use QQQ as the primary benchmark
**Decision:** Compare strategy performance to QQQ over matching dates.  
**Reason:** Absolute gains are insufficient; the process must justify its complexity.

## D-007 — Add buy-and-hold and ladder alpha
**Decision:** Compare actual results to holding the same selected stocks without trading.  
**Reason:** Separate stock-selection skill from execution skill.

## D-008 — Use cash-flow-segmented returns
**Decision:** Break performance at external contributions and withdrawals and chain subperiod returns.  
**Reason:** Deposits must not distort strategy performance.

## D-009 — Human approval is mandatory
**Decision:** The AI may propose strategy changes but may not silently apply them.  
**Reason:** Prevent uncontrolled learning and preserve accountability.

## D-010 — Record override reasons
**Decision:** Manual changes should capture what changed and why.  
**Reason:** Outcome data without intent cannot produce reliable learning.

## D-011 — Sell ladders must clear current price
**Decision:** Normal profit-taking sell orders may not begin at or below the latest market price.  
**Reason:** Such orders become accidental marketable orders rather than deliberate harvests.

## D-012 — Use one permanent build script
**Decision:** Use `build_ladder.py` rather than versioned build filenames.  
**Reason:** Version belongs in release metadata, not source filenames.

## D-013 — Adopt semantic versioning
**Decision:** Use `Major.Minor.Build`, for example `3.53.1`.  
**Reason:** Distinguish architectural releases, meaningful feature increments, and patches.
