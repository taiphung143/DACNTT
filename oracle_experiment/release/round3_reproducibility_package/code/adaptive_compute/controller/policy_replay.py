"""Leakage-safe replay for fixed profiles and the frozen depth-first heuristic."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from statistics import fmean, quantiles
from typing import Any

from adaptive_compute.aggregation import build_configuration_summary
from adaptive_compute.analysis.statistics import exact_mcnemar_p, holm_adjust
from adaptive_compute.controller.sequential_data import FROZEN_DATASET_SETTINGS
from adaptive_compute.math500_splits import read_math500_split_manifest
from adaptive_compute.phase2_splits import file_sha256, read_phase2_split_manifest


REPLAY_SCHEMA_VERSION = 3
HEURISTIC_POLICY_ID = "depth_first_tertile_validity_agreement_v1"
DEPTH_ONLY_POLICY_ID = "depth_only_input_tertile_k1_v1"
DEPTH_ONLY_POLICY_RULE = "Train prompt-token tertiles choose L; always use k=1"
BREADTH_ONLY_POLICY_RULE = (
    "fixed L; always acquire two samples; stop for two matching valid answers; "
    "otherwise acquire samples 3-4"
)
HEURISTIC_POLICY_RULE = (
    "inclusive Train prompt-token tertiles choose ordered L; stop at k=1 only "
    "for a valid non-truncated final answer; stop at k=2 only for two matching "
    "valid answers; otherwise acquire k=4"
)
DEFAULT_DEPTHS = (512, 1024, 2048)
DEFAULT_BREADTHS = (1, 2, 4)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _read_frozen_split_manifest(path: Path) -> tuple[str, dict[str, Any]]:
    payload = _read_json(path)
    dataset = str(payload.get("dataset", "")).strip().lower()
    if dataset == "gsm8k":
        return dataset, read_phase2_split_manifest(path)
    if dataset == "math500":
        return dataset, read_math500_split_manifest(path)
    raise ValueError(f"unsupported policy-replay dataset: {dataset or '<missing>'}")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"JSONL row {line_number} is not an object")
            rows.append(row)
    return rows


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"CSV table is empty: {path}")
    return rows


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty replay table: {path.name}")
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


def inclusive_tertile_thresholds(values: Sequence[int]) -> tuple[float, float]:
    """Return deterministic inclusive tertiles for the Train-only heuristic."""

    normalized = [int(value) for value in values]
    if len(normalized) < 3:
        raise ValueError("at least three Train problems are required for tertiles")
    lower, upper = quantiles(normalized, n=3, method="inclusive")
    return float(lower), float(upper)


def choose_tertile_depth(
    prompt_tokens: int,
    thresholds: tuple[float, float],
    depths: Sequence[int] = DEFAULT_DEPTHS,
) -> int:
    ordered = tuple(sorted(int(value) for value in depths))
    if len(ordered) != 3:
        raise ValueError("tertile heuristic requires exactly three ordered depths")
    lower, upper = thresholds
    if prompt_tokens <= lower:
        return ordered[0]
    if prompt_tokens <= upper:
        return ordered[1]
    return ordered[2]


def _answer(sample: Mapping[str, Any]) -> str | None:
    value = sample.get("final_response_answer", sample.get("parsed_answer"))
    return None if value is None or str(value).strip() == "" else str(value)


def choose_heuristic_breadth(samples: Sequence[Mapping[str, Any]]) -> tuple[int, str]:
    """Choose k using only the paid prefixes described by baseline B3."""

    if [int(sample["sample_id"]) for sample in samples] != [0, 1, 2, 3]:
        raise ValueError("heuristic replay requires the nested sample IDs 0,1,2,3")
    first_answer = _answer(samples[0])
    if first_answer is not None and not bool(samples[0].get("truncated")):
        return 1, "k1_valid_nontruncated"
    second_answer = _answer(samples[1])
    if (
        first_answer is not None
        and second_answer is not None
        and first_answer == second_answer
    ):
        return 2, "k2_two_matching_valid"
    return 4, "k4_fallback"


def choose_agreement_stopping_breadth(
    samples: Sequence[Mapping[str, Any]],
) -> tuple[int, str]:
    """Choose k for the frozen breadth-only agreement-stopping comparator."""

    if [int(sample["sample_id"]) for sample in samples] != [0, 1, 2, 3]:
        raise ValueError("breadth-only replay requires nested sample IDs 0,1,2,3")
    first_answer = _answer(samples[0])
    second_answer = _answer(samples[1])
    if (
        first_answer is not None
        and second_answer is not None
        and first_answer == second_answer
    ):
        return 2, "k2_two_matching_valid"
    return 4, "k4_disagreement_or_invalid"


def _pool_index(
    raw_rows: Sequence[Mapping[str, Any]],
    *,
    depths: Sequence[int],
    max_k: int,
) -> tuple[dict[tuple[str, int], list[Mapping[str, Any]]], dict[str, int]]:
    pools: dict[tuple[str, int], list[Mapping[str, Any]]] = defaultdict(list)
    input_tokens: dict[str, set[int]] = defaultdict(set)
    seen: set[tuple[str, int, int, int]] = set()
    for row in raw_rows:
        repetition = int(row.get("repetition_id", 0))
        if repetition != 0:
            raise ValueError("policy replay v1 supports exactly repetition_id=0")
        if row.get("generation_error"):
            raise ValueError(f"generation error in replay source: {row['problem_id']}")
        key = (
            str(row["problem_id"]),
            int(row["L"]),
            int(row["sample_id"]),
            repetition,
        )
        if key in seen:
            raise ValueError(f"duplicate raw sample key: {key}")
        seen.add(key)
        pools[(key[0], key[1])].append(row)
        input_tokens[key[0]].add(int(row["prompt_tokens"]))

    expected_depths = set(int(value) for value in depths)
    problem_ids = {problem_id for problem_id, _ in pools}
    for problem_id in problem_ids:
        available = {length for candidate, length in pools if candidate == problem_id}
        if available != expected_depths:
            raise ValueError(f"incomplete depth pools for {problem_id}: {available}")
        if len(input_tokens[problem_id]) != 1:
            raise ValueError(f"inconsistent prompt-token count for {problem_id}")
        for length in expected_depths:
            pool = sorted(
                pools[(problem_id, length)], key=lambda row: int(row["sample_id"])
            )
            if [int(row["sample_id"]) for row in pool] != list(range(max_k)):
                raise ValueError(f"incomplete nested sample pool for {problem_id}, L={length}")
            identities = {
                (str(row.get("question")), str(row.get("ground_truth"))) for row in pool
            }
            if len(identities) != 1:
                raise ValueError(f"inconsistent problem identity for {problem_id}, L={length}")
            pools[(problem_id, length)] = pool
    return pools, {problem_id: values.pop() for problem_id, values in input_tokens.items()}


def _trace_from_samples(
    *,
    policy_id: str,
    policy_type: str,
    partition: str,
    length: int,
    selected: Sequence[Mapping[str, Any]],
    decision_reason: str,
    prompt_tokens: int,
    thresholds: tuple[float, float] | None = None,
) -> dict[str, Any]:
    k = len(selected)
    summary = build_configuration_summary(
        [{**sample, "k": k, "L": length} for sample in selected]
    )
    first_answer = _answer(selected[0])
    second_answer = _answer(selected[1]) if k >= 2 else None
    return {
        "problem_id": str(selected[0]["problem_id"]),
        "partition": partition,
        "policy_id": policy_id,
        "policy_type": policy_type,
        "decision_selected_L": length,
        "decision_selected_k": k,
        "decision_stop_reason": decision_reason,
        "decision_paid_sample_ids": "|".join(str(row["sample_id"]) for row in selected),
        "feature_prompt_token_count": prompt_tokens,
        "feature_train_tertile_low": thresholds[0] if thresholds else "",
        "feature_train_tertile_high": thresholds[1] if thresholds else "",
        "feature_state1_answer_valid": int(first_answer is not None),
        "feature_state1_truncated": int(bool(selected[0].get("truncated"))),
        "feature_state1_actual_tokens": int(selected[0].get("generated_tokens", 0)),
        "feature_state2_observed": int(k >= 2),
        "feature_state2_two_valid": int(
            k >= 2 and first_answer is not None and second_answer is not None
        ),
        "feature_state2_answers_match": int(
            k >= 2
            and first_answer is not None
            and second_answer is not None
            and first_answer == second_answer
        ),
        "outcome_final_answer": summary["final_majority_answer"] or "",
        "outcome_final_valid": int(summary["valid_answer_count"] > 0),
        "outcome_correct": int(bool(summary["final_correct"])),
        "outcome_valid_answer_count": summary["valid_answer_count"],
        "outcome_invalid_answer_count": summary["invalid_answer_count"],
        "outcome_agreement": (
            summary["agreement"] if summary["agreement"] is not None else ""
        ),
        "outcome_actual_generated_tokens": summary["actual_generated_tokens"],
        "outcome_allocated_token_budget": summary["allocated_token_budget"],
        "outcome_total_prompt_tokens": summary["total_prompt_tokens"],
        "outcome_latency_ms": summary["total_latency_ms"],
        "outcome_sample_truncation_count": summary["sample_truncation_count"],
        "outcome_sample_parse_failure_count": summary["sample_parse_failure_count"],
    }


def _parse_bool(value: Any) -> bool:
    if value is True or str(value).strip().lower() == "true":
        return True
    if value is False or str(value).strip().lower() == "false":
        return False
    raise ValueError(f"expected Boolean value, found {value!r}")


def _verify_fixed_endpoints(
    traces: Sequence[Mapping[str, Any]], config_rows: Sequence[Mapping[str, Any]]
) -> None:
    expected = {
        (str(row["problem_id"]), int(row["k"]), int(row["L"])): row
        for row in config_rows
        if int(row.get("repetition_id", 0)) == 0
    }
    if len(expected) != len(config_rows):
        raise ValueError("configuration table contains duplicate or unsupported repetitions")
    if len(traces) != len(expected):
        raise ValueError("fixed replay does not cover every configuration endpoint")
    for trace in traces:
        key = (
            str(trace["problem_id"]),
            int(trace["decision_selected_k"]),
            int(trace["decision_selected_L"]),
        )
        row = expected.get(key)
        if row is None:
            raise ValueError(f"fixed replay produced unknown endpoint: {key}")
        checks = {
            "correct": int(_parse_bool(row["final_correct"])),
            "actual tokens": int(row["actual_generated_tokens"]),
            "allocated budget": int(row["allocated_token_budget"]),
            "valid answers": int(row["valid_answer_count"]),
            "invalid answers": int(row["invalid_answer_count"]),
            "truncations": int(row["sample_truncation_count"]),
        }
        actual = {
            "correct": int(trace["outcome_correct"]),
            "actual tokens": int(trace["outcome_actual_generated_tokens"]),
            "allocated budget": int(trace["outcome_allocated_token_budget"]),
            "valid answers": int(trace["outcome_valid_answer_count"]),
            "invalid answers": int(trace["outcome_invalid_answer_count"]),
            "truncations": int(trace["outcome_sample_truncation_count"]),
        }
        if checks != actual:
            raise ValueError(f"fixed replay disagrees with configuration endpoint {key}")
        if not math.isclose(
            float(trace["outcome_latency_ms"]),
            float(row["sum_sample_latency_ms"]),
            rel_tol=1e-12,
            abs_tol=1e-9,
        ):
            raise ValueError(f"fixed replay latency disagrees for {key}")


def _policy_summaries(traces: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for trace in traces:
        grouped[str(trace["policy_id"])].append(trace)
    rows: list[dict[str, Any]] = []
    for policy_id, group in sorted(grouped.items()):
        paid_samples = [int(row["decision_selected_k"]) for row in group]
        truncations = sum(int(row["outcome_sample_truncation_count"]) for row in group)
        rows.append(
            {
                "policy_id": policy_id,
                "policy_type": group[0]["policy_type"],
                "partition": group[0]["partition"],
                "num_problems": len(group),
                "correct_count": sum(int(row["outcome_correct"]) for row in group),
                "accuracy": fmean(int(row["outcome_correct"]) for row in group),
                "avg_actual_generated_tokens": fmean(
                    int(row["outcome_actual_generated_tokens"]) for row in group
                ),
                "avg_allocated_token_budget": fmean(
                    int(row["outcome_allocated_token_budget"]) for row in group
                ),
                "avg_latency_ms": fmean(float(row["outcome_latency_ms"]) for row in group),
                "final_valid_rate": fmean(
                    int(row["outcome_final_valid"]) for row in group
                ),
                "paid_sample_truncation_rate": truncations / sum(paid_samples),
                "selected_k_distribution": json.dumps(
                    dict(sorted(Counter(paid_samples).items()))
                ),
                "selected_L_distribution": json.dumps(
                    dict(
                        sorted(
                            Counter(
                                int(row["decision_selected_L"]) for row in group
                            ).items()
                        )
                    )
                ),
            }
        )
    return rows


def _bootstrap_interval(
    values: Sequence[float], *, repetitions: int, seed: str
) -> tuple[float, float]:
    if not values or repetitions < 100:
        raise ValueError("paired bootstrap requires values and at least 100 repetitions")
    rng = random.Random(seed)
    count = len(values)
    estimates = sorted(
        sum(values[rng.randrange(count)] for _ in range(count)) / count
        for _ in range(repetitions)
    )
    lower = estimates[math.floor(0.025 * (repetitions - 1))]
    upper = estimates[math.ceil(0.975 * (repetitions - 1))]
    return lower, upper


def _primary_policy_comparisons(
    comparator_traces: Sequence[Mapping[str, Any]],
    heuristic_traces: Sequence[Mapping[str, Any]],
    *,
    bootstrap_repetitions: int = 10_000,
) -> list[dict[str, Any]]:
    heuristic = {str(row["problem_id"]): row for row in heuristic_traces}
    comparators_by_policy: dict[str, dict[str, Mapping[str, Any]]] = defaultdict(dict)
    for row in comparator_traces:
        comparators_by_policy[str(row["policy_id"])][str(row["problem_id"])] = row
    output: list[dict[str, Any]] = []
    p_values: list[float] = []
    for policy_id, comparator in sorted(comparators_by_policy.items()):
        problem_ids = sorted(set(heuristic) & set(comparator))
        if len(problem_ids) != len(heuristic):
            raise ValueError(f"paired policy coverage mismatch for {policy_id}")
        accuracy_differences = [
            int(heuristic[problem_id]["outcome_correct"])
            - int(comparator[problem_id]["outcome_correct"])
            for problem_id in problem_ids
        ]
        token_differences = [
            int(heuristic[problem_id]["outcome_actual_generated_tokens"])
            - int(comparator[problem_id]["outcome_actual_generated_tokens"])
            for problem_id in problem_ids
        ]
        comparator_only = sum(value == -1 for value in accuracy_differences)
        heuristic_only = sum(value == 1 for value in accuracy_differences)
        accuracy_low, accuracy_high = _bootstrap_interval(
            accuracy_differences,
            repetitions=bootstrap_repetitions,
            seed=f"policy-replay-v3|42|{policy_id}|accuracy",
        )
        token_low, token_high = _bootstrap_interval(
            token_differences,
            repetitions=bootstrap_repetitions,
            seed=f"policy-replay-v3|42|{policy_id}|tokens",
        )
        comparator_accuracy = fmean(
            int(comparator[problem_id]["outcome_correct"]) for problem_id in problem_ids
        )
        heuristic_accuracy = fmean(
            int(heuristic[problem_id]["outcome_correct"]) for problem_id in problem_ids
        )
        comparator_tokens = fmean(
            int(comparator[problem_id]["outcome_actual_generated_tokens"])
            for problem_id in problem_ids
        )
        heuristic_tokens = fmean(
            int(heuristic[problem_id]["outcome_actual_generated_tokens"])
            for problem_id in problem_ids
        )
        exact_p = exact_mcnemar_p(comparator_only, heuristic_only)
        p_values.append(exact_p)
        output.append(
            {
                "comparison": f"{policy_id}_vs_{HEURISTIC_POLICY_ID}",
                "comparator_policy_id": policy_id,
                "comparator_policy_type": next(iter(comparator.values()))[
                    "policy_type"
                ],
                "heuristic_policy_id": HEURISTIC_POLICY_ID,
                "num_paired_problems": len(problem_ids),
                "comparator_accuracy": comparator_accuracy,
                "heuristic_accuracy": heuristic_accuracy,
                "accuracy_difference_heuristic_minus_comparator": heuristic_accuracy
                - comparator_accuracy,
                "accuracy_difference_bootstrap_95_low": accuracy_low,
                "accuracy_difference_bootstrap_95_high": accuracy_high,
                "comparator_avg_actual_tokens": comparator_tokens,
                "heuristic_avg_actual_tokens": heuristic_tokens,
                "token_difference_heuristic_minus_comparator": heuristic_tokens
                - comparator_tokens,
                "token_difference_bootstrap_95_low": token_low,
                "token_difference_bootstrap_95_high": token_high,
                "relative_token_change": (heuristic_tokens - comparator_tokens)
                / comparator_tokens,
                "comparator_only_correct": comparator_only,
                "heuristic_only_correct": heuristic_only,
                "mcnemar_exact_p": exact_p,
                "matched_actual_token_cost_within_10_percent": abs(
                    heuristic_tokens - comparator_tokens
                )
                / comparator_tokens
                <= 0.10,
            }
        )
    adjusted = holm_adjust(p_values)
    for row, adjusted_p in zip(output, adjusted, strict=True):
        row["holm_adjusted_p"] = adjusted_p
        row["accuracy_inference_status"] = (
            "significant" if adjusted_p < 0.05 else "inconclusive"
        )
    return output


def _pareto_rows(summary_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in summary_rows:
        accuracy = float(row["accuracy"])
        tokens = float(row["avg_actual_generated_tokens"])
        dominators = [
            str(other["policy_id"])
            for other in summary_rows
            if str(other["policy_id"]) != str(row["policy_id"])
            and float(other["accuracy"]) >= accuracy
            and float(other["avg_actual_generated_tokens"]) <= tokens
            and (
                float(other["accuracy"]) > accuracy
                or float(other["avg_actual_generated_tokens"]) < tokens
            )
        ]
        output.append(
            {
                "policy_id": row["policy_id"],
                "policy_type": row["policy_type"],
                "partition": row["partition"],
                "accuracy": accuracy,
                "avg_actual_generated_tokens": tokens,
                "pareto_nondominated": not dominators,
                "dominated_by": "|".join(sorted(dominators)),
                "interpretation": f"{str(row['partition']).title()}-only descriptive frontier",
            }
        )
    return sorted(output, key=lambda row: float(row["avg_actual_generated_tokens"]))


def build_policy_replay(
    *,
    experiment_dir: Path,
    split_manifest_path: Path,
    output_dir: Path,
    partition: str = "train",
    policy_config_path: Path | None = None,
    policy_freeze_manifest_path: Path | None = None,
    depths: Sequence[int] | None = None,
    breadths: Sequence[int] | None = None,
) -> dict[str, Any]:
    """Replay fixed profiles and frozen policies on an authorized partition."""

    if output_dir.exists():
        raise FileExistsError(f"policy replay output already exists: {output_dir}")
    if partition not in {"train", "validation", "test"}:
        raise ValueError("partition must be train, validation, or test")
    if partition == "train" and policy_config_path is not None:
        raise ValueError("Train replay fits its own tertiles; do not pass policy_config_path")
    if partition != "train" and policy_config_path is None:
        raise ValueError(f"{partition.title()} replay requires the frozen Train policy config")
    if partition == "test" and policy_freeze_manifest_path is None:
        raise ValueError("Test replay requires the pre-Test policy freeze manifest")
    if partition != "test" and policy_freeze_manifest_path is not None:
        raise ValueError("the policy freeze manifest is only accepted for Test replay")
    dataset_name, split = _read_frozen_split_manifest(split_manifest_path)
    frozen_settings = FROZEN_DATASET_SETTINGS[dataset_name]
    selected_depths = frozen_settings["depths"] if depths is None else depths
    selected_breadths = frozen_settings["breadths"] if breadths is None else breadths
    ordered_depths = tuple(sorted(int(value) for value in selected_depths))
    ordered_breadths = tuple(sorted(int(value) for value in selected_breadths))
    if ordered_depths != frozen_settings["depths"]:
        raise ValueError(
            f"replay depth action space for {dataset_name} must remain "
            f"{frozen_settings['depths']}"
        )
    if ordered_breadths != frozen_settings["breadths"]:
        raise ValueError(
            f"replay breadth action space for {dataset_name} must remain "
            f"{frozen_settings['breadths']}"
        )

    raw_path = experiment_dir / "raw_samples.jsonl"
    config_path = experiment_dir / "config_results.csv"
    experiment_manifest_path = experiment_dir / "experiment_manifest.json"
    experiment_manifest = _read_json(experiment_manifest_path)
    if experiment_manifest.get("dataset_partition") != partition:
        raise ValueError("experiment manifest partition does not match requested replay")
    manifest_depths = experiment_manifest.get("L_values")
    manifest_breadths = experiment_manifest.get("k_values")
    if manifest_depths is not None and tuple(sorted(map(int, manifest_depths))) != ordered_depths:
        raise ValueError("experiment depth action space disagrees with frozen protocol")
    if manifest_breadths is not None and tuple(sorted(map(int, manifest_breadths))) != ordered_breadths:
        raise ValueError("experiment breadth action space disagrees with frozen protocol")
    policy_freeze: dict[str, Any] | None = None
    if partition == "test":
        assert policy_config_path is not None
        assert policy_freeze_manifest_path is not None
        policy_freeze = _read_json(policy_freeze_manifest_path)
        expected_freeze_type = f"{dataset_name}_phase2_policy_freeze"
        if policy_freeze.get("artifact_type") != expected_freeze_type:
            raise ValueError("unexpected Test policy freeze artifact type")
        frozen_dataset = policy_freeze.get("dataset")
        if frozen_dataset is not None and frozen_dataset != dataset_name:
            raise ValueError("Test policy freeze dataset does not match replay")
        if policy_freeze.get("status") != "frozen":
            raise ValueError("Test policy freeze is not frozen")
        test_access = policy_freeze.get("test_access", {})
        if test_access.get("authorized_after_freeze") is not True:
            raise ValueError("policy freeze does not authorize Test replay")
        if test_access.get("outcomes_materialized_in_freeze_inputs") is not False:
            raise ValueError("policy freeze does not certify pre-Test isolation")
        frozen_artifacts = policy_freeze.get("frozen_artifacts", {})
        if file_sha256(policy_config_path) != frozen_artifacts.get(
            "policy_config_sha256"
        ):
            raise ValueError("Test policy config does not match the freeze bundle")
        provenance_checks = {
            "model": experiment_manifest.get("model"),
            "model_revision": experiment_manifest.get("model_revision"),
            "prompt_template_name": experiment_manifest.get(
                "prompt_template_name"
            ),
            "answer_parser_name": experiment_manifest.get("answer_parser_name"),
        }
        for field, actual in provenance_checks.items():
            if policy_freeze.get(field) != actual:
                raise ValueError(f"Test experiment differs from freeze: {field}")
        if policy_freeze.get("source_hashes", {}).get(
            "split_manifest_sha256"
        ) != file_sha256(split_manifest_path):
            raise ValueError("Test split manifest does not match the freeze bundle")
        frozen_test_count = test_access.get(
            "test_problem_count",
            test_access.get(f"{dataset_name}_test_problem_count", -1),
        )
        if int(frozen_test_count) != int(split["partition_sizes"]["test"]):
            raise ValueError("Test problem count differs from the freeze bundle")
        frozen_test_ids_hash = test_access.get(
            "test_problem_ids_sha256",
            test_access.get(f"{dataset_name}_test_problem_ids_sha256"),
        )
        if frozen_test_ids_hash != split["partition_problem_ids_sha256"]["test"]:
            raise ValueError("Test problem IDs differ from the freeze bundle")
    partition_by_id = {
        str(row["problem_id"]): name
        for name, rows in split["partitions"].items()
        for row in rows
    }
    split_rows_by_id = {
        str(row["problem_id"]): row
        for rows in split["partitions"].values()
        for row in rows
    }
    raw_rows = _read_jsonl(raw_path)
    pools, prompt_tokens = _pool_index(
        raw_rows, depths=ordered_depths, max_k=max(ordered_breadths)
    )
    problem_ids = sorted(prompt_tokens)
    if not problem_ids:
        raise ValueError("no replayable problems found")
    for problem_id in problem_ids:
        observed_partition = partition_by_id.get(problem_id)
        if observed_partition != partition:
            raise ValueError(
                f"problem {problem_id} belongs to {observed_partition}, not {partition}"
            )
        split_row = split_rows_by_id[problem_id]
        identity_sample = pools[(problem_id, ordered_depths[0])][0]
        if _sha256_text(str(identity_sample["question"])) != split_row[
            "question_sha256"
        ]:
            raise ValueError(f"question hash disagrees with frozen split: {problem_id}")
        if _sha256_text(str(identity_sample["ground_truth"])) != split_row[
            "ground_truth_sha256"
        ]:
            raise ValueError(f"ground-truth hash disagrees with frozen split: {problem_id}")

    if partition == "train":
        thresholds = inclusive_tertile_thresholds(
            [prompt_tokens[problem_id] for problem_id in problem_ids]
        )
        policy_config: dict[str, Any] = {
            "schema_version": REPLAY_SCHEMA_VERSION,
            "dataset": dataset_name,
            "heuristic_policy_id": HEURISTIC_POLICY_ID,
            "heuristic_policy_rule": HEURISTIC_POLICY_RULE,
            "depth_only_policy_id": DEPTH_ONLY_POLICY_ID,
            "depth_only_policy_rule": DEPTH_ONLY_POLICY_RULE,
            "breadth_only_policy_rule": BREADTH_ONLY_POLICY_RULE,
            "tertile_method": "statistics.quantiles(n=3, method='inclusive')",
            "tertile_fit_partition": "train",
            "prompt_token_tertile_low": thresholds[0],
            "prompt_token_tertile_high": thresholds[1],
            "depth_mapping": {
                f"prompt_tokens <= {thresholds[0]:g}": ordered_depths[0],
                f"{thresholds[0]:g} < prompt_tokens <= {thresholds[1]:g}": ordered_depths[1],
                f"prompt_tokens > {thresholds[1]:g}": ordered_depths[2],
            },
            "depth_actions": list(ordered_depths),
            "breadth_actions": list(ordered_breadths),
            "cost_metric": "all actual generated tokens from every paid sample",
            "paired_bootstrap_repetitions": 10_000,
            "paired_bootstrap_seed_policy": "policy-replay-v3|42|comparison|metric",
            "paired_accuracy_test": "two-sided exact McNemar with Holm correction",
        }
    else:
        assert policy_config_path is not None
        policy_config = _read_json(policy_config_path)
        replay_label = partition.title()
        if policy_config.get("tertile_fit_partition") != "train":
            raise ValueError(f"{replay_label} policy config was not fitted on Train")
        if policy_config.get("heuristic_policy_id") != HEURISTIC_POLICY_ID:
            raise ValueError(f"{replay_label} policy config has an unexpected heuristic ID")
        if policy_config.get("heuristic_policy_rule") != HEURISTIC_POLICY_RULE:
            raise ValueError(f"{replay_label} policy config changes the frozen heuristic rule")
        if policy_config.get("depth_only_policy_id") != DEPTH_ONLY_POLICY_ID:
            raise ValueError(f"{replay_label} policy config changes the depth-only policy ID")
        if policy_config.get("depth_only_policy_rule") != DEPTH_ONLY_POLICY_RULE:
            raise ValueError(f"{replay_label} policy config changes the depth-only rule")
        if policy_config.get("breadth_only_policy_rule") != BREADTH_ONLY_POLICY_RULE:
            raise ValueError(f"{replay_label} policy config changes the breadth-only rule")
        configured_dataset = policy_config.get("dataset")
        if configured_dataset is None and dataset_name != "gsm8k":
            raise ValueError(f"{replay_label} policy config is missing its dataset")
        if configured_dataset is not None and configured_dataset != dataset_name:
            raise ValueError(f"{replay_label} policy config changes the dataset")
        configured_depths = policy_config.get("depth_actions")
        if configured_depths is None and dataset_name != "gsm8k":
            raise ValueError(f"{replay_label} policy config is missing depth actions")
        if configured_depths is not None and configured_depths != list(ordered_depths):
            raise ValueError(f"{replay_label} policy config changes the depth action space")
        if policy_config.get("breadth_actions") != list(ordered_breadths):
            raise ValueError(f"{replay_label} policy config changes the breadth action space")
        thresholds = (
            float(policy_config["prompt_token_tertile_low"]),
            float(policy_config["prompt_token_tertile_high"]),
        )
    fixed_traces: list[dict[str, Any]] = []
    heuristic_traces: list[dict[str, Any]] = []
    depth_only_traces: list[dict[str, Any]] = []
    breadth_only_traces: list[dict[str, Any]] = []
    for problem_id in problem_ids:
        for length in ordered_depths:
            pool = pools[(problem_id, length)]
            for k in ordered_breadths:
                fixed_traces.append(
                    _trace_from_samples(
                        policy_id=f"fixed_k{k}_L{length}",
                        policy_type="fixed_profile",
                        partition=partition,
                        length=length,
                        selected=pool[:k],
                        decision_reason="fixed_profile",
                        prompt_tokens=prompt_tokens[problem_id],
                    )
                )
            breadth_k, breadth_reason = choose_agreement_stopping_breadth(pool)
            breadth_only_traces.append(
                _trace_from_samples(
                    policy_id=f"breadth_only_agreement_L{length}_v1",
                    policy_type="breadth_only_agreement_stopping",
                    partition=partition,
                    length=length,
                    selected=pool[:breadth_k],
                    decision_reason=breadth_reason,
                    prompt_tokens=prompt_tokens[problem_id],
                )
            )

        selected_length = choose_tertile_depth(
            prompt_tokens[problem_id], thresholds, ordered_depths
        )
        selected_pool = pools[(problem_id, selected_length)]
        depth_only_traces.append(
            _trace_from_samples(
                policy_id=DEPTH_ONLY_POLICY_ID,
                policy_type="depth_only_input_tertile",
                partition=partition,
                length=selected_length,
                selected=selected_pool[:1],
                decision_reason="input_tertile_k1",
                prompt_tokens=prompt_tokens[problem_id],
                thresholds=thresholds,
            )
        )
        selected_k, reason = choose_heuristic_breadth(selected_pool)
        heuristic_traces.append(
            _trace_from_samples(
                policy_id=HEURISTIC_POLICY_ID,
                policy_type="depth_first_heuristic",
                partition=partition,
                length=selected_length,
                selected=selected_pool[:selected_k],
                decision_reason=reason,
                prompt_tokens=prompt_tokens[problem_id],
                thresholds=thresholds,
            )
        )

    _verify_fixed_endpoints(fixed_traces, _read_csv(config_path))
    fixed_path = output_dir / "fixed_profile_traces.csv"
    heuristic_path = output_dir / "heuristic_trace.csv"
    depth_only_path = output_dir / "depth_only_heuristic_trace.csv"
    breadth_only_path = output_dir / "breadth_only_agreement_traces.csv"
    summary_path = output_dir / "policy_summary.csv"
    comparison_path = output_dir / "primary_heuristic_comparisons.csv"
    pareto_path = output_dir / "policy_pareto.csv"
    config_output_path = output_dir / "policy_config.json"
    schema_path = output_dir / "trace_schema.json"
    manifest_path = output_dir / "replay_manifest.json"
    _write_csv(fixed_path, fixed_traces)
    _write_csv(heuristic_path, heuristic_traces)
    _write_csv(depth_only_path, depth_only_traces)
    _write_csv(breadth_only_path, breadth_only_traces)
    comparator_traces = fixed_traces + depth_only_traces + breadth_only_traces
    all_traces = comparator_traces + heuristic_traces
    summary_rows = _policy_summaries(all_traces)
    _write_csv(summary_path, summary_rows)
    comparison_rows = _primary_policy_comparisons(comparator_traces, heuristic_traces)
    _write_csv(comparison_path, comparison_rows)
    _write_csv(pareto_path, _pareto_rows(summary_rows))
    _write_json(config_output_path, policy_config)
    feature_names = [
        "feature_prompt_token_count",
        "feature_train_tertile_low",
        "feature_train_tertile_high",
        "feature_state1_answer_valid",
        "feature_state1_truncated",
        "feature_state1_actual_tokens",
        "feature_state2_observed",
        "feature_state2_two_valid",
        "feature_state2_answers_match",
    ]
    outcome_names = [
        name
        for name in heuristic_traces[0]
        if name.startswith("outcome_")
    ]
    _write_json(
        schema_path,
        {
            "schema_version": REPLAY_SCHEMA_VERSION,
            "decision_feature_names": feature_names,
            "decision_columns": [
                "decision_selected_L",
                "decision_selected_k",
                "decision_stop_reason",
                "decision_paid_sample_ids",
            ],
            "outcome_columns": outcome_names,
            "forbidden_as_decision_inputs": outcome_names,
            "feature_availability": {
                "before_generation": [
                    "feature_prompt_token_count",
                    "feature_train_tertile_low",
                    "feature_train_tertile_high",
                ],
                "after_paid_sample_1": [
                    "feature_state1_answer_valid",
                    "feature_state1_truncated",
                    "feature_state1_actual_tokens",
                ],
                "after_paid_sample_2": [
                    "feature_state2_two_valid",
                    "feature_state2_answers_match",
                ],
            },
        },
    )
    manifest = {
        "schema_version": REPLAY_SCHEMA_VERSION,
        "artifact_type": "phase2_fixed_and_heuristic_policy_replay",
        "dataset": dataset_name,
        "source_experiment_id": experiment_manifest["experiment_id"],
        "source_model": experiment_manifest["model"],
        "source_model_revision": experiment_manifest["model_revision"],
        "source_prompt_template_name": experiment_manifest["prompt_template_name"],
        "source_answer_parser_name": experiment_manifest["answer_parser_name"],
        "partition": partition,
        "held_out_test_replayed": partition == "test",
        "test_replay_authorized_by_policy_freeze": (
            partition == "test" and policy_freeze is not None
        ),
        "selected_policy_id": (
            policy_freeze.get("selected_policy_id") if policy_freeze else None
        ),
        "problem_count": len(problem_ids),
        "row_counts": {
            "fixed_profile_traces": len(fixed_traces),
            "heuristic_traces": len(heuristic_traces),
            "depth_only_heuristic_traces": len(depth_only_traces),
            "breadth_only_agreement_traces": len(breadth_only_traces),
            "policy_summaries": len(ordered_depths) * len(ordered_breadths)
            + len(ordered_depths)
            + 2,
            "primary_heuristic_comparisons": len(ordered_depths)
            * len(ordered_breadths)
            + len(ordered_depths)
            + 1,
            "pareto_rows": len(ordered_depths) * len(ordered_breadths)
            + len(ordered_depths)
            + 2,
        },
        "fixed_endpoint_reconstruction": "exact",
        "source_hashes": {
            "raw_samples_sha256": file_sha256(raw_path),
            "config_results_sha256": file_sha256(config_path),
            "experiment_manifest_sha256": file_sha256(experiment_manifest_path),
            "split_manifest_sha256": file_sha256(split_manifest_path),
            "train_policy_config_sha256": (
                file_sha256(policy_config_path) if policy_config_path is not None else None
            ),
            "policy_freeze_manifest_sha256": (
                file_sha256(policy_freeze_manifest_path)
                if policy_freeze_manifest_path is not None
                else None
            ),
            "pre_freeze_policy_replay_sha256": (
                policy_freeze.get("software_hashes", {}).get("policy_replay.py")
                if policy_freeze
                else None
            ),
            "execution_policy_replay_sha256": file_sha256(Path(__file__)),
        },
        "artifacts": {
            "fixed_profile_traces": fixed_path.name,
            "fixed_profile_traces_sha256": file_sha256(fixed_path),
            "heuristic_trace": heuristic_path.name,
            "heuristic_trace_sha256": file_sha256(heuristic_path),
            "depth_only_heuristic_trace": depth_only_path.name,
            "depth_only_heuristic_trace_sha256": file_sha256(depth_only_path),
            "breadth_only_agreement_traces": breadth_only_path.name,
            "breadth_only_agreement_traces_sha256": file_sha256(breadth_only_path),
            "policy_summary": summary_path.name,
            "policy_summary_sha256": file_sha256(summary_path),
            "primary_heuristic_comparisons": comparison_path.name,
            "primary_heuristic_comparisons_sha256": file_sha256(comparison_path),
            "policy_pareto": pareto_path.name,
            "policy_pareto_sha256": file_sha256(pareto_path),
            "policy_config": config_output_path.name,
            "policy_config_sha256": file_sha256(config_output_path),
            "trace_schema": schema_path.name,
            "trace_schema_sha256": file_sha256(schema_path),
        },
    }
    _write_json(manifest_path, manifest)
    return manifest
