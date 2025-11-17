from __future__ import annotations
import argparse
import os
from src.core.config import load_config
from src.core.storage import new_run_id, run_dir, write_json, write_text
from src.core.sandbox_client import post_runner
from src.llm.generator import generate_minimal_request
from src.reliability import score_pre_execution, score_post_execution
from src.static_analysis import analyze_test_file


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

    static_metrics = None
    if cfg.static_analysis_enabled:
        static_metrics = analyze_test_file(out / "test_src.py")
        write_json(out / "static_analysis.json", static_metrics)

    pre_score = score_pre_execution(None, static_metrics)
    write_json(out / "reliability.json", {"pre": pre_score})

    resp = post_runner(cfg.runner_url, request_dict)

    if os.getenv("ENABLE_VALIDATION", "0") == "1":
        from src.core.schema import RunnerResponseModel  # type: ignore

        RunnerResponseModel(**resp)

    write_json(out / "response.json", resp)
    post_score = score_post_execution(pre_score, resp, cfg.target_coverage, cfg.target_mutation)
    write_json(out / "reliability.json", {"pre": pre_score, "post": post_score})

    cov_raw = resp.get("coverage", 0.0)
    cov = float(cov_raw) if isinstance(cov_raw, (int, float)) and cov_raw >= 0 else -1
    # dont print the stdout field since its large
    resp.pop("stdout", None)
    print(resp)
    cov_display = f"{cov:.2f}%" if cov >= 0 else "N/A"
    print(f"[{run_id}] status={resp['status']} success={resp['success']} coverage={cov_display}")


if __name__ == "__main__":
    main()
