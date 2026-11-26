"""Frozen MATH-500 Train/Validation/Test partitions for the 0.6B study."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from adaptive_compute.answer_parser import MATH500_ANSWER_PARSER_NAME
from adaptive_compute.dataset import DatasetLoader
from adaptive_compute.math500 import (
    MATH500_DATASET_REVISION,
    MATH500_HF_DATASET_ID,
    MATH500_PILOT_SEED,
    MATH500_SPLIT,
    Math500Problem,
    load_math500_indices,
    load_math500_subset,
)
from adaptive_compute.phase2_splits import file_sha256


MATH500_SPLIT_SCHEMA_VERSION = 1
MATH500_SPLIT_MANIFEST_TYPE = "math500_train_validation_test_split"
MATH500_ASSIGNMENT_POLICY = "math500-stratified-prefix-split-v1"
MATH500_PARTITIONS = ("train", "validation", "test")
DEFAULT_TRAIN_COUNT = 80
DEFAULT_VALIDATION_COUNT = 20
DEFAULT_TEST_COUNT = 100


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read required JSON {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return payload


def _problem_ids_sha256(rows: Sequence[Mapping[str, Any]]) -> str:
    return _sha256_text("\n".join(str(row["problem_id"]) for row in rows))


def _split_row(problem: Math500Problem) -> dict[str, Any]:
    return {
        "problem_id": problem.problem_id,
        "source_index": problem.source_index,
        "subject": problem.subject,
        "level": problem.level,
        "unique_id": problem.unique_id,
        "question_sha256": _sha256_text(problem.question),
        "ground_truth_sha256": _sha256_text(problem.ground_truth),
        "raw_answer_sha256": _sha256_text(problem.ground_truth_raw),
    }


def _distribution(rows: Sequence[Mapping[str, Any]], field: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row[field]) for row in rows).items()))


def validate_math500_split_manifest(payload: Mapping[str, Any]) -> None:
    expected = {
        "schema_version": MATH500_SPLIT_SCHEMA_VERSION,
        "manifest_type": MATH500_SPLIT_MANIFEST_TYPE,
        "status": "frozen",
        "dataset": "math500",
        "dataset_id": MATH500_HF_DATASET_ID,
        "dataset_revision": MATH500_DATASET_REVISION,
        "source_split": MATH500_SPLIT,
        "assignment_policy": MATH500_ASSIGNMENT_POLICY,
        "answer_parser_name": MATH500_ANSWER_PARSER_NAME,
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            raise ValueError(
                f"MATH-500 split mismatch for {field}: expected {value!r}, "
                f"found {payload.get(field)!r}"
            )
    partitions = payload.get("partitions")
    sizes = payload.get("partition_sizes")
    hashes = payload.get("partition_problem_ids_sha256")
    if not isinstance(partitions, Mapping) or set(partitions) != set(
        MATH500_PARTITIONS
    ):
        raise ValueError("MATH-500 split must contain train/validation/test")
    if not isinstance(sizes, Mapping) or not isinstance(hashes, Mapping):
        raise ValueError("MATH-500 split is missing partition metadata")

    required_fields = {
        "problem_id",
        "source_index",
        "subject",
        "level",
        "unique_id",
        "question_sha256",
        "ground_truth_sha256",
        "raw_answer_sha256",
    }
    all_ids: list[str] = []
    all_indices: list[int] = []
    for partition in MATH500_PARTITIONS:
        rows = partitions[partition]
        if not isinstance(rows, list) or sizes.get(partition) != len(rows):
            raise ValueError(f"MATH-500 partition size mismatch for {partition}")
        for position, row in enumerate(rows):
            if not isinstance(row, Mapping) or set(row) != required_fields:
                raise ValueError(f"invalid {partition} row at position {position}")
            if not isinstance(row["problem_id"], str) or not isinstance(
                row["source_index"], int
            ):
                raise ValueError(f"invalid identity in {partition} row {position}")
            if not isinstance(row["level"], int) or not 1 <= row["level"] <= 5:
                raise ValueError(f"invalid level in {partition} row {position}")
            for hash_field in (
                "question_sha256",
                "ground_truth_sha256",
                "raw_answer_sha256",
            ):
                if not isinstance(row[hash_field], str) or len(row[hash_field]) != 64:
                    raise ValueError(f"invalid {hash_field} in {partition} row {position}")
            all_ids.append(str(row["problem_id"]))
            all_indices.append(int(row["source_index"]))
        if hashes.get(partition) != _problem_ids_sha256(rows):
            raise ValueError(f"MATH-500 problem-ID hash mismatch for {partition}")
    if len(set(all_ids)) != len(all_ids) or len(set(all_indices)) != len(all_indices):
        raise ValueError("MATH-500 partitions overlap")

    pilot = payload.get("source_pilot_manifest")
    if not isinstance(pilot, Mapping) or not isinstance(pilot.get("sha256"), str):
        raise ValueError("MATH-500 split is missing pilot provenance")
    pilot_count = int(pilot.get("num_problems", -1))
    train_rows = partitions["train"]
    if pilot_count <= 0 or pilot_count > len(train_rows):
        raise ValueError("invalid MATH-500 pilot prefix size")
    if [row["problem_id"] for row in train_rows[:pilot_count]] != pilot.get(
        "problem_ids"
    ):
        raise ValueError("observed MATH-500 pilot is not preserved as Train prefix")


def read_math500_split_manifest(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    validate_math500_split_manifest(payload)
    return payload


def create_math500_split_manifest(
    *,
    pilot_manifest_path: Path,
    output_path: Path,
    train_count: int = DEFAULT_TRAIN_COUNT,
    validation_count: int = DEFAULT_VALIDATION_COUNT,
    test_count: int = DEFAULT_TEST_COUNT,
    split_seed: int = MATH500_PILOT_SEED,
    dataset_loader: DatasetLoader | None = None,
) -> dict[str, Any]:
    """Freeze a stratified split while retaining every observed pilot in Train."""

    if min(train_count, validation_count, test_count) <= 0:
        raise ValueError("Train, Validation, and Test counts must be positive")
    pilot = _read_json(pilot_manifest_path)
    expected_pilot = {
        "dataset": "math500",
        "dataset_id": MATH500_HF_DATASET_ID,
        "dataset_revision": MATH500_DATASET_REVISION,
        "split": MATH500_SPLIT,
        "seed": split_seed,
        "answer_parser_name": MATH500_ANSWER_PARSER_NAME,
    }
    for field, value in expected_pilot.items():
        if pilot.get(field) != value:
            raise ValueError(
                f"pilot manifest mismatch for {field}: expected {value!r}, "
                f"found {pilot.get(field)!r}"
            )
    pilot_rows = pilot.get("problems")
    if not isinstance(pilot_rows, list) or len(pilot_rows) != pilot.get(
        "num_problems"
    ):
        raise ValueError("pilot manifest problems do not match num_problems")
    if len(pilot_rows) > train_count:
        raise ValueError("Train must contain every previously observed pilot problem")

    selected_count = train_count + validation_count + test_count
    problems = load_math500_subset(
        num_problems=selected_count,
        seed=split_seed,
        revision=MATH500_DATASET_REVISION,
        split=MATH500_SPLIT,
        dataset_loader=dataset_loader,
    )
    for position, (row, problem) in enumerate(
        zip(pilot_rows, problems[: len(pilot_rows)], strict=True)
    ):
        expected_identity = {
            "problem_id": problem.problem_id,
            "source_index": problem.source_index,
            "unique_id": problem.unique_id,
            "subject": problem.subject,
            "level": problem.level,
            "question_sha256": _sha256_text(problem.question),
            "answer_sha256": _sha256_text(problem.ground_truth_raw),
            "ground_truth": problem.ground_truth,
        }
        if any(row.get(field) != value for field, value in expected_identity.items()):
            raise ValueError(f"pilot identity mismatch at prefix position {position}")

    partition_problems = {
        "train": problems[:train_count],
        "validation": problems[train_count : train_count + validation_count],
        "test": problems[train_count + validation_count :],
    }
    partitions = {
        name: [_split_row(problem) for problem in rows]
        for name, rows in partition_problems.items()
    }
    payload: dict[str, Any] = {
        "schema_version": MATH500_SPLIT_SCHEMA_VERSION,
        "manifest_type": MATH500_SPLIT_MANIFEST_TYPE,
        "status": "frozen",
        "dataset": "math500",
        "dataset_id": MATH500_HF_DATASET_ID,
        "dataset_revision": MATH500_DATASET_REVISION,
        "source_split": MATH500_SPLIT,
        "dataset_size": int(pilot["dataset_size"]),
        "split_seed": split_seed,
        "assignment_policy": MATH500_ASSIGNMENT_POLICY,
        "answer_parser_name": MATH500_ANSWER_PARSER_NAME,
        "source_pilot_manifest": {
            "sha256": file_sha256(pilot_manifest_path),
            "num_problems": len(pilot_rows),
            "problem_ids": [row["problem_id"] for row in pilot_rows],
        },
        "partition_sizes": {name: len(rows) for name, rows in partitions.items()},
        "unassigned_reserve_count": int(pilot["dataset_size"]) - selected_count,
        "partition_problem_ids_sha256": {
            name: _problem_ids_sha256(rows) for name, rows in partitions.items()
        },
        "partition_subject_counts": {
            name: _distribution(rows, "subject") for name, rows in partitions.items()
        },
        "partition_level_counts": {
            name: _distribution(rows, "level") for name, rows in partitions.items()
        },
        "partitions": partitions,
    }
    validate_math500_split_manifest(payload)
    serialized = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if output_path.exists():
        existing = read_math500_split_manifest(output_path)
        if existing != payload:
            raise FileExistsError(
                f"frozen MATH-500 split exists with different content: {output_path}"
            )
        return existing
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary.write_text(serialized, encoding="utf-8")
    temporary.replace(output_path)
    return payload


def load_math500_partition(
    *,
    manifest_path: Path,
    partition: str,
    cache_dir: Path | None = None,
    dataset_loader: DatasetLoader | None = None,
) -> list[Math500Problem]:
    """Load and hash-check one frozen MATH-500 research partition."""

    manifest = read_math500_split_manifest(manifest_path)
    if partition not in MATH500_PARTITIONS:
        raise ValueError(f"partition must be one of {MATH500_PARTITIONS}")
    rows = manifest["partitions"][partition]
    problems = load_math500_indices(
        source_indices=[row["source_index"] for row in rows],
        revision=str(manifest["dataset_revision"]),
        split=str(manifest["source_split"]),
        cache_dir=cache_dir,
        dataset_loader=dataset_loader,
    )
    for row, problem in zip(rows, problems, strict=True):
        checks = {
            "problem_id": problem.problem_id,
            "subject": problem.subject,
            "level": problem.level,
            "unique_id": problem.unique_id,
            "question_sha256": _sha256_text(problem.question),
            "ground_truth_sha256": _sha256_text(problem.ground_truth),
            "raw_answer_sha256": _sha256_text(problem.ground_truth_raw),
        }
        if any(row[field] != value for field, value in checks.items()):
            raise ValueError(f"MATH-500 record changed: {problem.problem_id}")
    return problems
