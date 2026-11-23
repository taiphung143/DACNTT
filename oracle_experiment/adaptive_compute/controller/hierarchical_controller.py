"""Offline feasibility study for a leakage-safe hierarchical controller.

The study pools the frozen GSM8K and MATH-500 Train label artifacts, produces
out-of-fold (OOF) predictions with problem-grouped cross-validation, and
replays those predictions as a sequential depth/breadth policy.  It never
loads the already-opened Test-100 artifacts and its results are development
evidence, not confirmatory evidence.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean
from typing import Any

from adaptive_compute.phase2_splits import file_sha256


CONTROLLER_SCHEMA_VERSION = 1
DEFAULT_LAMBDA = 0.05
DEFAULT_FOLDS = 5
DEFAULT_RANDOM_SEED = 42
DEFAULT_C = 1.0
DEFAULT_THRESHOLDS = (
    0.0,
    0.001,
    0.005,
    0.01,
    0.02,
    0.05,
    0.10,
    0.20,
    0.30,
    0.40,
    0.50,
    0.60,
    0.70,
    0.80,
)
DEFAULT_NONINFERIORITY_MARGIN = 0.02
DEFAULT_TOKEN_SAVING_TARGET = 0.10

DATASET_DEPTHS: dict[str, tuple[int, int, int]] = {
    "gsm8k": (512, 1024, 2048),
    "math500": (1024, 2048, 4096),
}
DATASET_TOKEN_REFERENCE = {"gsm8k": 2048, "math500": 4096}
BREADTH_ACTIONS = (1, 2, 4)

DEPTH_CONTEXT_FEATURES = (
    "feature_context_dataset_math500",
    "feature_context_stage_index",
    "feature_context_current_L_fraction",
    "feature_context_next_L_fraction",
)
BREADTH_CONTEXT_FEATURES = (
    "feature_context_dataset_math500",
    "feature_context_stage_index",
    "feature_context_L_fraction",
    "feature_state_actual_tokens_fraction",
    "feature_state_allocated_budget_fraction",
)
BREADTH_STATE_FEATURES = (
    "feature_state_token_utilization",
    "feature_state_valid_answer_count",
    "feature_state_invalid_answer_count",
    "feature_state_valid_answer_fraction",
    "feature_state_agreement_available",
    "feature_state_agreement",
    "feature_state_truncation_count",
    "feature_state_truncation_rate",
)


@dataclass(frozen=True)
class SequentialLabelSource:
    """One frozen Train-only sequential-label artifact."""

    dataset: str
    label_dir: Path

    def __post_init__(self) -> None:
        if self.dataset not in DATASET_DEPTHS:
            raise ValueError(f"unsupported controller dataset: {self.dataset}")
        object.__setattr__(self, "label_dir", Path(self.label_dir))


def _read_csv(path: Path) -> list[dict[str, str]]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    except OSError as exc:
        raise ValueError(f"could not read controller table {path}: {exc}") from exc
    if not rows:
        raise ValueError(f"controller table is empty: {path}")
    return rows


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read controller metadata {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"controller metadata must be an object: {path}")
    return payload


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty controller table: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for name in row:
            if name not in fieldnames:
                fieldnames.append(name)
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


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def _parse_float(row: Mapping[str, Any], name: str) -> float:
    try:
        value = float(row[name])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"missing or invalid numeric column {name}") from exc
    if not math.isfinite(value):
        raise ValueError(f"non-finite value in {name}")
    return value


def _parse_int(row: Mapping[str, Any], name: str) -> int:
    value = _parse_float(row, name)
    if not value.is_integer():
        raise ValueError(f"expected integer in {name}, found {value}")
    return int(value)


def _artifact_path(label_dir: Path, manifest: Mapping[str, Any], key: str) -> Path:
    artifacts = manifest.get("artifacts", {})
    filename = artifacts.get(key)
    expected_hash = artifacts.get(f"{key}_sha256")
    if not isinstance(filename, str) or not filename:
        raise ValueError(f"manifest is missing artifact {key}")
    path = label_dir / filename
    if not path.is_file():
        raise ValueError(f"controller artifact does not exist: {path}")
    if expected_hash is not None and file_sha256(path) != expected_hash:
        raise ValueError(f"controller artifact hash mismatch: {path}")
    return path


def _filter_lambda(
    rows: Sequence[dict[str, str]], *, lambda_value: float
) -> list[dict[str, str]]:
    selected = [
        row
        for row in rows
        if math.isclose(_parse_float(row, "lambda"), lambda_value, abs_tol=1e-12)
    ]
    if not selected:
        raise ValueError(f"no sequential rows exist for lambda={lambda_value:g}")
    return selected


def _load_source(
    source: SequentialLabelSource,
    *,
    lambda_value: float,
    expected_partition: str = "train",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    label_dir = source.label_dir
    manifest_path = label_dir / "dataset_manifest.json"
    schema_path = label_dir / "feature_schema.json"
    manifest = _read_json(manifest_path)
    schema = _read_json(schema_path)
    if manifest.get("artifact_type") != "phase2_sequential_marginal_utility_labels":
        raise ValueError(f"unexpected label artifact type for {source.dataset}")
    if manifest.get("held_out_test_materialized") is not False:
        raise ValueError(f"{source.dataset} artifact does not certify Test isolation")
    recorded_dataset = manifest.get("dataset")
    if recorded_dataset is not None and recorded_dataset != source.dataset:
        raise ValueError(f"dataset identity mismatch for {source.dataset}")
    if expected_partition not in ("train", "validation"):
        raise ValueError(f"unsupported controller partition: {expected_partition}")
    if set(manifest.get("problem_counts", {})) - {"total", expected_partition}:
        raise ValueError(
            f"{source.dataset} artifact contains a partition other than "
            f"{expected_partition}"
        )
    if int(manifest.get("problem_counts", {}).get("total", 0)) != int(
        manifest.get("problem_counts", {}).get(expected_partition, -1)
    ):
        raise ValueError(
            f"{source.dataset} artifact is not {expected_partition}-only"
        )
    depths = tuple(int(value) for value in manifest.get("depth_action_space", []))
    if depths != DATASET_DEPTHS[source.dataset]:
        raise ValueError(f"unexpected depth action space for {source.dataset}: {depths}")
    breadths = tuple(int(value) for value in manifest.get("breadth_action_space", []))
    if breadths != BREADTH_ACTIONS:
        raise ValueError(f"unexpected breadth action space for {source.dataset}: {breadths}")
    if not any(
        math.isclose(float(value), lambda_value, abs_tol=1e-12)
        for value in manifest.get("lambda_grid", [])
    ):
        raise ValueError(f"lambda={lambda_value:g} is absent for {source.dataset}")
    token_reference = int(manifest.get("token_reference", 0))
    if token_reference != DATASET_TOKEN_REFERENCE[source.dataset]:
        raise ValueError(f"unexpected token reference for {source.dataset}")

    input_features = schema.get("input_feature_names")
    if not isinstance(input_features, list) or not input_features:
        raise ValueError(f"missing input feature allowlist for {source.dataset}")
    if any(not isinstance(name, str) or not name.startswith("feature_") for name in input_features):
        raise ValueError(f"invalid input feature allowlist for {source.dataset}")
    forbidden = set(schema.get("forbidden_as_model_inputs", []))
    if forbidden.intersection(input_features):
        raise ValueError(f"feature allowlist overlaps forbidden columns for {source.dataset}")

    depth_path = _artifact_path(label_dir, manifest, "depth_labels")
    breadth_path = _artifact_path(label_dir, manifest, "breadth_labels")
    depth_raw = _filter_lambda(_read_csv(depth_path), lambda_value=lambda_value)
    breadth_raw = _filter_lambda(_read_csv(breadth_path), lambda_value=lambda_value)
    expected_depth_stages = {
        f"depth_L{lower}_to_L{upper}": index
        for index, (lower, upper) in enumerate(zip(depths, depths[1:]))
    }
    expected_breadth_stages = {
        f"breadth_L{length}_k{lower}_to_k{upper}": (length, index)
        for length in depths
        for index, (lower, upper) in enumerate(zip(BREADTH_ACTIONS, BREADTH_ACTIONS[1:]))
    }

    depth_rows: list[dict[str, Any]] = []
    seen_depth: set[tuple[str, str]] = set()
    for raw in depth_raw:
        if raw.get("partition") != expected_partition:
            raise ValueError(
                f"non-{expected_partition} depth row in {source.dataset}"
            )
        stage = str(raw.get("stage", ""))
        if stage not in expected_depth_stages:
            raise ValueError(f"unexpected depth stage for {source.dataset}: {stage}")
        problem_id = str(raw.get("problem_id", ""))
        key = (problem_id, stage)
        if not problem_id or key in seen_depth:
            raise ValueError(f"duplicate or empty depth key for {source.dataset}: {key}")
        seen_depth.add(key)
        stage_index = expected_depth_stages[stage]
        lower, upper = depths[stage_index], depths[stage_index + 1]
        row: dict[str, Any] = dict(raw)
        row.update(
            {
                "dataset": source.dataset,
                "group_id": f"{source.dataset}|{problem_id}",
                "stage_index": stage_index,
                "current_L": lower,
                "next_L": upper,
                "feature_context_dataset_math500": int(source.dataset == "math500"),
                "feature_context_stage_index": stage_index,
                "feature_context_current_L_fraction": lower / token_reference,
                "feature_context_next_L_fraction": upper / token_reference,
            }
        )
        depth_rows.append(row)

    breadth_rows: list[dict[str, Any]] = []
    seen_breadth: set[tuple[str, str]] = set()
    for raw in breadth_raw:
        if raw.get("partition") != expected_partition:
            raise ValueError(
                f"non-{expected_partition} breadth row in {source.dataset}"
            )
        stage = str(raw.get("stage", ""))
        if stage not in expected_breadth_stages:
            raise ValueError(f"unexpected breadth stage for {source.dataset}: {stage}")
        problem_id = str(raw.get("problem_id", ""))
        key = (problem_id, stage)
        if not problem_id or key in seen_breadth:
            raise ValueError(f"duplicate or empty breadth key for {source.dataset}: {key}")
        seen_breadth.add(key)
        length, stage_index = expected_breadth_stages[stage]
        if _parse_int(raw, "feature_state_L") != length:
            raise ValueError(f"breadth state L disagrees with stage for {source.dataset}")
        expected_k = BREADTH_ACTIONS[stage_index]
        if _parse_int(raw, "feature_state_k") != expected_k:
            raise ValueError(f"breadth state k disagrees with stage for {source.dataset}")
        row = dict(raw)
        row.update(
            {
                "dataset": source.dataset,
                "group_id": f"{source.dataset}|{problem_id}",
                "stage_index": stage_index,
                "current_L": length,
                "feature_context_dataset_math500": int(source.dataset == "math500"),
                "feature_context_stage_index": stage_index,
                "feature_context_L_fraction": length / token_reference,
                "feature_state_actual_tokens_fraction": _parse_float(
                    raw, "feature_state_actual_tokens"
                )
                / token_reference,
                "feature_state_allocated_budget_fraction": _parse_float(
                    raw, "feature_state_allocated_budget"
                )
                / token_reference,
            }
        )
        breadth_rows.append(row)

    problem_count = int(manifest["problem_counts"][expected_partition])
    if len({row["group_id"] for row in depth_rows}) != problem_count:
        raise ValueError(f"depth problem count mismatch for {source.dataset}")
    if len({row["group_id"] for row in breadth_rows}) != problem_count:
        raise ValueError(f"breadth problem count mismatch for {source.dataset}")
    metadata = {
        "dataset": source.dataset,
        "partition": expected_partition,
        "label_dir": str(label_dir),
        "problem_count": problem_count,
        "input_feature_names": list(input_features),
        "manifest_path": str(manifest_path),
        "manifest_sha256": file_sha256(manifest_path),
        "schema_path": str(schema_path),
        "schema_sha256": file_sha256(schema_path),
        "depth_labels_path": str(depth_path),
        "depth_labels_sha256": file_sha256(depth_path),
        "breadth_labels_path": str(breadth_path),
        "breadth_labels_sha256": file_sha256(breadth_path),
        "source_model": manifest.get("source_model"),
        "source_model_revision": manifest.get("source_model_revision"),
        "source_split_manifest_sha256": manifest.get("source_hashes", {}).get(
            "split_manifest_sha256"
        ),
    }
    return depth_rows, breadth_rows, metadata


def load_pooled_train_labels(
    sources: Sequence[SequentialLabelSource], *, lambda_value: float = DEFAULT_LAMBDA
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Load and normalize multiple frozen Train-only label artifacts."""

    if not sources:
        raise ValueError("at least one sequential label source is required")
    datasets = [source.dataset for source in sources]
    if len(set(datasets)) != len(datasets):
        raise ValueError("each dataset may appear only once")
    if lambda_value < 0:
        raise ValueError("lambda must be non-negative")

    all_depth: list[dict[str, Any]] = []
    all_breadth: list[dict[str, Any]] = []
    source_metadata: list[dict[str, Any]] = []
    feature_contract: list[str] | None = None
    model_identity: tuple[Any, Any] | None = None
    for source in sources:
        depth_rows, breadth_rows, metadata = _load_source(
            source, lambda_value=lambda_value, expected_partition="train"
        )
        current_contract = metadata["input_feature_names"]
        if feature_contract is None:
            feature_contract = current_contract
        elif current_contract != feature_contract:
            raise ValueError("input feature contracts differ across datasets")
        current_model = (metadata["source_model"], metadata["source_model_revision"])
        if model_identity is None:
            model_identity = current_model
        elif current_model != model_identity:
            raise ValueError("pooled controller sources use different model identities")
        all_depth.extend(depth_rows)
        all_breadth.extend(breadth_rows)
        source_metadata.append(metadata)

    depth_feature_names = list(feature_contract or []) + list(DEPTH_CONTEXT_FEATURES)
    breadth_feature_names = (
        list(feature_contract or [])
        + list(BREADTH_STATE_FEATURES)
        + list(BREADTH_CONTEXT_FEATURES)
    )
    forbidden_prefixes = ("label_", "outcome_")
    for name in depth_feature_names + breadth_feature_names:
        if not name.startswith("feature_") or name.startswith(forbidden_prefixes):
            raise ValueError(f"unsafe controller feature: {name}")
    return all_depth, all_breadth, {
        "lambda": lambda_value,
        "datasets": datasets,
        "problem_count": len({row["group_id"] for row in all_depth}),
        "input_feature_names": list(feature_contract or []),
        "depth_feature_names": depth_feature_names,
        "breadth_feature_names": breadth_feature_names,
        "sources": source_metadata,
        "model_identity": {
            "model": model_identity[0] if model_identity else None,
            "revision": model_identity[1] if model_identity else None,
        },
    }


