"""Paired Validation comparison of standard and force-answer decoding."""

from __future__ import annotations

import csv
import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from statistics import mean
from typing import Any

from adaptive_compute.analysis.statistics import exact_mcnemar_p, holm_adjust, wilson_interval


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _truthy(value: Any) -> bool:
    return value is True or str(value).lower() == "true"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at {path}:{line_number}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"non-object JSONL row at {path}:{line_number}")
            rows.append(row)
    return rows


def _load_experiment(path: Path, *, lengths: Sequence[int]) -> dict[str, Any]:
    manifest_path = path / "experiment_manifest.json"
    config_path = path / "config_results.csv"
    raw_path = path / "raw_samples.jsonl"
    for required in (manifest_path, config_path, raw_path):
        if not required.is_file():
            raise FileNotFoundError(f"missing comparison input: {required}")
    selected_lengths = set(lengths)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    config_rows = [
        row
        for row in _read_csv(config_path)
        if int(row["L"]) in selected_lengths and _truthy(row.get("evaluation_included", True))
    ]
    raw_rows = [row for row in _read_jsonl(raw_path) if int(row["L"]) in selected_lengths]
    config_keys = [
        (str(row["problem_id"]), int(row["k"]), int(row["L"]), int(row.get("repetition_id", 0)))
        for row in config_rows
    ]
    raw_keys = [
        (
            str(row["problem_id"]),
            int(row["L"]),
            int(row["sample_id"]),
            int(row.get("repetition_id", 0)),
        )
        for row in raw_rows
    ]
    if len(config_keys) != len(set(config_keys)):
        raise ValueError(f"duplicate config identity in {path}")
    if len(raw_keys) != len(set(raw_keys)):
        raise ValueError(f"duplicate raw identity in {path}")
    if any(row.get("generation_error") for row in raw_rows):
        raise ValueError(f"generation error present in {path}")
    return {
        "path": path,
        "manifest": manifest,
        "config_rows": config_rows,
        "raw_rows": raw_rows,
        "hashes": {
            "experiment_manifest_sha256": _sha256(manifest_path),
            "config_results_sha256": _sha256(config_path),
            "raw_samples_sha256": _sha256(raw_path),
        },
    }


