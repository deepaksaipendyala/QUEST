from __future__ import annotations
from typing import Dict
import os
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
        collect_logprobs = str(
            os.getenv("LLM_COLLECT_LOGPROBS", "0")
        ).lower() in ("1", "true", "yes")
        llm_cfg = LLMConfig(
            provider="openai",
            model=model,
            temperature=temperature,
            top_p=top_p,
            collect_logprobs=collect_logprobs,
        )

        revised, llm_result = enhance_with_llm(
            current=task["current_test_src"],
            instructions=task.get("instructions", []),
            missing_lines=task.get("missing_lines", []),
            context=task.get("context", {}),
            cfg=llm_cfg,
        )
        res: EnhanceResult = {
            "revised_test_src": revised,
            "notes": ["enhanced via LLM or fallback"],
            "llm_metadata": {
                "entropy": llm_result.entropy,
                "avg_logprob": llm_result.avg_logprob,
                "token_count": llm_result.token_count,
                "input_tokens": llm_result.input_tokens,
                "output_tokens": llm_result.output_tokens,
                "estimated_cost": llm_result.estimated_cost,
            } if llm_result.token_count > 0 else None,
        }
        return res
