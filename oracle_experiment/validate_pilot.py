"""Report strict-final accuracy and stage-aware truncation diagnostics."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from analysis.summarize import summarize_sample_group
from logging_utils import read_json_records


def build_validation_report(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    failure_counts = Counter(str(record.get("failure_type")) for record in records)
    by_length: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for record in records:
        by_length[int(record["L"])].append(record)
    overall = summarize_sample_group(records) if records else None
    report = {
        "total_samples": len(records),
        "correct": failure_counts["correct"],
        "wrong_explicit_answers": failure_counts["wrong_answer"],
        "truncated_before_answer": failure_counts["truncated_before_answer"],
        "truncated_after_reasoning": failure_counts["truncated_after_reasoning"],
        "parse_failures": failure_counts["parse_failure"],
        "empty_outputs": failure_counts["empty_response"],
        "generation_errors": failure_counts["generation_error"],
        "metrics": overall,
        "by_L": {
            str(length): summarize_sample_group(samples)
            for length, samples in sorted(by_length.items())
        },
    }
    if overall:
        # Compatibility aliases for callers of the previous validation schema.
        report["truncation_rate"] = overall["truncation_rate"]
        report["parse_failure_rate"] = overall["parse_failure_rate"]
        report["explicit_final_answer_rate"] = overall["explicit_final_response_rate"]
        report["mean_token_budget_utilization"] = overall[
            "avg_token_budget_utilization"
        ]
    return report


def _format(value: Any) -> str:
    return "N/A" if value is None else f"{float(value):.4f}"


def print_validation_report(report: Mapping[str, Any]) -> None:
    for label, key in (
        ("Total samples", "total_samples"),
        ("Correct final answers", "correct"),
        ("Wrong explicit final answers", "wrong_explicit_answers"),
        ("Truncated before answer", "truncated_before_answer"),
        ("Truncated after reasoning", "truncated_after_reasoning"),
        ("Parse failures", "parse_failures"),
        ("Empty outputs", "empty_outputs"),
        ("Generation errors", "generation_errors"),
    ):
        print(f"{label}: {report[key]}")
    metrics = report.get("metrics")
    if metrics:
        print(f"Flagged items: {metrics['num_flagged_items']}")
        print(f"Items used for main metrics: {metrics['num_items_used_for_main_metrics']}")
        print(f"Final answer accuracy: {_format(metrics['final_accuracy'])}")
        print(f"Reasoning solved rate: {_format(metrics['reasoning_solved_rate'])}")
    for length, values in report["by_L"].items():
        print(f"L={length}")
        for key in (
            "final_accuracy",
            "reasoning_solved_rate",
            "truncation_rate",
            "during_thinking_truncation_rate",
            "after_thinking_truncation_rate",
            "explicit_final_response_rate",
            "reasoning_answer_rate",
            "avg_generated_tokens",
            "avg_token_budget_utilization",
            "avg_latency_ms",
            "parse_failure_rate",
        ):
            print(f"  {key}: {_format(values[key])}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    print_validation_report(build_validation_report(read_json_records(args.input)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
