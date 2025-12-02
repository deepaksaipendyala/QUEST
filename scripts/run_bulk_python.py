#!/usr/bin/env python3
"""Simple bulk run script without datasets dependency.

Usage:
    python scripts/run_bulk_python.py
    python scripts/run_bulk_python.py --limit 5
    python scripts/run_bulk_python.py --max-iters 3
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from typing import List, Tuple

# Test cases: (repo, version, code_file)
TEST_CASES: List[Tuple[str, str, str]] = [
    ("django/django", "4.0", "django/db/models/query_utils.py"),
    ("django/django", "4.1", "django/views/static.py"),
    ("django/django", "4.2", "django/utils/numberformat.py"),
    ("django/django", "3.0", "django/utils/autoreload.py"),
    ("django/django", "3.1", "django/db/models/lookups.py"),
    ("django/django", "3.2", "django/db/models/base.py"),
    ("django/django", "4.0", "django/contrib/auth/forms.py"),
    ("django/django", "4.1", "django/utils/decorators.py"),
    ("django/django", "4.2", "django/core/management/base.py"),
    ("django/django", "4.0", "django/contrib/admin/sites.py"),
    ("django/django", "4.1", "django/forms/models.py"),
    ("django/django", "4.2", "django/db/migrations/serializer.py"),
    ("django/django", "3.0", "django/views/debug.py"),
    ("django/django", "3.1", "django/db/migrations/serializer.py"),
    ("django/django", "4.1", "django/template/autoreload.py"),
    ("django/django", "3.0", "django/db/models/deletion.py"),
    ("django/django", "4.2", "django/db/migrations/autodetector.py"),
    ("django/django", "4.0", "django/db/models/query_utils.py"),
    ("django/django", "4.1", "django/views/static.py"),
    ("django/django", "4.2", "django/utils/numberformat.py"),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run orchestrator for multiple test cases.")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of test cases to run (default: all).",
    )
    parser.add_argument(
        "--max-iters",
        type=int,
        default=2,
        help="Maximum iterations per run (default: 2).",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=0,
        help="Zero-based index to start from (default: 0).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print commands without executing them.",
    )
    args = parser.parse_args()

    # Set environment variable
    os.environ["LLM_SUPERVISOR"] = "true"

    test_cases = TEST_CASES[args.start :]
    if args.limit:
        test_cases = test_cases[: args.limit]

    total = len(test_cases)
    success = 0
    failures = 0

    print(f"Starting bulk run: {total} test case(s)")
    print(f"Max iterations: {args.max_iters}")
    print(f"LLM Supervisor: {os.environ.get('LLM_SUPERVISOR', 'false')}")
    print("")

    for idx, (repo, version, code_file) in enumerate(test_cases, start=1):
        print(f">>> [{idx}/{total}] repo={repo} version={version} code_file={code_file}")

        cmd = [
            sys.executable,
            "-m",
            "src.orchestrator.engine",
            "--repo",
            repo,
            "--version",
            version,
            "--code-file",
            code_file,
            "--max-iters",
            str(args.max_iters),
        ]

        print(" ".join(cmd))
        if args.dry_run:
            print("[DRY RUN] Would execute command")
            print("")
            continue

        proc = subprocess.run(cmd, check=False)
        if proc.returncode == 0:
            success += 1
            print(f"[OK] Test case {idx} completed successfully")
        else:
            failures += 1
            print(f"[FAIL] Test case {idx} failed (exit code: {proc.returncode})")
        print("")

    print("=" * 50)
    print("Bulk run completed:")
    print(f"  Total: {total}")
    print(f"  Success: {success}")
    print(f"  Failures: {failures}")
    print("=" * 50)

    if failures > 0:
        sys.exit(failures)


if __name__ == "__main__":
    main()

