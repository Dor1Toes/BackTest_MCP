from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from quantforge_stock.backtest.engine import _OHLCV_COLS, _SymbolBuffer
from quantforge_stock.core.event import SignalEvent
from quantforge_stock.strategies.base import Strategy


def _should_rebalance(rebalance: str, ts: pd.Timestamp, prev_ts: pd.Timestamp) -> bool:
    if rebalance == "weekly":
        return ts.isocalendar().week != prev_ts.isocalendar().week
    if rebalance == "monthly":
        return (ts.year, ts.month) != (prev_ts.year, prev_ts.month)
    return True


def _should_evaluate_latest_bar(
    rebalance: str,
    latest_ts: pd.Timestamp,
    last_rebalance_ts: str | None,
) -> bool:
    if rebalance == "bar":
        return True
    if not last_rebalance_ts:
        return True
    prev_ts = pd.Timestamp(last_rebalance_ts)
    return _should_rebalance(rebalance, latest_ts, prev_ts)


@dataclass
class ScanOutput:
    signals: list[SignalEvent]
    bar_dates: dict[str, str]
    closes: dict[str, float]
    warnings: list[str]
    latest_bar: str | None
    skipped_rebalance: bool = False


class SignalScanner:
    def scan(
        self,
        *,
        strategy: Strategy,
        data: dict[str, pd.DataFrame],
        rebalance: str = "bar",
        last_rebalance_ts: str | None = None,
        history_tail: int | None = None,
    ) -> ScanOutput:
        all_index = sorted({ts for df in data.values() for ts in df.index})
        if not all_index:
            return ScanOutput(signals=[], bar_dates={}, closes={}, warnings=["no market data available"], latest_bar=None)

        warmup = strategy.warmup()
        warnings: list[str] = []
        if len(all_index) <= warmup:
            warnings.append(
                f"insufficient bars: got {len(all_index)}, strategy warmup requires {warmup}"
            )

        col_cache: dict[str, dict[str, np.ndarray]] = {}
        ts_idx_cache: dict[str, dict[pd.Timestamp, int]] = {}
        for symbol, df in data.items():
            col_cache[symbol] = {col: df[col].values for col in _OHLCV_COLS if col in df.columns}
            if "volume" not in col_cache[symbol]:
                col_cache[symbol]["volume"] = np.ones(len(df))
            ts_idx_cache[symbol] = {ts: i for i, ts in enumerate(df.index)}

        buffers: dict[str, _SymbolBuffer] = {symbol: _SymbolBuffer() for symbol in data}
        latest_ts = all_index[-1]
        latest_i = len(all_index) - 1

        for i, ts in enumerate(all_index):
            for symbol in data:
                idx = ts_idx_cache[symbol].get(ts)
                if idx is None:
                    continue
                cc = col_cache[symbol]
                buffers[symbol].append(
                    ts,
                    cc["open"][idx],
                    cc["high"][idx],
                    cc["low"][idx],
                    cc["close"][idx],
                    cc["volume"][idx],
                )

        if latest_i < warmup:
            return ScanOutput(
                signals=[],
                bar_dates={},
                closes={},
                warnings=warnings or ["latest bar is still within warmup period"],
                latest_bar=latest_ts.strftime("%Y-%m-%d"),
            )

        if not _should_evaluate_latest_bar(rebalance, latest_ts, last_rebalance_ts):
            msg = (
                f"skipped signal scan: latest bar {latest_ts.strftime('%Y-%m-%d')} "
                f"is not a {rebalance} rebalance bar (last_rebalance_ts={last_rebalance_ts})"
            )
            warnings.append(msg)
            return ScanOutput(
                signals=[],
                bar_dates={},
                closes={},
                warnings=warnings,
                latest_bar=latest_ts.strftime("%Y-%m-%d"),
                skipped_rebalance=True,
            )

        signals: list[SignalEvent] = []
        bar_dates: dict[str, str] = {}
        closes: dict[str, float] = {}
        for symbol in data:
            idx = ts_idx_cache[symbol].get(latest_ts)
            if idx is None:
                continue
            cc = col_cache[symbol]
            bar = pd.Series({col: cc[col][idx] for col in _OHLCV_COLS}, name=latest_ts)
            history_df = buffers[symbol].as_frame(tail=history_tail)
            bar_dates[symbol] = latest_ts.strftime("%Y-%m-%d")
            closes[symbol] = float(cc["close"][idx])
            for sig in strategy.on_bar(symbol, bar, history_df):
                signals.append(sig)

        return ScanOutput(
            signals=signals,
            bar_dates=bar_dates,
            closes=closes,
            warnings=warnings,
            latest_bar=latest_ts.strftime("%Y-%m-%d"),
        )
