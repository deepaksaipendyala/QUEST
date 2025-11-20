"""Analyze run_summary_stats.csv to compare coverage against baseline."""

from __future__ import annotations

import argparse
import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Report how many runs beat baseline_first coverage."
    )
    parser.add_argument(
        "--input",
        default="artifacts/run_summary_stats.csv",
        help="Path to run_summary_stats.csv (default: artifacts/run_summary_stats.csv).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional path to save the filtered rows that beat the baseline.",
    )
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    metrics = [
        ("baseline_first", "coverage_minus_baseline_first", "beat_baseline_first"),
        ("baseline_last", "coverage_minus_baseline_last", "beat_baseline_last"),
        (
            "baseline_last_minus_one",
            "coverage_minus_baseline_last_minus_one",
            "beat_baseline_last_minus_one",
        ),
    ]

    total = len(df)
    print(f"Total runs: {total}")

    merged = df.copy()
    for baseline_col, delta_col, beat_col in metrics:
        subset = df.dropna(subset=["max_coverage", baseline_col]).copy()
        subset[delta_col] = subset["max_coverage"] - subset[baseline_col]
        subset[beat_col] = subset[delta_col] >= 0.0

        comparable = len(subset)
        beaten = int(subset[beat_col].sum())
        print(f"\nComparison vs. {baseline_col}:")
        print(f"  Runs with both coverage values: {comparable}")
        print(f"  Runs beating {baseline_col}: {beaten}")
        if comparable:
            rate = beaten / comparable * 100.0
            avg_delta = subset[delta_col].mean()
            best = subset[delta_col].max()
            worst = subset[delta_col].min()
            print(f"  Success rate: {rate:.1f}%")
            print(f"  Avg coverage delta: {avg_delta:.2f}")
            print(f"  Best delta: {best:.2f}")
            print(f"  Worst delta: {worst:.2f}")
        merged = merged.merge(
            subset[["run_id", delta_col, beat_col]],
            on="run_id",
            how="left",
            suffixes=("", "_dup"),
        )

    if args.output:
        merged.to_csv(args.output, index=False)
        print(f"Wrote comparison rows → {args.output}")


if __name__ == "__main__":  # pragma: no cover
    main()
