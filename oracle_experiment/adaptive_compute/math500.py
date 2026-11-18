"""Pinned MATH-500 loading and deterministic stratified pilot manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

from adaptive_compute.answer_parser import (
    MATH500_ANSWER_PARSER_NAME,
    parse_math500_ground_truth,
)
from adaptive_compute.dataset import DatasetLike, DatasetLoader


MATH500_MANIFEST_SCHEMA_VERSION = 1
MATH500_HF_DATASET_ID = "HuggingFaceH4/MATH-500"
# Verified repository head when the pilot protocol was implemented. Record
# hashes in the manifest provide a second guard against upstream changes.
MATH500_DATASET_REVISION = "6e4ed1a2a79af7d8630a6b768ec859cb5af4d3be"
MATH500_SPLIT = "test"
MATH500_PILOT_SIZE = 30
MATH500_PILOT_SEED = 42


@dataclass(frozen=True)
class Math500Problem:
    problem_id: str
    question: str
    ground_truth: str
    ground_truth_raw: str
    source_index: int
    subject: str
    level: int
    unique_id: str
    dataset: str = "math500"


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _default_dataset_loader(*args: Any, **kwargs: Any) -> DatasetLike:
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise RuntimeError(
            "The 'datasets' package is required to load MATH-500. "
            "Install dependencies with: python -m pip install -r requirements.txt"
        ) from exc
    return cast(DatasetLike, load_dataset(*args, **kwargs))


def _validated_metadata(
    record: Mapping[str, Any], source_index: int
) -> tuple[str, int]:
    subject = record.get("subject")
    level = record.get("level")
    if not isinstance(subject, str) or not subject.strip():
        raise ValueError(f"MATH-500 record {source_index} has no valid subject")
    if isinstance(level, bool) or not isinstance(level, int) or not 1 <= level <= 5:
        raise ValueError(f"MATH-500 record {source_index} has invalid level")
    return subject.strip(), level


def select_stratified_math500_indices(
    records: DatasetLike,
    *,
    num_problems: int,
    seed: int,
) -> tuple[int, ...]:
    """Round-robin non-empty subject/level strata after stable seeded shuffling."""

    if num_problems <= 0:
        raise ValueError("num_problems must be positive")
    if num_problems > len(records):
        raise ValueError(
            f"requested {num_problems} problems from a dataset of size {len(records)}"
        )

    strata: dict[tuple[str, int], list[int]] = defaultdict(list)
    for index in range(len(records)):
        subject, level = _validated_metadata(records[index], index)
        strata[(subject, level)].append(index)

    rng = random.Random(seed)
    keys = sorted(strata)
    rng.shuffle(keys)
    for key in keys:
        rng.shuffle(strata[key])

    selected: list[int] = []
    position = 0
    while len(selected) < num_problems:
        made_progress = False
        for key in keys:
            if position < len(strata[key]):
                selected.append(strata[key][position])
                made_progress = True
                if len(selected) == num_problems:
                    break
        if not made_progress:
            raise RuntimeError("stratified selection exhausted before reaching target size")
        position += 1
    return tuple(selected)


def _problem_from_record(
    record: Mapping[str, Any], source_index: int, split: str
) -> Math500Problem:
    question = record.get("problem")
    raw_answer = record.get("answer")
    unique_id = record.get("unique_id")
    subject, level = _validated_metadata(record, source_index)
    if not isinstance(question, str) or not question.strip():
        raise ValueError(f"MATH-500 record {source_index} has no valid problem")
    if not isinstance(raw_answer, str) or not raw_answer.strip():
        raise ValueError(f"MATH-500 record {source_index} has no valid answer")
    if not isinstance(unique_id, str) or not unique_id.strip():
        raise ValueError(f"MATH-500 record {source_index} has no valid unique_id")

    return Math500Problem(
        problem_id=f"math500-{split}-{source_index:03d}",
        question=question.strip(),
        ground_truth=parse_math500_ground_truth(raw_answer),
        ground_truth_raw=raw_answer.strip(),
        source_index=source_index,
        subject=subject,
        level=level,
        unique_id=unique_id.strip(),
    )


def _read_manifest(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read MATH-500 manifest {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("MATH-500 manifest must contain a JSON object")
    return payload


def _manifest_indices(
    manifest: Mapping[str, Any],
    *,
    revision: str,
    split: str,
    num_problems: int,
    seed: int,
) -> tuple[int, ...]:
    expected = {
        "schema_version": MATH500_MANIFEST_SCHEMA_VERSION,
        "dataset": "math500",
        "dataset_id": MATH500_HF_DATASET_ID,
        "dataset_revision": revision,
        "split": split,
        "selection_policy": "subject-level-round-robin-v1",
        "answer_parser_name": MATH500_ANSWER_PARSER_NAME,
        "num_problems": num_problems,
        "seed": seed,
    }
    for key, expected_value in expected.items():
        if manifest.get(key) != expected_value:
            raise ValueError(
                f"manifest setting mismatch for {key}: expected "
                f"{expected_value!r}, found {manifest.get(key)!r}"
            )
    rows = manifest.get("problems")
    if not isinstance(rows, list) or len(rows) != num_problems:
        raise ValueError("manifest problems must match num_problems")
    try:
        indices = tuple(int(row["source_index"]) for row in rows)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("manifest contains an invalid source_index") from exc
    if len(set(indices)) != len(indices):
        raise ValueError("manifest source indices must be unique")
    return indices


def _validate_manifest_records(
    manifest: Mapping[str, Any], problems: Sequence[Math500Problem]
) -> None:
    for row, problem in zip(manifest["problems"], problems, strict=True):
        if (
            row.get("problem_id") != problem.problem_id
            or row.get("unique_id") != problem.unique_id
            or row.get("question_sha256") != _sha256(problem.question)
            or row.get("answer_sha256") != _sha256(problem.ground_truth_raw)
            or row.get("ground_truth") != problem.ground_truth
            or row.get("subject") != problem.subject
            or row.get("level") != problem.level
        ):
            raise ValueError(
                f"MATH-500 record changed for source index {problem.source_index}; "
                "refusing to reuse the manifest"
            )


def _write_manifest(
    path: Path,
    *,
    revision: str,
    split: str,
    seed: int,
    dataset_size: int,
    problems: Sequence[Math500Problem],
) -> None:
    subject_counts: dict[str, int] = defaultdict(int)
    level_counts: dict[str, int] = defaultdict(int)
    for problem in problems:
        subject_counts[problem.subject] += 1
        level_counts[str(problem.level)] += 1
    payload = {
        "schema_version": MATH500_MANIFEST_SCHEMA_VERSION,
        "manifest_type": "math500_stratified_development_pilot",
        "status": "frozen",
        "dataset": "math500",
        "dataset_id": MATH500_HF_DATASET_ID,
        "dataset_revision": revision,
        "split": split,
        "selection_policy": "subject-level-round-robin-v1",
        "answer_parser_name": MATH500_ANSWER_PARSER_NAME,
        "num_problems": len(problems),
        "seed": seed,
        "dataset_size": dataset_size,
        "subject_counts": dict(sorted(subject_counts.items())),
        "level_counts": dict(sorted(level_counts.items())),
        "problems": [
            {
                "problem_id": problem.problem_id,
                "source_index": problem.source_index,
                "unique_id": problem.unique_id,
                "subject": problem.subject,
                "level": problem.level,
                "question_sha256": _sha256(problem.question),
                "answer_sha256": _sha256(problem.ground_truth_raw),
                "ground_truth": problem.ground_truth,
            }
            for problem in problems
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)


def load_math500_subset(
    *,
    num_problems: int = MATH500_PILOT_SIZE,
    seed: int = MATH500_PILOT_SEED,
    revision: str = MATH500_DATASET_REVISION,
    split: str = MATH500_SPLIT,
    manifest_path: Path | None = None,
    cache_dir: Path | None = None,
    dataset_loader: DatasetLoader | None = None,
) -> list[Math500Problem]:
    loader = dataset_loader or _default_dataset_loader
    loader_kwargs: dict[str, Any] = {"split": split, "revision": revision}
    if cache_dir is not None:
        loader_kwargs["cache_dir"] = str(cache_dir)
    records = loader(MATH500_HF_DATASET_ID, **loader_kwargs)

    manifest: dict[str, Any] | None = None
    if manifest_path is not None and manifest_path.exists():
        manifest = _read_manifest(manifest_path)
        indices = _manifest_indices(
            manifest,
            revision=revision,
            split=split,
            num_problems=num_problems,
            seed=seed,
        )
    else:
        indices = select_stratified_math500_indices(
            records, num_problems=num_problems, seed=seed
        )
    if any(index < 0 or index >= len(records) for index in indices):
        raise ValueError("manifest contains an index outside MATH-500")
    problems = [_problem_from_record(records[index], index, split) for index in indices]

    if manifest is not None:
        _validate_manifest_records(manifest, problems)
    elif manifest_path is not None:
        _write_manifest(
            manifest_path,
            revision=revision,
            split=split,
            seed=seed,
            dataset_size=len(records),
            problems=problems,
        )
    return problems


def load_math500_indices(
    *,
    source_indices: Sequence[int],
    revision: str = MATH500_DATASET_REVISION,
    split: str = MATH500_SPLIT,
    cache_dir: Path | None = None,
    dataset_loader: DatasetLoader | None = None,
) -> list[Math500Problem]:
    """Load exact MATH-500 source indices for a frozen research partition."""

    normalized = tuple(int(index) for index in source_indices)
    if not normalized:
        raise ValueError("source_indices must not be empty")
    if len(set(normalized)) != len(normalized):
        raise ValueError("source_indices must be unique")
    loader = dataset_loader or _default_dataset_loader
    loader_kwargs: dict[str, Any] = {"split": split, "revision": revision}
    if cache_dir is not None:
        loader_kwargs["cache_dir"] = str(cache_dir)
    records = loader(MATH500_HF_DATASET_ID, **loader_kwargs)
    if any(index < 0 or index >= len(records) for index in normalized):
        raise ValueError("source_indices contains an index outside MATH-500")
    return [_problem_from_record(records[index], index, split) for index in normalized]


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create or validate a deterministic stratified MATH-500 pilot"
    )
    parser.add_argument("--num-problems", type=int, default=MATH500_PILOT_SIZE)
    parser.add_argument("--seed", type=int, default=MATH500_PILOT_SEED)
    parser.add_argument("--revision", default=MATH500_DATASET_REVISION)
    parser.add_argument("--split", default=MATH500_SPLIT)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/splits/math500_pilot_v2.json"),
    )
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--preview", type=int, default=3)
    return parser


def main() -> int:
    args = build_argument_parser().parse_args()
    problems = load_math500_subset(
        num_problems=args.num_problems,
        seed=args.seed,
        revision=args.revision,
        split=args.split,
        manifest_path=args.manifest,
        cache_dir=args.cache_dir,
    )
    print(f"Loaded {len(problems)} MATH-500 problems; manifest: {args.manifest}")
    for problem in problems[: max(0, args.preview)]:
        preview = asdict(problem)
        preview["ground_truth_raw"] = "<omitted from preview>"
        print(json.dumps(preview, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
