"""Conservative answer parsing with thinking/final-response separation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from fractions import Fraction


_NUMBER_PATTERN = r"[+-]?(?:(?:\d{1,3}(?:,\d{3})+)|\d+)(?:\.\d+)?"
_HASH_MARKER_RE = re.compile(rf"####\s*({_NUMBER_PATTERN})", re.IGNORECASE)
_BOXED_RE = re.compile(r"\\boxed\s*\{\s*(" + _NUMBER_PATTERN + r")\s*\}", re.IGNORECASE)
_ANSWER_PHRASE_RE = re.compile(
    rf"(?:final\s+answer|the\s+answer|answer)\s*(?:is|:|=)\s*({_NUMBER_PATTERN})",
    re.IGNORECASE,
)
_CONCLUSION_RE = re.compile(
    rf"(?:therefore|thus|hence)\s*,?\s*({_NUMBER_PATTERN})\s*[.!]?\s*(?:$|\n)",
    re.IGNORECASE,
)
_STANDALONE_NUMBER_RE = re.compile(rf"^\s*({_NUMBER_PATTERN})\s*[.!]?\s*$")
_PLACEHOLDER_TOKEN_PATTERN = r"<\s*(?:numeric\s+)?answer\s*>"
_PLACEHOLDER_THEN_NUMBER_RE = re.compile(
    rf"####\s*{_PLACEHOLDER_TOKEN_PATTERN}\s*(?:[:=]\s*)?({_NUMBER_PATTERN})",
    re.IGNORECASE,
)
_NUMBER_THEN_PLACEHOLDER_RE = re.compile(
    rf"({_NUMBER_PATTERN})\s*####\s*{_PLACEHOLDER_TOKEN_PATTERN}",
    re.IGNORECASE,
)
_FINAL_ANSWER_LINE_RE = re.compile(
    r"^\s*final\s+answer\s*:\s*(.*?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_NUMBER_RE = re.compile(_NUMBER_PATTERN)
_THINK_START_RE = re.compile(r"<think>", re.IGNORECASE)
_THINK_END_RE = re.compile(r"</think>", re.IGNORECASE)
_MATH_HASH_MARKER_RE = re.compile(r"####\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)
_SIMPLE_FRACTION_RE = re.compile(
    r"^(?:"
    r"\\frac\{([+-]?\d+)\}\{([+-]?\d+)\}|"
    r"\\frac([+-]?\d)\{([+-]?\d+)\}|"
    r"\\frac\{([+-]?\d+)\}([+-]?\d)|"
    r"\\frac([+-]?\d)([+-]?\d)|"
    r"([+-]?\d+)\/([+-]?\d+)"
    r")$"
)
_BASE_ANNOTATED_INTEGER_RE = re.compile(r"^([+-]?\d+)_\{?(\d+)\}?$")
_SIMPLE_NUMERIC_LIST_RE = re.compile(
    r"^[+-]?\d+(?:\.\d+)?(?:\s*,\s*[+-]?\d+(?:\.\d+)?)+$"
)
_GROUPED_DECIMAL_RE = re.compile(r"^[+-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?$")

GSM8K_ANSWER_PARSER_NAME = "gsm8k_numeric_v1"
GSM8K_ANSWER_PARSER_V2_NAME = "gsm8k_numeric_v2"
GSM8K_ANSWER_PARSER_V3_NAME = "gsm8k_numeric_v3"
GSM8K_ANSWER_PARSER_NAMES = (
    GSM8K_ANSWER_PARSER_NAME,
    GSM8K_ANSWER_PARSER_V2_NAME,
    GSM8K_ANSWER_PARSER_V3_NAME,
)
MATH500_ANSWER_PARSER_V1_NAME = "math500_exact_v1"
MATH500_ANSWER_PARSER_NAME = "math500_exact_v2"


@dataclass(frozen=True)
class AnswerParseResult:
    parsed_answer: str | None
    explicit_final_answer_found: bool


@dataclass(frozen=True)
class ThinkingState:
    thinking_started: bool
    thinking_completed: bool


@dataclass(frozen=True)
class ResponseSections:
    reasoning_text: str | None
    final_response_text: str
    thinking_started: bool
    thinking_completed: bool


@dataclass(frozen=True)
class ResponseAnswerResult:
    reasoning_answer: str | None
    final_response_answer: str | None
    answer_source: str
    reasoning_final_disagreement: bool
    thinking_started: bool
    thinking_completed: bool


def normalize_numeric_answer(value: str) -> str | None:
    cleaned = value.strip().replace(",", "").replace("−", "-").replace("–", "-")
    if not cleaned:
        return None
    try:
        number = Decimal(cleaned)
    except InvalidOperation:
        return None
    if not number.is_finite():
        return None
    if number == 0:
        return "0"
    normalized = format(number.normalize(), "f")
    return normalized.rstrip("0").rstrip(".") if "." in normalized else normalized


def _last_normalized_match(text: str, pattern: re.Pattern[str]) -> str | None:
    matches = list(pattern.finditer(text))
    if not matches:
        return None
    return normalize_numeric_answer(matches[-1].group(1))


def _parse_explicit_answer(text: str) -> str | None:
    """Parse one already-selected response section without last-number fallback."""

    if not text or not text.strip():
        return None
    normalized_text = text.replace("−", "-").replace("–", "-")
    for pattern in (
        _HASH_MARKER_RE,
        _BOXED_RE,
        _ANSWER_PHRASE_RE,
        _CONCLUSION_RE,
        _STANDALONE_NUMBER_RE,
    ):
        parsed = _last_normalized_match(normalized_text, pattern)
        if parsed is not None:
            return parsed
    return None


def _parse_gsm8k_v2_explicit_answer(text: str) -> str | None:
    """Parse strict v1 forms plus two observed placeholder-echo forms.

    The 0.6B pilot sometimes copied the prompt's literal ``<numeric answer>``
    token while placing one numeric candidate immediately before or after it.
    V2 recovers only those local, unambiguous forms. It deliberately does not
    fall back to the last number or promote a reasoning-only answer.
    """

    parsed = _parse_explicit_answer(text)
    if parsed is not None:
        return parsed
    normalized_text = text.replace("âˆ’", "-").replace("â€“", "-")
    for pattern in (_PLACEHOLDER_THEN_NUMBER_RE, _NUMBER_THEN_PLACEHOLDER_RE):
        parsed = _last_normalized_match(normalized_text, pattern)
        if parsed is not None:
            return parsed
    return None


def _parse_gsm8k_v3_explicit_answer(text: str) -> str | None:
    """Parse v2 forms or one unambiguous number on a Final answer line.

    Prose is allowed after the explicit marker because Qwen3-0.6B often emits
    units or a short answer sentence. Recovery is refused unless the selected
    final-answer line contains exactly one numeric candidate.
    """

    parsed = _parse_gsm8k_v2_explicit_answer(text)
    if parsed is not None:
        return parsed
    matches = list(_FINAL_ANSWER_LINE_RE.finditer(text or ""))
    if not matches:
        return None
    candidates = list(_NUMBER_RE.finditer(matches[-1].group(1)))
    if len(candidates) != 1:
        return None
    return normalize_numeric_answer(candidates[0].group(0))


def split_response_sections(text: str) -> ResponseSections:
    """Split the first Qwen ``<think>...</think>`` block from user-facing text."""

    raw = text or ""
    start = _THINK_START_RE.search(raw)
    if start is None:
        return ResponseSections(None, raw, False, False)
    end = _THINK_END_RE.search(raw, start.end())
    if end is None:
        return ResponseSections(raw[start.end() :], "", True, False)
    return ResponseSections(
        reasoning_text=raw[start.end() : end.start()],
        final_response_text=raw[end.end() :],
        thinking_started=True,
        thinking_completed=True,
    )


def parse_response_answers(text: str) -> ResponseAnswerResult:
    """Extract diagnostic reasoning and strict user-facing final answers."""

    sections = split_response_sections(text)
    # A reasoning answer requires a closed thinking block. An answer inside an
    # unfinished block is not considered a completed reasoning result.
    reasoning_answer = (
        _parse_explicit_answer(sections.reasoning_text or "")
        if sections.thinking_completed
        else None
    )
    final_response_answer = _parse_explicit_answer(sections.final_response_text)
    if reasoning_answer is not None and final_response_answer is not None:
        answer_source = "both"
    elif reasoning_answer is not None:
        answer_source = "thinking"
    elif final_response_answer is not None:
        answer_source = "final_response"
    else:
        answer_source = "none"
    disagreement = (
        reasoning_answer is not None
        and final_response_answer is not None
        and normalize_numeric_answer(reasoning_answer)
        != normalize_numeric_answer(final_response_answer)
    )
    return ResponseAnswerResult(
        reasoning_answer=reasoning_answer,
        final_response_answer=final_response_answer,
        answer_source=answer_source,
        reasoning_final_disagreement=disagreement,
        thinking_started=sections.thinking_started,
        thinking_completed=sections.thinking_completed,
    )


def parse_gsm8k_v2_response_answers(text: str) -> ResponseAnswerResult:
    """Extract GSM8K answers with conservative placeholder-echo recovery."""

    sections = split_response_sections(text)
    reasoning_answer = (
        _parse_gsm8k_v2_explicit_answer(sections.reasoning_text or "")
        if sections.thinking_completed
        else None
    )
    final_response_answer = _parse_gsm8k_v2_explicit_answer(
        sections.final_response_text
    )
    if reasoning_answer is not None and final_response_answer is not None:
        answer_source = "both"
    elif reasoning_answer is not None:
        answer_source = "thinking"
    elif final_response_answer is not None:
        answer_source = "final_response"
    else:
        answer_source = "none"
    return ResponseAnswerResult(
        reasoning_answer=reasoning_answer,
        final_response_answer=final_response_answer,
        answer_source=answer_source,
        reasoning_final_disagreement=(
            reasoning_answer is not None
            and final_response_answer is not None
            and normalize_numeric_answer(reasoning_answer)
            != normalize_numeric_answer(final_response_answer)
        ),
        thinking_started=sections.thinking_started,
        thinking_completed=sections.thinking_completed,
    )


def parse_gsm8k_v3_response_answers(text: str) -> ResponseAnswerResult:
    """Extract GSM8K answers under the explicit-marker/unique-number rule."""

    sections = split_response_sections(text)
    reasoning_answer = (
        _parse_gsm8k_v3_explicit_answer(sections.reasoning_text or "")
        if sections.thinking_completed
        else None
    )
    final_response_answer = _parse_gsm8k_v3_explicit_answer(
        sections.final_response_text
    )
    if reasoning_answer is not None and final_response_answer is not None:
        answer_source = "both"
    elif reasoning_answer is not None:
        answer_source = "thinking"
    elif final_response_answer is not None:
        answer_source = "final_response"
    else:
        answer_source = "none"
    return ResponseAnswerResult(
        reasoning_answer=reasoning_answer,
        final_response_answer=final_response_answer,
        answer_source=answer_source,
        reasoning_final_disagreement=(
            reasoning_answer is not None
            and final_response_answer is not None
            and normalize_numeric_answer(reasoning_answer)
            != normalize_numeric_answer(final_response_answer)
        ),
        thinking_started=sections.thinking_started,
        thinking_completed=sections.thinking_completed,
    )


def parse_final_answer_details(text: str) -> AnswerParseResult:
    """Return only the strict user-facing final answer for compatibility."""

    result = parse_response_answers(text)
    return AnswerParseResult(
        result.final_response_answer,
        result.final_response_answer is not None,
    )


def parse_final_answer(text: str) -> str | None:
    return parse_final_answer_details(text).parsed_answer


def detect_thinking_state(text: str) -> ThinkingState:
    sections = split_response_sections(text)
    return ThinkingState(sections.thinking_started, sections.thinking_completed)


def parse_gsm8k_ground_truth(answer: str) -> str:
    parsed = _last_normalized_match(answer, _HASH_MARKER_RE)
    if parsed is None:
        raise ValueError("GSM8K ground truth does not contain a valid #### answer")
    return parsed


def _strip_balanced_outer_braces(value: str) -> str:
    current = value
    while current.startswith("{") and current.endswith("}"):
        depth = 0
        balanced = True
        for index, char in enumerate(current):
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0 and index != len(current) - 1:
                    balanced = False
                    break
                if depth < 0:
                    balanced = False
                    break
        if not balanced or depth != 0:
            break
        current = current[1:-1]
    return current


def _unwrap_text_answer(value: str) -> str:
    match = re.fullmatch(r"\\(?:text|mathrm)\{([^{}]*)\}", value)
    return match.group(1) if match else value


def _normalize_numeric_list(value: str) -> str | None:
    """Canonicalize a comma-separated numeric list without confusing 1,234."""

    if not _SIMPLE_NUMERIC_LIST_RE.fullmatch(value):
        return None
    has_comma_whitespace = bool(re.search(r"\s,|,\s", value))
    compact = re.sub(r"\s+", "", value)
    if not has_comma_whitespace and _GROUPED_DECIMAL_RE.fullmatch(compact):
        return None
    normalized_items = [normalize_numeric_answer(item) for item in compact.split(",")]
    if any(item is None for item in normalized_items):
        return None
    return ",".join(item for item in normalized_items if item is not None)


def normalize_math_answer(value: str) -> str | None:
    """Conservatively canonicalize an extracted MATH-500 final answer.

    The pilot deliberately avoids unrestricted symbolic equivalence. Common
    presentation-only differences and exact simple rational equivalence are
    normalized; remaining edge cases are surfaced for manual audit.
    """

    cleaned = value.strip()
    if not cleaned:
        return None
    cleaned = cleaned.replace("−", "-").replace("–", "-")
    cleaned = re.sub(r"^\$+|\$+[.!?,;:]*$", "", cleaned.strip())
    cleaned = re.sub(r"^\\\(|\\\)$", "", cleaned.strip())
    cleaned = re.sub(r"^\\\[|\\\]$", "", cleaned.strip())
    cleaned = cleaned.strip().rstrip(".!?,;:")
    cleaned = cleaned.replace("\\left", "").replace("\\right", "")
    cleaned = cleaned.replace("\\dfrac", "\\frac").replace("\\tfrac", "\\frac")
    cleaned = cleaned.replace("\\displaystyle", "")
    cleaned = re.sub(r"\\(?:,|!|;|:|quad|qquad)", "", cleaned)

    numeric_list = _normalize_numeric_list(cleaned)
    if numeric_list is not None:
        return numeric_list

    cleaned = re.sub(r"\s+", "", cleaned)
    cleaned = _strip_balanced_outer_braces(cleaned)
    cleaned = _unwrap_text_answer(cleaned).strip()
    if not cleaned:
        return None

    # Degrees are a presentation unit for the same scalar answer.
    cleaned = re.sub(r"(?:\^?\{?\\circ\}?|°)$", "", cleaned)

    # In answers such as 204_5, the subscript states the requested numeral
    # base; it is not an additional digit in the answer.
    base_annotated = _BASE_ANNOTATED_INTEGER_RE.fullmatch(cleaned)
    if base_annotated:
        digits, base_text = base_annotated.groups()
        base = int(base_text)
        unsigned_digits = digits.lstrip("+-")
        if 2 <= base <= 10 and all(int(digit) < base for digit in unsigned_digits):
            return normalize_numeric_answer(digits)

    numeric = normalize_numeric_answer(cleaned)
    if numeric is not None:
        return numeric

    fraction_match = _SIMPLE_FRACTION_RE.fullmatch(cleaned)
    if fraction_match:
        groups = fraction_match.groups()
        numerator_text = next(
            groups[index] for index in range(0, len(groups), 2) if groups[index] is not None
        )
        denominator_text = next(
            groups[index] for index in range(1, len(groups), 2) if groups[index] is not None
        )
        numerator = int(numerator_text)
        denominator = int(denominator_text)
        if denominator == 0:
            return None
        fraction = Fraction(numerator, denominator)
        return f"{fraction.numerator}/{fraction.denominator}"

    return cleaned.casefold()


def _balanced_command_arguments(text: str, command: str) -> list[str]:
    results: list[str] = []
    pattern = re.compile(rf"\\{command}\s*\{{", re.IGNORECASE)
    for match in pattern.finditer(text):
        start = match.end()
        depth = 1
        for index in range(start, len(text)):
            if text[index] == "{":
                depth += 1
            elif text[index] == "}":
                depth -= 1
                if depth == 0:
                    results.append(text[start:index])
                    break
    return results


def _parse_math_explicit_answer(text: str) -> str | None:
    if not text or not text.strip():
        return None
    boxed = _balanced_command_arguments(text, "boxed")
    boxed.extend(_balanced_command_arguments(text, "fbox"))
    if boxed:
        return normalize_math_answer(boxed[-1])
    hash_matches = list(_MATH_HASH_MARKER_RE.finditer(text))
    if hash_matches:
        return normalize_math_answer(hash_matches[-1].group(1))
    return None


def parse_math500_response_answers(text: str) -> ResponseAnswerResult:
    sections = split_response_sections(text)
    reasoning_answer = (
        _parse_math_explicit_answer(sections.reasoning_text or "")
        if sections.thinking_completed
        else None
    )
    final_response_answer = _parse_math_explicit_answer(sections.final_response_text)
    if reasoning_answer is not None and final_response_answer is not None:
        answer_source = "both"
    elif reasoning_answer is not None:
        answer_source = "thinking"
    elif final_response_answer is not None:
        answer_source = "final_response"
    else:
        answer_source = "none"
    return ResponseAnswerResult(
        reasoning_answer=reasoning_answer,
        final_response_answer=final_response_answer,
        answer_source=answer_source,
        reasoning_final_disagreement=(
            reasoning_answer is not None
            and final_response_answer is not None
            and reasoning_answer != final_response_answer
        ),
        thinking_started=sections.thinking_started,
        thinking_completed=sections.thinking_completed,
    )


def parse_math500_ground_truth(answer: str) -> str:
    parsed = normalize_math_answer(answer)
    if parsed is None:
        raise ValueError("MATH-500 ground truth is empty or unsupported")
    return parsed
