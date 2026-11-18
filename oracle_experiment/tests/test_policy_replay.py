import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from adaptive_compute.answer_parser import MATH500_ANSWER_PARSER_NAME
from adaptive_compute.analysis.aggregate import build_config_results
from adaptive_compute.controller.policy_replay import (
    HEURISTIC_POLICY_ID,
    build_policy_replay,
    choose_heuristic_breadth,
    choose_agreement_stopping_breadth,
    choose_tertile_depth,
    inclusive_tertile_thresholds,
)
from adaptive_compute.math500 import (
    MATH500_DATASET_REVISION,
    MATH500_HF_DATASET_ID,
    MATH500_SPLIT,
)
from adaptive_compute.math500_splits import (
    MATH500_ASSIGNMENT_POLICY,
    MATH500_SPLIT_MANIFEST_TYPE,
)
from adaptive_compute.phase2_splits import (
    create_phase2_split_manifest,
    file_sha256,
    read_phase2_split_manifest,
)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _question(index: int) -> str:
    return f"What is {index} plus two?"


def _source_manifest(count: int) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "dataset": "gsm8k",
        "dataset_id": "openai/gsm8k",
        "dataset_config": "main",
        "split": "test",
        "num_problems": count,
        "seed": 42,
        "dataset_size": 8,
        "problems": [
            {
                "problem_id": f"gsm8k-test-{index:05d}",
                "source_index": index,
                "question_sha256": _sha256(_question(index)),
                "ground_truth": str(index + 2),
            }
            for index in range(count)
        ],
    }


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _sample(
    *,
    problem_id: str,
    index: int,
    length: int,
    sample_id: int,
    prompt_tokens: int,
    answer: str | None,
    truncated: bool,
) -> dict[str, Any]:
    return {
        "problem_id": problem_id,
        "question": _question(index),
        "ground_truth": str(index + 2),
        "L": length,
        "sample_id": sample_id,
        "repetition_id": 0,
        "prompt_tokens": prompt_tokens,
        "generated_tokens": 100 + sample_id,
        "latency_ms": 10.0 + sample_id,
        "parsed_answer": answer,
        "final_response_answer": answer,
        "reasoning_answer": None,
        "answer_parser_name": "gsm8k_numeric_v3",
        "truncated": truncated,
        "truncation_stage": "during_thinking" if truncated else "none",
        "failure_type": "truncated_before_answer" if answer is None else "correct",
        "dataset_quality_flag": None,
        "token_budget_utilization": (100 + sample_id) / length,
        "generation_error": None,
    }


