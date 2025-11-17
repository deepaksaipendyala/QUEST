from __future__ import annotations
from typing import Dict
from src.contracts.messages import Critique
from src.llm.supervisor import analyze

class SupervisorAgent:
    name = "supervisor"
    def call(self, payload: Dict, *, cfg) -> Dict:
        # payload: RunnerResponse + {"target_coverage": float, "target_mutation": float}
        target_cov = float(payload.get("target_coverage", 60.0))
        target_mut = float(payload.get("target_mutation", 0.0))
        c: Critique = analyze(payload, target_cov, target_mut)
        return c
