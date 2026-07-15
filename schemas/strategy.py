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

    @field_validator("symbols")
    @classmethod
    def _non_empty_symbols(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("symbols 不能为空")
        return v


class BacktestConfigValidationResult(BaseModel):
    valid: bool
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


# Backward-compatible alias during migration.
StrategyConfig = BacktestConfig
