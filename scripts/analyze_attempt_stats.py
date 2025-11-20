"""Extract per-attempt metrics (entropy, logprobs, mutation) vs. baselines."""

from __future__ import annotations

import argparse
import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Summarize attempt-level entropy/logprobs/mutation vs. baselines."
    )
    parser.add_argument(
        "--attempt-csv",
        default="artifacts/attempt_stats.csv",
        help="Path to attempt_stats.csv (default: artifacts/attempt_stats.csv).",
    )
    parser.add_argument(
        "--output",
        default="artifacts/attempt_vs_baseline.csv",
        help="Output CSV path (default: artifacts/attempt_vs_baseline.csv).",
    )
    args = parser.parse_args()

    df = pd.read_csv(args.attempt_csv)

    cols = [
        "run_id",
        "attempt",
        "repo",
        "version",
        "code_file",
        "coverage",
        "mutation_score",
        "llm_entropy",
        "llm_avg_logprob",
        "llm_token_count",
        "llm_input_tokens",
        "llm_output_tokens",
        "llm_estimated_cost",
        "baseline_first",
        "baseline_last",
        "baseline_last_minus_one",
    ]
    available = [c for c in cols if c in df.columns]
    df_out = df[available].copy()
    df_out.to_csv(args.output, index=False)
    print(f"Wrote {len(df_out)} attempt rows → {args.output}")


if __name__ == "__main__":  # pragma: no cover
    main()

