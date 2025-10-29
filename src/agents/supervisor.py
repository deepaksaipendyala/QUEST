from __future__ import annotations
from typing import Dict
from src.contracts.messages import Critique
from src.llm.supervisor import analyze

class SupervisorAgent:
    name = "supervisor"
    def call(self, payload: Dict, *, cfg) -> Dict:
        # payload: RunnerResponse + {"target_coverage": float}
        target = float(payload.get("target_coverage", 60.0))
        c: Critique = analyze(payload, target)
        return c
