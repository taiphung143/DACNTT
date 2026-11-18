from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from adaptive_compute.cli.run_grid import main as run_grid_main
from adaptive_compute.math500 import (
    MATH500_DATASET_REVISION,
    MATH500_HF_DATASET_ID,
    load_math500_subset,
)
from adaptive_compute.math500_splits import (
    create_math500_split_manifest,
    load_math500_partition,
    read_math500_split_manifest,
)


def _records(count: int = 40) -> list[dict[str, Any]]:
    subjects = ("Algebra", "Geometry", "Number Theory", "Prealgebra")
    return [
        {
            "problem": f"Problem {index}",
            "solution": rf"Work. \boxed{{{index + 1}}}",
            "answer": str(index + 1),
            "subject": subjects[index % len(subjects)],
            "level": index % 5 + 1,
            "unique_id": f"test/synthetic/{index}.json",
        }
        for index in range(count)
    ]


def _loader(records: list[dict[str, Any]]):
    def load_dataset(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        assert args == (MATH500_HF_DATASET_ID,)
        assert kwargs["split"] == "test"
        assert kwargs["revision"] == MATH500_DATASET_REVISION
        return records

    return load_dataset


def _pilot(tmp_path: Path, records: list[dict[str, Any]]) -> Path:
    path = tmp_path / "pilot.json"
    load_math500_subset(
        num_problems=5,
        seed=42,
        revision=MATH500_DATASET_REVISION,
        manifest_path=path,
        dataset_loader=_loader(records),
    )
    return path


def test_math500_split_is_disjoint_idempotent_and_preserves_pilot(
    tmp_path: Path,
) -> None:
    records = _records()
    pilot_path = _pilot(tmp_path, records)
    output_path = tmp_path / "split.json"
    first = create_math500_split_manifest(
        pilot_manifest_path=pilot_path,
        output_path=output_path,
        train_count=10,
        validation_count=5,
        test_count=10,
        dataset_loader=_loader(records),
    )
    second = create_math500_split_manifest(
        pilot_manifest_path=pilot_path,
        output_path=output_path,
        train_count=10,
        validation_count=5,
        test_count=10,
        dataset_loader=_loader(records),
    )

    assert first == second == read_math500_split_manifest(output_path)
    assert first["partition_sizes"] == {"train": 10, "validation": 5, "test": 10}
    assert first["unassigned_reserve_count"] == 15
    pilot_ids = [row["problem_id"] for row in json.loads(pilot_path.read_text())["problems"]]
    assert [row["problem_id"] for row in first["partitions"]["train"][:5]] == pilot_ids
    partition_ids = [
        {row["problem_id"] for row in first["partitions"][name]}
        for name in ("train", "validation", "test")
    ]
    assert not partition_ids[0] & partition_ids[1]
    assert not partition_ids[0] & partition_ids[2]
    assert not partition_ids[1] & partition_ids[2]


def test_math500_partition_loader_detects_dataset_change(tmp_path: Path) -> None:
    records = _records()
    pilot_path = _pilot(tmp_path, records)
    output_path = tmp_path / "split.json"
    manifest = create_math500_split_manifest(
        pilot_manifest_path=pilot_path,
        output_path=output_path,
        train_count=10,
        validation_count=5,
        test_count=10,
        dataset_loader=_loader(records),
    )
    loaded = load_math500_partition(
        manifest_path=output_path,
        partition="validation",
        dataset_loader=_loader(records),
    )
    assert len(loaded) == 5

    changed_index = manifest["partitions"]["validation"][0]["source_index"]
    records[changed_index]["problem"] = "Changed upstream problem"
    with pytest.raises(ValueError, match="record changed"):
        load_math500_partition(
            manifest_path=output_path,
            partition="validation",
            dataset_loader=_loader(records),
        )


def test_math500_split_rejects_train_smaller_than_observed_pilot(
    tmp_path: Path,
) -> None:
    records = _records()
    pilot_path = _pilot(tmp_path, records)

    with pytest.raises(ValueError, match="every previously observed pilot"):
        create_math500_split_manifest(
            pilot_manifest_path=pilot_path,
            output_path=tmp_path / "split.json",
            train_count=4,
            validation_count=5,
            test_count=10,
            dataset_loader=_loader(records),
        )


def test_run_grid_validate_only_accepts_frozen_math_train_partition(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    records = _records()
    pilot_path = _pilot(tmp_path, records)
    split_path = tmp_path / "split.json"
    create_math500_split_manifest(
        pilot_manifest_path=pilot_path,
        output_path=split_path,
        train_count=10,
        validation_count=5,
        test_count=10,
        dataset_loader=_loader(records),
    )

    assert (
        run_grid_main(
            [
                "--dataset-name",
                "math500",
                "--num-problems",
                "10",
                "--phase2-split-manifest",
                str(split_path),
                "--phase2-partition",
                "train",
                "--k-values",
                "1",
                "2",
                "4",
                "--l-values",
                "1024",
                "2048",
                "4096",
                "--validate-only",
            ]
        )
        == 0
    )
    output = json.loads(capsys.readouterr().out)
    assert output["dataset_name"] == "math500"
    assert output["dataset_partition"] == "train"
    assert output["expected_unique_generations"] == 120


def test_run_grid_rejects_math_revision_different_from_frozen_split(
    tmp_path: Path,
) -> None:
    records = _records()
    pilot_path = _pilot(tmp_path, records)
    split_path = tmp_path / "split.json"
    create_math500_split_manifest(
        pilot_manifest_path=pilot_path,
        output_path=split_path,
        train_count=10,
        validation_count=5,
        test_count=10,
        dataset_loader=_loader(records),
    )

    with pytest.raises(ValueError, match="revision must match"):
        run_grid_main(
            [
                "--dataset-name",
                "math500",
                "--dataset-revision",
                "different-revision",
                "--num-problems",
                "10",
                "--phase2-split-manifest",
                str(split_path),
                "--phase2-partition",
                "train",
                "--validate-only",
            ]
        )
