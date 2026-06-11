# Local data

This directory holds LEAN historical data, populated by
`tools/download_data.py` (which fetches adjusted prices from `yfinance` and
writes them in LEAN's expected format).

Everything in here is gitignored except this README, the `.gitkeep` marker,
and the default tickers list.

## Quick start

```bash
bash tools/setup_local.sh
```

The setup script:

1. Checks that `docker` and `lean` CLI are installed and running.
2. Bootstraps the data folder with `lean init` if it hasn't been already
   (this works without a paid QuantConnect login).
3. Calls `python tools/download_data.py` to fetch data via `yfinance`.

If you only want to re-pull data (after the workspace is already
initialized):

```bash
python tools/download_data.py
```

## What the script writes

For each ticker in the tickers list:

| Path | Content |
|---|---|
| `data/equity/usa/<resolution>/<TICKER>.zip` | One CSV per zip: `DateTime,Open,High,Low,Close,Volume` in deci-cents. |
| `data/equity/usa/factor_files/<TICKER>.csv` | `YYYYMMDD,priceFactor,splitFactor,referencePrice` (no header, sentinel `20501231,1,1,0` at the end). |

Prices are derived from `yfinance`'s **raw** (unadjusted) series; the
factor file encodes the dividend/split adjustment so LEAN produces
adjusted prices that match `yfinance`'s `auto_adjust=True` series.

## Default tickers

`data/tickers.default.txt` lists the tickers downloaded by the script. Default
contents: `SPY`. The script auto-translates between yfinance-style
(`BRK-B`) and LEAN-style (`BRK.B`) symbols unless `--no-rename-tickers`
is passed.

## Resolutions

| Flag | Notes |
|---|---|
| `daily` (default) | Full yfinance history. Recommended. |
| `hour` | yfinance caps the `1h` interval at ~730 days. The script warns when `--start` is further back. |
| `minute` | yfinance caps at 30-60 days; useless for most backtests. The script refuses unless `--force` is passed. |

## Overriding defaults

```bash
START_DATE=2015-01-01 RESOLUTION=daily python tools/download_data.py
TICKERS_FILE=data/my_tickers.txt python tools/download_data.py
```

`data/my_tickers.txt` example:

```
SPY
QQQ
AAPL
BRK.B
```

## Free vs paid

`yfinance` is free and works without a QuantConnect account. The script
deliberately avoids `lean data download`, which would require a paid
subscription for the underlying dataset.

## Disk size

Approximate (daily resolution, 2010-01-01 → today, including the factor
file):

- SPY: ~3 MB (vs 1-2 GB for minute resolution from `lean data download`)

## Pre-requisite

Before the first run, the data folder needs `market-hours` and
`symbol-properties`. These are created by `lean init` (no login
required). The script detects missing files and prints a clear error
instructing you to run it.
