"""Freeze a selected dataset policy bundle before one-time Test evaluation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from adaptive_compute.controller.policy_freeze import (
    build_math500_policy_freeze_bundle,
    build_policy_freeze_bundle,
)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset-name", choices=("gsm8k", "math500"), default="gsm8k"
    )
    parser.add_argument("--train-replay-dir", type=Path, required=True)
    parser.add_argument("--validation-replay-dir", type=Path, required=True)
    parser.add_argument("--split-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    builder = (
        build_math500_policy_freeze_bundle
        if args.dataset_name == "math500"
        else build_policy_freeze_bundle
    )
    manifest = builder(
        train_replay_dir=args.train_replay_dir,
        validation_replay_dir=args.validation_replay_dir,
        split_manifest_path=args.split_manifest,
        output_dir=args.output_dir,
        repository_root=args.repository_root.resolve(),
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
