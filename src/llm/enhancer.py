from __future__ import annotations
from typing import List
from src.llm.provider import LLMConfig, run_completion

def _compose_prompt(current: str, instructions: List[str], missing_lines: List[int]) -> str:
    instruction_block = "\n".join(f"- {item}" for item in instructions)
    missing_block = ", ".join(str(m) for m in missing_lines)
    prompt_lines = [
        "You refine pytest modules.",
        "Current test suite:",
        current,
        "Instructions:",
        instruction_block or "- Improve coverage and robustness.",
        f"Missing lines to cover: {missing_block or 'none provided'}",
        "Return only the revised pytest module.",
    ]
    return "\n".join(prompt_lines)

def enhance_with_llm(current: str, instructions: List[str], missing_lines: List[int], cfg: LLMConfig) -> str:
    prompt = _compose_prompt(current, instructions, missing_lines)
    candidate = run_completion(prompt, cfg).strip()
    if candidate:
        return candidate
    return current
