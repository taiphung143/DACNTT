"""Build sequential marginal-utility labels from a completed development grid."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from adaptive_compute.controller.sequential_data import (
    DEFAULT_LAMBDAS,
    build_sequential_controller_dataset,
)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-dir", type=Path, required=True)
    parser.add_argument("--split-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--lambdas", type=float, nargs="+", default=DEFAULT_LAMBDAS)
    parser.add_argument(
        "--depths",
        type=int,
        nargs="+",
        help="Optional explicit frozen depth action space (auto-detected by dataset).",
    )
    parser.add_argument(
        "--breadths",
        type=int,
        nargs="+",
        help="Optional explicit frozen breadth action space (auto-detected by dataset).",
    )
    parser.add_argument(
        "--token-reference",
        type=int,
        help="Optional explicit frozen utility normalization reference.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    manifest = build_sequential_controller_dataset(
        experiment_dir=args.experiment_dir,
        split_manifest_path=args.split_manifest,
        output_dir=args.output_dir,
        lambdas=tuple(args.lambdas),
        depths=tuple(args.depths) if args.depths else None,
        breadths=tuple(args.breadths) if args.breadths else None,
        token_reference=args.token_reference,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
