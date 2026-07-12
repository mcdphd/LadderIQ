# Build Process

## Canonical command

```powershell
python .\build_ladder.py
```

## Build stages
- discover source CSV files
- import transactions and positions
- calculate leadership and market mode
- generate ladders
- run QA
- calculate performance
- render HTML
- update version and changelog metadata
- package release

Critical QA failures should stop the build.
