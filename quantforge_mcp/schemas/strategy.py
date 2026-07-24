"""动态回测配置与校验模型。"""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class BacktestConfig(BaseModel):
    name: str = "dynamic_strategy"
    symbols: list[str] = Field(default_factory=lambda: ["NVDA"])
    start: str = ""
    end: str = ""
    initial_capital: float = 100_000.0
    commission: float = 0.0003
    slippage: float = 0.001
    # If true, interpret Strategy SignalEvent.strength as a target weight
    # (fraction of equity) per symbol.
    target_weights: bool = False
    # Used when target_weights=false: per-signal sizing cap as fraction of equity.
    sizing_fraction: float = 0.95
    # Rebalance cadence. Applies after warmup.
    rebalance: str = "bar"  # "bar" | "weekly" | "monthly"
    # If set, strategy only sees last N bars in `history`.
    history_tail: int | None = None

    @field_validator("symbols")
    @classmethod
    def _non_empty_symbols(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("symbols 不能为空")
        return v

    @field_validator("rebalance")
    @classmethod
    def _validate_rebalance(cls, v: str) -> str:
        val = (v or "").strip().lower()
        if val not in {"bar", "weekly", "monthly"}:
            raise ValueError("rebalance must be one of: bar, weekly, monthly")
        return val

    @field_validator("history_tail")
    @classmethod
    def _validate_history_tail(cls, v: int | None) -> int | None:
        if v is None:
            return None
        if int(v) <= 0:
            raise ValueError("history_tail must be a positive integer")
        return int(v)


class BacktestConfigValidationResult(BaseModel):
    valid: bool
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


# Backward-compatible alias during migration.
StrategyConfig = BacktestConfig
