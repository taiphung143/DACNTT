"""Fixed, breadth-only, depth-only, and joint retrospective oracle analysis."""

from __future__ import annotations

import argparse
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from statistics import fmean
from typing import Any

from adaptive_compute.analysis.aggregate import read_csv, resolve_experiment_dir, write_csv
from adaptive_compute.config import EXCLUDE_FLAGGED_DATASET_ITEMS_FROM_MAIN_METRICS


def _truthy(value: Any) -> bool:
    return value is True or str(value).lower() == "true"


def _selection_key(item: Mapping[str, Any]) -> tuple[float, float, int, int, int]:
    return (
        float(item["actual_generated_tokens"]),
        float(item.get("sum_sample_latency_ms", item.get("total_latency_ms", 0.0))),
        int(item.get("allocated_token_budget", 0)),
        int(item.get("k", 0)),
        int(item.get("L", 0)),
    )


def select_min_cost_success(
    configurations: Sequence[Mapping[str, Any]],
    *,
    exclude_flagged: bool = EXCLUDE_FLAGGED_DATASET_ITEMS_FROM_MAIN_METRICS,
) -> Mapping[str, Any] | None:
    """Select the cheapest valid correct profile with deterministic tie-breaking."""

    eligible = [
        item
        for item in configurations
        if _truthy(item.get("final_correct"))
        and (not exclude_flagged or not item.get("dataset_quality_flag"))
        and int(item.get("valid_answer_count", 0)) > 0
        and item.get("majority_answer") not in (None, "")
    ]
    return min(eligible, key=_selection_key) if eligible else None


def _strategy_summary(
    strategy: str,
    groups: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    fixed_k: int | None = None,
    fixed_l: int | None = None,
) -> dict[str, Any]:
    selections: list[Mapping[str, Any]] = []
    solved = 0
    for rows in groups.values():
        candidates = [
            row
            for row in rows
            if (fixed_k is None or int(row["k"]) == fixed_k)
            and (fixed_l is None or int(row["L"]) == fixed_l)
        ]
        if not candidates:
            continue
        selected = select_min_cost_success(candidates, exclude_flagged=False)
        if selected is not None:
            solved += 1
        else:
            # The strategy still spends compute on unsolved problems; use its
            # cheapest observed candidate rather than excluding their cost.
            selected = min(candidates, key=_selection_key)
        selections.append(selected)
    count = len(selections)
    return {
        "strategy": strategy,
        "fixed_k": fixed_k,
        "fixed_L": fixed_l,
        "num_evaluated_problems": count,
        "accuracy": solved / count if count else None,
        "avg_generated_tokens": fmean(float(row["actual_generated_tokens"]) for row in selections) if selections else None,
        "avg_allocated_budget": fmean(float(row["allocated_token_budget"]) for row in selections) if selections else None,
        "avg_latency_ms": fmean(float(row.get("sum_sample_latency_ms", 0.0)) for row in selections) if selections else None,
    }


def _best_summary(candidates: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    return min(
        candidates,
        key=lambda row: (
            -float(row["accuracy"]),
            float(row["avg_generated_tokens"]),
            float(row["avg_latency_ms"]),
            float(row["avg_allocated_budget"]),
            int(row.get("fixed_k") or 0),
            int(row.get("fixed_L") or 0),
        ),
    )


def build_oracle_comparison(
    config_rows: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    included = [
        row
        for row in config_rows
        if _truthy(row.get("evaluation_included", True))
    ]
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in included:
        groups[f"{row['problem_id']}|{row.get('repetition_id', 0)}"].append(row)
    k_values = sorted({int(row["k"]) for row in included})
    l_values = sorted({int(row["L"]) for row in included})

    fixed_candidates = [
        _strategy_summary("fixed_candidate", groups, fixed_k=k, fixed_l=length)
        for k in k_values
        for length in l_values
    ]
    breadth_candidates = [
        _strategy_summary("breadth_oracle_candidate", groups, fixed_l=length)
        for length in l_values
    ]
    depth_candidates = [
        _strategy_summary("depth_oracle_candidate", groups, fixed_k=k)
        for k in k_values
    ]
    joint = _strategy_summary("joint_oracle", groups)
    best_fixed = {**_best_summary(fixed_candidates), "strategy": "best_fixed"}
    breadth = {**_best_summary(breadth_candidates), "strategy": "breadth_oracle"}
    depth = {**_best_summary(depth_candidates), "strategy": "depth_oracle"}
    comparison = [best_fixed, breadth, depth, joint]
    anchors = [
        {**row, "selected_as_best_anchor": row is _best_summary(breadth_candidates)}
        for row in breadth_candidates
    ] + [
        {**row, "selected_as_best_anchor": row is _best_summary(depth_candidates)}
        for row in depth_candidates
    ] + [
        {**row, "selected_as_best_anchor": row is _best_summary(fixed_candidates)}
        for row in fixed_candidates
    ]
    return [dict(row) for row in comparison], [dict(row) for row in anchors]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, required=True)
    args = parser.parse_args()
    experiment_dir = resolve_experiment_dir(args.experiment)
    comparison, anchors = build_oracle_comparison(
        read_csv(experiment_dir / "config_results.csv")
    )
    write_csv(experiment_dir / "oracle_comparison.csv", comparison)
    write_csv(experiment_dir / "oracle_anchor_evaluation.csv", anchors)
    print("Wrote oracle comparison and explicit anchor evaluation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
