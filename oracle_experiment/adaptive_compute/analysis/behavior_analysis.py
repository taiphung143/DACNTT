"""Conservative exploratory labels for observed per-problem grid behavior."""

from __future__ import annotations

import argparse
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path

from adaptive_compute.analysis.aggregate import read_csv, resolve_experiment_dir, write_csv


LABEL_ORDER = (
    "UNSOLVED",
    "LOW_COMPUTE_SUFFICIENT",
    "POSSIBLE_NON_MONOTONIC",
    "JOINT_SENSITIVE_CANDIDATE",
    "DEPTH_BENEFITING",
    "BREADTH_BENEFITING",
)


def _correct(row: Mapping[str, Any]) -> bool:
    value = row.get("final_correct")
    return value is True or str(value).lower() == "true"


def classify_problem(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise ValueError("at least one configuration is required")
    by_profile = {(int(row["k"]), int(row["L"])): _correct(row) for row in rows}
    k_values = sorted({key[0] for key in by_profile})
    l_values = sorted({key[1] for key in by_profile})
    min_k, min_l = k_values[0], l_values[0]
    labels: list[str] = []
    evidence: list[str] = []

    if not any(by_profile.values()):
        labels.append("UNSOLVED")
    if by_profile.get((min_k, min_l), False):
        labels.append("LOW_COMPUTE_SUFFICIENT")

    for (k1, l1), low_correct in by_profile.items():
        if not low_correct:
            continue
        for (k2, l2), high_correct in by_profile.items():
            if k2 >= k1 and l2 >= l1 and (k2 > k1 or l2 > l1) and not high_correct:
                labels.append("POSSIBLE_NON_MONOTONIC")
                evidence.append(f"{k1}x{l1}=correct -> {k2}x{l2}=incorrect")
                break
        if "POSSIBLE_NON_MONOTONIC" in labels:
            break

    depth_evidence = next(
        (
            f"k={k}: L={low_l} incorrect -> L={high_l} correct"
            for k in k_values
            for low_l in l_values
            for high_l in l_values
            if high_l > low_l
            and by_profile.get((k, low_l)) is False
            and by_profile.get((k, high_l)) is True
        ),
        None,
    )
    breadth_evidence = next(
        (
            f"L={length}: k={low_k} incorrect -> k={high_k} correct"
            for length in l_values
            for low_k in k_values
            for high_k in k_values
            if high_k > low_k
            and by_profile.get((low_k, length)) is False
            and by_profile.get((high_k, length)) is True
        ),
        None,
    )
    joint_evidence = next(
        (
            f"{k}x{length} succeeds while {min_k}x{length} and {k}x{min_l} fail"
            for k in k_values
            for length in l_values
            if k > min_k
            and length > min_l
            and by_profile.get((k, length)) is True
            and by_profile.get((min_k, length)) is False
            and by_profile.get((k, min_l)) is False
        ),
        None,
    )
    if joint_evidence:
        labels.append("JOINT_SENSITIVE_CANDIDATE")
        evidence.append(joint_evidence)
    if depth_evidence:
        labels.append("DEPTH_BENEFITING")
        evidence.append(depth_evidence)
    if breadth_evidence:
        labels.append("BREADTH_BENEFITING")
        evidence.append(breadth_evidence)

    labels = [label for label in LABEL_ORDER if label in set(labels)]
    return {
        "problem_id": rows[0]["problem_id"],
        "dataset_quality_flag": rows[0].get("dataset_quality_flag"),
        "evaluation_included": rows[0].get("evaluation_included", True),
        "primary_label": labels[0] if labels else "NO_CLEAR_PATTERN",
        "labels": "|".join(labels) if labels else "NO_CLEAR_PATTERN",
        "evidence": "; ".join(evidence),
        "note": "exploratory observed-grid label; not a ground-truth difficulty class",
    }


def classify_behaviors(config_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, int], list[Mapping[str, Any]]] = defaultdict(list)
    for row in config_rows:
        groups[(str(row["problem_id"]), int(row.get("repetition_id", 0)))].append(row)
    return [
        {**classify_problem(rows), "repetition_id": repetition_id}
        for (problem_id, repetition_id), rows in sorted(groups.items())
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, required=True)
    args = parser.parse_args()
    experiment_dir = resolve_experiment_dir(args.experiment)
    rows = classify_behaviors(read_csv(experiment_dir / "config_results.csv"))
    write_csv(experiment_dir / "behavior_classification.csv", rows)
    print(f"Wrote {len(rows)} exploratory behavior rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
