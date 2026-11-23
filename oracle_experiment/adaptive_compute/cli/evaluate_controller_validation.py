"""Replay the frozen learned-breadth controller on Validation once."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from adaptive_compute.controller.controller_validation import (
    evaluate_frozen_controller_validation,
)
from adaptive_compute.controller.hierarchical_controller import SequentialLabelSource


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--freeze-dir",
        type=Path,
        default=Path("results/phase2/qwen3_0_6b_learned_breadth_validation_freeze_v1"),
    )
    parser.add_argument(
        "--gsm8k-label-dir",
        type=Path,
        default=Path("results/phase2/qwen3_0_6b_gsm8k_validation_n20_sequential_labels_v1"),
    )
    parser.add_argument(
        "--math500-label-dir",
        type=Path,
        default=Path("results/phase2/qwen3_0_6b_math500_validation_n20_sequential_labels_v1"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/phase2/qwen3_0_6b_learned_breadth_validation_replay_v1"),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    manifest = evaluate_frozen_controller_validation(
        freeze_dir=args.freeze_dir,
        validation_sources=(
            SequentialLabelSource("gsm8k", args.gsm8k_label_dir),
            SequentialLabelSource("math500", args.math500_label_dir),
        ),
        output_dir=args.output_dir,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

