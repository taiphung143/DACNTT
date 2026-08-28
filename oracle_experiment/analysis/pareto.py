"""Eligibility guard for later accuracy-compute/Pareto analysis."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from config import EXCLUDE_FLAGGED_DATASET_ITEMS_FROM_MAIN_METRICS


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

