"""Transaction cost analysis helpers."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class TCAReport:
    """Transaction cost analysis report for a single order."""
    n_trades: int
    total_commission: float
    total_slippage: float
    total_notional: float
    avg_bps: float

    def summary(self) -> str:
        return (
            f"Trades: {self.n_trades}, "
            f"Notional: {self.total_notional}, "
            f"Commission: {self.total_commission}, "
            f"Slippage: {self.total_slippage}, "
            f"All-in cost: {self.avg_bps:.2f} bps of notional"
        )


def analyze_trades(trades: pd.DataFrame) -> TCAReport:
    """Given a BacktestResult.trades frame, compute TCA stats."""
    if trades.empty:
        return TCAReport(0, 0.0, 0.0, 0.0, 0.0)
    notional = (trades["qty"].abs() * trades["price"]).sum()
    slip_cost = (trades["qty"].abs() * trades["slippage"]).sum()
    commission = trades["commission"].sum()
    bps = 1e4 * (slip_cost + commission) / notional if notional > 0 else 0.0
    return TCAReport(
        n_trades=len(trades),
        total_commission=float(commission),
        total_slippage=float(slip_cost),
        total_notional=float(notional),
        avg_bps=float(bps),
    )

