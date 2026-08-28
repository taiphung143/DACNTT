"""List records that merit manual experiment or dataset audit."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from logging_utils import read_json_records, write_jsonl


AUDIT_FIELDS = (
    "problem_id",
    "question",
    "ground_truth",
    "majority_answer",
    "agreement",
    "failure_type",
    "dataset_quality_flag",
    "truncated",
    "truncation_stage",
    "parse_error",
    "reasoning_answer",
    "final_response_answer",
    "answer_source",
    "reasoning_final_disagreement",
    "reasoning_correct",
    "final_correct",
)


def select_audit_candidates(
    records: Sequence[Mapping[str, Any]], *, high_agreement: float = 0.9
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for record in records:
        incorrect = record.get("final_correct", record.get("correct")) is False
        agreement = record.get("agreement")
        high_agreement_wrong = (
            incorrect and agreement is not None and float(agreement) >= high_agreement
        )
        if (
            bool(record.get("truncated"))
            or bool(record.get("parse_error"))
            or record.get("dataset_quality_flag") is not None
            or high_agreement_wrong
        ):
            candidates.append({field: record.get(field) for field in AUDIT_FIELDS})
    return candidates


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--high-agreement", type=float, default=0.9)
    args = parser.parse_args()
    candidates = select_audit_candidates(
        read_json_records(args.input), high_agreement=args.high_agreement
    )
    if args.output:
        write_jsonl(args.output, candidates)
        print(f"Wrote {len(candidates)} audit candidates -> {args.output}")
    else:
        for candidate in candidates:
            print(json.dumps(candidate, ensure_ascii=False))
        print(f"Audit candidates: {len(candidates)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
