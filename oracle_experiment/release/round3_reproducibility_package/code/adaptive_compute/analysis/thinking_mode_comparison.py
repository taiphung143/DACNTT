"""Paired Validation comparison between Qwen thinking and non-thinking modes."""

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


def _load_experiment(path: Path, *, length: int) -> dict[str, Any]:
    manifest_path = path / "experiment_manifest.json"
    config_path = path / "config_results.csv"
    raw_path = path / "raw_samples.jsonl"
    for required in (manifest_path, config_path, raw_path):
        if not required.is_file():
            raise FileNotFoundError(f"missing comparison input: {required}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    config_rows = [
        row
        for row in _read_csv(config_path)
        if int(row["L"]) == length and _truthy(row.get("evaluation_included", True))
    ]
    raw_rows = [row for row in _read_jsonl(raw_path) if int(row["L"]) == length]
    config_keys = [
        (str(row["problem_id"]), int(row["k"]), int(row.get("repetition_id", 0)))
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


def compare_dataset_modes(
    *,
    dataset: str,
    thinking_dir: Path,
    nonthinking_dir: Path,
    length: int,
    k_values: Sequence[int] = (1, 2, 4),
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return paired policy rows and an auditable source record."""

    thinking = _load_experiment(thinking_dir, length=length)
    nonthinking = _load_experiment(nonthinking_dir, length=length)
    tm = thinking["manifest"]
    nm = nonthinking["manifest"]
    for field in ("model", "model_revision", "dataset_partition", "problem_ids"):
        if tm.get(field) != nm.get(field):
            raise ValueError(f"thinking/non-thinking manifest mismatch for {field}")
    if tm.get("dataset_partition") != "validation":
        raise ValueError("thinking-mode comparison is restricted to Validation")
    if not bool(tm.get("enable_thinking")) or bool(nm.get("enable_thinking")):
        raise ValueError("invalid thinking-mode flags")
    if tm.get("prompt_hash") != nm.get("prompt_hash"):
        raise ValueError("comparison requires byte-identical prompts")

    rows: list[dict[str, Any]] = []
    for k in k_values:
        t_rows = {
            (str(row["problem_id"]), int(row.get("repetition_id", 0))): row
            for row in thinking["config_rows"]
            if int(row["k"]) == k
        }
        n_rows = {
            (str(row["problem_id"]), int(row.get("repetition_id", 0))): row
            for row in nonthinking["config_rows"]
            if int(row["k"]) == k
        }
        if set(t_rows) != set(n_rows) or len(t_rows) != len(tm["problem_ids"]):
            raise ValueError(f"paired unit mismatch for {dataset}, k={k}")
        units = sorted(t_rows)
        t_correct = [_truthy(t_rows[unit]["final_correct"]) for unit in units]
        n_correct = [_truthy(n_rows[unit]["final_correct"]) for unit in units]
        total = len(units)
        t_successes = sum(t_correct)
        n_successes = sum(n_correct)
        t_only = sum(t and not n for t, n in zip(t_correct, n_correct, strict=True))
        n_only = sum(n and not t for t, n in zip(t_correct, n_correct, strict=True))
        t_tokens = mean(float(t_rows[unit]["actual_generated_tokens"]) for unit in units)
        n_tokens = mean(float(n_rows[unit]["actual_generated_tokens"]) for unit in units)
        t_ci = wilson_interval(t_successes, total)
        n_ci = wilson_interval(n_successes, total)

        t_samples = [row for row in thinking["raw_rows"] if int(row["sample_id"]) < k]
        n_samples = [row for row in nonthinking["raw_rows"] if int(row["sample_id"]) < k]
        expected_samples = total * k
        if len(t_samples) != expected_samples or len(n_samples) != expected_samples:
            raise ValueError(f"sample count mismatch for {dataset}, k={k}")
        rows.append(
            {
                "dataset": dataset,
                "k": k,
                "L": length,
                "problems": total,
                "thinking_correct": t_successes,
                "thinking_accuracy": t_successes / total,
                "thinking_ci95_low": t_ci[0],
                "thinking_ci95_high": t_ci[1],
                "thinking_mean_tokens": t_tokens,
                "thinking_parse_failure_rate": mean(bool(row["parse_error"]) for row in t_samples),
                "thinking_truncation_rate": mean(bool(row["truncated"]) for row in t_samples),
                "nonthinking_correct": n_successes,
                "nonthinking_accuracy": n_successes / total,
                "nonthinking_ci95_low": n_ci[0],
                "nonthinking_ci95_high": n_ci[1],
                "nonthinking_mean_tokens": n_tokens,
                "nonthinking_parse_failure_rate": mean(bool(row["parse_error"]) for row in n_samples),
                "nonthinking_truncation_rate": mean(bool(row["truncated"]) for row in n_samples),
                "accuracy_gap_nonthinking_minus_thinking": (n_successes - t_successes) / total,
                "token_saving_nonthinking_vs_thinking": 1.0 - n_tokens / t_tokens,
                "both_correct": sum(t and n for t, n in zip(t_correct, n_correct, strict=True)),
                "both_wrong": sum(not t and not n for t, n in zip(t_correct, n_correct, strict=True)),
                "thinking_only_correct": t_only,
                "nonthinking_only_correct": n_only,
                "mcnemar_exact_p": exact_mcnemar_p(t_only, n_only),
            }
        )
    adjusted = holm_adjust([float(row["mcnemar_exact_p"]) for row in rows])
    for row, adjusted_p in zip(rows, adjusted, strict=True):
        row["holm_adjusted_p_within_dataset"] = adjusted_p
    source = {
        "dataset": dataset,
        "L": length,
        "thinking": {"path": str(thinking_dir), **thinking["hashes"]},
        "nonthinking": {"path": str(nonthinking_dir), **nonthinking["hashes"]},
        "model": tm["model"],
        "model_revision": tm["model_revision"],
        "partition": tm["dataset_partition"],
        "problem_ids": tm["problem_ids"],
        "prompt_hash": tm["prompt_hash"],
        "thinking_parser": tm["answer_parser_name"],
        "nonthinking_parser": nm["answer_parser_name"],
    }
    return rows, source


def write_thinking_mode_comparison(
    *, rows: Sequence[Mapping[str, Any]], sources: Sequence[Mapping[str, Any]], output_dir: Path
) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"comparison output already exists: {output_dir}")
    output_dir.mkdir(parents=True)
    csv_path = output_dir / "paired_thinking_mode_comparison.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    report_lines = [
        "# Thinking versus non-thinking: frozen Validation comparison",
        "",
        "This is paired supplementary development evidence on the same Validation-20 items. "
        "It does not modify the frozen Test-100 claims.",
        "",
        "| Dataset | k,L | Thinking | Non-thinking | Accuracy gap | Token saving | McNemar p | Holm p |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        report_lines.append(
            f"| {row['dataset']} | {row['k']}x{row['L']} | "
            f"{row['thinking_correct']}/{row['problems']} ({100*float(row['thinking_accuracy']):.1f}%), "
            f"{float(row['thinking_mean_tokens']):.2f} tok | "
            f"{row['nonthinking_correct']}/{row['problems']} ({100*float(row['nonthinking_accuracy']):.1f}%), "
            f"{float(row['nonthinking_mean_tokens']):.2f} tok | "
            f"{100*float(row['accuracy_gap_nonthinking_minus_thinking']):+.1f} pp | "
            f"{100*float(row['token_saving_nonthinking_vs_thinking']):.1f}% | "
            f"{float(row['mcnemar_exact_p']):.4g} | "
            f"{float(row['holm_adjusted_p_within_dataset']):.4g} |"
        )
    report_lines.extend(
        [
            "",
            "Holm adjustment is applied across k={1,2,4} separately within each dataset. "
            "Failure to reject is not evidence of equivalence.",
        ]
    )
    report_path = output_dir / "comparison_report.md"
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "artifact_type": "paired_thinking_mode_validation_comparison",
        "development_only": True,
        "held_out_test_used": False,
        "sources": list(sources),
        "artifacts": {
            "paired_comparison": csv_path.name,
            "paired_comparison_sha256": _sha256(csv_path),
            "report": report_path.name,
            "report_sha256": _sha256(report_path),
        },
    }
    manifest_path = output_dir / "comparison_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest
