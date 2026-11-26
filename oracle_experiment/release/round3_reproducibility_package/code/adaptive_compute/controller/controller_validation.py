"""Freeze and evaluate the learned-breadth controller on Validation only."""

from __future__ import annotations

import csv
import json
import shutil
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from adaptive_compute.analysis.statistics import exact_mcnemar_p
from adaptive_compute.controller.hierarchical_controller import (
    DEFAULT_NONINFERIORITY_MARGIN,
    DEFAULT_TOKEN_SAVING_TARGET,
    SequentialLabelSource,
    comparator_traces,
    fitted_probabilities,
    load_pooled_validation_labels,
    replay_oof_controller,
    summarize_policy_traces,
)
from adaptive_compute.phase2_splits import file_sha256


VALIDATION_FREEZE_SCHEMA_VERSION = 1
VALIDATION_POLICY_ID = "learned_breadth_high_v1"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read JSON artifact {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(dict(payload), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty Validation table: {path.name}")
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


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def _copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    shutil.copyfile(source, temporary)
    temporary.replace(target)


def _split_validation_identity(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    sizes = payload.get("partition_sizes", {})
    hashes = payload.get("partition_problem_ids_sha256", {})
    if int(sizes.get("validation", 0)) <= 0 or not hashes.get("validation"):
        raise ValueError(f"split manifest has no frozen Validation identity: {path}")
    return {
        "path": str(path),
        "sha256": file_sha256(path),
        "problem_count": int(sizes["validation"]),
        "problem_ids_sha256": hashes["validation"],
    }


def build_controller_validation_freeze(
    *,
    feasibility_dir: Path,
    gsm8k_split_manifest: Path,
    math500_split_manifest: Path,
    output_dir: Path,
    repository_root: Path,
) -> dict[str, Any]:
    """Freeze the OOF-selected learned-breadth candidate before Validation."""

    if output_dir.exists():
        raise FileExistsError(f"controller Validation freeze already exists: {output_dir}")
    feasibility_path = feasibility_dir / "feasibility_manifest.json"
    feasibility = _read_json(feasibility_path)
    if feasibility.get("artifact_type") != "hierarchical_controller_train_oof_feasibility":
        raise ValueError("unexpected controller feasibility artifact type")
    if feasibility.get("held_out_test_used") is not False:
        raise ValueError("controller feasibility does not certify Test isolation")
    breadth_decision = feasibility.get("go_pivot_decision", {}).get(
        "breadth_only_candidate", {}
    )
    if breadth_decision.get("status") != "GO_BREADTH_ONLY_TO_FROZEN_VALIDATION":
        raise ValueError("learned breadth candidate did not pass the OOF gate")
    candidate = feasibility.get("selected_oof_candidates", {}).get(
        "learned_breadth_high"
    )
    if not isinstance(candidate, dict):
        raise ValueError("feasibility manifest has no learned breadth candidate")
    if float(candidate.get("depth_threshold", -1)) != 0.0:
        raise ValueError("Validation candidate must keep the high token cap fixed")
    if bool(candidate.get("adaptive_depth_both_datasets")):
        raise ValueError("breadth-only candidate unexpectedly adapts depth")
    model_entry = feasibility.get("artifacts", {}).get("controller_models", {})
    model_path = feasibility_dir / str(model_entry.get("path", ""))
    if not model_path.is_file() or file_sha256(model_path) != model_entry.get("sha256"):
        raise ValueError("controller model artifact is missing or has a hash mismatch")

    split_identity = {
        "gsm8k": _split_validation_identity(gsm8k_split_manifest),
        "math500": _split_validation_identity(math500_split_manifest),
    }
    model_target = output_dir / "controller_models.joblib"
    _copy(model_path, model_target)
    software_paths = {
        "hierarchical_controller.py": repository_root
        / "adaptive_compute"
        / "controller"
        / "hierarchical_controller.py",
        "controller_validation.py": repository_root
        / "adaptive_compute"
        / "controller"
        / "controller_validation.py",
    }
    manifest: dict[str, Any] = {
        "schema_version": VALIDATION_FREEZE_SCHEMA_VERSION,
        "artifact_type": "learned_breadth_controller_validation_freeze",
        "status": "frozen",
        "freeze_date": "2026-11-18",
        "policy_id": VALIDATION_POLICY_ID,
        "policy_role": "learned selective breadth at dataset-specific high L",
        "evidence_status": "Train-OOF selected; Validation not yet replayed",
        "model_identity": feasibility["model_identity"],
        "lambda": float(feasibility["lambda"]),
        "candidate": candidate,
        "decision_rules": {
            "depth": "always use dataset-specific high L",
            "k1_safety": "invalid or truncated first answer must continue to k2",
            "k1_learned_stop": (
                "stop only for valid non-truncated first answer when predicted "
                "marginal-utility probability is below frozen threshold"
            ),
            "k2_safety": "two matching valid answers stop at k2",
            "k2_learned_stop": (
                "otherwise stop at k2 when predicted marginal-utility probability "
                "is below frozen threshold; else acquire k4"
            ),
            "aggregation": "valid-only majority vote; lowest sample index tie break",
            "cost": "all actual generated tokens from every paid sample",
        },
        "validation_access": {
            "authorized": True,
            "execution_rule": "one-shot replay; no Validation-dependent retuning",
            "splits": split_identity,
        },
        "reserve_access": {
            "authorized": False,
            "condition": "requires passing the frozen Validation gate",
        },
        "gate": {
            "accuracy_margin": -DEFAULT_NONINFERIORITY_MARGIN,
            "minimum_token_saving": DEFAULT_TOKEN_SAVING_TARGET,
            "comparator": "agreement_high",
            "must_pass_each_dataset": True,
        },
        "source_hashes": {
            "feasibility_manifest_sha256": file_sha256(feasibility_path),
            "source_controller_models_sha256": file_sha256(model_path),
        },
        "software_hashes": {
            name: file_sha256(path) for name, path in software_paths.items()
        },
        "frozen_artifacts": {
            "controller_models": model_target.name,
            "controller_models_sha256": file_sha256(model_target),
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "controller_validation_freeze.json"
    _write_json(manifest_path, manifest)
    (output_dir / "controller_validation_freeze.sha256").write_text(
        file_sha256(manifest_path) + "\n", encoding="utf-8"
    )
    return {**manifest, "freeze_manifest_sha256": file_sha256(manifest_path)}


def validation_gate(
    comparisons: Sequence[Mapping[str, Any]],
    *,
    accuracy_margin: float = -DEFAULT_NONINFERIORITY_MARGIN,
    token_saving_target: float = DEFAULT_TOKEN_SAVING_TARGET,
) -> dict[str, Any]:
    """Apply the frozen per-dataset Validation gate."""

    required = {"gsm8k", "math500"}
    by_dataset = {str(row["dataset"]): row for row in comparisons}
    if set(by_dataset) != required:
        raise ValueError("Validation gate requires exactly GSM8K and MATH-500")
    checks: dict[str, Any] = {}
    for dataset in sorted(required):
        row = by_dataset[dataset]
        accuracy_pass = float(row["accuracy_gap"]) >= accuracy_margin
        token_pass = float(row["token_saving"]) >= token_saving_target
        checks[dataset] = {
            "accuracy_pass": accuracy_pass,
            "token_pass": token_pass,
            "pass": accuracy_pass and token_pass,
        }
    passed = all(row["pass"] for row in checks.values())
    return {
        "status": (
            "GO_CREATE_RESERVE_PROTOCOL"
            if passed
            else "PIVOT_NO_RESERVE_FOR_THIS_CONTROLLER"
        ),
        "passed": passed,
        "accuracy_margin": accuracy_margin,
        "token_saving_target": token_saving_target,
        "checks": checks,
        "rule": "both accuracy and token gates must pass separately on both datasets",
    }


def _comparison_rows(
    candidate_traces: Sequence[Mapping[str, Any]],
    comparator_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    candidate = {
        (str(row["dataset"]), str(row["problem_id"])): row
        for row in candidate_traces
    }
    comparator = {
        (str(row["dataset"]), str(row["problem_id"])): row
        for row in comparator_rows
        if row["policy_id"] == "agreement_high"
    }
    if set(candidate) != set(comparator):
        raise ValueError("candidate and agreement comparator traces are not paired")
    output: list[dict[str, Any]] = []
    for dataset in ("gsm8k", "math500"):
        keys = sorted(key for key in candidate if key[0] == dataset)
        candidate_correct = sum(int(candidate[key]["correct"]) for key in keys)
        comparator_correct = sum(int(comparator[key]["correct"]) for key in keys)
        candidate_tokens = sum(
            float(candidate[key]["actual_generated_tokens"]) for key in keys
        ) / len(keys)
        comparator_tokens = sum(
            float(comparator[key]["actual_generated_tokens"]) for key in keys
        ) / len(keys)
        candidate_only = sum(
            int(candidate[key]["correct"]) == 1
            and int(comparator[key]["correct"]) == 0
            for key in keys
        )
        comparator_only = sum(
            int(candidate[key]["correct"]) == 0
            and int(comparator[key]["correct"]) == 1
            for key in keys
        )
        output.append(
            {
                "dataset": dataset,
                "problems": len(keys),
                "candidate_correct": candidate_correct,
                "candidate_accuracy": candidate_correct / len(keys),
                "candidate_mean_tokens": candidate_tokens,
                "agreement_correct": comparator_correct,
                "agreement_accuracy": comparator_correct / len(keys),
                "agreement_mean_tokens": comparator_tokens,
                "accuracy_gap": (candidate_correct - comparator_correct) / len(keys),
                "token_saving": 1.0 - candidate_tokens / comparator_tokens,
                "candidate_only_correct": candidate_only,
                "agreement_only_correct": comparator_only,
                "mcnemar_exact_p": exact_mcnemar_p(
                    candidate_only, comparator_only
                ),
            }
        )
    return output


def evaluate_frozen_controller_validation(
    *,
    freeze_dir: Path,
    validation_sources: Sequence[SequentialLabelSource],
    output_dir: Path,
) -> dict[str, Any]:
    """Replay the frozen learned-breadth controller once on Validation."""

    try:
        import joblib
        import scipy
        import sklearn
    except ImportError as exc:
        raise RuntimeError("controller Validation requires joblib and scikit-learn") from exc
    if output_dir.exists():
        raise FileExistsError(f"controller Validation output already exists: {output_dir}")
    freeze_path = freeze_dir / "controller_validation_freeze.json"
    freeze = _read_json(freeze_path)
    if freeze.get("status") != "frozen" or freeze.get("artifact_type") != (
        "learned_breadth_controller_validation_freeze"
    ):
        raise ValueError("controller Validation freeze is invalid")
    model_path = freeze_dir / freeze["frozen_artifacts"]["controller_models"]
    if file_sha256(model_path) != freeze["frozen_artifacts"][
        "controller_models_sha256"
    ]:
        raise ValueError("frozen controller model hash mismatch")
    bundle = joblib.load(model_path)
    depth_rows, breadth_rows, validation_data = load_pooled_validation_labels(
        validation_sources, lambda_value=float(freeze["lambda"])
    )
    if validation_data["model_identity"] != freeze["model_identity"]:
        raise ValueError("Validation labels use a different model identity")
    for source in validation_data["sources"]:
        frozen_split = freeze["validation_access"]["splits"][source["dataset"]]
        if source["source_split_manifest_sha256"] != frozen_split["sha256"]:
            raise ValueError(f"Validation split hash mismatch for {source['dataset']}")
        if source["problem_count"] != frozen_split["problem_count"]:
            raise ValueError(f"Validation count mismatch for {source['dataset']}")
    if bundle["breadth_feature_names"] != validation_data["breadth_feature_names"]:
        raise ValueError("Validation breadth feature contract differs from Train")
    if bundle["depth_feature_names"] != validation_data["depth_feature_names"]:
        raise ValueError("Validation depth feature contract differs from Train")
    depth_probabilities = fitted_probabilities(
        depth_rows,
        feature_names=bundle["depth_feature_names"],
        pipeline=bundle["depth_pipeline"],
    )
    breadth_probabilities = fitted_probabilities(
        breadth_rows,
        feature_names=bundle["breadth_feature_names"],
        pipeline=bundle["breadth_pipeline"],
    )
    candidate = freeze["candidate"]
    candidate_traces = replay_oof_controller(
        depth_rows,
        depth_probabilities,
        breadth_rows,
        breadth_probabilities,
        depth_threshold=float(candidate["depth_threshold"]),
        breadth_threshold=float(candidate["breadth_threshold"]),
        policy_id=freeze["policy_id"],
        partition="validation",
    )
    comparators = comparator_traces(breadth_rows, partition="validation")
    summary = summarize_policy_traces(candidate_traces + comparators)
    comparisons = _comparison_rows(candidate_traces, comparators)
    gate = validation_gate(
        comparisons,
        accuracy_margin=float(freeze["gate"]["accuracy_margin"]),
        token_saving_target=float(freeze["gate"]["minimum_token_saving"]),
    )

    output_dir.mkdir(parents=True)
    trace_path = output_dir / "validation_controller_traces.csv"
    comparator_path = output_dir / "validation_comparator_traces.csv"
    summary_path = output_dir / "validation_policy_summary.csv"
    comparison_path = output_dir / "validation_paired_comparison.csv"
    decision_path = output_dir / "validation_gate_decision.json"
    report_path = output_dir / "validation_report.md"
    manifest_path = output_dir / "validation_manifest.json"
    _write_csv(trace_path, candidate_traces)
    _write_csv(comparator_path, comparators)
    _write_csv(summary_path, summary)
    _write_csv(comparison_path, comparisons)
    _write_json(decision_path, gate)
    report_lines = [
        "# Frozen learned-breadth controller: Validation-20 report",
        "",
        "## Evidence status",
        "",
        "One-shot replay of the pre-Validation frozen controller on the existing "
        "GSM8K Validation-20 and MATH-500 Validation-20 shared pools. Test-100 "
        "artifacts were not loaded. This is model-selection evidence, not a final "
        "held-out controller result.",
        "",
        f"Decision: **{gate['status']}**.",
        "",
        "| Dataset | Controller | Agreement-high | Accuracy gap | Token saving | McNemar p |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in comparisons:
        report_lines.append(
            f"| {row['dataset']} | {row['candidate_correct']}/{row['problems']}, "
            f"{row['candidate_mean_tokens']:.2f} tok | "
            f"{row['agreement_correct']}/{row['problems']}, "
            f"{row['agreement_mean_tokens']:.2f} tok | "
            f"{row['accuracy_gap']:+.1%} | {row['token_saving']:.1%} | "
            f"{row['mcnemar_exact_p']:.4g} |"
        )
    report_lines.extend(
        [
            "",
            "The gate requires accuracy loss no worse than 2 percentage points "
            "and at least 10% token saving separately on both datasets. No "
            "threshold may be changed after this report.",
            "",
        ]
    )
    _write_text(report_path, "\n".join(report_lines))
    artifacts = {
        "controller_traces": trace_path,
        "comparator_traces": comparator_path,
        "policy_summary": summary_path,
        "paired_comparison": comparison_path,
        "gate_decision": decision_path,
        "validation_report": report_path,
    }
    manifest = {
        "schema_version": 1,
        "artifact_type": "learned_breadth_controller_validation_replay",
        "development_only": True,
        "held_out_test_used": False,
        "one_shot_frozen_replay": True,
        "policy_id": freeze["policy_id"],
        "candidate": candidate,
        "problem_count": validation_data["problem_count"],
        "source_validation_labels": validation_data["sources"],
        "freeze_manifest_sha256": file_sha256(freeze_path),
        "gate_decision": gate,
        "library_versions": {
            "python": sys.version.split()[0],
            "scikit_learn": sklearn.__version__,
            "scipy": scipy.__version__,
            "joblib": joblib.__version__,
        },
        "artifacts": {
            name: {"path": path.name, "sha256": file_sha256(path)}
            for name, path in artifacts.items()
        },
        "interpretation": (
            "Frozen Validation selection evidence only; reserve evaluation remains "
            "unauthorized unless the recorded gate passes."
        ),
    }
    _write_json(manifest_path, manifest)
    return manifest

