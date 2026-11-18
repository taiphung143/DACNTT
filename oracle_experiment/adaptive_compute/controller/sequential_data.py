"""Leakage-safe sequential marginal-utility labels for Phase 2."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from adaptive_compute.controller.depth_data import extract_question_features
from adaptive_compute.math500_splits import read_math500_split_manifest
from adaptive_compute.phase2_splits import file_sha256, read_phase2_split_manifest


SEQUENTIAL_SCHEMA_VERSION = 1
SEQUENTIAL_LABEL_POLICY = "normalized-realized-marginal-utility-v1"
DEFAULT_LAMBDAS = (0.02, 0.05, 0.10)
DEFAULT_DEPTHS = (512, 1024, 2048)
DEFAULT_BREADTHS = (1, 2, 4)
DEFAULT_TOKEN_REFERENCE = 2048
MATH500_DEPTHS = (1024, 2048, 4096)
MATH500_TOKEN_REFERENCE = 4096

FROZEN_DATASET_SETTINGS = {
    "gsm8k": {
        "depths": DEFAULT_DEPTHS,
        "breadths": DEFAULT_BREADTHS,
        "token_reference": DEFAULT_TOKEN_REFERENCE,
    },
    "math500": {
        "depths": MATH500_DEPTHS,
        "breadths": DEFAULT_BREADTHS,
        "token_reference": MATH500_TOKEN_REFERENCE,
    },
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError(f"JSONL row {line_number} is not an object")
            rows.append(payload)
    return rows


def _read_frozen_split_manifest(path: Path) -> tuple[str, dict[str, Any]]:
    """Read and validate a supported dataset's frozen split manifest."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read required split manifest {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"expected a JSON object in split manifest: {path}")
    dataset = str(payload.get("dataset", "")).strip().lower()
    if dataset == "gsm8k":
        return dataset, read_phase2_split_manifest(path)
    if dataset == "math500":
        return dataset, read_math500_split_manifest(path)
    raise ValueError(f"unsupported sequential-label dataset: {dataset or '<missing>'}")


