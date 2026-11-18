"""Build leakage-safe Phase 2 depth-controller Train/Validation tables."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from adaptive_compute.controller.depth_data import build_depth_controller_dataset


DEFAULT_EXPERIMENT_DIR = Path("results/qwen3_1_7b_gsm8k_n100_r1")
DEFAULT_SPLIT_MANIFEST = Path("data/splits/phase2_gsm8k_split_v1.json")
DEFAULT_OUTPUT_DIR = Path("results/phase2/depth_controller_data_v1")


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-dir", type=Path, default=DEFAULT_EXPERIMENT_DIR)
    parser.add_argument("--split-manifest", type=Path, default=DEFAULT_SPLIT_MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--repetition-id", type=int, default=0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    manifest = build_depth_controller_dataset(
        raw_samples_path=args.experiment_dir / "raw_samples.jsonl",
        config_results_path=args.experiment_dir / "config_results.csv",
        split_manifest_path=args.split_manifest,
        output_dir=args.output_dir,
        source_experiment_id=args.experiment_dir.name,
        repetition_id=args.repetition_id,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
