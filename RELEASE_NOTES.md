# LadderIQ v3.55.2 Release Notes

## Dynamic Allocation Rebalancing

This patch makes NVDA's management ladder responsive to both completed transactions and the latest Opportunity Score.

### Current July 22 recalculation
- Current NVDA shares: 28.306
- Current portfolio weight: 32.03%
- Opportunity Score: 90
- Dynamic target weight: 30.00%
- Remaining excess: approximately 1.792 shares
- New ladder: 0.717, 0.627, and 0.448 shares at progressively higher limit prices

The previous fixed 3, 4, and 5-share ladder is no longer used.

### Additional correction
When multiple Fidelity position exports have the same date, LadderIQ now selects the newest numbered export, such as `Portfolio_Positions_Jul-22-2026 (1).csv`.
