from __future__ import annotations

import ast
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


@dataclass
class StaticMetrics:
    syntax_ok: bool
    syntax_error: str | None
    line_count: int
    function_count: int
    class_count: int
    avg_function_length: float
    max_function_length: int
    todo_count: int
    complexity: int


def _compute_function_lengths(tree: ast.AST) -> list[int]:
    lengths: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.body:
                start = getattr(node.body[0], "lineno", node.lineno)
                end = getattr(node.body[-1], "end_lineno", node.body[-1].lineno)
                lengths.append(max(1, end - start + 1))
            else:
                lengths.append(1)
    return lengths


def _run_tool(cmd: list[str], tool_name: str, path: Path) -> Dict[str, Any]:
    available = shutil.which(cmd[0]) is not None
    if not available:
        return {"available": False, "issue_count": 0, "exit_code": None, "output": ""}

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=path.parent,
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        return {
            "available": True,
            "issue_count": 0,
            "exit_code": -1,
            "output": f"{tool_name} failed: {exc}",
        }

    output = (proc.stdout or "") + (proc.stderr or "")
    lowered = output.lower()
    if tool_name == "pylint":
        issue_count = lowered.count("error") + lowered.count("fatal")
    else:
        issue_count = lowered.count("error:")

    return {
        "available": True,
        "issue_count": issue_count,
        "exit_code": proc.returncode,
        "output": output[-4000:],
    }


def run_linters(path: Path) -> Dict[str, Any]:
    """Best-effort lint and type checking for visibility in the supervisor."""
    results: Dict[str, Any] = {}
    results["pylint"] = _run_tool(
        ["pylint", "--score=no", "--disable=all", "--enable=E,F", str(path)],
        "pylint",
        path,
    )
    results["mypy"] = _run_tool(
        ["mypy", "--hide-error-context", "--hide-error-codes", str(path)],
        "mypy",
        path,
    )
    return results


def analyze_test_file(path: Path) -> Dict[str, Any]:
    """
    Perform lightweight static checks on the generated test file.
    Returns metrics that can be fed into reliability scoring.
    """
    path = path.resolve()
    text = path.read_text(encoding="utf-8")
    result: Dict[str, Any] = {
        "syntax_ok": True,
        "syntax_error": None,
        "line_count": len(text.splitlines()),
        "function_count": 0,
        "class_count": 0,
        "avg_function_length": 0.0,
        "max_function_length": 0,
        "todo_count": text.lower().count("todo"),
        "complexity": 0,
    }

    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        result["syntax_ok"] = False
        result["syntax_error"] = f"{exc.msg} (line {exc.lineno})"
        return result

    function_lengths = _compute_function_lengths(tree)
    if function_lengths:
        result["avg_function_length"] = sum(function_lengths) / len(function_lengths)
        result["max_function_length"] = max(function_lengths)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result["function_count"] += 1
        elif isinstance(node, ast.ClassDef):
            result["class_count"] += 1
        elif isinstance(
            node,
            (
                ast.If,
                ast.For,
                ast.While,
                ast.Try,
                ast.BoolOp,
                ast.With,
                ast.Assert,
            ),
        ):
            result["complexity"] += 1

    result["linters"] = run_linters(path)
    return result

