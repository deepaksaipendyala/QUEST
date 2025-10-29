from __future__ import annotations
from src.contracts.messages import Critique

def decide(critique: Critique, iterations_done: int, max_iterations: int) -> str:
    if iterations_done >= max_iterations:
        return "FINISH"
    if critique["compile_error"] or critique["no_tests"] or critique["low_coverage"]:
        return "ENHANCE"
    return "FINISH"
