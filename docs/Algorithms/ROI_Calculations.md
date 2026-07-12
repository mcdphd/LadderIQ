# ROI Calculations

## Net capital invested
Initial contributions plus later external contributions minus withdrawals.

## Personal ROI
`(Current account value - net capital invested) / net capital invested`

Useful for measuring personal wealth growth, but sensitive to contribution timing.

## Time-weighted return
1. Break the performance history at every external cash flow.
2. Calculate each subperiod return before the cash flow is added or removed.
3. Chain the subperiods: `(1+r1)(1+r2)...(1+rn)-1`.

This measures strategy performance independent of contributions and withdrawals.

## Money-weighted return
Use XIRR when measuring the investor's annualized return based on the timing and amount of cash flows.

## Required display
- total contributions
- net invested capital
- dollar gain/loss
- personal ROI
- time-weighted return
- benchmark return using matching periods
