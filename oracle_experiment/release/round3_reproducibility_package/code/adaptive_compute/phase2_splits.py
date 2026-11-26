"""Frozen problem-level Train/Validation/Test splits for Phase 2."""

from __future__ import annotations

import hashlib
import json
import random
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from adaptive_compute.config import MANUAL_AUDIT_PATH
from adaptive_compute.dataset import DatasetLoader, GSM8KProblem, load_gsm8k_indices
from adaptive_compute.dataset_audit import load_manual_audit


PHASE2_SPLIT_SCHEMA_VERSION = 1
PHASE2_SPLIT_MANIFEST_TYPE = "phase2_train_validation_test_split"
PHASE2_PARTITIONS = ("train", "validation", "test")
PHASE2_ASSIGNMENT_POLICY = "phase2-problem-split-v1"


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def file_sha256(path: Path) -> str:
    try:
        return _sha256_bytes(path.read_bytes())
    except OSError as exc:
        raise ValueError(f"could not hash required file {path}: {exc}") from exc


def _read_json_object(path: Path, description: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read {description} {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{description} {path} must contain a JSON object")
    return payload


def _subset_rows(manifest: Mapping[str, Any], description: str) -> list[dict[str, Any]]:
    rows = manifest.get("problems")
    expected_count = manifest.get("num_problems")
    if not isinstance(rows, list) or expected_count != len(rows):
        raise ValueError(f"{description} problems must match num_problems")
    normalized: list[dict[str, Any]] = []
    for position, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"{description} problem {position} must be an object")
        required = ("problem_id", "source_index", "question_sha256", "ground_truth")
        if any(key not in row for key in required):
            raise ValueError(f"{description} problem {position} is missing required fields")
        if not isinstance(row["problem_id"], str) or not isinstance(row["source_index"], int):
            raise ValueError(f"{description} problem {position} has invalid identity fields")
        if not isinstance(row["question_sha256"], str) or not isinstance(
            row["ground_truth"], str
        ):
            raise ValueError(f"{description} problem {position} has invalid hash inputs")
        normalized.append(row)
    problem_ids = [row["problem_id"] for row in normalized]
    source_indices = [row["source_index"] for row in normalized]
    if len(set(problem_ids)) != len(problem_ids):
        raise ValueError(f"{description} problem IDs must be unique")
    if len(set(source_indices)) != len(source_indices):
        raise ValueError(f"{description} source indices must be unique")
    return normalized


def _identity_tuple(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        row.get("problem_id"),
        row.get("source_index"),
        row.get("question_sha256"),
        row.get("ground_truth"),
    )


def _split_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "problem_id": row["problem_id"],
        "source_index": row["source_index"],
        "question_sha256": row["question_sha256"],
        # Do not place readable labels in the controller split manifest.
        "ground_truth_sha256": _sha256_text(str(row["ground_truth"])),
    }


def _problem_ids_sha256(rows: Sequence[Mapping[str, Any]]) -> str:
    canonical = "\n".join(str(row["problem_id"]) for row in rows)
    return _sha256_text(canonical)