def load_pooled_validation_labels(
    sources: Sequence[SequentialLabelSource], *, lambda_value: float = DEFAULT_LAMBDA
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Load frozen Validation-only labels under the Train feature contract."""

    if not sources:
        raise ValueError("at least one sequential label source is required")
    datasets = [source.dataset for source in sources]
    if len(set(datasets)) != len(datasets):
        raise ValueError("each dataset may appear only once")
    all_depth: list[dict[str, Any]] = []
    all_breadth: list[dict[str, Any]] = []
    source_metadata: list[dict[str, Any]] = []
    feature_contract: list[str] | None = None
    model_identity: tuple[Any, Any] | None = None
    for source in sources:
        depth_rows, breadth_rows, metadata = _load_source(
            source,
            lambda_value=lambda_value,
            expected_partition="validation",
        )
        current_contract = metadata["input_feature_names"]
        if feature_contract is None:
            feature_contract = current_contract
        elif current_contract != feature_contract:
            raise ValueError("input feature contracts differ across datasets")
        current_model = (metadata["source_model"], metadata["source_model_revision"])
        if model_identity is None:
            model_identity = current_model
        elif current_model != model_identity:
            raise ValueError("pooled controller sources use different model identities")
        all_depth.extend(depth_rows)
        all_breadth.extend(breadth_rows)
        source_metadata.append(metadata)
    return all_depth, all_breadth, {
        "lambda": lambda_value,
        "datasets": datasets,
        "partition": "validation",
        "problem_count": len({row["group_id"] for row in all_depth}),
        "input_feature_names": list(feature_contract or []),
        "depth_feature_names": list(feature_contract or [])
        + list(DEPTH_CONTEXT_FEATURES),
        "breadth_feature_names": list(feature_contract or [])
        + list(BREADTH_STATE_FEATURES)
        + list(BREADTH_CONTEXT_FEATURES),
        "sources": source_metadata,
        "model_identity": {
            "model": model_identity[0] if model_identity else None,
            "revision": model_identity[1] if model_identity else None,
        },
    }


def _feature_matrix(
    rows: Sequence[Mapping[str, Any]], feature_names: Sequence[str]
) -> list[list[float]]:
    matrix: list[list[float]] = []
    for row in rows:
        values = [_parse_float(row, name) for name in feature_names]
        matrix.append(values)
    return matrix


def grouped_oof_probabilities(
    rows: Sequence[Mapping[str, Any]],
    *,
    feature_names: Sequence[str],
    folds: int = DEFAULT_FOLDS,
    random_seed: int = DEFAULT_RANDOM_SEED,
    c_value: float = DEFAULT_C,
) -> tuple[list[float], list[int], list[dict[str, Any]], Any]:
    """Fit a logistic model with group-disjoint folds and return OOF scores."""

    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import StratifiedGroupKFold
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
    except ImportError as exc:
        raise RuntimeError("scikit-learn is required for controller feasibility") from exc
    if folds < 2:
        raise ValueError("fold count must be at least two")
    if c_value <= 0:
        raise ValueError("C must be positive")
    groups = [str(row["group_id"]) for row in rows]
    if len(set(groups)) < folds:
        raise ValueError("fold count exceeds the number of problem groups")
    labels = [_parse_int(row, "label_escalate") for row in rows]
    if set(labels) != {0, 1}:
        raise ValueError("controller labels must contain both binary classes")
    matrix = _feature_matrix(rows, feature_names)
    splitter = StratifiedGroupKFold(
        n_splits=folds, shuffle=True, random_state=random_seed
    )
    probabilities = [math.nan] * len(rows)
    fold_ids = [-1] * len(rows)
    fold_audit: list[dict[str, Any]] = []

    def new_pipeline() -> Any:
        return Pipeline(
            [
                ("scale", StandardScaler()),
                (
                    "classifier",
                    LogisticRegression(
                        C=float(c_value),
                        class_weight="balanced",
                        max_iter=5_000,
                        random_state=random_seed,
                        solver="lbfgs",
                    ),
                ),
            ]
        )

    for fold_id, (train_indices, validation_indices) in enumerate(
        splitter.split(matrix, labels, groups)
    ):
        train_groups = {groups[index] for index in train_indices}
        validation_groups = {groups[index] for index in validation_indices}
        overlap = train_groups.intersection(validation_groups)
        if overlap:
            raise AssertionError(f"group leakage in fold {fold_id}: {sorted(overlap)[:3]}")
        train_labels = [labels[index] for index in train_indices]
        if set(train_labels) != {0, 1}:
            raise ValueError(f"fold {fold_id} training rows contain only one class")
        pipeline = new_pipeline()
        pipeline.fit(
            [matrix[index] for index in train_indices], train_labels
        )
        classes = list(pipeline.named_steps["classifier"].classes_)
        positive_index = classes.index(1)
        fold_probabilities = pipeline.predict_proba(
            [matrix[index] for index in validation_indices]
        )[:, positive_index]
        for index, probability in zip(
            validation_indices, fold_probabilities, strict=True
        ):
            probabilities[int(index)] = float(probability)
            fold_ids[int(index)] = fold_id
        fold_audit.append(
            {
                "fold": fold_id,
                "train_rows": len(train_indices),
                "validation_rows": len(validation_indices),
                "train_groups": len(train_groups),
                "validation_groups": len(validation_groups),
                "group_overlap": 0,
                "train_positives": sum(train_labels),
                "validation_positives": sum(labels[index] for index in validation_indices),
            }
        )
    if any(not math.isfinite(value) for value in probabilities) or any(
        value < 0 for value in fold_ids
    ):
        raise AssertionError("OOF prediction coverage is incomplete")
    full_pipeline = new_pipeline()
    full_pipeline.fit(matrix, labels)
    return probabilities, fold_ids, fold_audit, full_pipeline


def fitted_probabilities(
    rows: Sequence[Mapping[str, Any]],
    *,
    feature_names: Sequence[str],
    pipeline: Any,
) -> list[float]:
    """Apply a frozen binary classifier to a new partition."""

    matrix = _feature_matrix(rows, feature_names)
    classes = list(pipeline.named_steps["classifier"].classes_)
    if 1 not in classes:
        raise ValueError("frozen controller model has no positive class")
    positive_index = classes.index(1)
    return [
        float(value)
        for value in pipeline.predict_proba(matrix)[:, positive_index]
    ]


def _classification_metrics(
    rows: Sequence[Mapping[str, Any]], probabilities: Sequence[float], *, family: str
) -> list[dict[str, Any]]:
    try:
        from sklearn.metrics import (
            average_precision_score,
            balanced_accuracy_score,
            brier_score_loss,
            f1_score,
            roc_auc_score,
        )
    except ImportError as exc:
        raise RuntimeError("scikit-learn is required for controller metrics") from exc
    if len(rows) != len(probabilities):
        raise ValueError("classification rows and probabilities are misaligned")
    output: list[dict[str, Any]] = []
    for dataset in ["pooled", *sorted({str(row["dataset"]) for row in rows})]:
        indices = [
            index
            for index, row in enumerate(rows)
            if dataset == "pooled" or row["dataset"] == dataset
        ]
        labels = [_parse_int(rows[index], "label_escalate") for index in indices]
        scores = [float(probabilities[index]) for index in indices]
        predictions = [int(value >= 0.5) for value in scores]
        output.append(
            {
                "family": family,
                "dataset": dataset,
                "rows": len(indices),
                "groups": len({str(rows[index]["group_id"]) for index in indices}),
                "positives": sum(labels),
                "positive_rate": fmean(labels),
                "roc_auc": float(roc_auc_score(labels, scores)),
                "average_precision": float(average_precision_score(labels, scores)),
                "brier_score": float(brier_score_loss(labels, scores)),
                "balanced_accuracy_at_0_5": float(
                    balanced_accuracy_score(labels, predictions)
                ),
                "f1_at_0_5": float(f1_score(labels, predictions, zero_division=0)),
            }
        )
    return output


def _outcome_at_k(
    first_transition: Mapping[str, Any],
    second_transition: Mapping[str, Any],
    selected_k: int,
) -> tuple[int, int]:
    if _parse_int(first_transition, "outcome_correct_after") != _parse_int(
        second_transition, "outcome_correct_before"
    ):
        raise ValueError("k=2 correctness is inconsistent across breadth stages")
    if _parse_int(first_transition, "outcome_tokens_after") != _parse_int(
        second_transition, "outcome_tokens_before"
    ):
        raise ValueError("k=2 token cost is inconsistent across breadth stages")
    if selected_k == 1:
        return (
            _parse_int(first_transition, "outcome_correct_before"),
            _parse_int(first_transition, "outcome_tokens_before"),
        )
    if selected_k == 2:
        return (
            _parse_int(first_transition, "outcome_correct_after"),
            _parse_int(first_transition, "outcome_tokens_after"),
        )
    if selected_k == 4:
        return (
            _parse_int(second_transition, "outcome_correct_after"),
            _parse_int(second_transition, "outcome_tokens_after"),
        )
    raise ValueError(f"unsupported breadth action: {selected_k}")


def replay_oof_controller(
    depth_rows: Sequence[Mapping[str, Any]],
    depth_probabilities: Sequence[float],
    breadth_rows: Sequence[Mapping[str, Any]],
    breadth_probabilities: Sequence[float],
    *,
    depth_threshold: float,
    breadth_threshold: float,
    policy_id: str = "oof_hierarchical_logistic",
    partition: str = "train_oof",
) -> list[dict[str, Any]]:
    """Replay OOF decisions into one deployable trace per Train problem."""

    if not 0 <= depth_threshold <= 1 or not 0 <= breadth_threshold <= 1:
        raise ValueError("controller thresholds must be in [0, 1]")
    if len(depth_rows) != len(depth_probabilities):
        raise ValueError("depth rows and probabilities are misaligned")
    if len(breadth_rows) != len(breadth_probabilities):
        raise ValueError("breadth rows and probabilities are misaligned")
    depth_index: dict[tuple[str, str, int], tuple[Mapping[str, Any], float]] = {}
    breadth_index: dict[
        tuple[str, str, int, int], tuple[Mapping[str, Any], float]
    ] = {}
    for row, probability in zip(depth_rows, depth_probabilities, strict=True):
        key = (str(row["dataset"]), str(row["problem_id"]), int(row["stage_index"]))
        if key in depth_index:
            raise ValueError(f"duplicate normalized depth row: {key}")
        depth_index[key] = (row, float(probability))
    for row, probability in zip(breadth_rows, breadth_probabilities, strict=True):
        key = (
            str(row["dataset"]),
            str(row["problem_id"]),
            int(row["current_L"]),
            int(row["stage_index"]),
        )
        if key in breadth_index:
            raise ValueError(f"duplicate normalized breadth row: {key}")
        breadth_index[key] = (row, float(probability))

    problem_keys = sorted({(key[0], key[1]) for key in depth_index})
    traces: list[dict[str, Any]] = []
    for dataset, problem_id in problem_keys:
        depths = DATASET_DEPTHS[dataset]
        depth_stage0, depth_p0 = depth_index[(dataset, problem_id, 0)]
        _, depth_p1 = depth_index[(dataset, problem_id, 1)]
        # The lowest cap remains a diagnostic action because its truncation
        # burden is too high.  The deployable router chooses only mid or high;
        # the low->mid rows still provide stage-conditioned training signal.
        if depth_p1 < depth_threshold:
            selected_l = depths[1]
            depth_reason = "select_mid"
        else:
            selected_l = depths[2]
            depth_reason = "select_high"
        breadth_stage0, breadth_p0 = breadth_index[
            (dataset, problem_id, selected_l, 0)
        ]
        breadth_stage1, breadth_p1 = breadth_index[
            (dataset, problem_id, selected_l, 1)
        ]
        first_valid = (
            _parse_int(breadth_stage0, "feature_state_valid_answer_count") == 1
        )
        first_truncated = (
            _parse_int(breadth_stage0, "feature_state_truncation_count") > 0
        )
        two_valid = (
            _parse_int(breadth_stage1, "feature_state_valid_answer_count") == 2
        )
        two_match = math.isclose(
            _parse_float(breadth_stage1, "feature_state_agreement"),
            1.0,
            abs_tol=1e-12,
        )
        # Safety constraints keep invalid/truncated first samples from being
        # treated as confident stops and preserve the strong registered
        # agreement rule after two paid samples.
        if first_valid and not first_truncated and breadth_p0 < breadth_threshold:
            selected_k = 1
            breadth_reason = "learned_stop_at_k1"
        elif two_valid and two_match:
            selected_k = 2
            breadth_reason = "safety_stop_two_matching_valid"
        elif breadth_p1 < breadth_threshold:
            selected_k = 2
            breadth_reason = "learned_stop_at_k2"
        else:
            selected_k = 4
            breadth_reason = "escalate_to_k4"
        correct, tokens = _outcome_at_k(
            breadth_stage0, breadth_stage1, selected_k
        )
        traces.append(
            {
                "policy_id": policy_id,
                "dataset": dataset,
                "problem_id": problem_id,
                "partition": partition,
                "selected_L": selected_l,
                "selected_k": selected_k,
                "depth_probability_low_to_mid": depth_p0,
                "depth_probability_mid_to_high": depth_p1,
                "breadth_probability_k1_to_k2": breadth_p0,
                "breadth_probability_k2_to_k4": breadth_p1,
                "depth_threshold": depth_threshold,
                "breadth_threshold": breadth_threshold,
                "depth_reason": depth_reason,
                "breadth_reason": breadth_reason,
                "correct": correct,
                "actual_generated_tokens": tokens,
                "normalized_actual_tokens": tokens
                / DATASET_TOKEN_REFERENCE[dataset],
                "token_reference": DATASET_TOKEN_REFERENCE[dataset],
                "question_sha256": depth_stage0["question_sha256"],
            }
        )
    return traces


def comparator_traces(
    breadth_rows: Sequence[Mapping[str, Any]],
    *,
    partition: str = "train_reconstruction",
) -> list[dict[str, Any]]:
    """Reconstruct strong high-cap fixed and agreement comparators."""

    index: dict[tuple[str, str, int, int], Mapping[str, Any]] = {}
    for row in breadth_rows:
        key = (
            str(row["dataset"]),
            str(row["problem_id"]),
            int(row["current_L"]),
            int(row["stage_index"]),
        )
        index[key] = row
    traces: list[dict[str, Any]] = []
    problem_keys = sorted({(key[0], key[1]) for key in index})
    for dataset, problem_id in problem_keys:
        high_l = DATASET_DEPTHS[dataset][-1]
        first = index[(dataset, problem_id, high_l, 0)]
        second = index[(dataset, problem_id, high_l, 1)]
        two_valid = _parse_int(second, "feature_state_valid_answer_count") == 2
        answers_match = math.isclose(
            _parse_float(second, "feature_state_agreement"), 1.0, abs_tol=1e-12
        )
        agreement_k = 2 if two_valid and answers_match else 4
        for policy_id, selected_k in (
            ("fixed_high_k1", 1),
            ("fixed_high_k2", 2),
            ("fixed_high_k4", 4),
            ("agreement_high", agreement_k),
        ):
            correct, tokens = _outcome_at_k(first, second, selected_k)
            traces.append(
                {
                    "policy_id": policy_id,
                    "dataset": dataset,
                    "problem_id": problem_id,
                    "partition": partition,
                    "selected_L": high_l,
                    "selected_k": selected_k,
                    "correct": correct,
                    "actual_generated_tokens": tokens,
                    "normalized_actual_tokens": tokens
                    / DATASET_TOKEN_REFERENCE[dataset],
                    "token_reference": DATASET_TOKEN_REFERENCE[dataset],
                    "question_sha256": first["question_sha256"],
                }
            )
    return traces


def summarize_policy_traces(
    traces: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in traces:
        grouped[(str(row["dataset"]), str(row["policy_id"]))].append(row)
        grouped[("pooled", str(row["policy_id"]))].append(row)
    output: list[dict[str, Any]] = []
    for (dataset, policy_id), rows in sorted(grouped.items()):
        output.append(
            {
                "dataset": dataset,
                "policy_id": policy_id,
                "problems": len(rows),
                "correct": sum(_parse_int(row, "correct") for row in rows),
                "accuracy": fmean(_parse_int(row, "correct") for row in rows),
                "mean_actual_generated_tokens": fmean(
                    _parse_float(row, "actual_generated_tokens") for row in rows
                ),
                "mean_normalized_actual_tokens": fmean(
                    _parse_float(row, "normalized_actual_tokens") for row in rows
                ),
                "selected_low_L": sum(
                    int(
                        _parse_int(row, "selected_L")
                        == DATASET_DEPTHS[str(row["dataset"])][0]
                    )
                    for row in rows
                ),
                "selected_mid_L": sum(
                    int(
                        _parse_int(row, "selected_L")
                        == DATASET_DEPTHS[str(row["dataset"])][1]
                    )
                    for row in rows
                ),
                "selected_high_L": sum(
                    int(
                        _parse_int(row, "selected_L")
                        == DATASET_DEPTHS[str(row["dataset"])][2]
                    )
                    for row in rows
                ),
                "selected_k1": sum(_parse_int(row, "selected_k") == 1 for row in rows),
                "selected_k2": sum(_parse_int(row, "selected_k") == 2 for row in rows),
                "selected_k4": sum(_parse_int(row, "selected_k") == 4 for row in rows),
            }
        )
    return output


def _summary_index(
    rows: Sequence[Mapping[str, Any]],
) -> dict[tuple[str, str], Mapping[str, Any]]:
    return {(str(row["dataset"]), str(row["policy_id"])): row for row in rows}


def _threshold_sweep(
    depth_rows: Sequence[Mapping[str, Any]],
    depth_probabilities: Sequence[float],
    breadth_rows: Sequence[Mapping[str, Any]],
    breadth_probabilities: Sequence[float],
    comparator_summary: Sequence[Mapping[str, Any]],
    *,
    thresholds: Sequence[float],
    noninferiority_margin: float,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    if not thresholds or any(not 0 <= value <= 1 for value in thresholds):
        raise ValueError("threshold grid must be non-empty and lie in [0, 1]")
    comparator_index = _summary_index(comparator_summary)
    candidates: list[dict[str, Any]] = []
    traces_by_candidate: dict[str, list[dict[str, Any]]] = {}
    for depth_threshold in thresholds:
        for breadth_threshold in thresholds:
            candidate_id = f"d={depth_threshold:g}|b={breadth_threshold:g}"
            traces = replay_oof_controller(
                depth_rows,
                depth_probabilities,
                breadth_rows,
                breadth_probabilities,
                depth_threshold=depth_threshold,
                breadth_threshold=breadth_threshold,
            )
            traces_by_candidate[candidate_id] = traces
            summary = _summary_index(summarize_policy_traces(traces))
            row: dict[str, Any] = {
                "candidate_id": candidate_id,
                "depth_threshold": depth_threshold,
                "breadth_threshold": breadth_threshold,
            }
            eligible_all = True
            savings_all = True
            minimum_gap = math.inf
            for dataset in ("gsm8k", "math500", "pooled"):
                learned = summary[(dataset, "oof_hierarchical_logistic")]
                baseline = comparator_index[(dataset, "agreement_high")]
                accuracy_gap = float(learned["accuracy"]) - float(baseline["accuracy"])
                token_saving = 1.0 - float(
                    learned["mean_normalized_actual_tokens"]
                ) / float(baseline["mean_normalized_actual_tokens"])
                prefix = dataset.replace("math500", "math")
                row.update(
                    {
                        f"{prefix}_accuracy": learned["accuracy"],
                        f"{prefix}_mean_tokens": learned[
                            "mean_actual_generated_tokens"
                        ],
                        f"{prefix}_mean_normalized_tokens": learned[
                            "mean_normalized_actual_tokens"
                        ],
                        f"{prefix}_accuracy_gap_vs_agreement": accuracy_gap,
                        f"{prefix}_token_saving_vs_agreement": token_saving,
                        f"{prefix}_selected_mid_L": learned["selected_mid_L"],
                        f"{prefix}_selected_high_L": learned["selected_high_L"],
                    }
                )
                if dataset != "pooled":
                    eligible_all &= accuracy_gap >= -noninferiority_margin
                    savings_all &= token_saving >= 0
                    minimum_gap = min(minimum_gap, accuracy_gap)
            row["noninferior_both_datasets"] = eligible_all
            row["nonnegative_saving_both_datasets"] = savings_all
            row["adaptive_depth_both_datasets"] = (
                int(row["gsm8k_selected_mid_L"]) > 0
                and int(row["math_selected_mid_L"]) > 0
            )
            row["minimum_dataset_accuracy_gap"] = minimum_gap
            candidates.append(row)

    eligible = [row for row in candidates if row["noninferior_both_datasets"]]
    eligible_joint = [row for row in eligible if row["adaptive_depth_both_datasets"]]
    if eligible_joint:
        selected = min(
            eligible_joint,
            key=lambda row: (
                float(row["pooled_mean_normalized_tokens"]),
                -float(row["pooled_accuracy"]),
                float(row["depth_threshold"]),
                float(row["breadth_threshold"]),
            ),
        )
    elif eligible:
        selected = min(
            eligible,
            key=lambda row: (
                float(row["pooled_mean_normalized_tokens"]),
                -float(row["pooled_accuracy"]),
                float(row["breadth_threshold"]),
            ),
        )
    else:
        selected = min(
            candidates,
            key=lambda row: (
                -float(row["minimum_dataset_accuracy_gap"]),
                -float(row["pooled_accuracy"]),
                float(row["pooled_mean_normalized_tokens"]),
            ),
        )
    selected_id = str(selected["candidate_id"])
    return candidates, dict(selected), traces_by_candidate[selected_id]


def _go_pivot_decision(
    selected: Mapping[str, Any], *, token_saving_target: float
) -> dict[str, Any]:
    noninferior = bool(selected["noninferior_both_datasets"])
    adaptive_depth = bool(selected["adaptive_depth_both_datasets"])
    savings = {
        "gsm8k": float(selected["gsm8k_token_saving_vs_agreement"]),
        "math500": float(selected["math_token_saving_vs_agreement"]),
        "pooled": float(selected["pooled_token_saving_vs_agreement"]),
    }
    if (
        noninferior
        and adaptive_depth
        and all(value >= token_saving_target for value in savings.values())
    ):
        status = "GO_JOINT_TO_FROZEN_VALIDATION"
        rationale = (
            "OOF development results meet the accuracy margin and token-saving "
            "target in both datasets while using both mid and high token caps; "
            "evaluate this joint candidate on untouched Validation before any "
            "reserve generation."
        )
    elif noninferior and all(
        value >= token_saving_target for value in savings.values()
    ):
        status = "GO_BREADTH_ONLY_TO_FROZEN_VALIDATION"
        rationale = (
            "OOF development results meet the accuracy and token-saving gates, "
            "but the selected policy always uses the high token cap. This is a "
            "learned selective-breadth candidate, not evidence for joint allocation."
        )
    elif noninferior:
        status = "CONDITIONAL_MORE_DATA_OR_THRESHOLD_REVIEW"
        rationale = (
            "OOF development accuracy is within the declared margin, but token "
            "savings are not strong and consistent enough for reserve evaluation."
        )
    else:
        status = "PIVOT_DO_NOT_GENERATE_RESERVE"
        rationale = (
            "No OOF threshold candidate stays within the accuracy margin on both "
            "datasets; do not spend GPU budget on a new reserve yet."
        )
    return {
        "status": status,
        "development_only": True,
        "selected_candidate_id": selected["candidate_id"],
        "noninferior_both_datasets": noninferior,
        "adaptive_depth_both_datasets": adaptive_depth,
        "token_saving_target": token_saving_target,
        "observed_token_saving_vs_agreement": savings,
        "rationale": rationale,
        "next_gate": (
            "Any deployable controller must be selected on frozen Validation and "
            "hashed before a new unused reserve set is opened."
        ),
    }


def run_hierarchical_controller_feasibility(
    *,
    sources: Sequence[SequentialLabelSource],
    output_dir: Path,
    lambda_value: float = DEFAULT_LAMBDA,
    folds: int = DEFAULT_FOLDS,
    random_seed: int = DEFAULT_RANDOM_SEED,
    c_value: float = DEFAULT_C,
    thresholds: Sequence[float] = DEFAULT_THRESHOLDS,
    noninferiority_margin: float = DEFAULT_NONINFERIORITY_MARGIN,
    token_saving_target: float = DEFAULT_TOKEN_SAVING_TARGET,
) -> dict[str, Any]:
    """Run the Train-only controller feasibility study and write an audit bundle."""

    try:
        import joblib
        import scipy
        import sklearn
    except ImportError as exc:
        raise RuntimeError(
            "scikit-learn and joblib are required for controller feasibility"
        ) from exc
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise FileExistsError(f"controller output already exists: {output_dir}")
    if not 0 <= noninferiority_margin < 1:
        raise ValueError("non-inferiority margin must lie in [0, 1)")
    if not 0 <= token_saving_target < 1:
        raise ValueError("token-saving target must lie in [0, 1)")

    depth_rows, breadth_rows, data_manifest = load_pooled_train_labels(
        sources, lambda_value=lambda_value
    )
    depth_probabilities, depth_fold_ids, depth_fold_audit, depth_model = (
        grouped_oof_probabilities(
            depth_rows,
            feature_names=data_manifest["depth_feature_names"],
            folds=folds,
            random_seed=random_seed,
            c_value=c_value,
        )
    )
    breadth_probabilities, breadth_fold_ids, breadth_fold_audit, breadth_model = (
        grouped_oof_probabilities(
            breadth_rows,
            feature_names=data_manifest["breadth_feature_names"],
            folds=folds,
            random_seed=random_seed,
            c_value=c_value,
        )
    )

    classification_rows = _classification_metrics(
        depth_rows, depth_probabilities, family="depth"
    ) + _classification_metrics(
        breadth_rows, breadth_probabilities, family="breadth"
    )
    oof_rows: list[dict[str, Any]] = []
    for family, rows, probabilities, fold_ids in (
        ("depth", depth_rows, depth_probabilities, depth_fold_ids),
        ("breadth", breadth_rows, breadth_probabilities, breadth_fold_ids),
    ):
        for row, probability, fold_id in zip(
            rows, probabilities, fold_ids, strict=True
        ):
            oof_rows.append(
                {
                    "family": family,
                    "dataset": row["dataset"],
                    "problem_id": row["problem_id"],
                    "group_id": row["group_id"],
                    "stage": row["stage"],
                    "stage_index": row["stage_index"],
                    "current_L": row["current_L"],
                    "label_escalate": _parse_int(row, "label_escalate"),
                    "oof_probability_escalate": probability,
                    "oof_fold": fold_id,
                }
            )

    comparators = comparator_traces(breadth_rows)
    comparator_summary = summarize_policy_traces(comparators)
    candidates, selected, selected_traces = _threshold_sweep(
        depth_rows,
        depth_probabilities,
        breadth_rows,
        breadth_probabilities,
        comparator_summary,
        thresholds=thresholds,
        noninferiority_margin=noninferiority_margin,
    )
    joint_candidate = selected
    joint_traces = [
        {**row, "policy_id": "oof_hybrid_joint_controller"}
        for row in selected_traces
    ]
    breadth_only_candidates = [
        row
        for row in candidates
        if row["noninferior_both_datasets"]
        and not row["adaptive_depth_both_datasets"]
        and math.isclose(float(row["depth_threshold"]), 0.0, abs_tol=1e-12)
    ]
    breadth_candidate = (
        min(
            breadth_only_candidates,
            key=lambda row: (
                float(row["pooled_mean_normalized_tokens"]),
                -float(row["pooled_accuracy"]),
                float(row["breadth_threshold"]),
            ),
        )
        if breadth_only_candidates
        else None
    )
    breadth_traces: list[dict[str, Any]] = []
    if breadth_candidate is not None:
        breadth_traces = [
            {**row, "policy_id": "oof_learned_breadth_high"}
            for row in replay_oof_controller(
                depth_rows,
                depth_probabilities,
                breadth_rows,
                breadth_probabilities,
                depth_threshold=float(breadth_candidate["depth_threshold"]),
                breadth_threshold=float(breadth_candidate["breadth_threshold"]),
            )
        ]
    selected_summary = summarize_policy_traces(
        joint_traces + breadth_traces + comparators
    )
    joint_decision = _go_pivot_decision(
        selected, token_saving_target=token_saving_target
    )
    breadth_decision = (
        _go_pivot_decision(breadth_candidate, token_saving_target=token_saving_target)
        if breadth_candidate is not None
        else {
            "status": "NO_NONINFERIOR_BREADTH_CANDIDATE",
            "development_only": True,
            "rationale": "No fixed-high learned-breadth candidate met the accuracy margin.",
        }
    )
    decision = {
        "development_only": True,
        "joint_candidate": joint_decision,
        "breadth_only_candidate": breadth_decision,
        "overall_interpretation": (
            "Advance only candidate roles whose own gate is GO. A breadth-only GO "
            "does not constitute evidence for successful joint depth-breadth allocation."
        ),
    }

    output_dir.mkdir(parents=True)
    oof_path = output_dir / "oof_decisions.csv"
    fold_path = output_dir / "fold_audit.csv"
    classification_path = output_dir / "oof_classification_metrics.csv"
    sweep_path = output_dir / "oof_threshold_sweep.csv"
    trace_path = output_dir / "selected_oof_policy_traces.csv"
    comparator_path = output_dir / "comparator_traces.csv"
    summary_path = output_dir / "selected_oof_policy_summary.csv"
    decision_path = output_dir / "go_pivot_decision.json"
    model_path = output_dir / "hierarchical_controller_models.joblib"
    report_path = output_dir / "development_report.md"
    manifest_path = output_dir / "feasibility_manifest.json"
    _write_csv(oof_path, oof_rows)
    _write_csv(
        fold_path,
        [
            {"family": family, **row}
            for family, audit in (
                ("depth", depth_fold_audit),
                ("breadth", breadth_fold_audit),
            )
            for row in audit
        ],
    )
    _write_csv(classification_path, classification_rows)
    _write_csv(sweep_path, candidates)
    _write_csv(trace_path, joint_traces + breadth_traces)
    _write_csv(comparator_path, comparators)
    _write_csv(summary_path, selected_summary)
    _write_json(decision_path, decision)
    joblib.dump(
        {
            "schema_version": CONTROLLER_SCHEMA_VERSION,
            "development_only": True,
            "lambda": lambda_value,
            "depth_pipeline": depth_model,
            "breadth_pipeline": breadth_model,
            "depth_feature_names": data_manifest["depth_feature_names"],
            "breadth_feature_names": data_manifest["breadth_feature_names"],
            "selected_oof_depth_threshold": selected["depth_threshold"],
            "selected_oof_breadth_threshold": selected["breadth_threshold"],
            "dataset_depths": DATASET_DEPTHS,
            "dataset_token_reference": DATASET_TOKEN_REFERENCE,
        },
        model_path,
    )

    summary_index = _summary_index(selected_summary)
    report_lines = [
        "# Hierarchical controller: Train-only OOF feasibility report",
        "",
        "## Evidence status",
        "",
        "This report uses only frozen Train sequential-label artifacts. Every "
        "reported learned-policy decision is out-of-fold with grouping by "
        "`dataset + problem_id`. The already-opened Test-100 artifacts were not "
        "loaded. Threshold exploration on these OOF predictions is development "
        "evidence and is not a confirmatory result.",
        "",
        "## Data and model",
        "",
        f"- Problems: {data_manifest['problem_count']} "
        f"({', '.join(data_manifest['datasets'])}).",
        f"- Marginal-utility lambda: {lambda_value:g}.",
        f"- Cross-validation: {folds}-fold StratifiedGroupKFold, seed {random_seed}.",
        f"- Learner: class-balanced regularized logistic regression, C={c_value:g}.",
        f"- Depth labels: {len(depth_rows)} rows, "
        f"{sum(_parse_int(row, 'label_escalate') for row in depth_rows)} positives.",
        f"- Breadth labels: {len(breadth_rows)} rows, "
        f"{sum(_parse_int(row, 'label_escalate') for row in breadth_rows)} positives.",
        "",
        "## Selected OOF threshold candidate",
        "",
        f"- Hybrid joint candidate: `{joint_candidate['candidate_id']}`.",
        f"- Joint decision: **{joint_decision['status']}**.",
        f"- Learned breadth/high-cap candidate: "
        f"`{breadth_candidate['candidate_id'] if breadth_candidate else 'none'}`.",
        f"- Breadth-only decision: **{breadth_decision['status']}**.",
        "",
        "| Dataset | Policy | Accuracy | Mean actual tokens | Mean normalized tokens |",
        "|---|---|---:|---:|---:|",
    ]
    for dataset in ("gsm8k", "math500", "pooled"):
        policy_ids = ["oof_hybrid_joint_controller"]
        if breadth_candidate is not None:
            policy_ids.append("oof_learned_breadth_high")
        policy_ids.extend(["agreement_high", "fixed_high_k4"])
        for policy_id in policy_ids:
            row = summary_index[(dataset, policy_id)]
            report_lines.append(
                f"| {dataset} | {policy_id} | {int(row['correct'])}/{int(row['problems'])} "
                f"({float(row['accuracy']):.1%}) | "
                f"{float(row['mean_actual_generated_tokens']):.2f} | "
                f"{float(row['mean_normalized_actual_tokens']):.3f} |"
            )
    report_lines.extend(
        [
            "",
            "## Go/pivot interpretation",
            "",
            f"Joint candidate: {joint_decision['rationale']}",
            "",
            f"Breadth-only candidate: {breadth_decision['rationale']}",
            "",
            str(joint_decision["next_gate"]),
            "",
            "No accuracy or token value in this report may replace the frozen "
            "Test-100 estimates in the thesis. A future controller claim requires "
            "a separately frozen Validation selection and a new unused reserve set.",
            "",
        ]
    )
    _write_text(report_path, "\n".join(report_lines))

    artifact_paths = {
        "oof_decisions": oof_path,
        "fold_audit": fold_path,
        "oof_classification_metrics": classification_path,
        "oof_threshold_sweep": sweep_path,
        "selected_oof_policy_traces": trace_path,
        "comparator_traces": comparator_path,
        "selected_oof_policy_summary": summary_path,
        "go_pivot_decision": decision_path,
        "controller_models": model_path,
        "development_report": report_path,
    }
    manifest = {
        "schema_version": CONTROLLER_SCHEMA_VERSION,
        "artifact_type": "hierarchical_controller_train_oof_feasibility",
        "development_only": True,
        "held_out_test_used": False,
        "lambda": lambda_value,
        "folds": folds,
        "group_key": "dataset + problem_id",
        "random_seed": random_seed,
        "C": c_value,
        "class_weight": "balanced",
        "threshold_grid": [float(value) for value in thresholds],
        "noninferiority_margin": noninferiority_margin,
        "token_saving_target": token_saving_target,
        "model_identity": data_manifest["model_identity"],
        "problem_count": data_manifest["problem_count"],
        "row_counts": {"depth": len(depth_rows), "breadth": len(breadth_rows)},
        "label_balance": {
            "depth_positive": sum(
                _parse_int(row, "label_escalate") for row in depth_rows
            ),
            "breadth_positive": sum(
                _parse_int(row, "label_escalate") for row in breadth_rows
            ),
        },
        "feature_contract": {
            "depth": data_manifest["depth_feature_names"],
            "breadth": data_manifest["breadth_feature_names"],
            "forbidden_prefixes": ["label_", "outcome_"],
        },
        "sources": data_manifest["sources"],
        "selected_oof_candidates": {
            "hybrid_joint": joint_candidate,
            "learned_breadth_high": breadth_candidate,
        },
        "go_pivot_decision": decision,
        "library_versions": {
            "python": sys.version.split()[0],
            "scikit_learn": sklearn.__version__,
            "scipy": scipy.__version__,
            "joblib": joblib.__version__,
        },
        "artifacts": {
            name: {"path": path.name, "sha256": file_sha256(path)}
            for name, path in artifact_paths.items()
        },
        "interpretation": (
            "Train-only grouped OOF feasibility; thresholds are exploratory and "
            "must be selected/frozen on untouched Validation before reserve evaluation."
        ),
    }
    _write_json(manifest_path, manifest)
    return manifest
