"""Data loaders. yfinance is optional; falls back gracefully without network."""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from collections.abc import Iterable

import pandas as pd


def load_csv(path: str| os.PathLike, parse_dates: str = "date") -> pd.DataFrame:
    df = pd.read_csv(path)
    if parse_dates in df.columns:
        df[parse_dates] = pd.to_datetime(df[parse_dates])
        df = df.set_index(parse_dates)
    df.columns = [col.lower() for col in df.columns]
    return df.sort_index()


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize rows into open/high/low/close/volume + DatetimeIndex."""
    work = df.copy()
    work.columns = [str(col).lower() for col in work.columns]
    rename_map = {
        "date": "date",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "volume": "volume",
        "日期": "date",
        "开盘": "open",
        "最高": "high",
        "最低": "low",
        "收盘": "close",
        "成交量": "volume",
    }
    work = work.rename(columns=rename_map)
    if "date" in work.columns:
        work["date"] = pd.to_datetime(work["date"])
        work = work.set_index("date")
    work = work.sort_index()
    for col in ("open", "high", "low", "close", "volume"):
        if col not in work.columns:
            work[col] = work.get("close", pd.Series(index=work.index, dtype="float64"))
    return work[["open", "high", "low", "close", "volume"]]


def _parse_a_share_symbol(symbol: str) -> str:
    """Parse 600519 / sh600519 / 600519.SH into 600519."""
    raw = symbol.strip().upper()
    if raw.startswith(("SH", "SZ")):
        raw = raw[2:]
    if "." in raw:
        raw = raw.split(".")[0]
    return raw


def _to_sina_symbol(code: str) -> str:
    """Map 6-digit A-share code to Sina prefix form used by stock_zh_a_daily."""
    if code.startswith(("6", "9")):
        return f"sh{code}"
    return f"sz{code}"


@dataclass
class DataLoader:
    cache_dir: str | None = None

    def __post_init__(self) -> None:
        if self.cache_dir:
            Path(self.cache_dir).mkdir(parents=True, exist_ok = True)
    
    def _cache_path(self, symbol: str, start: str, end: str, interval: str) -> Path | None:
        if not self.cache_dir:
            return None
        filename = f"{symbol}_{start}_{end}_{interval}.parquet"
        return Path(self.cache_dir)/filename
    
    def yfinance(self, symbol: str, start: str, end: str, interval: str = "1d") -> pd.DataFrame:
        cache_path = self._cache_path(symbol,start,end,interval)
        if cache_path and cache_path.exists():
            return pd.read_parquet(cache_path)
        try:
            import yfinance as yf
        except ImportError as e:
            raise ImportError("yfinance not installed; use synthetic data or csv") from e
        df = yf.download(symbol, start=start, end=end, interval=interval, auto_adjust=True, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0].lower() for col in df.columns]
        else:
            df.columns = [col.lower() for col in df.columns]
        if cache_path is not None and not df.empty:
            df.to_parquet(cache_path)
        return df
    
    def yfinance_many(self,symbols: Iterable[str], start: str, end: str, interval: str = "1d") -> dict:
        return {symbol: self.yfinance(symbol, start, end , interval) for symbol in symbols}

    def akshare(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str = "1d",
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        cache_path = self._cache_path(symbol, start, end, interval)
        if cache_path and cache_path.exists():
            return pd.read_parquet(cache_path)
        try:
            import akshare as ak
        except ImportError as e:
            raise ImportError("akshare not installed") from e

        if interval != "1d":
            raise ValueError("akshare loader supports daily (1d) bars only")

        code = _parse_a_share_symbol(symbol)
        if not (code.isdigit() and len(code) == 6):
            raise ValueError(f"invalid A-share symbol: {symbol}")

        frame = ak.stock_zh_a_daily(
            symbol=_to_sina_symbol(code),
            start_date=start,
            end_date=end,
            adjust=adjust,
        )
        frame = _normalize_ohlcv(frame)
        if frame.empty:
            raise RuntimeError(f"akshare returned empty daily data for {symbol}")

        if cache_path is not None and not frame.empty:
            frame.to_parquet(cache_path)
        return frame
