# LadderIQ v3.60.3 — Scanner Stability Patch

- Added QQQ benchmark caching and stale-cache fallback.
- Prevented empty benchmark data from causing `IndexError`.
- Added per-symbol price-history cache under `market_cache/`.
- Refreshes only stale symbols instead of re-downloading every symbol every run.
- Increased batch size, added pacing, bounded retries, and exponential backoff.
- Stops new provider requests when rate limiting is detected and reuses cached data.
- Preserves the last valid `leadership_scores.json` when no usable fresh data exists.
- Added seven-day fundamental cache and bounded fundamental lookups.
- Added scan diagnostics for cache hits, refreshed symbols, provider failures, and rate limiting.
- Disabled Git automatic garbage collection during automated add/commit/push to prevent the `.git/objects/*` retry loop from blocking publication.
