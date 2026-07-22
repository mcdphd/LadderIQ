# Patch Notes — v3.55.1 Dynamic Growth Candidates

## Scope
Only Section 5, **Growth Candidates**, was changed. Sections 1–4 remain fixed exactly as configured.

## Changes
- Rebuilds Growth Candidates on every run from `watchlist.json` → `watch_candidates`.
- Includes every non-owned candidate with a current Leadership/Opportunity Score of 60 or higher.
- Displays one candidate when one qualifies and multiple candidates when multiple qualify.
- Sorts only Growth Candidates by score; Sections 1–4 retain their configured order.
- Uses Candidate/Candidates wording rather than Holdings for Section 5.
- Does not create automatic buy ladders for candidates.
