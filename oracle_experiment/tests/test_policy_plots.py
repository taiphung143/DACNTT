from __future__ import annotations

import csv
from pathlib import Path

import pytest

from adaptive_compute.cli.plot_policy_pareto import (
    load_policy_points,
    short_policy_label,
)


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_load_policy_points_requires_matching_ids(tmp_path: Path) -> None:
    summary = tmp_path / "summary.csv"
    pareto = tmp_path / "pareto.csv"
    _write_csv(
        summary,
        [
            {
                "policy_id": "fixed_k1_L1024",
                "policy_type": "fixed_profile",
                "accuracy": 0.5,
                "avg_actual_generated_tokens": 100.0,
            }
        ],
    )
    _write_csv(
        pareto,
        [
            {
                "policy_id": "fixed_k2_L1024",
                "accuracy": 0.5,
                "avg_actual_generated_tokens": 100.0,
                "pareto_nondominated": True,
            }
        ],
    )
    with pytest.raises(ValueError, match="Policy-ID mismatch"):
        load_policy_points(summary, pareto)


def test_load_policy_points_parses_frontier_and_sorts(tmp_path: Path) -> None:
    summary = tmp_path / "summary.csv"
    pareto = tmp_path / "pareto.csv"
    _write_csv(
        summary,
        [
            {
                "policy_id": "fixed_k2_L1024",
                "policy_type": "fixed_profile",
                "accuracy": 0.6,
                "avg_actual_generated_tokens": 200.0,
            },
            {
                "policy_id": "fixed_k1_L1024",
                "policy_type": "fixed_profile",
                "accuracy": 0.5,
                "avg_actual_generated_tokens": 100.0,
            },
        ],
    )
    _write_csv(
        pareto,
        [
            {
                "policy_id": "fixed_k1_L1024",
                "accuracy": 0.5,
                "avg_actual_generated_tokens": 100.0,
                "pareto_nondominated": True,
            },
            {
                "policy_id": "fixed_k2_L1024",
                "accuracy": 0.6,
                "avg_actual_generated_tokens": 200.0,
                "pareto_nondominated": False,
            },
        ],
    )
    points = load_policy_points(summary, pareto)
    assert [point["policy_id"] for point in points] == [
        "fixed_k1_L1024",
        "fixed_k2_L1024",
    ]
    assert points[0]["pareto_nondominated"] is True
    assert points[1]["pareto_nondominated"] is False


def test_short_policy_label() -> None:
    assert short_policy_label("fixed_k2_L4096") == "Fixed k=2, L=4096"
    assert (
        short_policy_label("breadth_only_agreement_L1024_v1")
        == "Breadth stop L=1024"
    )
    assert (
        short_policy_label("depth_first_tertile_validity_agreement_v1")
        == "Joint heuristic"
    )
