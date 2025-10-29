from __future__ import annotations
from typing import Dict
from src.core.types import RunnerRequest
from src.contracts.messages import ContextPack

class GeneratorAgent:
    name = "generator"

    def call(self, payload: Dict, *, cfg) -> Dict:
        # payload: {"repo","version","code_file","context": ContextPack}
        repo = str(payload["repo"])
        version = str(payload["version"])
        code_file = str(payload["code_file"])
        context: ContextPack = payload.get("context", {"summary":"","symbols":[],"docstrings":[]})  # type: ignore[assignment]

        # Compose a deterministic minimal test using context (forward-compatible promptless baseline)
        symbols = context.get("symbols", [])
        target_name = symbols[0] if symbols else "sanity"
        test_src = (
            "import math\n"
            f"def test_{target_name}_sanity():\n"
            "    x = 1 + 1\n"
            "    assert x == 2\n"
        )
        req: RunnerRequest = {"repo": repo, "version": version, "code_file": code_file, "test_src": test_src}
        return req
