"""Build the frozen paired Validation comparison for thinking modes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from adaptive_compute.analysis.thinking_mode_comparison import (
    compare_dataset_modes,
    write_thinking_mode_comparison,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gsm-thinking-dir",
        type=Path,
        default=Path("results/qwen3_0_6b_gsm8k_validation_n20_contract_v3_parser_v4"),
    )
    parser.add_argument(
        "--gsm-nonthinking-dir",
        type=Path,
        default=Path("results/qwen3_0_6b_gsm8k_validation_n20_nonthinking_highL_v1"),
    )
    parser.add_argument(
        "--math-thinking-dir",
        type=Path,
        default=Path("results/qwen3_0_6b_math500_validation_n20_contract_v1"),
    )
    parser.add_argument(
        "--math-nonthinking-dir",
        type=Path,
        default=Path("results/qwen3_0_6b_math500_validation_n20_nonthinking_highL_v1"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/phase2/qwen3_0_6b_nonthinking_validation_comparison_v1"),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    gsm_rows, gsm_source = compare_dataset_modes(
        dataset="gsm8k",
        thinking_dir=args.gsm_thinking_dir,
        nonthinking_dir=args.gsm_nonthinking_dir,
        length=2048,
    )
    math_rows, math_source = compare_dataset_modes(
        dataset="math500",
        thinking_dir=args.math_thinking_dir,
        nonthinking_dir=args.math_nonthinking_dir,
        length=4096,
    )
    manifest = write_thinking_mode_comparison(
        rows=[*gsm_rows, *math_rows],
        sources=[gsm_source, math_source],
        output_dir=args.output_dir,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