def validate_phase2_split_manifest(payload: Mapping[str, Any]) -> None:
    """Validate schema, declared sizes, and cross-partition disjointness."""

    expected_header = {
        "schema_version": PHASE2_SPLIT_SCHEMA_VERSION,
        "manifest_type": PHASE2_SPLIT_MANIFEST_TYPE,
        "status": "frozen",
        "assignment_policy": PHASE2_ASSIGNMENT_POLICY,
    }
    for key, expected in expected_header.items():
        if payload.get(key) != expected:
            raise ValueError(
                f"Phase 2 split manifest mismatch for {key}: "
                f"expected {expected!r}, found {payload.get(key)!r}"
            )

    partitions = payload.get("partitions")
    sizes = payload.get("partition_sizes")
    partition_hashes = payload.get("partition_problem_ids_sha256")
    if not isinstance(partitions, Mapping) or set(partitions) != set(PHASE2_PARTITIONS):
        raise ValueError("Phase 2 manifest must contain exactly train/validation/test")
    if not isinstance(sizes, Mapping) or not isinstance(partition_hashes, Mapping):
        raise ValueError("Phase 2 manifest is missing partition metadata")

    all_problem_ids: list[str] = []
    all_source_indices: list[int] = []
    for partition in PHASE2_PARTITIONS:
        rows = partitions[partition]
        if not isinstance(rows, list) or sizes.get(partition) != len(rows):
            raise ValueError(f"partition size mismatch for {partition}")
        for position, row in enumerate(rows):
            if not isinstance(row, Mapping):
                raise ValueError(f"invalid {partition} row at position {position}")
            required = {
                "problem_id",
                "source_index",
                "question_sha256",
                "ground_truth_sha256",
            }
            if set(row) != required:
                raise ValueError(f"invalid fields in {partition} row at position {position}")
            if not isinstance(row["problem_id"], str) or not isinstance(
                row["source_index"], int
            ):
                raise ValueError(f"invalid identity in {partition} row at position {position}")
            for hash_key in ("question_sha256", "ground_truth_sha256"):
                value = row[hash_key]
                if not isinstance(value, str) or len(value) != 64:
                    raise ValueError(
                        f"invalid {hash_key} in {partition} row at position {position}"
                    )
            all_problem_ids.append(row["problem_id"])
            all_source_indices.append(row["source_index"])
        if partition_hashes.get(partition) != _problem_ids_sha256(rows):
            raise ValueError(f"problem ID hash mismatch for {partition}")

    if len(set(all_problem_ids)) != len(all_problem_ids):
        raise ValueError("Phase 2 partitions overlap by problem ID")
    if len(set(all_source_indices)) != len(all_source_indices):
        raise ValueError("Phase 2 partitions overlap by source index")

    source_manifests = payload.get("source_manifests")
    if not isinstance(source_manifests, Mapping):
        raise ValueError("Phase 2 manifest is missing source_manifests")
    for source_name in ("development", "expanded_pool", "manual_audit"):
        source = source_manifests.get(source_name)
        if not isinstance(source, Mapping):
            raise ValueError(f"Phase 2 manifest is missing {source_name} provenance")
        digest = source.get("sha256")
        if not isinstance(digest, str) or len(digest) != 64:
            raise ValueError(f"invalid SHA-256 for {source_name}")


def read_phase2_split_manifest(path: Path) -> dict[str, Any]:
    payload = _read_json_object(path, "Phase 2 split manifest")
    validate_phase2_split_manifest(payload)
    return payload


