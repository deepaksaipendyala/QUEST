from __future__ import annotations
import argparse
import os
import pathlib
import yaml

from src.core.config import load_config
from src.core.storage import new_run_id, run_dir, write_json, write_text
from src.core.sandbox_client import post_runner
from src.llm.generator import generate_minimal_request
from src.llm.provider import LLMConfig, run_completion


def _load_defaults() -> dict[str, object]:
    cfg_path = pathlib.Path("configs/default.yaml")
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

    if isinstance(llm_block, dict):
        provider_default = str(llm_block.get("provider", provider_default))
        model_default = str(llm_block.get("model", model_default))
        decoding = llm_block.get("decoding", {})
        if isinstance(decoding, dict):
            temperature_default = str(decoding.get("temperature", temperature_default))
            top_p_default = str(decoding.get("top_p", top_p_default))

    return LLMConfig(
        provider=os.getenv("LLM_PROVIDER", provider_default),
        model=os.getenv("LLM_MODEL", model_default),
        temperature=float(os.getenv("LLM_TEMPERATURE", temperature_default)),
        top_p=float(os.getenv("LLM_TOP_P", top_p_default)),
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

    for index in range(1, max_iters + 1):
        iteration_dir = base_dir / f"iter_{index:03d}"
        iteration_dir.mkdir(parents=True, exist_ok=True)

        request_dict = generate_minimal_request(args.repo, args.version, args.code_file)
        prompt = (
            "Generate a pytest module that exercises the target file.\n"
            f"Repository: {args.repo}\nVersion: {args.version}\nFile: {args.code_file}\n"
            "Return only valid Python test code."
        )

        candidate_src = run_completion(prompt, llm_cfg).strip()
        if candidate_src:
            request_dict["test_src"] = candidate_src

        if os.getenv("ENABLE_VALIDATION", "0") == "1":
            from src.core.schema import RunnerRequestModel  # type: ignore

            RunnerRequestModel(**request_dict)

        write_json(iteration_dir / "request.json", request_dict)
        write_text(iteration_dir / "test_src.py", request_dict["test_src"])

        resp = post_runner(app_cfg.runner_url, request_dict)

        if os.getenv("ENABLE_VALIDATION", "0") == "1":
            from src.core.schema import RunnerResponseModel  # type: ignore

            RunnerResponseModel(**resp)

        write_json(iteration_dir / "response.json", resp)

        cov = float(resp.get("coverage", 0.0))
        print(
            f"[{run_id} iter={index}] status={resp['status']} success={resp['success']} coverage={cov:.2f}%"
        )


if __name__ == "__main__":
    main()
