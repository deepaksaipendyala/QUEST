"""Run the orchestrator against every row in a TestGenEval dataset split.

This reads the locally cloned Hugging Face dataset (e.g., external/testgeneval),
extracts repo/version/code_file triples, and sequentially launches
``python -m src.orchestrator.engine`` for each instance.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

try:
    from datasets import load_dataset, load_from_disk
except ImportError as exc:  # pragma: no cover - load failure is fatal
    raise SystemExit(
        "Missing dependency: datasets. Install it with `pip install datasets`."
    ) from exc


def _coerce_str(value: Any) -> str:
    if isinstance(value, str):
        return value
    return str(value)


def _slice_iterable(items: Iterable[Any], start: int, limit: int | None) -> Iterable[Any]:
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


def _load_dataset_dict(dataset_path: Path):
    dataset_dict_json = dataset_path / "dataset_dict.json"
    if dataset_dict_json.exists():
        return load_from_disk(str(dataset_path))

    data_dir = dataset_path / "data"
    if not data_dir.exists():
        raise FileNotFoundError(
            f"Path {dataset_path} is not a saved dataset (missing dataset_dict.json "
            "and data/)."
        )

    split_patterns = {
        "train": "train-*.parquet",
        "validation": "dev-*.parquet",
        "test": "test-*.parquet",
    }
    data_files: dict[str, list[str]] = {}
    for split_name, pattern in split_patterns.items():
        matches = sorted(data_dir.glob(pattern))
        if matches:
            data_files[split_name] = [str(match) for match in matches]

    if not data_files:
        raise FileNotFoundError(
            f"No parquet shards found under {data_dir}. Expected files like "
            "'test-00000-of-00001.parquet'."
        )

    return load_dataset("parquet", data_files=data_files)


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch runner for TestGenEval dataset.")
    parser.add_argument(
        "--dataset",
        default="external/testgeneval",
        help="Path to the local dataset clone (default: external/testgeneval).",
    )
    parser.add_argument(
        "--split",
        default="test",
        help="Dataset split to iterate (default: test).",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=0,
        help="Zero-based index to start from (useful for resuming).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of rows to process (default: all remaining).",
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
        help="Only print the commands without executing them.",
    )
    parser.add_argument(
        "--repo-col",
        default="repo",
        help="Dataset column containing the repo slug (default: repo).",
    )
    parser.add_argument(
        "--version-col",
        default="version",
        help="Dataset column containing the version/tag (default: version).",
    )
    parser.add_argument(
        "--code-col",
        default="code_file",
        help="Dataset column containing the code file path (default: code_file).",
    )
    parser.add_argument(
        "--id-col",
        default="instance_id",
        help="Dataset column used for logging progress (default: instance_id).",
    )
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        raise SystemExit(f"Dataset path not found: {dataset_path}")

    ds = _load_dataset_dict(dataset_path)
    if args.split not in ds:
        raise SystemExit(f"Split '{args.split}' not found. Available: {list(ds.keys())}")
    split = ds[args.split]

    print(
        f"Loaded split '{args.split}' with {len(split)} rows "
        f"(start={args.start}, limit={args.limit or 'all'})."
    )

    failures = 0
    total = 0
    for row in _slice_iterable(split, args.start, args.limit):
        repo = row[args.repo_col]
        version = row[args.version_col]
        code_file = row[args.code_col]
        instance_id = row.get(args.id_col, "<unknown>")

        cmd = [
            sys.executable,
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
        print(f"\n>>> [{total}] instance={instance_id} repo={repo} version={version}")
        print(" ".join(cmd))

        if args.dry_run:
            continue

        proc = subprocess.run(cmd, check=False)
        if proc.returncode != 0:
            failures += 1
            print(
                f"[warn] Orchestrator failed for instance {instance_id} "
                f"(repo={repo}, version={version}).",
                file=sys.stderr,
            )

    print(f"\nCompleted {total} run(s). Failures: {failures}.")
    if failures:
        raise SystemExit(failures)


if __name__ == "__main__":  # pragma: no cover
    main()
