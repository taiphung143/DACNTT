"""Run the Train-only pooled hierarchical-controller feasibility study."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from adaptive_compute.controller.hierarchical_controller import (
    DEFAULT_FOLDS,
    DEFAULT_LAMBDA,
    SequentialLabelSource,
    run_hierarchical_controller_feasibility,
)


DEFAULT_GSM8K_LABEL_DIR = Path(
    "results/phase2/qwen3_0_6b_gsm8k_n79_sequential_labels_v1"
)
DEFAULT_MATH500_LABEL_DIR = Path(
    "results/phase2/qwen3_0_6b_math500_train_n80_sequential_labels_v1"
)
DEFAULT_OUTPUT_DIR = Path(
    "results/phase2/qwen3_0_6b_pooled_hierarchical_controller_oof_v5"
)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gsm8k-label-dir", type=Path, default=DEFAULT_GSM8K_LABEL_DIR)
    parser.add_argument("--math500-label-dir", type=Path, default=DEFAULT_MATH500_LABEL_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--lambda-value", type=float, default=DEFAULT_LAMBDA)
    parser.add_argument("--folds", type=int, default=DEFAULT_FOLDS)
    parser.add_argument("--seed", type=int, default=42)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    manifest = run_hierarchical_controller_feasibility(
        sources=(
            SequentialLabelSource("gsm8k", args.gsm8k_label_dir),
            SequentialLabelSource("math500", args.math500_label_dir),
        ),
        output_dir=args.output_dir,
        lambda_value=args.lambda_value,
        folds=args.folds,
        random_seed=args.seed,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
