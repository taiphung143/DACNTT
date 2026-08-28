from analysis.oracle import select_min_cost_success
from analysis.depth_diagnostics import summarize_by_depth
from analysis.summarize import summarize_profiles
from audit_results import select_audit_candidates
from validate_pilot import build_validation_report


def _samples():
    return [
        {
            "problem_id": "p1",
            "k": 1,
            "L": 512,
            "correct": False,
            "truncated": True,
            "truncation_stage": "during_thinking",
            "failure_type": "truncated_before_answer",
            "explicit_final_answer_found": False,
            "thinking_started": True,
            "thinking_completed": False,
            "token_budget_utilization": 1.0,
            "parse_error": True,
            "final_response_answer": None,
            "reasoning_answer": None,
            "final_correct": False,
            "reasoning_correct": None,
            "generated_tokens": 512,
            "latency_ms": 10.0,
        },
        {
            "problem_id": "p2",
            "k": 1,
            "L": 512,
            "correct": True,
            "truncated": False,
            "truncation_stage": "none",
            "failure_type": "correct",
            "explicit_final_answer_found": True,
            "thinking_started": True,
            "thinking_completed": True,
            "token_budget_utilization": 0.5,
            "parse_error": False,
            "final_response_answer": "42",
            "reasoning_answer": "42",
            "final_correct": True,
            "reasoning_correct": True,
            "generated_tokens": 256,
            "latency_ms": 5.0,
        },
    ]


def test_profile_summary_separates_truncation_and_parse_failure() -> None:
    summary = summarize_profiles(_samples())[0]

    assert summary["accuracy"] == 0.5
    assert summary["truncation_rate"] == 0.5
    assert summary["parse_failure_rate"] == 0.0
    assert summary["thinking_completion_rate"] == 0.5
    assert summary["mean_token_budget_utilization"] == 0.75


def test_oracle_ignores_correct_flag_without_valid_majority() -> None:
    invalid = {
        "final_correct": True,
        "valid_answer_count": 0,
        "majority_answer": None,
        "actual_generated_tokens": 10,
    }
    valid = {
        "final_correct": True,
        "valid_answer_count": 1,
        "majority_answer": "42",
        "actual_generated_tokens": 20,
        "allocated_token_budget": 512,
        "k": 1,
        "L": 512,
    }
    more_expensive_valid = {
        **valid,
        "actual_generated_tokens": 40,
        "allocated_token_budget": 1024,
        "L": 1024,
    }

    assert select_min_cost_success([invalid, more_expensive_valid, valid]) is valid
    assert select_min_cost_success([invalid]) is None


def test_validation_report_and_audit_selection() -> None:
    report = build_validation_report(_samples())
    candidates = select_audit_candidates(_samples())

    assert report["total_samples"] == 2
    assert report["truncated_before_answer"] == 1
    assert report["truncation_rate"] == 0.5
    assert len(candidates) == 1
    assert candidates[0]["problem_id"] == "p1"


def test_depth_diagnostic_reports_stage_breakdown() -> None:
    rows = summarize_by_depth(_samples())

    assert rows[0]["L"] == 512
    assert rows[0]["during_thinking_truncation_rate"] == 0.5
    assert rows[0]["after_thinking_truncation_rate"] == 0.0
