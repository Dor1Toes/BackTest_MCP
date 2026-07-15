from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd

from quantforge_mcp.quantforge_stock.data.loader import DataLoader
from quantforge_mcp.quantforge_stock.data.synthetic import generate_ohlcv

from quantforge_mcp.db.repositories import OhlcvRepository


class DataService:
    def __init__(self, ohlcv_repo: OhlcvRepository, *, allow_synthetic_fallback: bool = True) -> None:
        self._repo = ohlcv_repo
        self._loader = DataLoader(cache_dir=None)
        self._allow_synthetic_fallback = allow_synthetic_fallback

    @staticmethod
    def default_dates(start: str, end: str) -> tuple[str, str]:
        end_d = end or date.today().isoformat()
        start_d = start or (date.fromisoformat(end_d) - timedelta(days=365)).isoformat()
        return start_d, end_d

    def _fetch_remote(self, symbol: str, start: str, end: str, interval: str) -> tuple[pd.DataFrame, str]:
        try:
            frame = self._loader.yfinance(symbol, start, end, interval=interval)
            if frame is not None and not frame.empty:
                return frame, "yfinance"
        except Exception:
            pass
        if not self._allow_synthetic_fallback:
            raise RuntimeError("fetch market data failed and synthetic fallback disabled")
        expected = len(pd.bdate_range(start=start, end=end))
        days = max(60, expected)
        seed = abs(hash(symbol)) % (2**31)
        frame = generate_ohlcv(n=min(days, 756), seed=seed)
        if expected > 0:
            frame = frame.tail(expected).copy()
            idx = pd.bdate_range(start=start, end=end)
            if len(idx) == len(frame):
                frame.index = idx
        return frame, "synthetic"

    def get_ohlcv(self, symbol: str, start: str, end: str, interval: str = "1d") -> tuple[pd.DataFrame, str]:
        start_d, end_d = self.default_dates(start, end)
        cached = self._repo.fetch_range(symbol, start_d, end_d, interval)

        needs_refetch = cached.empty
        if not cached.empty:
            first = cached.index.min().strftime("%Y-%m-%d")
            last = cached.index.max().strftime("%Y-%m-%d")
            needs_refetch = first > start_d or last < end_d

        source = "cache"
        if needs_refetch:
            fetched, source = self._fetch_remote(symbol, start_d, end_d, interval)
            rows = self._repo.upsert_rows(symbol, fetched, interval=interval, source=source)
            self._repo.insert_fetch_log(
                symbol=symbol,
                start=start_d,
                end=end_d,
                interval=interval,
                rows_added=rows,
                source=source,
            )
            cached = self._repo.fetch_range(symbol, start_d, end_d, interval)

        return cached, source

    def get_coverage(self, symbol: str, start: str, end: str, interval: str = "1d") -> dict[str, Any]:
        start_d, end_d = self.default_dates(start, end)
        frame = self._repo.fetch_range(symbol, start_d, end_d, interval)
        expected_days = len(pd.bdate_range(start=start_d, end=end_d))
        rows = len(frame)
        missing_pct = 0.0 if expected_days == 0 else round(max(0.0, 1.0 - rows / expected_days) * 100, 2)
        return {
            "symbol": symbol,
            "start": start_d,
            "end": end_d,
            "rows": rows,
            "expected_days": expected_days,
            "missing_pct": missing_pct,
        }

    def list_symbols(self) -> list[dict[str, Any]]:
        return self._repo.list_symbols()
