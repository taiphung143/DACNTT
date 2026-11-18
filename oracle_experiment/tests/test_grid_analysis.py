from math import isnan

from adaptive_compute.analysis.aggregate import (
    build_config_results,
    build_grid_summary,
    build_iso_budget_summary,
)
from adaptive_compute.analysis.behavior_analysis import classify_problem
from adaptive_compute.analysis.oracle import build_oracle_comparison, select_min_cost_success
from adaptive_compute.analysis.pareto import pareto_frontier
from adaptive_compute.analysis.plots import _number


def _sample(problem: str, sample_id: int, *, length: int = 512, answer: str | None = "7", flagged: str | None = None) -> dict:
    return {
        "experiment_id": "e",
        "problem_id": problem,
        "question": "3+4?",
        "L": length,
        "sample_id": sample_id,
        "repetition_id": 0,
        "model_revision": "r",
        "prompt_hash": "h",
        "final_response_answer": answer,
        "reasoning_answer": answer,
        "ground_truth": "7",
        "dataset_quality_flag": flagged,
        "truncated": answer is None,
        "truncation_stage": "during_thinking" if answer is None else "none",
        "failure_type": "truncated_before_answer" if answer is None else "correct",
        "generated_tokens": 500,
        "prompt_tokens": 10,
        "latency_ms": 20.0,
        "token_budget_utilization": 500 / length,
    }


def test_config_results_use_prefix_and_sum_realized_compute() -> None:
    records = [_sample("p1", index, answer=None if index == 1 else "7") for index in range(4)]
    rows = build_config_results(records, [1, 2, 4])
    by_k = {row["k"]: row for row in rows}
    assert by_k[1]["sample_ids"] == "0"
    assert by_k[2]["sample_ids"] == "0|1"
    assert by_k[4]["sample_ids"] == "0|1|2|3"
    assert by_k[4]["actual_generated_tokens"] == 2000
    assert by_k[4]["allocated_token_budget"] == 2048
    assert by_k[4]["valid_answer_fraction"] == 0.75


def test_grid_summary_excludes_flagged_accuracy_but_keeps_counts() -> None:
    records = [_sample("p1", 0), _sample("p2", 0, answer="8", flagged="manual_review_required")]
    summary = build_grid_summary(build_config_results(records, [1]))[0]
    assert summary["num_total_problems"] == 2
    assert summary["num_evaluated_problems"] == 1
    assert summary["num_flagged_problems"] == 1
    assert summary["final_accuracy"] == 1.0


def test_plot_number_converts_missing_metrics_to_nan() -> None:
    assert isnan(_number({"avg_agreement": None}, "avg_agreement"))
    assert isnan(_number({"avg_agreement": ""}, "avg_agreement"))


def test_iso_budget_selects_three_requested_profiles() -> None:
    rows = [
        {"k": k, "L": length, "final_accuracy": .5, "avg_generated_tokens": 100, "avg_latency_ms": 2, "avg_valid_answer_fraction": 1, "avg_agreement": 1}
        for k, length in ((4, 512), (2, 1024), (1, 2048), (1, 512))
    ]
    assert {row["profile"] for row in build_iso_budget_summary(rows)} == {"4x512", "2x1024", "1x2048"}


def test_pareto_frontier_uses_true_dominance() -> None:
    rows = [
        {"name": "a", "avg_generated_tokens": 10, "final_accuracy": .5},
        {"name": "b", "avg_generated_tokens": 20, "final_accuracy": .4},
        {"name": "c", "avg_generated_tokens": 30, "final_accuracy": .8},
    ]
    assert [row["name"] for row in pareto_frontier(rows)] == ["a", "c"]


def test_oracle_tie_breaks_on_latency_after_actual_tokens() -> None:
    common = {"final_correct": True, "valid_answer_count": 1, "majority_answer": "7", "actual_generated_tokens": 10, "allocated_token_budget": 20, "dataset_quality_flag": None}
    slow = {**common, "k": 1, "L": 20, "sum_sample_latency_ms": 9}
    fast = {**common, "k": 2, "L": 10, "sum_sample_latency_ms": 3}
    assert select_min_cost_success([slow, fast]) is fast


def test_behavior_classification_reports_depth_and_non_monotonic() -> None:
    rows = [
        {"problem_id": "p", "k": 1, "L": 512, "final_correct": False},
        {"problem_id": "p", "k": 1, "L": 1024, "final_correct": True},
        {"problem_id": "p", "k": 2, "L": 1024, "final_correct": False},
    ]
    result = classify_problem(rows)
    assert "DEPTH_BENEFITING" in result["labels"]
    assert "POSSIBLE_NON_MONOTONIC" in result["labels"]


def test_oracle_comparison_has_four_strategies() -> None:
    samples = []
    for length in (512, 1024):
        for sample_id in range(2):
            samples.append(_sample("p", sample_id, length=length, answer="7"))
    config_rows = build_config_results(samples, [1, 2])
    comparison, anchors = build_oracle_comparison(config_rows)
    assert {row["strategy"] for row in comparison} == {"best_fixed", "breadth_oracle", "depth_oracle", "joint_oracle"}
    assert anchors
