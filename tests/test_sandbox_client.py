from __future__ import annotations
import importlib
import json
import sys
import types
import src.core.sandbox_client as sandbox_client
from src.core.sandbox_client import post_runner
from src.core.types import RunnerRequest, RunnerResponse

def test_post_runner_dryrun(monkeypatch) -> None:
    monkeypatch.setenv("DRY_RUN", "1")
    payload: RunnerRequest = {
        "repo": "o/r",
        "version": "v",
        "code_file": "m.py",
        "test_src": "def test_x():\n    assert True",
    }
    resp = post_runner("http://ignored", payload)
    assert resp["status"] in {"failed", "no_tests_collected"}
    assert "coverage" in resp and isinstance(resp["coverage"], float)

def test_post_runner_fake_requests(monkeypatch) -> None:
    # Build a fake 'requests' module so this test runs offline without installing requests.
    fake_requests = types.SimpleNamespace()
    monkeypatch.delenv("DRY_RUN", raising=False)

    class DummyResp:
        def __init__(self, payload: RunnerResponse) -> None:
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> RunnerResponse:
            return self._payload

    def fake_post(url: str, headers: dict[str, str], data: str, timeout: int) -> DummyResp:
        body = json.loads(data)
        assert "repo" in body and "test_src" in body
        response_payload: RunnerResponse = {
            "status": "no_tests_collected",
            "success": False,
            "exitCode": 5,
            "executionTime": 0.01,
            "coverage": 0.0,
            "coverageDetails": {
                "covered_lines": 0,
                "num_statements": 0,
                "missing_lines": [],
                "excluded_lines": [],
            },
            "stdout": "",
            "stderr": "",
            "repoPath": "/tmp/x",
            "code_file": body["code_file"],
        }
        return DummyResp(response_payload)

    fake_requests.post = fake_post  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "requests", fake_requests)
    importlib.reload(sandbox_client)

    payload: RunnerRequest = {
        "repo": "o/r",
        "version": "v",
        "code_file": "m.py",
        "test_src": "def test_y():\n    assert True",
    }
    # Force non-dry run branch to exercise requests.post
    resp = sandbox_client.post_runner("http://localhost:3000/runner", payload)
    assert resp["status"] == "no_tests_collected"
