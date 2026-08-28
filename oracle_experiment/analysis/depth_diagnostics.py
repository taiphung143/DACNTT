"""Print a depth-level diagnostic table from sample JSON/JSONL records."""

from __future__ import annotations

import argparse
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from analysis.summarize import summarize_sample_group
from logging_utils import read_json_records


def summarize_by_depth(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for record in records:
        groups[int(record["L"])].append(record)
    return [
        {"L": length, **summarize_sample_group(samples)}
        for length, samples in sorted(groups.items())
    ]


def print_depth_table(rows: Sequence[Mapping[str, Any]]) -> None:
    print(
        "| L | Final Accuracy | Reasoning Solved | During-think Trunc. | "
        "After-think Trunc. | Avg Tokens | Avg Utilization |"
    )
    print("|---:|---:|---:|---:|---:|---:|---:|")
    for row in rows:
        def metric(name: str) -> str:
            value = row.get(name)
            return "N/A" if value is None else f"{float(value):.4f}"

        print(
            f"| {row['L']} | {metric('final_accuracy')} | "
            f"{metric('reasoning_solved_rate')} | "
            f"{metric('during_thinking_truncation_rate')} | "
            f"{metric('after_thinking_truncation_rate')} | "
            f"{metric('avg_generated_tokens')} | "
            f"{metric('avg_token_budget_utilization')} |"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    print_depth_table(summarize_by_depth(read_json_records(args.input)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
