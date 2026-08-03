from __future__ import annotations

from pydantic import BaseModel, Field


class SignalInfo(BaseModel):
    symbol: str
    direction: int
    strength: float
    strategy_id: str
    bar_date: str
    close: float


class ScanResult(BaseModel):
    ok: bool
    strategy_name: str
    symbols: list[str]
    data_range: dict[str, str | int]
    signals: list[SignalInfo] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    validation: dict | None = None
    notified: bool = False
    notify_error: str | None = None
