from __future__ import annotations
from typing import Dict
from src.core.types import RunnerRequest


def generate_minimal_request(repo: str, version: str, code_file: str) -> RunnerRequest:
    # Deterministic, trivially valid pytest module just to exercise the Runner.
    test_src = "import httpx\n\ndef test_client_creation():\n    client = httpx.Client()\n    assert client is not None\n\ndef test_async_client():\n    client = httpx.AsyncClient()\n    assert client is not None\n"
    return {"repo": repo, "version": version, "code_file": code_file, "test_src": test_src}
