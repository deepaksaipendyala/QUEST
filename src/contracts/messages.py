from __future__ import annotations
from typing import List, TypedDict

class Critique(TypedDict):
    compile_error: bool
    no_tests: bool
    low_coverage: bool
    low_mutation: bool
    mutation_score: float
    lint_issue_count: int
    lint_missing_tools: List[str]
    coverage_delta: float
    mutation_delta: float
    no_progress: bool
    missing_lines: List[int]
    instructions: List[str]

class EnhanceTask(TypedDict):
    current_test_src: str
    instructions: List[str]
    missing_lines: List[int]
    context: dict  # {"repo": str, "version": str, "code_file": str}

class EnhanceResult(TypedDict, total=False):
    revised_test_src: str
    notes: List[str]
    llm_metadata: dict  # Optional LLM metadata with entropy, cost, tokens, etc.

class ContextPack(TypedDict):
    # forward-compatible container for repo/file insights
    summary: str              # 1-2 line description of module
    symbols: List[str]        # function/class names
    docstrings: List[str]     # top-level or selected docstrings
