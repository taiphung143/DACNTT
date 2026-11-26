"""Rebuild round-3 paper figures as readable vector PDFs.

Only existing CSV results are read.  No inference or result mutation occurs.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from statistics import fmean


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "results" / "qwen3_1_7b_gsm8k_n100_r1" / "config_results.csv"
OUTPUT = ROOT / "paper" / "figures"


def _truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true"}


def _load() -> list[dict[str, str]]:
    with SOURCE.open(newline="", encoding="utf-8") as handle:
        return [row for row in csv.DictReader(handle) if _truthy(row["evaluation_included"])]


def main() -> int:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    rows = _load()
    grouped: dict[tuple[int, int], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(int(row["k"]), int(row["L"]))].append(row)

    ks = [1, 2, 4]
    lengths = [512, 1024, 2048]
    accuracy = np.array(
        [
            [100 * fmean(_truthy(row["final_correct"]) for row in grouped[(k, length)]) for length in lengths]
            for k in ks
        ]
    )
    tokens = {
        (k, length): fmean(float(row["actual_generated_tokens"]) for row in grouped[(k, length)])
        for k in ks
        for length in lengths
    }

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.size": 11,
            "axes.labelsize": 11,
            "axes.titlesize": 12,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
        }
    )
    OUTPUT.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    image = ax.imshow(accuracy, cmap="Blues", vmin=0, vmax=100, aspect="auto")
    for row_index, k in enumerate(ks):
        for column_index, length in enumerate(lengths):
            value = accuracy[row_index, column_index]
            ax.text(
                column_index,
                row_index,
                f"{value:.1f}%",
                ha="center",
                va="center",
                color="white" if value >= 55 else "black",
                fontsize=11,
            )
    ax.set_xticks(range(len(lengths)), [str(value) for value in lengths])
    ax.set_yticks(range(len(ks)), [str(value) for value in ks])
    ax.set_xlabel("Token cap L")
    ax.set_ylabel("Number of samples k")
    ax.set_title("Historical Qwen3-1.7B / GSM8K accuracy (n=99)")
    colorbar = fig.colorbar(image, ax=ax, pad=0.03)
    colorbar.set_label("Exact-answer accuracy (%)")
    fig.tight_layout()
    fig.savefig(OUTPUT / "historical_accuracy_heatmap_round3.pdf", bbox_inches="tight")
    plt.close(fig)

    points = []
    for k in ks:
        for length in lengths:
            points.append((tokens[(k, length)], accuracy[ks.index(k), lengths.index(length)], k, length))
    frontier = []
    for point in points:
        x, y, _, _ = point
        dominated = any(
            other_x <= x and other_y >= y and (other_x < x or other_y > y)
            for other_x, other_y, _, _ in points
        )
        if not dominated:
            frontier.append(point)
    frontier.sort()

    fig, ax = plt.subplots(figsize=(6.8, 4.5))
    ax.scatter([p[0] for p in points], [p[1] for p in points], s=60, color="#2C7FB8")
    ax.plot(
        [p[0] for p in frontier],
        [p[1] for p in frontier],
        linestyle="--",
        color="#222222",
        linewidth=1.4,
        label="Observed Pareto frontier",
    )
    for x, y, k, length in points:
        ax.annotate(f"{k}x{length}", (x, y), xytext=(4, 5), textcoords="offset points", fontsize=9.5)
    ax.set_xlabel("Mean actual generated tokens per problem")
    ax.set_ylabel("Exact-answer accuracy (%)")
    ax.set_title("Historical fixed-profile trade-off")
    ax.grid(True, color="#D9D9D9", linewidth=0.6)
    ax.legend(fontsize=10)
    fig.tight_layout()
    fig.savefig(OUTPUT / "historical_fixed_pareto_round3.pdf", bbox_inches="tight")
    plt.close(fig)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
