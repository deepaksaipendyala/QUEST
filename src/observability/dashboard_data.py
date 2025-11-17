from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

RUNS_ROOT = Path(os.getenv("TESTGENEVAL_RUNS_DIR", "artifacts/runs")).resolve()


def _safe_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None


def _safe_text(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _trim_response(payload: Optional[Dict[str, Any]], max_chars: int = 2000) -> Optional[Dict[str, Any]]:
    if payload is None:
        return None
    trimmed = dict(payload)
    stdout = trimmed.pop("stdout", None)
    if isinstance(stdout, str):
        if len(stdout) > max_chars:
            trimmed["stdout_preview"] = stdout[:max_chars] + "\n... (truncated)"
        else:
            trimmed["stdout_preview"] = stdout
    return trimmed


def _infer_timestamp(run_id: str, default_ts: float) -> float:
    parts = run_id.split("_")
    if len(parts) >= 2:
        try:
            return int(parts[1]) / 1000.0
        except ValueError:
            return default_ts
    return default_ts


def _format_ts(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def detect_run_type(run_path: Path) -> str:
    if any(child.is_dir() and child.name.startswith("iter_") for child in run_path.iterdir()):
        return "pipeline"
    attempt_files = list(run_path.glob("attempt_*.request.json"))
    if attempt_files:
        return "orchestrator"
    return "unknown"


def _list_pipeline_dirs(run_path: Path) -> List[Path]:
    return sorted(
        [child for child in run_path.iterdir() if child.is_dir() and child.name.startswith("iter_")]
    )


def _list_orchestrator_attempts(run_path: Path) -> List[int]:
    indices: List[int] = []
    seen = set()
    for file in run_path.glob("attempt_*.*"):
        name = file.name  # e.g., attempt_0.request.json or attempt_0.test_src.py
        match = re.match(r"attempt_(\d+)", name)
        if match:
            value = int(match.group(1))
            if value not in seen:
                seen.add(value)
                indices.append(value)
    return sorted(indices)


def _infer_last_stage(
    run_path: Path, run_type: str
) -> Tuple[Optional[str], Optional[Dict[str, Any]], Optional[float]]:
    if run_type == "pipeline":
        dirs = _list_pipeline_dirs(run_path)
        if not dirs:
            return None, None, None
        last_dir = dirs[-1]
        response = _safe_json(last_dir / "response.json")
        return last_dir.name, response, (last_dir / "response.json").stat().st_mtime if (last_dir / "response.json").exists() else last_dir.stat().st_mtime
    if run_type == "orchestrator":
        attempts = _list_orchestrator_attempts(run_path)
        if not attempts:
            return None, None, None
        idx = attempts[-1]
        resp_path = run_path / f"attempt_{idx}.response.json"
        response = _safe_json(resp_path)
        ts = resp_path.stat().st_mtime if resp_path.exists() else run_path.stat().st_mtime
        return f"attempt_{idx}", response, ts
    return None, None, None


def _lint_from_sources(*sources: Optional[Dict[str, Any]]) -> Optional[int]:
    for source in sources:
        if not isinstance(source, dict):
            continue
        lint_block = source.get("lint")
        if isinstance(lint_block, dict) and "issues" in lint_block:
            try:
                return int(lint_block.get("issues", 0))
            except (ValueError, TypeError):
                return None
        if "lint_issue_count" in source:
            try:
                return int(source["lint_issue_count"])
            except (ValueError, TypeError):
                return None
    return None


def _best_metrics(run_path: Path, run_type: str, coverage: Optional[float], mutation: Optional[float]) -> Tuple[Optional[float], Optional[float]]:
    best_cov = coverage
    best_mut = mutation
    if run_type == "pipeline":
        for stage_dir in _list_pipeline_dirs(run_path):
            resp = _safe_json(stage_dir / "response.json")
            if not resp:
                continue
            cov = _to_float(resp.get("coverage"))
            mut = _to_float(resp.get("mutation_score"))
            if cov is not None and cov >= 0 and (best_cov is None or cov > best_cov):
                best_cov = cov
            if mut is not None and mut >= 0 and (best_mut is None or mut > best_mut):
                best_mut = mut
    elif run_type == "orchestrator":
        for idx in _list_orchestrator_attempts(run_path):
            resp = _safe_json(run_path / f"attempt_{idx}.response.json")
            if not resp:
                continue
            cov = _to_float(resp.get("coverage"))
            mut = _to_float(resp.get("mutation_score"))
            if cov is not None and cov >= 0 and (best_cov is None or cov > best_cov):
                best_cov = cov
            if mut is not None and mut >= 0 and (best_mut is None or mut > best_mut):
                best_mut = mut
    return best_cov, best_mut


def get_run_summaries(limit: int = 30) -> List[Dict[str, Any]]:
    if not RUNS_ROOT.exists():
        return []
    candidates = [p for p in RUNS_ROOT.iterdir() if p.is_dir()]
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    summaries: List[Dict[str, Any]] = []
    for path in candidates[:limit]:
        run_type = detect_run_type(path)
        last_stage, response, last_ts = _infer_last_stage(path, run_type)
        created_ts = _infer_timestamp(path.name, path.stat().st_mtime)

        coverage = _to_float(response.get("coverage")) if response else None
        mutation = _to_float(response.get("mutation_score")) if response else None
        coverage, mutation = _best_metrics(path, run_type, coverage, mutation)
        success = bool(response.get("success")) if isinstance(response, dict) else None
        if run_type == "pipeline" and last_stage:
            rel = _safe_json(path / last_stage / "reliability.json") or {}
            lint_issues = _lint_from_sources(rel.get("pre"), rel.get("post"))
            stage_count = len(_list_pipeline_dirs(path))
        elif run_type == "orchestrator" and last_stage:
            crit = _safe_json(path / f"{last_stage}.critique.json") or {}
            lint_issues = _lint_from_sources(crit)
            stage_count = len(_list_orchestrator_attempts(path))
        else:
            lint_issues = _lint_from_sources(response)
            stage_count = 0
        
        run_summary = _safe_json(path / "run_summary.json")
        total_cost = _to_float(run_summary.get("total_llm_cost")) if run_summary else None
        total_duration = _to_float(run_summary.get("total_duration_seconds")) if run_summary else None
        
        summary = {
            "run_id": path.name,
            "kind": run_type,
            "created_ts": created_ts,
            "created_at": _format_ts(created_ts),
            "updated_ts": last_ts or path.stat().st_mtime,
            "updated_at": _format_ts(last_ts or path.stat().st_mtime),
            "last_stage": last_stage,
            "stage_count": stage_count,
            "coverage": coverage,
            "mutation_score": mutation,
            "success": success,
            "status": response.get("status") if isinstance(response, dict) else None,
            "lint_issues": lint_issues,
            "total_cost": total_cost,
            "total_duration_seconds": total_duration,
            "path": str(path),
        }
        summaries.append(summary)
    return summaries


def _load_pipeline_iterations(run_path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for idx, stage_dir in enumerate(_list_pipeline_dirs(run_path), start=1):
        request = _safe_json(stage_dir / "request.json")
        response = _trim_response(_safe_json(stage_dir / "response.json"))
        reliability = _safe_json(stage_dir / "reliability.json") or {}
        static_metrics = _safe_json(stage_dir / "static_analysis.json") or {}
        llm_metadata = _safe_json(stage_dir / "llm_metadata.json")
        metrics = _safe_json(stage_dir / "metrics.json")
        test_src = _safe_text(stage_dir / "test_src.py")
        cov = _to_float(response.get("coverage")) if response else None
        mutation = _to_float(response.get("mutation_score")) if response else None
        lint_issues = _lint_from_sources(reliability.get("pre"), reliability.get("post"))
        record = {
            "label": stage_dir.name,
            "index": idx,
            "coverage": cov,
            "mutation_score": mutation,
            "success": bool(response.get("success")) if response and "success" in response else None,
            "status": response.get("status") if response else None,
            "lint_issues": lint_issues,
            "request": request,
            "response": response,
            "reliability": reliability,
            "static_metrics": static_metrics if static_metrics else None,
            "llm_metadata": llm_metadata,
            "metrics": metrics,
            "test_src": test_src,
            "paths": {
                "dir": str(stage_dir),
                "request": str(stage_dir / "request.json"),
                "response": str(stage_dir / "response.json"),
            },
        }
        records.append(record)
    return records


def _load_orchestrator_attempts(run_path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for idx in _list_orchestrator_attempts(run_path):
        stem = f"attempt_{idx}"
        request = _safe_json(run_path / f"{stem}.request.json")
        response = _trim_response(_safe_json(run_path / f"{stem}.response.json"))
        critique = _safe_json(run_path / f"{stem}.critique.json")
        static_metrics = _safe_json(run_path / f"{stem}.static.json")
        llm_metadata = _safe_json(run_path / f"{stem}.llm_metadata.json")
        pre_reliability = _safe_json(run_path / f"{stem}.pre_reliability.json")
        post_reliability = _safe_json(run_path / f"{stem}.post_reliability.json")
        metrics = _safe_json(run_path / f"{stem}.metrics.json")
        test_src = _safe_text(run_path / f"{stem}.test_src.py")
        cov = _to_float(response.get("coverage")) if response else None
        mutation = _to_float(response.get("mutation_score")) if response else None
        lint_issues = _lint_from_sources(critique)
        
        reliability = {}
        if pre_reliability:
            reliability["pre"] = pre_reliability
        if post_reliability:
            reliability["post"] = post_reliability
        
        record = {
            "label": stem,
            "index": idx + 1,
            "coverage": cov,
            "mutation_score": mutation,
            "success": bool(response.get("success")) if response and "success" in response else None,
            "status": response.get("status") if response else None,
            "lint_issues": lint_issues,
            "request": request,
            "response": response,
            "critique": critique,
            "static_metrics": static_metrics if static_metrics else None,
            "llm_metadata": llm_metadata,
            "reliability": reliability if reliability else None,
            "metrics": metrics,
            "test_src": test_src,
            "paths": {
                "request": str(run_path / f"{stem}.request.json"),
                "response": str(run_path / f"{stem}.response.json"),
            },
        }
        records.append(record)
    return records


def _build_history(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    history: List[Dict[str, Any]] = []
    for record in records:
        history.append(
            {
                "stage": record["label"],
                "index": record["index"],
                "coverage": record.get("coverage"),
                "mutation_score": record.get("mutation_score"),
                "lint_issues": record.get("lint_issues"),
                "status": record.get("status"),
            }
        )
    return history


def load_run_detail(run_id: str) -> Dict[str, Any]:
    run_path = RUNS_ROOT / run_id
    if not run_path.exists():
        raise FileNotFoundError(f"Run directory not found: {run_path}")
    kind = detect_run_type(run_path)
    summaries = get_run_summaries(limit=200)
    summary = next((item for item in summaries if item["run_id"] == run_id), None)
    if summary is None:
        created_ts = _infer_timestamp(run_path.name, run_path.stat().st_mtime)
        summary = {
            "run_id": run_path.name,
            "kind": kind,
            "created_ts": created_ts,
            "created_at": _format_ts(created_ts),
            "updated_ts": run_path.stat().st_mtime,
            "updated_at": _format_ts(run_path.stat().st_mtime),
        }
    if kind == "pipeline":
        records = _load_pipeline_iterations(run_path)
    elif kind == "orchestrator":
        records = _load_orchestrator_attempts(run_path)
    else:
        records = []
    events = _safe_text(run_path / "events.log")
    return {
        "summary": summary,
        "iterations": records,
        "history": _build_history(records),
        "events": events.splitlines() if events else [],
        "path": str(run_path),
    }


def gather_recent_llm_calls(limit: int = 20) -> List[Dict[str, Any]]:
    calls: List[Dict[str, Any]] = []
    if not RUNS_ROOT.exists():
        return calls
    for run_path in RUNS_ROOT.iterdir():
        if not run_path.is_dir():
            continue
        for meta_path in run_path.glob("iter_*/llm_metadata.json"):
            data = _safe_json(meta_path)
            if not data:
                continue
            stat = meta_path.stat()
            calls.append(
                {
                    "run_id": run_path.name,
                    "stage": meta_path.parent.name,
                    "entropy": data.get("entropy"),
                    "avg_logprob": data.get("avg_logprob"),
                    "token_count": data.get("token_count"),
                    "path": str(meta_path),
                    "updated_ts": stat.st_mtime,
                    "updated_at": _format_ts(stat.st_mtime),
                }
            )
    calls.sort(key=lambda item: item["updated_ts"], reverse=True)
    return calls[:limit]

