from __future__ import annotations

import inspect
from typing import Any

from quantforge_stock import indicators, portfolio, risk, stats

MODULES: list[tuple[str, Any]] = [
    ("indicators", indicators),
    ("stats", stats),
    ("risk", risk),
    ("portfolio", portfolio),
]


def _safe_signature(obj: Any) -> str:
    try:
        return str(inspect.signature(obj))
    except Exception:
        return "()"


def _short_doc(obj: Any) -> str:
    doc = inspect.getdoc(obj) or ""
    if not doc:
        return ""
    return doc.splitlines()[0].strip()


def _module_payload(module_name: str, module_obj: Any) -> list[dict[str, str]]:
    exports = list(getattr(module_obj, "__all__", []))
    symbols: list[dict[str, str]] = []
    for symbol in exports:
        obj = getattr(module_obj, symbol, None)
        if obj is None:
            symbols.append({"name": symbol, "signature": "()", "description": ""})
            continue
        symbols.append(
            {
                "name": symbol,
                "signature": _safe_signature(obj),
                "description": _short_doc(obj),
            }
        )
    return symbols


def register_compute_resources(mcp) -> None:
    @mcp.resource("quantforge://compute/modules")
    def compute_modules_index() -> str:
        lines = [
            "# QuantForge Compute Modules",
            "",
            "Use these modules/functions to build dynamic strategy code.",
            "Read module details with `quantforge://compute/{module}`.",
            "",
        ]
        for module_name, module_obj in MODULES:
            lines.append(f"## {module_name}")
            lines.append(f"- URI: `quantforge://compute/{module_name}`")
            for item in _module_payload(module_name, module_obj):
                desc = f" - {item['description']}" if item["description"] else ""
                lines.append(f"- `{item['name']}{item['signature']}`{desc}")
            lines.append("")
        return "\n".join(lines)

    @mcp.resource("quantforge://compute/{module}")
    def compute_module_detail(module: str) -> str:
        module_name = module.strip().lower()
        candidates = {name: mod for name, mod in MODULES}
        target = candidates.get(module_name)
        if target is None:
            raise ValueError(f"unknown compute module: {module}")
        lines = [
            f"# Compute Module: {module_name}",
            "",
            f"**URI:** `quantforge://compute/{module_name}`",
            "",
        ]
        for item in _module_payload(module_name, target):
            lines.append(f"## {item['name']}")
            lines.append(f"- Signature: `{item['name']}{item['signature']}`")
            lines.append(f"- Description: {item['description'] or '(no description)'}")
            lines.append("")
        return "\n".join(lines)
