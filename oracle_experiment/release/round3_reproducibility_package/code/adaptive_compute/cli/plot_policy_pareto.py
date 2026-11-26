"""Plot frozen policy accuracy--token frontiers from replay CSV artifacts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any


POLICY_STYLE = {
    "fixed_profile": ("#4C78A8", "o", "Fixed profile"),
    "breadth_only_agreement_stopping": ("#59A14F", "^", "Breadth stopping"),
    "depth_only_input_tertile": ("#F28E2B", "D", "Depth only"),
    "depth_first_heuristic": ("#E15759", "*", "Joint heuristic"),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def load_policy_points(summary_path: Path, pareto_path: Path) -> list[dict[str, Any]]:
    """Load replay outputs and require an exact policy-ID match."""

    summaries = _read_csv(summary_path)
    pareto_rows = _read_csv(pareto_path)
    summary_ids = {row["policy_id"] for row in summaries}
    pareto_by_id = {row["policy_id"]: row for row in pareto_rows}
    if len(summary_ids) != len(summaries):
        raise ValueError(f"Duplicate policy IDs in {summary_path}")
    if summary_ids != set(pareto_by_id):
        missing = sorted(summary_ids - set(pareto_by_id))
        extra = sorted(set(pareto_by_id) - summary_ids)
        raise ValueError(f"Policy-ID mismatch: missing={missing}, extra={extra}")

    output: list[dict[str, Any]] = []
    for row in summaries:
        policy_id = row["policy_id"]
        pareto = pareto_by_id[policy_id]
        summary_accuracy = float(row["accuracy"])
        summary_tokens = float(row["avg_actual_generated_tokens"])
        if summary_accuracy != float(pareto["accuracy"]):
            raise ValueError(f"Accuracy mismatch for {policy_id}")
        if summary_tokens != float(pareto["avg_actual_generated_tokens"]):
            raise ValueError(f"Token mismatch for {policy_id}")
        output.append(
            {
                "policy_id": policy_id,
                "policy_type": row["policy_type"],
                "accuracy": summary_accuracy,
                "tokens": summary_tokens,
                "pareto_nondominated": pareto["pareto_nondominated"].strip().lower()
                == "true",
            }
        )
    return sorted(output, key=lambda item: (item["tokens"], item["policy_id"]))


def short_policy_label(policy_id: str) -> str:
    fixed = re.fullmatch(r"fixed_k(\d+)_L(\d+)", policy_id)
    if fixed:
        return f"Fixed k={fixed.group(1)}, L={fixed.group(2)}"
    breadth = re.fullmatch(r"breadth_only_agreement_L(\d+)_v1", policy_id)
    if breadth:
        return f"Breadth stop L={breadth.group(1)}"
    if policy_id == "depth_first_tertile_validity_agreement_v1":
        return "Joint heuristic"
    if policy_id == "depth_only_input_tertile_k1_v1":
        return "Depth only"
    return policy_id


def _annotation_specs(selected_policy_id: str) -> dict[str, tuple[int, int]]:
    common = {"depth_first_tertile_validity_agreement_v1": (7, -12)}
    if selected_policy_id == "breadth_only_agreement_L1024_v1":
        return {
            **common,
            selected_policy_id: (-7, 9),
            "fixed_k4_L1024": (7, -12),
        }
    if selected_policy_id == "fixed_k2_L4096":
        return {
            **common,
            selected_policy_id: (7, -12),
            "breadth_only_agreement_L4096_v1": (-7, 9),
            "fixed_k4_L4096": (-7, -12),
        }
    return {**common, selected_policy_id: (7, 9)}


def plot_panel(
    ax: Any,
    points: list[dict[str, Any]],
    *,
    title: str,
    selected_policy_id: str,
) -> None:
    """Draw one policy frontier panel."""

    unknown_types = {point["policy_type"] for point in points} - set(POLICY_STYLE)
    if unknown_types:
        raise ValueError(f"Unknown policy types: {sorted(unknown_types)}")
    if selected_policy_id not in {point["policy_id"] for point in points}:
        raise ValueError(f"Selected policy is absent: {selected_policy_id}")

    for policy_type, (color, marker, legend_label) in POLICY_STYLE.items():
        subset = [point for point in points if point["policy_type"] == policy_type]
        if not subset:
            continue
        ax.scatter(
            [point["tokens"] for point in subset],
            [100.0 * point["accuracy"] for point in subset],
            color=color,
            marker=marker,
            s=70 if marker != "*" else 140,
            alpha=0.9,
            label=legend_label,
            zorder=3,
        )

    frontier = [point for point in points if point["pareto_nondominated"]]
    frontier.sort(key=lambda point: point["tokens"])
    ax.plot(
        [point["tokens"] for point in frontier],
        [100.0 * point["accuracy"] for point in frontier],
        color="#222222",
        linewidth=1.3,
        linestyle="--",
        label="Test Pareto frontier",
        zorder=2,
    )

    selected = next(point for point in points if point["policy_id"] == selected_policy_id)
    ax.scatter(
        [selected["tokens"]],
        [100.0 * selected["accuracy"]],
        facecolors="none",
        edgecolors="#111111",
        linewidths=1.8,
        s=210,
        zorder=5,
        label="Pre-Test selected",
    )

    annotation_specs = _annotation_specs(selected_policy_id)
    for point in [
        point for point in points if point["policy_id"] in annotation_specs
    ]:
        dx, dy = annotation_specs[point["policy_id"]]
        ax.annotate(
            short_policy_label(point["policy_id"]),
            (point["tokens"], 100.0 * point["accuracy"]),
            xytext=(dx, dy),
            textcoords="offset points",
            fontsize=9.5,
            ha="left" if dx > 0 else "right",
            va="bottom" if dy > 0 else "top",
        )

    ax.set_title(title, fontweight="bold")
    ax.set_xlabel("Mean actual generated tokens per problem")
    ax.set_ylabel("Exact-answer accuracy (%)")
    ax.grid(True, color="#D9D9D9", linewidth=0.6, alpha=0.75)
    ax.set_axisbelow(True)
    ax.margins(x=0.10, y=0.12)


def _save_figure(fig: Any, output_stem: Path) -> list[Path]:
    png_path = output_stem.with_suffix(".png")
    pdf_path = output_stem.with_suffix(".pdf")
    fig.savefig(png_path, dpi=240, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    return [png_path, pdf_path]


def generate_policy_pareto_figures(
    *,
    gsm_summary: Path,
    gsm_pareto: Path,
    math_summary: Path,
    math_pareto: Path,
    output_dir: Path,
    gsm_selected_policy_id: str,
    math_selected_policy_id: str,
) -> dict[str, Any]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output_dir.mkdir(parents=True, exist_ok=True)
    gsm_points = load_policy_points(gsm_summary, gsm_pareto)
    math_points = load_policy_points(math_summary, math_pareto)
    if len(gsm_points) != 14 or len(math_points) != 14:
        raise ValueError(
            f"Expected 14 policies per dataset; got GSM8K={len(gsm_points)}, "
            f"MATH-500={len(math_points)}"
        )

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.size": 11,
            "axes.labelsize": 11,
            "axes.titlesize": 11.5,
            "xtick.labelsize": 9.5,
            "ytick.labelsize": 9.5,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    outputs: list[Path] = []
    for points, title, selected, stem in (
        (gsm_points, "GSM8K Test-100", gsm_selected_policy_id, "gsm8k_test_policy_pareto"),
        (math_points, "MATH-500 Test-100", math_selected_policy_id, "math500_test_policy_pareto"),
    ):
        fig, ax = plt.subplots(figsize=(7.2, 4.8))
        plot_panel(ax, points, title=title, selected_policy_id=selected)
        ax.legend(fontsize=9.5, frameon=True, loc="lower right")
        fig.tight_layout()
        outputs.extend(_save_figure(fig, output_dir / stem))
        plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(12.2, 5.2))
    plot_panel(
        axes[0],
        gsm_points,
        title="(a) GSM8K Test-100",
        selected_policy_id=gsm_selected_policy_id,
    )
    plot_panel(
        axes[1],
        math_points,
        title="(b) MATH-500 Test-100",
        selected_policy_id=math_selected_policy_id,
    )
    handles, labels = axes[1].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="lower center",
        ncol=3,
        fontsize=9.5,
        frameon=True,
        bbox_to_anchor=(0.5, -0.01),
    )
    fig.subplots_adjust(bottom=0.24, wspace=0.25)
    outputs.extend(_save_figure(fig, output_dir / "cross_dataset_test_policy_pareto"))
    plt.close(fig)

    manifest = {
        "schema_version": 1,
        "artifact_type": "frozen_test_policy_pareto_figures",
        "source_hashes": {
            str(gsm_summary): _sha256(gsm_summary),
            str(gsm_pareto): _sha256(gsm_pareto),
            str(math_summary): _sha256(math_summary),
            str(math_pareto): _sha256(math_pareto),
        },
        "selected_policy_ids": {
            "gsm8k": gsm_selected_policy_id,
            "math500": math_selected_policy_id,
        },
        "policy_counts": {"gsm8k": len(gsm_points), "math500": len(math_points)},
        "outputs": {path.name: _sha256(path) for path in outputs},
        "interpretation": (
            "Test Pareto status is descriptive; figures do not authorize "
            "post-Test policy reselection."
        ),
    }
    manifest_path = output_dir / "policy_pareto_figure_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gsm-summary", type=Path, required=True)
    parser.add_argument("--gsm-pareto", type=Path, required=True)
    parser.add_argument("--math-summary", type=Path, required=True)
    parser.add_argument("--math-pareto", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--gsm-selected-policy-id",
        default="breadth_only_agreement_L1024_v1",
    )
    parser.add_argument("--math-selected-policy-id", default="fixed_k2_L4096")
    args = parser.parse_args()
    manifest = generate_policy_pareto_figures(
        gsm_summary=args.gsm_summary,
        gsm_pareto=args.gsm_pareto,
        math_summary=args.math_summary,
        math_pareto=args.math_pareto,
        output_dir=args.output_dir,
        gsm_selected_policy_id=args.gsm_selected_policy_id,
        math_selected_policy_id=args.math_selected_policy_id,
    )
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