def compare_dataset_strategies(
    *,
    dataset: str,
    standard_dir: Path,
    force_dir: Path,
    lengths: Sequence[int],
    k_values: Sequence[int] = (1, 2, 4),
    partition: str = "validation",
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return paired policy comparisons and an auditable source record."""

    standard = _load_experiment(standard_dir, lengths=lengths)
    forced = _load_experiment(force_dir, lengths=lengths)
    sm = standard["manifest"]
    fm = forced["manifest"]
    for field in (
        "model",
        "model_revision",
        "dataset_partition",
        "problem_ids",
        "global_seed",
        "sample_seed_policy",
        "temperature",
        "top_p",
    ):
        if sm.get(field) != fm.get(field):
            raise ValueError(f"standard/force-answer manifest mismatch for {field}")
    if partition not in {"validation", "test"}:
        raise ValueError("partition must be validation or test")
    if sm.get("dataset_partition") != partition:
        raise ValueError(f"decoding-strategy comparison requires {partition} inputs")
    if not bool(sm.get("enable_thinking")) or not bool(fm.get("enable_thinking")):
        raise ValueError("both decoding strategies must use thinking mode")
    if sm.get("prompt_hash") != fm.get("prompt_hash"):
        raise ValueError("comparison requires byte-identical prompts")
    if sm.get("answer_parser_name") != fm.get("answer_parser_name"):
        raise ValueError("comparison requires the same answer parser")
    if sm.get("decoding_strategy") not in (None, "standard"):
        raise ValueError("standard input is not standard decoding")
    if fm.get("decoding_strategy") != "force_answer":
        raise ValueError("force input is not force-answer decoding")
    if fm.get("decoding_strategy_version") != "force_answer_v2":
        raise ValueError("comparison requires force_answer_v2")

    standard_raw = {
        (
            str(row["problem_id"]),
            int(row["L"]),
            int(row["sample_id"]),
            int(row.get("repetition_id", 0)),
        ): row
        for row in standard["raw_rows"]
    }
    forced_raw = {
        (
            str(row["problem_id"]),
            int(row["L"]),
            int(row["sample_id"]),
            int(row.get("repetition_id", 0)),
        ): row
        for row in forced["raw_rows"]
    }
    if set(standard_raw) != set(forced_raw):
        raise ValueError("raw generation identities do not match")
    for key in standard_raw:
        if standard_raw[key].get("seed") != forced_raw[key].get("seed"):
            raise ValueError(f"sample seed mismatch for {key}")
        if standard_raw[key].get("prompt_hash") != forced_raw[key].get("prompt_hash"):
            raise ValueError(f"row-level prompt mismatch for {key}")

    rows: list[dict[str, Any]] = []
    for length in lengths:
        for k in k_values:
            standard_configs = {
                (str(row["problem_id"]), int(row.get("repetition_id", 0))): row
                for row in standard["config_rows"]
                if int(row["L"]) == length and int(row["k"]) == k
            }
            forced_configs = {
                (str(row["problem_id"]), int(row.get("repetition_id", 0))): row
                for row in forced["config_rows"]
                if int(row["L"]) == length and int(row["k"]) == k
            }
            if set(standard_configs) != set(forced_configs):
                raise ValueError(f"paired unit mismatch for {dataset}, k={k}, L={length}")
            if len(standard_configs) != len(sm["problem_ids"]):
                raise ValueError(f"incomplete paired units for {dataset}, k={k}, L={length}")
            units = sorted(standard_configs)
            standard_correct = [_truthy(standard_configs[unit]["final_correct"]) for unit in units]
            forced_correct = [_truthy(forced_configs[unit]["final_correct"]) for unit in units]
            total = len(units)
            standard_successes = sum(standard_correct)
            forced_successes = sum(forced_correct)
            standard_only = sum(
                s and not f for s, f in zip(standard_correct, forced_correct, strict=True)
            )
            forced_only = sum(
                f and not s for s, f in zip(standard_correct, forced_correct, strict=True)
            )
            standard_tokens = mean(
                float(standard_configs[unit]["actual_generated_tokens"]) for unit in units
            )
            forced_tokens = mean(
                float(forced_configs[unit]["actual_generated_tokens"]) for unit in units
            )
            standard_ci = wilson_interval(standard_successes, total)
            forced_ci = wilson_interval(forced_successes, total)
            standard_samples = [
                row
                for key, row in standard_raw.items()
                if key[1] == length and key[2] < k
            ]
            forced_samples = [
                row for key, row in forced_raw.items() if key[1] == length and key[2] < k
            ]
            expected_samples = total * k
            if len(standard_samples) != expected_samples or len(forced_samples) != expected_samples:
                raise ValueError(f"sample count mismatch for {dataset}, k={k}, L={length}")
            rows.append(
                {
                    "dataset": dataset,
                    "k": k,
                    "L": length,
                    "problems": total,
                    "standard_correct": standard_successes,
                    "standard_accuracy": standard_successes / total,
                    "standard_ci95_low": standard_ci[0],
                    "standard_ci95_high": standard_ci[1],
                    "standard_mean_tokens": standard_tokens,
                    "standard_parse_failure_rate": mean(
                        bool(row["parse_error"]) for row in standard_samples
                    ),
                    "standard_truncation_rate": mean(
                        bool(row["truncated"]) for row in standard_samples
                    ),
                    "force_correct": forced_successes,
                    "force_accuracy": forced_successes / total,
                    "force_ci95_low": forced_ci[0],
                    "force_ci95_high": forced_ci[1],
                    "force_mean_tokens": forced_tokens,
                    "force_parse_failure_rate": mean(
                        bool(row["parse_error"]) for row in forced_samples
                    ),
                    "force_truncation_rate": mean(
                        bool(row["truncated"]) for row in forced_samples
                    ),
                    "force_transition_rate": mean(
                        bool(row.get("forced_transition", False)) for row in forced_samples
                    ),
                    "accuracy_gap_force_minus_standard": (
                        forced_successes - standard_successes
                    )
                    / total,
                    "token_saving_force_vs_standard": 1.0 - forced_tokens / standard_tokens,
                    "both_correct": sum(
                        s and f for s, f in zip(standard_correct, forced_correct, strict=True)
                    ),
                    "both_wrong": sum(
                        not s and not f
                        for s, f in zip(standard_correct, forced_correct, strict=True)
                    ),
                    "standard_only_correct": standard_only,
                    "force_only_correct": forced_only,
                    "mcnemar_exact_p": exact_mcnemar_p(standard_only, forced_only),
                }
            )
    adjusted = holm_adjust([float(row["mcnemar_exact_p"]) for row in rows])
    for row, adjusted_p in zip(rows, adjusted, strict=True):
        row["holm_adjusted_p_within_dataset"] = adjusted_p
    source = {
        "dataset": dataset,
        "lengths": list(lengths),
        "standard": {"path": str(standard_dir), **standard["hashes"]},
        "force_answer": {"path": str(force_dir), **forced["hashes"]},
        "model": sm["model"],
        "model_revision": sm["model_revision"],
        "partition": sm["dataset_partition"],
        "problem_ids": sm["problem_ids"],
        "prompt_hash": sm["prompt_hash"],
        "answer_parser": sm["answer_parser_name"],
        "force_answer_version": fm["decoding_strategy_version"],
        "answer_reserve_tokens": fm["answer_reserve_tokens"],
    }
    return rows, source


def write_decoding_strategy_comparison(
    *, rows: Sequence[Mapping[str, Any]], sources: Sequence[Mapping[str, Any]], output_dir: Path
) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"comparison output already exists: {output_dir}")
    if not rows:
        raise ValueError("comparison rows cannot be empty")
    partitions = {str(source["partition"]) for source in sources}
    if len(partitions) != 1:
        raise ValueError("all comparison sources must use one partition")
    partition = next(iter(partitions))
    partition_label = "Test" if partition == "test" else "Validation"
    output_dir.mkdir(parents=True)
    csv_path = output_dir / "paired_decoding_strategy_comparison.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    report_lines = [
        f"# Standard versus force-answer: frozen {partition_label} comparison",
        "",
        f"This is paired supplementary evidence on the same {partition_label} items, sample "
        "seeds, prompts, and parser. The primary thesis results remain unchanged.",
        "",
        "| Dataset | k,L | Standard | Force-answer | Accuracy gap | Token saving | Parse fail S/F | Trunc. S/F | McNemar p | Holm p |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        report_lines.append(
            f"| {row['dataset']} | {row['k']}x{row['L']} | "
            f"{row['standard_correct']}/{row['problems']} ({100*float(row['standard_accuracy']):.1f}%), "
            f"{float(row['standard_mean_tokens']):.2f} tok | "
            f"{row['force_correct']}/{row['problems']} ({100*float(row['force_accuracy']):.1f}%), "
            f"{float(row['force_mean_tokens']):.2f} tok | "
            f"{100*float(row['accuracy_gap_force_minus_standard']):+.1f} pp | "
            f"{100*float(row['token_saving_force_vs_standard']):+.1f}% | "
            f"{100*float(row['standard_parse_failure_rate']):.1f}%/"
            f"{100*float(row['force_parse_failure_rate']):.1f}% | "
            f"{100*float(row['standard_truncation_rate']):.1f}%/"
            f"{100*float(row['force_truncation_rate']):.1f}% | "
            f"{float(row['mcnemar_exact_p']):.4g} | "
            f"{float(row['holm_adjusted_p_within_dataset']):.4g} |"
        )
    report_lines.extend(
        [
            "",
            "Holm adjustment is applied across all registered (k,L) profiles within the dataset. "
            "Failure to reject is not evidence of equivalence or non-inferiority.",
        ]
    )
    report_path = output_dir / "comparison_report.md"
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "artifact_type": f"paired_decoding_strategy_{partition}_comparison",
        "development_only": True,
        "held_out_test_used": partition == "test",
        "sources": list(sources),
        "artifacts": {
            "paired_comparison": csv_path.name,
            "paired_comparison_sha256": _sha256(csv_path),
            "report": report_path.name,
            "report_sha256": _sha256(report_path),
        },
    }
    manifest_path = output_dir / "comparison_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest
