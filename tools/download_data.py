#!/usr/bin/env python3
"""Download US equity data via yfinance and emit LEAN-format data + factor files.

Designed for users on the free QuantConnect plan who still want to run
``lean backtest`` locally. Replaces the old ``tools/download_data.sh`` which
called ``lean data download`` (paid) and then exited.

For each ticker in the tickers file, the script:

  1. Downloads raw OHLCV from yfinance (``auto_adjust=False``).
  2. Downloads the ticker's dividend and split history.
  3. Writes ``data/equity/usa/<resolution>/<TICKER>.zip`` containing
     ``<TICKER>.csv`` (deci-cents, one row per bar).
  4. Writes ``data/equity/usa/factor_files/<TICKER>.csv`` in LEAN's factor
     file format: ``YYYYMMDD,priceFactor,splitFactor,referencePrice``,
     ending with the sentinel ``20501231,1,1,0``.
  5. Sanity-checks the output by comparing ``raw * factor`` against
     yfinance's adjusted close at three sample dates.   

Ticker symbol translation: yfinance uses ``-`` for share classes
(``BRK-B``); LEAN uses ``.`` (``BRK.B``). The script auto-translates
unless ``--no-rename-tickers`` is passed.

Resolution caveats:

  - ``daily``  : full yfinance history. Default.
  - ``hour``   : yfinance caps the ``1h`` interval at ~730 days.
  - ``minute`` : yfinance caps at 30-60 days. Refused unless ``--force``.

Pre-requisite: run ``lean init`` once in the repo root to bootstrap
``data/market-hours/`` and ``data/symbol-properties/``. The script
prints a clear error and exits if those are missing.

Usage:

    python tools/download_data.py
    python tools/download_data.py --start 2015-01-01 --end 2024-12-31
    python tools/download_data.py --resolution hour --tickers-file data/my.txt
    python tools/download_data.py --resolution minute --force
"""

from __future__ import annotations

import argparse
import os
import sys
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import cast


def _require_deps() -> None:
    missing: list[str] = []
    try:
        import pandas  # noqa: F401
    except ImportError:
        missing.append('pandas')
    try:
        import yfinance  # noqa: F401
    except ImportError:
        missing.append('yfinance')
    if missing:
        print(
            'ERROR: missing required packages: ' + ', '.join(missing) + '\n'
            'Install them with:\n'
            '  pip install -r requirements-dev.txt',
            file=sys.stderr,
        )
        sys.exit(2)


_require_deps()
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / 'data'
EQUITY_DIR = DATA_DIR / 'equity' / 'usa'
FACTOR_DIR = EQUITY_DIR / 'factor_files'
LEAN_TZ = 'America/New_York'
DECI_CENTS = 10000
SENTINEL_DATE = '20501231'

HOUR_MAX_DAYS = 730


def lean_ticker(s: str, *, to_yfinance: bool) -> str:
    """Translate between yfinance (``BRK-B``) and LEAN (``BRK.B``) tickers."""
    if to_yfinance:
        return s.replace('.', '-')
    return s.replace('-', '.')


def parse_date(s: str) -> date:
    return datetime.strptime(s, '%Y-%m-%d').date()


def read_tickers(path: Path) -> list[str]:
    out: list[str] = []
    for line in path.read_text().splitlines():
        s = line.strip()
        if not s or s.startswith('#'):
            continue
        out.append(s)
    return out


def require_lean_workspace() -> None:
    """Make sure the user has run ``lean init`` (or otherwise set up
    ``data/market-hours`` and ``data/symbol-properties``)."""
    missing: list[str] = []
    if not (DATA_DIR / 'market-hours' / 'market-hours-database.json').exists():
        missing.append('data/market-hours/market-hours-database.json')
    if not (DATA_DIR / 'symbol-properties' / 'symbol-properties-database.csv').exists():
        missing.append('data/symbol-properties/symbol-properties-database.csv')
    if missing:
        print(
            'ERROR: missing LEAN data folder infrastructure:\n'
            + '\n'.join(f'  - {m}' for m in missing)
            + '\n\nRun `lean init` once in the repo root to bootstrap the\n'
            'standard data folder (works without login), then re-run this script.',
            file=sys.stderr,
        )
        sys.exit(2)


