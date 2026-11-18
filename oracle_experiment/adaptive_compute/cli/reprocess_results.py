"""Re-run deterministic parsing/evaluation on existing JSON or JSONL records."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping
from datetime import datetime, timezone
from dataclasses import asdict
from pathlib import Path
from typing import Any

from adaptive_compute.answer_parser import (
    GSM8K_ANSWER_PARSER_NAME,
    GSM8K_ANSWER_PARSER_NAMES,
    MATH500_ANSWER_PARSER_NAME,
    parse_math500_ground_truth,
)
from adaptive_compute.config import GLOBAL_SEED, MANUAL_AUDIT_PATH, NUM_PROBLEMS
from adaptive_compute.dataset import load_gsm8k_subset
from adaptive_compute.dataset_audit import ManualAuditEntry, get_dataset_quality_flag, load_manual_audit
from adaptive_compute.evaluate import evaluate_response
from adaptive_compute.logging_utils import read_json_records, write_jsonl


def reprocess_record(
    record: Mapping[str, Any],
    *,
    questions: Mapping[str, str] | None = None,
    audit_entries: Mapping[str, ManualAuditEntry] | None = None,
    answer_parser_name: str | None = None,
) -> dict[str, Any]:
    raw_response = str(record.get("raw_response") or record.get("text") or "")
    if "ground_truth" not in record:
        raise ValueError("record is missing ground_truth")
    length = int(record["L"]) if record.get("L") is not None else None
    generated_tokens = (
        int(record["generated_tokens"])
        if record.get("generated_tokens") is not None
        else None
    )
    generation_error = record.get("generation_error") or record.get("error")
    manual_flag = (
        get_dataset_quality_flag(str(record.get("problem_id")), audit_entries)
        if audit_entries is not None
        else None
    )
    quality_flag = manual_flag or record.get("dataset_quality_flag")
    selected_parser = answer_parser_name or str(
        record.get("answer_parser_name", GSM8K_ANSWER_PARSER_NAME)
    )
    ground_truth = str(record["ground_truth"])
    if selected_parser == MATH500_ANSWER_PARSER_NAME and record.get("ground_truth_raw"):
        ground_truth = parse_math500_ground_truth(str(record["ground_truth_raw"]))
    evaluation = evaluate_response(
        raw_response,
        ground_truth,
        finish_reason=record.get("finish_reason"),
        generated_tokens=generated_tokens,
        max_new_tokens=length,
        generation_error=str(generation_error) if generation_error else None,
        dataset_quality_flag=quality_flag,
        answer_parser_name=selected_parser,
    )
    updated = dict(record)
    updated["text"] = str(record.get("text") or raw_response)
    updated.update(asdict(evaluation))
    updated["answer_parser_name"] = selected_parser
    if not updated.get("question") and questions is not None:
        updated["question"] = questions.get(str(record.get("problem_id")))
    updated.setdefault("dataset_quality_flag", None)
    return updated


def reprocess_experiment(
    *,
    source_dir: Path,
    output_dir: Path,
    answer_parser_name: str,
    audit_entries: Mapping[str, ManualAuditEntry],
) -> int:
    """Create a provenance-preserving parser-only derivative experiment."""

    if output_dir.exists():
        raise FileExistsError(f"reprocessed experiment already exists: {output_dir}")
    source_manifest_path = source_dir / "experiment_manifest.json"
    source_raw_path = source_dir / "raw_samples.jsonl"
    if not source_manifest_path.exists() or not source_raw_path.exists():
        raise FileNotFoundError(
            "source experiment must contain experiment_manifest.json and raw_samples.jsonl"
        )
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    source_records = read_json_records(source_raw_path)
    source_experiment_id = str(source_manifest.get("experiment_id", source_dir.name))
    records: list[dict[str, Any]] = []
    for record in source_records:
        updated = reprocess_record(
            record,
            audit_entries=audit_entries,
            answer_parser_name=answer_parser_name,
        )
        updated["source_experiment_id"] = source_experiment_id
        updated["experiment_id"] = output_dir.name
        records.append(updated)

    manifest = dict(source_manifest)
    manifest["experiment_id"] = output_dir.name
    manifest["timestamp"] = datetime.now(timezone.utc).isoformat()
    manifest["answer_parser_name"] = answer_parser_name
    manifest["config"] = dict(source_manifest.get("config", {}))
    manifest["config"]["answer_parser_name"] = answer_parser_name
    manifest["derived_from"] = {
        "experiment_id": source_experiment_id,
        "raw_samples_sha256": hashlib.sha256(source_raw_path.read_bytes()).hexdigest(),
        "transformation": "parser_only_reprocessing",
        "original_prompt_template_name": source_manifest.get("prompt_template_name"),
        "original_answer_parser_name": source_manifest.get("answer_parser_name"),
    }

    output_dir.mkdir(parents=True, exist_ok=False)
    write_jsonl(output_dir / "raw_samples.jsonl", records)
    (output_dir / "experiment_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return len(records)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, nargs="+")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--source-experiment", type=Path)
    parser.add_argument("--output-experiment", type=Path)
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="rebuild analysis artifacts after experiment-directory reprocessing",
    )
    parser.add_argument("--enrich-gsm8k", action="store_true")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("results/raw/gsm8k_subset_manifest.json"),
    )
    parser.add_argument("--num-problems", type=int, default=NUM_PROBLEMS)
    parser.add_argument("--seed", type=int, default=GLOBAL_SEED)
    parser.add_argument("--manual-audit", type=Path, default=MANUAL_AUDIT_PATH)
    parser.add_argument(
        "--answer-parser-name",
        choices=(*GSM8K_ANSWER_PARSER_NAMES, MATH500_ANSWER_PARSER_NAME),
        help="explicitly upgrade all input records to this parser version",
    )
    return parser


def main() -> int:
    args = build_argument_parser().parse_args()
    file_mode = args.input is not None or args.output is not None
    experiment_mode = (
        args.source_experiment is not None or args.output_experiment is not None
    )
    if file_mode == experiment_mode:
        raise ValueError(
            "choose exactly one mode: --input/--output or "
            "--source-experiment/--output-experiment"
        )
    if file_mode and (args.input is None or args.output is None):
        raise ValueError("--input and --output must be supplied together")
    if experiment_mode and (
        args.source_experiment is None or args.output_experiment is None
    ):
        raise ValueError(
            "--source-experiment and --output-experiment must be supplied together"
        )
    if experiment_mode and args.answer_parser_name is None:
        raise ValueError("experiment reprocessing requires --answer-parser-name")
    questions: dict[str, str] | None = None
    if args.enrich_gsm8k:
        problems = load_gsm8k_subset(
            num_problems=args.num_problems,
            seed=args.seed,
            manifest_path=args.manifest,
        )
        questions = {problem.problem_id: problem.question for problem in problems}
    audit_entries = load_manual_audit(args.manual_audit)
    if experiment_mode:
        count = reprocess_experiment(
            source_dir=args.source_experiment,
            output_dir=args.output_experiment,
            answer_parser_name=args.answer_parser_name,
            audit_entries=audit_entries,
        )
        if args.analyze:
            from adaptive_compute.cli.analyze_grid import run_analysis

            run_analysis(args.output_experiment)
        print(f"Reprocessed {count} records -> {args.output_experiment}")
        return 0
    input_records = [
        record for input_path in args.input for record in read_json_records(input_path)
    ]
    records = [
        reprocess_record(
            record,
            questions=questions,
            audit_entries=audit_entries,
            answer_parser_name=args.answer_parser_name,
        )
        for record in input_records
    ]
    write_jsonl(args.output, records)
    print(f"Reprocessed {len(records)} records -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
