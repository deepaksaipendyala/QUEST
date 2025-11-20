from __future__ import annotations
from typing import Dict, List, Tuple
from src.llm.provider import LLMConfig, LLMResult, run_completion


def _infer_framework(current: str, repo: str) -> str:
    lowered = current.lower()
    if "pytest" in lowered or "@pytest" in lowered:
        return "pytest"
    if (
        "unittest" in lowered
        or "testcase" in lowered
        or "simpletestcase" in lowered
        or "django.test" in lowered
    ):
        return "unittest"
    if "django" in repo.lower():
        return "unittest"
    return "pytest"


def _compose_prompt(
    current: str,
    instructions: List[str],
    missing_lines: List[int],
    context: Dict,
) -> str:
    repo = str((context or {}).get("repo", "") or "")
    version = str((context or {}).get("version", "") or "")
    code_file = str((context or {}).get("code_file", "") or "")
    framework = _infer_framework(current, repo)

    guardrails: List[str] = [
        "Keep the existing imports unless a new helper is strictly required.",
        "Avoid filesystem or network dependencies; prefer in-memory values/mocks.",
        "Do not add `if __name__ == '__main__':` or call unittest.main/pytest.main.",
    ]
    if framework == "unittest":
        guardrails.insert(
            0,
            "Use unittest-style classes/tests (unittest.TestCase or django.test.SimpleTestCase). "
            "Do NOT import pytest or use pytest fixtures/decorators.",
        )
    else:
        guardrails.insert(
            0,
            "Pytest-style functions and fixtures are acceptable, but keep the current style consistent.",
        )
    if "django" in repo.lower():
        guardrails.append(
            "When interacting with Django utilities, use django.test helpers and avoid touching real files."
        )

    instruction_block = "\n".join(f"- {item}" for item in instructions if item)
    if missing_lines:
        line_targets = ", ".join(str(m) for m in missing_lines[:10])
        instruction_block += f"\n- Increase coverage for lines: {line_targets}."
    if not instruction_block.strip():
        instruction_block = "- Improve coverage and robustness without breaking existing passing tests."

    prompt_lines = [
        "You are an expert Python test engineer improving an existing test module.",
        f"Repository: {repo or 'unknown'}",
        f"Version: {version or 'unknown'}",
        f"Target file: {code_file or 'unknown'}",
        "Follow these guardrails:",
        "\n".join(f"- {rule}" for rule in guardrails),
        "Current test suite:",
        current,
        "Rewrite the suite by applying the instructions below while preserving the existing framework/style.",
        "Instructions:",
        instruction_block.strip(),
        "Return only the revised Python test module (plain code, no markdown).",
    ]
    return "\n".join(prompt_lines)


def enhance_with_llm(
    current: str,
    instructions: List[str],
    missing_lines: List[int],
    context: Dict,
    cfg: LLMConfig,
) -> Tuple[str, LLMResult]:
    prompt = _compose_prompt(current, instructions, missing_lines, context)
    result = run_completion(prompt, cfg)
    candidate = result.text.strip()
    if candidate:
        return candidate, result
    return current, result

