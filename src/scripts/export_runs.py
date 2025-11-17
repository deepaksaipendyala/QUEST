from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List

import sys

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from src.observability.dashboard_data import get_run_summaries, load_run_detail  # noqa: E402


def export_summaries_csv(output_path: Path, limit: int = 100) -> None:
    summaries = get_run_summaries(limit=limit)
    if not summaries:
        print("No runs found to export.")
        return

    fieldnames = [
        "run_id",
        "kind",
        "created_at",
        "updated_at",
        "stage_count",
        "coverage",
        "mutation_score",
        "total_cost",
        "total_duration_seconds",
        "success",
        "status",
        "lint_issues",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for summary in summaries:
            row = {field: summary.get(field) for field in fieldnames}
            writer.writerow(row)

    print(f"Exported {len(summaries)} run summaries to {output_path}")


def export_summaries_json(output_path: Path, limit: int = 100) -> None:
    summaries = get_run_summaries(limit=limit)
    if not summaries:
        print("No runs found to export.")
        return

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(summaries, f, indent=2)

    print(f"Exported {len(summaries)} run summaries to {output_path}")


def export_run_detail_json(run_id: str, output_path: Path) -> None:
    try:
        detail = load_run_detail(run_id)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(detail, f, indent=2)

    print(f"Exported run detail for {run_id} to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export run summaries and details")
    parser.add_argument("--format", choices=["csv", "json"], default="csv", help="Output format")
    parser.add_argument("--output", type=Path, required=True, help="Output file path")
    parser.add_argument("--limit", type=int, default=100, help="Maximum number of runs to export")
    parser.add_argument("--run-id", type=str, help="Export detailed data for a specific run ID")
    args = parser.parse_args()

    if args.run_id:
        if args.format != "json":
            print("Warning: Detailed run export only supports JSON format. Switching to JSON.")
        export_run_detail_json(args.run_id, args.output)
    else:
        if args.format == "csv":
            export_summaries_csv(args.output, args.limit)
        else:
            export_summaries_json(args.output, args.limit)


if __name__ == "__main__":
    main()

