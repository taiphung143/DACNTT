from __future__ import annotations

import json
from pathlib import Path

import pytest

from adaptive_compute.problem_snapshot import load_phase2_partition_from_snapshot


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_load_gsm_snapshot_checks_frozen_hashes(tmp_path: Path) -> None:
    import hashlib

    question = "What is 1 + 1?"
    answer = "2"
    raw = "#### 2"
    digest = lambda value: hashlib.sha256(value.encode("utf-8")).hexdigest()
    manifest = {
        "schema_version": 1,
        "manifest_type": "phase2_train_validation_test_split",
        "status": "frozen",
        "dataset": "gsm8k",
        "dataset_id": "openai/gsm8k",
        "dataset_config": "main",
        "source_split": "test",
        "dataset_size": 1,
        "split_seed": 42,
        "assignment_policy": "phase2-problem-split-v1",
        "source_manifests": {
            "development": {"sha256": "a" * 64, "num_problems": 1},
            "expanded_pool": {"sha256": "b" * 64, "num_problems": 1},
            "manual_audit": {"sha256": "c" * 64, "num_entries": 0},
        },
        "excluded_from_development": [],
        "partition_sizes": {"train": 1, "validation": 0, "test": 0},
        "partition_problem_ids_sha256": {
            "train": digest("gsm8k-test-00000"),
            "validation": digest(""),
            "test": digest(""),
        },
        "partitions": {
            "train": [{
                "problem_id": "gsm8k-test-00000",
                "source_index": 0,
                "question_sha256": digest(question),
                "ground_truth_sha256": digest(answer),
            }],
            "validation": [],
            "test": [],
        },
    }
    manifest_path = tmp_path / "split.json"
    snapshot_path = tmp_path / "raw.jsonl"
    _write_json(manifest_path, manifest)
    snapshot_path.write_text(
        json.dumps({
            "dataset": "gsm8k",
            "problem_id": "gsm8k-test-00000",
            "question": question,
            "ground_truth": answer,
            "ground_truth_raw": raw,
        }) + "\n",
        encoding="utf-8",
    )

    problems = load_phase2_partition_from_snapshot(
        dataset_name="gsm8k",
        split_manifest_path=manifest_path,
        partition="train",
        snapshot_path=snapshot_path,
    )
    assert problems[0].question == question

    snapshot_path.write_text(
        snapshot_path.read_text(encoding="utf-8").replace(question, "Changed"),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="question hash mismatch"):
        load_phase2_partition_from_snapshot(
            dataset_name="gsm8k",
            split_manifest_path=manifest_path,
            partition="train",
            snapshot_path=snapshot_path,
        )