def fetch_ohlcv(yf_symbol: str, start: date, end: date, interval: str) -> pd.DataFrame:
    import yfinance as yf
    end_excl = end + timedelta(days=1)
    df = yf.Ticker(yf_symbol).history(
        start=start.isoformat(),
        end=end_excl.isoformat(),
        interval=interval,
        auto_adjust=False,
        actions=False,
    )
    if df.empty:
        raise RuntimeError(f'yfinance returned no data for {yf_symbol}')
    if pd.DatetimeIndex(df.index).tz is not None:
        df = df.tz_convert(LEAN_TZ).tz_localize(None)
    return df


def fetch_dividends(yf_symbol: str) -> pd.Series:
    import yfinance as yf
    divs = yf.Ticker(yf_symbol).dividends
    if divs is None or len(divs) == 0:
        return pd.Series(dtype=float)
    if pd.DatetimeIndex(divs.index).tz is not None:
        divs = divs.tz_convert(LEAN_TZ).tz_localize(None)
    return divs


def fetch_splits(yf_symbol: str) -> pd.Series:
    import yfinance as yf
    splits = yf.Ticker(yf_symbol).splits
    if splits is None or len(splits) == 0:
        return pd.Series(dtype=float)
    if pd.DatetimeIndex(splits.index).tz is not None:
        splits = splits.tz_convert(LEAN_TZ).tz_localize(None)
    return splits


def fetch_adjusted_close(yf_symbol: str, start: date, end: date, interval: str) -> pd.Series:
    import yfinance as yf
    end_excl = end + timedelta(days=1)
    df = yf.Ticker(yf_symbol).history(
        start=start.isoformat(),
        end=end_excl.isoformat(),
        interval=interval,
        auto_adjust=True,
        actions=False,
    )
    if df.empty:
        return pd.Series(dtype=float)
    if pd.DatetimeIndex(df.index).tz is not None:
        df = df.tz_convert(LEAN_TZ).tz_localize(None)
    return df['Close']


def _to_deci_cents(x: float) -> int:
    return int(round(x * DECI_CENTS))


def write_lean_daily_or_hour(
    zip_path: Path,
    csv_name: str,
    df: pd.DataFrame,
    resolution: str,
) -> int:
    """Write daily/hour bars to a single zip with a CSV inside. Returns bar count."""
    df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])
    df = df[df['Volume'] > 0]
    if df.empty:
        return 0

    lines: list[str] = []
    for ts, row in df.iterrows():
        d: date = ts.date() if isinstance(ts, pd.Timestamp) else cast(date, ts)
        yyyymmdd = d.strftime('%Y%m%d')
        time_str = '00:00' if resolution == 'daily' else cast(pd.Timestamp, ts).strftime('%H:%M')
        lines.append(
            f'{yyyymmdd} {time_str},'
            f'{_to_deci_cents(row["Open"])},'
            f'{_to_deci_cents(row["High"])},'
            f'{_to_deci_cents(row["Low"])},'
            f'{_to_deci_cents(row["Close"])},'
            f'{int(row["Volume"])}'
        )

    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(csv_name, '\n'.join(lines) + '\n')
    return len(lines)


def write_lean_minute(
    out_dir: Path,
    ticker: str,
    df: pd.DataFrame,
) -> tuple[int, int]:
    """Write minute bars to per-day zips. Returns (days_written, bars_written)."""
    df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])
    df = df[df['Volume'] > 0]
    if df.empty:
        return 0, 0

    days = sorted({cast(pd.Timestamp, ts).date() for ts in df.index})
    days_written = 0
    bars_written = 0
    for d in days:
        mask = [cast(pd.Timestamp, ts).date() == d for ts in df.index]
        day_bars = df[mask]
        if day_bars.empty:
            continue
        yyyymmdd = d.strftime('%Y%m%d')
        day_dir = out_dir / ticker
        day_dir.mkdir(parents=True, exist_ok=True)
        zip_path = day_dir / f'{yyyymmdd}_trade.zip'
        csv_name = f'{yyyymmdd}_{ticker}_minute_trade.csv'
        lines: list[str] = []
        for ts, row in day_bars.iterrows():
            ts = cast(pd.Timestamp, ts)
            midnight = ts.replace(hour=0, minute=0, second=0, microsecond=0)
            ms = int((ts - midnight).total_seconds() * 1000)
            lines.append(
                f'{ms},'
                f'{_to_deci_cents(row["Open"])},'
                f'{_to_deci_cents(row["High"])},'
                f'{_to_deci_cents(row["Low"])},'
                f'{_to_deci_cents(row["Close"])},'
                f'{int(row["Volume"])}'
            )
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(csv_name, '\n'.join(lines) + '\n')
        days_written += 1
        bars_written += len(lines)
    return days_written, bars_written


@dataclass
class FactorRow:
    date: date
    price_factor: float
    split_factor: float
    reference_price: float


def build_factor_rows(
    start: date,
    dividends: pd.Series,
    splits: pd.Series,
    raw_closes: pd.Series,
    initial_price_factor: float | None = None,
) -> list[FactorRow]:
    """Build the in-range factor file rows for a ticker.

    `dividends` and `splits` are yfinance Series indexed by ex-date (NY).
    `raw_closes` is a Series of raw (unadjusted) closes indexed by date.
    The returned list starts with an entry for `start` and contains one
    entry per in-range event.

    `initial_price_factor` (optional): if provided, used as the factor
    at the start of the data range instead of computing it from
    pre-`start` events. Useful for hourly/minute resolutions where
    yfinance limits the OHLCV history.
    """
    def _to_date(d: object) -> date:
        return d.date() if isinstance(d, pd.Timestamp) else cast(date, d)

    div_dict: dict[date, float] = {_to_date(d): float(a) for d, a in dividends.items()}
    spl_dict: dict[date, float] = {_to_date(d): float(a) for d, a in splits.items()}

    all_event_dates = sorted(set(div_dict) | set(spl_dict))
    raw_closes_index = list(raw_closes.index)

    def _close_on(d: date) -> float:
        """Raw close on date `d`, or the nearest prior close if missing.

        Handles multi-row dates (e.g. hourly bars) by taking the first match.
        """
        matches = raw_closes[raw_closes.index == d]
        if not matches.empty:
            return float(matches.iloc[0])
        prior = [x for x in raw_closes_index if x < d]
        return float(raw_closes.loc[prior[-1]]) if prior else float('nan')

    pf = 1.0
    sf = 1.0
    all_rows: list[FactorRow] = []
    for ed in all_event_dates:
        r = _close_on(ed)

        if ed in div_dict:
            d_amt = div_dict[ed]
            if r == r and d_amt > 0:  # r == r is NaN check
                pf *= (r + d_amt) / r
        if ed in spl_dict:
            sf *= spl_dict[ed]

        all_rows.append(FactorRow(
            date=ed, price_factor=pf, split_factor=sf, reference_price=r,
        ))

    if initial_price_factor is not None:
        # Caller supplied the factor at the start of the data range.
        initial_pf = initial_price_factor
    else:
        # Factor at start = cumulative effect of pre-start events.
        initial_pf = 1.0
        for r in all_rows:
            if r.date < start:
                initial_pf = r.price_factor
            else:
                break
    initial_sf = 1.0

    in_range = [r for r in all_rows if r.date >= start]

    if in_range:
        final_pf = in_range[-1].price_factor
        final_sf = in_range[-1].split_factor
    else:
        final_pf = initial_pf
        final_sf = initial_sf

    pf_scale = 1.0 / final_pf if final_pf else 1.0
    sf_scale = 1.0 / final_sf if final_sf else 1.0
    out: list[FactorRow] = [
        FactorRow(
            date=start,
            price_factor=initial_pf * pf_scale,
            split_factor=initial_sf * sf_scale,
            reference_price=0.0,
        ),
    ]
    for r in in_range:
        out.append(FactorRow(
            date=r.date,
            price_factor=r.price_factor * pf_scale,
            split_factor=r.split_factor * sf_scale,
            reference_price=r.reference_price,
        ))
    return out


def write_factor_file(lean_symbol: str, rows: list[FactorRow]) -> Path:
    FACTOR_DIR.mkdir(parents=True, exist_ok=True)
    path = FACTOR_DIR / f'{lean_symbol}.csv'
    lines = [
        f'{r.date.strftime("%Y%m%d")},{r.price_factor:.7f},{r.split_factor:.7g},{r.reference_price:.4f}'
        for r in rows
    ]
    lines.append(f'{SENTINEL_DATE},1,1,0')
    path.write_text('\n'.join(lines) + '\n')
    return path


