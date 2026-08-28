"""Strict-final accuracy and reasoning/truncation diagnostics."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from statistics import fmean
from typing import Any

from config import EXCLUDE_FLAGGED_DATASET_ITEMS_FROM_MAIN_METRICS


def summarize_sample_group(
    samples: Sequence[Mapping[str, Any]],
    *,
    exclude_flagged: bool = EXCLUDE_FLAGGED_DATASET_ITEMS_FROM_MAIN_METRICS,
) -> dict[str, Any]:
    if not samples:
        raise ValueError("at least one sample is required")
    flagged = [item for item in samples if item.get("dataset_quality_flag") is not None]
    used = [
        item
        for item in samples
        if not exclude_flagged or item.get("dataset_quality_flag") is None
    ]
    total = len(samples)
    used_count = len(used)
    utilizations = [
        float(item["token_budget_utilization"])
        for item in samples
        if item.get("token_budget_utilization") is not None
    ]
    generated_tokens = [float(item.get("generated_tokens", 0)) for item in samples]
    latencies = [float(item.get("latency_ms", 0.0)) for item in samples]
    thinking_started = sum(bool(item.get("thinking_started")) for item in samples)
    thinking_completed = sum(bool(item.get("thinking_completed")) for item in samples)
    final_accuracy = (
        sum(bool(item.get("final_correct", item.get("correct"))) for item in used)
        / used_count
        if used_count
        else None
    )
    reasoning_solved_rate = (
        sum(item.get("reasoning_correct") is True for item in used) / used_count
        if used_count
        else None
    )
    return {
        "num_total_items": total,
        "num_flagged_items": len(flagged),
        "num_items_used_for_main_metrics": used_count,
        "final_accuracy": final_accuracy,
        "accuracy": final_accuracy,  # backward-compatible alias
        "reasoning_solved_rate": reasoning_solved_rate,
        "truncation_rate": sum(bool(item.get("truncated")) for item in samples) / total,
        "during_thinking_truncation_rate": sum(
            item.get("truncation_stage") == "during_thinking" for item in samples
        )
        / total,
        "after_thinking_truncation_rate": sum(
            item.get("truncation_stage") == "after_thinking" for item in samples
        )
        / total,
        "explicit_final_response_rate": sum(
            item.get("final_response_answer") is not None for item in samples
        )
        / total,
        "reasoning_answer_rate": sum(
            item.get("reasoning_answer") is not None for item in samples
        )
        / total,
        "thinking_completion_rate": (
            thinking_completed / thinking_started if thinking_started else None
        ),
        "avg_generated_tokens": fmean(generated_tokens),
        "avg_token_budget_utilization": fmean(utilizations) if utilizations else None,
        "mean_token_budget_utilization": fmean(utilizations) if utilizations else None,
        "avg_latency_ms": fmean(latencies),
        "parse_failure_rate": sum(
            item.get("failure_type") == "parse_failure" for item in samples
        )
        / total,
    }


def summarize_profiles(
    records: Iterable[Mapping[str, Any]],
    *,
    exclude_flagged: bool = EXCLUDE_FLAGGED_DATASET_ITEMS_FROM_MAIN_METRICS,
) -> list[dict[str, Any]]:
    groups: dict[tuple[int, int], list[Mapping[str, Any]]] = defaultdict(list)
    for record in records:
        groups[(int(record["k"]), int(record["L"]))].append(record)
    return [
        {
            "k": k,
            "L": length,
            **summarize_sample_group(samples, exclude_flagged=exclude_flagged),
        }
        for (k, length), samples in sorted(groups.items())
    ]
