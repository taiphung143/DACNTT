from answer_parser import parse_final_answer, parse_response_answers
from evaluate import evaluate_response


def test_truncate_during_thinking() -> None:
    result = evaluate_response(
        "<think>\nReasoning ...",
        "42",
        finish_reason="length",
    )

    assert result.truncation_stage == "during_thinking"
    assert result.reasoning_answer is None
    assert result.final_response_answer is None
    assert result.answer_source == "none"
    assert result.failure_type == "truncated_before_answer"


def test_answer_inside_thinking_is_not_main_answer_when_final_is_truncated() -> None:
    response = "<think>\nWork\n#### 42\n</think>\nHere is the explanation..."
    result = evaluate_response(response, "42", finish_reason="length")

    assert result.thinking_completed is True
    assert result.reasoning_answer == "42"
    assert result.final_response_answer is None
    assert result.answer_source == "thinking"
    assert result.parsed_answer is None
    assert result.final_correct is False
    assert result.reasoning_correct is True
    assert result.truncation_stage == "after_thinking"
    assert result.failure_type == "truncated_after_reasoning"
    assert parse_final_answer(response) is None


def test_complete_reasoning_and_final_response() -> None:
    result = evaluate_response(
        "<think>\n#### 42\n</think>\nThe answer is 42.",
        "42",
        finish_reason="stop",
    )

    assert result.reasoning_answer == "42"
    assert result.final_response_answer == "42"
    assert result.answer_source == "both"
    assert result.parsed_answer == "42"
    assert result.final_correct is True
    assert result.reasoning_correct is True
    assert result.truncation_stage == "none"


def test_reasoning_final_disagreement_uses_final_response() -> None:
    result = parse_response_answers(
        "<think>\n#### 42\n</think>\nThe answer is 43."
    )

    assert result.reasoning_answer == "42"
    assert result.final_response_answer == "43"
    assert result.answer_source == "both"
    assert result.reasoning_final_disagreement is True
    assert parse_final_answer("<think>#### 42</think> The answer is 43.") == "43"


def test_final_answer_only() -> None:
    result = parse_response_answers("The answer is 42.")

    assert result.reasoning_answer is None
    assert result.final_response_answer == "42"
    assert result.answer_source == "final_response"

