"""Execute the reproducible shared-sample Oracle Grid Experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Sequence

from config import (
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
from dataset import GSM8KProblem, extend_gsm8k_subset_manifest, load_gsm8k_subset
from dataset_audit import load_manual_audit
from experiment_runner import (
    build_experiment_manifest,
    create_or_validate_manifest,
    default_experiment_id,
    run_shared_sample_pool,
)
from models.transformers_adapter import TransformersModelAdapter


DEFAULT_DATASET_MANIFEST = Path("results/raw/gsm8k_subset_manifest.json")
DEFAULT_GENERATION_CACHE = Path("results/generation_cache.jsonl")


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--num-problems", type=int, default=NUM_PROBLEMS)
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
    parser.add_argument("--dataset-manifest", type=Path, default=DEFAULT_DATASET_MANIFEST)
    parser.add_argument(
        "--extend-dataset-manifest-from",
        type=Path,
        help="create a larger manifest whose prefix exactly matches this existing manifest",
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
    return ExperimentConfig(
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


def _validation_payload(config: ExperimentConfig) -> dict[str, object]:
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
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    config = config_from_args(args)
    if args.validate_only:
        print(json.dumps(_validation_payload(config), indent=2, ensure_ascii=False))
        return 0
    if args.model_backend != "transformers":
        raise ValueError(f"unsupported model backend: {args.model_backend}")

    problems = load_staged_problems(config, args.dataset_manifest, args.extend_dataset_manifest_from)
    dataset_manifest_hash = hashlib.sha256(args.dataset_manifest.read_bytes()).hexdigest()
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
        from analyze_grid import run_analysis

        run_analysis(experiment_dir)
        print(f"Analysis written to {experiment_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
