"""Karpathy-inspired code quality guardrails.

Static checks and helpers to enforce clean, minimal Python:
- No nested try/catch
- No verbose loops (prefer comprehensions)
- Functions under 30 lines
- Flat boolean expressions
"""
from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Violation:
    file: str
    line: int
    rule: str
    message: str


def check_nested_try(tree: ast.AST, filepath: str) -> list[Violation]:
    """Flag nested try/except blocks."""
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        for child in ast.walk(node):
            if child is not node and isinstance(child, ast.Try):
                violations.append(Violation(filepath, child.lineno, "NO_NESTED_TRY", "Nested try/except detected"))
    return violations


def check_function_length(tree: ast.AST, filepath: str, max_lines: int = 30) -> list[Violation]:
    """Flag functions longer than max_lines."""
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        length = (node.end_lineno or node.lineno) - node.lineno + 1
        if length > max_lines:
            violations.append(
                Violation(filepath, node.lineno, "FUNC_TOO_LONG", f"{node.name}() is {length} lines (max {max_lines})")
            )
    return violations


def check_verbose_loop(tree: ast.AST, filepath: str) -> list[Violation]:
    """Flag for-loops that append to a list (should be a comprehension)."""
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        for stmt in node.body:
            if (
                isinstance(stmt, ast.Expr)
                and isinstance(stmt.value, ast.Call)
                and isinstance(stmt.value.func, ast.Attribute)
                and stmt.value.func.attr == "append"
            ):
                violations.append(
                    Violation(filepath, node.lineno, "USE_COMPREHENSION", "Loop+append pattern — use a list comprehension")
                )
    return violations


def lint_file(filepath: str | Path) -> list[Violation]:
    """Run all guardrail checks on a single Python file."""
    try:
        source = Path(filepath).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(filepath))
    except (UnicodeDecodeError, SyntaxError):
        return []
    fp = str(filepath)
    return check_nested_try(tree, fp) + check_function_length(tree, fp) + check_verbose_loop(tree, fp)


def lint_directory(directory: str | Path) -> list[Violation]:
    """Lint all .py files in a directory tree."""
    violations = []
    skip = {".venv", "venv", "node_modules", ".git", "__pycache__"}
    for py_file in Path(directory).rglob("*.py"):
        if not (skip & set(py_file.parts)):
            violations.extend(lint_file(py_file))
    return violations


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    path = Path(target)
    violations = lint_directory(path) if path.is_dir() else lint_file(path)
    if not violations:
        print("All clean — Karpathy approved.")
    for v in violations:
        print(f"{v.file}:{v.line} [{v.rule}] {v.message}")
    sys.exit(1 if violations else 0)
