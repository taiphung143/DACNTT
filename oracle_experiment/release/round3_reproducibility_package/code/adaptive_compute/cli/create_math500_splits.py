"""Create or validate the frozen MATH-500 Train/Validation/Test split."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from adaptive_compute.math500_splits import create_math500_split_manifest


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pilot-manifest",
        type=Path,
        default=Path("data/splits/math500_pilot_v2.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/splits/math500_split_v1.json"),
    )
    parser.add_argument("--train-count", type=int, default=80)
    parser.add_argument("--validation-count", type=int, default=20)
    parser.add_argument("--test-count", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    manifest = create_math500_split_manifest(
        pilot_manifest_path=args.pilot_manifest,
        output_path=args.output,
        train_count=args.train_count,
        validation_count=args.validation_count,
        test_count=args.test_count,
        split_seed=args.seed,
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "partition_sizes": manifest["partition_sizes"],
                "unassigned_reserve_count": manifest["unassigned_reserve_count"],
                "partition_problem_ids_sha256": manifest[
                    "partition_problem_ids_sha256"
                ],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
