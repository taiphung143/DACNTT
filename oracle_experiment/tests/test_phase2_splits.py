import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from adaptive_compute.cli.run_grid import main as run_grid_main
from adaptive_compute.phase2_splits import (
    create_phase2_split_manifest,
    load_phase2_partition,
    read_phase2_split_manifest,
    validate_phase2_split_manifest,
)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _records(count: int = 8) -> list[dict[str, str]]:
    return [
        {
            "question": f"What is {index} + 0?",
            "answer": f"No change is needed.\n#### {index}",
        }
        for index in range(count)
    ]


def _row(index: int) -> dict[str, Any]:
    return {
        "problem_id": f"gsm8k-test-{index:05d}",
        "source_index": index,
        "question_sha256": _sha256(f"What is {index} + 0?"),
        "ground_truth": str(index),
    }


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


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
        "problems": [_row(index) for index in range(count)],
    }


def _create_fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
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
    return development_path, expanded_path, audit_path, split_path


def test_phase2_split_is_frozen_disjoint_and_label_blind(tmp_path: Path) -> None:
    _, _, _, split_path = _create_fixture(tmp_path)
    payload = read_phase2_split_manifest(split_path)

    assert payload["status"] == "frozen"
    assert payload["partition_sizes"] == {"train": 3, "validation": 2, "test": 2}
    assert payload["excluded_from_development"][0]["problem_id"] == "gsm8k-test-00000"
    rows = [row for partition in payload["partitions"].values() for row in partition]
    assert len({row["problem_id"] for row in rows}) == 7
    assert len({row["source_index"] for row in rows}) == 7
    assert all("ground_truth" not in row for row in rows)
    assert all(len(row["ground_truth_sha256"]) == 64 for row in rows)
    assert {row["source_index"] for row in payload["partitions"]["test"]} == {6, 7}


def test_phase2_split_creation_is_idempotent_but_refuses_reassignment(tmp_path: Path) -> None:
    development_path, expanded_path, audit_path, split_path = _create_fixture(tmp_path)
    original = split_path.read_bytes()
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
    assert split_path.read_bytes() == original

    with pytest.raises(FileExistsError, match="frozen Phase 2 split"):
        create_phase2_split_manifest(
            development_manifest_path=development_path,
            expanded_pool_manifest_path=expanded_path,
            output_path=split_path,
            train_count=3,
            validation_count=2,
            test_count=2,
            split_seed=7,
            manual_audit_path=audit_path,
        )


def test_manifest_validator_rejects_cross_partition_overlap(tmp_path: Path) -> None:
    _, _, _, split_path = _create_fixture(tmp_path)
    payload = read_phase2_split_manifest(split_path)
    payload["partitions"]["test"][0] = dict(payload["partitions"]["train"][0])

    with pytest.raises(ValueError, match="hash mismatch|overlap"):
        validate_phase2_split_manifest(payload)


def test_load_partition_verifies_dataset_records_and_audit(tmp_path: Path) -> None:
    _, _, audit_path, split_path = _create_fixture(tmp_path)
    records = _records()

    def loader(*args: Any, **kwargs: Any) -> list[dict[str, str]]:
        assert args == ("openai/gsm8k", "main")
        assert kwargs["split"] == "test"
        return records

    problems = load_phase2_partition(
        manifest_path=split_path,
        partition="test",
        manual_audit_path=audit_path,
        dataset_loader=loader,
    )
    assert {problem.source_index for problem in problems} == {6, 7}

    records[6]["question"] = "Changed after freezing"
    with pytest.raises(ValueError, match="question changed"):
        load_phase2_partition(
            manifest_path=split_path,
            partition="test",
            manual_audit_path=audit_path,
            dataset_loader=loader,
        )

    records[6]["question"] = "What is 6 + 0?"
    _write_json(audit_path, {})
    with pytest.raises(ValueError, match="manual audit changed"):
        load_phase2_partition(
            manifest_path=split_path,
            partition="test",
            manual_audit_path=audit_path,
            dataset_loader=loader,
        )


