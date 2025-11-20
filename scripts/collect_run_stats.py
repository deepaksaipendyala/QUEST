"""Aggregate orchestrator attempt artifacts into CSVs and coverage plots.

For each run directory under ``artifacts/runs/run_*`` the script collects data
from every ``attempt_X.*`` file (request, response, critique, static, etc.),
builds an attempt-level table, a run-level summary with max coverage, and
optionally renders a coverage bar chart.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import matplotlib.pyplot as plt

try:
    from datasets import load_dataset
except ImportError:  # pragma: no cover - dataset join optional
    load_dataset = None  # type: ignore[assignment]


ATTEMPT_RE = re.compile(r"attempt_(\d+)\.request\.json$")


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        try:
            return json.load(handle)
        except json.JSONDecodeError:
            return None


def _attempt_records(run_dir: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for request_path in sorted(run_dir.glob("attempt_*.request.json")):
        match = ATTEMPT_RE.match(request_path.name)
        if not match:
            continue
        attempt_idx = int(match.group(1))
        prefix = f"attempt_{attempt_idx}"
        response = _load_json(run_dir / f"{prefix}.response.json") or {}
        critique = _load_json(run_dir / f"{prefix}.critique.json") or {}
        llm_metadata = _load_json(run_dir / f"{prefix}.llm_metadata.json") or {}
        metrics = _load_json(run_dir / f"{prefix}.metrics.json") or {}
        pre_rel = _load_json(run_dir / f"{prefix}.pre_reliability.json") or {}
        post_rel = _load_json(run_dir / f"{prefix}.post_reliability.json") or {}
        static_metrics = _load_json(run_dir / f"{prefix}.static.json") or {}
        request = _load_json(request_path) or {}

        record: Dict[str, Any] = {
            "run_id": run_dir.name,
            "attempt": attempt_idx,
            "repo": request.get("repo"),
            "version": request.get("version"),
            "code_file": request.get("code_file"),
            "coverage": response.get("coverage"),
            "mutation_score": response.get("mutation_score"),
            "runner_status": response.get("status"),
            "runner_success": response.get("success"),
            "runner_exit_code": response.get("exitCode"),
            "runner_stdout": response.get("stdout"),
            "runner_stderr": response.get("stderr"),
            "llm_entropy": llm_metadata.get("entropy"),
            "llm_avg_logprob": llm_metadata.get("avg_logprob"),
            "llm_token_count": llm_metadata.get("token_count"),
            "llm_input_tokens": llm_metadata.get("input_tokens"),
            "llm_output_tokens": llm_metadata.get("output_tokens"),
            "llm_estimated_cost": llm_metadata.get("estimated_cost"),
            "enhancer_duration_seconds": metrics.get("enhancer_duration_seconds"),
            "runner_duration_seconds": metrics.get("runner_duration_seconds"),
            "static_analysis_duration_seconds": metrics.get(
                "static_analysis_duration_seconds"
            ),
            "pre_reliability": pre_rel,
            "post_reliability": post_rel,
            "static_metrics": static_metrics,
            "critique": critique,
            "instructions": critique.get("instructions") if critique else None,
            "missing_lines": critique.get("missing_lines") if critique else None,
            "test_src_path": str(run_dir / f"{prefix}.test_src.py"),
        }
        records.append(record)
    return records


def _summarize_runs(
    run_dirs: List[Path], baseline_lookup: Dict[Tuple[str, str, str], Dict[str, Any]]
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    attempt_records: List[Dict[str, Any]] = []
    run_records: List[Dict[str, Any]] = []

    for run_dir in run_dirs:
        attempts = _attempt_records(run_dir)
        if not attempts:
            continue
        attempt_records.extend(attempts)

        repo = attempts[0].get("repo")
        version = attempts[0].get("version")
        code_file = attempts[0].get("code_file")
        baseline = baseline_lookup.get((str(repo), str(version), str(code_file)), {})
        coverages = [
            float(a["coverage"])
            for a in attempts
            if isinstance(a.get("coverage"), (int, float))
        ]
        max_cov = max(coverages) if coverages else None
        mutations = [
            float(a["mutation_score"])
            for a in attempts
            if isinstance(a.get("mutation_score"), (int, float))
        ]
        max_mut = max(mutations) if mutations else None
        summary_json = _load_json(run_dir / "run_summary.json") or {}

        run_record = {
            "run_id": run_dir.name,
            "repo": repo,
            "version": version,
            "code_file": code_file,
            "attempt_count": len(attempts),
            "max_coverage": max_cov,
            "max_mutation_score": max_mut,
            "total_duration_seconds": summary_json.get("total_duration_seconds"),
            "iterations_recorded": summary_json.get("iterations"),
            "total_llm_cost": summary_json.get("total_llm_cost"),
            "total_llm_input_tokens": summary_json.get("total_llm_input_tokens"),
            "total_llm_output_tokens": summary_json.get("total_llm_output_tokens"),
            "total_runner_duration_seconds": summary_json.get(
                "total_runner_duration_seconds"
            ),
            "total_static_duration_seconds": summary_json.get(
                "total_static_analysis_duration_seconds"
            ),
            "baseline_first": baseline.get("first"),
            "baseline_last": baseline.get("last"),
            "baseline_last_minus_one": baseline.get("last_minus_one"),
        }
        run_records.append(run_record)

        for attempt in attempts:
            attempt["baseline_first"] = baseline.get("first")
            attempt["baseline_last"] = baseline.get("last")
            attempt["baseline_last_minus_one"] = baseline.get("last_minus_one")

    return attempt_records, run_records


def _save_dataframe(records: List[Dict[str, Any]], path: Path) -> pd.DataFrame:
    df = pd.DataFrame.from_records(records)
    df.to_csv(path, index=False)
    return df


def _plot_coverage(run_df: pd.DataFrame, output_path: Path, title: str) -> None:
    subset = run_df.dropna(subset=["max_coverage"]).sort_values("max_coverage", ascending=False)
    if subset.empty:
        print("No coverage data available for plotting.")
        return
    plt.figure(figsize=(12, 0.4 * len(subset) + 2))
    plt.barh(subset["run_id"], subset["max_coverage"], color="#5B8DEF")
    plt.xlabel("Coverage (%)")
    plt.ylabel("Run ID")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect orchestrator run statistics.")
    parser.add_argument(
        "--runs-dir",
        default="artifacts/runs",
        help="Directory containing run_* folders (default: artifacts/runs).",
    )
    parser.add_argument(
        "--attempt-csv",
        default="artifacts/attempt_stats.csv",
        help="Output CSV path for attempt-level data.",
    )
    parser.add_argument(
        "--run-csv",
        default="artifacts/run_summary_stats.csv",
        help="Output CSV path for run-level summaries.",
    )
    parser.add_argument(
        "--coverage-plot",
        default="artifacts/run_coverage.png",
        help="Output PNG path for run-level max coverage plot.",
    )
    parser.add_argument(
        "--plot-title",
        default="Max Coverage per Run",
        help="Custom title for the coverage plot.",
    )
    parser.add_argument(
        "--dataset",
        default=None,
        help="Optional Hugging Face dataset identifier to pull baseline coverage values.",
    )
    parser.add_argument(
        "--split",
        default="test",
        help="Dataset split to read when --dataset is provided (default: test).",
    )
    parser.add_argument(
        "--repo-col",
        default="repo",
        help="Dataset column name containing repo slug (default: repo).",
    )
    parser.add_argument(
        "--version-col",
        default="version",
        help="Dataset column for repo tag/version (default: version).",
    )
    parser.add_argument(
        "--code-col",
        default="code_file",
        help="Dataset column containing target file path (default: code_file).",
    )
    parser.add_argument(
        "--baseline-col",
        default="baseline_covs",
        help="Dataset column containing baseline coverage dict (default: baseline_covs).",
    )
    args = parser.parse_args()

    runs_dir = Path(args.runs_dir)
    run_dirs = sorted([p for p in runs_dir.iterdir() if p.is_dir()])
    if not run_dirs:
        raise SystemExit(f"No run directories found under {runs_dir}")

    baseline_lookup: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    if args.dataset:
        if load_dataset is None:
            raise SystemExit("datasets package missing; install `pip install datasets`.")
        print(f"Loading dataset {args.dataset!r} (split={args.split!r}) for baselines...")
        ds = load_dataset(args.dataset, split=args.split)
        for row in ds:
            repo = str(row[args.repo_col])
            version = str(row[args.version_col])
            code_file = str(row[args.code_col])
            baseline_covs = row.get(args.baseline_col) or {}
            if isinstance(baseline_covs, dict):
                baseline_lookup[(repo, version, code_file)] = {
                    "first": baseline_covs.get("first"),
                    "last": baseline_covs.get("last"),
                    "last_minus_one": baseline_covs.get("last_minus_one"),
                }

    attempt_records, run_records = _summarize_runs(run_dirs, baseline_lookup)
    if not attempt_records:
        raise SystemExit("No attempt_* artifacts found to summarize.")

    attempt_df = _save_dataframe(attempt_records, Path(args.attempt_csv))
    run_df = _save_dataframe(run_records, Path(args.run_csv))
    print(f"Wrote {len(attempt_df)} attempt rows → {args.attempt_csv}")
    print(f"Wrote {len(run_df)} run rows → {args.run_csv}")

    _plot_coverage(run_df, Path(args.coverage_plot), args.plot_title)
    print(f"Saved coverage plot → {args.coverage_plot}")


if __name__ == "__main__":  # pragma: no cover
    main()
