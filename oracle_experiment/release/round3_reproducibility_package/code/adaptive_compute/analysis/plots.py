"""Generate restrained visual diagnostics from rerunnable CSV artifacts."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from math import nan
from pathlib import Path
from typing import Any

from adaptive_compute.analysis.aggregate import read_csv, resolve_experiment_dir
from adaptive_compute.analysis.heatmap import save_grid_heatmap
from adaptive_compute.analysis.pareto import pareto_frontier


def _number(row: Mapping[str, Any], key: str) -> float:
    value = row.get(key)
    if value in (None, ""):
        return nan
    return float(value)


def _label(row: Mapping[str, Any]) -> str:
    return f"{int(row['k'])}×{int(row['L'])}"


def generate_plots(
    experiment_dir: Path,
    grid_rows: Sequence[Mapping[str, Any]] | None = None,
    oracle_rows: Sequence[Mapping[str, Any]] | None = None,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    grid = list(grid_rows or read_csv(experiment_dir / "grid_summary.csv"))
    oracle = list(oracle_rows or read_csv(experiment_dir / "oracle_comparison.csv"))
    plots_dir = experiment_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    save_grid_heatmap(
        grid,
        value_key="final_accuracy",
        title="Historical Qwen3-1.7B GSM8K accuracy (n=99)",
        output=plots_dir / "accuracy_heatmap.png",
    )
    save_grid_heatmap(
        grid,
        value_key="avg_generated_tokens",
        title="Average realized generated tokens",
        output=plots_dir / "generated_tokens_heatmap.png",
        value_format=".0f",
    )
    save_grid_heatmap(
        grid,
        value_key="truncation_rate",
        title="Sample truncation rate",
        output=plots_dir / "truncation_heatmap.png",
    )

    depth = sorted((row for row in grid if int(row["k"]) == 1), key=lambda row: int(row["L"]))
    fig, axes = plt.subplots(2, 2, figsize=(10, 7))
    lengths = [int(row["L"]) for row in depth]
    rate_axis = axes[0, 0]
    for key, label in (
        ("final_accuracy", "Final accuracy"),
        ("truncation_rate", "All truncation"),
        ("during_thinking_truncation_rate", "During-thinking truncation"),
        ("after_thinking_truncation_rate", "After-thinking truncation"),
    ):
        rate_axis.plot(lengths, [_number(row, key) for row in depth], marker="o", label=label)
    rate_axis.set_ylim(-0.03, 1.03)
    rate_axis.set_title("Outcome rates")
    rate_axis.legend(fontsize=8)
    axes[0, 1].plot(lengths, [_number(row, "avg_generated_tokens") for row in depth], marker="o")
    axes[0, 1].set_title("Average generated tokens")
    axes[1, 0].plot(lengths, [_number(row, "avg_token_budget_utilization") for row in depth], marker="o")
    axes[1, 0].set_title("Average token utilization")
    axes[1, 0].set_ylim(-0.03, 1.03)
    axes[1, 1].plot(lengths, [_number(row, "avg_latency_ms") for row in depth], marker="o")
    axes[1, 1].set_title("Average latency (ms)")
    for ax in axes.flat:
        ax.set_xlabel("L at fixed k=1")
    fig.suptitle("Depth diagnostic (exploratory pilot)")
    fig.tight_layout()
    fig.savefig(plots_dir / "depth_effect.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(2, 2, figsize=(10, 7))
    for length in sorted({int(row["L"]) for row in grid}):
        subset = sorted((row for row in grid if int(row["L"]) == length), key=lambda row: int(row["k"]))
        ks = [int(row["k"]) for row in subset]
        axes[0, 0].plot(ks, [_number(row, "final_accuracy") for row in subset], marker="o", label=f"L={length}")
        axes[0, 1].plot(ks, [_number(row, "avg_agreement") for row in subset], marker="o", label=f"L={length}")
        axes[0, 1].plot(ks, [_number(row, "avg_valid_answer_fraction") for row in subset], marker="x", linestyle="--")
        axes[1, 0].plot(ks, [_number(row, "avg_generated_tokens") for row in subset], marker="o", label=f"L={length}")
        axes[1, 1].plot(ks, [_number(row, "avg_latency_ms") for row in subset], marker="o", label=f"L={length}")
    axes[0, 0].set_title("Final accuracy")
    axes[0, 1].set_title("Agreement (solid) / valid fraction (dashed)")
    axes[1, 0].set_title("Average generated tokens")
    axes[1, 1].set_title("Average latency (ms)")
    for ax in axes.flat:
        ax.set_xlabel("k (shared prefix size)")
        ax.set_xticks(sorted({int(row["k"]) for row in grid}))
        ax.legend()
    axes[0, 0].set_ylim(-0.03, 1.03)
    axes[0, 1].set_ylim(-0.03, 1.03)
    fig.suptitle("Breadth diagnostic; k=1 agreement is not interpreted")
    fig.tight_layout()
    fig.savefig(plots_dir / "breadth_effect.png", dpi=180)
    plt.close(fig)

    iso = [row for row in grid if int(row["k"]) * int(row["L"]) == 2048]
    fig, ax = plt.subplots(figsize=(7, 4))
    labels = [_label(row) for row in iso]
    ax.bar(labels, [_number(row, "final_accuracy") for row in iso], color="#4C78A8")
    ax.set_ylim(0, 1)
    ax.set_ylabel("Final accuracy")
    ax.set_title("Iso-budget 2048: observed breadth/depth outcomes")
    fig.tight_layout()
    fig.savefig(plots_dir / "iso_budget_2048.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 5))
    allocated = [_number(row, "avg_allocated_token_budget") for row in grid]
    realized = [_number(row, "avg_generated_tokens") for row in grid]
    ax.scatter(allocated, realized)
    for row, x, y in zip(grid, allocated, realized, strict=True):
        ax.annotate(_label(row), (x, y), xytext=(4, 4), textcoords="offset points", fontsize=8)
    limit = max(allocated + realized) if grid else 1
    ax.plot([0, limit], [0, limit], linestyle="--", color="gray", label="allocated = realized")
    ax.set_xlabel("Average allocated token budget (k×L)")
    ax.set_ylabel("Average realized generated tokens")
    ax.set_title("Allocated budget is an upper bound")
    ax.legend()
    fig.tight_layout()
    fig.savefig(plots_dir / "allocated_vs_realized.png", dpi=180)
    plt.close(fig)

    frontier = pareto_frontier(grid)
    fig, ax = plt.subplots(figsize=(7, 5))
    for row in grid:
        x, y = _number(row, "avg_generated_tokens"), _number(row, "final_accuracy")
        ax.scatter(x, y, color="#4C78A8")
        ax.annotate(_label(row), (x, y), xytext=(4, 4), textcoords="offset points", fontsize=8)
    if frontier:
        ax.plot(
            [_number(row, "avg_generated_tokens") for row in frontier],
            [_number(row, "final_accuracy") for row in frontier],
            color="#E45756",
            label="Non-dominated frontier",
        )
    ax.set_xlabel("Average realized generated tokens")
    ax.set_ylabel("Final accuracy")
    ax.set_title("Observed fixed-profile accuracy–compute frontier")
    ax.legend()
    fig.tight_layout()
    fig.savefig(plots_dir / "pareto.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 5))
    for row in grid:
        ax.scatter(_number(row, "avg_generated_tokens"), _number(row, "final_accuracy"), color="lightgray")
    for row in oracle:
        x, y = _number(row, "avg_generated_tokens"), _number(row, "accuracy")
        ax.scatter(x, y, s=65)
        ax.annotate(str(row["strategy"]), (x, y), xytext=(5, 5), textcoords="offset points")
    ax.set_xlabel("Average realized generated tokens")
    ax.set_ylabel("Accuracy")
    ax.set_title("Retrospective oracle headroom (not an adaptive controller)")
    fig.tight_layout()
    fig.savefig(plots_dir / "oracle_pareto.png", dpi=180)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, required=True)
    args = parser.parse_args()
    experiment_dir = resolve_experiment_dir(args.experiment)
    generate_plots(experiment_dir)
    print(f"Plots written to {experiment_dir / 'plots'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
