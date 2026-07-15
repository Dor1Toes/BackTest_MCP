"""回测相关模型。"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class EquityPoint(BaseModel):
    date: str
    equity: float


class BacktestMetrics(BaseModel):
    total_return: float | None = None
    annual_return: float | None = None
    sharpe_ratio: float | None = None
    sortino_ratio: float | None = None
    max_drawdown: float | None = None
    calmar_ratio: float | None = None
    win_rate: float | None = None
    n_trades: int = 0
    initial_capital: float = 100_000.0
    final_equity: float | None = None


class BacktestResultSummary(BaseModel):
    job_id: str
    status: Literal["done", "failed"]
    symbol: str
    strategy_name: str
    metrics: BacktestMetrics
    equity_curve_sample: list[EquityPoint] = Field(default_factory=list)
    trades_sample: list[dict] = Field(default_factory=list)
    artifact_id: str | None = None


class BacktestJobStatus(BaseModel):
    job_id: str
    status: Literal["pending", "running", "done", "failed"]
    message: str = ""
    result: BacktestResultSummary | None = None
