import pytest

from adaptive_compute.controller.controller_validation import validation_gate


def test_validation_gate_requires_both_datasets_to_pass_both_metrics() -> None:
    passing = [
        {"dataset": "gsm8k", "accuracy_gap": 0.0, "token_saving": 0.2},
        {"dataset": "math500", "accuracy_gap": -0.02, "token_saving": 0.1},
    ]
    failing = [
        {"dataset": "gsm8k", "accuracy_gap": 0.0, "token_saving": 0.2},
        {"dataset": "math500", "accuracy_gap": -0.05, "token_saving": 0.3},
    ]

    assert validation_gate(passing)["status"] == "GO_CREATE_RESERVE_PROTOCOL"
    assert validation_gate(failing)["status"] == (
        "PIVOT_NO_RESERVE_FOR_THIS_CONTROLLER"
    )


def test_validation_gate_rejects_incomplete_dataset_pair() -> None:
    with pytest.raises(ValueError, match="exactly GSM8K and MATH-500"):
        validation_gate(
            [{"dataset": "gsm8k", "accuracy_gap": 0.0, "token_saving": 0.2}]
        )

