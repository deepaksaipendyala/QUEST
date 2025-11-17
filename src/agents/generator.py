from __future__ import annotations
from typing import Dict
from src.core.types import RunnerRequest
from src.contracts.messages import ContextPack
from src.llm.generator import generate_minimal_request

class GeneratorAgent:
    name = "generator"

    def call(self, payload: Dict, *, cfg) -> Dict:
        # payload: {"repo","version","code_file","context": ContextPack}
        repo = str(payload["repo"])
        version = str(payload["version"])
        code_file = str(payload["code_file"])
        context: ContextPack = payload.get("context", {"summary":"","symbols":[],"docstrings":[]})  # type: ignore[assignment]

        # Compose a deterministic minimal test using our known working baseline.
        # In the future we can vary this based on context, but for now we defer to generate_minimal_request.
        baseline: RunnerRequest = generate_minimal_request(repo, version, code_file)
        # Ensure we preserve repo/version/code_file even if the helper changes later.
        baseline["repo"] = repo
        baseline["version"] = version
        baseline["code_file"] = code_file
        return baseline
