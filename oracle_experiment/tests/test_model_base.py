import pytest

from adaptive_compute.models.base import GenerationResult


def test_generation_result_computes_total_tokens() -> None:
    result = GenerationResult(
        text="#### 42",
        prompt_tokens=10,
        generated_tokens=4,
        latency_ms=12.5,
        finish_reason="stop",
    )

    assert result.total_tokens == 14


def test_generation_result_rejects_negative_counts() -> None:
    with pytest.raises(ValueError, match="generated_tokens"):
        GenerationResult(
            text="",
            prompt_tokens=0,
            generated_tokens=-1,
            latency_ms=0.0,
            finish_reason=None,
        )
    with pytest.raises(ValueError, match="injected_control_tokens"):
        GenerationResult(
            text="",
            prompt_tokens=0,
            generated_tokens=0,
            latency_ms=0.0,
            finish_reason=None,
            injected_control_tokens=-1,
        )
