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
    
    


    
