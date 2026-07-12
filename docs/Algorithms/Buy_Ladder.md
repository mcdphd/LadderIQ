# Buy Ladder

Buy ladders stage capital below the current reference price unless the order is explicitly classified as a breakout entry.

## Inputs
- market mode
- priority tier
- latest price
- available cash
- target position weight
- volatility / spacing rule

## QA requirements
- ordinary buy levels should not exceed current market price
- aggregate allocation must not exceed deployable cash
- resulting position should respect concentration limits or issue a warning
