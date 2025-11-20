"""Summarize best coverage/mutation scores per target.

Scans the artifacts/runs directory (by default) and prints the highest coverage
and mutation score achieved for every unique repo/version/code_file triple.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


@dataclass
class TargetKey:
    repo: str
    version: str
    code_file: str

    def label(self) -> str:
        return f"{self.repo}@{self.version} :: {self.code_file}"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_attempts(run_dir: Path) -> Iterator[tuple[Path, Path]]:
    iter_dirs = sorted(run_dir.glob("iter_*"))
    if iter_dirs:
        for iter_dir in iter_dirs:
            req = iter_dir / "request.json"
            resp = iter_dir / "response.json"
            if req.exists() and resp.exists():
                yield req, resp
    else:
        req = run_dir / "request.json"
        resp = run_dir / "response.json"
        if req.exists() and resp.exists():
            yield req, resp


def summarize_runs(runs_dir: Path) -> dict[TargetKey, dict[str, float]]:
    results: dict[TargetKey, dict[str, float]] = {}

    for run_dir in sorted(runs_dir.iterdir()):
        if not run_dir.is_dir():
            continue

        for req_path, resp_path in _iter_attempts(run_dir):
            req = _read_json(req_path)
            resp = _read_json(resp_path)

            key = TargetKey(
                repo=req.get("repo", "<unknown>"),
                version=str(req.get("version", "<unknown>")),
                code_file=req.get("code_file", "<unknown>"),
            )

            entry = results.setdefault(
                key,
                {
                    "best_coverage": float("-inf"),
                    "best_mutation": float("-inf"),
                    "runs": 0,
                },
            )

            cov_raw = resp.get("coverage", -1)
            cov = float(cov_raw) if isinstance(cov_raw, (int, float)) else -1.0
            mut_raw = resp.get("mutation_score", -1)
            mutation = float(mut_raw) if isinstance(mut_raw, (int, float)) else -1.0

            entry["best_coverage"] = max(entry["best_coverage"], cov)
            entry["best_mutation"] = max(entry["best_mutation"], mutation)
            entry["runs"] += 1

    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Summarize best coverage/mutation per target."
    )
    parser.add_argument(
        "--runs-dir",
        default="artifacts/runs",
        help="Directory containing run_* folders (default: artifacts/runs)",
    )
    args = parser.parse_args()

    runs_dir = Path(args.runs_dir)
    if not runs_dir.exists():
        raise SystemExit(f"No such directory: {runs_dir}")

    results = summarize_runs(runs_dir)
    if not results:
        print("No runs found.")
        return

    header = f"{'Target':70}  {'Best Cov':>8}  {'Best Mut':>8}  {'Attempts':>9}"
    print(header)
    print("-" * len(header))
    for key, metrics in sorted(results.items(), key=lambda x: x[0].label()):
        cov = metrics["best_coverage"]
        mut = metrics["best_mutation"]
        runs = metrics["runs"]
        cov_display = f"{cov:6.2f}" if cov >= 0 else "  N/A "
        mut_display = f"{mut:6.2f}" if mut >= 0 else "  N/A "
        print(f"{key.label():70}  {cov_display}  {mut_display}  {runs:9d}")


if __name__ == "__main__":  # pragma: no cover
    main()
