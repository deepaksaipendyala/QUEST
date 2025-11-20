"""Compute distribution of repos in the TestGenEval Lite dataset."""

from __future__ import annotations

import argparse
from collections import Counter

try:
    from datasets import load_dataset
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Missing dependency: datasets. Install it with `pip install datasets`."
    ) from exc


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Show distribution of repos in a Hugging Face dataset split."
    )
    parser.add_argument(
        "--dataset",
        default="kjain14/testgenevallite",
        help="Dataset identifier (default: kjain14/testgenevallite).",
    )
    parser.add_argument(
        "--split",
        default="test",
        help="Dataset split to load (default: test).",
    )
    parser.add_argument(
        "--repo-col",
        default="repo",
        help="Column name containing the repo slug (default: repo).",
    )
    parser.add_argument(
        "--output-csv",
        default=None,
        help="Optional path to save the repo distribution as CSV.",
    )
    args = parser.parse_args()

    ds = load_dataset(args.dataset, split=args.split)
    repos = ds[args.repo_col]
    counts = Counter(repos)
    total = sum(counts.values())

    print(f"Dataset: {args.dataset} (split={args.split})")
    print(f"Total rows: {total}")
    print("\nRepo distribution:")
    for repo, n in counts.most_common():
        pct = 100.0 * n / total if total else 0.0
        print(f"{repo:40s} {n:6d} rows  ({pct:5.1f}%)")

    if args.output_csv:
        import csv

        with open(args.output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["repo", "count", "percentage"])
            for repo, n in counts.most_common():
                pct = 100.0 * n / total if total else 0.0
                writer.writerow([repo, n, pct])
        print(f"\nWrote repo distribution → {args.output_csv}")


if __name__ == "__main__":  # pragma: no cover
    main()

