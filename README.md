# lean-trading

Develop and troubleshoot QuantConnect (LEAN) strategies in Python locally,
then copy them into the QuantConnect browser IDE for deployment.

## Workflow

```
edit locally (VS Code + Pylance sees LEAN stubs)
        ↓
python tools/format_for_qc.py strategies/<name>/main.py --clipboard
        ↓
paste into QC browser IDE → click Backtest
        ↓
on error, copy traceback → python tools/parse_error.py --clipboard --open
        ↓
VS Code jumps to the offending line in your local file
```

## First-time setup

```bash
pip install -r requirements-dev.txt
lean login
```

For local backtesting you also need Docker; see "Local backtesting" below.

## Repository layout

```
strategies/<name>/main.py    # one file per strategy (QC-compatible)
strategies/_template/        # skeleton to copy
tools/parse_error.py         # QC traceback → local file:line refs
tools/format_for_qc.py       # strip local imports, ensure AlgorithmImports, copy to clipboard
tools/download_data.py       # populate ./data/ with yfinance data + factor files
tools/setup_local.sh         # check Docker, lean init, run download_data.py
lean_stubs/                  # LEAN API stubs for offline type checking
data/                        # local historical data (gitignored)
```

## Editing a strategy

```bash
cp -r strategies/_template strategies/my_strategy
$EDITOR strategies/my_strategy/main.py
```

Type checking works offline through `lean_stubs/AlgorithmImports.pyi`. If you
install LEAN CLI's bundled Python and select it in VS Code, Pylance will use
the real LEAN stubs instead (better fidelity).

## Backtesting

### Cloud (no local data, uses QC quota)

```bash
lean cloud backtest strategies/<name> --open
```

Works on QuantConnect's free plan but is subject to the daily backtest quota.

### Local (no quota, requires Docker + data)

```bash
bash tools/setup_local.sh       # one-time
lean backtest strategies/<name> --open
```

`setup_local.sh` checks Docker is running, bootstraps the data folder
with `lean init` if needed, then runs `tools/download_data.py`, which
fetches `data/tickers.default.txt` (SPY) at daily resolution from
2010-01-01 to today via `yfinance`. No paid QuantConnect subscription
required.

## Pasting a strategy into the QC IDE

```bash
python tools/format_for_qc.py strategies/<name>/main.py --clipboard
# switch to QC browser IDE, paste, click Backtest
```

`format_for_qc.py` strips local-only imports (anything from `lean_stubs.*`),
ensures `from AlgorithmImports import *` is present, and copies the cleaned
source to your clipboard.

## Debugging a QC error

```bash
# 1. Copy the traceback from the QC IDE
# 2. Run:
python tools/parse_error.py --clipboard --open
# 3. VS Code opens each local frame at the right line.
```

`parse_error.py` filters out LEAN-internal frames and only surfaces frames
inside this repo.

## Validation before finishing edits

If you change `strategies/<name>/main.py`, validate before committing:

```bash
python -c "import ast; ast.parse(open('strategies/<name>/main.py').read())"
```

If LEAN CLI is installed, prefer:

```bash
lean backtest strategies/<name> --open        # local, no quota
# or
lean cloud backtest strategies/<name> --open  # cloud, no local data
```

See `AGENTS.md` for the full agent validation checklist.
