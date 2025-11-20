from __future__ import annotations

import argparse
import os
import pathlib
import time
from typing import Dict, Optional, Tuple
import yaml

from src.agents.enhancer import EnhancerAgent
from src.agents.generator import GeneratorAgent
from src.agents.supervisor import SupervisorAgent
from src.bus.inproc import send
from src.context.miner import mine_python_context
from src.core.config import load_config
from src.core.sandbox_client import post_runner
from src.core.storage import new_run_id, run_dir, write_json, write_text
from src.llm.provider import LLMConfig, llm_enabled, run_completion
from src.observability.events import append_event
from src.orchestrator.router import decide
from src.reliability import score_pre_execution, score_post_execution
from src.static_analysis import analyze_test_file


def _as_float(value: object, default: float = 0.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _build_llm_config() -> LLMConfig:
    """Build LLMConfig from config file and environment variables."""
    cfg_path = pathlib.Path("configs/default.yaml")
    raw_cfg: dict = {}
    if cfg_path.exists():
        with cfg_path.open("r", encoding="utf-8") as f:
            raw_cfg = yaml.safe_load(f) or {}
    
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


def _maybe_analyze(cfg, path: pathlib.Path, out_path: pathlib.Path) -> Optional[Dict]:
    if not cfg.static_analysis_enabled:
        return None
    metrics = analyze_test_file(path)
    write_json(out_path, metrics)
    return metrics


def _write_run_summary(
    out: pathlib.Path,
    run_id: str,
    iterations: int,
    total_llm_cost: float,
    total_llm_input_tokens: int,
    total_llm_output_tokens: int,
    total_llm_duration: float,
    total_runner_duration: float,
    total_static_duration: float,
    run_duration: float,
) -> None:
    summary = {
        "run_id": run_id,
        "total_duration_seconds": run_duration,
        "iterations": iterations,
        "total_llm_cost": total_llm_cost,
        "total_llm_input_tokens": total_llm_input_tokens,
        "total_llm_output_tokens": total_llm_output_tokens,
        "total_llm_duration_seconds": total_llm_duration,
        "total_runner_duration_seconds": total_runner_duration,
        "total_static_analysis_duration_seconds": total_static_duration,
    }
    write_json(out / "run_summary.json", summary)


def _update_progress(
    critique: Dict,
    coverage: float,
    mutation_score: float,
    last_cov: Optional[float],
    last_mut: Optional[float],
    stagnation_count: int,
) -> Tuple[Dict, Optional[float], Optional[float], int]:
    cov_delta = coverage - (last_cov if last_cov is not None else coverage)
    mut_delta = 0.0
    if mutation_score >= 0.0:
        baseline = last_mut if last_mut is not None else mutation_score
        mut_delta = mutation_score - baseline

    progress = cov_delta >= 1.0 or mut_delta >= 2.0
    if not progress and (critique.get("low_coverage") or critique.get("low_mutation")):
        stagnation_count += 1
    else:
        stagnation_count = 0

    critique["coverage_delta"] = cov_delta
    critique["mutation_delta"] = mut_delta
    critique["no_progress"] = stagnation_count >= 2

    last_cov = coverage
    if mutation_score >= 0.0:
        last_mut = mutation_score

    return critique, last_cov, last_mut, stagnation_count


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--version", required=True)
    ap.add_argument("--code-file", required=True)
    ap.add_argument("--max-iters", type=int, default=2)
    ap.add_argument("--repo-root", default=".")  # local path for context miner (forward-compat)
    args = ap.parse_args()

    cfg = load_config()
    run_id = new_run_id()
    out = run_dir(run_id)
    events_log = out / "events.log"
    target_cov = cfg.target_coverage
    target_mutation = cfg.target_mutation
    max_iters = int(args.max_iters)

    run_start_time = time.time()
    total_llm_cost = 0.0
    total_llm_input_tokens = 0
    total_llm_output_tokens = 0
    total_llm_duration = 0.0
    total_runner_duration = 0.0
    total_static_duration = 0.0

    # Context mining (forward-compat; uses local repo-root by default)
    context = mine_python_context(pathlib.Path(args.repo_root), args.code_file)
    write_json(out / "context.json", context)

    gen = GeneratorAgent()
    sup = SupervisorAgent()
    enh = EnhancerAgent()

    stagnation = 0
    last_cov: Optional[float] = None
    last_mut: Optional[float] = None

    # Attempt 0 - Generate initial test
    gen_payload: Dict = {"repo": args.repo, "version": args.version, "code_file": args.code_file, "context": context}
    
    llm_metadata0: Optional[Dict] = None
    llm_result0 = None
    
    # if llm_enabled():
    #     # Use LLM for initial generation
    #     is_django = "django" in args.repo.lower()
    #     framework_instruction = (
    #         "Use unittest.TestCase (import unittest, create a class inheriting from unittest.TestCase). "
    #         "For Django, import from django.test import TestCase or SimpleTestCase as needed."
    #         if is_django
    #         else "Use pytest (functions starting with test_)"
    #     )
        
    #     # Get a baseline test from the generator as fallback and as an example
    #     baseline_req = send(gen, gen_payload, cfg)
    #     baseline_test = baseline_req["test_src"]
    #     symbols = context.get("symbols") or []
    #     extra_reqs = ""
    #     if isinstance(symbols, list) and any(
    #         isinstance(sym, str) and sym.lower() == "was_modified_since" for sym in symbols
    #     ):
    #         extra_reqs = "- Prefer calling was_modified_since with simple timestamps instead of touching the filesystem.\n"
    #     prompt = (
    #         f"Generate a Python test module that exercises the target file.\n"
    #         f"Repository: {args.repo}\nVersion: {args.version}\nFile: {args.code_file}\n"
    #         f"Test framework: {framework_instruction}\n\n"
    #         "Example of a working test for this file:\n"
    #         f"```python\n{baseline_test}\n```\n\n"
    #         "Requirements:\n"
    #         "- Test functions/classes that can be tested without file system dependencies when possible\n"
    #         "- Use simple, direct function calls with mock data\n"
    #         "- Avoid calling django.views.static.serve with real paths; do not rely on actual files on disk\n"
    #         "- Make sure all imports are correct and available in the test environment\n"
    #         "- For Django: Import necessary test base classes (e.g., from django.test import TestCase, SimpleTestCase)\n"
    #         "- Do NOT include a __main__ guard or run the tests directly\n"
    #         "- Return ONLY the Python code, no markdown formatting, no explanations, no triple backticks\n"
    #         f"{extra_reqs}"
    #     )
        
    #     llm_cfg = _build_llm_config()
    #     llm_start = time.time()
    #     llm_result0 = run_completion(prompt, llm_cfg)
    #     llm_duration = time.time() - llm_start
    #     total_llm_duration += llm_duration
    #     total_llm_cost += llm_result0.estimated_cost
    #     total_llm_input_tokens += llm_result0.input_tokens
    #     total_llm_output_tokens += llm_result0.output_tokens
        
    #     candidate_src = llm_result0.text.strip()
    #     if candidate_src:
    #         req0: Dict = {"repo": args.repo, "version": args.version, "code_file": args.code_file, "test_src": candidate_src}
    #     else:
    #         req0 = baseline_req
    #     llm_metadata0 = {
    #         "entropy": llm_result0.entropy,
    #         "avg_logprob": llm_result0.avg_logprob,
    #         "token_count": llm_result0.token_count,
    #         "input_tokens": llm_result0.input_tokens,
    #         "output_tokens": llm_result0.output_tokens,
    #         "estimated_cost": llm_result0.estimated_cost,
    #         "llm_duration_seconds": llm_duration,
    #     }
    # else:
    #     # Fall back to basic generator
    #     req0: Dict = send(gen, gen_payload, cfg)
    # Attempt 0 - Free-form initial test generation using raw code file
    
    # Attempt 0 - Free-form initial test generation using raw code file
    if llm_enabled():

        # 1. Fetch real source code from runner
        code_fetch_payload = {
            "repo": args.repo,
            "version": args.version,
            "code_file": args.code_file,
        }

        code_resp = post_runner(cfg.runner_code_url, code_fetch_payload)

        if "contents" not in code_resp:
            raise RuntimeError(f"Failed to fetch code from runner: {code_resp}")

        code_src = code_resp["contents"]
        code_src_path = out / "target_code.py"
        write_text(code_src_path, code_src)

        # 2. Build the free-form GPT prompt
        # 2. Build the free-form GPT prompt with Django-aware switching
        is_django = "django" in args.repo.lower()

        if is_django:
            test_style_instructions = """
        You MUST generate tests using Django's unittest framework.

        Strict requirements:
        - Use: from django.test import SimpleTestCase or TestCase
        - DO NOT import pytest anywhere
        - DO NOT use pytest-style asserts or fixtures
        - Use unittest assertions: self.assertEqual, self.assertTrue, self.assertRaises, etc.
        - Use unittest.mock instead of pytest.mock
        - Maximise coverage by using real filesystem:
            * use tempfile.TemporaryDirectory()
            * create real files/directories using pathlib.Path
            * exercise actual Path.exists(), Path.is_dir(), Path.stat(), Path.iterdir()
            * exercise serve(), directory_index(), and was_modified_since()
        - Test branches:
            * directory with show_indexes=True → HTML response
            * directory with show_indexes=False → Http404
            * missing file → Http404
            * valid file → FileResponse (validate headers)
            * If-Modified-Since → HttpResponseNotModified
        - Avoid Django test client; call the functions directly.
        """
        else:
            test_style_instructions = """
            You MUST generate tests using Python's built-in unittest framework.

            Strict requirements:
            - DO NOT import pytest
            - DO NOT use pytest-style asserts
            - DO NOT use fixtures or parametrize
            - Use: import unittest
            - Test classes must subclass unittest.TestCase
            - Use unittest assertions:
                * self.assertEqual
                * self.assertTrue
                * self.assertFalse
                * self.assertRaises
            - Use unittest.mock for mocking
            - Use tempfile.TemporaryDirectory() for real filesystem testing
            - Use real pathlib.Path operations, avoid mocking whenever possible
            - Maximise branch coverage and mutation score
            - Imports must match the repo's internal structure
            """

        prompt = f"""
        You are an expert Python test generator.
        Your goal is to maximise BRANCH COVERAGE and MUTATION SCORE for the target file.

        Repository: {args.repo}
        Version: {args.version}
        Target file: {args.code_file}

        Here is the full source code of the file under test:
        ----------------
        {code_src}
        ----------------

        Follow these framework rules:
        {test_style_instructions}

        Global requirements for ALL repos:
        - Maximise branch coverage
        - Use real filesystem operations where possible (tempfile.TemporaryDirectory())
        - Avoid network or database calls
        - Imports must be correct for the target repo
        - Output ONLY Python test code (no markdown, no comments, no headings)
        """

        llm_cfg = _build_llm_config()
        llm_start = time.time()

        llm_result0 = run_completion(prompt, llm_cfg)
        llm_duration = time.time() - llm_start

        total_llm_duration += llm_duration
        total_llm_cost += llm_result0.estimated_cost
        total_llm_input_tokens += llm_result0.input_tokens
        total_llm_output_tokens += llm_result0.output_tokens

        candidate_src = llm_result0.text.strip()

        # 3. Build request to runner
        req0 = {
            "repo": args.repo,
            "version": args.version,
            "code_file": args.code_file,
            "test_src": candidate_src,
        }

        llm_metadata0 = {
            "entropy": llm_result0.entropy,
            "avg_logprob": llm_result0.avg_logprob,
            "token_count": llm_result0.token_count,
            "input_tokens": llm_result0.input_tokens,
            "output_tokens": llm_result0.output_tokens,
            "estimated_cost": llm_result0.estimated_cost,
            "llm_duration_seconds": llm_duration,
        }

    else:
        # fallback to basic generator
        req0 = send(gen, gen_payload, cfg)
        llm_metadata0 = None


    write_json(out / "attempt_0.request.json", req0)
    if llm_metadata0:
        write_json(out / "attempt_0.llm_metadata.json", llm_metadata0)
    
    attempt0_path = out / "attempt_0.test_src.py"
    write_text(attempt0_path, req0["test_src"])


    
    static_start = time.time()
    static0 = _maybe_analyze(cfg, attempt0_path, out / "attempt_0.static.json")
    static_duration = time.time() - static_start
    total_static_duration += static_duration

    pre_reliability0 = score_pre_execution(llm_result0, static0)
    write_json(out / "attempt_0.pre_reliability.json", pre_reliability0)

    runner_start = time.time()
    resp0: Dict = post_runner(cfg.runner_url, req0)
    runner_duration = time.time() - runner_start
    total_runner_duration += runner_duration
    write_json(out / "attempt_0.response.json", resp0)

    post_reliability0 = score_post_execution(
        pre_reliability0, resp0, target_cov, target_mutation
    )
    write_json(out / "attempt_0.post_reliability.json", post_reliability0)

    sup_payload = dict(resp0)
    sup_payload["target_coverage"] = target_cov
    sup_payload["target_mutation"] = target_mutation
    if static0:
        sup_payload["static_metrics"] = static0
    sup_payload["pre_reliability"] = pre_reliability0 or {}
    sup_payload["post_reliability"] = post_reliability0 or {}
    critique0: Dict = send(sup, sup_payload, cfg)

    # Track supervisor LLM metadata if available
    supervisor_llm_metadata = critique0.get("llm_supervisor_metadata")
    if supervisor_llm_metadata:
        total_llm_cost += supervisor_llm_metadata.get("estimated_cost", 0.0)
        total_llm_input_tokens += supervisor_llm_metadata.get("input_tokens", 0)
        total_llm_output_tokens += supervisor_llm_metadata.get("output_tokens", 0)
        write_json(out / "attempt_0.supervisor_llm_metadata.json", supervisor_llm_metadata)

    cov = max(_as_float(resp0.get("coverage", 0.0), 0.0), 0.0)
    mutation_score = _as_float(resp0.get("mutation_score", -1.0), -1.0)
    critique0, last_cov, last_mut, stagnation = _update_progress(
        critique0, cov, mutation_score, last_cov, last_mut, stagnation
    )
    write_json(out / "attempt_0.critique.json", critique0)

    attempt0_metrics = {
        "attempt": 0,
        "runner_duration_seconds": runner_duration,
        "static_analysis_duration_seconds": static_duration,
    }
    if llm_metadata0:
        attempt0_metrics["llm_duration_seconds"] = llm_metadata0.get("llm_duration_seconds", 0.0)
        attempt0_metrics["llm_cost"] = llm_metadata0.get("estimated_cost", 0.0)
        attempt0_metrics["llm_input_tokens"] = llm_metadata0.get("input_tokens", 0)
        attempt0_metrics["llm_output_tokens"] = llm_metadata0.get("output_tokens", 0)
    write_json(out / "attempt_0.metrics.json", attempt0_metrics)

    append_event(events_log, f"run={run_id} attempt=0 state=RUN status={resp0['status']} cov={cov:.2f}")

    if cov >= target_cov:
        append_event(events_log, f"run={run_id} finish reason=coverage-met")
        print(f"[{run_id}] coverage={cov:.2f}% target met in attempt 0")
        run_duration = time.time() - run_start_time
        _write_run_summary(out, run_id, max_iters, total_llm_cost, total_llm_input_tokens, 
                          total_llm_output_tokens, total_llm_duration, total_runner_duration, 
                          total_static_duration, run_duration)
        return

    # Iterate
    current_src = req0["test_src"]
    for k in range(1, max_iters + 1):
        route = decide(critique0, k - 1, max_iters)
        route = "ENHANCE"

        if route != "ENHANCE":
            append_event(events_log, f"run={run_id} finish reason=router-finish iter={k-1}")
            break

        enh_payload: Dict = {
            "current_test_src": current_src,
            "instructions": critique0.get("instructions", []),
            "missing_lines": critique0.get("missing_lines", []),
            "context": {"repo": args.repo, "version": args.version, "code_file": args.code_file},
        }
        enh_start = time.time()
        enh_res: Dict = send(enh, enh_payload, cfg)
        enh_duration = time.time() - enh_start
        total_llm_duration += enh_duration
        
        next_src = str(enh_res["revised_test_src"])
        attempt_path = out / f"attempt_{k}.test_src.py"
        write_text(attempt_path, next_src)
        
        llm_metadata = enh_res.get("llm_metadata")
        if llm_metadata:
            total_llm_cost += llm_metadata.get("estimated_cost", 0.0)
            total_llm_input_tokens += llm_metadata.get("input_tokens", 0)
            total_llm_output_tokens += llm_metadata.get("output_tokens", 0)
            write_json(out / f"attempt_{k}.llm_metadata.json", llm_metadata)
        
        static_start = time.time()
        static_metrics = _maybe_analyze(cfg, attempt_path, out / f"attempt_{k}.static.json")
        static_duration = time.time() - static_start
        total_static_duration += static_duration

        pre_reliability = score_pre_execution(None, static_metrics)
        if llm_metadata:
            from src.llm.provider import LLMResult
            llm_result = LLMResult(
                text="",
                token_logprobs=None,
                entropy=llm_metadata.get("entropy"),
                avg_logprob=llm_metadata.get("avg_logprob"),
                token_count=llm_metadata.get("token_count", 0),
                input_tokens=llm_metadata.get("input_tokens", 0),
                output_tokens=llm_metadata.get("output_tokens", 0),
                estimated_cost=llm_metadata.get("estimated_cost", 0.0),
            )
            pre_reliability = score_pre_execution(llm_result, static_metrics)
        write_json(out / f"attempt_{k}.pre_reliability.json", pre_reliability)

        next_req = {"repo": args.repo, "version": args.version, "code_file": args.code_file, "test_src": next_src}
        write_json(out / f"attempt_{k}.request.json", next_req)

        runner_start = time.time()
        resp = post_runner(cfg.runner_url, next_req)
        runner_duration = time.time() - runner_start
        total_runner_duration += runner_duration
        write_json(out / f"attempt_{k}.response.json", resp)

        post_reliability = score_post_execution(
            pre_reliability, resp, target_cov, target_mutation
        )
        write_json(out / f"attempt_{k}.post_reliability.json", post_reliability)

        cov = max(_as_float(resp.get("coverage", 0.0), 0.0), 0.0)
        mutation = _as_float(resp.get("mutation_score", -1.0), -1.0)
        append_event(events_log, f"run={run_id} attempt={k} state=RUN status={resp['status']} cov={cov:.2f}")
        if cov >= target_cov:
            print(f"[{run_id}] coverage={cov:.2f}% target met in attempt {k}")
            append_event(events_log, f"run={run_id} finish reason=coverage-met iter={k}")
            run_duration = time.time() - run_start_time
            _write_run_summary(out, run_id, k + 1, total_llm_cost, total_llm_input_tokens,
                              total_llm_output_tokens, total_llm_duration, total_runner_duration,
                              total_static_duration, run_duration)
            break

        sup_payload = dict(resp)
        sup_payload["target_coverage"] = target_cov
        sup_payload["target_mutation"] = target_mutation
        if static_metrics:
            sup_payload["static_metrics"] = static_metrics
        sup_payload["pre_reliability"] = pre_reliability or {}
        sup_payload["post_reliability"] = post_reliability or {}
        critique0 = send(sup, sup_payload, cfg)
        
        # Track supervisor LLM metadata if available
        supervisor_llm_metadata = critique0.get("llm_supervisor_metadata")
        if supervisor_llm_metadata:
            total_llm_cost += supervisor_llm_metadata.get("estimated_cost", 0.0)
            total_llm_input_tokens += supervisor_llm_metadata.get("input_tokens", 0)
            total_llm_output_tokens += supervisor_llm_metadata.get("output_tokens", 0)
            write_json(out / f"attempt_{k}.supervisor_llm_metadata.json", supervisor_llm_metadata)
        
        critique0, last_cov, last_mut, stagnation = _update_progress(
            critique0, cov, mutation, last_cov, last_mut, stagnation
        )
        write_json(out / f"attempt_{k}.critique.json", critique0)
        
        attempt_metrics = {
            "attempt": k,
            "enhancer_duration_seconds": enh_duration,
            "runner_duration_seconds": runner_duration,
            "static_analysis_duration_seconds": static_duration,
        }
        if llm_metadata:
            attempt_metrics["llm_duration_seconds"] = llm_metadata.get("llm_duration_seconds", 0.0)
            attempt_metrics["llm_cost"] = llm_metadata.get("estimated_cost", 0.0)
            attempt_metrics["llm_input_tokens"] = llm_metadata.get("input_tokens", 0)
            attempt_metrics["llm_output_tokens"] = llm_metadata.get("output_tokens", 0)
        write_json(out / f"attempt_{k}.metrics.json", attempt_metrics)
        
        current_src = next_src

    run_duration = time.time() - run_start_time
    _write_run_summary(out, run_id, max_iters + 1, total_llm_cost, total_llm_input_tokens,
                      total_llm_output_tokens, total_llm_duration, total_runner_duration,
                      total_static_duration, run_duration)
    print(f"[{run_id}] Run complete: total_cost=${total_llm_cost:.6f} total_duration={run_duration:.2f}s")


if __name__ == "__main__":
    main()
