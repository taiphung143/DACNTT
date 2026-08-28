"""Run one real GSM8K generation for Milestone 3 verification."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from config import (
    GLOBAL_SEED,
    MODEL_ID,
    MODEL_REVISION,
    NUM_PROBLEMS,
    TEMPERATURE,
    TOP_P,
)
from dataset import load_gsm8k_subset
from dataset_audit import get_dataset_quality_flag, load_manual_audit
from evaluate import evaluate_response
from logging_utils import write_jsonl
from models.transformers_adapter import TransformersModelAdapter
from prompts import build_gsm8k_prompt


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-id", default=MODEL_ID)
    parser.add_argument("--revision", default=MODEL_REVISION)
    parser.add_argument("--num-problems", type=int, default=NUM_PROBLEMS)
    parser.add_argument("--problem-index", type=int, default=0)
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument("--temperature", type=float, default=TEMPERATURE)
    parser.add_argument("--top-p", type=float, default=TOP_P)
    parser.add_argument("--seed", type=int, default=GLOBAL_SEED)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("results/raw/gsm8k_subset_manifest.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
    )
    return parser


def main() -> int:
    args = build_argument_parser().parse_args()
    problems = load_gsm8k_subset(
        num_problems=args.num_problems,
        seed=args.seed,
        manifest_path=args.manifest,
    )
    if not 0 <= args.problem_index < len(problems):
        raise ValueError("problem-index is outside the selected subset")
    problem = problems[args.problem_index]
    dataset_quality_flag = get_dataset_quality_flag(
        problem.problem_id, load_manual_audit()
    )

    adapter = None
    generation_error: str | None = None
    try:
        adapter = TransformersModelAdapter(
            args.model_id,
            revision=args.revision,
            dtype="bfloat16",
            top_p=args.top_p,
            use_chat_template=True,
            enable_thinking=True,
        )
        generation = adapter.generate(
            build_gsm8k_prompt(problem.question),
            max_new_tokens=args.max_new_tokens,
            temperature=args.temperature,
            seed=args.seed,
        )
        generation_payload = asdict(generation)
        evaluation = evaluate_response(
            generation.text,
            problem.ground_truth,
            finish_reason=generation.finish_reason,
            generated_tokens=generation.generated_tokens,
            max_new_tokens=args.max_new_tokens,
            dataset_quality_flag=dataset_quality_flag,
        )
    except Exception as exc:  # sample-level logging must survive backend failures
        generation_error = f"{type(exc).__name__}: {exc}"
        generation_payload = {
            "text": "",
            "prompt_tokens": 0,
            "generated_tokens": 0,
            "latency_ms": 0.0,
            "finish_reason": "error",
        }
        evaluation = evaluate_response(
            "",
            problem.ground_truth,
            finish_reason="error",
            generated_tokens=0,
            max_new_tokens=args.max_new_tokens,
            generation_error=generation_error,
            dataset_quality_flag=dataset_quality_flag,
        )
    record = {
        "problem_id": problem.problem_id,
        "question": problem.question,
        "dataset": problem.dataset,
        "model": args.model_id,
        "model_revision": (
            adapter.resolved_revision if adapter is not None else None
        )
        or args.revision,
        "k": 1,
        "L": args.max_new_tokens,
        "sample_id": 0,
        "repetition_id": 0,
        "seed": args.seed,
        **generation_payload,
        **asdict(evaluation),
        "ground_truth_raw": problem.ground_truth_raw,
        "generation_error": generation_error,
        "device": str(adapter.device) if adapter is not None else "cuda",
        "dtype": adapter.dtype_name if adapter is not None else "bfloat16",
        "temperature": args.temperature,
        "top_p": args.top_p,
        "enable_thinking": adapter.enable_thinking if adapter is not None else True,
    }
    output = args.output or Path(
        f"results/raw/smoke_L{args.max_new_tokens}_seed{args.seed}.jsonl"
    )
    write_jsonl(output, [record])
    print(json.dumps(record, indent=2, ensure_ascii=False))
    print(f"Saved smoke result to {output}")
    return 1 if generation_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
