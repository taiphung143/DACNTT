"""Load hash-verified problem inputs from an existing immutable raw artifact."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from adaptive_compute.dataset import GSM8KProblem
from adaptive_compute.math500 import Math500Problem
from adaptive_compute.math500_splits import read_math500_split_manifest
from adaptive_compute.phase2_splits import read_phase2_split_manifest


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _read_snapshot_rows(path: Path, expected_dataset: str) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"problem snapshot not found: {path}")
    rows: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid snapshot JSON at line {line_number}") from exc
            if row.get("dataset") != expected_dataset:
                raise ValueError(
                    f"snapshot dataset mismatch at line {line_number}: "
                    f"expected {expected_dataset!r}"
                )
            problem_id = row.get("problem_id")
            if not isinstance(problem_id, str) or not problem_id:
                raise ValueError(f"snapshot line {line_number} has no problem_id")
            previous = rows.setdefault(problem_id, row)
            for field in ("question", "ground_truth", "ground_truth_raw"):
                if previous.get(field) != row.get(field):
                    raise ValueError(
                        f"snapshot field {field} changes across rows for {problem_id}"
                    )
    return rows


def load_phase2_partition_from_snapshot(
    *,
    dataset_name: str,
    split_manifest_path: Path,
    partition: str,
    snapshot_path: Path,
) -> list[GSM8KProblem | Math500Problem]:
    """Reconstruct a frozen partition and verify it against every manifest hash."""

    if dataset_name == "math500":
        manifest = read_math500_split_manifest(split_manifest_path)
    elif dataset_name == "gsm8k":
        manifest = read_phase2_split_manifest(split_manifest_path)
    else:
        raise ValueError(f"unsupported snapshot dataset: {dataset_name}")
    partitions = manifest["partitions"]
    if partition not in partitions:
        raise ValueError(f"partition not found in split manifest: {partition}")

    snapshot = _read_snapshot_rows(snapshot_path, dataset_name)
    problems: list[GSM8KProblem | Math500Problem] = []
    for expected in partitions[partition]:
        problem_id = expected["problem_id"]
        try:
            row = snapshot[problem_id]
        except KeyError as exc:
            raise ValueError(f"snapshot is missing frozen problem {problem_id}") from exc
        question = row.get("question")
        ground_truth = row.get("ground_truth")
        ground_truth_raw = row.get("ground_truth_raw")
        if not all(isinstance(value, str) for value in (question, ground_truth, ground_truth_raw)):
            raise ValueError(f"snapshot has invalid problem text for {problem_id}")
        if _sha256_text(question) != expected["question_sha256"]:
            raise ValueError(f"snapshot question hash mismatch for {problem_id}")
        if _sha256_text(ground_truth) != expected["ground_truth_sha256"]:
            raise ValueError(f"snapshot ground-truth hash mismatch for {problem_id}")

        if dataset_name == "math500":
            if _sha256_text(ground_truth_raw) != expected["raw_answer_sha256"]:
                raise ValueError(f"snapshot raw-answer hash mismatch for {problem_id}")
            metadata = {
                "subject": row.get("dataset_subject"),
                "level": row.get("dataset_level"),
                "unique_id": row.get("dataset_unique_id"),
            }
            if any(metadata[key] != expected[key] for key in metadata):
                raise ValueError(f"snapshot metadata mismatch for {problem_id}")
            problem = Math500Problem(
                problem_id=problem_id,
                question=question,
                ground_truth=ground_truth,
                ground_truth_raw=ground_truth_raw,
                source_index=int(expected["source_index"]),
                subject=str(metadata["subject"]),
                level=int(metadata["level"]),
                unique_id=str(metadata["unique_id"]),
            )
        else:
            problem = GSM8KProblem(
                problem_id=problem_id,
                question=question,
                ground_truth=ground_truth,
                ground_truth_raw=ground_truth_raw,
                source_index=int(expected["source_index"]),
            )
        problems.append(problem)
    return problems
