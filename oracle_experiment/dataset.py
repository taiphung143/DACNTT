"""GSM8K loading, deterministic subset selection, and manifest handling."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol, cast

from answer_parser import parse_gsm8k_ground_truth
from config import GLOBAL_SEED, NUM_PROBLEMS


MANIFEST_SCHEMA_VERSION = 1
HF_DATASET_ID = "openai/gsm8k"


class DatasetLike(Protocol):
    """Small part of the Hugging Face Dataset API used by this module."""

    def __len__(self) -> int: ...

    def __getitem__(self, index: int) -> Mapping[str, Any]: ...


DatasetLoader = Callable[..., DatasetLike]


@dataclass(frozen=True)
class GSM8KProblem:
    problem_id: str
    question: str
    ground_truth: str
    ground_truth_raw: str
    source_index: int
    dataset: str = "gsm8k"


def _question_sha256(question: str) -> str:
    return hashlib.sha256(question.encode("utf-8")).hexdigest()


def select_problem_indices(
    dataset_size: int,
    num_problems: int,
    seed: int,
) -> tuple[int, ...]:
    """Select unique source indices using Python's stable seeded PRNG."""

    if dataset_size <= 0:
        raise ValueError("dataset_size must be positive")
    if num_problems <= 0:
        raise ValueError("num_problems must be positive")
    if num_problems > dataset_size:
        raise ValueError(
            f"requested {num_problems} problems from a dataset of size {dataset_size}"
        )
    return tuple(random.Random(seed).sample(range(dataset_size), num_problems))


def _default_dataset_loader(*args: Any, **kwargs: Any) -> DatasetLike:
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise RuntimeError(
            "The 'datasets' package is required to load GSM8K. "
            "Install dependencies with: python -m pip install -r requirements.txt"
        ) from exc
    return cast(DatasetLike, load_dataset(*args, **kwargs))


def _problem_from_record(record: Mapping[str, Any], source_index: int, split: str) -> GSM8KProblem:
    question = record.get("question")
    raw_answer = record.get("answer")
    if not isinstance(question, str) or not question.strip():
        raise ValueError(f"GSM8K record {source_index} has no valid question")
    if not isinstance(raw_answer, str):
        raise ValueError(f"GSM8K record {source_index} has no valid answer")

    ground_truth = parse_gsm8k_ground_truth(raw_answer)
    return GSM8KProblem(
        problem_id=f"gsm8k-{split}-{source_index:05d}",
        question=question.strip(),
        ground_truth=ground_truth,
        ground_truth_raw=raw_answer,
        source_index=source_index,
    )


def _read_manifest(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read dataset manifest {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"dataset manifest {path} must contain a JSON object")
    return payload


def _manifest_indices(
    manifest: Mapping[str, Any],
    *,
    dataset_config: str,
    split: str,
    num_problems: int,
    seed: int,
) -> tuple[int, ...]:
    expected = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "dataset": "gsm8k",
        "dataset_id": HF_DATASET_ID,
        "dataset_config": dataset_config,
        "split": split,
        "num_problems": num_problems,
        "seed": seed,
    }
    for key, expected_value in expected.items():
        if manifest.get(key) != expected_value:
            raise ValueError(
                f"manifest setting mismatch for {key}: "
                f"expected {expected_value!r}, found {manifest.get(key)!r}"
            )

    rows = manifest.get("problems")
    if not isinstance(rows, list) or len(rows) != num_problems:
        raise ValueError("manifest problems must be a list matching num_problems")
    try:
        indices = tuple(int(row["source_index"]) for row in rows)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("manifest contains an invalid source_index") from exc
    if len(set(indices)) != len(indices):
        raise ValueError("manifest source indices must be unique")
    return indices


def _validate_manifest_records(
    manifest: Mapping[str, Any], problems: Sequence[GSM8KProblem]
) -> None:
    rows = manifest["problems"]
    for row, problem in zip(rows, problems, strict=True):
        expected_hash = row.get("question_sha256")
        actual_hash = _question_sha256(problem.question)
        if row.get("problem_id") != problem.problem_id or expected_hash != actual_hash:
            raise ValueError(
                f"dataset record changed for source index {problem.source_index}; "
                "refusing to reuse the manifest"
            )
        if row.get("ground_truth") != problem.ground_truth:
            raise ValueError(
                f"ground truth changed for source index {problem.source_index}; "
                "refusing to reuse the manifest"
            )


def _write_manifest(
    path: Path,
    *,
    dataset_config: str,
    split: str,
    num_problems: int,
    seed: int,
    dataset_size: int,
    problems: Sequence[GSM8KProblem],
) -> None:
    payload = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "dataset": "gsm8k",
        "dataset_id": HF_DATASET_ID,
        "dataset_config": dataset_config,
        "split": split,
        "num_problems": num_problems,
        "seed": seed,
        "dataset_size": dataset_size,
        "problems": [
            {
                "problem_id": item.problem_id,
                "source_index": item.source_index,
                "question_sha256": _question_sha256(item.question),
                "ground_truth": item.ground_truth,
            }
            for item in problems
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)


