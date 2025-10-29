from __future__ import annotations
from typing import Dict
from src.contracts.messages import EnhanceTask, EnhanceResult
from src.llm.provider import LLMConfig
from src.llm.enhancer import enhance_with_llm

class EnhancerAgent:
    name = "enhancer"
    def call(self, payload: Dict, *, cfg) -> Dict:
        task: EnhanceTask = payload  # type: ignore[assignment]
        model = "gpt-4o-mini"
        temperature = 0.2
        top_p = 0.95
        llm_cfg = LLMConfig(provider="openai", model=model, temperature=temperature, top_p=top_p)

        revised = enhance_with_llm(
            current=task["current_test_src"],
            instructions=task.get("instructions", []),
            missing_lines=task.get("missing_lines", []),
            cfg=llm_cfg,
        )
        res: EnhanceResult = {"revised_test_src": revised, "notes": ["enhanced via LLM or fallback"]}
        return res
