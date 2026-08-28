"""Command-line entry point for the Oracle Grid Experiment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from config import (
    GLOBAL_SEED,
    K_VALUES,
    L_VALUES,
    MODEL_ID,
    MODEL_REVISION,
    NUM_PROBLEMS,
    NUM_REPETITIONS,
    TEMPERATURE,
    TOP_P,
    ExperimentConfig,
)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--num-problems", type=int, default=NUM_PROBLEMS)
    parser.add_argument("--k-values", type=int, nargs="+", default=K_VALUES)
    parser.add_argument("--l-values", type=int, nargs="+", default=L_VALUES)
    parser.add_argument("--seed", type=int, default=GLOBAL_SEED)
    parser.add_argument("--num-repetitions", type=int, default=NUM_REPETITIONS)
    parser.add_argument("--temperature", type=float, default=TEMPERATURE)
    parser.add_argument("--top-p", type=float, default=TOP_P)
    parser.add_argument("--model-id", default=MODEL_ID)
    parser.add_argument("--model-revision", default=MODEL_REVISION)
    parser.add_argument("--model-backend", default="transformers")
    parser.add_argument("--results-dir", type=Path, default=Path("results"))
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="validate and print the plan without loading data or a model",
    )
    return parser


def config_from_args(args: argparse.Namespace) -> ExperimentConfig:
    return ExperimentConfig(
        num_problems=args.num_problems,
        model_id=args.model_id,
        model_revision=args.model_revision,
        model_backend=args.model_backend,
        k_values=tuple(args.k_values),
        l_values=tuple(args.l_values),
        temperature=args.temperature,
        top_p=args.top_p,
        global_seed=args.seed,
        num_repetitions=args.num_repetitions,
        results_dir=args.results_dir,
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    config = config_from_args(args)

    if not args.validate_only:
        raise SystemExit(
            "Grid execution is not implemented in Milestone 1. "
            "Use --validate-only to inspect the configuration."
        )

    payload = config.to_dict()
    payload["grid"] = [
        {
            "k": profile.k,
            "L": profile.max_new_tokens,
            "allocated_token_budget": profile.allocated_token_budget,
        }
        for profile in config.grid
    ]
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
