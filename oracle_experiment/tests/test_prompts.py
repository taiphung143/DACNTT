from adaptive_compute.prompts import (
    GSM8K_PROMPT_TEMPLATE_V2_NAME,
    GSM8K_PROMPT_TEMPLATE_V3_NAME,
    build_gsm8k_prompt,
    build_math500_prompt,
    build_prompt,
)


def test_prompt_is_fixed_and_contains_question() -> None:
    prompt = build_gsm8k_prompt("What is 40 + 2?")

    assert "What is 40 + 2?" in prompt
    assert "#### <numeric answer>" in prompt


def test_math500_prompt_requires_boxed_final_answer() -> None:
    prompt = build_math500_prompt("Compute a symbolic expression.")

    assert "Compute a symbolic expression." in prompt
    assert r"\boxed{<final answer>}" in prompt


def test_gsm8k_v2_prompt_has_no_literal_answer_placeholder() -> None:
    prompt = build_prompt(GSM8K_PROMPT_TEMPLATE_V2_NAME, "What is 40 + 2?")

    assert "What is 40 + 2?" in prompt
    assert "<numeric answer>" not in prompt
    assert "Do not print angle brackets" in prompt


def test_gsm8k_v3_prompt_uses_natural_final_answer_marker() -> None:
    prompt = build_prompt(GSM8K_PROMPT_TEMPLATE_V3_NAME, "What is 40 + 2?")

    assert "What is 40 + 2?" in prompt
    assert "Final answer:" in prompt
    assert "#" in prompt  # The prohibition is explicit rather than implicit.
    assert "Do not use # symbols" in prompt
    assert "<numeric answer>" not in prompt
