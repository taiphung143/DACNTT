from __future__ import annotations

import pytest

from adaptive_compute.controller.policy_freeze import (
    build_math500_policy_freeze_bundle,
    build_policy_freeze_bundle,
    select_validation_candidate,
)


def _row(
    policy_id: str,
    *,
    accuracy: float,
    tokens: float,
    policy_type: str = "adaptive",
) -> dict[str, str]:
    return {
        "policy_id": policy_id,
        "policy_type": policy_type,
        "accuracy": str(accuracy),
        "avg_actual_generated_tokens": str(tokens),
    }


def test_selection_maximizes_accuracy_then_minimizes_tokens() -> None:
    rows = [
        _row("cheap_but_less_accurate", accuracy=0.70, tokens=500),
        _row("joint", accuracy=0.75, tokens=2149.05),
        _row("breadth", accuracy=0.75, tokens=2095.85),
        _row(
            "fixed_profile_is_not_a_candidate",
            accuracy=0.80,
            tokens=3000,
            policy_type="fixed_profile",
        ),
    ]

    selected, accuracy_ties = select_validation_candidate(rows)

    assert selected["policy_id"] == "breadth"
    assert accuracy_ties == ["breadth", "joint"]


def test_selection_uses_policy_id_as_final_deterministic_tie_break() -> None:
    rows = [
        _row("policy_z", accuracy=0.75, tokens=1000),
        _row("policy_a", accuracy=0.75, tokens=1000),
    ]

    selected, _ = select_validation_candidate(rows)

    assert selected["policy_id"] == "policy_a"


def test_selection_rejects_summary_without_deployable_policy() -> None:
    rows = [
        _row(
            "fixed_k1_L512",
            accuracy=0.5,
            tokens=400,
            policy_type="fixed_profile",
        )
    ]

    with pytest.raises(ValueError, match="no deployable adaptive policies"):
        select_validation_candidate(rows)


def test_selection_can_include_fixed_policy_after_registered_pivot() -> None:
    rows = [
        _row("breadth", accuracy=0.65, tokens=7500),
        _row(
            "fixed_k2_L4096",
            accuracy=0.65,
            tokens=4700,
            policy_type="fixed_profile",
        ),
        _row(
            "fixed_k4_L4096",
            accuracy=0.65,
            tokens=9000,
            policy_type="fixed_profile",
        ),
    ]

    selected, accuracy_ties = select_validation_candidate(
        rows, include_fixed=True
    )

    assert selected["policy_id"] == "fixed_k2_L4096"
    assert accuracy_ties == ["breadth", "fixed_k2_L4096", "fixed_k4_L4096"]


def test_freeze_builder_refuses_to_overwrite_existing_bundle(tmp_path) -> None:
    output_dir = tmp_path / "existing_freeze"
    output_dir.mkdir()

    with pytest.raises(FileExistsError, match="already exists"):
        build_policy_freeze_bundle(
            train_replay_dir=tmp_path / "unused_train",
            validation_replay_dir=tmp_path / "unused_validation",
            split_manifest_path=tmp_path / "unused_split.json",
            output_dir=output_dir,
            repository_root=tmp_path,
        )

    with pytest.raises(FileExistsError, match="already exists"):
        build_math500_policy_freeze_bundle(
            train_replay_dir=tmp_path / "unused_train",
            validation_replay_dir=tmp_path / "unused_validation",
            split_manifest_path=tmp_path / "unused_split.json",
            output_dir=output_dir,
            repository_root=tmp_path,
        )