def validate_factor(
    raw_close: pd.Series,
    adj_close: pd.Series,
    rows: list[FactorRow],
) -> list[str]:
    """Spot-check that ``raw * priceFactor / splitFactor`` matches yfinance's adjusted close.

    yfinance's ``ticker.dividends`` and its ``auto_adjust=True`` series are
    not always in agreement (e.g. SPY 2024 dividends: yfinance reports
    $1.595 but the public amount is $1.913, leading to ~0.7% cumulative
    factor drift). We treat anything within 1% as a pass and flag larger
    gaps as likely script bugs.
    """
    notes: list[str] = []
    if not rows or raw_close.empty:
        return notes

    def factor_on(d: date) -> tuple[float, float]:
        pf = rows[0].price_factor
        sf = rows[0].split_factor
        for r in rows:
            if r.date <= d:
                pf = r.price_factor
                sf = r.split_factor
            else:
                break
        return pf, sf

    sample_idx: list[date] = []
    idx = list(raw_close.index)
    if idx:
        sample_idx.append(idx[0])
        sample_idx.append(idx[len(idx) // 2])
        sample_idx.append(idx[-1])
    for d in sample_idx:
        if d not in adj_close.index:
            continue
        pf, sf = factor_on(d)
        raw_matches = raw_close[raw_close.index == d]
        r = float(raw_matches.iloc[0]) if not raw_matches.empty else float('nan')
        adj_matches = adj_close[adj_close.index == d]
        a = float(adj_matches.iloc[0]) if not adj_matches.empty else float('nan')
        if r != r or a != a or r == 0 or a == 0:  # NaN checks
            continue
        expected = r * pf / sf if sf else r * pf
        err = abs(expected - a) / a
        if err > 0.01:  # 1% tolerance; yfinance data is the bottleneck
            notes.append(
                f'  ! factor mismatch on {d}: raw={r:.4f} pf={pf:.6f} sf={sf:g} -> '
                f'{expected:.4f}, adj={a:.4f} (err={err:.2%})'
            )
    return notes


def process_ticker(
    lean_symbol: str,
    start: date,
    end: date,
    resolution: str,
) -> str:
    yf_symbol = lean_ticker(lean_symbol, to_yfinance=True)
    interval = {'daily': '1d', 'hour': '1h', 'minute': '1m'}[resolution]

    divs = fetch_dividends(yf_symbol)
    splits = fetch_splits(yf_symbol)

    # For the factor file we need raw closes on every event date. yfinance
    # caps hourly and minute data at ~730 / 30-60 days, so for those
    # resolutions we can only honor events within the yfinance window.
    # Daily data is unlimited, so we pull the full event range.
    def _to_date(d: object) -> date:
        return d.date() if isinstance(d, pd.Timestamp) else cast(date, d)
    if resolution == 'daily':
        ohlcv_start = start
        for s in list(divs.items()) + list(splits.items()):
            ed = _to_date(s[0])
            if ed < ohlcv_start:
                ohlcv_start = ed
    else:
        ohlcv_start = max(start, end - timedelta(days=HOUR_MAX_DAYS))
    raw_df = fetch_ohlcv(yf_symbol, ohlcv_start, end, interval)
    if raw_df.empty:
        raise RuntimeError(f'yfinance returned no data for {yf_symbol}')

    raw_close_full = raw_df['Close'].copy()
    raw_close_full.index = [cast(pd.Timestamp, ts).date() for ts in raw_close_full.index]

    # Slice the user's data range for the data file.
    idx = pd.DatetimeIndex(raw_df.index)
    data_df = raw_df[(idx.date >= start) & (idx.date <= end)] if not raw_df.empty else raw_df

    adj_close = fetch_adjusted_close(yf_symbol, start, end, interval)
    adj_close.index = [ts.date() if isinstance(ts, pd.Timestamp) else ts for ts in adj_close.index]

    res_dir = EQUITY_DIR / resolution
    if resolution in ('daily', 'hour'):
        zip_path = res_dir / f'{lean_symbol}.zip'
        n_bars = write_lean_daily_or_hour(zip_path, f'{lean_symbol}.csv', data_df, resolution)
        data_rel = zip_path.relative_to(ROOT)
        bar_label = 'bar'
    else:
        days, n_bars = write_lean_minute(res_dir, lean_symbol, data_df)
        data_rel = (res_dir / lean_symbol).relative_to(ROOT)
        bar_label = f'bar across {days} day(s)'

    rows = build_factor_rows(start, divs, splits, raw_close_full)
    factor_path = write_factor_file(lean_symbol, rows)

    # Validate using the in-range raw close.
    raw_close = raw_close_full[(raw_close_full.index >= start) & (raw_close_full.index <= end)]
    notes = validate_factor(raw_close, adj_close, rows)

    msg = f'{n_bars} {bar_label}(s) -> {data_rel}; factor file: {factor_path.relative_to(ROOT)}'
    if notes:
        msg += '\n' + '\n'.join(notes)
    return msg


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument('--start', default=os.environ.get('START_DATE', '2010-01-01'),
                    help='Start date YYYY-MM-DD (default: 2010-01-01)')
    ap.add_argument('--end', default=os.environ.get('END_DATE', date.today().isoformat()),
                    help='End date YYYY-MM-DD (default: today)')
    ap.add_argument('--resolution', default=os.environ.get('RESOLUTION', 'daily'),
                    choices=['daily', 'hour', 'minute'],
                    help='Bar resolution (default: daily)')
    ap.add_argument('--tickers-file', type=Path,
                    default=Path(os.environ.get('TICKERS_FILE', 'data/tickers.default.txt')),
                    help='Path to tickers file (default: data/tickers.default.txt)')
    ap.add_argument('--market', default=os.environ.get('DATASET', 'usa'),
                    help='Market folder name under data/equity/ (default: usa)')
    ap.add_argument('--force', action='store_true',
                    help='Allow minute resolution despite yfinance 30-60 day cap, '
                         'and silence hour-resolution span warnings')
    ap.add_argument('--no-rename-tickers', action='store_true',
                    help='Pass tickers through to yfinance verbatim '
                         '(no BRK.B <-> BRK-B translation; you must use yfinance-style symbols)')
    args = ap.parse_args()

    try:
        start = parse_date(args.start)
    except ValueError:
        print(f'ERROR: bad --start date: {args.start}', file=sys.stderr)
        return 2
    try:
        end = parse_date(args.end)
    except ValueError:
        print(f'ERROR: bad --end date: {args.end}', file=sys.stderr)
        return 2
    if end < start:
        print(f'ERROR: --end ({args.end}) is before --start ({args.start})', file=sys.stderr)
        return 2

    if args.resolution == 'minute' and not args.force:
        print(
            'ERROR: minute resolution is not practical with yfinance\n'
            '(1m interval caps at 7 days, 5m/15m/30m/60m cap at 60 days).\n'
            'Use --force to download the partial data anyway.',
            file=sys.stderr,
        )
        return 2
    if args.resolution == 'hour' and not args.force:
        span = (end - start).days
        if span > HOUR_MAX_DAYS:
            print(
                f'WARNING: hour resolution with --start {args.start} ({span} days) '
                f'exceeds yfinance 1h cap of {HOUR_MAX_DAYS} days.\n'
                'yfinance will return only the last ~2 years. Pass --force to silence this.',
                file=sys.stderr,
            )

    if not args.tickers_file.exists():
        print(f'ERROR: tickers file not found: {args.tickers_file}', file=sys.stderr)
        return 1
    tickers = read_tickers(args.tickers_file)
    if not tickers:
        print(f'ERROR: no tickers in {args.tickers_file}', file=sys.stderr)
        return 1

    require_lean_workspace()

    print(f'Market:     {args.market}')
    print(f'Resolution: {args.resolution}')
    print(f'Range:      {start} -> {end}')
    print(f'Tickers:    {args.tickers_file} ({len(tickers)} ticker(s))')
    print(f'Output:     {EQUITY_DIR.relative_to(ROOT)}')
    print()

    ok = 0
    fail = 0
    for t in tickers:
        lean_sym = t
        yf_sym = lean_ticker(lean_sym, to_yfinance=True) if not args.no_rename_tickers else lean_sym
        print(f'-> {lean_sym}  (yfinance: {yf_sym})')
        try:
            msg = process_ticker(lean_sym, start, end, args.resolution)
        except Exception as e:  # noqa: BLE001
            print(f'  ! failed: {e}', file=sys.stderr)
            fail += 1
            continue
        print(f'  {msg}')
        ok += 1

    print()
    print(f'Done. {ok} succeeded, {fail} failed.')
    return 0 if fail == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
