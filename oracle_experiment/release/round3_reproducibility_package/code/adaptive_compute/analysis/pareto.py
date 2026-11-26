"""Eligibility guard for later accuracy-compute/Pareto analysis."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from adaptive_compute.config import EXCLUDE_FLAGGED_DATASET_ITEMS_FROM_MAIN_METRICS


def pareto_eligible_records(
    records: Sequence[Mapping[str, Any]],
    *,
    exclude_flagged: bool = EXCLUDE_FLAGGED_DATASET_ITEMS_FROM_MAIN_METRICS,
) -> list[Mapping[str, Any]]:
    """Keep raw records available while excluding flagged items from the curve."""

    return [
        record
        for record in records
        if not exclude_flagged or record.get("dataset_quality_flag") is None
    ]


def pareto_frontier(
    records: Sequence[Mapping[str, Any]],
    *,
    cost_key: str = "avg_generated_tokens",
    score_key: str = "final_accuracy",
) -> list[Mapping[str, Any]]:
    """Return non-dominated points for lower cost and higher score."""

    frontier: list[Mapping[str, Any]] = []
    for candidate in records:
        candidate_cost = float(candidate[cost_key])
        candidate_score = float(candidate[score_key])
        dominated = any(
            float(other[cost_key]) <= candidate_cost
            and float(other[score_key]) >= candidate_score
            and (
                float(other[cost_key]) < candidate_cost
                or float(other[score_key]) > candidate_score
            )
            for other in records
            if other is not candidate
        )
        if not dominated:
            frontier.append(candidate)
    return sorted(frontier, key=lambda row: (float(row[cost_key]), -float(row[score_key])))
