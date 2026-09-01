# Project Status

**Product:** LadderIQ  
**Version:** 3.60.29  
**Release:** Capital Preservation Shadow  
**Status:** Phase 1 observational / no live ladder impact  
**Release date:** 2026-09-01

## Current Phase 1 controls

- Broad-market Opportunity Score scanner and confirmation logic remain authoritative for live opportunity selection.
- News refinement remains bounded and fails open.
- Market Regime remains shadow-only.
- NE Weather remains research-only.
- Capital Preservation is now shadow-only and records a 0–100 recession/crisis risk score from four equal pillars:
  - market deterioration
  - economic deterioration
  - financial stress
  - breadth / leadership stress
- Capital Preservation history is written to `capital_preservation_history.json`.
- Hypothetical preservation sell ladders are displayed only when the shadow regime reaches Preservation, Recession, or Crisis.
- Hypothetical below-cost rungs explicitly state why the normal profit floor would be overridden.
- Live sell ladders remain protected by the existing cost-basis profit floor in Phase 1.

## Capital Preservation regimes

- 0–24: Growth — hypothetical buy capital 100%
- 25–44: Caution — hypothetical buy capital 75%
- 45–64: Preservation — hypothetical buy capital 40%
- 65–79: Recession — hypothetical buy capital 15%
- 80–100: Crisis — hypothetical buy capital 5%

## Phase 2 backlog

- Backtest Capital Preservation thresholds and hysteresis against 2000–02, 2008–09, 2020, and 2022.
- Validate the shadow model against accumulated live observations before activation.
- **Go live with Capital Preservation-adjusted ladders only after validation.**
- In Phase 2, allow Preservation/Recession/Crisis to override the ordinary profit floor when risk evidence warrants a below-cost sale.
- Every live below-cost sell must include a short, stock-specific explanation showing the capital-preservation regime, relevant macro/market triggers, stock-level weakness, and estimated loss versus average cost.
- Add regime hysteresis / confirmation rules so one noisy data point cannot rapidly flip Growth ↔ Preservation.
- Add staged recovery/re-entry logic to redeploy preserved cash as breadth, financial stress, and market structure recover.
