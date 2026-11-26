"""Recalculate the paper's final scientific audit from existing artifacts.

This script performs no model generation and does not modify raw experiment
records.  It exports compact, machine-readable checks used by the final paper
revision.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from math import comb
from pathlib import Path
from statistics import fmean
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper" / "audit_outputs"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def truthy(value: Any) -> bool:
    return value is True or str(value).strip().lower() in {"true", "1"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def exact_mcnemar(a_only: int, b_only: int) -> float:
    discordant = a_only + b_only
    if discordant == 0:
        return 1.0
    tail = sum(comb(discordant, index) for index in range(min(a_only, b_only) + 1))
    return min(1.0, 2 * tail / (2**discordant))


def holm(p_values: list[float]) -> list[float]:
    adjusted = [1.0] * len(p_values)
    running = 0.0
    for rank, index in enumerate(sorted(range(len(p_values)), key=p_values.__getitem__)):
        running = max(running, min(1.0, (len(p_values) - rank) * p_values[index]))
        adjusted[index] = running
    return adjusted


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


def historical_verification() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    base = ROOT / "results" / "qwen3_1_7b_gsm8k_n100_r1"
    configs = read_csv(base / "config_results.csv")
    saved = read_csv(base / "paired_comparisons.csv")
    included = [row for row in configs if truthy(row["evaluation_included"])]
    all_rows = configs

    def outcomes(rows: list[dict[str, str]]) -> dict[tuple[int, int], dict[str, bool]]:
        result: dict[tuple[int, int], dict[str, bool]] = defaultdict(dict)
        for row in rows:
            result[(int(row["k"]), int(row["L"]))][row["problem_id"]] = truthy(
                row["final_correct"]
            )
        return result

    observed = outcomes(included)
    checks: list[dict[str, Any]] = []
    by_family: dict[str, list[int]] = defaultdict(list)
    for saved_row in saved:
        a_k, a_l = (int(value) for value in saved_row["profile_a"].split("x"))
        b_k, b_l = (int(value) for value in saved_row["profile_b"].split("x"))
        common = sorted(set(observed[(a_k, a_l)]) & set(observed[(b_k, b_l)]))
        a_only = sum(observed[(a_k, a_l)][pid] and not observed[(b_k, b_l)][pid] for pid in common)
        b_only = sum(not observed[(a_k, a_l)][pid] and observed[(b_k, b_l)][pid] for pid in common)
        p_value = exact_mcnemar(a_only, b_only)
        index = len(checks)
        by_family[saved_row["comparison_family"]].append(index)
        checks.append(
            {
                "family": saved_row["comparison_family"],
                "profile_a": saved_row["profile_a"],
                "profile_b": saved_row["profile_b"],
                "paired_n": len(common),
                "a_only_recomputed": a_only,
                "b_only_recomputed": b_only,
                "exact_p_recomputed": p_value,
                "saved_counts_match": a_only == int(saved_row["a_only_correct"])
                and b_only == int(saved_row["b_only_correct"]),
                "saved_p_matches": abs(p_value - float(saved_row["mcnemar_exact_p"])) < 1e-15,
            }
        )
    for indices in by_family.values():
        adjusted = holm([float(checks[index]["exact_p_recomputed"]) for index in indices])
        for index, value in zip(indices, adjusted, strict=True):
            matching = next(
                row
                for row in saved
                if row["comparison_family"] == checks[index]["family"]
                and row["profile_a"] == checks[index]["profile_a"]
                and row["profile_b"] == checks[index]["profile_b"]
            )
            checks[index]["holm_p_recomputed"] = value
            checks[index]["saved_holm_matches"] = abs(
                value - float(matching["holm_adjusted_p"])
            ) < 1e-15

    sensitivity: list[dict[str, Any]] = []
    for label, rows in (("main_99", included), ("all_manifest_100", all_rows)):
        grouped = outcomes(rows)
        for profile in sorted(grouped):
            values = grouped[profile].values()
            correct = sum(values)
            sensitivity.append(
                {
                    "analysis": label,
                    "profile": f"{profile[0]}x{profile[1]}",
                    "n": len(grouped[profile]),
                    "correct": correct,
                    "accuracy": correct / len(grouped[profile]),
                }
            )
    return checks, sensitivity


def policy_verification(dataset: str, replay_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    summaries = read_csv(replay_dir / "policy_summary.csv")
    fixed = read_csv(replay_dir / "fixed_profile_traces.csv")
    breadth = read_csv(replay_dir / "breadth_only_agreement_traces.csv")
    heuristic = read_csv(replay_dir / "heuristic_trace.csv")
    depth = read_csv(replay_dir / "depth_only_heuristic_trace.csv")
    saved_comparisons = read_csv(replay_dir / "primary_heuristic_comparisons.csv")

    fixed_index = {(row["policy_id"], row["problem_id"]): row for row in fixed}
    equality_rows: list[dict[str, Any]] = []
    for policy_id in sorted({row["policy_id"] for row in breadth}):
        length = int(policy_id.split("_L", 1)[1].split("_", 1)[0])
        adaptive = [row for row in breadth if row["policy_id"] == policy_id]
        prediction_equal = 0
        correctness_equal = 0
        stopped_at_two = 0
        token_differences: list[float] = []
        for row in adaptive:
            comparator = fixed_index[(f"fixed_k4_L{length}", row["problem_id"])]
            prediction_equal += row["outcome_final_answer"] == comparator["outcome_final_answer"]
            correctness_equal += row["outcome_correct"] == comparator["outcome_correct"]
            stopped_at_two += int(row["decision_selected_k"]) == 2
            token_differences.append(
                float(comparator["outcome_actual_generated_tokens"])
                - float(row["outcome_actual_generated_tokens"])
            )
        equality_rows.append(
            {
                "dataset": dataset,
                "policy": policy_id,
                "n": len(adaptive),
                "prediction_equal_n": prediction_equal,
                "correctness_equal_n": correctness_equal,
                "stopped_at_k2_n": stopped_at_two,
                "mean_tokens_saved": fmean(token_differences),
            }
        )

    comparator_rows = fixed + breadth + depth
    comparator_index: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for row in comparator_rows:
        comparator_index[row["policy_id"]][row["problem_id"]] = row
    heuristic_index = {row["problem_id"]: row for row in heuristic}
    recalculated: list[dict[str, Any]] = []
    for saved in saved_comparisons:
        policy = saved["comparator_policy_id"]
        problem_ids = sorted(set(heuristic_index) & set(comparator_index[policy]))
        comparator_only = sum(
            truthy(comparator_index[policy][pid]["outcome_correct"])
            and not truthy(heuristic_index[pid]["outcome_correct"])
            for pid in problem_ids
        )
        heuristic_only = sum(
            not truthy(comparator_index[policy][pid]["outcome_correct"])
            and truthy(heuristic_index[pid]["outcome_correct"])
            for pid in problem_ids
        )
        p_value = exact_mcnemar(comparator_only, heuristic_only)
        recalculated.append(
            {
                "dataset": dataset,
                "comparator": policy,
                "paired_n": len(problem_ids),
                "comparator_only": comparator_only,
                "heuristic_only": heuristic_only,
                "exact_p": p_value,
                "saved_counts_match": comparator_only == int(saved["comparator_only_correct"])
                and heuristic_only == int(saved["heuristic_only_correct"]),
                "saved_p_matches": abs(p_value - float(saved["mcnemar_exact_p"])) < 1e-15,
                "saved_holm_p": float(saved["holm_adjusted_p"]),
            }
        )
    adjusted = holm([float(row["exact_p"]) for row in recalculated])
    for row, value in zip(recalculated, adjusted, strict=True):
        row["holm_p_recomputed"] = value
        row["saved_holm_matches"] = abs(value - float(row["saved_holm_p"])) < 1e-15

    summary = {
        row["policy_id"]: {
            "correct": int(row["correct_count"]),
            "accuracy": float(row["accuracy"]),
            "mean_tokens": float(row["avg_actual_generated_tokens"]),
        }
        for row in summaries
    }
    return equality_rows + recalculated, summary


def raw_outcome_categories(dataset: str, experiment: Path) -> list[dict[str, Any]]:
    rows = read_jsonl(experiment / "raw_samples.jsonl")
    output: list[dict[str, Any]] = []
    for length in sorted({int(row["L"]) for row in rows}):
        selected = [row for row in rows if int(row["L"]) == length]
        categories = defaultdict(int)
        parse_failures = 0
        truncated = 0
        for row in selected:
            stage = row.get("truncation_stage")
            if stage == "during_thinking":
                category = "truncated_during_thinking"
            elif stage == "after_thinking":
                category = "truncated_after_thinking"
            elif row.get("final_response_answer") in (None, ""):
                category = "completed_unparseable"
            else:
                category = "completed_valid_final_answer"
            categories[category] += 1
            parse_failures += int(bool(row.get("parse_error")))
            truncated += int(bool(row.get("truncated")))
        output.append(
            {
                "dataset": dataset,
                "L": length,
                "n": len(selected),
                **categories,
                "exclusive_categories_sum": sum(categories.values()),
                "parse_failure_n_nonexclusive": parse_failures,
                "truncation_n_nonexclusive": truncated,
            }
        )
    return output


def manifest_verification() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name in ("gsm8k_policy_freeze_v1", "math500_policy_freeze_v1"):
        directory = ROOT / "results" / "phase2" / name
        manifest_path = directory / "policy_freeze.json"
        manifest = read_json(manifest_path)
        sidecar = (directory / "policy_freeze.sha256").read_text(encoding="utf-8").split()[0]
        rows.append(
            {
                "manifest": name,
                "artifact": "policy_freeze.json",
                "expected_sha256": sidecar,
                "actual_sha256": sha256(manifest_path),
                "matches": sidecar == sha256(manifest_path),
                "freeze_date": manifest["freeze_date"],
            }
        )
        for artifact_name, artifact_path in manifest["frozen_artifacts"].items():
            if not artifact_name.endswith("_sha256"):
                continue
            stem = artifact_name.removesuffix("_sha256")
            filename = manifest["frozen_artifacts"][stem]
            target = directory / filename
            rows.append(
                {
                    "manifest": name,
                    "artifact": filename,
                    "expected_sha256": artifact_path,
                    "actual_sha256": sha256(target),
                    "matches": artifact_path == sha256(target),
                    "freeze_date": manifest["freeze_date"],
                }
            )
    for name in (
        "qwen3_0_6b_gsm8k_test_n100_policy_replay_v3",
        "qwen3_0_6b_math500_test_n100_baseline_replay_v1",
    ):
        directory = ROOT / "results" / "phase2" / name
        manifest = read_json(directory / "replay_manifest.json")
        for key, expected in manifest["artifacts"].items():
            if not key.endswith("_sha256"):
                continue
            filename = manifest["artifacts"][key.removesuffix("_sha256")]
            target = directory / filename
            rows.append(
                {
                    "manifest": name,
                    "artifact": filename,
                    "expected_sha256": expected,
                    "actual_sha256": sha256(target),
                    "matches": expected == sha256(target),
                    "freeze_date": "replay artifact",
                }
            )
    return rows


def supplementary_control_verification() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    specifications = (
        (
            ROOT / "results" / "phase2" / "qwen3_0_6b_forceanswer_test_comparison_v1",
            "paired_decoding_strategy_comparison.csv",
            "standard",
            "force_answer",
            "standard_only_correct",
            "force_only_correct",
            "standard_correct",
            "force_correct",
            "holm_adjusted_p_within_dataset",
        ),
        (
            ROOT / "results" / "phase2" / "qwen3_0_6b_nonthinking_validation_comparison_v1",
            "paired_thinking_mode_comparison.csv",
            "thinking",
            "nonthinking",
            "thinking_only_correct",
            "nonthinking_only_correct",
            "thinking_correct",
            "nonthinking_correct",
            "holm_adjusted_p_within_dataset",
        ),
    )
    checks: list[dict[str, Any]] = []
    source_hashes: list[dict[str, Any]] = []
    for (
        directory,
        table_name,
        left_name,
        right_name,
        left_only_name,
        right_only_name,
        left_correct_name,
        right_correct_name,
        holm_name,
    ) in specifications:
        manifest = read_json(directory / "comparison_manifest.json")
        table = read_csv(directory / table_name)
        sources = {source["dataset"]: source for source in manifest["sources"]}
        cache: dict[tuple[str, str], list[dict[str, str]]] = {}
        family_indices: dict[str, list[int]] = defaultdict(list)
        for source in manifest["sources"]:
            for strategy in (left_name, right_name):
                relative = Path(str(source[strategy]["path"]).replace("\\", "/"))
                source_dir = ROOT / relative
                for filename, expected in (
                    ("experiment_manifest.json", source[strategy]["experiment_manifest_sha256"]),
                    ("config_results.csv", source[strategy]["config_results_sha256"]),
                    ("raw_samples.jsonl", source[strategy]["raw_samples_sha256"]),
                ):
                    target = source_dir / filename
                    actual = sha256(target)
                    source_hashes.append(
                        {
                            "control": directory.name,
                            "dataset": source["dataset"],
                            "strategy": strategy,
                            "artifact": str(target.relative_to(ROOT)),
                            "expected_sha256": expected,
                            "actual_sha256": actual,
                            "matches": expected == actual,
                        }
                    )
                cache[(source["dataset"], strategy)] = read_csv(source_dir / "config_results.csv")

        for saved in table:
            dataset = saved["dataset"]
            k = int(saved["k"])
            length = int(saved["L"])
            left = {
                row["problem_id"]: row
                for row in cache[(dataset, left_name)]
                if int(row["k"]) == k and int(row["L"]) == length
            }
            right = {
                row["problem_id"]: row
                for row in cache[(dataset, right_name)]
                if int(row["k"]) == k and int(row["L"]) == length
            }
            problem_ids = sorted(set(left) & set(right))
            left_values = [truthy(left[pid]["final_correct"]) for pid in problem_ids]
            right_values = [truthy(right[pid]["final_correct"]) for pid in problem_ids]
            left_only = sum(a and not b for a, b in zip(left_values, right_values, strict=True))
            right_only = sum(not a and b for a, b in zip(left_values, right_values, strict=True))
            p_value = exact_mcnemar(left_only, right_only)
            family_indices[dataset].append(len(checks))
            checks.append(
                {
                    "control": directory.name,
                    "dataset": dataset,
                    "k": k,
                    "L": length,
                    "paired_n": len(problem_ids),
                    "left_correct_recomputed": sum(left_values),
                    "right_correct_recomputed": sum(right_values),
                    "left_only_recomputed": left_only,
                    "right_only_recomputed": right_only,
                    "exact_p_recomputed": p_value,
                    "saved_counts_match": sum(left_values) == int(saved[left_correct_name])
                    and sum(right_values) == int(saved[right_correct_name])
                    and left_only == int(saved[left_only_name])
                    and right_only == int(saved[right_only_name]),
                    "saved_p_matches": abs(p_value - float(saved["mcnemar_exact_p"])) < 1e-15,
                    "saved_holm_p": float(saved[holm_name]),
                }
            )
        for indices in family_indices.values():
            adjusted = holm([float(checks[index]["exact_p_recomputed"]) for index in indices])
            for index, value in zip(indices, adjusted, strict=True):
                checks[index]["holm_p_recomputed"] = value
                checks[index]["saved_holm_matches"] = abs(
                    value - float(checks[index]["saved_holm_p"])
                ) < 1e-15
    return checks, source_hashes


def main() -> int:
    historical, sensitivity = historical_verification()
    gsm_dir = ROOT / "results" / "phase2" / "qwen3_0_6b_gsm8k_test_n100_policy_replay_v3"
    math_dir = ROOT / "results" / "phase2" / "qwen3_0_6b_math500_test_n100_baseline_replay_v1"
    gsm_checks, gsm_summary = policy_verification("gsm8k", gsm_dir)
    math_checks, math_summary = policy_verification("math500", math_dir)
    categories = raw_outcome_categories(
        "gsm8k", ROOT / "results" / "qwen3_0_6b_gsm8k_test_n100_contract_v3"
    ) + raw_outcome_categories(
        "math500", ROOT / "results" / "qwen3_0_6b_math500_test_n100_contract_v1"
    )
    manifests = manifest_verification()
    supplementary, supplementary_hashes = supplementary_control_verification()

    write_csv(OUTPUT / "historical_paired_verification.csv", historical)
    write_csv(OUTPUT / "historical_exclusion_sensitivity.csv", sensitivity)
    write_csv(OUTPUT / "primary_policy_verification.csv", gsm_checks + math_checks)
    write_csv(OUTPUT / "raw_outcome_categories.csv", categories)
    write_csv(OUTPUT / "freeze_hash_verification.csv", manifests)
    write_csv(OUTPUT / "supplementary_control_verification.csv", supplementary)
    write_csv(OUTPUT / "supplementary_source_hash_verification.csv", supplementary_hashes)

    report = {
        "audit_scope": "existing artifacts only; no LLM generation",
        "historical_pair_rows_verified": len(historical),
        "historical_all_saved_values_match": all(
            row["saved_counts_match"] and row["saved_p_matches"] and row["saved_holm_matches"]
            for row in historical
        ),
        "all_primary_policy_statistics_match": all(
            row.get("saved_counts_match", True)
            and row.get("saved_p_matches", True)
            and row.get("saved_holm_matches", True)
            for row in gsm_checks + math_checks
        ),
        "all_breadth_predictions_equal_fixed_k4": all(
            row["prediction_equal_n"] == row["n"]
            for row in gsm_checks + math_checks
            if "prediction_equal_n" in row
        ),
        "all_freeze_artifact_hashes_match": all(row["matches"] for row in manifests),
        "all_supplementary_statistics_match": all(
            row["saved_counts_match"] and row["saved_p_matches"] and row["saved_holm_matches"]
            for row in supplementary
        ),
        "all_supplementary_source_hashes_match": all(
            row["matches"] for row in supplementary_hashes
        ),
        "raw_category_rows_sum_to_400": all(
            row["n"] == 400 and row["exclusive_categories_sum"] == 400 for row in categories
        ),
        "gsm8k_policy_summary": gsm_summary,
        "math500_policy_summary": math_summary,
    }
    (OUTPUT / "audit_summary.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
