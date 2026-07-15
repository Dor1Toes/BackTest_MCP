from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd


class OhlcvRepository:
    def __init__(self, conn_factory) -> None:
        self._conn_factory = conn_factory

    def fetch_range(self, symbol: str, start: str, end: str, interval: str = "1d") -> pd.DataFrame:
        sql = """
        SELECT date, open, high, low, close, volume, source
        FROM ohlcv
        WHERE symbol = ? AND interval = ? AND date BETWEEN ? AND ?
        ORDER BY date
        """
        with self._conn_factory() as conn:
            rows = conn.execute(sql, (symbol, interval, start, end)).fetchall()
        if not rows:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume", "source"])
        frame = pd.DataFrame([dict(r) for r in rows])
        frame["date"] = pd.to_datetime(frame["date"])
        frame = frame.set_index("date").sort_index()
        return frame

    def upsert_rows(self, symbol: str, frame: pd.DataFrame, interval: str = "1d", source: str = "yfinance") -> int:
        if frame is None or frame.empty:
            return 0
        work = frame.copy()
        work.columns = [str(c).lower() for c in work.columns]
        needed = ["open", "high", "low", "close", "volume"]
        for col in needed:
            if col not in work.columns:
                if col == "volume":
                    work[col] = 0.0
                else:
                    work[col] = work["close"]
        now = datetime.utcnow().isoformat()
        payload: list[tuple[Any, ...]] = []
        for ts, row in work.iterrows():
            payload.append(
                (
                    symbol,
                    pd.Timestamp(ts).strftime("%Y-%m-%d"),
                    interval,
                    float(row["open"]),
                    float(row["high"]),
                    float(row["low"]),
                    float(row["close"]),
                    float(row.get("volume", 0.0)),
                    source,
                    now,
                )
            )
        sql = """
        INSERT INTO ohlcv(symbol, date, interval, open, high, low, close, volume, source, updated_at)
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(symbol, date, interval) DO UPDATE SET
            open=excluded.open,
            high=excluded.high,
            low=excluded.low,
            close=excluded.close,
            volume=excluded.volume,
            source=excluded.source,
            updated_at=excluded.updated_at
        """
        with self._conn_factory() as conn:
            conn.executemany(sql, payload)
            conn.commit()
        return len(payload)

    def insert_fetch_log(
        self,
        *,
        symbol: str,
        start: str,
        end: str,
        interval: str,
        rows_added: int,
        source: str,
    ) -> None:
        sql = """
        INSERT INTO data_fetch_log(symbol, start_date, end_date, interval, rows_added, source, fetched_at)
        VALUES(?, ?, ?, ?, ?, ?, ?)
        """
        with self._conn_factory() as conn:
            conn.execute(
                sql,
                (symbol, start, end, interval, rows_added, source, datetime.utcnow().isoformat()),
            )
            conn.commit()

    def list_symbols(self) -> list[dict[str, Any]]:
        sql = """
        SELECT symbol, MIN(date) AS start_date, MAX(date) AS end_date, COUNT(*) AS rows
        FROM ohlcv
        GROUP BY symbol
        ORDER BY symbol
        """
        with self._conn_factory() as conn:
            rows = conn.execute(sql).fetchall()
        return [dict(r) for r in rows]
