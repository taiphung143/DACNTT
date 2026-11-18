"""Regenerate all Phase-1 tables, demo cases, and plots without model inference."""

from __future__ import annotations

import argparse
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from adaptive_compute.analysis.aggregate import resolve_experiment_dir, run_aggregation, write_csv
from adaptive_compute.analysis.behavior_analysis import classify_behaviors
from adaptive_compute.analysis.oracle import build_oracle_comparison
from adaptive_compute.analysis.plots import generate_plots
from adaptive_compute.analysis.statistics import (
    build_accuracy_intervals,
    build_paired_comparisons,
    build_statistical_report,
)
from adaptive_compute.experiment_runner import derive_shared_prefix, latest_checkpoint_records


def build_demo_cases(
    raw_records: Sequence[Mapping[str, Any]],
    config_rows: Sequence[Mapping[str, Any]],
    *,
    max_cases: int = 3,
) -> str:
    """Create compact, auditable majority-vote examples without full traces."""

    if not config_rows:
        return "# Demo cases\n\nNo complete configurations are available.\n"
    max_k = max(int(row["k"]) for row in config_rows)
    l_values = sorted({int(row["L"]) for row in config_rows})
    chosen_l = l_values[len(l_values) // 2]
    candidates = [
        row for row in config_rows if int(row["k"]) == max_k and int(row["L"]) == chosen_l
    ]
    candidates.sort(
        key=lambda row: (
            -int(row.get("sample_truncation_count", 0)),
            float(row.get("agreement") if row.get("agreement") is not None else 1.0),
            str(row["problem_id"]),
        )
    )
    raw_groups: dict[tuple[str, int, int], list[Mapping[str, Any]]] = defaultdict(list)
    for record in raw_records:
        raw_groups[
            (
                str(record["problem_id"]),
                int(record["L"]),
                int(record.get("repetition_id", 0)),
            )
        ].append(record)

    lines = [
        "# Shared-sample majority-vote demo",
        "",
        "Exploratory pilot output. Full responses remain in `raw_samples.jsonl`; only short excerpts are shown here.",
        "",
    ]
    for case_index, row in enumerate(candidates[:max_cases], start=1):
        key = (str(row["problem_id"]), int(row["L"]), int(row.get("repetition_id", 0)))
        samples = derive_shared_prefix(raw_groups[key], int(row["k"]))
        lines.extend(
            [
                f"## Case {case_index}: {row['problem_id']}",
                "",
                f"**Question:** {samples[0].get('question', '')}",
                "",
                f"**Configuration:** k={row['k']}, L={row['L']} (sample prefix `{row['sample_ids']}`)",
                "",
            ]
        )
        valid_answers: list[str] = []
        for sample in samples:
            answer = sample.get("final_response_answer")
            if answer not in (None, ""):
                valid_answers.append(str(answer))
            excerpt = " ".join(str(sample.get("raw_response") or sample.get("text") or "").split())
            if len(excerpt) > 240:
                excerpt = excerpt[:237] + "..."
            lines.extend(
                [
                    f"### Sample {sample['sample_id']}",
                    "",
                    f"- Final answer: `{answer}`",
                    f"- Generated tokens: {sample.get('generated_tokens')}",
                    f"- Valid: {'yes' if answer not in (None, '') else 'no'}",
                    f"- Truncated: {str(bool(sample.get('truncated'))).lower()} ({sample.get('truncation_stage')})",
                    f"- Failure type: `{sample.get('failure_type')}`",
                    f"- Short excerpt: {excerpt or '<empty>'}",
                    "",
                ]
            )
        lines.extend(
            [
                f"**Valid answers:** `{valid_answers}`  ",
                f"**Majority:** `{row.get('majority_answer')}`  ",
                f"**Agreement among valid:** `{row.get('agreement')}`  ",
                f"**Valid answer fraction:** `{row.get('valid_answer_fraction')}`  ",
                f"**Ground truth:** `{row.get('ground_truth')}`  ",
                f"**Final correct:** `{str(row.get('final_correct')).lower()}`  ",
                "**Raw pointer:** match `problem_id`, `L`, `repetition_id`, and `sample_id` in `raw_samples.jsonl`.",
                "",
            ]
        )
    return "\n".join(lines)


def run_analysis(experiment_dir: Path) -> None:
    config_rows, grid_rows = run_aggregation(experiment_dir)
    behavior_rows = classify_behaviors(config_rows)
    write_csv(experiment_dir / "behavior_classification.csv", behavior_rows)
    oracle_rows, anchor_rows = build_oracle_comparison(config_rows)
    write_csv(experiment_dir / "oracle_comparison.csv", oracle_rows)
    write_csv(experiment_dir / "oracle_anchor_evaluation.csv", anchor_rows)
    accuracy_rows = build_accuracy_intervals(config_rows)
    comparison_rows = build_paired_comparisons(config_rows)
    write_csv(experiment_dir / "accuracy_intervals.csv", accuracy_rows)
    write_csv(experiment_dir / "paired_comparisons.csv", comparison_rows)
    (experiment_dir / "statistical_report.md").write_text(
        build_statistical_report(accuracy_rows, comparison_rows), encoding="utf-8"
    )
    raw_records = list(latest_checkpoint_records(experiment_dir / "raw_samples.jsonl").values())
    (experiment_dir / "demo_cases.md").write_text(
        build_demo_cases(raw_records, config_rows), encoding="utf-8"
    )
    generate_plots(experiment_dir, grid_rows=grid_rows, oracle_rows=oracle_rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, required=True)
    args = parser.parse_args()
    experiment_dir = resolve_experiment_dir(args.experiment)
    run_analysis(experiment_dir)
    print(f"Rebuilt analysis artifacts under {experiment_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
