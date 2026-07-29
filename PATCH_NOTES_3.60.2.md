# LadderIQ v3.60.2 Patch Notes

## Broad-Market Symbol Hygiene Fix

- Rejects preferred-share and special-issue symbols such as `BAC$L`, `DBRG$J`, and `GAB$H` before Yahoo Finance requests.
- Excludes ETFs, warrants, rights, units, notes, debt securities, depositary preferreds, and other non-common issues from automatic discovery.
- Preserves legitimate class-share symbols and converts dot notation such as `BRK.B` to Yahoo's `BRK-B` format.
- Invalidates the prior universe cache by introducing cache schema version 2, forcing one clean rebuild.
- Validates symbols again immediately before price-history download.
- Captures expected yfinance invalid-symbol noise and reports a concise scan summary instead of hundreds of console warnings.
- Reduces batch size from 100 to 75 for more reliable provider requests.
- Adds universe-filter and download diagnostics to `leadership_scores.json`.

Apply these files over v3.60.1, preserving their paths.
