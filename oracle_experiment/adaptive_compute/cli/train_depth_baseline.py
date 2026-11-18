"""Train and select the Phase 2 depth-only logistic baseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from adaptive_compute.controller.depth_baseline import train_depth_only_baseline


DEFAULT_DATA_DIR = Path("results/phase2/depth_controller_data_v1")
DEFAULT_OUTPUT_DIR = Path("results/phase2/depth_baseline_v1")


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--seed", type=int, default=42)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    manifest = train_depth_only_baseline(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        random_seed=args.seed,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
