import csv
import json
from pathlib import Path
from typing import Any

import pytest

from adaptive_compute.controller.depth_baseline import (
    evaluate_depth_policy,
    quantile_depth_predictions,
    train_depth_only_baseline,
)


def _row(problem_id: str, partition: str, target: int, feature_value: float) -> dict[str, Any]:
    row: dict[str, Any] = {
        "problem_id": problem_id,
        "partition": partition,
        "question_sha256": "0" * 64,
        "feature_length": feature_value,
        "feature_count": feature_value / 2,
        "label_depth_target_L": target,
        "label_observed_lowest_correct_L": target,
        "label_target_status": "observed_success",
        "label_escalate_beyond_512": int(target > 512),
        "label_escalate_beyond_1024": int(target > 1024),
    }
    for depth in (512, 1024, 2048):
        correct = int(depth >= target)
        row.update(
            {
                f"outcome_k1_correct_L{depth}": correct,
                f"outcome_k1_actual_tokens_L{depth}": min(depth, target),
                f"outcome_k1_latency_ms_L{depth}": float(min(depth, target)),
                f"outcome_k1_truncated_L{depth}": int(not correct),
                f"outcome_k1_valid_answer_fraction_L{depth}": float(correct),
            }
        )
    return row


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _data_dir(tmp_path: Path) -> Path:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    train_rows = [
        _row(f"train-{index}", "train", target, float(index + 1))
        for index, target in enumerate((512, 512, 512, 1024, 1024, 1024, 2048, 2048, 2048))
    ]
    validation_rows = [
        _row("validation-1", "validation", 512, 1.5),
        _row("validation-2", "validation", 1024, 4.5),
        _row("validation-3", "validation", 2048, 8.5),
    ]
    _write_csv(data_dir / "depth_controller_train.csv", train_rows)
    _write_csv(data_dir / "depth_controller_validation.csv", validation_rows)
    (data_dir / "feature_schema.json").write_text(
        json.dumps(
            {
                "feature_names": ["feature_length", "feature_count"],
                "forbidden_as_model_inputs": [
                    "label_depth_target_L",
                    "outcome_k1_correct_L512",
                ],
            }
        ),
        encoding="utf-8",
    )
    (data_dir / "dataset_manifest.json").write_text(
        json.dumps({"held_out_test_materialized": False}), encoding="utf-8"
    )
    return data_dir


def test_quantile_depth_predictions_respects_ordered_classes() -> None:
    probabilities = [[0.6, 0.3, 0.1], [0.1, 0.4, 0.5]]
    classes = [512, 1024, 2048]

    assert quantile_depth_predictions(probabilities, classes, 0.5) == [512, 1024]
    assert quantile_depth_predictions(probabilities, classes, 0.9) == [1024, 2048]


def test_policy_evaluation_charges_selected_observed_cost() -> None:
    rows = [
        {key: str(value) for key, value in _row("p1", "validation", 1024, 1.0).items()}
    ]
    metrics = evaluate_depth_policy(rows, [1024], strategy="test")

    assert metrics["policy_accuracy"] == 1.0
    assert metrics["avg_actual_generated_tokens"] == 1024
    assert metrics["avg_allocated_token_budget"] == 1024


def test_training_uses_only_allowlisted_features_and_writes_artifacts(tmp_path: Path) -> None:
    data_dir = _data_dir(tmp_path)
    output_dir = tmp_path / "model"

    manifest = train_depth_only_baseline(
        data_dir=data_dir,
        output_dir=output_dir,
        c_values=(1.0,),
        class_weights=(None,),
        decision_quantiles=(0.5,),
    )

    assert manifest["held_out_test_used"] is False
    assert manifest["num_candidates"] == 1
    assert manifest["feature_names"] == ["feature_length", "feature_count"]
    assert (output_dir / "depth_logistic_model.joblib").exists()
    assert (output_dir / "validation_policy_summary.csv").exists()
    assert "not confirmatory evidence" in (output_dir / "development_report.md").read_text(
        encoding="utf-8"
    )


def test_training_rejects_label_in_feature_allowlist(tmp_path: Path) -> None:
    data_dir = _data_dir(tmp_path)
    (data_dir / "feature_schema.json").write_text(
        json.dumps(
            {
                "feature_names": ["feature_length", "label_depth_target_L"],
                "forbidden_as_model_inputs": ["label_depth_target_L"],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="non-feature model input"):
        train_depth_only_baseline(data_dir=data_dir, output_dir=tmp_path / "model")
