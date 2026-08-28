from evaluate import (
    answers_equal,
    compute_token_budget_utilization,
    evaluate_response,
    is_truncated,
)


def test_numeric_answers_are_compared_canonically() -> None:
    assert answers_equal("1,250", "1250")
    assert answers_equal("42.0", "42")


def test_parse_failure_is_incorrect() -> None:
    result = evaluate_response("No numeric answer.", "42")

    assert result.parsed_answer is None
    assert result.parse_error is True
    assert result.correct is False


def test_evaluation_preserves_raw_response() -> None:
    result = evaluate_response("Therefore, -3.5.", "-3.5")

    assert result.raw_response == "Therefore, -3.5."
    assert result.parsed_answer == "-3.5"
    assert result.correct is True
    assert result.parse_error is False
    assert result.failure_type == "correct"


def test_truncated_thinking_without_explicit_answer_is_classified() -> None:
    result = evaluate_response(
        "<think>\nWe compute 430 + 750 + 700 + 300.",
        "2280",
        finish_reason="length",
        generated_tokens=512,
        max_new_tokens=512,
    )

    assert result.parsed_answer is None
    assert result.parse_error is True
    assert result.truncated is True
    assert result.thinking_started is True
    assert result.thinking_completed is False
    assert result.explicit_final_answer_found is False
    assert result.failure_type == "truncated_before_answer"
    assert result.token_budget_utilization == 1.0


def test_complete_thinking_with_explicit_answer_is_parsed() -> None:
    result = evaluate_response(
        "<think>reasoning</think>\nThe answer is 42.",
        "42",
        finish_reason="stop",
    )

    assert result.parsed_answer == "42"
    assert result.thinking_completed is True
    assert result.explicit_final_answer_found is True
    assert result.failure_type == "correct"


def test_truncated_response_can_keep_prior_explicit_answer() -> None:
    result = evaluate_response(
        "The answer is 42. Then let me continue with 7 + 8.",
        "42",
        finish_reason="length",
    )

    assert result.parsed_answer == "42"
    assert result.explicit_final_answer_found is True
    assert result.truncated is True
    assert result.parse_error is False
    assert result.failure_type == "correct"


def test_completed_response_without_explicit_answer_is_parse_failure() -> None:
    result = evaluate_response("We compute 40 + 2 = 42.", "42", finish_reason="stop")

    assert result.parsed_answer is None
    assert result.truncated is False
    assert result.failure_type == "parse_failure"


def test_empty_and_generation_error_are_distinct() -> None:
    empty = evaluate_response("", "42", finish_reason="stop")
    error = evaluate_response("", "42", generation_error="CUDA OOM")

    assert empty.failure_type == "empty_response"
    assert error.failure_type == "generation_error"


def test_budget_utilization() -> None:
    assert compute_token_budget_utilization(512, 512) == 1.0
    assert compute_token_budget_utilization(10, 0) is None


def test_backend_token_limit_reasons_are_normalized() -> None:
    assert is_truncated("length")
    assert is_truncated("max_tokens")
    assert is_truncated("max_length")
    assert not is_truncated("stop")


def test_dataset_quality_flag_is_never_inferred_from_wrong_answer() -> None:
    result = evaluate_response("The answer is 2180.", "2280")

    assert result.failure_type == "wrong_answer"
    assert result.dataset_quality_flag is None
