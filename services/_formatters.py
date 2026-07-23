from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pandas as pd

from schemas.data import OHLCVSummary, StockDataSummary
from schemas.indicator import IndicatorPoint, IndicatorResultSummary


def _fmt_date(ts: Any) -> str:
    if isinstance(ts, (pd.Timestamp, datetime)):
        return ts.strftime("%Y-%m-%d")
    if isinstance(ts, date):
        return ts.isoformat()
    return str(ts)


def summarize_ohlcv(df: pd.DataFrame, symbol: str, start: str, end: str, preview: int = 3) -> StockDataSummary:
    if df.empty:
        return StockDataSummary(symbol=symbol, start=start, end=end, rows=0)
    work = df.copy()
    work.columns = [str(c).lower() for c in work.columns]
    missing_pct = float(work.isna().mean().mean() * 100)

    def _rows(sub: pd.DataFrame) -> list[OHLCVSummary]:
        return [
            OHLCVSummary(
                date=_fmt_date(ts),
                open=float(row.get("open", row["close"])),
                high=float(row.get("high", row["close"])),
                low=float(row.get("low", row["close"])),
                close=float(row["close"]),
                volume=float(row.get("volume", 0.0)),
            )
            for ts, row in sub.iterrows()
        ]

    close = work["close"].dropna()
    stats = {
        "close_min": float(close.min()) if len(close) else 0.0,
        "close_max": float(close.max()) if len(close) else 0.0,
        "close_last": float(close.iloc[-1]) if len(close) else 0.0,
        "avg_volume": float(work["volume"].mean()) if "volume" in work else 0.0,
    }
    return StockDataSummary(
        symbol=symbol,
        start=start,
        end=end,
        rows=len(work),
        missing_pct=round(missing_pct, 2),
        date_range=(_fmt_date(work.index[0]), _fmt_date(work.index[-1])),
        head=_rows(work.head(preview)),
        tail=_rows(work.tail(preview)),
        stats=stats,
    )


def summarize_indicator(df: pd.DataFrame | pd.Series, symbol: str, indicator: str, params: dict, max_points: int = 120) -> IndicatorResultSummary:
    if isinstance(df, pd.Series):
        series = df.dropna()
        sample = series.tail(max_points)
        return IndicatorResultSummary(
            symbol=symbol,
            indicator=indicator,
            params=params,
            last_value=float(series.iloc[-1]) if len(series) else None,
            min_value=float(series.min()) if len(series) else None,
            max_value=float(series.max()) if len(series) else None,
            mean_value=float(series.mean()) if len(series) else None,
            sample=[IndicatorPoint(date=_fmt_date(ts), value=float(v)) for ts, v in sample.items()],
            columns=[indicator],
        )

    work = df.dropna(how="all").tail(max_points)
    col = work.columns[0]
    series = work[col]
    return IndicatorResultSummary(
        symbol=symbol,
        indicator=indicator,
        params=params,
        last_value=float(work.iloc[-1][col]) if len(work) else None,
        min_value=float(series.min()) if len(series) else None,
        max_value=float(series.max()) if len(series) else None,
        mean_value=float(series.mean()) if len(series) else None,
        sample=[IndicatorPoint(date=_fmt_date(ts), value=float(row[col])) for ts, row in work.iterrows()],
        columns=[str(c) for c in work.columns],
    )


def sample_equity_curve(equity: pd.Series, max_points: int = 60) -> list[dict[str, float]]:
    if equity.empty:
        return []
    sampled = equity if len(equity) <= max_points else equity.iloc[:: max(1, len(equity) // max_points)]
    return [{"date": _fmt_date(ts), "equity": float(v)} for ts, v in sampled.items()]


def sample_trades(trades: pd.DataFrame, max_rows: int = 5) -> list[dict[str, Any]]:
    if trades.empty:
        return []
    out: list[dict[str, Any]] = []
    for _, row in trades.head(max_rows).iterrows():
        item = {k: (_fmt_date(v) if k == "timestamp" and not isinstance(v, str) else v) for k, v in row.items()}
        out.append(item)
    return out
