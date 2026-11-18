import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from adaptive_compute.controller.sequential_data import (
    build_sequential_controller_dataset,
    marginal_utility_label,
)
from adaptive_compute.answer_parser import MATH500_ANSWER_PARSER_NAME
from adaptive_compute.math500 import (
    MATH500_DATASET_REVISION,
    MATH500_HF_DATASET_ID,
    MATH500_SPLIT,
)
from adaptive_compute.math500_splits import (
    MATH500_ASSIGNMENT_POLICY,
    MATH500_SPLIT_MANIFEST_TYPE,
)
from adaptive_compute.phase2_splits import (
    create_phase2_split_manifest,
    read_phase2_split_manifest,
)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _question(index: int) -> str:
    return f"If Sam has {index} apples and gets 2 more, how many apples total?"


def _source_manifest(count: int) -> dict[str, Any]:
    rows = [
        {
            "problem_id": f"gsm8k-test-{index:05d}",
            "source_index": index,
            "question_sha256": _sha256(_question(index)),
            "ground_truth": str(index + 2),
        }
        for index in range(count)
    ]
    return {
        "schema_version": 1,
        "dataset": "gsm8k",
        "dataset_id": "openai/gsm8k",
        "dataset_config": "main",
        "split": "test",
        "num_problems": count,
        "seed": 42,
        "dataset_size": 8,
        "problems": rows,
    }


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _make_fixture(tmp_path: Path) -> tuple[Path, Path]:
    development_path = tmp_path / "development.json"
    expanded_path = tmp_path / "expanded.json"
    audit_path = tmp_path / "audit.json"
    split_path = tmp_path / "split.json"
    _write_json(development_path, _source_manifest(6))
    _write_json(expanded_path, _source_manifest(8))
    _write_json(audit_path, {})
    create_phase2_split_manifest(
        development_manifest_path=development_path,
        expanded_pool_manifest_path=expanded_path,
        output_path=split_path,
        train_count=4,
        validation_count=2,
        test_count=2,
        split_seed=42,
        manual_audit_path=audit_path,
    )
    split = read_phase2_split_manifest(split_path)
    selected = split["partitions"]["train"][:2]

    experiment_dir = tmp_path / "experiment"
    experiment_dir.mkdir()
    _write_json(
        experiment_dir / "experiment_manifest.json",
        {
            "experiment_id": "synthetic-sequential-grid",
            "model": "Qwen/Qwen3-0.6B",
            "model_revision": "synthetic-revision",
            "prompt_template_name": "gsm8k_cot_v3",
            "answer_parser_name": "gsm8k_numeric_v3",
        },
    )
    raw_rows = []
    config_rows: list[dict[str, Any]] = []
    for problem_position, split_row in enumerate(selected):
        index = int(split_row["source_index"])
        raw_rows.append(
            {
                "problem_id": split_row["problem_id"],
                "repetition_id": 0,
                "question": _question(index),
                "ground_truth": str(index + 2),
                "prompt_tokens": 20 + index,
            }
        )
        for length in (512, 1024, 2048):
            for k in (1, 2, 4):
                # The first problem has useful escalations; the second does not.
                correct = problem_position == 0 and (
                    (length >= 1024 and k == 1) or k >= 2
                )
                actual_tokens = k * min(length, 100 + length // 8)
                valid = k if correct else 0
                config_rows.append(
                    {
                        "problem_id": split_row["problem_id"],
                        "k": k,
                        "L": length,
                        "repetition_id": 0,
                        "final_correct": correct,
                        "actual_generated_tokens": actual_tokens,
                        "allocated_token_budget": k * length,
                        "valid_answer_count": valid,
                        "invalid_answer_count": k - valid,
                        "valid_answer_fraction": valid / k,
                        "agreement": 1.0 if valid else "",
                        "sample_truncation_count": 0 if valid else k,
                    }
                )
    (experiment_dir / "raw_samples.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in raw_rows), encoding="utf-8"
    )
    _write_csv(experiment_dir / "config_results.csv", config_rows)
    return experiment_dir, split_path


def _math_split_row(index: int) -> dict[str, Any]:
    return {
        "problem_id": f"math500-test-{index:03d}",
        "source_index": index,
        "subject": "Algebra",
        "level": index % 5 + 1,
        "unique_id": f"test/algebra/{index}.json",
        "question_sha256": _sha256(_question(index)),
        "ground_truth_sha256": _sha256(str(index + 2)),
        "raw_answer_sha256": _sha256(str(index + 2)),
    }


def _problem_ids_hash(rows: list[dict[str, Any]]) -> str:
    return _sha256("\n".join(str(row["problem_id"]) for row in rows))


def _make_math_fixture(tmp_path: Path) -> tuple[Path, Path]:
    partitions = {
        "train": [_math_split_row(0), _math_split_row(1)],
        "validation": [_math_split_row(2)],
        "test": [_math_split_row(3)],
    }
    split_path = tmp_path / "math_split.json"
    _write_json(
        split_path,
        {
            "schema_version": 1,
            "manifest_type": MATH500_SPLIT_MANIFEST_TYPE,
            "status": "frozen",
            "dataset": "math500",
            "dataset_id": MATH500_HF_DATASET_ID,
            "dataset_revision": MATH500_DATASET_REVISION,
            "source_split": MATH500_SPLIT,
            "assignment_policy": MATH500_ASSIGNMENT_POLICY,
            "answer_parser_name": MATH500_ANSWER_PARSER_NAME,
            "source_pilot_manifest": {
                "sha256": "synthetic",
                "num_problems": 1,
                "problem_ids": [partitions["train"][0]["problem_id"]],
            },
            "partition_sizes": {
                name: len(rows) for name, rows in partitions.items()
            },
            "partition_problem_ids_sha256": {
                name: _problem_ids_hash(rows) for name, rows in partitions.items()
            },
            "partitions": partitions,
        },
    )

    experiment_dir = tmp_path / "math_experiment"
    experiment_dir.mkdir()
    _write_json(
        experiment_dir / "experiment_manifest.json",
        {
            "experiment_id": "synthetic-math-sequential-grid",
            "model": "Qwen/Qwen3-0.6B",
            "model_revision": "synthetic-revision",
            "prompt_template_name": "math500_cot_v1",
            "answer_parser_name": MATH500_ANSWER_PARSER_NAME,
            "L_values": [1024, 2048, 4096],
            "k_values": [1, 2, 4],
        },
    )
    raw_rows: list[dict[str, Any]] = []
    config_rows: list[dict[str, Any]] = []
    for problem_position, split_row in enumerate(partitions["train"]):
        index = int(split_row["source_index"])
        raw_rows.append(
            {
                "problem_id": split_row["problem_id"],
                "repetition_id": 0,
                "question": _question(index),
                "ground_truth": str(index + 2),
                "prompt_tokens": 30 + index,
            }
        )
        for length in (1024, 2048, 4096):
            for k in (1, 2, 4):
                correct = problem_position == 0 and (
                    (length >= 2048 and k == 1) or k >= 2
                )
                actual_tokens = k * min(length, 200 + length // 8)
                valid = k if correct else 0
                config_rows.append(
                    {
                        "problem_id": split_row["problem_id"],
                        "k": k,
                        "L": length,
                        "repetition_id": 0,
                        "final_correct": correct,
                        "actual_generated_tokens": actual_tokens,
                        "allocated_token_budget": k * length,
                        "valid_answer_count": valid,
                        "invalid_answer_count": k - valid,
                        "valid_answer_fraction": valid / k,
                        "agreement": 1.0 if valid else "",
                        "sample_truncation_count": 0 if valid else k,
                    }
                )
    (experiment_dir / "raw_samples.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in raw_rows), encoding="utf-8"
    )
    _write_csv(experiment_dir / "config_results.csv", config_rows)
    return experiment_dir, split_path


def test_marginal_utility_label_uses_realized_gain_and_normalized_cost() -> None:
    delta, label = marginal_utility_label(
        correct_before=False,
        correct_after=True,
        tokens_before=100,
        tokens_after=612,
        lambda_value=0.10,
        token_reference=2048,
    )
    assert delta == pytest.approx(0.975)
    assert label == 1

    delta, label = marginal_utility_label(
        correct_before=True,
        correct_after=True,
        tokens_before=100,
        tokens_after=612,
        lambda_value=0.10,
        token_reference=2048,
    )
    assert delta == pytest.approx(-0.025)
    assert label == 0

    with pytest.raises(ValueError, match="monotone"):
        marginal_utility_label(
            correct_before=False,
            correct_after=True,
            tokens_before=612,
            tokens_after=100,
            lambda_value=0.10,
            token_reference=2048,
        )


def test_builder_materializes_leakage_safe_stage_labels(tmp_path: Path) -> None:
    experiment_dir, split_path = _make_fixture(tmp_path)
    output_dir = tmp_path / "labels"
    manifest = build_sequential_controller_dataset(
        experiment_dir=experiment_dir,
        split_manifest_path=split_path,
        output_dir=output_dir,
    )

    assert manifest["held_out_test_materialized"] is False
    assert manifest["row_counts"] == {"depth": 12, "breadth": 36}
    with (output_dir / "depth_marginal_utility_labels.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        depth_rows = list(csv.DictReader(handle))
    with (output_dir / "breadth_marginal_utility_labels.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        breadth_rows = list(csv.DictReader(handle))
    assert {row["partition"] for row in depth_rows + breadth_rows} == {"train"}
    assert sum(int(row["label_escalate"]) for row in depth_rows) == 3
    assert sum(int(row["label_escalate"]) for row in breadth_rows) == 3

    schema = json.loads((output_dir / "feature_schema.json").read_text("utf-8"))
    assert schema["paid_state_feature_names"]
    assert all(
        name.startswith(("label_", "outcome_"))
        for name in schema["forbidden_as_model_inputs"]
    )
    assert not set(schema["forbidden_as_model_inputs"]) & set(
        schema["input_feature_names"] + schema["paid_state_feature_names"]
    )
    with pytest.raises(FileExistsError, match="already exists"):
        build_sequential_controller_dataset(
            experiment_dir=experiment_dir,
            split_manifest_path=split_path,
            output_dir=output_dir,
        )


def test_builder_rejects_changed_ground_truth(tmp_path: Path) -> None:
    experiment_dir, split_path = _make_fixture(tmp_path)
    raw_path = experiment_dir / "raw_samples.jsonl"
    rows = [json.loads(line) for line in raw_path.read_text("utf-8").splitlines()]
    rows[0]["ground_truth"] = "changed"
    raw_path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="ground-truth hash"):
        build_sequential_controller_dataset(
            experiment_dir=experiment_dir,
            split_manifest_path=split_path,
            output_dir=tmp_path / "labels",
        )


def test_builder_auto_detects_math500_frozen_contract(tmp_path: Path) -> None:
    experiment_dir, split_path = _make_math_fixture(tmp_path)
    output_dir = tmp_path / "math_labels"

    manifest = build_sequential_controller_dataset(
        experiment_dir=experiment_dir,
        split_manifest_path=split_path,
        output_dir=output_dir,
    )

    assert manifest["dataset"] == "math500"
    assert manifest["depth_action_space"] == [1024, 2048, 4096]
    assert manifest["breadth_action_space"] == [1, 2, 4]
    assert manifest["token_reference"] == 4096
    assert manifest["problem_counts"] == {"total": 2, "train": 2}
    assert manifest["row_counts"] == {"depth": 12, "breadth": 36}
    schema = json.loads((output_dir / "feature_schema.json").read_text("utf-8"))
    assert schema["dataset"] == "math500"
    assert schema["token_reference"] == 4096


def test_builder_rejects_non_frozen_math500_action_space(tmp_path: Path) -> None:
    experiment_dir, split_path = _make_math_fixture(tmp_path)

    with pytest.raises(ValueError, match="depth action space for math500"):
        build_sequential_controller_dataset(
            experiment_dir=experiment_dir,
            split_manifest_path=split_path,
            output_dir=tmp_path / "labels",
            depths=(512, 1024, 2048),
        )
