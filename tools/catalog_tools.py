from __future__ import annotations

import ast
import inspect
from pathlib import Path
from typing import Any

from quantforge_mcp.quantforge_stock import indicators, portfolio, risk, stats


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


def _strategy_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "quantforge_stock" / "strategies"


def _extract_strategy_meta(path: Path) -> dict[str, Any]:
    source = path.read_text(encoding="utf-8")
    classes: list[dict[str, str]] = []
    file_desc = ""
    try:
        tree = ast.parse(source)
        file_desc = ast.get_docstring(tree) or ""
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                class_doc = ast.get_docstring(node) or ""
                classes.append(
                    {
                        "name": node.name,
                        "description": class_doc.splitlines()[0].strip() if class_doc else "",
                    }
                )
    except SyntaxError:
        pass

    return {
        "file": path.name,
        "description": file_desc.splitlines()[0].strip() if file_desc else "",
        "classes": classes,
    }


def register_catalog_tools(mcp) -> None:
    @mcp.tool()
    def list_compute_modules() -> dict[str, Any]:
        """列出可供 LLM 生成策略使用的计算模块函数（含签名/描述）。"""
        modules_payload: list[dict[str, Any]] = []
        for module_name, module_obj in MODULES:
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
            modules_payload.append({"module": module_name, "symbols": symbols})
        return {"ok": True, "modules": modules_payload}

    @mcp.tool()
    def list_strategy_examples() -> dict[str, Any]:
        """列出 quantforge 策略示例文件（含类名和描述）。"""
        base = _strategy_dir()
        if not base.exists():
            return {"ok": False, "error": f"strategy directory not found: {base}"}
        items = [_extract_strategy_meta(p) for p in sorted(base.glob("*.py")) if p.name != "__init__.py"]
        return {"ok": True, "strategies": items}

