"""动态回测 config.json 的 Pydantic 模型。"""
from __future__ import annotations

from datetime import date
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator


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
    # Last rebalance anchor (YYYY-MM-DD). Optional; only honored when rebalance is weekly/monthly.
    last_rebalance_ts: str | None = None
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

    @field_validator("last_rebalance_ts")
    @classmethod
    def _validate_last_rebalance_ts(cls, v: str | None) -> str | None:
        if v is None or not str(v).strip():
            return None
        val = str(v).strip()
        try:
            date.fromisoformat(val)
        except ValueError:
            raise ValueError("last_rebalance_ts format must be YYYY-MM-DD")
        return val

    @model_validator(mode="after")
    def _validate_ranges_and_dates(self) -> Self:
        errors: list[str] = []
        if self.initial_capital <= 0:
            errors.append("initial_capital must be > 0")
        if self.commission < 0:
            errors.append("commission must be >= 0")
        if self.slippage < 0:
            errors.append("slippage must be >= 0")
        if not (0 < float(self.sizing_fraction) <= 1.0):
            errors.append("sizing_fraction must be in (0, 1]")
        if self.start:
            try:
                date.fromisoformat(self.start)
            except ValueError:
                errors.append("start format must be YYYY-MM-DD")
        if self.end:
            try:
                date.fromisoformat(self.end)
            except ValueError:
                errors.append("end format must be YYYY-MM-DD")
        if self.start and self.end and self.start >= self.end:
            errors.append("start must be earlier than end")
        if errors:
            raise ValueError("; ".join(errors))
        return self


class BacktestConfigValidationResult(BaseModel):
    valid: bool
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


# Backward-compatible alias during migration.
StrategyConfig = BacktestConfig
