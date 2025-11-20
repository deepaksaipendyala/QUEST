"""Run the orchestrator for every django/django row in TestGenEval Lite.

This script mirrors the manual `/code` filtering logic: it loads the
``kjain14/testgenevallite`` split via Hugging Face datasets, filters rows where
``repo == "django/django"``, and launches ``python -m src.orchestrator.engine``
for each matching triple (repo, version, code_file).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from typing import Any, Iterable

try:
    from datasets import load_dataset
except ImportError as exc:  # pragma: no cover - required dependency
    raise SystemExit(
        "Missing dependency: datasets. Install it with `pip install datasets`."
    ) from exc


def _coerce_str(value: Any) -> str:
    if isinstance(value, str):
        return value
    return str(value)


def _slice_rows(items: Iterable[Any], start: int, limit: int | None) -> Iterable[Any]:
    skipped = 0
    emitted = 0
    for item in items:
        if skipped < start:
            skipped += 1
            continue
        if limit is not None and emitted >= limit:
            break
        yield item
        emitted += 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run orchestrator for all django/django rows in a dataset split."
    )
    parser.add_argument(
        "--dataset",
        default="kjain14/testgenevallite",
        help="Hugging Face dataset identifier (default: kjain14/testgenevallite).",
    )
    parser.add_argument(
        "--split",
        default="test",
        help="Dataset split to load (default: test).",
    )
    parser.add_argument(
        "--repo",
        default="django/django",
        help="Repository slug to filter (default: django/django).",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=0,
        help="Zero-based index to start from within the filtered rows.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of filtered rows to process (default: all).",
    )
    parser.add_argument(
        "--max-iters",
        type=int,
        default=None,
        help="Optional --max-iters override passed to the orchestrator.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print the orchestrator commands instead of executing them.",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable used to invoke the orchestrator (default: current interpreter).",
    )
    parser.add_argument(
        "--repo-col",
        default="repo",
        help="Dataset column for the repo slug (default: repo).",
    )
    parser.add_argument(
        "--version-col",
        default="version",
        help="Dataset column for the repo version/tag (default: version).",
    )
    parser.add_argument(
        "--code-col",
        default="code_file",
        help="Dataset column for the target source file (default: code_file).",
    )
    parser.add_argument(
        "--id-col",
        default="instance_id",
        help="Dataset column to display progress (default: instance_id).",
    )
    args = parser.parse_args()

    print(f"Loading dataset {args.dataset!r} ({args.split} split)...")
    split = load_dataset(args.dataset, split=args.split)
    print(f"Loaded {len(split)} row(s). Filtering for repo == {args.repo!r}...")
    filtered = split.filter(lambda row: row[args.repo_col] == args.repo)
    print(
        f"Found {len(filtered)} matching rows "
        f"(start={args.start}, limit={args.limit or 'all'})."
    )

    total = 0
    failures = 0
    for row in _slice_rows(filtered, args.start, args.limit):
        repo = row[args.repo_col]
        version = row[args.version_col]
        code_file = row[args.code_col]
        instance_id = row.get(args.id_col, "<unknown>")

        cmd = [
            args.python,
            "-m",
            "src.orchestrator.engine",
            "--repo",
            _coerce_str(repo),
            "--version",
            _coerce_str(version),
            "--code-file",
            _coerce_str(code_file),
        ]
        if args.max_iters is not None and args.max_iters > 0:
            cmd.extend(["--max-iters", str(args.max_iters)])

        total += 1
        print(
            f"\n>>> [{total}] instance={instance_id} repo={repo} "
            f"version={version} code_file={code_file}"
        )
        print(" ".join(cmd))
        if args.dry_run:
            continue

        proc = subprocess.run(cmd, check=False)
        if proc.returncode != 0:
            failures += 1
            print(
                f"[warn] Orchestrator failed for instance {instance_id} "
                f"(repo={repo}, version={version}, code_file={code_file}).",
                file=sys.stderr,
            )

    print(f"\nCompleted {total} run(s). Failures: {failures}.")
    if failures:
        raise SystemExit(failures)


if __name__ == "__main__":  # pragma: no cover
    main()
