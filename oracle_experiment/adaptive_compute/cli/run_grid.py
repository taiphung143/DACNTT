"""Execute the reproducible shared-sample Oracle Grid Experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Sequence

from adaptive_compute.answer_parser import (
    GSM8K_ANSWER_PARSER_NAME,
    GSM8K_ANSWER_PARSER_V2_NAME,
    GSM8K_ANSWER_PARSER_V3_NAME,
    MATH500_ANSWER_PARSER_NAME,
)
from adaptive_compute.config import (
    GLOBAL_SEED,
    K_VALUES,
    L_VALUES,
    MODEL_ID,
    MODEL_REVISION,
    NUM_PROBLEMS,
    NUM_REPETITIONS,
    TEMPERATURE,
    TOP_P,
    ExperimentConfig,
)
from adaptive_compute.dataset import GSM8KProblem, extend_gsm8k_subset_manifest, load_gsm8k_subset
from adaptive_compute.dataset_audit import load_manual_audit
from adaptive_compute.experiment_runner import (
    build_experiment_manifest,
    create_or_validate_manifest,
    default_experiment_id,
    run_shared_sample_pool,
)
from adaptive_compute.models.transformers_adapter import TransformersModelAdapter
from adaptive_compute.math500 import (
    MATH500_DATASET_REVISION,
    MATH500_HF_DATASET_ID,
    load_math500_subset,
)
from adaptive_compute.math500_splits import (
    load_math500_partition,
    read_math500_split_manifest,
)
from adaptive_compute.phase2_splits import (
    PHASE2_PARTITIONS,
    file_sha256,
    load_phase2_partition,
    read_phase2_split_manifest,
)
from adaptive_compute.prompts import (
    GSM8K_PROMPT_TEMPLATE_NAME,
    GSM8K_PROMPT_TEMPLATE_V2_NAME,
    GSM8K_PROMPT_TEMPLATE_V3_NAME,
    MATH500_PROMPT_TEMPLATE_NAME,
)


DEFAULT_DATASET_MANIFEST = Path("results/raw/gsm8k_subset_manifest.json")
DEFAULT_MATH500_MANIFEST = Path("data/splits/math500_pilot_v2.json")
DEFAULT_GENERATION_CACHE = Path("results/generation_cache.jsonl")


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--num-problems", type=int, default=NUM_PROBLEMS)
    parser.add_argument(
        "--dataset-name",
        choices=("gsm8k", "math500"),
        default="gsm8k",
    )
    parser.add_argument(
        "--dataset-revision",
        help="pinned dataset repository revision; MATH-500 has a protocol default",
    )
    parser.add_argument(
        "--gsm8k-contract-version",
        choices=("v1", "v2", "v3"),
        default="v3",
        help="versioned GSM8K prompt/parser contract; v1 is for historical resume only",
    )
    parser.add_argument("--k-values", type=int, nargs="+", default=K_VALUES)
    parser.add_argument("--l-values", type=int, nargs="+", default=L_VALUES)
    parser.add_argument("--seed", type=int, default=GLOBAL_SEED)
    parser.add_argument("--num-repetitions", type=int, default=NUM_REPETITIONS)
    parser.add_argument("--temperature", type=float, default=TEMPERATURE)
    parser.add_argument("--top-p", type=float, default=TOP_P)
    parser.add_argument("--model-id", default=MODEL_ID)
    parser.add_argument("--model-revision", default=MODEL_REVISION)
    parser.add_argument("--model-backend", default="transformers")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--dtype", default="bfloat16")
    parser.add_argument("--allow-cpu", action="store_true")
    parser.add_argument("--results-dir", type=Path, default=Path("results"))
    parser.add_argument("--dataset-manifest", type=Path)
    parser.add_argument(
        "--extend-dataset-manifest-from",
        type=Path,
        help="create a larger manifest whose prefix exactly matches this existing manifest",
    )
    parser.add_argument(
        "--phase2-split-manifest",
        type=Path,
        help="frozen dataset-specific Train/Validation/Test manifest",
    )
    parser.add_argument(
        "--phase2-partition",
        choices=PHASE2_PARTITIONS,
        help="partition to load from --phase2-split-manifest",
    )
    parser.add_argument(
        "--phase2-limit",
        type=int,
        help=(
            "use a deterministic prefix of a frozen Phase 2 partition; "
            "intended for bounded Train/Validation development pilots"
        ),
    )
    parser.add_argument("--generation-cache", type=Path, default=DEFAULT_GENERATION_CACHE)
    parser.add_argument("--no-generation-cache", action="store_true")
    parser.add_argument("--experiment-id")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--retry-errors", action="store_true")
    parser.add_argument("--no-analysis", action="store_true")
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="validate and print the shared-pool plan without loading data or a model",
    )
    return parser


def config_from_args(args: argparse.Namespace) -> ExperimentConfig:
    if args.dataset_name == "math500":
        dataset_settings = {
            "dataset_name": "math500",
            "dataset_id": MATH500_HF_DATASET_ID,
            "dataset_config": "default",
            "dataset_split": "test",
            "dataset_revision": args.dataset_revision or MATH500_DATASET_REVISION,
            "prompt_template_name": MATH500_PROMPT_TEMPLATE_NAME,
            "answer_parser_name": MATH500_ANSWER_PARSER_NAME,
        }
    else:
        gsm8k_contract = {
            "v1": (GSM8K_PROMPT_TEMPLATE_NAME, GSM8K_ANSWER_PARSER_NAME),
            "v2": (GSM8K_PROMPT_TEMPLATE_V2_NAME, GSM8K_ANSWER_PARSER_V2_NAME),
            "v3": (GSM8K_PROMPT_TEMPLATE_V3_NAME, GSM8K_ANSWER_PARSER_V3_NAME),
        }[args.gsm8k_contract_version]
        dataset_settings = {
            "dataset_name": "gsm8k",
            "dataset_id": "openai/gsm8k",
            "dataset_config": "main",
            "dataset_split": "test",
            "dataset_revision": args.dataset_revision,
            "prompt_template_name": gsm8k_contract[0],
            "answer_parser_name": gsm8k_contract[1],
        }
    return ExperimentConfig(
        **dataset_settings,
        num_problems=args.num_problems,
        model_id=args.model_id,
        model_revision=args.model_revision,
        model_backend=args.model_backend,
        model_dtype=args.dtype,
        k_values=tuple(args.k_values),
        l_values=tuple(args.l_values),
        temperature=args.temperature,
        top_p=args.top_p,
        global_seed=args.seed,
        num_repetitions=args.num_repetitions,
        results_dir=args.results_dir,
    )


def _read_manifest_problem_count(path: Path) -> int | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    value = payload.get("num_problems")
    return int(value) if value is not None else None


def load_staged_problems(
    config: ExperimentConfig,
    manifest_path: Path,
    extend_manifest_from: Path | None = None,
) -> list[GSM8KProblem]:
    """Load a stable prefix of the fixed manifest for 3/10/30 staged runs."""

    if extend_manifest_from is not None and not manifest_path.exists():
        return extend_gsm8k_subset_manifest(
            base_manifest_path=extend_manifest_from,
            output_manifest_path=manifest_path,
            num_problems=config.num_problems,
            seed=config.global_seed,
            dataset_config=config.dataset_config,
            split=config.dataset_split,
        )
    recorded_count = _read_manifest_problem_count(manifest_path)
    if recorded_count is not None and config.num_problems > recorded_count:
        raise ValueError(
            f"requested {config.num_problems} problems but manifest contains {recorded_count}"
        )
    master_count = recorded_count or max(NUM_PROBLEMS, config.num_problems)
    problems = load_gsm8k_subset(
        num_problems=master_count,
        seed=config.global_seed,
        dataset_config=config.dataset_config,
        split=config.dataset_split,
        manifest_path=manifest_path,
    )
    return problems[: config.num_problems]


def _validation_payload(
    config: ExperimentConfig,
    *,
    dataset_partition: str | None = None,
) -> dict[str, object]:
    payload = config.to_dict()
    payload["grid"] = [
        {
            "k": profile.k,
            "L": profile.max_new_tokens,
            "allocated_token_budget": profile.allocated_token_budget,
        }
        for profile in config.grid
    ]
    payload["shared_pool_max_k"] = max(config.k_values)
    payload["expected_unique_generations"] = (
        config.num_problems
        * len(config.l_values)
        * max(config.k_values)
        * config.num_repetitions
    )
    payload["dataset_partition"] = dataset_partition
    return payload


def _validate_phase2_arguments(args: argparse.Namespace, config: ExperimentConfig) -> None:
    has_manifest = args.phase2_split_manifest is not None
    has_partition = args.phase2_partition is not None
    if has_manifest != has_partition:
        raise ValueError(
            "--phase2-split-manifest and --phase2-partition must be supplied together"
        )
    if has_manifest and args.extend_dataset_manifest_from is not None:
        raise ValueError(
            "--extend-dataset-manifest-from cannot be combined with a frozen Phase 2 split"
        )
    if args.extend_dataset_manifest_from is not None and args.dataset_name != "gsm8k":
        raise ValueError("manifest extension currently applies only to GSM8K")
    if args.phase2_limit is not None and not has_manifest:
        raise ValueError(
            "--phase2-limit requires --phase2-split-manifest and --phase2-partition"
        )
    if args.phase2_limit is not None and args.phase2_limit <= 0:
        raise ValueError("--phase2-limit must be positive")
    if args.phase2_limit is not None and args.phase2_partition == "test":
        raise ValueError("--phase2-limit is not allowed for the held-out test partition")
    if has_manifest:
        split_manifest = (
            read_math500_split_manifest(args.phase2_split_manifest)
            if args.dataset_name == "math500"
            else read_phase2_split_manifest(args.phase2_split_manifest)
        )
        if args.dataset_name == "math500" and (
            config.dataset_revision != split_manifest["dataset_revision"]
        ):
            raise ValueError(
                "MATH-500 dataset revision must match the frozen split manifest"
            )
        frozen_count = int(split_manifest["partition_sizes"][args.phase2_partition])
        selected_count = args.phase2_limit or frozen_count
        if selected_count > frozen_count:
            raise ValueError(
                f"--phase2-limit cannot exceed the frozen {args.phase2_partition} "
                f"partition size ({frozen_count})"
            )
        if config.num_problems != selected_count:
            raise ValueError(
                f"--num-problems must equal the selected {args.phase2_partition} "
                f"problem count ({selected_count})"
            )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    config = config_from_args(args)
    _validate_phase2_arguments(args, config)
    if args.validate_only:
        print(
            json.dumps(
                _validation_payload(config, dataset_partition=args.phase2_partition),
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    if args.model_backend != "transformers":
        raise ValueError(f"unsupported model backend: {args.model_backend}")

    dataset_manifest_path = args.dataset_manifest
    if dataset_manifest_path is None:
        dataset_manifest_path = (
            DEFAULT_MATH500_MANIFEST
            if args.dataset_name == "math500"
            else DEFAULT_DATASET_MANIFEST
        )

    if args.phase2_split_manifest is not None:
        if args.dataset_name == "math500":
            problems = load_math500_partition(
                manifest_path=args.phase2_split_manifest,
                partition=args.phase2_partition,
            )
        else:
            problems = load_phase2_partition(
                manifest_path=args.phase2_split_manifest,
                partition=args.phase2_partition,
                manual_audit_path=config.manual_audit_path,
            )
        if args.phase2_limit is not None:
            problems = problems[: args.phase2_limit]
        dataset_manifest_hash = file_sha256(args.phase2_split_manifest)
    elif args.dataset_name == "math500":
        problems = load_math500_subset(
            num_problems=config.num_problems,
            seed=config.global_seed,
            revision=config.dataset_revision or MATH500_DATASET_REVISION,
            split=config.dataset_split,
            manifest_path=dataset_manifest_path,
        )
        dataset_manifest_hash = hashlib.sha256(dataset_manifest_path.read_bytes()).hexdigest()
    else:
        problems = load_staged_problems(
            config, dataset_manifest_path, args.extend_dataset_manifest_from
        )
        dataset_manifest_hash = hashlib.sha256(dataset_manifest_path.read_bytes()).hexdigest()
    experiment_id = args.experiment_id or default_experiment_id(
        config, [item.problem_id for item in problems]
    )
    experiment_dir = config.results_dir / experiment_id
    proposed_manifest = build_experiment_manifest(
        experiment_id=experiment_id,
        config=config,
        problems=problems,
        dataset_manifest_hash=dataset_manifest_hash,
        device=args.device,
        dtype=args.dtype,
        dataset_partition=args.phase2_partition,
    )
    create_or_validate_manifest(
        experiment_dir / "experiment_manifest.json",
        proposed_manifest,
        resume=args.resume,
    )

    adapter = TransformersModelAdapter(
        config.model_id,
        revision=config.model_revision,
        device=args.device,
        dtype=args.dtype,
        top_p=config.top_p,
        use_chat_template=config.use_chat_template,
        enable_thinking=config.enable_thinking,
        allow_cpu=args.allow_cpu,
    )
    stats = run_shared_sample_pool(
        config=config,
        problems=problems,
        adapter=adapter,
        experiment_id=experiment_id,
        raw_samples_path=experiment_dir / "raw_samples.jsonl",
        audit_entries=load_manual_audit(config.manual_audit_path),
        resume=args.resume,
        retry_errors=args.retry_errors,
        generation_cache_path=None if args.no_generation_cache else args.generation_cache,
    )
    print(json.dumps({"experiment_id": experiment_id, **stats}, indent=2))

    if not args.no_analysis:
        from adaptive_compute.cli.analyze_grid import run_analysis

        run_analysis(experiment_dir)
        print(f"Analysis written to {experiment_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
