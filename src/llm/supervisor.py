from __future__ import annotations
from typing import Dict, List
from src.contracts.messages import Critique

def _extract_missing_lines(payload: Dict) -> List[int]:
    coverage_details = payload.get("coverageDetails", {})
    if not isinstance(coverage_details, dict):
        return []
    missing = coverage_details.get("missing_lines", [])
    if not isinstance(missing, list):
        return []
    return [int(x) for x in missing if isinstance(x, int)]

def analyze(payload: Dict, target_coverage: float) -> Critique:
    status = str(payload.get("status", "error"))
    success = bool(payload.get("success", False))
    coverage = float(payload.get("coverage", 0.0))
    missing_lines = _extract_missing_lines(payload)

    compile_error = not success and status == "error"
    no_tests = status == "no_tests_collected"
    low_coverage = coverage < float(target_coverage)

    instructions: List[str] = []
    if compile_error:
        instructions.append("Resolve Runner errors and ensure tests execute successfully.")
    if no_tests:
        instructions.append("Add at least one pytest function so tests are collected.")
    if low_coverage:
        if missing_lines:
            targets = ", ".join(str(m) for m in missing_lines[:10])
            instructions.append(f"Add coverage for lines: {targets}.")
        else:
            instructions.append("Increase test coverage with more assertions.")

    critique: Critique = {
        "compile_error": compile_error,
        "no_tests": no_tests,
        "low_coverage": low_coverage,
        "missing_lines": missing_lines,
        "instructions": instructions,
    }
    return critique
