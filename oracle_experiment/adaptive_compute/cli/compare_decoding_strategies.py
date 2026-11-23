"""Build the paired GSM8K Validation comparison for force-answer decoding."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from adaptive_compute.analysis.decoding_strategy_comparison import (
    compare_dataset_strategies,
    write_decoding_strategy_comparison,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--partition",
        choices=("validation", "test"),
        default="validation",
        help="frozen partition represented by both comparator grids",
    )
    parser.add_argument(
        "--standard-dir",
        type=Path,
        default=Path("results/qwen3_0_6b_gsm8k_validation_n20_contract_v3_parser_v4"),
    )
    parser.add_argument(
        "--force-dir",
        type=Path,
        default=Path("results/qwen3_0_6b_gsm8k_validation_n20_forceanswer_v2"),
    )
    parser.add_argument(
        "--include-math",
        action="store_true",
        help="also compare the registered MATH-500 Validation-20 profiles",
    )
    parser.add_argument(
        "--math-standard-dir",
        type=Path,
        default=Path("results/qwen3_0_6b_math500_validation_n20_contract_v1"),
    )
    parser.add_argument(
        "--math-force-dir",
        type=Path,
        default=Path("results/qwen3_0_6b_math500_validation_n20_forceanswer_v2"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(
            "results/phase2/qwen3_0_6b_gsm8k_forceanswer_validation_comparison_v1"
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    gsm_lengths = (512,) if args.partition == "test" else (512, 1024)
    math_lengths = (1024,) if args.partition == "test" else (1024, 4096)
    rows, source = compare_dataset_strategies(
        dataset="gsm8k",
        standard_dir=args.standard_dir,
        force_dir=args.force_dir,
        lengths=gsm_lengths,
        partition=args.partition,
    )
    sources = [source]
    if args.include_math:
        math_rows, math_source = compare_dataset_strategies(
            dataset="math500",
            standard_dir=args.math_standard_dir,
            force_dir=args.math_force_dir,
            lengths=math_lengths,
            partition=args.partition,
        )
        rows.extend(math_rows)
        sources.append(math_source)
    manifest = write_decoding_strategy_comparison(
        rows=rows,
        sources=sources,
        output_dir=args.output_dir,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
