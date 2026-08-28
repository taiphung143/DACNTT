import pytest

from aggregation import aggregate_answers, build_configuration_summary


def test_majority_ignores_invalid_samples() -> None:
    result = aggregate_answers([None, "42", "42", "40"])

    assert result.majority_answer == "42"
    assert result.valid_answer_count == 3
    assert result.invalid_answer_count == 1
    assert result.agreement_among_valid == pytest.approx(2 / 3)
    assert result.agreement == pytest.approx(2 / 3)
    assert result.valid_answer_fraction == 0.75


def test_all_invalid_samples_do_not_crash() -> None:
    result = aggregate_answers([None, None, None])

    assert result.majority_answer is None
    assert result.valid_answer_count == 0
    assert result.invalid_answer_count == 3
    assert result.agreement is None


def test_tie_breaking_uses_lowest_valid_sample_index() -> None:
    assert aggregate_answers(["40", "42"]).majority_answer == "40"


def test_main_aggregation_uses_final_not_reasoning_answers() -> None:
    samples = [
        {
            "problem_id": "p1",
            "k": 2,
            "L": 512,
            "final_response_answer": None,
            "reasoning_answer": "42",
            "ground_truth": "42",
            "generated_tokens": 512,
            "prompt_tokens": 10,
            "latency_ms": 1.0,
            "token_budget_utilization": 1.0,
            "truncated": True,
            "truncation_stage": "after_thinking",
            "failure_type": "truncated_after_reasoning",
            "dataset_quality_flag": None,
        },
        {
            "problem_id": "p1",
            "k": 2,
            "L": 512,
            "final_response_answer": "40",
            "reasoning_answer": "42",
            "ground_truth": "42",
            "generated_tokens": 400,
            "prompt_tokens": 10,
            "latency_ms": 1.0,
            "token_budget_utilization": 0.8,
            "truncated": False,
            "truncation_stage": "none",
            "failure_type": "wrong_answer",
            "dataset_quality_flag": None,
        },
    ]

    summary = build_configuration_summary(samples)

    assert summary["final_majority_answer"] == "40"
    assert summary["majority_answer"] == "40"
    assert summary["reasoning_majority_answer"] == "42"
    assert summary["final_correct"] is False
    assert summary["reasoning_correct"] is True


def test_configuration_summary_tracks_invalid_and_compute() -> None:
    samples = [
        {
            "problem_id": "p1",
            "question": "q",
            "k": 2,
            "L": 512,
            "parsed_answer": None,
            "final_response_answer": None,
            "reasoning_answer": None,
            "ground_truth": "42",
            "truncated": True,
            "failure_type": "truncated_before_answer",
            "generated_tokens": 512,
            "prompt_tokens": 10,
            "latency_ms": 20.0,
            "token_budget_utilization": 1.0,
        },
        {
            "problem_id": "p1",
            "question": "q",
            "k": 2,
            "L": 512,
            "parsed_answer": "42",
            "final_response_answer": "42",
            "reasoning_answer": None,
            "ground_truth": "42",
            "truncated": False,
            "failure_type": "correct",
            "generated_tokens": 256,
            "prompt_tokens": 10,
            "latency_ms": 10.0,
            "token_budget_utilization": 0.5,
        },
    ]

    summary = build_configuration_summary(samples)

    assert summary["valid_answer_count"] == 1
    assert summary["invalid_answer_count"] == 1
    assert summary["final_correct"] is True
    assert summary["sample_truncation_count"] == 1
    assert summary["actual_generated_tokens"] == 768
    assert summary["avg_token_budget_utilization"] == 0.75
