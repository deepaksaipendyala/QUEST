from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from src.llm.provider import LLMResult


@dataclass
class PreExecutionScore:
    level: str
    entropy: Optional[float]
    avg_logprob: Optional[float]
    token_count: int
    rationale: str


@dataclass
class PostExecutionScore:
    level: str
    reasons: list[str]
    coverage: float
    target_coverage: float
    mutation_score: float
    target_mutation: float
    success: bool
    test_error: str


def _entropy_level(entropy: Optional[float]) -> str:
    if entropy is None:
        return "unknown"
    if entropy <= 0.15:
        return "high"
    if entropy <= 0.4:
        return "medium"
    return "low"


def _downgrade_level(level: str) -> str:
    order = ["high", "medium", "low"]
    if level not in order:
        return "low"
    idx = order.index(level)
    return order[min(idx + 1, len(order) - 1)]


def _summarize_lint(static_metrics: Dict[str, Any]) -> Dict[str, Any]:
    linters = static_metrics.get("linters", {}) if isinstance(static_metrics, dict) else {}
    total_issues = 0
    missing_tools: list[str] = []
    reports: Dict[str, Any] = {}
    if isinstance(linters, dict):
        for tool, info in linters.items():
            if not isinstance(info, dict):
                continue
            available = bool(info.get("available", True))
            issue_count = int(info.get("issue_count", 0))
            if not available:
                missing_tools.append(tool)
            else:
                total_issues += max(issue_count, 0)
            reports[tool] = {
                "available": available,
                "issue_count": issue_count,
                "exit_code": info.get("exit_code"),
            }
    return {
        "issues": total_issues,
        "missing": missing_tools,
        "reports": reports,
    }


def score_pre_execution(
    llm_result: Optional[LLMResult],
    static_metrics: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    static_metrics = static_metrics or {}
    syntax_ok = static_metrics.get("syntax_ok", True)
    syntax_error = static_metrics.get("syntax_error")
    lint_summary = _summarize_lint(static_metrics)
    if llm_result is None:
        base_level = "unknown"
        entropy = None
        avg_logprob = None
        token_count = 0
    else:
        entropy = llm_result.entropy
        avg_logprob = llm_result.avg_logprob
        token_count = llm_result.token_count
        base_level = _entropy_level(entropy)

    level = base_level
    rationale_parts: list[str] = []

    if not syntax_ok:
        level = "low"
        rationale_parts.append("Syntax errors detected in test file.")
        if syntax_error:
            rationale_parts.append(syntax_error)
    else:
        if entropy is None:
            rationale_parts.append("Entropy not available from provider.")
        elif base_level == "high":
            rationale_parts.append("Low entropy indicates confident generation.")
        elif base_level == "medium":
            rationale_parts.append("Moderate entropy; some uncertainty present.")
        else:
            rationale_parts.append("High entropy indicates uncertain generation.")

    if lint_summary["issues"] > 0:
        level = _downgrade_level(level)
        rationale_parts.append(
            f"Lint/type checks surfaced {lint_summary['issues']} blocking issue(s)."
        )
    elif lint_summary["missing"]:
        rationale_parts.append(
            f"Lint/type tools unavailable: {', '.join(lint_summary['missing'])}."
        )

    return {
        "level": level,
        "entropy": entropy,
        "avg_logprob": avg_logprob,
        "token_count": token_count,
        "rationale": " ".join(rationale_parts) if rationale_parts else "No confidence data available.",
        "static": static_metrics,
        "lint": lint_summary,
    }


def score_post_execution(
    pre_score: Dict[str, Any],
    runner_response: Dict[str, Any],
    target_coverage: float,
    target_mutation: float,
) -> Dict[str, Any]:
    coverage = float(runner_response.get("coverage", 0.0))
    mutation_score = float(runner_response.get("mutation_score", -1.0))
    success = bool(runner_response.get("success", False))
    test_error = str(runner_response.get("test_error", ""))

    reasons: list[str] = []
    level = "needs_review"

    if not success:
        level = "discard"
        reasons.append("Tests failed to execute successfully.")
    else:
        if coverage >= target_coverage and (
            target_mutation <= 0.0 or mutation_score >= target_mutation or mutation_score < 0.0
        ):
            level = "trusted"
            reasons.append("Coverage and mutation targets met.")
        elif coverage >= 0.8 * target_coverage:
            level = "needs_review"
            reasons.append("Coverage close to target; review before trust.")
        else:
            level = "needs_review"
            reasons.append("Coverage below target threshold.")

        if target_mutation > 0.0:
            if mutation_score < 0.0:
                reasons.append("Mutation score unavailable; rerun mutation testing.")
            elif mutation_score < target_mutation:
                reasons.append("Mutation score below target.")

    return {
        "pre_level": pre_score.get("level", "unknown"),
        "level": level,
        "reasons": reasons,
        "coverage": coverage,
        "target_coverage": target_coverage,
        "mutation_score": mutation_score,
        "target_mutation": target_mutation,
        "success": success,
        "test_error": test_error,
        "lint": pre_score.get("lint"),
    }

