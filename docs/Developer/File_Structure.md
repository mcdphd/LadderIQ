# File Structure

## Root
Build scripts, current inputs, current state, generated dashboard, release documentation.

## `/docs`
Product knowledge base.

## Recommended future directories
- `/src` — application code
- `/data` — normalized state
- `/imports` — raw broker exports
- `/output` — generated reports
- `/tests` — automated tests

Migration should occur deliberately in a major release to avoid breaking the current daily workflow.
