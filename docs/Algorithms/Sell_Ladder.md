# Sell Ladder

Sell ladders harvest strength in planned increments.

## Core validation
For normal harvest orders, the first sell price must be greater than the latest market price by at least the configured minimum distance.

## Additional checks
- total shares sold cannot exceed holdings
- levels must rise monotonically
- proceeds must be calculated from current share quantities
- a below-market sell requires an explicit exit or risk-reduction classification
