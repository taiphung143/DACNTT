"""Paired statistical inference for fixed grid profiles."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from math import comb, sqrt
from typing import Any


MIN_INFERENCE_PROBLEMS = 20
Z_95 = 1.959963984540054


def _truthy(value: Any) -> bool:
    return value is True or str(value).lower() == "true"


def wilson_interval(successes: int, total: int, *, z: float = Z_95) -> tuple[float, float]:
    """Return a Wilson score interval for a binomial proportion."""

    if total <= 0:
        raise ValueError("total must be positive")
    if not 0 <= successes <= total:
        raise ValueError("successes must be between zero and total")
    proportion = successes / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    margin = z * sqrt(proportion * (1 - proportion) / total + z * z / (4 * total * total)) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)


def exact_mcnemar_p(a_only: int, b_only: int) -> float:
    """Two-sided exact McNemar p-value from discordant paired outcomes."""

    if a_only < 0 or b_only < 0:
        raise ValueError("discordant counts must be non-negative")
    discordant = a_only + b_only
    if discordant == 0:
        return 1.0
    tail = sum(comb(discordant, index) for index in range(min(a_only, b_only) + 1))
    return min(1.0, 2 * tail / (2**discordant))


def holm_adjust(p_values: Sequence[float]) -> list[float]:
    """Return Holm family-wise adjusted p-values in original order."""

    count = len(p_values)
    adjusted = [1.0] * count
    running_max = 0.0
    for rank, index in enumerate(sorted(range(count), key=lambda item: p_values[item])):
        candidate = min(1.0, (count - rank) * float(p_values[index]))
        running_max = max(running_max, candidate)
        adjusted[index] = running_max
    return adjusted


def _included_rows(config_rows: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [row for row in config_rows if _truthy(row.get("evaluation_included", True))]


def build_accuracy_intervals(
    config_rows: Sequence[Mapping[str, Any]],
    *,
    min_problems: int = MIN_INFERENCE_PROBLEMS,
) -> list[dict[str, Any]]:
    """Build profile accuracy estimates with 95% Wilson intervals."""

    groups: dict[tuple[int, int], list[Mapping[str, Any]]] = defaultdict(list)
    for row in _included_rows(config_rows):
        groups[(int(row["k"]), int(row["L"]))].append(row)

    output: list[dict[str, Any]] = []
    for (k, length), rows in sorted(groups.items()):
        successes = sum(_truthy(row.get("final_correct")) for row in rows)
        total = len(rows)
        lower, upper = wilson_interval(successes, total)
        output.append(
            {
                "k": k,
                "L": length,
                "num_evaluated_problems": total,
                "num_correct": successes,
                "accuracy": successes / total,
                "ci_95_low": lower,
                "ci_95_high": upper,
                "inference_status": "ready" if total >= min_problems else "insufficient_sample",
                "minimum_problem_threshold": min_problems,
            }
        )
    return output


def _profile_outcomes(
    config_rows: Sequence[Mapping[str, Any]],
) -> dict[tuple[int, int], dict[tuple[str, int], bool]]:
    outcomes: dict[tuple[int, int], dict[tuple[str, int], bool]] = defaultdict(dict)
    for row in _included_rows(config_rows):
        profile = (int(row["k"]), int(row["L"]))
        unit = (str(row["problem_id"]), int(row.get("repetition_id", 0)))
        outcomes[profile][unit] = _truthy(row.get("final_correct"))
    return outcomes


def _planned_pairs(profiles: set[tuple[int, int]]) -> list[tuple[str, tuple[int, int], tuple[int, int]]]:
    pairs: list[tuple[str, tuple[int, int], tuple[int, int]]] = []
    k_values = sorted({k for k, _ in profiles})
    l_values = sorted({length for _, length in profiles})
    for k in k_values:
        available = [length for length in l_values if (k, length) in profiles]
        pairs.extend(("depth", (k, left), (k, right)) for left, right in zip(available, available[1:]))
    for length in l_values:
        available = [k for k in k_values if (k, length) in profiles]
        pairs.extend(("breadth", (left, length), (right, length)) for left, right in zip(available, available[1:]))
    iso = [profile for profile in ((4, 512), (2, 1024), (1, 2048)) if profile in profiles]
    pairs.extend(("iso_budget_2048", left, right) for index, left in enumerate(iso) for right in iso[index + 1 :])
    return pairs


def build_paired_comparisons(
    config_rows: Sequence[Mapping[str, Any]],
    *,
    min_problems: int = MIN_INFERENCE_PROBLEMS,
) -> list[dict[str, Any]]:
    """Compare planned profiles with exact paired tests and Holm correction."""

    outcomes = _profile_outcomes(config_rows)
    rows: list[dict[str, Any]] = []
    for family, profile_a, profile_b in _planned_pairs(set(outcomes)):
        common = sorted(set(outcomes[profile_a]) & set(outcomes[profile_b]))
        a_values = [outcomes[profile_a][unit] for unit in common]
        b_values = [outcomes[profile_b][unit] for unit in common]
        both_correct = sum(a and b for a, b in zip(a_values, b_values, strict=True))
        both_wrong = sum(not a and not b for a, b in zip(a_values, b_values, strict=True))
        a_only = sum(a and not b for a, b in zip(a_values, b_values, strict=True))
        b_only = sum(not a and b for a, b in zip(a_values, b_values, strict=True))
        total = len(common)
        rows.append(
            {
                "comparison_family": family,
                "profile_a": f"{profile_a[0]}x{profile_a[1]}",
                "profile_b": f"{profile_b[0]}x{profile_b[1]}",
                "num_paired_problems": total,
                "accuracy_a": sum(a_values) / total if total else None,
                "accuracy_b": sum(b_values) / total if total else None,
                "accuracy_difference_b_minus_a": (sum(b_values) - sum(a_values)) / total if total else None,
                "both_correct": both_correct,
                "both_wrong": both_wrong,
                "a_only_correct": a_only,
                "b_only_correct": b_only,
                "discordant_pairs": a_only + b_only,
                "mcnemar_exact_p": exact_mcnemar_p(a_only, b_only),
                "minimum_problem_threshold": min_problems,
            }
        )

    by_family: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        by_family[str(row["comparison_family"])].append(index)
    for indices in by_family.values():
        adjusted = holm_adjust([float(rows[index]["mcnemar_exact_p"]) for index in indices])
        for index, adjusted_p in zip(indices, adjusted, strict=True):
            row = rows[index]
            row["holm_adjusted_p"] = adjusted_p
            enough = int(row["num_paired_problems"]) >= min_problems
            row["statistically_significant_0_05"] = enough and adjusted_p < 0.05
            row["inference_status"] = (
                "insufficient_sample"
                if not enough
                else "significant"
                if adjusted_p < 0.05
                else "inconclusive"
            )
    return rows


def build_statistical_report(
    accuracy_rows: Sequence[Mapping[str, Any]],
    comparison_rows: Sequence[Mapping[str, Any]],
) -> str:
    """Render a compact, auditable Markdown inference report."""

    lines = [
        "# Statistical inference report",
        "",
        "Flagged dataset items are excluded. Accuracy intervals are Wilson 95% intervals. "
        "Comparisons use paired exact McNemar tests on the same problem/repetition units, "
        "with Holm correction within each planned comparison family.",
        "",
        "A minimum of 20 evaluated problems is required before a result is labelled inferentially ready. "
        "This guard is not a power guarantee; inconclusive does not mean equivalent.",
        "",
        "## Profile estimates",
        "",
        "| Profile | n | Accuracy | 95% CI | Status |",
        "|---|---:|---:|---:|---|",
    ]
    for row in accuracy_rows:
        lines.append(
            f"| {row['k']}x{row['L']} | {row['num_evaluated_problems']} | "
            f"{float(row['accuracy']):.3f} | "
            f"[{float(row['ci_95_low']):.3f}, {float(row['ci_95_high']):.3f}] | "
            f"{row['inference_status']} |"
        )
    lines.extend(
        [
            "",
            "## Planned paired comparisons",
            "",
            "| Family | A -> B | n | Accuracy difference | Exact p | Holm p | Status |",
            "|---|---|---:|---:|---:|---:|---|",
        ]
    )
    for row in comparison_rows:
        difference = row.get("accuracy_difference_b_minus_a")
        lines.append(
            f"| {row['comparison_family']} | {row['profile_a']} -> {row['profile_b']} | "
            f"{row['num_paired_problems']} | "
            f"{float(difference):+.3f} | "
            f"{float(row['mcnemar_exact_p']):.4g} | "
            f"{float(row['holm_adjusted_p']):.4g} | {row['inference_status']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation rule",
            "",
            "Only rows marked `significant` support a directional accuracy claim at family-wise alpha=0.05. "
            "Rows marked `inconclusive` do not establish equality or equivalence. Compute and latency remain "
            "descriptive outcomes and should be considered alongside accuracy.",
            "",
        ]
    )
    return "\n".join(lines)
