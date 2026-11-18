"""Versioned, fixed prompt templates used across the grid."""

GSM8K_PROMPT_TEMPLATE_NAME = "gsm8k_cot_v1"
GSM8K_PROMPT_TEMPLATE = """Solve the following math problem step by step. End your response with a line in the format: #### <numeric answer>

Problem:
{question}
"""

GSM8K_PROMPT_TEMPLATE_V2_NAME = "gsm8k_cot_v2"
GSM8K_PROMPT_TEMPLATE_V2 = """Solve the following math problem step by step. After the reasoning, write the final numeric answer on its own line. The final line must start with four # characters and one space, followed immediately by the numeric result. Do not print angle brackets or placeholder words after ####.

Problem:
{question}
"""

GSM8K_PROMPT_TEMPLATE_V3_NAME = "gsm8k_cot_v3"
GSM8K_PROMPT_TEMPLATE_V3 = """Solve the following math problem step by step. After the reasoning, end with one separate final line. That line must begin with the literal words Final answer: followed by your numeric result. Do not use # symbols, angle brackets, placeholder words, or intermediate values on the final line.

Problem:
{question}
"""

MATH500_PROMPT_TEMPLATE_NAME = "math500_cot_v1"
MATH500_PROMPT_TEMPLATE = r"""Solve the following competition mathematics problem step by step. End your response with exactly one line in the format: \boxed{{<final answer>}}

Problem:
{question}
"""


def build_gsm8k_prompt(question: str) -> str:
    """Build the fixed prompt without profile-specific changes."""

    if not question.strip():
        raise ValueError("question must not be empty")
    return GSM8K_PROMPT_TEMPLATE.format(question=question.strip())


def build_math500_prompt(question: str) -> str:
    """Build the fixed MATH-500 prompt without profile-specific changes."""

    if not question.strip():
        raise ValueError("question must not be empty")
    return MATH500_PROMPT_TEMPLATE.format(question=question.strip())


def get_prompt_template(template_name: str) -> str:
    templates = {
        GSM8K_PROMPT_TEMPLATE_NAME: GSM8K_PROMPT_TEMPLATE,
        GSM8K_PROMPT_TEMPLATE_V2_NAME: GSM8K_PROMPT_TEMPLATE_V2,
        GSM8K_PROMPT_TEMPLATE_V3_NAME: GSM8K_PROMPT_TEMPLATE_V3,
        MATH500_PROMPT_TEMPLATE_NAME: MATH500_PROMPT_TEMPLATE,
    }
    try:
        return templates[template_name]
    except KeyError as exc:
        raise ValueError(f"unsupported prompt template: {template_name}") from exc


def build_prompt(template_name: str, question: str) -> str:
    if template_name == GSM8K_PROMPT_TEMPLATE_NAME:
        return build_gsm8k_prompt(question)
    if template_name == GSM8K_PROMPT_TEMPLATE_V2_NAME:
        if not question.strip():
            raise ValueError("question must not be empty")
        return GSM8K_PROMPT_TEMPLATE_V2.format(question=question.strip())
    if template_name == GSM8K_PROMPT_TEMPLATE_V3_NAME:
        if not question.strip():
            raise ValueError("question must not be empty")
        return GSM8K_PROMPT_TEMPLATE_V3.format(question=question.strip())
    if template_name == MATH500_PROMPT_TEMPLATE_NAME:
        return build_math500_prompt(question)
    raise ValueError(f"unsupported prompt template: {template_name}")
