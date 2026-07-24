from __future__ import annotations

ALLOWED_MODULES = {
    "pandas",
    "numpy",
    "dataclasses",
    "typing",
    "quantforge_stock.strategies.base",
    "quantforge_stock.core.event",
    "quantforge_stock.indicators.technical",
    "quantforge_stock.indicators.statistical",
}

FORBIDDEN_CALLS = {"exec", "eval", "open", "__import__", "compile"}
