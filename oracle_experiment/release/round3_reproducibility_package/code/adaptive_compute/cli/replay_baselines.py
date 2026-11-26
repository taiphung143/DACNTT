"""Replay fixed profiles and the pre-registered depth-first heuristic."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from adaptive_compute.controller.policy_replay import build_policy_replay


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-dir", type=Path, required=True)
    parser.add_argument("--split-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--partition", choices=("train", "validation", "test"), default="train"
    )
    parser.add_argument(
        "--policy-config",
        type=Path,
        help="required for Validation/Test; must be the frozen Train policy_config.json",
    )
    parser.add_argument(
        "--policy-freeze-manifest",
        type=Path,
        help="required for Test; pre-Test policy_freeze.json authorizing replay",
    )
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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    manifest = build_policy_replay(
        experiment_dir=args.experiment_dir,
        split_manifest_path=args.split_manifest,
        output_dir=args.output_dir,
        partition=args.partition,
        policy_config_path=args.policy_config,
        policy_freeze_manifest_path=args.policy_freeze_manifest,
        depths=tuple(args.depths) if args.depths else None,
        breadths=tuple(args.breadths) if args.breadths else None,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
