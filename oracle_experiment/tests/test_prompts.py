from prompts import build_gsm8k_prompt


def test_prompt_is_fixed_and_contains_question() -> None:
    prompt = build_gsm8k_prompt("What is 40 + 2?")

    assert "What is 40 + 2?" in prompt
    assert "#### <numeric answer>" in prompt

