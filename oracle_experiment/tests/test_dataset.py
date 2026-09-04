import json
from pathlib import Path
from typing import Any

import pytest

from dataset import extend_gsm8k_subset_manifest, load_gsm8k_subset, select_problem_indices


def _records() -> list[dict[str, str]]:
    return [
        {
            "question": f"What is {index} + 1?",
            "answer": f"We add one.\n#### {index + 1}",
        }
        for index in range(10)
    ]


def _loader_factory(records: list[dict[str, str]]):
    def load_dataset(*args: Any, **kwargs: Any) -> list[dict[str, str]]:
        assert args == ("openai/gsm8k", "main")
        assert kwargs["split"] == "test"
        return records

    return load_dataset


def test_index_selection_is_deterministic_and_unique() -> None:
    first = select_problem_indices(dataset_size=100, num_problems=30, seed=42)
    second = select_problem_indices(dataset_size=100, num_problems=30, seed=42)

    assert first == second
    assert len(first) == len(set(first)) == 30


def test_loader_creates_and_reuses_manifest(tmp_path: Path) -> None:
    manifest_path = tmp_path / "subset.json"
    loader = _loader_factory(_records())

    first = load_gsm8k_subset(
        num_problems=4,
        seed=42,
        manifest_path=manifest_path,
        dataset_loader=loader,
    )
    second = load_gsm8k_subset(
        num_problems=4,
        seed=42,
        manifest_path=manifest_path,
        dataset_loader=loader,
    )

    assert first == second
    assert manifest_path.exists()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["num_problems"] == 4
    assert len(payload["problems"]) == 4
    assert all(problem.ground_truth.isdigit() for problem in first)


def test_manifest_rejects_conflicting_seed(tmp_path: Path) -> None:
    manifest_path = tmp_path / "subset.json"
    loader = _loader_factory(_records())
    load_gsm8k_subset(
        num_problems=3,
        seed=42,
        manifest_path=manifest_path,
        dataset_loader=loader,
    )

    with pytest.raises(ValueError, match="seed"):
        load_gsm8k_subset(
            num_problems=3,
            seed=7,
            manifest_path=manifest_path,
            dataset_loader=loader,
        )


def test_manifest_detects_changed_dataset_record(tmp_path: Path) -> None:
    manifest_path = tmp_path / "subset.json"
    records = _records()
    loader = _loader_factory(records)
    problems = load_gsm8k_subset(
        num_problems=3,
        seed=42,
        manifest_path=manifest_path,
        dataset_loader=loader,
    )
    records[problems[0].source_index]["question"] = "Changed question"

    with pytest.raises(ValueError, match="dataset record changed"):
        load_gsm8k_subset(
            num_problems=3,
            seed=42,
            manifest_path=manifest_path,
            dataset_loader=loader,
        )


def test_extended_manifest_preserves_base_as_exact_prefix(tmp_path: Path) -> None:
    base_path = tmp_path / "base.json"
    extended_path = tmp_path / "extended.json"
    loader = _loader_factory(_records())
    base = load_gsm8k_subset(
        num_problems=3,
        seed=42,
        manifest_path=base_path,
        dataset_loader=loader,
    )
    extended = extend_gsm8k_subset_manifest(
        base_manifest_path=base_path,
        output_manifest_path=extended_path,
        num_problems=7,
        seed=42,
        dataset_loader=loader,
    )
    assert extended[:3] == base
    assert len({problem.source_index for problem in extended}) == 7
    assert json.loads(base_path.read_text(encoding="utf-8"))["num_problems"] == 3
