"""Create an immutable, auditable policy bundle before held-out Test access."""

from __future__ import annotations

import csv
import json
import shutil
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from adaptive_compute.controller.policy_replay import (
    DEPTH_ONLY_POLICY_ID,
    HEURISTIC_POLICY_ID,
)
from adaptive_compute.math500_splits import read_math500_split_manifest
from adaptive_compute.phase2_splits import file_sha256, read_phase2_split_manifest


FREEZE_SCHEMA_VERSION = 1
SELECTED_POLICY_ID = "breadth_only_agreement_L1024_v1"
MATH500_SELECTED_POLICY_ID = "fixed_k2_L4096"
SELECTION_RULE = (
    "among frozen non-fixed deployable policies, maximize Validation accuracy; "
    "then minimize Validation mean actual generated tokens; then lexical policy ID"
)
MATH500_SELECTION_RULE = (
    "post-Validation registered pivot: among all frozen fixed and adaptive "
    "policies, maximize Validation accuracy; then minimize Validation mean "
    "actual generated tokens; then lexical policy ID"
)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"CSV table is empty: {path}")
    return rows


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(dict(payload), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    shutil.copyfile(source, temporary)
    temporary.replace(target)


def select_validation_candidate(
    summary_rows: Sequence[Mapping[str, Any]],
    *,
    include_fixed: bool = False,
) -> tuple[dict[str, Any], list[str]]:
    """Apply the frozen lexicographic Validation selection rule."""

    deployable = [
        row
        for row in summary_rows
        if include_fixed or row.get("policy_type") != "fixed_profile"
    ]
    if not deployable:
        policy_kind = "policies" if include_fixed else "adaptive policies"
        raise ValueError(f"Validation summary has no deployable {policy_kind}")
    max_accuracy = max(float(row["accuracy"]) for row in deployable)
    accuracy_ties = [
        row for row in deployable if float(row["accuracy"]) == max_accuracy
    ]
    min_tokens = min(float(row["avg_actual_generated_tokens"]) for row in accuracy_ties)
    cost_ties = [
        row
        for row in accuracy_ties
        if float(row["avg_actual_generated_tokens"]) == min_tokens
    ]
    selected = min(cost_ties, key=lambda row: str(row["policy_id"]))
    return dict(selected), sorted(str(row["policy_id"]) for row in accuracy_ties)


def _verify_replay_pair(
    *,
    train_dir: Path,
    validation_dir: Path,
    split_manifest_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], Path, Path]:
    train_manifest_path = train_dir / "replay_manifest.json"
    validation_manifest_path = validation_dir / "replay_manifest.json"
    train = _read_json(train_manifest_path)
    validation = _read_json(validation_manifest_path)
    if train.get("schema_version") != 3 or validation.get("schema_version") != 3:
        raise ValueError("policy freeze requires replay schema v3")
    if train.get("partition") != "train" or validation.get("partition") != "validation":
        raise ValueError("replay pair must contain Train and Validation respectively")
    if train.get("held_out_test_replayed") is not False or validation.get(
        "held_out_test_replayed"
    ) is not False:
        raise ValueError("replay artifacts do not certify Test isolation")
    if train.get("fixed_endpoint_reconstruction") != "exact" or validation.get(
        "fixed_endpoint_reconstruction"
    ) != "exact":
        raise ValueError("fixed endpoints were not reconstructed exactly")
    provenance_fields = (
        "source_model",
        "source_model_revision",
        "source_prompt_template_name",
        "source_answer_parser_name",
    )
    for field in provenance_fields:
        if train.get(field) != validation.get(field):
            raise ValueError(f"Train/Validation provenance mismatch: {field}")
    split_hash = file_sha256(split_manifest_path)
    if train["source_hashes"].get("split_manifest_sha256") != split_hash or validation[
        "source_hashes"
    ].get("split_manifest_sha256") != split_hash:
        raise ValueError("replay artifact split hash mismatch")

    train_policy_path = train_dir / train["artifacts"]["policy_config"]
    validation_policy_path = validation_dir / validation["artifacts"]["policy_config"]
    train_policy_hash = file_sha256(train_policy_path)
    if train["artifacts"].get("policy_config_sha256") != train_policy_hash:
        raise ValueError("Train policy config hash mismatch")
    if file_sha256(validation_policy_path) != train_policy_hash:
        raise ValueError("Validation policy config is not byte-identical to Train")
    if validation["source_hashes"].get("train_policy_config_sha256") != train_policy_hash:
        raise ValueError("Validation did not record the frozen Train policy hash")

    train_schema_path = train_dir / train["artifacts"]["trace_schema"]
    validation_schema_path = validation_dir / validation["artifacts"]["trace_schema"]
    if file_sha256(train_schema_path) != file_sha256(validation_schema_path):
        raise ValueError("Train/Validation trace schemas differ")
    return train, validation, train_policy_path, train_schema_path


