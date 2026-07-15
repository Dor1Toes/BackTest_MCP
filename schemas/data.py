"""行情数据摘要。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class OHLCVSummary(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class StockDataSummary(BaseModel):
    symbol: str
    start: str
    end: str
    rows: int
    missing_pct: float = 0.0
    date_range: tuple[str, str] | None = None
    head: list[OHLCVSummary] = Field(default_factory=list)
    tail: list[OHLCVSummary] = Field(default_factory=list)
    stats: dict[str, float] = Field(default_factory=dict)