def create_phase2_split_manifest(
    *,
    development_manifest_path: Path,
    expanded_pool_manifest_path: Path,
    output_path: Path,
    train_count: int,
    validation_count: int,
    test_count: int,
    split_seed: int,
    manual_audit_path: Path = MANUAL_AUDIT_PATH,
) -> dict[str, Any]:
    """Create an immutable split using n=100 only for development.

    The expanded pool must preserve the development manifest as an exact
    prefix.  Held-out test problems are selected exclusively from its suffix.
    Existing manual-audit flags are excluded from train and validation.
    """

    if min(train_count, validation_count, test_count) <= 0:
        raise ValueError("train, validation, and test counts must be positive")
    development = _read_json_object(development_manifest_path, "development manifest")
    expanded = _read_json_object(expanded_pool_manifest_path, "expanded-pool manifest")
    development_rows = _subset_rows(development, "development manifest")
    expanded_rows = _subset_rows(expanded, "expanded-pool manifest")

    for key in ("dataset", "dataset_id", "dataset_config", "split", "dataset_size"):
        if development.get(key) != expanded.get(key):
            raise ValueError(f"source manifests disagree on {key}")
    if len(expanded_rows) < len(development_rows) + test_count:
        raise ValueError("expanded-pool manifest does not contain enough new test problems")
    for position, development_row in enumerate(development_rows):
        if _identity_tuple(development_row) != _identity_tuple(expanded_rows[position]):
            raise ValueError(
                "expanded-pool manifest does not preserve the development prefix "
                f"at position {position}"
            )

    audit_entries = load_manual_audit(manual_audit_path)
    excluded_ids = set(audit_entries)
    eligible_development = [
        row for row in development_rows if row["problem_id"] not in excluded_ids
    ]
    if train_count + validation_count != len(eligible_development):
        raise ValueError(
            "train_count + validation_count must use every non-flagged "
            f"development problem ({len(eligible_development)})"
        )

    rng = random.Random(f"{PHASE2_ASSIGNMENT_POLICY}|{split_seed}|development")
    rng.shuffle(eligible_development)
    train_rows = eligible_development[:train_count]
    validation_rows = eligible_development[train_count:]
    test_candidates = expanded_rows[len(development_rows) :]
    test_rng = random.Random(f"{PHASE2_ASSIGNMENT_POLICY}|{split_seed}|held-out-test")
    test_rng.shuffle(test_candidates)
    test_rows = test_candidates[:test_count]

    partitions = {
        "train": [_split_row(row) for row in train_rows],
        "validation": [_split_row(row) for row in validation_rows],
        "test": [_split_row(row) for row in test_rows],
    }
    excluded_rows = [
        {
            "problem_id": row["problem_id"],
            "source_index": row["source_index"],
            "audit_status": audit_entries[row["problem_id"]].status,
        }
        for row in development_rows
        if row["problem_id"] in audit_entries
    ]
    payload: dict[str, Any] = {
        "schema_version": PHASE2_SPLIT_SCHEMA_VERSION,
        "manifest_type": PHASE2_SPLIT_MANIFEST_TYPE,
        "status": "frozen",
        "dataset": development.get("dataset"),
        "dataset_id": development.get("dataset_id"),
        "dataset_config": development.get("dataset_config"),
        "source_split": development.get("split"),
        "dataset_size": development.get("dataset_size"),
        "split_seed": split_seed,
        "assignment_policy": PHASE2_ASSIGNMENT_POLICY,
        "source_manifests": {
            "development": {
                "sha256": file_sha256(development_manifest_path),
                "num_problems": len(development_rows),
            },
            "expanded_pool": {
                "sha256": file_sha256(expanded_pool_manifest_path),
                "num_problems": len(expanded_rows),
            },
            "manual_audit": {
                "sha256": file_sha256(manual_audit_path),
                "num_entries": len(audit_entries),
            },
        },
        "excluded_from_development": excluded_rows,
        "partition_sizes": {name: len(rows) for name, rows in partitions.items()},
        "partition_problem_ids_sha256": {
            name: _problem_ids_sha256(rows) for name, rows in partitions.items()
        },
        "partitions": partitions,
    }
    validate_phase2_split_manifest(payload)

    serialized = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if output_path.exists():
        existing = read_phase2_split_manifest(output_path)
        if existing != payload:
            raise FileExistsError(
                f"frozen Phase 2 split already exists with different content: {output_path}"
            )
        return existing
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary_path.write_text(serialized, encoding="utf-8")
    temporary_path.replace(output_path)
    return payload


def load_phase2_partition(
    *,
    manifest_path: Path,
    partition: str,
    manual_audit_path: Path = MANUAL_AUDIT_PATH,
    cache_dir: Path | None = None,
    dataset_loader: DatasetLoader | None = None,
) -> list[GSM8KProblem]:
    """Load one frozen partition and verify current dataset records by hash."""

    manifest = read_phase2_split_manifest(manifest_path)
    if partition not in PHASE2_PARTITIONS:
        raise ValueError(f"partition must be one of {PHASE2_PARTITIONS}")
    expected_audit_hash = manifest["source_manifests"]["manual_audit"]["sha256"]
    if file_sha256(manual_audit_path) != expected_audit_hash:
        raise ValueError(
            "manual audit changed after the Phase 2 split was frozen; "
            "create a reviewed manifest revision"
        )

    rows = manifest["partitions"][partition]
    problems = load_gsm8k_indices(
        source_indices=[row["source_index"] for row in rows],
        dataset_config=str(manifest["dataset_config"]),
        split=str(manifest["source_split"]),
        cache_dir=cache_dir,
        dataset_loader=dataset_loader,
    )
    for row, problem in zip(rows, problems, strict=True):
        if row["problem_id"] != problem.problem_id:
            raise ValueError(f"problem ID changed for source index {problem.source_index}")
        if row["question_sha256"] != _sha256_text(problem.question):
            raise ValueError(f"question changed for source index {problem.source_index}")
        if row["ground_truth_sha256"] != _sha256_text(problem.ground_truth):
            raise ValueError(f"ground truth changed for source index {problem.source_index}")
    return problems