def load_gsm8k_subset(
    *,
    num_problems: int = NUM_PROBLEMS,
    seed: int = GLOBAL_SEED,
    dataset_config: str = "main",
    split: str = "test",
    manifest_path: Path | None = None,
    cache_dir: Path | None = None,
    dataset_loader: DatasetLoader | None = None,
) -> list[GSM8KProblem]:
    """Load a reproducible GSM8K subset and optionally persist its manifest.

    If the manifest already exists, its exact source indices are reused and
    record hashes are verified. A conflicting seed/subset setting raises rather
    than silently changing the experimental sample.
    """

    loader = dataset_loader or _default_dataset_loader
    loader_kwargs: dict[str, Any] = {"split": split}
    if cache_dir is not None:
        loader_kwargs["cache_dir"] = str(cache_dir)
    records = loader(HF_DATASET_ID, dataset_config, **loader_kwargs)
    dataset_size = len(records)

    manifest: dict[str, Any] | None = None
    if manifest_path is not None and manifest_path.exists():
        manifest = _read_manifest(manifest_path)
        indices = _manifest_indices(
            manifest,
            dataset_config=dataset_config,
            split=split,
            num_problems=num_problems,
            seed=seed,
        )
    else:
        indices = select_problem_indices(dataset_size, num_problems, seed)

    if any(index < 0 or index >= dataset_size for index in indices):
        raise ValueError("manifest contains an index outside the loaded dataset")
    problems = [_problem_from_record(records[index], index, split) for index in indices]

    if manifest is not None:
        _validate_manifest_records(manifest, problems)
    elif manifest_path is not None:
        _write_manifest(
            manifest_path,
            dataset_config=dataset_config,
            split=split,
            num_problems=num_problems,
            seed=seed,
            dataset_size=dataset_size,
            problems=problems,
        )
    return problems


def extend_gsm8k_subset_manifest(
    *,
    base_manifest_path: Path,
    output_manifest_path: Path,
    num_problems: int,
    seed: int = GLOBAL_SEED,
    dataset_config: str = "main",
    split: str = "test",
    cache_dir: Path | None = None,
    dataset_loader: DatasetLoader | None = None,
) -> list[GSM8KProblem]:
    """Create a larger manifest while preserving every base problem as a prefix."""

    if output_manifest_path.exists():
        return load_gsm8k_subset(
            num_problems=num_problems,
            seed=seed,
            dataset_config=dataset_config,
            split=split,
            manifest_path=output_manifest_path,
            cache_dir=cache_dir,
            dataset_loader=dataset_loader,
        )
    base = _read_manifest(base_manifest_path)
    base_count = int(base.get("num_problems", 0))
    if num_problems <= base_count:
        raise ValueError("extended manifest must request more problems than its base")
    _manifest_indices(
        base,
        dataset_config=dataset_config,
        split=split,
        num_problems=base_count,
        seed=seed,
    )

    loader = dataset_loader or _default_dataset_loader
    loader_kwargs: dict[str, Any] = {"split": split}
    if cache_dir is not None:
        loader_kwargs["cache_dir"] = str(cache_dir)
    records = loader(HF_DATASET_ID, dataset_config, **loader_kwargs)
    if num_problems > len(records):
        raise ValueError(f"requested {num_problems} problems from a dataset of size {len(records)}")
    base_indices = tuple(int(row["source_index"]) for row in base["problems"])
    base_problems = [_problem_from_record(records[index], index, split) for index in base_indices]
    _validate_manifest_records(base, base_problems)
    remaining = [index for index in range(len(records)) if index not in set(base_indices)]
    extension_seed = f"gsm8k-manifest-extension-v1|{seed}|{base_count}"
    extra_indices = random.Random(extension_seed).sample(remaining, num_problems - base_count)
    problems = base_problems + [
        _problem_from_record(records[index], index, split) for index in extra_indices
    ]
    _write_manifest(
        output_manifest_path,
        dataset_config=dataset_config,
        split=split,
        num_problems=num_problems,
        seed=seed,
        dataset_size=len(records),
        problems=problems,
    )
    return problems


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Load and preview a deterministic GSM8K subset")
    parser.add_argument("--num-problems", type=int, default=NUM_PROBLEMS)
    parser.add_argument("--seed", type=int, default=GLOBAL_SEED)
    parser.add_argument("--dataset-config", default="main")
    parser.add_argument("--split", default="test")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("results/raw/gsm8k_subset_manifest.json"),
    )
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--preview", type=int, default=3)
    return parser


def main() -> int:
    args = build_argument_parser().parse_args()
    problems = load_gsm8k_subset(
        num_problems=args.num_problems,
        seed=args.seed,
        dataset_config=args.dataset_config,
        split=args.split,
        manifest_path=args.manifest,
        cache_dir=args.cache_dir,
    )
    print(f"Loaded {len(problems)} GSM8K problems; manifest: {args.manifest}")
    for problem in problems[: max(0, args.preview)]:
        preview = asdict(problem)
        preview["ground_truth_raw"] = "<omitted from preview>"
        print(json.dumps(preview, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
