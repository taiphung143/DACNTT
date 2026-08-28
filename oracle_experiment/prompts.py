"""Versioned, fixed prompt templates used across the grid."""

GSM8K_PROMPT_TEMPLATE_NAME = "gsm8k_cot_v1"
GSM8K_PROMPT_TEMPLATE = """Solve the following math problem step by step. End your response with a line in the format: #### <numeric answer>

Problem:
{question}
"""


def build_gsm8k_prompt(question: str) -> str:
    """Build the fixed prompt without profile-specific changes."""

    if not question.strip():
        raise ValueError("question must not be empty")
    return GSM8K_PROMPT_TEMPLATE.format(question=question.strip())

