from __future__ import annotations
import os
from typing import Dict
from src.contracts.messages import Critique
from src.llm.supervisor import analyze, analyze_with_llm
from src.llm.provider import LLMConfig, llm_enabled

class SupervisorAgent:
    name = "supervisor"
    def call(self, payload: Dict, *, cfg) -> Dict:
        # payload: RunnerResponse + {"target_coverage": float, "target_mutation": float}
        target_cov = float(payload.get("target_coverage", 60.0))
        target_mut = float(payload.get("target_mutation", 0.0))
        
        # Check if LLM-enhanced supervisor is enabled
        use_llm_supervisor = str(os.getenv("LLM_SUPERVISOR", "true")).lower() in ("1", "true", "yes")
        
        if use_llm_supervisor and llm_enabled():
            # Build LLM config for supervisor
            llm_config = LLMConfig(
                provider="openai",
                model="gpt-4o-mini",  # Use efficient model for analysis
                temperature=0.1,      # Low temperature for consistent analysis
                top_p=0.9,
                collect_logprobs=True  # Enable to get entropy/confidence metrics for supervisor analysis
            )
            
            critique, llm_result = analyze_with_llm(payload, target_cov, target_mut, llm_config)
            
            # Add LLM metadata to critique if available
            if llm_result:
                critique["llm_supervisor_metadata"] = {
                    "entropy": llm_result.entropy,
                    "avg_logprob": llm_result.avg_logprob,
                    "token_count": llm_result.token_count,
                    "input_tokens": llm_result.input_tokens,
                    "output_tokens": llm_result.output_tokens,
                    "estimated_cost": llm_result.estimated_cost,
                }
            
            return critique
        else:
            # Fall back to rule-based supervisor
            c: Critique = analyze(payload, target_cov, target_mut)
            return c
