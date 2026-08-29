"""Small plotting helper for k-by-L experiment heatmaps."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path


def save_grid_heatmap(
    rows: Sequence[Mapping[str, Any]],
    *,
    value_key: str,
    title: str,
    output: Path,
    value_format: str = ".3f",
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    k_values = sorted({int(row["k"]) for row in rows})
    l_values = sorted({int(row["L"]) for row in rows})
    lookup = {(int(row["k"]), int(row["L"])): float(row[value_key]) for row in rows}
    matrix = np.array(
        [[lookup.get((k, length), float("nan")) for length in l_values] for k in k_values]
    )
    fig, ax = plt.subplots(figsize=(7, 4.5))
    image = ax.imshow(matrix, aspect="auto", cmap="Blues")
    for row_index, k in enumerate(k_values):
        for column_index, length in enumerate(l_values):
            value = matrix[row_index, column_index]
            if not np.isnan(value):
                ax.text(column_index, row_index, format(value, value_format), ha="center", va="center")
    ax.set_xticks(range(len(l_values)), [str(value) for value in l_values])
    ax.set_yticks(range(len(k_values)), [str(value) for value in k_values])
    ax.set_xlabel("Depth L (max new tokens)")
    ax.set_ylabel("Breadth k (shared prefix samples)")
    ax.set_title(title)
    fig.colorbar(image, ax=ax)
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)
