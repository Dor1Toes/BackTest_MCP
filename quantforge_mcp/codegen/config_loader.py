"""Load and validate model-generated backtest config.json."""
from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from quantforge_mcp.schemas.config import BacktestConfig, BacktestConfigValidationResult


class BacktestConfigError(ValueError):
    """Raised when backtest config fails validation."""

    def __init__(self, message: str, *, errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.errors = errors or [message]

    def to_validation_dict(self) -> dict:
        return BacktestConfigValidationResult(valid=False, errors=self.errors).model_dump()


def _format_validation_error(exc: ValidationError) -> list[str]:
    formatted: list[str] = []
    for err in exc.errors():
        loc = ".".join(str(part) for part in err.get("loc", ()))
        msg = err.get("msg", "invalid value")
        formatted.append(f"{loc}: {msg}" if loc else str(msg))
    return formatted


def load_backtest_config(
    *,
    config_json: str | None = None,
    source: Path | str | None = None,
) -> BacktestConfig:
    """Parse and validate backtest config.

    Provide either ``config_json`` (JSON text) or ``source`` (path to config.json), not both.
    """
    if config_json is not None and source is not None:
        raise ValueError("provide config_json or source, not both")
    if source is not None:
        text = Path(source).read_text(encoding="utf-8")
    elif config_json is not None:
        text = config_json
    else:
        raise ValueError("provide config_json or source")

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise BacktestConfigError(f"invalid json: {exc}") from exc

    if not isinstance(data, dict):
        raise BacktestConfigError("config must be a JSON object")

    try:
        return BacktestConfig(**data)
    except ValidationError as exc:
        errors = _format_validation_error(exc)
        raise BacktestConfigError(
            "config validation failed: " + "; ".join(errors),
            errors=errors,
        ) from exc
