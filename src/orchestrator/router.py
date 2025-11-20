from __future__ import annotations
from src.contracts.messages import Critique


# def decide(critique: Critique, iterations_done: int, max_iterations: int) -> str:
#     if iterations_done >= max_iterations:
#         return "FINISH"
#     if critique.get("no_progress"):
#         return "FINISH"
#     if (
#         critique["compile_error"]
#         or critique["no_tests"]
#         or critique["low_coverage"]
#         or critique.get("low_mutation", False)
#     ):
#         return "ENHANCE"
#     return "FINISH"

def decide(critique: Critique, iterations_done: int, max_iterations: int) -> str:
    if iterations_done >= max_iterations:
        return "FINISH"
    return "ENHANCE"