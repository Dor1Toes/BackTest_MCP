from __future__ import annotations

import ast
from dataclasses import dataclass, field

from codegen.allowlist import ALLOWED_MODULES, FORBIDDEN_CALLS


@dataclass
class ValidationResult:
    valid: bool
    class_name: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "class_name": self.class_name,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def validate_strategy_code(code: str) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    class_name: str | None = None
    strategy_classes: list[ast.ClassDef] = []

    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return ValidationResult(valid=False, errors=[f"syntax error: {exc}"])

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name not in ALLOWED_MODULES:
                    errors.append(f"import not allowed: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod not in ALLOWED_MODULES:
                errors.append(f"import not allowed: {mod}")
        elif isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Name) and fn.id in FORBIDDEN_CALLS:
                errors.append(f"forbidden call: {fn.id}")

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            is_strategy = any(
                (isinstance(base, ast.Name) and base.id == "Strategy")
                or (isinstance(base, ast.Attribute) and base.attr == "Strategy")
                for base in node.bases
            )
            if is_strategy:
                strategy_classes.append(node)

    if len(strategy_classes) != 1:
        errors.append("exactly one Strategy subclass is required")
    else:
        target = strategy_classes[0]
        class_name = target.name
        methods = {n.name for n in target.body if isinstance(n, ast.FunctionDef)}
        for required in ("on_bar", "warmup"):
            if required not in methods:
                errors.append(f"missing required method: {required}")

    return ValidationResult(valid=not errors, class_name=class_name, errors=errors, warnings=warnings)
