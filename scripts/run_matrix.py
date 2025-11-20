"""Batch runner for TestGenFlow pipeline.

Reads a YAML or JSON manifest describing repo/version/code_file triples and
invokes ``python -m src.pipeline.iterate`` for each item. This lets you sweep
across every SWE-bench repo (or any subset) without manually launching runs.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml
except ImportError as exc:  # pragma: no cover - handled in CLI output
    raise SystemExit(
        "Missing dependency: pyyaml. Install it via `pip install pyyaml`."
    ) from exc


def _load_manifest(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found: {path}")

    with path.open("r", encoding="utf-8") as fh:
        text = fh.read()

    if path.suffix in {".json", ".jsonl"}:
        data = json.loads(text)
    else:
        data = yaml.safe_load(text)

    if isinstance(data, dict):
        items = data.get("targets") or data.get("matrix")
        if not isinstance(items, Iterable):
            raise ValueError(
                "Manifest dictionaries must contain a 'targets' (or 'matrix') list."
            )
        entries = list(items)
    elif isinstance(data, list):
        entries = data
    else:
        raise ValueError("Manifest must be a list or dict of targets.")

    parsed: list[dict[str, Any]] = []
    for idx, raw in enumerate(entries):
        if not isinstance(raw, dict):
            raise ValueError(f"Entry {idx} must be a mapping, got {type(raw)}.")
        missing = [key for key in ("repo", "version", "code_file") if key not in raw]
        if missing:
            raise ValueError(f"Entry {idx} missing required fields: {missing}")
        parsed.append(raw)
    return parsed


def _run_single(entry: dict[str, Any], dry_run: bool) -> int:
    repo = entry["repo"]
    version = str(entry["version"])
    code_file = entry["code_file"]
    max_iters = entry.get("max_iters")

    cmd = [
        sys.executable,
        "-m",
        "src.pipeline.iterate",
        "--repo",
        repo,
        "--version",
        version,
        "--code-file",
        code_file,
    ]
    if isinstance(max_iters, int) and max_iters > 0:
        cmd.extend(["--max-iters", str(max_iters)])

    print(f"\n>>> Running {repo}@{version} ({code_file})")
    print(" ".join(cmd))

    if dry_run:
        return 0

    proc = subprocess.run(cmd, check=False)
    if proc.returncode != 0:
        print(f"[warn] Run failed for {repo}@{version}", file=sys.stderr)
    return proc.returncode


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch runner for repo/version matrix.")
    parser.add_argument(
        "--manifest",
        required=True,
        help="Path to YAML/JSON manifest describing targets to run.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print the commands that would be executed.",
    )
    args = parser.parse_args()

    entries = _load_manifest(Path(args.manifest))
    failures = 0
    for entry in entries:
        rc = _run_single(entry, args.dry_run)
        if rc != 0:
            failures += 1

    if failures:
        raise SystemExit(f"{failures} run(s) failed")


if __name__ == "__main__":  # pragma: no cover
    main()
