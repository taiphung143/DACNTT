import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from adaptive_compute.controller.depth_data import (
    build_depth_controller_dataset,
    choose_depth_target,
    extract_question_features,
)
from adaptive_compute.phase2_splits import create_phase2_split_manifest


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _question(index: int) -> str:
    return f"If Sam has {index} apples and gets 2 more, how many apples total?"


def _source_row(index: int) -> dict[str, Any]:
    return {
        "problem_id": f"gsm8k-test-{index:05d}",
        "source_index": index,
        "question_sha256": _sha256(_question(index)),
        "ground_truth": str(index + 2),
    }


def _source_manifest(count: int) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "dataset": "gsm8k",
        "dataset_id": "openai/gsm8k",
        "dataset_config": "main",
        "split": "test",
        "num_problems": count,
        "seed": 42,
        "dataset_size": 8,
        "problems": [_source_row(index) for index in range(count)],
    }


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _fixture_files(tmp_path: Path) -> tuple[Path, Path, Path]:
    development_path = tmp_path / "development.json"
    expanded_path = tmp_path / "expanded.json"
    audit_path = tmp_path / "audit.json"
    split_path = tmp_path / "split.json"
    _write_json(development_path, _source_manifest(6))
    _write_json(expanded_path, _source_manifest(8))
    _write_json(
        audit_path,
        {
            "gsm8k-test-00000": {
                "status": "manual_review_required",
                "note": "synthetic exclusion",
            }
        },
    )
    create_phase2_split_manifest(
        development_manifest_path=development_path,
        expanded_pool_manifest_path=expanded_path,
        output_path=split_path,
        train_count=3,
        validation_count=2,
        test_count=2,
        split_seed=42,
        manual_audit_path=audit_path,
    )

    raw_path = tmp_path / "raw.jsonl"
    raw_rows = [
        {
            "problem_id": f"gsm8k-test-{index:05d}",
            "repetition_id": 0,
            "question": _question(index),
            "prompt_tokens": 20 + index,
            "ground_truth": str(index + 2),
        }
        for index in range(1, 6)
    ]
    _write_jsonl(raw_path, raw_rows)

    correctness = {
        1: (True, True, True),
        2: (False, True, True),
        3: (False, False, True),
        4: (False, False, False),
        5: (True, True, True),
    }
    config_path = tmp_path / "config.csv"
    config_rows: list[dict[str, Any]] = []
    for index, pattern in correctness.items():
        for depth, correct in zip((512, 1024, 2048), pattern, strict=True):
            config_rows.append(
                {
                    "problem_id": f"gsm8k-test-{index:05d}",
                    "k": 1,
                    "L": depth,
                    "repetition_id": 0,
                    "final_correct": correct,
                    "actual_generated_tokens": min(depth, 100 + index),
                    "sum_sample_latency_ms": float(depth),
                    "sample_truncation_count": int(not correct),
                    "valid_answer_fraction": float(correct),
                }
            )
    _write_csv(config_path, config_rows)
    return raw_path, config_path, split_path


def test_question_features_are_input_only_and_deterministic() -> None:
    features = extract_question_features(
        "A baker has 3 dozen rolls at $4 each. How much is the total?", 24
    )

    assert features["feature_prompt_token_count"] == 24
    assert features["feature_number_count"] == 2
    assert features["feature_currency_symbol_count"] == 1
    assert features["feature_has_each"] == 1
    assert features["feature_has_how_much"] == 1
    assert features["feature_has_total"] == 1
    assert all(name.startswith("feature_") for name in features)


def test_depth_target_uses_lowest_success_and_marks_unsolved_fallback() -> None:
    assert choose_depth_target({512: False, 1024: True, 2048: True}) == (
        1024,
        1024,
        "observed_success",
    )
    assert choose_depth_target({512: False, 1024: False, 2048: False}) == (
        2048,
        None,
        "max_depth_fallback_unsolved",
    )


def test_build_dataset_materializes_only_train_and_validation(tmp_path: Path) -> None:
    raw_path, config_path, split_path = _fixture_files(tmp_path)
    output_dir = tmp_path / "output"

    manifest = build_depth_controller_dataset(
        raw_samples_path=raw_path,
        config_results_path=config_path,
        split_manifest_path=split_path,
        output_dir=output_dir,
        source_experiment_id="synthetic",
    )

    assert manifest["row_counts"] == {"total": 5, "train": 3, "validation": 2}
    assert manifest["held_out_test_materialized"] is False
    with (output_dir / "depth_controller_development.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert {row["partition"] for row in rows} == {"train", "validation"}
    assert "gsm8k-test-00006" not in {row["problem_id"] for row in rows}
    assert "question" not in rows[0]
    by_id = {row["problem_id"]: row for row in rows}
    assert by_id["gsm8k-test-00002"]["label_depth_target_L"] == "1024"
    assert by_id["gsm8k-test-00004"]["label_target_status"] == (
        "max_depth_fallback_unsolved"
    )
    schema = json.loads((output_dir / "feature_schema.json").read_text(encoding="utf-8"))
    assert all(name.startswith("feature_") for name in schema["feature_names"])
    assert all(
        name.startswith(("label_", "outcome_"))
        for name in schema["forbidden_as_model_inputs"]
    )


def test_build_dataset_rejects_changed_question(tmp_path: Path) -> None:
    raw_path, config_path, split_path = _fixture_files(tmp_path)
    rows = [json.loads(line) for line in raw_path.read_text(encoding="utf-8").splitlines()]
    rows[0]["question"] = "Changed after split freeze"
    _write_jsonl(raw_path, rows)

    with pytest.raises(ValueError, match="question hash mismatch"):
        build_depth_controller_dataset(
            raw_samples_path=raw_path,
            config_results_path=config_path,
            split_manifest_path=split_path,
            output_dir=tmp_path / "output",
            source_experiment_id="synthetic",
        )
