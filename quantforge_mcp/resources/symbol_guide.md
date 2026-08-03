# Symbol guide

## Symbol formats

- **A-share examples**: `600519`, `000001`, `sh600519`, `sz000001`, `600519.SH`
- **US examples**: `NVDA`, `AAPL`, `MSFT`, `TSLA`
- **Best compatibility**: prefer **6-digit numeric** A-share codes (e.g. `600519`, `000001`).

## Data source routing

- When `QUANTFORGE_DATA_SOURCE=auto`:
  - **A-share** → `akshare`
  - **Non A-share (e.g. US stocks)** → `yfinance`
- You can also set it explicitly: `QUANTFORGE_DATA_SOURCE=akshare` or `QUANTFORGE_DATA_SOURCE=yfinance`.
- A-share adjustment: `QUANTFORGE_AKSHARE_ADJUST` (default: `qfq`).

## Dates and interval

- Use **`YYYY-MM-DD`** for `start` / `end` (e.g. `2024-01-01`).
- If `start` or `end` is empty, the server will use a default window (typically “end date minus 365 days” to “end date / today”).
- `interval` default is `1d` (consistent with `get_stock_data`).

## Cache and prefetch tips

1. Call `list_cached_symbols()` to check local cache status.
2. For multi-symbol backtests, call `get_stock_data(symbols, start, end, preview=False)` first to warm the cache before running.
3. To inspect a symbol's shape, use `get_stock_data(["SYMBOL"], preview=True)`.

## Fallback (synthetic data)

If remote fetching fails and `QUANTFORGE_ALLOW_SYNTHETIC_FALLBACK=true`, the system may fall back to synthetic OHLCV (useful for demos/debugging).
