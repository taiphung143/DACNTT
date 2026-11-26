"""Freeze the OOF-selected learned-breadth controller before Validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from adaptive_compute.controller.controller_validation import (
    build_controller_validation_freeze,
)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--feasibility-dir",
        type=Path,
        default=Path("results/phase2/qwen3_0_6b_pooled_hierarchical_controller_oof_v5"),
    )
    parser.add_argument(
        "--gsm8k-split-manifest",
        type=Path,
        default=Path("data/splits/phase2_gsm8k_split_v1.json"),
    )
    parser.add_argument(
        "--math500-split-manifest",
        type=Path,
        default=Path("data/splits/math500_split_v1.json"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/phase2/qwen3_0_6b_learned_breadth_validation_freeze_v1"),
    )
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    manifest = build_controller_validation_freeze(
        feasibility_dir=args.feasibility_dir,
        gsm8k_split_manifest=args.gsm8k_split_manifest,
        math500_split_manifest=args.math500_split_manifest,
        output_dir=args.output_dir,
        repository_root=args.repository_root.resolve(),
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

