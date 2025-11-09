from __future__ import annotations
import argparse, os, pathlib
from typing import Dict
from src.core.config import load_config
from src.core.storage import new_run_id, run_dir, write_json, write_text
from src.core.sandbox_client import post_runner
from src.agents.generator import GeneratorAgent
from src.agents.supervisor import SupervisorAgent
from src.agents.enhancer import EnhancerAgent
from src.bus.inproc import send
from src.orchestrator.router import decide
from src.observability.events import append_event
from src.context.miner import mine_python_context

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
    max_iters = int(args.max_iters)

    # Context mining (forward-compat; uses local repo-root by default)
    context = mine_python_context(pathlib.Path(args.repo_root), args.code_file)
    write_json(out / "context.json", context)

    gen = GeneratorAgent()
    sup = SupervisorAgent()
    enh = EnhancerAgent()

    # Attempt 0
    gen_payload: Dict = {"repo": args.repo, "version": args.version, "code_file": args.code_file, "context": context}
    req0: Dict = send(gen, gen_payload, cfg)
    write_json(out / "attempt_0.request.json", req0)
    write_text(out / "attempt_0.test_src.py", req0["test_src"])

    resp0: Dict = post_runner(cfg.runner_url, req0)
    write_json(out / "attempt_0.response.json", resp0)

    sup_payload = dict(resp0)
    sup_payload["target_coverage"] = target_cov
    critique0: Dict = send(sup, sup_payload, cfg)
    write_json(out / "attempt_0.critique.json", critique0)

    cov_raw0 = resp0.get("coverage", 0.0)
    cov = float(cov_raw0) if isinstance(cov_raw0, (int, float, str)) and cov_raw0 != "" else 0.0
    append_event(events_log, f"run={run_id} attempt=0 state=RUN status={resp0['status']} cov={cov:.2f}")

    if cov >= target_cov:
        append_event(events_log, f"run={run_id} finish reason=coverage-met")
        print(f"[{run_id}] coverage={cov:.2f}% target met in attempt 0")
        return

    # Iterate
    current_src = req0["test_src"]
    for k in range(1, max_iters + 1):
        route = decide(critique0, k - 1, max_iters)
        if route != "ENHANCE":
            append_event(events_log, f"run={run_id} finish reason=router-finish iter={k-1}")
            break

        enh_payload: Dict = {
            "current_test_src": current_src,
            "instructions": critique0.get("instructions", []),
            "missing_lines": critique0.get("missing_lines", []),
            "context": {"repo": args.repo, "version": args.version, "code_file": args.code_file},
        }
        enh_res: Dict = send(enh, enh_payload, cfg)
        next_src = str(enh_res["revised_test_src"])
        write_text(out / f"attempt_{k}.test_src.py", next_src)

        next_req = {"repo": args.repo, "version": args.version, "code_file": args.code_file, "test_src": next_src}
        write_json(out / f"attempt_{k}.request.json", next_req)

        resp = post_runner(cfg.runner_url, next_req)
        write_json(out / f"attempt_{k}.response.json", resp)

        cov_raw = resp.get("coverage", 0.0)
        cov = float(cov_raw) if isinstance(cov_raw, (int, float, str)) and cov_raw != "" else 0.0
        append_event(events_log, f"run={run_id} attempt={k} state=RUN status={resp['status']} cov={cov:.2f}")
        if cov >= target_cov:
            print(f"[{run_id}] coverage={cov:.2f}% target met in attempt {k}")
            append_event(events_log, f"run={run_id} finish reason=coverage-met iter={k}")
            break

        sup_payload = dict(resp)
        sup_payload["target_coverage"] = target_cov
        critique0 = send(sup, sup_payload, cfg)
        write_json(out / f"attempt_{k}.critique.json", critique0)
        current_src = next_src

if __name__ == "__main__":
    main()