def _fixture(tmp_path: Path, partition: str = "train") -> tuple[Path, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    development_path = tmp_path / "development.json"
    expanded_path = tmp_path / "expanded.json"
    audit_path = tmp_path / "audit.json"
    split_path = tmp_path / "split.json"
    _write_json(development_path, _source_manifest(6))
    _write_json(expanded_path, _source_manifest(8))
    _write_json(audit_path, {})
    create_phase2_split_manifest(
        development_manifest_path=development_path,
        expanded_pool_manifest_path=expanded_path,
        output_path=split_path,
        train_count=4,
        validation_count=2,
        test_count=2,
        split_seed=42,
        manual_audit_path=audit_path,
    )
    split = read_phase2_split_manifest(split_path)
    selected = sorted(split["partitions"][partition], key=lambda row: row["problem_id"])

    experiment_dir = tmp_path / "experiment"
    experiment_dir.mkdir()
    _write_json(
        experiment_dir / "experiment_manifest.json",
        {
            "experiment_id": "synthetic-policy-replay",
            "model": "Qwen/Qwen3-0.6B",
            "model_revision": "synthetic-revision",
            "prompt_template_name": "gsm8k_cot_v3",
            "answer_parser_name": "gsm8k_numeric_v3",
            "dataset_partition": partition,
        },
    )
    raw: list[dict[str, Any]] = []
    for position, row in enumerate(selected):
        index = int(row["source_index"])
        prompt_tokens = (position + 1) * 10
        truth = str(index + 2)
        for length in (512, 1024, 2048):
            for sample_id in range(4):
                answer: str | None = truth
                truncated = False
                if position == 1 and sample_id == 0:
                    # Valid but capped sample forces k=2; sample 2 agrees.
                    truncated = True
                if position == 2 and sample_id == 0:
                    # Invalid first sample and only one valid answer by k=2 forces k=4.
                    answer = None
                    truncated = True
                raw.append(
                    _sample(
                        problem_id=str(row["problem_id"]),
                        index=index,
                        length=length,
                        sample_id=sample_id,
                        prompt_tokens=prompt_tokens,
                        answer=answer,
                        truncated=truncated,
                    )
                )
    (experiment_dir / "raw_samples.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in raw), encoding="utf-8"
    )
    _write_csv(experiment_dir / "config_results.csv", build_config_results(raw, [1, 2, 4]))
    return experiment_dir, split_path


def _math_split_row(index: int) -> dict[str, Any]:
    return {
        "problem_id": f"math500-test-{index:03d}",
        "source_index": index,
        "subject": "Algebra",
        "level": index % 5 + 1,
        "unique_id": f"test/algebra/{index}.json",
        "question_sha256": _sha256(_question(index)),
        "ground_truth_sha256": _sha256(str(index + 2)),
        "raw_answer_sha256": _sha256(str(index + 2)),
    }


def _problem_ids_hash(rows: list[dict[str, Any]]) -> str:
    return _sha256("\n".join(str(row["problem_id"]) for row in rows))


def _math_fixture(tmp_path: Path, partition: str = "train") -> tuple[Path, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    partitions = {
        "train": [_math_split_row(index) for index in range(4)],
        "validation": [_math_split_row(index) for index in range(4, 6)],
        "test": [_math_split_row(index) for index in range(6, 8)],
    }
    split_path = tmp_path / "math_split.json"
    _write_json(
        split_path,
        {
            "schema_version": 1,
            "manifest_type": MATH500_SPLIT_MANIFEST_TYPE,
            "status": "frozen",
            "dataset": "math500",
            "dataset_id": MATH500_HF_DATASET_ID,
            "dataset_revision": MATH500_DATASET_REVISION,
            "source_split": MATH500_SPLIT,
            "assignment_policy": MATH500_ASSIGNMENT_POLICY,
            "answer_parser_name": MATH500_ANSWER_PARSER_NAME,
            "source_pilot_manifest": {
                "sha256": "synthetic",
                "num_problems": 1,
                "problem_ids": [partitions["train"][0]["problem_id"]],
            },
            "partition_sizes": {
                name: len(rows) for name, rows in partitions.items()
            },
            "partition_problem_ids_sha256": {
                name: _problem_ids_hash(rows) for name, rows in partitions.items()
            },
            "partitions": partitions,
        },
    )

    experiment_dir = tmp_path / "math_experiment"
    experiment_dir.mkdir()
    _write_json(
        experiment_dir / "experiment_manifest.json",
        {
            "experiment_id": "synthetic-math-policy-replay",
            "model": "Qwen/Qwen3-0.6B",
            "model_revision": "synthetic-revision",
            "prompt_template_name": "math500_cot_v1",
            "answer_parser_name": MATH500_ANSWER_PARSER_NAME,
            "dataset_partition": partition,
            "L_values": [1024, 2048, 4096],
            "k_values": [1, 2, 4],
        },
    )
    raw: list[dict[str, Any]] = []
    selected = sorted(partitions[partition], key=lambda row: row["problem_id"])
    for position, row in enumerate(selected):
        index = int(row["source_index"])
        prompt_tokens = (position + 1) * 10
        truth = str(index + 2)
        for length in (1024, 2048, 4096):
            for sample_id in range(4):
                answer: str | None = truth
                truncated = False
                if position == 1 and sample_id == 0:
                    truncated = True
                if position == 2 and sample_id == 0:
                    answer = None
                    truncated = True
                sample = _sample(
                    problem_id=str(row["problem_id"]),
                    index=index,
                    length=length,
                    sample_id=sample_id,
                    prompt_tokens=prompt_tokens,
                    answer=answer,
                    truncated=truncated,
                )
                sample["answer_parser_name"] = MATH500_ANSWER_PARSER_NAME
                raw.append(sample)
    (experiment_dir / "raw_samples.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in raw), encoding="utf-8"
    )
    _write_csv(experiment_dir / "config_results.csv", build_config_results(raw, [1, 2, 4]))
    return experiment_dir, split_path


def test_frozen_heuristic_stage_rules() -> None:
    assert inclusive_tertile_thresholds([10, 20, 30, 40]) == (20.0, 30.0)
    assert choose_tertile_depth(20, (20, 30)) == 512
    assert choose_tertile_depth(21, (20, 30)) == 1024
    assert choose_tertile_depth(31, (20, 30)) == 2048

    base = [
        {"sample_id": index, "final_response_answer": "42", "truncated": False}
        for index in range(4)
    ]
    assert choose_heuristic_breadth(base) == (1, "k1_valid_nontruncated")
    base[0]["truncated"] = True
    assert choose_heuristic_breadth(base) == (2, "k2_two_matching_valid")
    base[1]["final_response_answer"] = "40"
    assert choose_heuristic_breadth(base) == (4, "k4_fallback")
    assert choose_agreement_stopping_breadth(base) == (
        4,
        "k4_disagreement_or_invalid",
    )
    base[1]["final_response_answer"] = "42"
    assert choose_agreement_stopping_breadth(base) == (
        2,
        "k2_two_matching_valid",
    )


def test_replay_reconstructs_fixed_endpoints_and_charges_paid_prefixes(
    tmp_path: Path,
) -> None:
    experiment_dir, split_path = _fixture(tmp_path)
    output_dir = tmp_path / "replay"
    manifest = build_policy_replay(
        experiment_dir=experiment_dir,
        split_manifest_path=split_path,
        output_dir=output_dir,
    )

    assert manifest["held_out_test_replayed"] is False
    assert manifest["fixed_endpoint_reconstruction"] == "exact"
    assert manifest["row_counts"] == {
        "fixed_profile_traces": 36,
        "heuristic_traces": 4,
        "depth_only_heuristic_traces": 4,
        "breadth_only_agreement_traces": 12,
        "policy_summaries": 14,
        "primary_heuristic_comparisons": 13,
        "pareto_rows": 14,
    }
    with (output_dir / "heuristic_trace.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        traces = list(csv.DictReader(handle))
    assert {row["partition"] for row in traces} == {"train"}
    assert {row["policy_id"] for row in traces} == {HEURISTIC_POLICY_ID}
    assert sorted(int(row["decision_selected_k"]) for row in traces) == [1, 1, 2, 4]
    assert sorted(int(row["decision_selected_L"]) for row in traces) == [512, 512, 1024, 2048]
    by_k = {int(row["decision_selected_k"]): row for row in traces}
    assert by_k[1]["decision_paid_sample_ids"] == "0"
    assert by_k[2]["decision_paid_sample_ids"] == "0|1"
    assert by_k[4]["decision_paid_sample_ids"] == "0|1|2|3"
    assert int(by_k[1]["feature_state2_observed"]) == 0

    schema = json.loads((output_dir / "trace_schema.json").read_text("utf-8"))
    assert not set(schema["decision_feature_names"]) & set(
        schema["forbidden_as_decision_inputs"]
    )
    with pytest.raises(FileExistsError, match="already exists"):
        build_policy_replay(
            experiment_dir=experiment_dir,
            split_manifest_path=split_path,
            output_dir=output_dir,
        )


def test_test_replay_requires_policy_freeze_manifest(tmp_path: Path) -> None:
    experiment_dir, split_path = _fixture(tmp_path)
    with pytest.raises(ValueError, match="requires the pre-Test policy freeze manifest"):
        build_policy_replay(
            experiment_dir=experiment_dir,
            split_manifest_path=split_path,
            output_dir=tmp_path / "replay",
            partition="test",
            policy_config_path=tmp_path / "policy_config.json",
        )


def test_validation_replay_requires_frozen_train_policy_config(tmp_path: Path) -> None:
    experiment_dir, split_path = _fixture(tmp_path)
    with pytest.raises(ValueError, match="requires the frozen Train policy config"):
        build_policy_replay(
            experiment_dir=experiment_dir,
            split_manifest_path=split_path,
            output_dir=tmp_path / "replay",
            partition="validation",
        )


def test_authorized_test_replay_uses_frozen_policy_and_records_hashes(
    tmp_path: Path,
) -> None:
    train_experiment, _ = _fixture(tmp_path / "train", partition="train")
    train_replay = tmp_path / "train_replay"
    build_policy_replay(
        experiment_dir=train_experiment,
        split_manifest_path=tmp_path / "train" / "split.json",
        output_dir=train_replay,
        partition="train",
    )
    policy_config = train_replay / "policy_config.json"

    test_experiment, test_split_path = _fixture(tmp_path / "test", partition="test")
    split = read_phase2_split_manifest(test_split_path)
    freeze_path = tmp_path / "policy_freeze.json"
    _write_json(
        freeze_path,
        {
            "artifact_type": "gsm8k_phase2_policy_freeze",
            "status": "frozen",
            "model": "Qwen/Qwen3-0.6B",
            "model_revision": "synthetic-revision",
            "prompt_template_name": "gsm8k_cot_v3",
            "answer_parser_name": "gsm8k_numeric_v3",
            "selected_policy_id": "breadth_only_agreement_L1024_v1",
            "test_access": {
                "authorized_after_freeze": True,
                "outcomes_materialized_in_freeze_inputs": False,
                "gsm8k_test_problem_count": 2,
                "gsm8k_test_problem_ids_sha256": split[
                    "partition_problem_ids_sha256"
                ]["test"],
            },
            "source_hashes": {
                "split_manifest_sha256": file_sha256(test_split_path),
            },
            "software_hashes": {"policy_replay.py": "pre-freeze-code-hash"},
            "frozen_artifacts": {
                "policy_config_sha256": file_sha256(policy_config),
            },
        },
    )
    output_dir = tmp_path / "test_replay"

    manifest = build_policy_replay(
        experiment_dir=test_experiment,
        split_manifest_path=test_split_path,
        output_dir=output_dir,
        partition="test",
        policy_config_path=policy_config,
        policy_freeze_manifest_path=freeze_path,
    )

    assert manifest["held_out_test_replayed"] is True
    assert manifest["test_replay_authorized_by_policy_freeze"] is True
    assert manifest["selected_policy_id"] == "breadth_only_agreement_L1024_v1"
    assert manifest["problem_count"] == 2
    assert manifest["source_hashes"]["policy_freeze_manifest_sha256"] == file_sha256(
        freeze_path
    )
    assert manifest["source_hashes"]["pre_freeze_policy_replay_sha256"] == (
        "pre-freeze-code-hash"
    )
    assert manifest["source_hashes"]["execution_policy_replay_sha256"] == file_sha256(
        Path(__file__).parents[1]
        / "adaptive_compute"
        / "controller"
        / "policy_replay.py"
    )


def test_math_replay_auto_detects_contract_and_reconstructs_endpoints(
    tmp_path: Path,
) -> None:
    experiment_dir, split_path = _math_fixture(tmp_path)
    output_dir = tmp_path / "math_replay"

    manifest = build_policy_replay(
        experiment_dir=experiment_dir,
        split_manifest_path=split_path,
        output_dir=output_dir,
    )

    assert manifest["dataset"] == "math500"
    assert manifest["fixed_endpoint_reconstruction"] == "exact"
    assert manifest["row_counts"]["fixed_profile_traces"] == 36
    policy = json.loads((output_dir / "policy_config.json").read_text("utf-8"))
    assert policy["dataset"] == "math500"
    assert policy["depth_actions"] == [1024, 2048, 4096]
    with (output_dir / "heuristic_trace.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        traces = list(csv.DictReader(handle))
    assert sorted(int(row["decision_selected_L"]) for row in traces) == [
        1024,
        1024,
        2048,
        4096,
    ]


def test_math_replay_rejects_non_frozen_action_space(tmp_path: Path) -> None:
    experiment_dir, split_path = _math_fixture(tmp_path)

    with pytest.raises(ValueError, match="depth action space for math500"):
        build_policy_replay(
            experiment_dir=experiment_dir,
            split_manifest_path=split_path,
            output_dir=tmp_path / "replay",
            depths=(512, 1024, 2048),
        )


def test_replay_rejects_question_identity_drift(tmp_path: Path) -> None:
    experiment_dir, split_path = _math_fixture(tmp_path)
    raw_path = experiment_dir / "raw_samples.jsonl"
    rows = [json.loads(line) for line in raw_path.read_text("utf-8").splitlines()]
    rows[0]["question"] = "changed after split freeze"
    raw_path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="inconsistent problem identity"):
        build_policy_replay(
            experiment_dir=experiment_dir,
            split_manifest_path=split_path,
            output_dir=tmp_path / "replay",
        )


def test_authorized_math_test_replay_accepts_generic_freeze_fields(
    tmp_path: Path,
) -> None:
    train_experiment, train_split_path = _math_fixture(
        tmp_path / "train", partition="train"
    )
    train_replay = tmp_path / "math_train_replay"
    build_policy_replay(
        experiment_dir=train_experiment,
        split_manifest_path=train_split_path,
        output_dir=train_replay,
        partition="train",
    )
    policy_config = train_replay / "policy_config.json"

    test_experiment, test_split_path = _math_fixture(
        tmp_path / "test", partition="test"
    )
    split = json.loads(test_split_path.read_text("utf-8"))
    freeze_path = tmp_path / "math_policy_freeze.json"
    _write_json(
        freeze_path,
        {
            "artifact_type": "math500_phase2_policy_freeze",
            "status": "frozen",
            "dataset": "math500",
            "model": "Qwen/Qwen3-0.6B",
            "model_revision": "synthetic-revision",
            "prompt_template_name": "math500_cot_v1",
            "answer_parser_name": MATH500_ANSWER_PARSER_NAME,
            "selected_policy_id": "fixed_k2_L4096",
            "test_access": {
                "dataset": "math500",
                "authorized_after_freeze": True,
                "outcomes_materialized_in_freeze_inputs": False,
                "test_problem_count": 2,
                "test_problem_ids_sha256": split[
                    "partition_problem_ids_sha256"
                ]["test"],
            },
            "source_hashes": {
                "split_manifest_sha256": file_sha256(test_split_path),
            },
            "software_hashes": {"policy_replay.py": "math-pre-freeze-hash"},
            "frozen_artifacts": {
                "policy_config_sha256": file_sha256(policy_config),
            },
        },
    )
    output_dir = tmp_path / "math_test_replay"

    manifest = build_policy_replay(
        experiment_dir=test_experiment,
        split_manifest_path=test_split_path,
        output_dir=output_dir,
        partition="test",
        policy_config_path=policy_config,
        policy_freeze_manifest_path=freeze_path,
    )

    assert manifest["dataset"] == "math500"
    assert manifest["held_out_test_replayed"] is True
    assert manifest["test_replay_authorized_by_policy_freeze"] is True
    assert manifest["selected_policy_id"] == "fixed_k2_L4096"
    assert manifest["problem_count"] == 2
