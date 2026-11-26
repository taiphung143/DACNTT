"""Strict final-response evaluation plus reasoning diagnostics."""

from __future__ import annotations

from dataclasses import dataclass

from adaptive_compute.answer_parser import (
    GSM8K_ANSWER_PARSER_NAME,
    GSM8K_ANSWER_PARSER_NAMES,
    GSM8K_ANSWER_PARSER_V2_NAME,
    GSM8K_ANSWER_PARSER_V3_NAME,
    GSM8K_ANSWER_PARSER_V4_NAME,
    MATH500_ANSWER_PARSER_NAME,
    normalize_math_answer,
    normalize_numeric_answer,
    parse_math500_response_answers,
    parse_gsm8k_v2_response_answers,
    parse_gsm8k_v3_response_answers,
    parse_gsm8k_v4_response_answers,
    parse_response_answers,
)


TRUNCATION_FINISH_REASONS = frozenset({"length", "max_tokens", "max_length"})
DATASET_QUALITY_FLAGS = frozenset(
    {None, "suspected_ground_truth_error", "manual_review_required"}
)


@dataclass(frozen=True)
class EvaluationResult:
    raw_response: str
    reasoning_answer: str | None
    final_response_answer: str | None
    answer_source: str
    reasoning_final_disagreement: bool
    parsed_answer: str | None
    ground_truth: str
    reasoning_correct: bool | None
    final_correct: bool
    correct: bool
    parse_error: bool
    truncated: bool
    truncation_stage: str
    thinking_started: bool
    thinking_completed: bool
    explicit_final_answer_found: bool
    failure_type: str
    dataset_quality_flag: str | None
    token_budget_utilization: float | None


def answers_equal(
    parsed_answer: str | None,
    ground_truth: str,
    *,
    answer_parser_name: str = GSM8K_ANSWER_PARSER_NAME,
) -> bool:
    if parsed_answer is None:
        return False
    if answer_parser_name in GSM8K_ANSWER_PARSER_NAMES:
        prediction = normalize_numeric_answer(parsed_answer)
        truth = normalize_numeric_answer(ground_truth)
    elif answer_parser_name == MATH500_ANSWER_PARSER_NAME:
        prediction = normalize_math_answer(parsed_answer)
        truth = normalize_math_answer(ground_truth)
    else:
        raise ValueError(f"unsupported answer parser: {answer_parser_name}")
    return prediction is not None and truth is not None and prediction == truth


def is_truncated(finish_reason: str | None) -> bool:
    return bool(
        finish_reason
        and finish_reason.strip().lower() in TRUNCATION_FINISH_REASONS
    )


def compute_token_budget_utilization(
    generated_tokens: int | None, max_new_tokens: int | None
) -> float | None:
    if generated_tokens is None or max_new_tokens is None or max_new_tokens <= 0:
        return None
    if generated_tokens < 0:
        raise ValueError("generated_tokens must be non-negative")
    return generated_tokens / max_new_tokens


def determine_truncation_stage(
    *, truncated: bool, thinking_started: bool, thinking_completed: bool
) -> str:
    if not truncated:
        return "none"
    if thinking_started and not thinking_completed:
        return "during_thinking"
    # With no thinking tags, generation is in the user-facing response stage.
    return "after_thinking"


def evaluate_response(
    raw_response: str,
    ground_truth: str,
    *,
    finish_reason: str | None = None,
    generated_tokens: int | None = None,
    max_new_tokens: int | None = None,
    generation_error: str | None = None,
    dataset_quality_flag: str | None = None,
    answer_parser_name: str = GSM8K_ANSWER_PARSER_NAME,
) -> EvaluationResult:
    if dataset_quality_flag not in DATASET_QUALITY_FLAGS:
        raise ValueError(f"unsupported dataset_quality_flag: {dataset_quality_flag}")

    truncated = is_truncated(finish_reason)
    if answer_parser_name == GSM8K_ANSWER_PARSER_NAME:
        answers = parse_response_answers(raw_response)
    elif answer_parser_name == GSM8K_ANSWER_PARSER_V2_NAME:
        answers = parse_gsm8k_v2_response_answers(raw_response)
    elif answer_parser_name == GSM8K_ANSWER_PARSER_V3_NAME:
        answers = parse_gsm8k_v3_response_answers(raw_response)
    elif answer_parser_name == GSM8K_ANSWER_PARSER_V4_NAME:
        answers = parse_gsm8k_v4_response_answers(raw_response)
    elif answer_parser_name == MATH500_ANSWER_PARSER_NAME:
        answers = parse_math500_response_answers(raw_response)
    else:
        raise ValueError(f"unsupported answer parser: {answer_parser_name}")
    truncation_stage = determine_truncation_stage(
        truncated=truncated,
        thinking_started=answers.thinking_started,
        thinking_completed=answers.thinking_completed,
    )
    utilization = compute_token_budget_utilization(generated_tokens, max_new_tokens)
    empty_response = not raw_response or not raw_response.strip()

    reasoning_correct = (
        None
        if answers.reasoning_answer is None or dataset_quality_flag is not None
        else answers_equal(
            answers.reasoning_answer,
            ground_truth,
            answer_parser_name=answer_parser_name,
        )
    )
    parsed_answer = answers.final_response_answer
    final_correct = answers_equal(
        parsed_answer,
        ground_truth,
        answer_parser_name=answer_parser_name,
    )

    if generation_error is not None:
        failure_type = "generation_error"
        parsed_answer = None
        final_correct = False
    elif empty_response:
        failure_type = "empty_response"
    elif parsed_answer is not None:
        failure_type = "correct" if final_correct else "wrong_answer"
    elif truncated and answers.thinking_completed:
        failure_type = "truncated_after_reasoning"
    elif truncated:
        failure_type = "truncated_before_answer"
    else:
        failure_type = "parse_failure"

    return EvaluationResult(
        raw_response=raw_response,
        reasoning_answer=answers.reasoning_answer,
        final_response_answer=answers.final_response_answer,
        answer_source=answers.answer_source,
        reasoning_final_disagreement=answers.reasoning_final_disagreement,
        parsed_answer=parsed_answer,
        ground_truth=ground_truth,
        reasoning_correct=reasoning_correct,
        final_correct=final_correct,
        correct=final_correct,  # backward-compatible alias; main accuracy is strict final accuracy
        parse_error=parsed_answer is None,
        truncated=truncated,
        truncation_stage=truncation_stage,
        thinking_started=answers.thinking_started,
        thinking_completed=answers.thinking_completed,
        explicit_final_answer_found=answers.final_response_answer is not None,
        failure_type=failure_type,
        dataset_quality_flag=dataset_quality_flag,
        token_budget_utilization=utilization,
    )
