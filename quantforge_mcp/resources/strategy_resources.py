from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

def _strategies_dir() -> Path:
    import quantforge_stock

    return Path(quantforge_stock.__file__).resolve().parent / "strategies"


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


def _iter_strategy_files() -> list[Path]:
    root = _strategies_dir()
    if not root.exists():
        return []
    return sorted(p for p in root.glob("*.py") if p.name != "__init__.py")


def _resolve_strategy_path(name: str) -> Path:
    safe = name.strip().replace("/", "").replace("\\", "").removesuffix(".py")
    if not safe:
        raise ValueError("strategy name must not be empty")
    path = _strategies_dir() / f"{safe}.py"
    if not path.exists():
        raise ValueError(f"unknown strategy: {name}")
    return path


def register_strategy_resources(mcp) -> None:
    @mcp.resource("quantforge://strategies/index")
    def strategies_index() -> str:
        """Built-in strategy examples index."""
        lines = [
            "# QuantForge Strategy Examples",
            "",
            "Read a single example with `quantforge://strategies/{name}`.",
            "Dynamic backtest code must follow `quantforge://codegen/spec` (allowlist imports only).",
            "",
        ]
        for path in _iter_strategy_files():
            meta = _extract_strategy_meta(path)
            stem = path.stem
            lines.append(f"## {stem}")
            lines.append(f"- File: `{meta['file']}`")
            if meta["description"]:
                lines.append(f"- Summary: {meta['description']}")
            for cls in meta["classes"]:
                desc = f" - {cls['description']}" if cls["description"] else ""
                lines.append(f"- Class: `{cls['name']}`{desc}")
            lines.append(f"- URI: `quantforge://strategies/{stem}`")
            lines.append("")
        return "\n".join(lines)

    @mcp.resource("quantforge://strategies/{name}")
    def strategy_detail(name: str) -> str:
        """Full source and metadata for one built-in strategy example."""
        path = _resolve_strategy_path(name)
        meta = _extract_strategy_meta(path)
        source = path.read_text(encoding="utf-8")
        lines = [
            f"# Strategy: {path.stem}",
            "",
            f"**File:** `{meta['file']}`",
        ]
        if meta["description"]:
            lines.append(f"**Summary:** {meta['description']}")
        lines.extend(["", "## Classes", ""])
        for cls in meta["classes"]:
            desc = f": {cls['description']}" if cls["description"] else ""
            lines.append(f"- `{cls['name']}`{desc}")
        lines.extend(
            [
                "",
                "> Reference only. For `run_backtest_dynamic`, rewrite as a single Strategy subclass per codegen spec.",
                "",
                "## Source",
                "",
                "```python",
                source.rstrip(),
                "```",
            ]
        )
        return "\n".join(lines)
