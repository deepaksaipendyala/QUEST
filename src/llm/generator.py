from __future__ import annotations
from typing import Dict
from src.core.types import RunnerRequest

def generate_minimal_request(repo: str, version: str, code_file: str) -> RunnerRequest:
    # Deterministic, trivially valid pytest module just to exercise the Runner.
    test_src = (
        "def test_sanity():\n"
        "    x = 1 + 1\n"
        "    assert x == 2\n"
    )
    return {"repo": repo, "version": version, "code_file": code_file, "test_src": test_src}
