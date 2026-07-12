# Getting Started

## Daily workflow

1. Export the latest Fidelity account history and portfolio positions CSV files into the project folder.
2. Run:

```powershell
python .\import_fidelity_csv.py --csv "<latest history file>"
python .\leadership_scanner.py
python .\build_ladder.py
start .\reports\latestladder.html
```

The current build is intended to auto-detect Fidelity filenames matching `Accounts_History*.csv` and `Portfolio_Positions*.csv` where supported.

## Core files

- `build_ladder.py` — primary build script.
- `leadership_scanner.py` — calculates current technical leadership.
- `portfolio_state.json` — account state, cash, positions, and market mode.
- `transactions.json` — normalized trade history.
- `strategy_profile.json` — user-approved strategy settings.
- `learning_events.json` — recorded overrides and learning observations.
- `reports/latestladder.html` — authoritative latest generated dashboard.
- `latestladder.html` and `index.html` — temporary compatibility copies.

## Documentation map

- `01_CHANGELOG.md` — what changed.
- `02_HISTORY.md` — how the product evolved.
- `03_DECISIONS.md` — why major decisions were made.
- `04_DESIGN_PHILOSOPHY.md` — principles governing the system.
- `05_ROADMAP.md` — planned development.
