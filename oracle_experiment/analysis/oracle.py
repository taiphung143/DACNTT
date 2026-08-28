"""Safety guard for later oracle selection."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from config import EXCLUDE_FLAGGED_DATASET_ITEMS_FROM_MAIN_METRICS


def select_min_cost_success(
    configurations: Sequence[Mapping[str, Any]],
    *,
    exclude_flagged: bool = EXCLUDE_FLAGGED_DATASET_ITEMS_FROM_MAIN_METRICS,
) -> Mapping[str, Any] | None:
    """Select the cheapest valid correct profile, never a parse artifact."""

    eligible = [
        item
        for item in configurations
        if item.get("final_correct") is True
        and (not exclude_flagged or item.get("dataset_quality_flag") is None)
        and int(item.get("valid_answer_count", 0)) > 0
        and item.get("majority_answer") is not None
    ]
    if not eligible:
        return None
    return min(
        eligible,
        key=lambda item: (
            int(item["actual_generated_tokens"]),
            int(item.get("allocated_token_budget", 0)),
            int(item.get("k", 0)),
            int(item.get("L", 0)),
        ),
    )

