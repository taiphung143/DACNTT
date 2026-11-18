import pytest

from adaptive_compute.models.transformers_adapter import infer_finish_reason


def test_finish_reason_is_length_at_budget() -> None:
    assert (
        infer_finish_reason(
            generated_ids=[1, 2],
            generated_tokens=2,
            max_new_tokens=2,
            eos_token_id=2,
        )
        == "length"
    )


def test_finish_reason_detects_eos() -> None:
    assert (
        infer_finish_reason(
            generated_ids=[1, 2],
            generated_tokens=2,
            max_new_tokens=10,
            eos_token_id=2,
        )
        == "stop"
    )


@pytest.mark.parametrize(
    ("generated_ids", "generated_tokens", "expected"),
    [([], 0, "empty"), ([7], 1, "unknown")],
)
def test_other_finish_reasons(
    generated_ids: list[int], generated_tokens: int, expected: str
) -> None:
    assert (
        infer_finish_reason(
            generated_ids=generated_ids,
            generated_tokens=generated_tokens,
            max_new_tokens=10,
            eos_token_id=2,
        )
        == expected
    )
