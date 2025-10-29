from __future__ import annotations
from typing import List, TypedDict

class Critique(TypedDict):
    compile_error: bool
    no_tests: bool
    low_coverage: bool
    missing_lines: List[int]
    instructions: List[str]

class EnhanceTask(TypedDict):
    current_test_src: str
    instructions: List[str]
    missing_lines: List[int]
    context: dict  # {"repo": str, "version": str, "code_file": str}

class EnhanceResult(TypedDict):
    revised_test_src: str
    notes: List[str]

class ContextPack(TypedDict):
    # forward-compatible container for repo/file insights
    summary: str              # 1-2 line description of module
    symbols: List[str]        # function/class names
    docstrings: List[str]     # top-level or selected docstrings
