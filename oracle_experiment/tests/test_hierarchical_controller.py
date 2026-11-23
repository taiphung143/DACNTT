from typing import Any

from adaptive_compute.controller.hierarchical_controller import (
    DATASET_DEPTHS,
    grouped_oof_probabilities,
    replay_oof_controller,
    summarize_policy_traces,
)


def test_grouped_oof_never_splits_one_problem_across_folds() -> None:
    rows: list[dict[str, Any]] = []
    for problem_index in range(15):
        for stage_index in (0, 1):
            rows.append(
                {
                    "group_id": f"gsm8k|p{problem_index}",
                    "feature_signal": float(problem_index + stage_index),
                    "label_escalate": int((problem_index + stage_index) % 4 == 0),
                }
            )

    probabilities, fold_ids, fold_audit, _ = grouped_oof_probabilities(
        rows,
        feature_names=("feature_signal",),
        folds=3,
        random_seed=7,
    )

    assert len(probabilities) == len(rows)
    assert all(0.0 <= value <= 1.0 for value in probabilities)
    assert all(row["group_overlap"] == 0 for row in fold_audit)
    folds_by_group: dict[str, set[int]] = {}
    for row, fold_id in zip(rows, fold_ids, strict=True):
        folds_by_group.setdefault(row["group_id"], set()).add(fold_id)
    assert all(len(values) == 1 for values in folds_by_group.values())


def _depth_rows(problem_id: str) -> list[dict[str, Any]]:
    depths = DATASET_DEPTHS["gsm8k"]
    return [
        {
            "dataset": "gsm8k",
            "problem_id": problem_id,
            "stage_index": stage_index,
            "question_sha256": "0" * 64,
            "label_escalate": 1,
            "current_L": depths[stage_index],
        }
        for stage_index in (0, 1)
    ]


def _breadth_rows(problem_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for length in DATASET_DEPTHS["gsm8k"]:
        k1_correct = int(length >= 1024)
        k2_correct = 1
        k4_correct = 1
        rows.extend(
            [
                {
                    "dataset": "gsm8k",
                    "problem_id": problem_id,
                    "current_L": length,
                    "stage_index": 0,
                    "question_sha256": "0" * 64,
                    "outcome_correct_before": k1_correct,
                    "outcome_correct_after": k2_correct,
                    "outcome_tokens_before": length,
                    "outcome_tokens_after": 2 * length,
                    "feature_state_valid_answer_count": 1,
                    "feature_state_truncation_count": 0,
                    "feature_state_agreement": -1.0,
                },
                {
                    "dataset": "gsm8k",
                    "problem_id": problem_id,
                    "current_L": length,
                    "stage_index": 1,
                    "question_sha256": "0" * 64,
                    "outcome_correct_before": k2_correct,
                    "outcome_correct_after": k4_correct,
                    "outcome_tokens_before": 2 * length,
                    "outcome_tokens_after": 4 * length,
                    "feature_state_valid_answer_count": 1,
                    "feature_state_truncation_count": 0,
                    "feature_state_agreement": 0.0,
                },
            ]
        )
    return rows


def test_oof_replay_applies_depth_then_paid_breadth_decisions() -> None:
    depth_rows = _depth_rows("p1")
    breadth_rows = _breadth_rows("p1")
    # Escalate low->mid, stop before high. At selected mid L, escalate k1->k2
    # and then stop before k4. Probabilities for unused L states are arbitrary.
    depth_probabilities = [0.9, 0.1]
    breadth_probabilities = [
        0.1,
        0.1,
        0.9,
        0.1,
        0.1,
        0.1,
    ]

    traces = replay_oof_controller(
        depth_rows,
        depth_probabilities,
        breadth_rows,
        breadth_probabilities,
        depth_threshold=0.5,
        breadth_threshold=0.5,
    )

    assert len(traces) == 1
    assert traces[0]["selected_L"] == 1024
    assert traces[0]["selected_k"] == 2
    assert traces[0]["correct"] == 1
    assert traces[0]["actual_generated_tokens"] == 2048


def test_policy_summary_keeps_raw_and_dataset_normalized_cost() -> None:
    traces = [
        {
            "dataset": "gsm8k",
            "policy_id": "test",
            "selected_L": 1024,
            "selected_k": 2,
            "correct": 1,
            "actual_generated_tokens": 1500,
            "normalized_actual_tokens": 1500 / 2048,
        },
        {
            "dataset": "math500",
            "policy_id": "test",
            "selected_L": 4096,
            "selected_k": 1,
            "correct": 0,
            "actual_generated_tokens": 3000,
            "normalized_actual_tokens": 3000 / 4096,
        },
    ]

    summary = summarize_policy_traces(traces)
    pooled = next(
        row
        for row in summary
        if row["dataset"] == "pooled" and row["policy_id"] == "test"
    )

    assert pooled["accuracy"] == 0.5
    assert pooled["mean_actual_generated_tokens"] == 2250
    assert 0.7 < pooled["mean_normalized_actual_tokens"] < 0.8
