from __future__ import annotations
from typing import Dict, List, Optional
from src.contracts.messages import Critique


def _extract_missing_lines(payload: Dict) -> List[int]:
    coverage_details = payload.get("coverageDetails", {})
    if not isinstance(coverage_details, dict):
        return []
    missing = coverage_details.get("missing_lines", [])
    if not isinstance(missing, list):
        return []
    return [int(x) for x in missing if isinstance(x, int)]


def _as_float(value: object, default: float) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _lint_stats(static_metrics: Dict) -> tuple[int, List[str], bool]:
    if not isinstance(static_metrics, dict):
        return 0, [], True
    linters = static_metrics.get("linters", {})
    total_issues = 0
    missing_tools: List[str] = []
    if isinstance(linters, dict):
        for tool, info in linters.items():
            if not isinstance(info, dict):
                continue
            available = bool(info.get("available", True))
            if not available:
                missing_tools.append(tool)
                continue
            total_issues += max(int(info.get("issue_count", 0)), 0)
    syntax_ok = bool(static_metrics.get("syntax_ok", True))
    return total_issues, missing_tools, syntax_ok


def _reliability_guidance(
    pre_reliability: Optional[Dict], post_reliability: Optional[Dict]
) -> List[str]:
    tips: List[str] = []
    for label, rel in (("pre", pre_reliability), ("post", post_reliability)):
        if not isinstance(rel, dict):
            continue
        level = str(rel.get("level", "")).lower()
        if label == "post" and level and level not in ("trusted", "pass"):
            reasons = rel.get("reasons")
            if isinstance(reasons, list) and reasons:
                tip = "; ".join(str(r) for r in reasons if isinstance(r, str))
                if tip:
                    tips.append(f"Reliability blockers: {tip}.")
        lint_block = rel.get("lint")
        if isinstance(lint_block, dict):
            issues = lint_block.get("issues")
            if isinstance(issues, int) and issues > 0:
                tips.append(f"Fix {issues} lint/type issues noted in reliability analysis.")
        test_error = rel.get("test_error")
        if isinstance(test_error, str) and test_error:
            tips.append(f"Address runner error reported: {test_error}.")
    return tips


def analyze(payload: Dict, target_coverage: float, target_mutation: float = 0.0) -> Critique:
    status = str(payload.get("status", "error"))
    success = bool(payload.get("success", False))
    coverage = _as_float(payload.get("coverage"), 0.0)
    mutation_score = _as_float(payload.get("mutation_score"), -1.0)
    missing_lines = _extract_missing_lines(payload)
    static_metrics = payload.get("static_metrics") if isinstance(payload, dict) else None
    lint_issue_count, lint_missing_tools, syntax_ok = _lint_stats(static_metrics or {})

    compile_error = (not success and status == "error") or not syntax_ok
    no_tests = status == "no_tests_collected"
    coverage_target = _as_float(target_coverage, 0.0)
    low_coverage = coverage_target > 0.0 and coverage < coverage_target
    mutation_target = _as_float(target_mutation, 0.0)
    low_mutation = (
        mutation_target > 0.0
        and (
            mutation_score < mutation_target
            if mutation_score >= 0.0
            else True
        )
    )

    instructions: List[str] = []
    if not syntax_ok:
        instructions.append("Static analyzer found syntax issues; fix parser errors first.")
    if lint_issue_count > 0:
        instructions.append(
            f"Resolve {lint_issue_count} lint/type errors reported by available tools."
        )
    elif lint_missing_tools:
        instructions.append(
            f"Install lint/type tools ({', '.join(lint_missing_tools)}) to improve diagnostics."
        )
    if compile_error and syntax_ok:
        instructions.append("Resolve Runner errors and ensure tests execute successfully.")
    if no_tests:
        instructions.append("Add at least one pytest/unittest case so tests are collected.")
    if low_coverage:
        if missing_lines:
            targets = ", ".join(str(m) for m in missing_lines[:10])
            instructions.append(f"Add coverage for lines: {targets}.")
        else:
            instructions.append("Increase test coverage with more assertions.")
    if low_mutation and mutation_target > 0.0:
        if mutation_score >= 0.0:
            instructions.append(
                f"Improve mutation score from {mutation_score:.2f}% toward {mutation_target:.2f}%."
            )
        else:
            instructions.append(
                "Mutation score unavailable; ensure mutation testing runs and improves surviving mutants."
            )

    instructions.extend(
        _reliability_guidance(
            payload.get("pre_reliability"), payload.get("post_reliability")
        )
    )

    critique: Critique = {
        "compile_error": compile_error,
        "no_tests": no_tests,
        "low_coverage": low_coverage,
        "low_mutation": low_mutation,
        "mutation_score": mutation_score if mutation_score >= 0.0 else -1.0,
        "lint_issue_count": lint_issue_count,
        "lint_missing_tools": lint_missing_tools,
        "coverage_delta": 0.0,
        "mutation_delta": 0.0,
        "no_progress": False,
        "missing_lines": missing_lines,
        "instructions": instructions,
    }
    return critique
