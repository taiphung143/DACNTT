"""Create and freeze the Phase 2 Train/Validation/Test problem manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from adaptive_compute.config import GLOBAL_SEED, MANUAL_AUDIT_PATH
from adaptive_compute.dataset import extend_gsm8k_subset_manifest
from adaptive_compute.phase2_splits import create_phase2_split_manifest, file_sha256


DEFAULT_DEVELOPMENT_MANIFEST = Path("results/raw/gsm8k_subset_manifest_n100.json")
DEFAULT_EXPANDED_POOL_MANIFEST = Path("results/raw/gsm8k_phase2_pool_manifest.json")
DEFAULT_PHASE2_SPLIT_MANIFEST = Path("data/splits/phase2_gsm8k_split_v1.json")


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--development-manifest", type=Path, default=DEFAULT_DEVELOPMENT_MANIFEST)
    parser.add_argument("--expanded-pool-manifest", type=Path, default=DEFAULT_EXPANDED_POOL_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_PHASE2_SPLIT_MANIFEST)
    parser.add_argument("--manual-audit", type=Path, default=MANUAL_AUDIT_PATH)
    parser.add_argument("--train-count", type=int, default=79)
    parser.add_argument("--validation-count", type=int, default=20)
    parser.add_argument("--test-count", type=int, default=100)
    parser.add_argument("--seed", type=int, default=GLOBAL_SEED)
    parser.add_argument("--cache-dir", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    if not args.expanded_pool_manifest.exists():
        development = json.loads(args.development_manifest.read_text(encoding="utf-8"))
        development_count = int(development["num_problems"])
        extend_gsm8k_subset_manifest(
            base_manifest_path=args.development_manifest,
            output_manifest_path=args.expanded_pool_manifest,
            num_problems=development_count + args.test_count,
            seed=int(development["seed"]),
            dataset_config=str(development["dataset_config"]),
            split=str(development["split"]),
            cache_dir=args.cache_dir,
        )

    manifest = create_phase2_split_manifest(
        development_manifest_path=args.development_manifest,
        expanded_pool_manifest_path=args.expanded_pool_manifest,
        output_path=args.output,
        train_count=args.train_count,
        validation_count=args.validation_count,
        test_count=args.test_count,
        split_seed=args.seed,
        manual_audit_path=args.manual_audit,
    )
    print(
        json.dumps(
            {
                "manifest": str(args.output),
                "sha256": file_sha256(args.output),
                "status": manifest["status"],
                "partition_sizes": manifest["partition_sizes"],
                "excluded_from_development": manifest["excluded_from_development"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
