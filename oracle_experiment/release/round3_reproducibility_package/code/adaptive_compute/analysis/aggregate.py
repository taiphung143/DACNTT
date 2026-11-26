"""Derive shared-pool k profiles and reproducible CSV summaries from raw samples."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from statistics import fmean, median
from typing import Any

from adaptive_compute.aggregation import build_configuration_summary
from adaptive_compute.experiment_runner import derive_shared_prefix, latest_checkpoint_records


def resolve_experiment_dir(value: Path) -> Path:
    """Accept either an experiment directory or its ID under ./results."""

    if (value / "experiment_manifest.json").exists():
        return value
    candidate = Path("results") / value
    return candidate if (candidate / "experiment_manifest.json").exists() else value


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _latest_raw_records(records: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Deduplicate retried generation keys while preserving final record order."""

    # latest_checkpoint_records is path-based; this equivalent keeps this pure for tests.
    from adaptive_compute.experiment_runner import sample_key

    latest: dict[tuple[Any, ...], Mapping[str, Any]] = {}
    for record in records:
        latest[sample_key(record)] = record
    return list(latest.values())


def build_config_results(
    records: Sequence[Mapping[str, Any]],
    k_values: Sequence[int],
    *,
    exclude_flagged: bool = True,
) -> list[dict[str, Any]]:
    """Build one result per complete problem/repetition/(k,L) prefix."""

    groups: dict[tuple[str, int, int], list[Mapping[str, Any]]] = defaultdict(list)
    for record in _latest_raw_records(records):
        groups[
            (
                str(record["problem_id"]),
                int(record["L"]),
                int(record.get("repetition_id", 0)),
            )
        ].append(record)

    output: list[dict[str, Any]] = []
    for (problem_id, length, repetition_id), pool in sorted(groups.items()):
        for k in sorted(k_values):
            try:
                selected = derive_shared_prefix(pool, int(k))
            except ValueError:
                continue  # a partial checkpoint can still yield smaller completed k profiles
            materialized = [{**sample, "k": int(k)} for sample in selected]
            summary = build_configuration_summary(materialized)
            quality_flag = summary.get("dataset_quality_flag")
            summary.update(
                {
                    "problem_id": problem_id,
                    "repetition_id": repetition_id,
                    "ground_truth": selected[0].get("ground_truth"),
                    "sum_sample_latency_ms": summary.pop("total_latency_ms"),
                    "evaluation_included": not (exclude_flagged and quality_flag is not None),
                    "sample_ids": "|".join(str(item["sample_id"]) for item in selected),
                }
            )
            output.append(summary)
    return sorted(output, key=lambda row: (row["problem_id"], row["repetition_id"], row["k"], row["L"]))


def build_grid_summary(config_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[int, int], list[Mapping[str, Any]]] = defaultdict(list)
    for row in config_rows:
        groups[(int(row["k"]), int(row["L"]))].append(row)

    summaries: list[dict[str, Any]] = []
    for (k, length), rows in sorted(groups.items()):
        evaluated = [row for row in rows if bool(row.get("evaluation_included"))]
        agreements = [float(row["agreement"]) for row in rows if row.get("agreement") is not None]
        total_samples = sum(int(row["valid_answer_count"]) + int(row["invalid_answer_count"]) for row in rows)
        actual_tokens = [int(row["actual_generated_tokens"]) for row in rows]
        allocated = [int(row["allocated_token_budget"]) for row in rows]
        summaries.append(
            {
                "k": k,
                "L": length,
                "num_total_problems": len(rows),
                "num_evaluated_problems": len(evaluated),
                "num_flagged_problems": len(rows) - len(evaluated),
                "final_accuracy": (
                    sum(bool(row.get("final_correct")) for row in evaluated) / len(evaluated)
                    if evaluated
                    else None
                ),
                "avg_generated_tokens": fmean(actual_tokens),
                "median_generated_tokens": median(actual_tokens),
                "avg_allocated_token_budget": fmean(allocated),
                "avg_latency_ms": fmean(float(row["sum_sample_latency_ms"]) for row in rows),
                "truncation_rate": (
                    sum(int(row["sample_truncation_count"]) for row in rows) / total_samples
                    if total_samples
                    else None
                ),
                "during_thinking_truncation_rate": (
                    sum(int(row["sample_during_thinking_truncation_count"]) for row in rows)
                    / total_samples
                    if total_samples
                    else None
                ),
                "after_thinking_truncation_rate": (
                    sum(int(row["sample_after_thinking_truncation_count"]) for row in rows)
                    / total_samples
                    if total_samples
                    else None
                ),
                "parse_failure_rate": (
                    sum(int(row["sample_parse_failure_count"]) for row in rows) / total_samples
                    if total_samples
                    else None
                ),
                "avg_valid_answer_fraction": fmean(float(row["valid_answer_fraction"]) for row in rows),
                "avg_agreement": fmean(agreements) if agreements else None,
                "avg_token_budget_utilization": fmean(
                    actual / budget if budget else 0.0
                    for actual, budget in zip(actual_tokens, allocated, strict=True)
                ),
                "agreement_note": "not meaningful for k=1" if k == 1 else "valid answers only",
            }
        )
    return summaries


def build_iso_budget_summary(
    grid_rows: Sequence[Mapping[str, Any]], budget: int = 2048
) -> list[dict[str, Any]]:
    expected = {(4, 512), (2, 1024), (1, 2048)} if budget == 2048 else None
    selected = [
        row
        for row in grid_rows
        if int(row["k"]) * int(row["L"]) == budget
        and (expected is None or (int(row["k"]), int(row["L"])) in expected)
    ]
    return [
        {
            "profile": f"{int(row['k'])}x{int(row['L'])}",
            "k": int(row["k"]),
            "L": int(row["L"]),
            "allocated_budget": budget,
            "accuracy": row["final_accuracy"],
            "avg_actual_generated_tokens": row["avg_generated_tokens"],
            "avg_latency_ms": row["avg_latency_ms"],
            "avg_valid_answer_fraction": row["avg_valid_answer_fraction"],
            "avg_agreement": row["avg_agreement"],
        }
        for row in sorted(selected, key=lambda item: int(item["k"]), reverse=True)
    ]


def run_aggregation(experiment_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    manifest = json.loads((experiment_dir / "experiment_manifest.json").read_text(encoding="utf-8"))
    raw_path = experiment_dir / "raw_samples.jsonl"
    raw_records = list(latest_checkpoint_records(raw_path).values())
    config_rows = build_config_results(
        raw_records,
        [int(value) for value in manifest["k_values"]],
        exclude_flagged=bool(
            manifest.get("config", {}).get("exclude_flagged_dataset_items_from_main_metrics", True)
        ),
    )
    grid_rows = build_grid_summary(config_rows)
    write_csv(experiment_dir / "config_results.csv", config_rows)
    write_csv(experiment_dir / "grid_summary.csv", grid_rows)
    write_csv(
        experiment_dir / "depth_diagnostic.csv",
        [row for row in grid_rows if int(row["k"]) == 1],
    )
    write_csv(experiment_dir / "breadth_diagnostic.csv", grid_rows)
    write_csv(experiment_dir / "iso_budget_2048.csv", build_iso_budget_summary(grid_rows))
    return config_rows, grid_rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, required=True)
    args = parser.parse_args()
    config_rows, grid_rows = run_aggregation(resolve_experiment_dir(args.experiment))
    print(f"Wrote {len(config_rows)} configuration rows and {len(grid_rows)} grid rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
