"""Conservative answer parsing with thinking/final-response separation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


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
_THINK_START_RE = re.compile(r"<think>", re.IGNORECASE)
_THINK_END_RE = re.compile(r"</think>", re.IGNORECASE)


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