def test_split_rejects_expanded_pool_that_changes_development_prefix(tmp_path: Path) -> None:
    development_path, expanded_path, audit_path, _ = _create_fixture(tmp_path)
    expanded = json.loads(expanded_path.read_text(encoding="utf-8"))
    expanded["problems"][1]["question_sha256"] = "0" * 64
    _write_json(expanded_path, expanded)

    with pytest.raises(ValueError, match="does not preserve the development prefix"):
        create_phase2_split_manifest(
            development_manifest_path=development_path,
            expanded_pool_manifest_path=expanded_path,
            output_path=tmp_path / "other.json",
            train_count=3,
            validation_count=2,
            test_count=2,
            split_seed=42,
            manual_audit_path=audit_path,
        )


def test_run_grid_validate_only_accepts_exact_frozen_partition(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _, _, _, split_path = _create_fixture(tmp_path)

    assert (
        run_grid_main(
            [
                "--num-problems",
                "3",
                "--phase2-split-manifest",
                str(split_path),
                "--phase2-partition",
                "train",
                "--validate-only",
            ]
        )
        == 0
    )
    output = json.loads(capsys.readouterr().out)
    assert output["dataset_partition"] == "train"
    assert output["expected_unique_generations"] == 36


def test_run_grid_rejects_count_different_from_frozen_partition(tmp_path: Path) -> None:
    _, _, _, split_path = _create_fixture(tmp_path)

    with pytest.raises(ValueError, match="selected train problem count"):
        run_grid_main(
            [
                "--num-problems",
                "2",
                "--phase2-split-manifest",
                str(split_path),
                "--phase2-partition",
                "train",
                "--validate-only",
            ]
        )


def test_run_grid_validate_only_accepts_train_prefix(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _, _, _, split_path = _create_fixture(tmp_path)

    assert (
        run_grid_main(
            [
                "--num-problems",
                "2",
                "--phase2-split-manifest",
                str(split_path),
                "--phase2-partition",
                "train",
                "--phase2-limit",
                "2",
                "--validate-only",
            ]
        )
        == 0
    )
    output = json.loads(capsys.readouterr().out)
    assert output["dataset_partition"] == "train"
    assert output["num_problems"] == 2
    assert output["expected_unique_generations"] == 24


def test_run_grid_validate_only_records_non_thinking_mode(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _, _, _, split_path = _create_fixture(tmp_path)

    assert (
        run_grid_main(
            [
                "--num-problems",
                "2",
                "--phase2-split-manifest",
                str(split_path),
                "--phase2-partition",
                "train",
                "--phase2-limit",
                "2",
                "--disable-thinking",
                "--validate-only",
            ]
        )
        == 0
    )
    output = json.loads(capsys.readouterr().out)
    assert output["enable_thinking"] is False


def test_run_grid_validate_only_records_force_answer_strategy(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _, _, _, split_path = _create_fixture(tmp_path)

    assert (
        run_grid_main(
            [
                "--num-problems",
                "2",
                "--phase2-split-manifest",
                str(split_path),
                "--phase2-partition",
                "train",
                "--phase2-limit",
                "2",
                "--l-values",
                "512",
                "--decoding-strategy",
                "force_answer",
                "--answer-reserve-tokens",
                "128",
                "--validate-only",
            ]
        )
        == 0
    )
    output = json.loads(capsys.readouterr().out)
    assert output["decoding_strategy"] == "force_answer"
    assert output["decoding_strategy_version"] == "force_answer_v2"
    assert output["answer_reserve_tokens"] == 128


def test_run_grid_rejects_test_prefix(tmp_path: Path) -> None:
    _, _, _, split_path = _create_fixture(tmp_path)

    with pytest.raises(ValueError, match="not allowed for the held-out test"):
        run_grid_main(
            [
                "--num-problems",
                "1",
                "--phase2-split-manifest",
                str(split_path),
                "--phase2-partition",
                "test",
                "--phase2-limit",
                "1",
                "--validate-only",
            ]
        )
