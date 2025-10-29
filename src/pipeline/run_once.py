from __future__ import annotations
import argparse
import os
from src.core.config import load_config
from src.core.storage import new_run_id, run_dir, write_json, write_text
from src.core.sandbox_client import post_runner
from src.llm.generator import generate_minimal_request

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--code-file", required=True)
    args = parser.parse_args()

    cfg = load_config()
    run_id = new_run_id()
    out = run_dir(run_id)

    request_dict = generate_minimal_request(args.repo, args.version, args.code_file)

    if os.getenv("ENABLE_VALIDATION", "0") == "1":
        # Import inside the guarded block so environments without pydantic still work.
        from src.core.schema import RunnerRequestModel  # type: ignore
        RunnerRequestModel(**request_dict)

    write_json(out / "request.json", request_dict)
    write_text(out / "test_src.py", request_dict["test_src"])

    resp = post_runner(cfg.runner_url, request_dict)

    if os.getenv("ENABLE_VALIDATION", "0") == "1":
        from src.core.schema import RunnerResponseModel  # type: ignore
        RunnerResponseModel(**resp)

    write_json(out / "response.json", resp)

    cov = resp.get("coverage", 0.0)
    print(f"[{run_id}] status={resp['status']} success={resp['success']} coverage={cov:.2f}%")

if __name__ == "__main__":
    main()