def build_policy_freeze_bundle(
    *,
    train_replay_dir: Path,
    validation_replay_dir: Path,
    split_manifest_path: Path,
    output_dir: Path,
    repository_root: Path,
) -> dict[str, Any]:
    """Freeze the selected GSM8K candidate and all confirmatory comparators."""

    if output_dir.exists():
        raise FileExistsError(f"policy freeze output already exists: {output_dir}")
    train, validation, train_policy_path, train_schema_path = _verify_replay_pair(
        train_dir=train_replay_dir,
        validation_dir=validation_replay_dir,
        split_manifest_path=split_manifest_path,
    )
    split = read_phase2_split_manifest(split_manifest_path)
    validation_summary_path = validation_replay_dir / validation["artifacts"][
        "policy_summary"
    ]
    validation_comparison_path = validation_replay_dir / validation["artifacts"][
        "primary_heuristic_comparisons"
    ]
    validation_rows = _read_csv(validation_summary_path)
    selected, accuracy_ties = select_validation_candidate(validation_rows)
    if selected["policy_id"] != SELECTED_POLICY_ID:
        raise ValueError(
            "Validation selection no longer matches the pre-freeze decision: "
            f"expected {SELECTED_POLICY_ID}, found {selected['policy_id']}"
        )
    by_id = {row["policy_id"]: row for row in validation_rows}
    required_policy_ids = {
        SELECTED_POLICY_ID,
        HEURISTIC_POLICY_ID,
        DEPTH_ONLY_POLICY_ID,
        "breadth_only_agreement_L512_v1",
        "breadth_only_agreement_L2048_v1",
        *(f"fixed_k{k}_L{length}" for k in (1, 2, 4) for length in (512, 1024, 2048)),
    }
    missing = sorted(required_policy_ids - set(by_id))
    if missing:
        raise ValueError(f"freeze bundle is missing policies: {', '.join(missing)}")

    policy_target = output_dir / "policy_config.json"
    schema_target = output_dir / "trace_schema.json"
    summary_target = output_dir / "validation_policy_summary.csv"
    comparison_target = output_dir / "validation_primary_comparisons.csv"
    _copy(train_policy_path, policy_target)
    _copy(train_schema_path, schema_target)
    _copy(validation_summary_path, summary_target)
    _copy(validation_comparison_path, comparison_target)

    software_paths = {
        "policy_replay.py": repository_root
        / "adaptive_compute"
        / "controller"
        / "policy_replay.py",
        "aggregation.py": repository_root / "adaptive_compute" / "aggregation.py",
        "answer_parser.py": repository_root / "adaptive_compute" / "answer_parser.py",
        "prompts.py": repository_root / "adaptive_compute" / "prompts.py",
    }
    policy_config = _read_json(policy_target)
    manifest: dict[str, Any] = {
        "schema_version": FREEZE_SCHEMA_VERSION,
        "artifact_type": "gsm8k_phase2_policy_freeze",
        "status": "frozen",
        "freeze_date": "2026-11-12",
        "model": train["source_model"],
        "model_revision": train["source_model_revision"],
        "prompt_template_name": train["source_prompt_template_name"],
        "answer_parser_name": train["source_answer_parser_name"],
        "generation_seed": 42,
        "action_space": {"k": [1, 2, 4], "L": [512, 1024, 2048]},
        "selection_rule": SELECTION_RULE,
        "selected_policy_id": SELECTED_POLICY_ID,
        "selected_policy_type": selected["policy_type"],
        "selected_validation_metrics": {
            "num_problems": int(selected["num_problems"]),
            "correct_count": int(selected["correct_count"]),
            "accuracy": float(selected["accuracy"]),
            "avg_actual_generated_tokens": float(
                selected["avg_actual_generated_tokens"]
            ),
            "avg_latency_ms": float(selected["avg_latency_ms"]),
        },
        "max_accuracy_validation_ties": accuracy_ties,
        "joint_hypothesis_policy_id": HEURISTIC_POLICY_ID,
        "joint_go_status": "not_met_on_validation",
        "learned_joint_controller_status": "not_fitted_insufficient_positive_events",
        "confirmatory_policy_ids": sorted(required_policy_ids),
        "train_prompt_token_thresholds": {
            "low": float(policy_config["prompt_token_tertile_low"]),
            "high": float(policy_config["prompt_token_tertile_high"]),
            "method": policy_config["tertile_method"],
        },
        "test_access": {
            "gsm8k_test_problem_count": int(split["partition_sizes"]["test"]),
            "gsm8k_test_problem_ids_sha256": split[
                "partition_problem_ids_sha256"
            ]["test"],
            "outcomes_materialized_in_freeze_inputs": False,
            "authorized_after_freeze": True,
            "execution_rule": "one-time frozen evaluation; no Test-dependent retuning",
        },
        "scope_limitations": [
            "GSM8K confirmatory policy evaluation only",
            "MATH-500 controller confirmation is not complete",
            "no learned joint controller is claimed",
            "Validation selection uses n=20 and is optimistic",
        ],
        "source_hashes": {
            "split_manifest_sha256": file_sha256(split_manifest_path),
            "train_replay_manifest_sha256": file_sha256(
                train_replay_dir / "replay_manifest.json"
            ),
            "validation_replay_manifest_sha256": file_sha256(
                validation_replay_dir / "replay_manifest.json"
            ),
            "train_policy_config_sha256": file_sha256(train_policy_path),
            "train_trace_schema_sha256": file_sha256(train_schema_path),
        },
        "software_hashes": {
            name: file_sha256(path) for name, path in software_paths.items()
        },
        "frozen_artifacts": {
            "policy_config": policy_target.name,
            "policy_config_sha256": file_sha256(policy_target),
            "trace_schema": schema_target.name,
            "trace_schema_sha256": file_sha256(schema_target),
            "validation_policy_summary": summary_target.name,
            "validation_policy_summary_sha256": file_sha256(summary_target),
            "validation_primary_comparisons": comparison_target.name,
            "validation_primary_comparisons_sha256": file_sha256(comparison_target),
        },
    }
    manifest_path = output_dir / "policy_freeze.json"
    _write_json(manifest_path, manifest)
    checksum_path = output_dir / "policy_freeze.sha256"
    checksum_path.write_text(file_sha256(manifest_path) + "\n", encoding="utf-8")
    return {**manifest, "policy_freeze_sha256": file_sha256(manifest_path)}


