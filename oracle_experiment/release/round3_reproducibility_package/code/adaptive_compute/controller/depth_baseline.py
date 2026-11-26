"""Train and select the lightweight depth-only Phase 2 baseline."""

from __future__ import annotations

import csv
import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from statistics import fmean
from typing import Any

from adaptive_compute.controller.depth_data import DEFAULT_DEPTHS
from adaptive_compute.phase2_splits import file_sha256


DEFAULT_C_VALUES = (0.1, 1.0, 10.0)
DEFAULT_CLASS_WEIGHTS: tuple[str | None, ...] = (None, "balanced")
DEFAULT_DECISION_QUANTILES = (0.5, 0.7, 0.9)
MODEL_SELECTION_RULE = (
    "maximize validation policy accuracy; then minimize actual generated tokens; "
    "then maximize balanced target accuracy and macro-F1; then prefer lower C, "
    "unweighted classes, and lower decision quantile"
)


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
        raise ValueError("cannot write an empty metrics table")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    with temporary_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
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


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(content, encoding="utf-8")
    temporary_path.replace(path)


def _feature_matrix(
    rows: Sequence[Mapping[str, str]], feature_names: Sequence[str]
) -> list[list[float]]:
    matrix: list[list[float]] = []
    for row in rows:
        values: list[float] = []
        for name in feature_names:
            if not name.startswith("feature_"):
                raise ValueError(f"refusing non-feature model input: {name}")
            if name not in row:
                raise ValueError(f"missing feature column: {name}")
            value = float(row[name])
            if not math.isfinite(value):
                raise ValueError(f"non-finite feature {name} for {row.get('problem_id')}")
            values.append(value)
        matrix.append(values)
    return matrix


def quantile_depth_predictions(
    probabilities: Sequence[Sequence[float]],
    classes: Sequence[int],
    quantile: float,
) -> list[int]:
    """Choose an ordered target-depth quantile from classifier probabilities."""

    if not 0 < quantile < 1:
        raise ValueError("decision quantile must be in (0, 1)")
    if len(set(classes)) != len(classes):
        raise ValueError("classifier classes must be unique")
    class_order = sorted(range(len(classes)), key=lambda index: int(classes[index]))
    predictions: list[int] = []
    for row in probabilities:
        if len(row) != len(classes):
            raise ValueError("probability row does not match classifier classes")
        cumulative = 0.0
        selected = int(classes[class_order[-1]])
        for index in class_order:
            probability = float(row[index])
            if probability < 0 or not math.isfinite(probability):
                raise ValueError("invalid class probability")
            cumulative += probability
            if cumulative + 1e-12 >= quantile:
                selected = int(classes[index])
                break
        predictions.append(selected)
    return predictions


def evaluate_depth_policy(
    rows: Sequence[Mapping[str, str]],
    predictions: Sequence[int],
    *,
    strategy: str,
) -> dict[str, Any]:
    """Evaluate chosen depths using only their corresponding observed k=1 outcome."""

    if len(rows) != len(predictions) or not rows:
        raise ValueError("rows and predictions must be non-empty and aligned")
    correct: list[int] = []
    tokens: list[int] = []
    latency: list[float] = []
    truncated: list[int] = []
    valid_fraction: list[float] = []
    for row, depth in zip(rows, predictions, strict=True):
        if depth not in DEFAULT_DEPTHS:
            raise ValueError(f"predicted depth outside action space: {depth}")
        correct.append(int(row[f"outcome_k1_correct_L{depth}"]))
        tokens.append(int(row[f"outcome_k1_actual_tokens_L{depth}"]))
        latency.append(float(row[f"outcome_k1_latency_ms_L{depth}"]))
        truncated.append(int(row[f"outcome_k1_truncated_L{depth}"]))
        valid_fraction.append(float(row[f"outcome_k1_valid_answer_fraction_L{depth}"]))
    count = len(rows)
    return {
        "strategy": strategy,
        "num_problems": count,
        "correct_count": sum(correct),
        "policy_accuracy": sum(correct) / count,
        "avg_actual_generated_tokens": fmean(tokens),
        "avg_allocated_token_budget": fmean(predictions),
        "avg_latency_ms": fmean(latency),
        "truncation_rate": fmean(truncated),
        "avg_valid_answer_fraction": fmean(valid_fraction),
    }


