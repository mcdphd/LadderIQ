# LadderIQ 3.54.0 — Tomorrow Ladder

Updated with the latest Fidelity files detected in the project folder.

## Correct PowerShell Workflow

```powershell
cd "C:\Users\mcdph\OneDrive\03 - LadderIQ Platform\04 - Development"
python .\import_fidelity_csv.py
python .\import_positions.py
python .\leadership_scanner.py
python .\build_ladder.py
start .\reports\latestladder.html
```

If `leadership_scanner.py` fails because `yfinance` is not installed, either install it:

```powershell
pip install yfinance
```

or skip that step and build using the latest existing `leadership_scores.json`:

```powershell
python .\build_ladder.py
start .\reports\latestladder.html
```

## CSV Auto-Detection

You no longer need to rename Fidelity exports. The scripts automatically select the newest matching files in the project folder:

- Account history: `Accounts_History*.csv` or `History_for_Account*.csv`
- Positions: `Portfolio_Positions*.csv`

Examples that now work without renaming:

- `Accounts_History.csv`
- `Accounts_History (1).csv`
- `Accounts_History (2).csv`
- `Accounts_History (3).csv`
- `History_for_Account_Z25686771.csv`
- `Portfolio_Positions_Jul-09-2026.csv`

If you need to force a specific history file:

```powershell
python .\import_fidelity_csv.py --csv "Accounts_History (3).csv"
```

If you need to force a specific positions file:

```powershell
python .\import_positions.py --csv "Portfolio_Positions_Jul-09-2026.csv"
```

## Build Script

Use `build_ladder.py`. The old version-specific build name (`build_v41.py`) has been removed.

Do not run `update_portfolio.py`; that file is not part of this system.

## 3.54.0 Features

- Portfolio Command Center layout
- Decision Center: Buy Today / Sell Today / Watch Closely
- Left-side portfolio hierarchy
- Opportunity Score and Business Quality are separated.
- Benchmark vs QQQ card uses cash-flow-segmented TWR and keeps Personal ROI separate.
- Capital ledger records the $5,055.52 external contribution without treating it as gain.
- Adaptive learning records NVDA and AMZN manual ladder overrides for future rule proposals.
- META remains removed.

## Latest Build Inputs

- Positions file: `Portfolio_Positions_Jul-16-2026.csv`
- Account Total: $18,497.09
- Effective Cash: $1,892.50
- ROI Since Inception: 35.59%
- Next ladder: Thursday, July 16, 2026
