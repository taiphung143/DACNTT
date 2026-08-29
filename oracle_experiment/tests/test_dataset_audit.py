from pathlib import Path

from analysis.oracle import select_min_cost_success
from analysis.pareto import pareto_eligible_records
from dataset_audit import get_dataset_quality_flag, load_manual_audit
from reprocess_results import reprocess_record


def test_known_item_is_manually_flagged() -> None:
    entries = load_manual_audit(Path("data/manual_audit.json"))

    assert (
        get_dataset_quality_flag("gsm8k-test-01309", entries)
        == "manual_review_required"
    )


def test_manual_flag_does_not_mutate_ground_truth() -> None:
    entries = load_manual_audit(Path("data/manual_audit.json"))
    raw_ground_truth = "Rationale with official label.\n#### 2280"
    record = {
        "problem_id": "gsm8k-test-01309",
        "L": 1024,
        "raw_response": "<think>#### 2180</think> unfinished final",
        "ground_truth": "2280",
        "ground_truth_raw": raw_ground_truth,
        "generated_tokens": 1024,
        "finish_reason": "length",
    }

    updated = reprocess_record(record, audit_entries=entries)

    assert updated["dataset_quality_flag"] == "manual_review_required"
    assert updated["ground_truth"] == "2280"
    assert updated["ground_truth_raw"] == raw_ground_truth
    assert updated["reasoning_answer"] == "2180"
    assert updated["reasoning_correct"] is None
    assert updated["final_response_answer"] is None
    assert updated["failure_type"] == "truncated_after_reasoning"


def test_flagged_item_is_excluded_from_pareto_inputs() -> None:
    records = [
        {
            "final_correct": True,
            "reasoning_correct": True,
            "dataset_quality_flag": "manual_review_required",
            "truncated": False,
            "truncation_stage": "none",
            "final_response_answer": "42",
            "reasoning_answer": "42",
            "generated_tokens": 10,
            "latency_ms": 1.0,
            "token_budget_utilization": 0.1,
            "failure_type": "correct",
        },
        {
            "final_correct": False,
            "reasoning_correct": False,
            "dataset_quality_flag": None,
            "truncated": False,
            "truncation_stage": "none",
            "final_response_answer": "40",
            "reasoning_answer": "40",
            "generated_tokens": 10,
            "latency_ms": 1.0,
            "token_budget_utilization": 0.1,
            "failure_type": "wrong_answer",
        },
    ]

    assert len(pareto_eligible_records(records)) == 1


def test_flagged_configuration_is_excluded_from_oracle() -> None:
    flagged = {
        "final_correct": True,
        "valid_answer_count": 1,
        "majority_answer": "42",
        "actual_generated_tokens": 1,
        "dataset_quality_flag": "manual_review_required",
    }

    assert select_min_cost_success([flagged]) is None