def _parse_bool(value: Any) -> bool:
    if value is True or str(value).strip().lower() == "true":
        return True
    if value is False or str(value).strip().lower() == "false":
        return False
    raise ValueError(f"expected Boolean value, found {value!r}")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def marginal_utility_label(
    *,
    correct_before: bool,
    correct_after: bool,
    tokens_before: int,
    tokens_after: int,
    lambda_value: float,
    token_reference: int,
) -> tuple[float, int]:
    """Return realized utility change and its positive-escalation label."""

    if tokens_before < 0 or tokens_after < tokens_before:
        raise ValueError("transition tokens must be non-negative and monotone")
    if lambda_value < 0 or token_reference <= 0:
        raise ValueError("lambda must be non-negative and token_reference positive")
    delta = int(correct_after) - int(correct_before) - lambda_value * (
        tokens_after - tokens_before
    ) / token_reference
    return delta, int(delta > 0)


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty sequential table: {path.name}")
    fieldnames: list[str] = []
    for row in rows:
        for name in row:
            if name not in fieldnames:
                fieldnames.append(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(dict(payload), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _partition_map(split_manifest: Mapping[str, Any]) -> dict[str, str]:
    return {
        str(row["problem_id"]): partition
        for partition, rows in split_manifest["partitions"].items()
        for row in rows
    }


def _split_rows(split_manifest: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        str(row["problem_id"]): row
        for rows in split_manifest["partitions"].values()
        for row in rows
    }


def _input_metadata(raw_rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in raw_rows:
        if int(row.get("repetition_id", 0)) == 0:
            grouped[str(row["problem_id"])].append(row)
    output: dict[str, dict[str, Any]] = {}
    for problem_id, rows in grouped.items():
        questions = {str(row["question"]) for row in rows}
        ground_truths = {str(row["ground_truth"]) for row in rows}
        prompt_tokens = {int(row["prompt_tokens"]) for row in rows}
        if len(questions) != 1 or len(ground_truths) != 1 or len(prompt_tokens) != 1:
            raise ValueError(f"inconsistent input metadata for {problem_id}")
        output[problem_id] = {
            "question": questions.pop(),
            "ground_truth": ground_truths.pop(),
            "prompt_token_count": prompt_tokens.pop(),
        }
    return output


def _configuration_index(
    rows: Sequence[Mapping[str, Any]],
) -> dict[tuple[str, int, int], dict[str, Any]]:
    index: dict[tuple[str, int, int], dict[str, Any]] = {}
    for row in rows:
        if int(row.get("repetition_id", 0)) != 0:
            continue
        key = (str(row["problem_id"]), int(row["k"]), int(row["L"]))
        if key in index:
            raise ValueError(f"duplicate configuration row: {key}")
        index[key] = {
            "correct": _parse_bool(row["final_correct"]),
            "actual_tokens": int(row["actual_generated_tokens"]),
            "allocated_budget": int(row["allocated_token_budget"]),
            "valid_answer_count": int(row["valid_answer_count"]),
            "invalid_answer_count": int(row["invalid_answer_count"]),
            "valid_answer_fraction": float(row["valid_answer_fraction"]),
            "agreement": (
                float(row["agreement"])
                if str(row.get("agreement", "")).strip()
                else None
            ),
            "truncation_count": int(row["sample_truncation_count"]),
        }
    return index


def _state_features(outcome: Mapping[str, Any], *, k: int, length: int) -> dict[str, Any]:
    agreement = outcome["agreement"]
    return {
        "feature_state_k": k,
        "feature_state_L": length,
        "feature_state_actual_tokens": outcome["actual_tokens"],
        "feature_state_allocated_budget": outcome["allocated_budget"],
        "feature_state_token_utilization": (
            outcome["actual_tokens"] / outcome["allocated_budget"]
        ),
        "feature_state_valid_answer_count": outcome["valid_answer_count"],
        "feature_state_invalid_answer_count": outcome["invalid_answer_count"],
        "feature_state_valid_answer_fraction": outcome["valid_answer_fraction"],
        "feature_state_agreement_available": int(agreement is not None),
        "feature_state_agreement": agreement if agreement is not None else -1.0,
        "feature_state_truncation_count": outcome["truncation_count"],
        "feature_state_truncation_rate": outcome["truncation_count"] / k,
    }


def _balance(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    grouped: dict[tuple[str, float], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["stage"]), float(row["lambda"]))].append(row)
    stages: dict[str, Any] = {}
    for (stage, lambda_value), group in sorted(grouped.items()):
        positives = sum(int(row["label_escalate"]) for row in group)
        stage_payload = stages.setdefault(stage, {})
        stage_payload[f"{lambda_value:.2f}"] = {
            "total": len(group),
            "positive": positives,
            "negative": len(group) - positives,
            "positive_rate": positives / len(group),
            "meets_30_positive_floor": positives >= 30,
        }
    return stages


def build_sequential_controller_dataset(
    *,
    experiment_dir: Path,
    split_manifest_path: Path,
    output_dir: Path,
    lambdas: Sequence[float] = DEFAULT_LAMBDAS,
    depths: Sequence[int] | None = None,
    breadths: Sequence[int] | None = None,
    token_reference: int | None = None,
) -> dict[str, Any]:
    """Materialize depth and breadth labels without accessing held-out Test."""

    if output_dir.exists():
        raise FileExistsError(f"sequential dataset output already exists: {output_dir}")

    dataset_name, split_manifest = _read_frozen_split_manifest(split_manifest_path)
    frozen_settings = FROZEN_DATASET_SETTINGS[dataset_name]
    selected_depths = frozen_settings["depths"] if depths is None else depths
    selected_breadths = frozen_settings["breadths"] if breadths is None else breadths
    selected_token_reference = (
        int(frozen_settings["token_reference"])
        if token_reference is None
        else int(token_reference)
    )
    ordered_depths = tuple(sorted(int(value) for value in selected_depths))
    ordered_breadths = tuple(sorted(int(value) for value in selected_breadths))
    lambda_grid = tuple(float(value) for value in lambdas)
    if ordered_depths != frozen_settings["depths"]:
        raise ValueError(
            f"sequential depth action space for {dataset_name} must remain "
            f"{frozen_settings['depths']}"
        )
    if ordered_breadths != frozen_settings["breadths"]:
        raise ValueError(
            f"sequential breadth action space for {dataset_name} must remain "
            f"{frozen_settings['breadths']}"
        )
    if selected_token_reference != frozen_settings["token_reference"]:
        raise ValueError(
            f"token reference for {dataset_name} must remain "
            f"{frozen_settings['token_reference']}"
        )
    if not lambda_grid or any(value < 0 for value in lambda_grid):
        raise ValueError("lambda grid must contain non-negative values")

    raw_path = experiment_dir / "raw_samples.jsonl"
    config_path = experiment_dir / "config_results.csv"
    experiment_manifest_path = experiment_dir / "experiment_manifest.json"
    experiment_manifest = json.loads(experiment_manifest_path.read_text(encoding="utf-8"))
    manifest_depths = experiment_manifest.get("L_values")
    manifest_breadths = experiment_manifest.get("k_values")
    if manifest_depths is not None and tuple(sorted(map(int, manifest_depths))) != ordered_depths:
        raise ValueError("experiment depth action space disagrees with frozen protocol")
    if manifest_breadths is not None and tuple(sorted(map(int, manifest_breadths))) != ordered_breadths:
        raise ValueError("experiment breadth action space disagrees with frozen protocol")
    partitions = _partition_map(split_manifest)
    split_identity = _split_rows(split_manifest)
    metadata = _input_metadata(_read_jsonl(raw_path))
    configurations = _configuration_index(_read_csv(config_path))
    problem_ids = sorted({key[0] for key in configurations})
    if not problem_ids:
        raise ValueError("no configuration rows found")
    for problem_id in problem_ids:
        partition = partitions.get(problem_id)
        if partition is None:
            raise ValueError(f"problem is absent from frozen split: {problem_id}")
        if partition == "test":
            raise ValueError(f"held-out Test problem must not be materialized: {problem_id}")
        if problem_id not in metadata:
            raise ValueError(f"missing raw input metadata for {problem_id}")
        if _sha256_text(metadata[problem_id]["question"]) != split_identity[problem_id][
            "question_sha256"
        ]:
            raise ValueError(f"question hash disagrees with frozen split: {problem_id}")
        if _sha256_text(metadata[problem_id]["ground_truth"]) != split_identity[
            problem_id
        ]["ground_truth_sha256"]:
            raise ValueError(f"ground-truth hash disagrees with frozen split: {problem_id}")
        for k in ordered_breadths:
            for length in ordered_depths:
                if (problem_id, k, length) not in configurations:
                    raise ValueError(f"incomplete configuration grid for {problem_id}")

    depth_rows: list[dict[str, Any]] = []
    breadth_rows: list[dict[str, Any]] = []
    input_feature_names: list[str] | None = None
    for problem_id in problem_ids:
        partition = partitions[problem_id]
        info = metadata[problem_id]
        input_features = extract_question_features(
            info["question"], int(info["prompt_token_count"])
        )
        if input_feature_names is None:
            input_feature_names = list(input_features)
        elif list(input_features) != input_feature_names:
            raise AssertionError("input feature schema is unstable")
        identity = {
            "problem_id": problem_id,
            "partition": partition,
            "question_sha256": split_identity[problem_id]["question_sha256"],
        }

        for lower, upper in zip(ordered_depths, ordered_depths[1:]):
            before = configurations[(problem_id, 1, lower)]
            after = configurations[(problem_id, 1, upper)]
            for lambda_value in lambda_grid:
                delta, label = marginal_utility_label(
                    correct_before=before["correct"],
                    correct_after=after["correct"],
                    tokens_before=before["actual_tokens"],
                    tokens_after=after["actual_tokens"],
                    lambda_value=lambda_value,
                    token_reference=selected_token_reference,
                )
                depth_rows.append(
                    {
                        **identity,
                        "stage": f"depth_L{lower}_to_L{upper}",
                        "action": f"increase_L_to_{upper}",
                        "lambda": lambda_value,
                        **input_features,
                        "label_escalate": label,
                        "label_delta_utility": delta,
                        "outcome_correct_before": int(before["correct"]),
                        "outcome_correct_after": int(after["correct"]),
                        "outcome_delta_correct": int(after["correct"])
                        - int(before["correct"]),
                        "outcome_tokens_before": before["actual_tokens"],
                        "outcome_tokens_after": after["actual_tokens"],
                        "outcome_delta_tokens": after["actual_tokens"]
                        - before["actual_tokens"],
                    }
                )

        for length in ordered_depths:
            for lower_k, upper_k in zip(
                ordered_breadths, ordered_breadths[1:]
            ):
                before = configurations[(problem_id, lower_k, length)]
                after = configurations[(problem_id, upper_k, length)]
                state_features = _state_features(before, k=lower_k, length=length)
                for lambda_value in lambda_grid:
                    delta, label = marginal_utility_label(
                        correct_before=before["correct"],
                        correct_after=after["correct"],
                        tokens_before=before["actual_tokens"],
                        tokens_after=after["actual_tokens"],
                        lambda_value=lambda_value,
                        token_reference=selected_token_reference,
                    )
                    breadth_rows.append(
                        {
                            **identity,
                            "stage": f"breadth_L{length}_k{lower_k}_to_k{upper_k}",
                            "action": f"increase_k_to_{upper_k}",
                            "lambda": lambda_value,
                            **input_features,
                            **state_features,
                            "label_escalate": label,
                            "label_delta_utility": delta,
                            "outcome_correct_before": int(before["correct"]),
                            "outcome_correct_after": int(after["correct"]),
                            "outcome_delta_correct": int(after["correct"])
                            - int(before["correct"]),
                            "outcome_tokens_before": before["actual_tokens"],
                            "outcome_tokens_after": after["actual_tokens"],
                            "outcome_delta_tokens": after["actual_tokens"]
                            - before["actual_tokens"],
                        }
                    )

    depth_path = output_dir / "depth_marginal_utility_labels.csv"
    breadth_path = output_dir / "breadth_marginal_utility_labels.csv"
    balance_path = output_dir / "label_balance.json"
    schema_path = output_dir / "feature_schema.json"
    manifest_path = output_dir / "dataset_manifest.json"
    _write_csv(depth_path, depth_rows)
    _write_csv(breadth_path, breadth_rows)
    balance = {
        "positive_floor": 30,
        "depth": _balance(depth_rows),
        "breadth": _balance(breadth_rows),
    }
    _write_json(balance_path, balance)
    state_feature_names = [
        name for name in breadth_rows[0] if name.startswith("feature_state_")
    ]
    label_names = ["label_escalate", "label_delta_utility"]
    outcome_names = [
        "outcome_correct_before",
        "outcome_correct_after",
        "outcome_delta_correct",
        "outcome_tokens_before",
        "outcome_tokens_after",
        "outcome_delta_tokens",
    ]
    _write_json(
        schema_path,
        {
            "schema_version": SEQUENTIAL_SCHEMA_VERSION,
            "input_feature_names": input_feature_names or [],
            "paid_state_feature_names": state_feature_names,
            "label_names": label_names,
            "outcome_names": outcome_names,
            "forbidden_as_model_inputs": label_names + outcome_names,
            "label_policy": SEQUENTIAL_LABEL_POLICY,
            "dataset": dataset_name,
            "token_reference": selected_token_reference,
            "lambda_grid": list(lambda_grid),
        },
    )
    partition_counts = Counter(partitions[problem_id] for problem_id in problem_ids)
    manifest = {
        "schema_version": 1,
        "artifact_type": "phase2_sequential_marginal_utility_labels",
        "dataset": dataset_name,
        "source_experiment_id": experiment_manifest["experiment_id"],
        "source_model": experiment_manifest["model"],
        "source_model_revision": experiment_manifest["model_revision"],
        "source_prompt_template_name": experiment_manifest["prompt_template_name"],
        "source_answer_parser_name": experiment_manifest["answer_parser_name"],
        "label_policy": SEQUENTIAL_LABEL_POLICY,
        "lambda_grid": list(lambda_grid),
        "token_reference": selected_token_reference,
        "depth_action_space": list(ordered_depths),
        "breadth_action_space": list(ordered_breadths),
        "held_out_test_materialized": False,
        "problem_counts": {"total": len(problem_ids), **dict(partition_counts)},
        "row_counts": {"depth": len(depth_rows), "breadth": len(breadth_rows)},
        "source_hashes": {
            "raw_samples_sha256": file_sha256(raw_path),
            "config_results_sha256": file_sha256(config_path),
            "experiment_manifest_sha256": file_sha256(experiment_manifest_path),
            "split_manifest_sha256": file_sha256(split_manifest_path),
        },
        "artifacts": {
            "depth_labels": depth_path.name,
            "depth_labels_sha256": file_sha256(depth_path),
            "breadth_labels": breadth_path.name,
            "breadth_labels_sha256": file_sha256(breadth_path),
            "label_balance": balance_path.name,
            "label_balance_sha256": file_sha256(balance_path),
            "feature_schema": schema_path.name,
            "feature_schema_sha256": file_sha256(schema_path),
        },
    }
    _write_json(manifest_path, manifest)
    return manifest
