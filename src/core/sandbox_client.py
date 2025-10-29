from __future__ import annotations
import os, json, requests
from .types import RunnerRequest, RunnerResponse

def _synthetic_response(payload: RunnerRequest) -> RunnerResponse:
    test_src = payload["test_src"]
    test_count = sum(1 for line in test_src.splitlines() if line.strip().startswith("def test_"))
    status = "no_tests_collected" if test_count == 0 else "failed"
    return {
        "status": status,
        "success": False,
        "exitCode": 5,
        "executionTime": 0.01,
        "coverage": 0.0,
        "coverageDetails": {
            "covered_lines": 0,
            "num_statements": 0,
            "missing_lines": [],
            "excluded_lines": []
        },
        "stdout": "",
        "stderr": "" if test_count > 0 else "no tests collected",
        "repoPath": "/tmp/dryrun",
        "code_file": payload["code_file"],
    }

def post_runner(runner_url: str, payload: RunnerRequest) -> RunnerResponse:
    # Dry-run if env flag is set or runner_url uses the dryrun:// scheme.
    if os.getenv("DRY_RUN", "0") == "1" or runner_url.startswith("dryrun://"):
        return _synthetic_response(payload)
    r = requests.post(
        runner_url,
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload),
        timeout=600,
    )
    r.raise_for_status()
    return r.json()  # type: ignore[return-value]
