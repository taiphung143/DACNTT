"""Regenerate Phase 1.5 analysis without loading or invoking a model."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from adaptive_compute.analysis.aggregate import read_csv, resolve_experiment_dir, write_csv
from adaptive_compute.analysis.phase1_5 import (
    BOOTSTRAP_RESAMPLES,
    BOOTSTRAP_SEED,
    build_bootstrap_uncertainty,
    build_budget_frontiers,
    build_cost_accounting,
    build_depth_before_breadth,
    build_failure_analysis,
    build_frontier_headroom,
    build_iso_budget_extended,
    build_oracle_strategies,
    build_per_problem_preferences,
    build_phase1_5_report,
    build_phase2_decision_report,
    build_preference_distribution,
    generate_phase1_5_plots,
)
from adaptive_compute.experiment_runner import latest_checkpoint_records
from adaptive_compute.generation_cache import populate_generation_cache


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_phase1_5(
    experiment_dir: Path,
    *,
    output_dir: Path | None = None,
    generation_cache_path: Path | None = None,
) -> Path:
    experiment_dir = resolve_experiment_dir(experiment_dir)
    output_dir = output_dir or experiment_dir / "phase1_5"
    generation_cache_path = generation_cache_path or experiment_dir.parent / "generation_cache.jsonl"
    raw_path = experiment_dir / "raw_samples.jsonl"
    manifest_path = experiment_dir / "experiment_manifest.json"
    source_hashes_before = {"raw_samples.jsonl": _sha256(raw_path), "experiment_manifest.json": _sha256(manifest_path)}

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    config_rows = read_csv(experiment_dir / "config_results.csv")
    raw_records = list(latest_checkpoint_records(raw_path).values())
    output_dir.mkdir(parents=True, exist_ok=True)

    preferences = build_per_problem_preferences(config_rows)
    distribution = build_preference_distribution(preferences)
    depth_rows = build_depth_before_breadth(config_rows)
    strategy_rows, selections = build_oracle_strategies(config_rows)
    frontier_rows = build_budget_frontiers(config_rows)
    headroom_rows = build_frontier_headroom(frontier_rows)
    bootstrap_rows = build_bootstrap_uncertainty(strategy_rows, selections)
    iso_rows = build_iso_budget_extended(config_rows)
    cost_rows = build_cost_accounting(config_rows)
    failure_rows = build_failure_analysis(raw_records, config_rows)

    for name, rows in (
        ("per_problem_profile_preferences.csv", preferences),
        ("profile_preference_distribution.csv", distribution),
        ("depth_before_breadth.csv", depth_rows),
        ("oracle_strategy_summary.csv", strategy_rows),
        ("oracle_budget_frontier.csv", frontier_rows),
        ("oracle_headroom.csv", headroom_rows),
        ("bootstrap_uncertainty.csv", bootstrap_rows),
        ("iso_budget_2048_extended.csv", iso_rows),
        ("cost_accounting.csv", cost_rows),
        ("failure_analysis.csv", failure_rows),
    ):
        write_csv(output_dir / name, rows)

    generate_phase1_5_plots(output_dir, distribution, depth_rows, frontier_rows, iso_rows)
    (output_dir / "phase1_5_report.md").write_text(
        build_phase1_5_report(
            manifest=manifest,
            preference_distribution=distribution,
            depth_rows=depth_rows,
            cost_rows=cost_rows,
            strategy_rows=strategy_rows,
            frontier_rows=frontier_rows,
            headroom_rows=headroom_rows,
            bootstrap_rows=bootstrap_rows,
            iso_rows=iso_rows,
            failure_rows=failure_rows,
        ),
        encoding="utf-8",
    )
    (output_dir / "phase2_decision.md").write_text(
        build_phase2_decision_report(distribution, depth_rows, strategy_rows, bootstrap_rows),
        encoding="utf-8",
    )

    cache_stats = populate_generation_cache(generation_cache_path, raw_records)
    source_hashes_after = {"raw_samples.jsonl": _sha256(raw_path), "experiment_manifest.json": _sha256(manifest_path)}
    if source_hashes_after != source_hashes_before:
        raise RuntimeError("source experiment artifacts changed during Phase 1.5 analysis")
    (output_dir / "analysis_manifest.json").write_text(
        json.dumps(
            {
                "phase": "1.5",
                "source_experiment_id": manifest["experiment_id"],
                "source_hashes": source_hashes_after,
                "evaluated_problem_count": len(preferences),
                "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
                "bootstrap_seed": BOOTSTRAP_SEED,
                "frontier_method": "exact Pareto-pruned multiple-choice knapsack; exactly one profile per problem; no skip",
                "primary_compute_metric": "actual_generated_tokens",
                "secondary_system_metric": "latency_ms",
                "generation_cache": str(generation_cache_path),
                "generation_cache_stats": cache_stats,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return output_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--generation-cache", type=Path)
    args = parser.parse_args()
    output = run_phase1_5(
        args.experiment,
        output_dir=args.output_dir,
        generation_cache_path=args.generation_cache,
    )
    print(f"Phase 1.5 artifacts written to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
