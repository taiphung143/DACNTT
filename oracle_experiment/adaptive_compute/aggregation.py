"""Valid-only majority voting and per-configuration summaries."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from statistics import fmean
from typing import Any

from adaptive_compute.answer_parser import GSM8K_ANSWER_PARSER_NAME
from adaptive_compute.evaluate import answers_equal, compute_token_budget_utilization


@dataclass(frozen=True)
class AggregationResult:
    majority_answer: str | None
    valid_answer_count: int
    invalid_answer_count: int
    agreement: float | None
    agreement_among_valid: float | None
    valid_answer_fraction: float


def aggregate_answers(
    parsed_answers: Sequence[str | None], *, expected_k: int | None = None
) -> AggregationResult:
    """Vote only on valid answers; ties use the lowest sample index."""

    k = len(parsed_answers) if expected_k is None else expected_k
    if k <= 0:
        raise ValueError("expected_k must be positive")
    if len(parsed_answers) > k:
        raise ValueError("more parsed answers were supplied than expected_k")

    valid = [(index, answer) for index, answer in enumerate(parsed_answers) if answer is not None]
    if not valid:
        return AggregationResult(None, 0, k, None, None, 0.0)

    counts = Counter(answer for _, answer in valid)
    max_frequency = max(counts.values())
    winners = {answer for answer, count in counts.items() if count == max_frequency}
    majority_answer = next(answer for _, answer in valid if answer in winners)
    valid_count = len(valid)
    agreement = max_frequency / valid_count
    return AggregationResult(
        majority_answer=majority_answer,
        valid_answer_count=valid_count,
        invalid_answer_count=k - valid_count,
        agreement=agreement,
        agreement_among_valid=agreement,
        valid_answer_fraction=valid_count / k,
    )


def build_configuration_summary(samples: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Aggregate one problem/repetition/profile from sample-level records."""

    if not samples:
        raise ValueError("at least one sample record is required")
    first = samples[0]
    k = int(first["k"])
    length = int(first["L"])
    final_aggregation = aggregate_answers(
        [sample.get("final_response_answer") for sample in samples], expected_k=k
    )
    reasoning_aggregation = aggregate_answers(
        [sample.get("reasoning_answer") for sample in samples], expected_k=k
    )
    ground_truth = str(first["ground_truth"])
    answer_parser_name = str(
        first.get("answer_parser_name", GSM8K_ANSWER_PARSER_NAME)
    )
    utilizations = [
        sample.get("token_budget_utilization")
        if sample.get("token_budget_utilization") is not None
        else compute_token_budget_utilization(sample.get("generated_tokens"), length)
        for sample in samples
    ]
    valid_utilizations = [float(value) for value in utilizations if value is not None]
    final_correct = final_aggregation.valid_answer_count > 0 and answers_equal(
        final_aggregation.majority_answer,
        ground_truth,
        answer_parser_name=answer_parser_name,
    )
    dataset_quality_flag = first.get("dataset_quality_flag")
    reasoning_correct = (
        None
        if reasoning_aggregation.valid_answer_count == 0 or dataset_quality_flag is not None
        else answers_equal(
            reasoning_aggregation.majority_answer,
            ground_truth,
            answer_parser_name=answer_parser_name,
        )
    )
    return {
        "problem_id": first["problem_id"],
        "question": first.get("question"),
        "k": k,
        "L": length,
        "repetition_id": first.get("repetition_id", 0),
        # Backward-compatible main fields all refer to strict final responses.
        **asdict(final_aggregation),
        "majority_answer": final_aggregation.majority_answer,
        "final_majority_answer": final_aggregation.majority_answer,
        "reasoning_majority_answer": reasoning_aggregation.majority_answer,
        "final_agreement": final_aggregation.agreement,
        "reasoning_agreement": reasoning_aggregation.agreement,
        "reasoning_valid_answer_count": reasoning_aggregation.valid_answer_count,
        "reasoning_invalid_answer_count": reasoning_aggregation.invalid_answer_count,
        "final_correct": final_correct,
        "reasoning_correct": reasoning_correct,
        "dataset_quality_flag": dataset_quality_flag,
        "sample_truncation_count": sum(bool(sample.get("truncated")) for sample in samples),
        "sample_parse_failure_count": sum(
            sample.get("failure_type") == "parse_failure" for sample in samples
        ),
        "sample_during_thinking_truncation_count": sum(
            sample.get("truncation_stage") == "during_thinking" for sample in samples
        ),
        "sample_after_thinking_truncation_count": sum(
            sample.get("truncation_stage") == "after_thinking" for sample in samples
        ),
        "allocated_token_budget": k * length,
        "actual_generated_tokens": sum(int(sample.get("generated_tokens", 0)) for sample in samples),
        "total_prompt_tokens": sum(int(sample.get("prompt_tokens", 0)) for sample in samples),
        "total_latency_ms": sum(float(sample.get("latency_ms", 0.0)) for sample in samples),
        "avg_token_budget_utilization": (
            fmean(valid_utilizations) if valid_utilizations else None
        ),
    }
