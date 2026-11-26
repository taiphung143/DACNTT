"""GPU-free audit for the round-3 reviewer comments.

The script reads only frozen/local artifacts.  It never invokes a model,
changes a split, or writes into an experiment directory.  Outputs are compact
evidence tables under ``paper/audit_outputs``.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import fmean
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper" / "audit_outputs"
PRIMARY_REVISION = "c1899de289a04d12100db370d81485cdf75e47ca"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def truthy(value: Any) -> bool:
    return value is True or str(value).strip().lower() in {"1", "true"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    materialized = [dict(row) for row in rows]
    if not materialized:
        raise ValueError(f"no rows for {path}")
    fields: list[str] = []
    for row in materialized:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(materialized)


def breadth_stopping_rows() -> list[dict[str, Any]]:
    specifications = (
        (
            "GSM8K",
            ROOT
            / "results"
            / "phase2"
            / "qwen3_0_6b_gsm8k_test_n100_policy_replay_v3",
        ),
        (
            "MATH-500",
            ROOT
            / "results"
            / "phase2"
            / "qwen3_0_6b_math500_test_n100_baseline_replay_v1",
        ),
    )
    output: list[dict[str, Any]] = []
    for dataset, directory in specifications:
        breadth = read_csv(directory / "breadth_only_agreement_traces.csv")
        fixed = read_csv(directory / "fixed_profile_traces.csv")
        fixed_index = {(row["policy_id"], row["problem_id"]): row for row in fixed}
        for policy_id in sorted({row["policy_id"] for row in breadth}):
            length = int(policy_id.split("_L", 1)[1].split("_", 1)[0])
            adaptive = [row for row in breadth if row["policy_id"] == policy_id]
            comparators = [
                fixed_index[(f"fixed_k4_L{length}", row["problem_id"])]
                for row in adaptive
            ]
            adaptive_tokens = [float(row["outcome_actual_generated_tokens"]) for row in adaptive]
            fixed_tokens = [float(row["outcome_actual_generated_tokens"]) for row in comparators]
            stopped = sum(int(row["decision_selected_k"]) == 2 for row in adaptive)
            adaptive_mean = fmean(adaptive_tokens)
            fixed_mean = fmean(fixed_tokens)
            output.append(
                {
                    "dataset": dataset,
                    "L": length,
                    "n": len(adaptive),
                    "stopped_at_k2_n": stopped,
                    "required_k4_n": len(adaptive) - stopped,
                    "stopping_frequency": stopped / len(adaptive),
                    "breadth_stop_mean_actual_tokens": adaptive_mean,
                    "fixed_k4_mean_actual_tokens": fixed_mean,
                    "mean_actual_tokens_saved": fixed_mean - adaptive_mean,
                    "mean_actual_token_saving_fraction": (fixed_mean - adaptive_mean)
                    / fixed_mean,
                    "breadth_stop_correct_n": sum(
                        truthy(row["outcome_correct"]) for row in adaptive
                    ),
                    "fixed_k4_correct_n": sum(
                        truthy(row["outcome_correct"]) for row in comparators
                    ),
                    "prediction_equal_n": sum(
                        left["outcome_final_answer"] == right["outcome_final_answer"]
                        for left, right in zip(adaptive, comparators, strict=True)
                    ),
                    "correctness_equal_n": sum(
                        left["outcome_correct"] == right["outcome_correct"]
                        for left, right in zip(adaptive, comparators, strict=True)
                    ),
                    "trace_path": str(
                        (directory / "breadth_only_agreement_traces.csv").relative_to(ROOT)
                    ).replace("\\", "/"),
                }
            )
    return sorted(output, key=lambda row: (row["dataset"], row["L"]))


def parse_failure_audit() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    path = (
        ROOT
        / "results"
        / "qwen3_0_6b_gsm8k_test_n100_contract_v3"
        / "raw_samples.jsonl"
    )
    rows = [row for row in read_jsonl(path) if int(row["L"]) == 512]
    groups: Counter[tuple[Any, ...]] = Counter()
    for row in rows:
        groups[
            (
                bool(row.get("truncated")),
                not bool(row.get("parse_error")),
                str(row.get("truncation_stage", "none")),
                str(row.get("failure_type", "unknown")),
                row.get("final_response_answer") not in (None, ""),
            )
        ] += 1
    table = [
        {
            "truncated": truncated,
            "parseable": parseable,
            "truncation_stage": stage,
            "failure_type": failure,
            "final_response_answer_present": answer_present,
            "count": count,
        }
        for (truncated, parseable, stage, failure, answer_present), count in sorted(
            groups.items(), key=lambda item: tuple(str(value) for value in item[0])
        )
    ]
    after = [row for row in rows if row.get("truncation_stage") == "after_thinking"]
    summary = {
        "source": str(path.relative_to(ROOT)).replace("\\", "/"),
        "L": 512,
        "n": len(rows),
        "parse_failure_n": sum(bool(row.get("parse_error")) for row in rows),
        "parse_failure_fraction": sum(bool(row.get("parse_error")) for row in rows)
        / len(rows),
        "truncated_n": sum(bool(row.get("truncated")) for row in rows),
        "truncated_fraction": sum(bool(row.get("truncated")) for row in rows)
        / len(rows),
        "truncated_after_thinking_n": len(after),
        "truncated_after_thinking_parseable_n": sum(
            not bool(row.get("parse_error")) for row in after
        ),
        "truncated_after_thinking_unparseable_n": sum(
            bool(row.get("parse_error")) for row in after
        ),
        "cross_tab_total": sum(row["count"] for row in table),
    }
    return table, summary


def dataset_partition_relationship() -> dict[str, Any]:
    split_path = ROOT / "data" / "splits" / "phase2_gsm8k_split_v1.json"
    historical_manifest_path = ROOT / "results" / "raw" / "gsm8k_subset_manifest_n100.json"
    historical_experiment_path = (
        ROOT / "results" / "qwen3_1_7b_gsm8k_n100_r1" / "experiment_manifest.json"
    )
    historical_config_path = (
        ROOT / "results" / "qwen3_1_7b_gsm8k_n100_r1" / "config_results.csv"
    )
    split = read_json(split_path)
    historical_manifest = read_json(historical_manifest_path)
    historical_experiment = read_json(historical_experiment_path)
    config = read_csv(historical_config_path)

    partitions = {
        name: {row["problem_id"] for row in values}
        for name, values in split["partitions"].items()
    }
    hashes = {
        name: {row["question_sha256"] for row in values}
        for name, values in split["partitions"].items()
    }
    historical_ids = set(historical_experiment["problem_ids"])
    manifest_ids = {row["problem_id"] for row in historical_manifest["problems"]}
    manifest_hashes = {row["question_sha256"] for row in historical_manifest["problems"]}
    included_ids = {
        row["problem_id"] for row in config if truthy(row["evaluation_included"])
    }
    excluded_ids = sorted(historical_ids - included_ids)
    development_ids = partitions["train"] | partitions["validation"]
    development_hashes = hashes["train"] | hashes["validation"]
    return {
        "sources": {
            "split_manifest": str(split_path.relative_to(ROOT)).replace("\\", "/"),
            "historical_subset_manifest": str(
                historical_manifest_path.relative_to(ROOT)
            ).replace("\\", "/"),
            "historical_experiment_manifest": str(
                historical_experiment_path.relative_to(ROOT)
            ).replace("\\", "/"),
        },
        "counts": {
            "historical_manifest": len(manifest_ids),
            "historical_experiment": len(historical_ids),
            "historical_evaluation_included": len(included_ids),
            "train": len(partitions["train"]),
            "validation": len(partitions["validation"]),
            "test": len(partitions["test"]),
        },
        "excluded_historical_problem_ids": excluded_ids,
        "checks": {
            "historical_experiment_equals_historical_manifest_ids": historical_ids
            == manifest_ids,
            "historical_valid99_equals_train_union_validation_ids": included_ids
            == development_ids,
            "historical_manifest100_equals_development_plus_excluded_ids": historical_ids
            == development_ids | set(excluded_ids),
            "historical_question_hashes_equal_development_plus_excluded": manifest_hashes
            == development_hashes
            | {
                row["question_sha256"]
                for row in historical_manifest["problems"]
                if row["problem_id"] in excluded_ids
            },
            "historical_test_id_overlap_n": len(historical_ids & partitions["test"]),
            "development_test_id_overlap_n": len(development_ids & partitions["test"]),
            "train_validation_id_overlap_n": len(
                partitions["train"] & partitions["validation"]
            ),
            "train_test_question_hash_overlap_n": len(hashes["train"] & hashes["test"]),
            "validation_test_question_hash_overlap_n": len(
                hashes["validation"] & hashes["test"]
            ),
            "train_validation_question_hash_overlap_n": len(
                hashes["train"] & hashes["validation"]
            ),
        },
        "sha256": {
            "split_manifest": sha256(split_path),
            "historical_subset_manifest": sha256(historical_manifest_path),
            "historical_experiment_manifest": sha256(historical_experiment_path),
        },
    }


def escalation_rows() -> list[dict[str, Any]]:
    specifications = (
        (
            "GSM8K",
            ROOT
            / "results"
            / "phase2"
            / "qwen3_0_6b_gsm8k_n79_sequential_labels_v1",
        ),
        (
            "MATH-500",
            ROOT
            / "results"
            / "phase2"
            / "qwen3_0_6b_math500_train_n80_sequential_labels_v1",
        ),
    )
    output: list[dict[str, Any]] = []
    for dataset, directory in specifications:
        for family, filename in (
            ("depth", "depth_marginal_utility_labels.csv"),
            ("breadth", "breadth_marginal_utility_labels.csv"),
        ):
            rows = [
                row
                for row in read_csv(directory / filename)
                if abs(float(row["lambda"]) - 0.05) < 1e-12
            ]
            for stage in sorted({row["stage"] for row in rows}):
                selected = [row for row in rows if row["stage"] == stage]
                output.append(
                    {
                        "dataset": dataset,
                        "family": family,
                        "stage": stage,
                        "lambda": 0.05,
                        "eligible_n": len(selected),
                        "positive_escalation_label_n": sum(
                            truthy(row["label_escalate"]) for row in selected
                        ),
                        "negative_escalation_label_n": sum(
                            not truthy(row["label_escalate"]) for row in selected
                        ),
                        "correctness_gain_n": sum(
                            int(row["outcome_delta_correct"]) > 0 for row in selected
                        ),
                        "correctness_regression_n": sum(
                            int(row["outcome_delta_correct"]) < 0 for row in selected
                        ),
                        "correctness_unchanged_n": sum(
                            int(row["outcome_delta_correct"]) == 0 for row in selected
                        ),
                        "meets_30_positive_floor": sum(
                            truthy(row["label_escalate"]) for row in selected
                        )
                        >= 30,
                        "source_path": str((directory / filename).relative_to(ROOT)).replace(
                            "\\", "/"
                        ),
                    }
                )
    return output


def effective_sampling_configuration() -> dict[str, Any]:
    local_config = (
        Path.home()
        / ".cache"
        / "huggingface"
        / "hub"
        / "models--Qwen--Qwen3-0.6B"
        / "snapshots"
        / PRIMARY_REVISION
        / "generation_config.json"
    )
    adapter_path = ROOT / "adaptive_compute" / "models" / "transformers_adapter.py"
    manifests = (
        ROOT
        / "results"
        / "qwen3_0_6b_gsm8k_test_n100_contract_v3"
        / "experiment_manifest.json",
        ROOT
        / "results"
        / "qwen3_0_6b_math500_test_n100_contract_v1"
        / "experiment_manifest.json",
    )
    config = read_json(local_config)
    adapter = adapter_path.read_text(encoding="utf-8")
    manifest_values = [read_json(path) for path in manifests]
    return {
        "model_revision": PRIMARY_REVISION,
        "effective_top_k": config["top_k"],
        "effective_temperature": manifest_values[0]["temperature"],
        "effective_top_p": manifest_values[0]["top_p"],
        "enable_thinking": manifest_values[0]["enable_thinking"],
        "do_sample": manifest_values[0]["temperature"] > 0,
        "model_generation_config_temperature": config["temperature"],
        "model_generation_config_top_p": config["top_p"],
        "adapter_passes_temperature": "generation_kwargs.update(temperature=temperature" in adapter,
        "adapter_passes_top_p": "top_p=self.top_p" in adapter,
        "adapter_explicitly_passes_top_k": "top_k=" in adapter,
        "all_primary_manifests_same_revision": all(
            item["model_revision"] == PRIMARY_REVISION for item in manifest_values
        ),
        "all_primary_manifests_temperature_0_7": all(
            float(item["temperature"]) == 0.7 for item in manifest_values
        ),
        "all_primary_manifests_top_p_0_95": all(
            float(item["top_p"]) == 0.95 for item in manifest_values
        ),
        "local_generation_config_path": str(local_config),
        "local_generation_config_sha256": sha256(local_config),
        "adapter_path": str(adapter_path.relative_to(ROOT)).replace("\\", "/"),
        "adapter_sha256": sha256(adapter_path),
        "interpretation": (
            "temperature=0.7 and top_p=0.95 are explicit experiment overrides; "
            "top_k is not passed by the adapter and therefore inherits top_k=20 "
            "from the pinned model generation_config"
        ),
    }


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    breadth = breadth_stopping_rows()
    parse_table, parse_summary = parse_failure_audit()
    partitions = dataset_partition_relationship()
    escalation = escalation_rows()
    sampling = effective_sampling_configuration()

    write_csv(OUTPUT / "round3_breadth_stopping_rates.csv", breadth)
    write_csv(OUTPUT / "round3_train_escalation_counts.csv", escalation)
    write_csv(OUTPUT / "round3_gsm8k_L512_parse_crosstab.csv", parse_table)
    (OUTPUT / "round3_dataset_partition_relationship.json").write_text(
        json.dumps(partitions, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (OUTPUT / "round3_effective_sampling_config.json").write_text(
        json.dumps(sampling, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    partition_checks = partitions["checks"]
    all_checks = {
        "six_breadth_policies_present": len(breadth) == 6,
        "all_breadth_predictions_equal_fixed_k4": all(
            row["prediction_equal_n"] == row["n"] for row in breadth
        ),
        "all_breadth_correctness_equal_fixed_k4": all(
            row["correctness_equal_n"] == row["n"] for row in breadth
        ),
        "gsm8k_L512_parse_failure_is_233_of_400": parse_summary["n"] == 400
        and parse_summary["parse_failure_n"] == 233,
        "gsm8k_L512_after_thinking_split_is_4_parseable_3_unparseable": parse_summary[
            "truncated_after_thinking_parseable_n"
        ]
        == 4
        and parse_summary["truncated_after_thinking_unparseable_n"] == 3,
        "historical_valid99_equals_train79_plus_validation20": partition_checks[
            "historical_valid99_equals_train_union_validation_ids"
        ],
        "held_out_test_has_zero_id_or_question_hash_overlap": partition_checks[
            "historical_test_id_overlap_n"
        ]
        == 0
        and partition_checks["development_test_id_overlap_n"] == 0
        and partition_checks["train_test_question_hash_overlap_n"] == 0
        and partition_checks["validation_test_question_hash_overlap_n"] == 0,
        "all_escalation_stages_below_30_positive_floor": all(
            not row["meets_30_positive_floor"] for row in escalation
        ),
        "effective_top_k_verified_as_20": sampling["effective_top_k"] == 20
        and not sampling["adapter_explicitly_passes_top_k"],
    }
    summary = {
        "audit_scope": "existing local artifacts only; no model generation",
        "breadth_stopping": breadth,
        "gsm8k_L512_parse_failure": parse_summary,
        "sampling": sampling,
        "checks": all_checks,
        "all_checks_pass": all(all_checks.values()),
    }
    (OUTPUT / "round3_audit_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary["all_checks_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