def build_math500_policy_freeze_bundle(
    *,
    train_replay_dir: Path,
    validation_replay_dir: Path,
    split_manifest_path: Path,
    output_dir: Path,
    repository_root: Path,
) -> dict[str, Any]:
    """Freeze the post-Validation MATH-500 pivot before any Test access."""

    if output_dir.exists():
        raise FileExistsError(f"policy freeze output already exists: {output_dir}")
    train, validation, train_policy_path, train_schema_path = _verify_replay_pair(
        train_dir=train_replay_dir,
        validation_dir=validation_replay_dir,
        split_manifest_path=split_manifest_path,
    )
    if train.get("dataset") != "math500" or validation.get("dataset") != "math500":
        raise ValueError("MATH-500 freeze requires MATH-500 replay artifacts")
    split = read_math500_split_manifest(split_manifest_path)
    validation_summary_path = validation_replay_dir / validation["artifacts"][
        "policy_summary"
    ]
    validation_comparison_path = validation_replay_dir / validation["artifacts"][
        "primary_heuristic_comparisons"
    ]
    validation_rows = _read_csv(validation_summary_path)
    selected, accuracy_ties = select_validation_candidate(
        validation_rows, include_fixed=True
    )
    if selected["policy_id"] != MATH500_SELECTED_POLICY_ID:
        raise ValueError(
            "MATH-500 Validation pivot no longer matches the frozen decision: "
            f"expected {MATH500_SELECTED_POLICY_ID}, found {selected['policy_id']}"
        )
    required_policy_ids = {
        HEURISTIC_POLICY_ID,
        DEPTH_ONLY_POLICY_ID,
        *(f"breadth_only_agreement_L{length}_v1" for length in (1024, 2048, 4096)),
        *(
            f"fixed_k{k}_L{length}"
            for k in (1, 2, 4)
            for length in (1024, 2048, 4096)
        ),
    }
    by_id = {str(row["policy_id"]): row for row in validation_rows}
    missing = sorted(required_policy_ids - set(by_id))
    if missing:
        raise ValueError(f"MATH-500 freeze bundle is missing policies: {', '.join(missing)}")

    policy_target = output_dir / "policy_config.json"
    schema_target = output_dir / "trace_schema.json"
    summary_target = output_dir / "validation_policy_summary.csv"
    comparison_target = output_dir / "validation_primary_comparisons.csv"
    _copy(train_policy_path, policy_target)
    _copy(train_schema_path, schema_target)
    _copy(validation_summary_path, summary_target)
    _copy(validation_comparison_path, comparison_target)

    software_paths = {
        "policy_replay.py": repository_root
        / "adaptive_compute"
        / "controller"
        / "policy_replay.py",
        "aggregation.py": repository_root / "adaptive_compute" / "aggregation.py",
        "answer_parser.py": repository_root / "adaptive_compute" / "answer_parser.py",
        "prompts.py": repository_root / "adaptive_compute" / "prompts.py",
    }
    policy_config = _read_json(policy_target)
    if policy_config.get("dataset") != "math500":
        raise ValueError("frozen MATH-500 policy config has the wrong dataset")
    manifest: dict[str, Any] = {
        "schema_version": FREEZE_SCHEMA_VERSION,
        "artifact_type": "math500_phase2_policy_freeze",
        "status": "frozen",
        "freeze_date": "2026-11-14",
        "dataset": "math500",
        "model": train["source_model"],
        "model_revision": train["source_model_revision"],
        "prompt_template_name": train["source_prompt_template_name"],
        "answer_parser_name": train["source_answer_parser_name"],
        "generation_seed": 42,
        "action_space": {"k": [1, 2, 4], "L": [1024, 2048, 4096]},
        "selection_rule": MATH500_SELECTION_RULE,
        "selection_provenance": (
            "registered after frozen Validation showed every adaptive policy "
            "was point-Pareto-dominated; this is a transparent pivot, not a "
            "pre-Validation selection claim"
        ),
        "selected_policy_id": MATH500_SELECTED_POLICY_ID,
        "selected_policy_type": selected["policy_type"],
        "selected_validation_metrics": {
            "num_problems": int(selected["num_problems"]),
            "correct_count": int(selected["correct_count"]),
            "accuracy": float(selected["accuracy"]),
            "avg_actual_generated_tokens": float(
                selected["avg_actual_generated_tokens"]
            ),
            "avg_latency_ms": float(selected["avg_latency_ms"]),
        },
        "max_accuracy_validation_ties": accuracy_ties,
        "joint_hypothesis_policy_id": HEURISTIC_POLICY_ID,
        "joint_go_status": "not_met_on_validation",
        "cross_dataset_joint_status": "pivot_not_supported_consistently",
        "learned_joint_controller_status": "not_fitted_insufficient_positive_events",
        "confirmatory_policy_ids": sorted(required_policy_ids),
        "train_prompt_token_thresholds": {
            "low": float(policy_config["prompt_token_tertile_low"]),
            "high": float(policy_config["prompt_token_tertile_high"]),
            "method": policy_config["tertile_method"],
        },
        "test_access": {
            "dataset": "math500",
            "test_problem_count": int(split["partition_sizes"]["test"]),
            "test_problem_ids_sha256": split["partition_problem_ids_sha256"][
                "test"
            ],
            "outcomes_materialized_in_freeze_inputs": False,
            "authorized_after_freeze": True,
            "execution_rule": "one-time frozen evaluation; no Test-dependent retuning",
        },
        "scope_limitations": [
            "MATH-500 confirmatory policy evaluation only",
            "selected MATH policy is a fixed comparator after a transparent Validation pivot",
            "no learned joint controller is claimed",
            "Validation selection uses n=20 and is uncertain",
            "GSM8K retains its independently frozen dataset-specific policy",
        ],
        "source_hashes": {
            "split_manifest_sha256": file_sha256(split_manifest_path),
            "train_replay_manifest_sha256": file_sha256(
                train_replay_dir / "replay_manifest.json"
            ),
            "validation_replay_manifest_sha256": file_sha256(
                validation_replay_dir / "replay_manifest.json"
            ),
            "train_policy_config_sha256": file_sha256(train_policy_path),
            "train_trace_schema_sha256": file_sha256(train_schema_path),
        },
        "software_hashes": {
            name: file_sha256(path) for name, path in software_paths.items()
        },
        "frozen_artifacts": {
            "policy_config": policy_target.name,
            "policy_config_sha256": file_sha256(policy_target),
            "trace_schema": schema_target.name,
            "trace_schema_sha256": file_sha256(schema_target),
            "validation_policy_summary": summary_target.name,
            "validation_policy_summary_sha256": file_sha256(summary_target),
            "validation_primary_comparisons": comparison_target.name,
            "validation_primary_comparisons_sha256": file_sha256(
                comparison_target
            ),
        },
    }
    manifest_path = output_dir / "policy_freeze.json"
    _write_json(manifest_path, manifest)
    checksum_path = output_dir / "policy_freeze.sha256"
    checksum_path.write_text(file_sha256(manifest_path) + "\n", encoding="utf-8")
    return {**manifest, "policy_freeze_sha256": file_sha256(manifest_path)}
