"""Load and validate dynamically generated strategy code."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from quantforge_stock.strategies.base import Strategy

from quantforge_mcp.codegen.validator import ValidationResult, validate_strategy_code


class StrategyLoadError(RuntimeError):
    """Raised when dynamic strategy code fails validation or loading."""

    def __init__(self, message: str, *, validation: ValidationResult | None = None) -> None:
        super().__init__(message)
        self.validation = validation


def _instantiate_strategy(mod: ModuleType) -> Strategy:
    candidates = []
    for obj in mod.__dict__.values():
        if isinstance(obj, type) and issubclass(obj, Strategy) and obj is not Strategy:
            candidates.append(obj)
    if len(candidates) != 1:
        raise StrategyLoadError("dynamic strategy must contain exactly one Strategy subclass")
    return candidates[0]()


def _exec_strategy_module(code: str, *, compile_name: str) -> ModuleType:
    module_name = f"_quantforge_dynamic_{abs(hash(compile_name)) & 0xFFFFFFFF:08x}"
    spec = importlib.util.spec_from_loader(module_name, loader=None)
    if spec is None:
        raise StrategyLoadError(f"unable to create module spec for {compile_name}")
    mod = importlib.util.module_from_spec(spec)
    mod.__file__ = compile_name
    sys.modules[module_name] = mod
    exec(compile(code, compile_name, "exec"), mod.__dict__)  # noqa: S102 — validated user strategy
    return mod


def load_strategy(*, code: str | None = None, source: Path | str | None = None) -> Strategy:
    """Validate and load exactly one Strategy subclass.

    Provide either ``code`` (source text) or ``source`` (path to strategy.py), not both.
    """
    if code is not None and source is not None:
        raise ValueError("provide code or source path, not both")
    if source is not None:
        path = Path(source)
        text = path.read_text(encoding="utf-8")
        compile_name = str(path)
    elif code is not None:
        text = code
        compile_name = "<dynamic_strategy>"
    else:
        raise ValueError("provide code or source")

    validation = validate_strategy_code(text)
    if not validation.valid:
        raise StrategyLoadError(
            "strategy validation failed: " + "; ".join(validation.errors),
            validation=validation,
        )
    mod = _exec_strategy_module(text, compile_name=compile_name)
    return _instantiate_strategy(mod)
