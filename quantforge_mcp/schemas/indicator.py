"""指标计算摘要。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class IndicatorPoint(BaseModel):
    date: str
    value: float | None = None


class IndicatorResultSummary(BaseModel):
    symbol: str
    indicator: str
    params: dict = Field(default_factory=dict)
    last_value: float | None = None
    min_value: float | None = None
    max_value: float | None = None
    mean_value: float | None = None
    sample: list[IndicatorPoint] = Field(default_factory=list)
    columns: list[str] = Field(default_factory=list)
