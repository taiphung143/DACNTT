"""Re-run deterministic parsing/evaluation on existing JSON or JSONL records."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import asdict
from pathlib import Path
from typing import Any

from config import GLOBAL_SEED, MANUAL_AUDIT_PATH, NUM_PROBLEMS
from dataset import load_gsm8k_subset
from dataset_audit import ManualAuditEntry, get_dataset_quality_flag, load_manual_audit
from evaluate import evaluate_response
from logging_utils import read_json_records, write_jsonl


def reprocess_record(
    record: Mapping[str, Any],
    *,
    questions: Mapping[str, str] | None = None,
    audit_entries: Mapping[str, ManualAuditEntry] | None = None,
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
    evaluation = evaluate_response(
        raw_response,
        str(record["ground_truth"]),
        finish_reason=record.get("finish_reason"),
        generated_tokens=generated_tokens,
        max_new_tokens=length,
        generation_error=str(generation_error) if generation_error else None,
        dataset_quality_flag=quality_flag,
    )
    updated = dict(record)
    updated["text"] = str(record.get("text") or raw_response)
    updated.update(asdict(evaluation))
    if not updated.get("question") and questions is not None:
        updated["question"] = questions.get(str(record.get("problem_id")))
    updated.setdefault("dataset_quality_flag", None)
    return updated


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--enrich-gsm8k", action="store_true")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("results/raw/gsm8k_subset_manifest.json"),
    )
    parser.add_argument("--num-problems", type=int, default=NUM_PROBLEMS)
    parser.add_argument("--seed", type=int, default=GLOBAL_SEED)
    parser.add_argument("--manual-audit", type=Path, default=MANUAL_AUDIT_PATH)
    return parser


def main() -> int:
    args = build_argument_parser().parse_args()
    questions: dict[str, str] | None = None
    if args.enrich_gsm8k:
        problems = load_gsm8k_subset(
            num_problems=args.num_problems,
            seed=args.seed,
            manifest_path=args.manifest,
        )
        questions = {problem.problem_id: problem.question for problem in problems}
    audit_entries = load_manual_audit(args.manual_audit)
    input_records = [
        record for input_path in args.input for record in read_json_records(input_path)
    ]
    records = [
        reprocess_record(
            record, questions=questions, audit_entries=audit_entries
        )
        for record in input_records
    ]
    write_jsonl(args.output, records)
    print(f"Reprocessed {len(records)} records -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
