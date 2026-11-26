"""Leakage-safe input features and depth-only supervision from Phase 1 data."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from adaptive_compute.phase2_splits import file_sha256, read_phase2_split_manifest


DEPTH_FEATURE_SCHEMA_VERSION = 1
DEPTH_LABEL_POLICY = "lowest-observed-correct-L-else-max-L-v1"
DEFAULT_DEPTHS = (512, 1024, 2048)
DEVELOPMENT_PARTITIONS = ("train", "validation")

_NUMBER_PATTERN = re.compile(r"\d[\d,]*(?:\.\d+)?")
_FRACTION_PATTERN = re.compile(r"\b\d+\s*/\s*\d+\b")
_WORD_PATTERN = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
_SENTENCE_PATTERN = re.compile(r"[.!?]+")

_LEXICAL_INDICATORS: dict[str, re.Pattern[str]] = {
    "how_many": re.compile(r"\bhow\s+many\b", re.IGNORECASE),
    "how_much": re.compile(r"\bhow\s+much\b", re.IGNORECASE),
    "total": re.compile(r"\btotal\b", re.IGNORECASE),
    "each": re.compile(r"\beach\b", re.IGNORECASE),
    "more": re.compile(r"\bmore\b", re.IGNORECASE),
    "less": re.compile(r"\bless\b", re.IGNORECASE),
    "left": re.compile(r"\bleft\b", re.IGNORECASE),
    "difference": re.compile(r"\bdifference\b", re.IGNORECASE),
    "percent": re.compile(r"\bpercent(?:age)?\b|%", re.IGNORECASE),
    "average": re.compile(r"\baverage\b", re.IGNORECASE),
    "ratio": re.compile(r"\bratio\b", re.IGNORECASE),
    "per": re.compile(r"\bper\b", re.IGNORECASE),
    "twice": re.compile(r"\btwice\b", re.IGNORECASE),
    "times": re.compile(r"\btimes\b", re.IGNORECASE),
    "dozen": re.compile(r"\bdozens?\b", re.IGNORECASE),
    "remaining": re.compile(r"\bremain(?:ing|s|ed)?\b", re.IGNORECASE),
}


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _parse_bool(value: Any) -> bool:
    if value is True or str(value).strip().lower() == "true":
        return True
    if value is False or str(value).strip().lower() == "false":
        return False
    raise ValueError(f"expected a Boolean value, found {value!r}")


def extract_question_features(question: str, prompt_token_count: int) -> dict[str, int | float]:
    """Extract inexpensive features available before any generation."""

    if not question.strip():
        raise ValueError("question must not be empty")
    if prompt_token_count <= 0:
        raise ValueError("prompt_token_count must be positive")

    words = _WORD_PATTERN.findall(question)
    numbers = _NUMBER_PATTERN.findall(question)
    normalized_numbers = [value.replace(",", "") for value in numbers]
    number_digit_lengths = [sum(character.isdigit() for character in value) for value in numbers]
    operator_counts = {
        "addition": question.count("+"),
        "subtraction": question.count("-") + question.count("−"),
        "multiplication": question.count("*") + question.count("×"),
        "division": question.count("/") + question.count("÷"),
        "equals": question.count("="),
    }
    features: dict[str, int | float] = {
        "feature_question_char_count": len(question),
        "feature_question_word_count": len(words),
        "feature_prompt_token_count": prompt_token_count,
        "feature_number_count": len(numbers),
        "feature_unique_number_count": len(set(normalized_numbers)),
        "feature_decimal_number_count": sum("." in value for value in normalized_numbers),
        "feature_fraction_count": len(_FRACTION_PATTERN.findall(question)),
        "feature_digit_count": sum(character.isdigit() for character in question),
        "feature_max_number_digits": max(number_digit_lengths, default=0),
        "feature_currency_symbol_count": sum(question.count(symbol) for symbol in ("$", "£", "€")),
        "feature_percent_symbol_count": question.count("%"),
        "feature_operator_count": sum(operator_counts.values()),
        "feature_addition_operator_count": operator_counts["addition"],
        "feature_subtraction_operator_count": operator_counts["subtraction"],
        "feature_multiplication_operator_count": operator_counts["multiplication"],
        "feature_division_operator_count": operator_counts["division"],
        "feature_equals_operator_count": operator_counts["equals"],
        "feature_sentence_count": len(_SENTENCE_PATTERN.findall(question)),
        "feature_comma_count": question.count(","),
        "feature_question_mark_count": question.count("?"),
        "feature_average_word_length": (
            sum(len(word) for word in words) / len(words) if words else 0.0
        ),
    }
    features.update(
        {
            f"feature_has_{name}": int(pattern.search(question) is not None)
            for name, pattern in _LEXICAL_INDICATORS.items()
        }
    )
    return features


def choose_depth_target(
    correctness_by_depth: Mapping[int, bool], depths: Sequence[int] = DEFAULT_DEPTHS
) -> tuple[int, int | None, str]:
    """Return deployable depth action, observed lowest success, and label status."""

    ordered_depths = tuple(sorted(depths))
    if not ordered_depths or set(correctness_by_depth) != set(ordered_depths):
        raise ValueError("correctness_by_depth must contain every configured depth exactly once")
    successful = [depth for depth in ordered_depths if correctness_by_depth[depth]]
    if successful:
        lowest = min(successful)
        return lowest, lowest, "observed_success"
    return max(ordered_depths), None, "max_depth_fallback_unsolved"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                payload = json.loads(line)
                if not isinstance(payload, dict):
                    raise ValueError(f"JSONL row {line_number} is not an object")
                rows.append(payload)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read raw samples {path}: {exc}") from exc
    return rows


def _read_csv(path: Path) -> list[dict[str, str]]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))
    except OSError as exc:
        raise ValueError(f"could not read configuration results {path}: {exc}") from exc


def _development_rows(split_manifest: Mapping[str, Any]) -> list[tuple[str, Mapping[str, Any]]]:
    output: list[tuple[str, Mapping[str, Any]]] = []
    for partition in DEVELOPMENT_PARTITIONS:
        output.extend((partition, row) for row in split_manifest["partitions"][partition])
    return output


def _raw_input_metadata(
    raw_rows: Sequence[Mapping[str, Any]],
    *,
    repetition_id: int,
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in raw_rows:
        if int(row.get("repetition_id", 0)) == repetition_id:
            grouped[str(row["problem_id"])].append(row)

    metadata: dict[str, dict[str, Any]] = {}
    for problem_id, rows in grouped.items():
        questions = {str(row["question"]) for row in rows}
        prompt_tokens = {int(row["prompt_tokens"]) for row in rows}
        ground_truths = {str(row["ground_truth"]) for row in rows}
        if len(questions) != 1 or len(prompt_tokens) != 1 or len(ground_truths) != 1:
            raise ValueError(f"inconsistent raw input metadata for {problem_id}")
        metadata[problem_id] = {
            "question": questions.pop(),
            "prompt_token_count": prompt_tokens.pop(),
            "ground_truth": ground_truths.pop(),
        }
    return metadata


def _k1_outcomes(
    config_rows: Sequence[Mapping[str, Any]],
    *,
    repetition_id: int,
    depths: Sequence[int],
) -> dict[str, dict[int, dict[str, Any]]]:
    grouped: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
    allowed_depths = set(depths)
    for row in config_rows:
        if int(row["k"]) != 1 or int(row.get("repetition_id", 0)) != repetition_id:
            continue
        depth = int(row["L"])
        if depth not in allowed_depths:
            continue
        problem_id = str(row["problem_id"])
        if depth in grouped[problem_id]:
            raise ValueError(f"duplicate k=1 outcome for {problem_id} at L={depth}")
        grouped[problem_id][depth] = {
            "correct": _parse_bool(row["final_correct"]),
            "actual_generated_tokens": int(row["actual_generated_tokens"]),
            "latency_ms": float(row["sum_sample_latency_ms"]),
            "truncated": int(row["sample_truncation_count"]) > 0,
            "valid_answer_fraction": float(row["valid_answer_fraction"]),
        }
    return dict(grouped)


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    with temporary_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    temporary_path.replace(path)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(dict(payload), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)


def build_depth_controller_dataset(
    *,
    raw_samples_path: Path,
    config_results_path: Path,
    split_manifest_path: Path,
    output_dir: Path,
    source_experiment_id: str,
    repetition_id: int = 0,
    depths: Sequence[int] = DEFAULT_DEPTHS,
) -> dict[str, Any]:
    """Build Train/Validation rows without loading or materializing held-out test data."""

    ordered_depths = tuple(sorted(depths))
    if ordered_depths != DEFAULT_DEPTHS:
        raise ValueError(f"Phase 2 depth action space must remain {DEFAULT_DEPTHS}")
    split_manifest = read_phase2_split_manifest(split_manifest_path)
    split_rows = _development_rows(split_manifest)
    raw_metadata = _raw_input_metadata(_read_jsonl(raw_samples_path), repetition_id=repetition_id)
    outcomes = _k1_outcomes(
        _read_csv(config_results_path),
        repetition_id=repetition_id,
        depths=ordered_depths,
    )

    dataset_rows: list[dict[str, Any]] = []
    feature_names: list[str] | None = None
    for partition, split_row in split_rows:
        problem_id = str(split_row["problem_id"])
        if problem_id not in raw_metadata or problem_id not in outcomes:
            raise ValueError(f"missing development evidence for {problem_id}")
        if set(outcomes[problem_id]) != set(ordered_depths):
            raise ValueError(f"incomplete k=1 depth outcomes for {problem_id}")

        metadata = raw_metadata[problem_id]
        if _sha256_text(metadata["question"]) != split_row["question_sha256"]:
            raise ValueError(f"question hash mismatch for {problem_id}")
        if _sha256_text(metadata["ground_truth"]) != split_row["ground_truth_sha256"]:
            raise ValueError(f"ground-truth hash mismatch for {problem_id}")

        features = extract_question_features(
            metadata["question"], int(metadata["prompt_token_count"])
        )
        if feature_names is None:
            feature_names = list(features)
        elif list(features) != feature_names:
            raise AssertionError("feature extraction produced an unstable schema")

        correctness = {
            depth: bool(outcomes[problem_id][depth]["correct"]) for depth in ordered_depths
        }
        target_l, lowest_correct_l, target_status = choose_depth_target(
            correctness, ordered_depths
        )
        record: dict[str, Any] = {
            "problem_id": problem_id,
            "partition": partition,
            "question_sha256": split_row["question_sha256"],
            **features,
            "label_depth_target_L": target_l,
            "label_observed_lowest_correct_L": (
                lowest_correct_l if lowest_correct_l is not None else ""
            ),
            "label_target_status": target_status,
            "label_escalate_beyond_512": int(target_l > 512),
            "label_escalate_beyond_1024": int(target_l > 1024),
        }
        for depth in ordered_depths:
            outcome = outcomes[problem_id][depth]
            record.update(
                {
                    f"outcome_k1_correct_L{depth}": int(outcome["correct"]),
                    f"outcome_k1_actual_tokens_L{depth}": outcome[
                        "actual_generated_tokens"
                    ],
                    f"outcome_k1_latency_ms_L{depth}": outcome["latency_ms"],
                    f"outcome_k1_truncated_L{depth}": int(outcome["truncated"]),
                    f"outcome_k1_valid_answer_fraction_L{depth}": outcome[
                        "valid_answer_fraction"
                    ],
                }
            )
        dataset_rows.append(record)

    if feature_names is None:
        raise ValueError("no development rows were available")
    identity_names = ["problem_id", "partition", "question_sha256"]
    label_names = [
        "label_depth_target_L",
        "label_observed_lowest_correct_L",
        "label_target_status",
        "label_escalate_beyond_512",
        "label_escalate_beyond_1024",
    ]
    outcome_names = [
        name
        for depth in ordered_depths
        for name in (
            f"outcome_k1_correct_L{depth}",
            f"outcome_k1_actual_tokens_L{depth}",
            f"outcome_k1_latency_ms_L{depth}",
            f"outcome_k1_truncated_L{depth}",
            f"outcome_k1_valid_answer_fraction_L{depth}",
        )
    ]
    fieldnames = identity_names + feature_names + label_names + outcome_names

    combined_path = output_dir / "depth_controller_development.csv"
    train_path = output_dir / "depth_controller_train.csv"
    validation_path = output_dir / "depth_controller_validation.csv"
    schema_path = output_dir / "feature_schema.json"
    manifest_path = output_dir / "dataset_manifest.json"
    _write_csv(combined_path, dataset_rows, fieldnames)
    _write_csv(
        train_path,
        [row for row in dataset_rows if row["partition"] == "train"],
        fieldnames,
    )
    _write_csv(
        validation_path,
        [row for row in dataset_rows if row["partition"] == "validation"],
        fieldnames,
    )
    _write_json(
        schema_path,
        {
            "schema_version": DEPTH_FEATURE_SCHEMA_VERSION,
            "feature_availability": "pre_generation_input_only",
            "feature_names": feature_names,
            "label_names": label_names,
            "outcome_names": outcome_names,
            "forbidden_as_model_inputs": label_names + outcome_names,
            "label_policy": DEPTH_LABEL_POLICY,
            "depth_action_space": list(ordered_depths),
        },
    )

    partition_counts = Counter(str(row["partition"]) for row in dataset_rows)
    target_distribution = {
        partition: dict(
            sorted(
                Counter(
                    int(row["label_depth_target_L"])
                    for row in dataset_rows
                    if row["partition"] == partition
                ).items()
            )
        )
        for partition in DEVELOPMENT_PARTITIONS
    }
    target_status_distribution = {
        partition: dict(
            sorted(
                Counter(
                    str(row["label_target_status"])
                    for row in dataset_rows
                    if row["partition"] == partition
                ).items()
            )
        )
        for partition in DEVELOPMENT_PARTITIONS
    }
    manifest = {
        "schema_version": 1,
        "artifact_type": "phase2_depth_controller_development_data",
        "source_experiment_id": source_experiment_id,
        "source_repetition_id": repetition_id,
        "source_hashes": {
            "raw_samples_sha256": file_sha256(raw_samples_path),
            "config_results_sha256": file_sha256(config_results_path),
            "phase2_split_manifest_sha256": file_sha256(split_manifest_path),
        },
        "feature_schema_version": DEPTH_FEATURE_SCHEMA_VERSION,
        "label_policy": DEPTH_LABEL_POLICY,
        "depth_action_space": list(ordered_depths),
        "held_out_test_materialized": False,
        "row_counts": {
            "total": len(dataset_rows),
            **{partition: partition_counts[partition] for partition in DEVELOPMENT_PARTITIONS},
        },
        "target_distribution": target_distribution,
        "target_status_distribution": target_status_distribution,
        "artifacts": {
            "development_csv": combined_path.name,
            "development_csv_sha256": file_sha256(combined_path),
            "train_csv": train_path.name,
            "train_csv_sha256": file_sha256(train_path),
            "validation_csv": validation_path.name,
            "validation_csv_sha256": file_sha256(validation_path),
            "feature_schema": schema_path.name,
            "feature_schema_sha256": file_sha256(schema_path),
        },
    }
    _write_json(manifest_path, manifest)
    return manifest
