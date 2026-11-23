import pytest

from adaptive_compute.answer_parser import (
    detect_thinking_state,
    normalize_numeric_answer,
    parse_final_answer,
    parse_final_answer_details,
    parse_gsm8k_ground_truth,
    parse_gsm8k_v2_response_answers,
    parse_gsm8k_v3_response_answers,
    parse_gsm8k_v4_response_answers,
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


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        ("<think>done</think>\n#### <numeric answer> 55", "55"),
        ("<think>done</think>\n55 #### <numeric answer>", "55"),
        ("<think>done</think>\n#### <answer>: -3.5", "-3.5"),
    ],
)
def test_gsm8k_v2_recovers_observed_placeholder_echoes(
    response: str, expected: str
) -> None:
    result = parse_gsm8k_v2_response_answers(response)

    assert result.final_response_answer == expected


def test_gsm8k_v2_does_not_guess_placeholder_without_adjacent_number() -> None:
    result = parse_gsm8k_v2_response_answers(
        "<think>The answer is 55.</think>\n#### <numeric answer>"
    )

    assert result.reasoning_answer == "55"
    assert result.final_response_answer is None


def test_gsm8k_v2_does_not_use_last_intermediate_number() -> None:
    result = parse_gsm8k_v2_response_answers(
        "<think>done</think>\nWe compute 430 + 750 + 700 + 300."
    )

    assert result.final_response_answer is None


@pytest.mark.parametrize(
    ("final_line", "expected"),
    [
        ("Final answer: Eve gave away 15 pomelos.", "15"),
        ("Final answer: Final answer is $20,000.", "20000"),
        ("Final answer: It took James 1 hour.", "1"),
        ("Final answer: -3.5 degrees.", "-3.5"),
    ],
)
def test_gsm8k_v3_accepts_one_number_after_explicit_marker(
    final_line: str, expected: str
) -> None:
    result = parse_gsm8k_v3_response_answers(f"<think>done</think>\n{final_line}")

    assert result.final_response_answer == expected


@pytest.mark.parametrize(
    "final_line",
    [
        "Final answer: no numeric result is available.",
        "Final answer: use 15 plus 5 to obtain 20.",
        "The calculation contains 15 and the answer is unclear.",
    ],
)
def test_gsm8k_v3_refuses_zero_multiple_or_unmarked_numbers(
    final_line: str,
) -> None:
    result = parse_gsm8k_v3_response_answers(f"<think>done</think>\n{final_line}")

    assert result.final_response_answer is None


def test_gsm8k_v3_does_not_promote_reasoning_only_answer() -> None:
    result = parse_gsm8k_v3_response_answers(
        "<think>Final answer: 42</think>\nNo final result was provided."
    )

    assert result.reasoning_answer == "42"
    assert result.final_response_answer is None


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (
            "Final answer: The total is $15000 + $5000 = $20000. "
            "Final answer: $20000.",
            "20000",
        ),
        (
            "Final answer: The first year is $15000 and the second is $5000. "
            "The total is $15000 + $5000 = $20000.",
            "20000",
        ),
    ],
)
def test_gsm8k_v4_recovers_compact_non_thinking_conclusions(
    response: str, expected: str
) -> None:
    result = parse_gsm8k_v4_response_answers(response)
    assert result.final_response_answer == expected


def test_gsm8k_v4_refuses_unmarked_last_number() -> None:
    result = parse_gsm8k_v4_response_answers("We compute 15 + 5 and obtain 20.")
    assert result.final_response_answer is None
