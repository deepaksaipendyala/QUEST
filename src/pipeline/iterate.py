from __future__ import annotations
import argparse
import os
import pathlib
import time
from typing import Dict
import yaml

from src.core.config import load_config
from src.core.storage import new_run_id, run_dir, write_json, write_text
from src.core.sandbox_client import post_runner
from src.llm.generator import generate_minimal_request
from src.llm.provider import LLMConfig, run_completion, llm_enabled
from src.reliability import score_pre_execution, score_post_execution
from src.static_analysis import analyze_test_file


def _load_defaults() -> dict[str, object]:
    cfg_path = pathlib.Path("configs/default.yaml")
    if not cfg_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {cfg_path}\n"
            "Please ensure configs/default.yaml exists."
        )
    with cfg_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        return {}
    return raw


def _build_llm_config(raw_cfg: dict[str, object]) -> LLMConfig:
    llm_block = raw_cfg.get("llm", {})
    provider_default = "openai"
    model_default = "gpt-4o-mini"
    temperature_default = "0.2"
    top_p_default = "0.95"
    collect_logprobs_default = True

    if isinstance(llm_block, dict):
        provider_default = str(llm_block.get("provider", provider_default))
        model_default = str(llm_block.get("model", model_default))
        decoding = llm_block.get("decoding", {})
        if isinstance(decoding, dict):
            temperature_default = str(decoding.get("temperature", temperature_default))
            top_p_default = str(decoding.get("top_p", top_p_default))
        collect_logprobs_default = bool(llm_block.get("collect_logprobs", collect_logprobs_default))

    return LLMConfig(
        provider=os.getenv("LLM_PROVIDER", provider_default),
        model=os.getenv("LLM_MODEL", model_default),
        temperature=float(os.getenv("LLM_TEMPERATURE", temperature_default)),
        top_p=float(os.getenv("LLM_TOP_P", top_p_default)),
        collect_logprobs=str(os.getenv("LLM_COLLECT_LOGPROBS", str(collect_logprobs_default))).lower()
        in ("1", "true", "yes"),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--code-file", required=True)
    parser.add_argument("--max-iters", type=int, default=None)
    args = parser.parse_args()

    app_cfg = load_config()
    raw_cfg = _load_defaults()
    llm_cfg = _build_llm_config(raw_cfg)

    default_iters = 1
    budgets = raw_cfg.get("budgets", {})
    if isinstance(budgets, dict):
        maybe_iters = budgets.get("max_iterations")
        if isinstance(maybe_iters, int) and maybe_iters > 0:
            default_iters = maybe_iters

    max_iters = args.max_iters if args.max_iters is not None and args.max_iters > 0 else default_iters

    run_id = new_run_id()
    base_dir = run_dir(run_id)
    run_start_time = time.time()
    total_llm_cost = 0.0
    total_llm_input_tokens = 0
    total_llm_output_tokens = 0
    total_llm_duration = 0.0
    total_runner_duration = 0.0
    total_static_duration = 0.0

    for index in range(1, max_iters + 1):
        iteration_dir = base_dir / f"iter_{index:03d}"
        iteration_dir.mkdir(parents=True, exist_ok=True)

        request_dict = generate_minimal_request(args.repo, args.version, args.code_file)
        
        # Only try to use LLM if it's enabled (has API key and not in dry-run mode)
        # Otherwise, use the default generator output which is known to work
        llm_metadata: dict[str, object] | None = None
        llm_result = None

        if llm_enabled():
            # Determine test framework based on repository
            # Django uses unittest, not pytest
            is_django = "django" in args.repo.lower()
            framework_instruction = (
                "Use unittest.TestCase (import unittest, create a class inheriting from unittest.TestCase)"
                if is_django
                else "Use pytest (functions starting with test_)"
            )
            
            # Use the already-generated test as an example (avoid duplicate generation)
            example_test = request_dict["test_src"]
            
            prompt = (
                f"Generate a Python test module that exercises the target file.\n"
                f"Repository: {args.repo}\nVersion: {args.version}\nFile: {args.code_file}\n"
                f"Test framework: {framework_instruction}\n\n"
                f"Example of a working test for this file:\n```python\n{example_test}\n```\n\n"
                "Requirements:\n"
                "- Test functions/classes that can be tested without file system dependencies when possible\n"
                "- Use simple, direct function calls with mock data\n"
                "- Avoid testing complex functions that require file setup unless necessary\n"
                "- Make sure all imports are correct and available in the test environment\n"
                "- Follow the example style: test simple utility functions first\n"
                "- Return ONLY the Python code, no markdown formatting, no explanations, no triple backticks\n"
            )

            llm_start = time.time()
            llm_result = run_completion(prompt, llm_cfg)
            llm_duration = time.time() - llm_start
            candidate_src = llm_result.text.strip()
            if candidate_src:
                request_dict["test_src"] = candidate_src
            llm_metadata = {
                "entropy": llm_result.entropy,
                "avg_logprob": llm_result.avg_logprob,
                "token_count": llm_result.token_count,
                "input_tokens": llm_result.input_tokens,
                "output_tokens": llm_result.output_tokens,
                "estimated_cost": llm_result.estimated_cost,
                "llm_duration_seconds": llm_duration,
                "token_logprobs": llm_result.token_logprobs,
            }
        # If LLM is not enabled, use the default generator output (already in request_dict)

        if os.getenv("ENABLE_VALIDATION", "0") == "1":
            from src.core.schema import RunnerRequestModel  # type: ignore

            RunnerRequestModel(**request_dict)

        write_json(iteration_dir / "request.json", request_dict)
        write_text(iteration_dir / "test_src.py", request_dict["test_src"])
        if llm_metadata is not None:
            write_json(iteration_dir / "llm_metadata.json", llm_metadata)

        static_metrics: Dict[str, object] | None = None
        static_duration = 0.0
        if app_cfg.static_analysis_enabled:
            static_start = time.time()
            static_metrics = analyze_test_file(iteration_dir / "test_src.py")
            static_duration = time.time() - static_start
            write_json(iteration_dir / "static_analysis.json", static_metrics)

        pre_reliability = score_pre_execution(llm_result, static_metrics)
        write_json(iteration_dir / "reliability.json", {"pre": pre_reliability})

        runner_start = time.time()
        resp = post_runner(app_cfg.runner_url, request_dict)
        runner_duration = time.time() - runner_start

        if os.getenv("ENABLE_VALIDATION", "0") == "1":
            from src.core.schema import RunnerResponseModel  # type: ignore

            RunnerResponseModel(**resp)

        write_json(iteration_dir / "response.json", resp)
        post_reliability = score_post_execution(
            pre_reliability or score_pre_execution(None, static_metrics),
            resp,
            app_cfg.target_coverage,
            app_cfg.target_mutation,
        )
        write_json(
            iteration_dir / "reliability.json",
            {"pre": pre_reliability, "post": post_reliability},
        )

        total_runner_duration += runner_duration
        total_static_duration += static_duration
        if llm_metadata:
            total_llm_cost += llm_metadata.get("estimated_cost", 0.0)
            total_llm_input_tokens += llm_metadata.get("input_tokens", 0)
            total_llm_output_tokens += llm_metadata.get("output_tokens", 0)
            total_llm_duration += llm_metadata.get("llm_duration_seconds", 0.0)

        iteration_metrics = {
            "iteration": index,
            "runner_duration_seconds": runner_duration,
            "static_analysis_duration_seconds": static_duration,
        }
        if llm_metadata:
            iteration_metrics["llm_duration_seconds"] = llm_metadata.get("llm_duration_seconds", 0.0)
            iteration_metrics["llm_cost"] = llm_metadata.get("estimated_cost", 0.0)
            iteration_metrics["llm_input_tokens"] = llm_metadata.get("input_tokens", 0)
            iteration_metrics["llm_output_tokens"] = llm_metadata.get("output_tokens", 0)
        write_json(iteration_dir / "metrics.json", iteration_metrics)

        cov_raw = resp.get("coverage", 0.0)
        cov = float(cov_raw) if isinstance(cov_raw, (int, float)) and cov_raw >= 0 else -1
        cov_display = f"{cov:.2f}%" if cov >= 0 else "N/A"
        cost_display = f"${llm_metadata.get('estimated_cost', 0.0):.6f}" if llm_metadata else "N/A"
        print(
            f"[{run_id} iter={index}] status={resp['status']} success={resp['success']} coverage={cov_display} cost={cost_display}"
        )

    run_duration = time.time() - run_start_time
    run_summary = {
        "run_id": run_id,
        "total_duration_seconds": run_duration,
        "iterations": max_iters,
        "total_llm_cost": total_llm_cost,
        "total_llm_input_tokens": total_llm_input_tokens,
        "total_llm_output_tokens": total_llm_output_tokens,
        "total_llm_duration_seconds": total_llm_duration,
        "total_runner_duration_seconds": total_runner_duration,
        "total_static_analysis_duration_seconds": total_static_duration,
    }
    write_json(base_dir / "run_summary.json", run_summary)
    print(f"[{run_id}] Run complete: total_cost=${total_llm_cost:.6f} total_duration={run_duration:.2f}s")


if __name__ == "__main__":
    main()