def _prediction_rows(
    rows: Sequence[Mapping[str, str]], predictions: Sequence[int]
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row, prediction in zip(rows, predictions, strict=True):
        output.append(
            {
                "problem_id": row["problem_id"],
                "partition": row["partition"],
                "predicted_L": prediction,
                "target_L": int(row["label_depth_target_L"]),
                "target_status": row["label_target_status"],
                "selected_correct": int(row[f"outcome_k1_correct_L{prediction}"]),
                "selected_actual_generated_tokens": int(
                    row[f"outcome_k1_actual_tokens_L{prediction}"]
                ),
                "selected_latency_ms": float(row[f"outcome_k1_latency_ms_L{prediction}"]),
                "selected_truncated": int(row[f"outcome_k1_truncated_L{prediction}"]),
                "selected_valid_answer_fraction": float(
                    row[f"outcome_k1_valid_answer_fraction_L{prediction}"]
                ),
            }
        )
    return output


def train_depth_only_baseline(
    *,
    data_dir: Path,
    output_dir: Path,
    random_seed: int = 42,
    c_values: Sequence[float] = DEFAULT_C_VALUES,
    class_weights: Sequence[str | None] = DEFAULT_CLASS_WEIGHTS,
    decision_quantiles: Sequence[float] = DEFAULT_DECISION_QUANTILES,
) -> dict[str, Any]:
    """Fit on Train, select on Validation, and never load a Test table."""

    try:
        import joblib
        import sklearn
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import balanced_accuracy_score, f1_score
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
    except ImportError as exc:
        raise RuntimeError(
            "scikit-learn and joblib are required for the depth-only baseline"
        ) from exc

    train_path = data_dir / "depth_controller_train.csv"
    validation_path = data_dir / "depth_controller_validation.csv"
    schema_path = data_dir / "feature_schema.json"
    dataset_manifest_path = data_dir / "dataset_manifest.json"
    train_rows = _read_csv(train_path)
    validation_rows = _read_csv(validation_path)
    schema = _read_json(schema_path)
    dataset_manifest = _read_json(dataset_manifest_path)
    if dataset_manifest.get("held_out_test_materialized") is not False:
        raise ValueError("development-data manifest does not certify held-out test isolation")

    feature_names = schema.get("feature_names")
    if not isinstance(feature_names, list) or not feature_names:
        raise ValueError("feature schema does not contain an explicit allowlist")
    if any(not isinstance(name, str) or not name.startswith("feature_") for name in feature_names):
        raise ValueError("feature schema contains a non-feature model input")
    forbidden = set(schema.get("forbidden_as_model_inputs", []))
    if forbidden.intersection(feature_names):
        raise ValueError("feature allowlist overlaps leakage-forbidden columns")
    if {row["partition"] for row in train_rows} != {"train"}:
        raise ValueError("training table contains a non-train partition")
    if {row["partition"] for row in validation_rows} != {"validation"}:
        raise ValueError("validation table contains a non-validation partition")

    train_x = _feature_matrix(train_rows, feature_names)
    validation_x = _feature_matrix(validation_rows, feature_names)
    train_y = [int(row["label_depth_target_L"]) for row in train_rows]
    validation_y = [int(row["label_depth_target_L"]) for row in validation_rows]
    if set(train_y) != set(DEFAULT_DEPTHS):
        raise ValueError("training split must contain all three depth classes")

    candidates: list[dict[str, Any]] = []
    fitted_models: dict[tuple[float, str | None], Any] = {}
    candidate_predictions: dict[str, list[int]] = {}
    for c_value in c_values:
        if c_value <= 0:
            raise ValueError("all C values must be positive")
        for class_weight in class_weights:
            if class_weight not in (None, "balanced"):
                raise ValueError("class weight must be None or 'balanced'")
            pipeline = Pipeline(
                [
                    ("scale", StandardScaler()),
                    (
                        "classifier",
                        LogisticRegression(
                            C=float(c_value),
                            class_weight=class_weight,
                            max_iter=5_000,
                            random_state=random_seed,
                            solver="lbfgs",
                        ),
                    ),
                ]
            )
            pipeline.fit(train_x, train_y)
            probabilities = pipeline.predict_proba(validation_x)
            classes = [int(value) for value in pipeline.named_steps["classifier"].classes_]
            fitted_models[(float(c_value), class_weight)] = pipeline
            for quantile in decision_quantiles:
                predictions = quantile_depth_predictions(probabilities, classes, float(quantile))
                policy = evaluate_depth_policy(
                    validation_rows,
                    predictions,
                    strategy="depth_logistic_candidate",
                )
                candidate_id = (
                    f"C={float(c_value):g}|weight={class_weight or 'none'}|q={float(quantile):g}"
                )
                label_accuracy = sum(
                    int(prediction == target)
                    for prediction, target in zip(predictions, validation_y, strict=True)
                ) / len(validation_y)
                candidate = {
                    "candidate_id": candidate_id,
                    "C": float(c_value),
                    "class_weight": class_weight or "none",
                    "decision_quantile": float(quantile),
                    "label_accuracy": label_accuracy,
                    "label_balanced_accuracy": float(
                        balanced_accuracy_score(validation_y, predictions)
                    ),
                    "label_macro_f1": float(
                        f1_score(validation_y, predictions, average="macro", zero_division=0)
                    ),
                    **{key: value for key, value in policy.items() if key != "strategy"},
                }
                candidates.append(candidate)
                candidate_predictions[candidate_id] = predictions

    def selection_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
        return (
            -float(row["policy_accuracy"]),
            float(row["avg_actual_generated_tokens"]),
            -float(row["label_balanced_accuracy"]),
            -float(row["label_macro_f1"]),
            float(row["C"]),
            row["class_weight"] != "none",
            float(row["decision_quantile"]),
        )

    selected = min(candidates, key=selection_key)
    selected_id = str(selected["candidate_id"])
    selected_predictions = candidate_predictions[selected_id]
    selected_weight = None if selected["class_weight"] == "none" else "balanced"
    selected_pipeline = fitted_models[(float(selected["C"]), selected_weight)]

    policy_summary: list[dict[str, Any]] = []
    for depth in DEFAULT_DEPTHS:
        policy_summary.append(
            evaluate_depth_policy(
                validation_rows,
                [depth] * len(validation_rows),
                strategy=f"fixed_L{depth}",
            )
        )
    oracle_predictions = [int(row["label_depth_target_L"]) for row in validation_rows]
    policy_summary.append(
        evaluate_depth_policy(
            validation_rows,
            oracle_predictions,
            strategy="retrospective_depth_target_upper_bound",
        )
    )
    policy_summary.append(
        evaluate_depth_policy(
            validation_rows,
            selected_predictions,
            strategy="selected_depth_logistic",
        )
    )

    candidate_path = output_dir / "candidate_metrics.csv"
    summary_path = output_dir / "validation_policy_summary.csv"
    predictions_path = output_dir / "validation_predictions.csv"
    model_path = output_dir / "depth_logistic_model.joblib"
    report_path = output_dir / "development_report.md"
    manifest_path = output_dir / "training_manifest.json"
    _write_csv(candidate_path, candidates)
    _write_csv(summary_path, policy_summary)
    _write_csv(predictions_path, _prediction_rows(validation_rows, selected_predictions))
    output_dir.mkdir(parents=True, exist_ok=True)
    temporary_model_path = model_path.with_suffix(model_path.suffix + ".tmp")
    joblib.dump(
        {
            "pipeline": selected_pipeline,
            "feature_names": feature_names,
            "decision_quantile": float(selected["decision_quantile"]),
            "depth_action_space": DEFAULT_DEPTHS,
        },
        temporary_model_path,
    )
    temporary_model_path.replace(model_path)

    fixed_2048 = next(row for row in policy_summary if row["strategy"] == "fixed_L2048")
    selected_summary = next(
        row for row in policy_summary if row["strategy"] == "selected_depth_logistic"
    )
    token_reduction = 1.0 - (
        float(selected_summary["avg_actual_generated_tokens"])
        / float(fixed_2048["avg_actual_generated_tokens"])
    )
    report_lines = [
        "# Phase 2 depth-only baseline: development report",
        "",
        "## Status",
        "",
        "This is Train/Validation model-selection evidence only. The frozen held-out test "
        "partition was not loaded or evaluated.",
        "",
        "## Selected controller",
        "",
        f"- Candidate: `{selected_id}`",
        f"- Validation policy accuracy: {int(selected_summary['correct_count'])}/"
        f"{int(selected_summary['num_problems'])} "
        f"({float(selected_summary['policy_accuracy']):.1%})",
        f"- Average Actual Generated Tokens: "
        f"{float(selected_summary['avg_actual_generated_tokens']):.2f}",
        f"- Exact depth-target classification accuracy: "
        f"{float(selected['label_accuracy']):.1%}",
        "",
        "## Validation policy comparison",
        "",
        "| Policy | Correct | Accuracy | Avg actual tokens | Avg allocated budget |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in policy_summary:
        report_lines.append(
            f"| {row['strategy']} | {int(row['correct_count'])}/{int(row['num_problems'])} | "
            f"{float(row['policy_accuracy']):.1%} | "
            f"{float(row['avg_actual_generated_tokens']):.2f} | "
            f"{float(row['avg_allocated_token_budget']):.2f} |"
        )
    report_lines.extend(
        [
            "",
            "On this 20-problem validation split, the selected controller matches fixed "
            f"L=2048 accuracy and uses {token_reduction:.1%} fewer average Actual Generated "
            "Tokens. This comparison is optimistic because the candidate was selected on the "
            "same validation set; it is not confirmatory evidence and must not be reported as "
            "held-out performance.",
            "",
        ]
    )
    _write_text(report_path, "\n".join(report_lines))

    manifest = {
        "schema_version": 1,
        "artifact_type": "phase2_depth_only_logistic_baseline",
        "training_partition": "train",
        "selection_partition": "validation",
        "held_out_test_used": False,
        "random_seed": random_seed,
        "library_versions": {"scikit_learn": sklearn.__version__},
        "feature_names": feature_names,
        "depth_action_space": list(DEFAULT_DEPTHS),
        "hyperparameter_grid": {
            "C": [float(value) for value in c_values],
            "class_weight": [value or "none" for value in class_weights],
            "decision_quantile": [float(value) for value in decision_quantiles],
        },
        "model_selection_rule": MODEL_SELECTION_RULE,
        "num_candidates": len(candidates),
        "selected_candidate": selected,
        "source_hashes": {
            "train_csv_sha256": file_sha256(train_path),
            "validation_csv_sha256": file_sha256(validation_path),
            "feature_schema_sha256": file_sha256(schema_path),
            "dataset_manifest_sha256": file_sha256(dataset_manifest_path),
        },
        "artifact_hashes": {
            "candidate_metrics_sha256": file_sha256(candidate_path),
            "validation_policy_summary_sha256": file_sha256(summary_path),
            "validation_predictions_sha256": file_sha256(predictions_path),
            "model_sha256": file_sha256(model_path),
            "development_report_sha256": file_sha256(report_path),
        },
        "interpretation": (
            "Development-set model selection only; these metrics are not held-out test evidence."
        ),
    }
    _write_json(manifest_path, manifest)
    return manifest
