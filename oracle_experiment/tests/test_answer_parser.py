import pytest

from answer_parser import (
    detect_thinking_state,
    normalize_numeric_answer,
    parse_final_answer,
    parse_final_answer_details,
    parse_gsm8k_ground_truth,
)


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        ("#### 42", "42"),
        ("The answer is 42.", "42"),
        (r"\boxed{42}", "42"),
        ("-3.5", "-3.5"),
        ("1,250", "1250"),
        ("Therefore, 42.", "42"),
        ("Reasoning: 2 + 2 = 4.\n#### 4", "4"),
    ],
)
def test_parse_supported_answer_formats(response: str, expected: str) -> None:
    assert parse_final_answer(response) == expected


def test_explicit_marker_takes_priority_over_later_numbers() -> None:
    assert parse_final_answer("#### 42\nConfidence: 0.9") == "42"


def test_parse_failure_returns_none() -> None:
    assert parse_final_answer("I cannot determine the result.") is None


def test_intermediate_last_number_is_not_a_final_answer() -> None:
    response = "We compute 430 + 750 + 700 + 300."

    result = parse_final_answer_details(response)

    assert result.parsed_answer is None
    assert result.explicit_final_answer_found is False


def test_thinking_completion_requires_both_tags() -> None:
    incomplete = detect_thinking_state("<think>still reasoning")
    complete = detect_thinking_state("<think>done</think> The answer is 42.")

    assert incomplete.thinking_started is True
    assert incomplete.thinking_completed is False
    assert complete.thinking_started is True
    assert complete.thinking_completed is True


def test_ground_truth_requires_hash_marker() -> None:
    with pytest.raises(ValueError, match="####"):
        parse_gsm8k_ground_truth("The answer is 42")


def test_ground_truth_uses_final_hash_marker() -> None:
    assert parse_gsm8k_ground_truth("work\n#### 1,250") == "1250"


@pytest.mark.parametrize(
    ("value", "expected"),
    [("42.00", "42"), ("-0.0", "0"), ("001.50", "1.5")],
)
def test_numeric_normalization(value: str, expected: str) -> None:
    assert normalize_numeric_answer(value) == expected
