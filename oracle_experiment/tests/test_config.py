from pathlib import Path

import pytest

from config import MODEL_ID, MODEL_REVISION, ExperimentConfig, GridConfiguration


def test_default_grid_has_expected_nine_profiles() -> None:
    config = ExperimentConfig()

    assert [(item.k, item.max_new_tokens) for item in config.grid] == [
        (1, 512),
        (1, 1024),
        (1, 2048),
        (2, 512),
        (2, 1024),
        (2, 2048),
        (4, 512),
        (4, 1024),
        (4, 2048),
    ]


def test_allocated_budget_is_k_times_l() -> None:
    assert GridConfiguration(k=4, max_new_tokens=1024).allocated_token_budget == 4096


def test_invalid_sampling_configuration_is_rejected() -> None:
    with pytest.raises(ValueError, match="top_p"):
        ExperimentConfig(top_p=0.0)


def test_configuration_snapshot_serializes_path() -> None:
    payload = ExperimentConfig(results_dir=Path("custom-results")).to_dict()

    assert payload["results_dir"] == "custom-results"


def test_model_checkpoint_is_selected_and_revision_pinned() -> None:
    assert MODEL_ID == "Qwen/Qwen3-1.7B"
    assert len(MODEL_REVISION) == 40
