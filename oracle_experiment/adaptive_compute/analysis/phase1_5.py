"""Offline Phase 1.5 oracle-headroom, cost, and robustness analysis."""

from __future__ import annotations

import json
import random
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean, median
from typing import Any

from adaptive_compute.analysis.oracle import select_min_cost_success
from adaptive_compute.experiment_runner import derive_shared_prefix


PROFILE_ORDER = tuple((k, length) for k in (1, 2, 4) for length in (512, 1024, 2048))
BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 42_015


def _truthy(value: Any) -> bool:
    return value is True or str(value).lower() == "true"


def _profile(row: Mapping[str, Any]) -> tuple[int, int]:
    return int(row["k"]), int(row["L"])


def _label(profile: tuple[int, int]) -> str:
    return f"{profile[0]}x{profile[1]}"


def _selection_key(row: Mapping[str, Any]) -> tuple[float, float, int, int, int]:
    return (
        float(row["actual_generated_tokens"]),
        float(row["sum_sample_latency_ms"]),
        int(row["allocated_token_budget"]),
        int(row["k"]),
        int(row["L"]),
    )


def included_config_rows(rows: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [row for row in rows if _truthy(row.get("evaluation_included", True))]


def group_configurations(
    rows: Sequence[Mapping[str, Any]],
) -> dict[tuple[str, int], list[Mapping[str, Any]]]:
    groups: dict[tuple[str, int], list[Mapping[str, Any]]] = defaultdict(list)
    for row in included_config_rows(rows):
        groups[(str(row["problem_id"]), int(row.get("repetition_id", 0)))].append(row)
    return dict(sorted(groups.items()))


def choose_cheapest_correct(rows: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    """Apply the declared actual-token-first oracle tie-breaking rule."""

    return select_min_cost_success(rows, exclude_flagged=False)


def build_per_problem_preferences(
    config_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for (problem_id, repetition_id), rows in group_configurations(config_rows).items():
        by_profile = {_profile(row): row for row in rows}
        record: dict[str, Any] = {
            "problem_id": problem_id,
            "repetition_id": repetition_id,
        }
        for profile in PROFILE_ORDER:
            row = by_profile.get(profile)
            prefix = _label(profile)
            record[f"{prefix}_final_correct"] = _truthy(row.get("final_correct")) if row else None
            record[f"{prefix}_actual_generated_tokens"] = int(row["actual_generated_tokens"]) if row else None
            record[f"{prefix}_allocated_token_budget"] = int(row["allocated_token_budget"]) if row else None
            record[f"{prefix}_latency_ms"] = float(row["sum_sample_latency_ms"]) if row else None
            record[f"{prefix}_valid_answer_fraction"] = float(row["valid_answer_fraction"]) if row else None
            record[f"{prefix}_agreement"] = (
                float(row["agreement"]) if row and row.get("agreement") not in (None, "") else None
            )
        selected = choose_cheapest_correct(rows)
        if selected is None:
            record.update(
                {
                    "status": "UNSOLVED",
                    "minimum_actual_token_correct_profile": None,
                    "preferred_k": None,
                    "preferred_L": None,
                    "preferred_actual_tokens": None,
                    "preferred_allocated_budget": None,
                    "preferred_latency_ms": None,
                }
            )
        else:
            profile = _profile(selected)
            record.update(
                {
                    "status": "SOLVED",
                    "minimum_actual_token_correct_profile": _label(profile),
                    "preferred_k": profile[0],
                    "preferred_L": profile[1],
                    "preferred_actual_tokens": int(selected["actual_generated_tokens"]),
                    "preferred_allocated_budget": int(selected["allocated_token_budget"]),
                    "preferred_latency_ms": float(selected["sum_sample_latency_ms"]),
                }
            )
        output.append(record)
    return output


def build_preference_distribution(
    preference_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    counts = Counter(row.get("minimum_actual_token_correct_profile") for row in preference_rows)
    solved = sum(row.get("status") == "SOLVED" for row in preference_rows)
    output = [
        {
            "profile": _label(profile),
            "preferred_problem_count": counts[_label(profile)],
            "percentage_of_solved_problems": counts[_label(profile)] / solved if solved else None,
            "solved_problem_count": solved,
            "total_evaluated_problems": len(preference_rows),
        }
        for profile in PROFILE_ORDER
    ]
    output.append(
        {
            "profile": "UNSOLVED",
            "preferred_problem_count": len(preference_rows) - solved,
            "percentage_of_solved_problems": None,
            "solved_problem_count": solved,
            "total_evaluated_problems": len(preference_rows),
        }
    )
    return output


def _transition_metrics(
    by_k: Mapping[int, Mapping[tuple[str, int], Mapping[str, Any]]],
    lower_k: int,
    upper_k: int,
) -> dict[str, Any]:
    common = sorted(set(by_k.get(lower_k, {})) & set(by_k.get(upper_k, {})))
    eligible = [
        unit for unit in common if int(by_k[upper_k][unit].get("valid_answer_count", 0)) >= 2
    ]
    wrong_to_correct = correct_to_wrong = unchanged = other_changed = 0
    for unit in eligible:
        lower = by_k[lower_k][unit]
        upper = by_k[upper_k][unit]
        lower_correct = _truthy(lower.get("final_correct"))
        upper_correct = _truthy(upper.get("final_correct"))
        if not lower_correct and upper_correct:
            wrong_to_correct += 1
        elif lower_correct and not upper_correct:
            correct_to_wrong += 1
        elif lower.get("majority_answer") == upper.get("majority_answer"):
            unchanged += 1
        else:
            other_changed += 1
    total = len(eligible)
    return {
        "eligible": total,
        "wrong_to_correct": wrong_to_correct,
        "wrong_to_correct_rate": wrong_to_correct / total if total else None,
        "correct_to_wrong": correct_to_wrong,
        "correct_to_wrong_rate": correct_to_wrong / total if total else None,
        "answer_unchanged": unchanged,
        "answer_unchanged_rate": unchanged / total if total else None,
        "other_answer_changed": other_changed,
    }


def build_depth_before_breadth(
    config_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    included = included_config_rows(config_rows)
    lengths = sorted({int(row["L"]) for row in included})
    output: list[dict[str, Any]] = []
    for length in lengths:
        length_rows = [row for row in included if int(row["L"]) == length]
        by_k: dict[int, dict[tuple[str, int], Mapping[str, Any]]] = defaultdict(dict)
        for row in length_rows:
            by_k[int(row["k"])][(str(row["problem_id"]), int(row.get("repetition_id", 0)))] = row
        baseline_wrong = [unit for unit, row in by_k[1].items() if not _truthy(row["final_correct"])]
        record: dict[str, Any] = {
            "L": length,
            "evaluated_problems": len(by_k[1]),
            "k1_incorrect_count": len(baseline_wrong),
        }
        for k in (2, 4):
            rescued = sum(
                unit in by_k[k] and _truthy(by_k[k][unit]["final_correct"])
                for unit in baseline_wrong
            )
            record[f"k{k}_rescue_count"] = rescued
            record[f"k{k}_rescue_rate_among_k1_incorrect"] = (
                rescued / len(baseline_wrong) if baseline_wrong else None
            )
        for k in (1, 2, 4):
            rows = list(by_k[k].values())
            total_samples = sum(int(row["valid_answer_count"]) + int(row["invalid_answer_count"]) for row in rows)
            record[f"k{k}_avg_valid_answer_fraction"] = fmean(
                float(row["valid_answer_fraction"]) for row in rows
            )
            record[f"k{k}_zero_valid_problem_fraction"] = (
                sum(int(row["valid_answer_count"]) == 0 for row in rows) / len(rows)
            )
            record[f"k{k}_sample_truncation_rate"] = (
                sum(int(row["sample_truncation_count"]) for row in rows) / total_samples
            )
            record[f"k{k}_during_thinking_truncation_rate"] = (
                sum(int(row["sample_during_thinking_truncation_count"]) for row in rows)
                / total_samples
            )
            record[f"k{k}_after_thinking_truncation_rate"] = (
                sum(int(row["sample_after_thinking_truncation_count"]) for row in rows)
                / total_samples
            )
        for lower, upper in ((1, 2), (2, 4)):
            metrics = _transition_metrics(by_k, lower, upper)
            for key, value in metrics.items():
                record[f"k{lower}_to_k{upper}_{key}"] = value
        output.append(record)
    return output


def _strategy_selections(
    groups: Mapping[tuple[str, int], Sequence[Mapping[str, Any]]],
    allowed_profiles: set[tuple[int, int]],
) -> dict[tuple[str, int], Mapping[str, Any]]:
    selections: dict[tuple[str, int], Mapping[str, Any]] = {}
    for unit, rows in groups.items():
        candidates = [row for row in rows if _profile(row) in allowed_profiles]
        if not candidates:
            raise ValueError(f"no eligible profile for {unit}")
        selections[unit] = choose_cheapest_correct(candidates) or min(candidates, key=_selection_key)
    return selections


def _summarize_selections(
    strategy: str,
    selections: Mapping[tuple[str, int], Mapping[str, Any]],
    *,
    fixed_k: int | None = None,
    fixed_l: int | None = None,
) -> dict[str, Any]:
    rows = list(selections.values())
    correct = sum(_truthy(row["final_correct"]) for row in rows)
    actual = [int(row["actual_generated_tokens"]) for row in rows]
    return {
        "strategy": strategy,
        "fixed_k": fixed_k,
        "fixed_L": fixed_l,
        "num_evaluated_problems": len(rows),
        "solved_count": correct,
        "accuracy": correct / len(rows),
        "avg_actual_generated_tokens": fmean(actual),
        "median_actual_generated_tokens": median(actual),
        "avg_allocated_budget": fmean(int(row["allocated_token_budget"]) for row in rows),
        "avg_latency_ms": fmean(float(row["sum_sample_latency_ms"]) for row in rows),
    }


def build_oracle_strategies(
    config_rows: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, dict[tuple[str, int], Mapping[str, Any]]]]:
    groups = group_configurations(config_rows)
    profiles = sorted({_profile(row) for rows in groups.values() for row in rows})
    summaries: list[dict[str, Any]] = []
    selections_by_name: dict[str, dict[tuple[str, int], Mapping[str, Any]]] = {}
    for k, length in profiles:
        name = f"FIXED_{k}x{length}"
        selections = _strategy_selections(groups, {(k, length)})
        selections_by_name[name] = selections
        summaries.append(_summarize_selections("FIXED", selections, fixed_k=k, fixed_l=length))
    for length in sorted({length for _, length in profiles}):
        name = f"BREADTH_ONLY_L{length}"
        selections = _strategy_selections(groups, {profile for profile in profiles if profile[1] == length})
        selections_by_name[name] = selections
        summaries.append(_summarize_selections("BREADTH_ONLY", selections, fixed_l=length))
    for k in sorted({k for k, _ in profiles}):
        name = f"DEPTH_ONLY_k{k}"
        selections = _strategy_selections(groups, {profile for profile in profiles if profile[0] == k})
        selections_by_name[name] = selections
        summaries.append(_summarize_selections("DEPTH_ONLY", selections, fixed_k=k))
    joint = _strategy_selections(groups, set(profiles))
    selections_by_name["JOINT"] = joint
    summaries.append(_summarize_selections("JOINT", joint))
    return summaries, selections_by_name


def _best_summary(rows: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    return min(
        rows,
        key=lambda row: (
            -float(row["accuracy"]),
            float(row["avg_actual_generated_tokens"]),
            float(row["avg_latency_ms"]),
            float(row["avg_allocated_budget"]),
            int(row.get("fixed_k") or 0),
            int(row.get("fixed_L") or 0),
        ),
    )


@dataclass(frozen=True)
class _DPState:
    correct: int
    counts: tuple[int, ...]


def _pareto_states(states: Mapping[int, _DPState]) -> dict[int, _DPState]:
    output: dict[int, _DPState] = {}
    best_correct = -1
    for cost, state in sorted(states.items()):
        if state.correct > best_correct:
            output[cost] = state
            best_correct = state.correct
    return output


def optimize_budget_frontier(
    groups: Mapping[tuple[str, int], Sequence[Mapping[str, Any]]],
    allowed_profiles: set[tuple[int, int]],
) -> list[dict[str, Any]]:
    """Exact multiple-choice knapsack frontier without a zero-compute skip option."""

    profile_indices = {profile: index for index, profile in enumerate(PROFILE_ORDER)}
    states: dict[int, _DPState] = {0: _DPState(0, (0,) * len(PROFILE_ORDER))}
    for unit, rows in sorted(groups.items()):
        options = sorted(
            (row for row in rows if _profile(row) in allowed_profiles),
            key=lambda row: (_selection_key(row), _profile(row)),
        )
        if not options:
            raise ValueError(f"no frontier option for {unit}")
        expanded: dict[int, _DPState] = {}
        for prior_cost, state in states.items():
            for row in options:
                profile = _profile(row)
                cost = prior_cost + int(row["actual_generated_tokens"])
                counts = list(state.counts)
                counts[profile_indices[profile]] += 1
                candidate = _DPState(
                    state.correct + int(_truthy(row["final_correct"])), tuple(counts)
                )
                previous = expanded.get(cost)
                if previous is None or (candidate.correct, tuple(-x for x in candidate.counts)) > (
                    previous.correct,
                    tuple(-x for x in previous.counts),
                ):
                    expanded[cost] = candidate
        states = _pareto_states(expanded)
    total = len(groups)
    return [
        {
            "budget_total_tokens": cost,
            "avg_budget_tokens": cost / total,
            "max_correct": state.correct,
            "accuracy": state.correct / total,
            "selected_profile_counts": json.dumps(
                {
                    _label(profile): state.counts[index]
                    for index, profile in enumerate(PROFILE_ORDER)
                    if state.counts[index]
                },
                sort_keys=True,
            ),
        }
        for cost, state in states.items()
    ]


def _frontier_envelope(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_cost: dict[int, Mapping[str, Any]] = {}
    for row in rows:
        cost = int(row["budget_total_tokens"])
        previous = by_cost.get(cost)
        if previous is None or int(row["max_correct"]) > int(previous["max_correct"]):
            by_cost[cost] = row
    output: list[dict[str, Any]] = []
    best = -1
    for cost, row in sorted(by_cost.items()):
        if int(row["max_correct"]) > best:
            output.append(dict(row))
            best = int(row["max_correct"])
    return output


def build_budget_frontiers(config_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    groups = group_configurations(config_rows)
    profiles = sorted({_profile(row) for rows in groups.values() for row in rows})
    fixed_rows: list[dict[str, Any]] = []
    for profile in profiles:
        selections = _strategy_selections(groups, {profile})
        total_cost = sum(int(row["actual_generated_tokens"]) for row in selections.values())
        correct = sum(_truthy(row["final_correct"]) for row in selections.values())
        counts = {_label(profile): len(groups)}
        fixed_rows.append(
            {
                "strategy": "FIXED",
                "anchor": _label(profile),
                "budget_total_tokens": total_cost,
                "avg_budget_tokens": total_cost / len(groups),
                "max_correct": correct,
                "accuracy": correct / len(groups),
                "selected_profile_counts": json.dumps(counts, sort_keys=True),
            }
        )
    output = _frontier_envelope(fixed_rows)
    for strategy, anchor_values in (
        ("BREADTH_ONLY", sorted({length for _, length in profiles})),
        ("DEPTH_ONLY", sorted({k for k, _ in profiles})),
    ):
        candidate_rows: list[dict[str, Any]] = []
        for anchor in anchor_values:
            allowed = {
                profile
                for profile in profiles
                if (profile[1] == anchor if strategy == "BREADTH_ONLY" else profile[0] == anchor)
            }
            for row in optimize_budget_frontier(groups, allowed):
                candidate_rows.append({"strategy": strategy, "anchor": anchor, **row})
        output.extend(_frontier_envelope(candidate_rows))
    output.extend(
        {"strategy": "JOINT", "anchor": None, **row}
        for row in optimize_budget_frontier(groups, set(profiles))
    )
    return sorted(output, key=lambda row: (str(row["strategy"]), int(row["budget_total_tokens"])))


def build_frontier_headroom(frontier_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_strategy: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in frontier_rows:
        by_strategy[str(row["strategy"])].append(row)
    output: list[dict[str, Any]] = []
    for joint in by_strategy.get("JOINT", []):
        budget = int(joint["budget_total_tokens"])
        for strategy in ("FIXED", "BREADTH_ONLY", "DEPTH_ONLY"):
            feasible = [row for row in by_strategy[strategy] if int(row["budget_total_tokens"]) <= budget]
            if not feasible:
                continue
            matched = min(
                feasible,
                key=lambda row: (-int(row["max_correct"]), int(row["budget_total_tokens"])),
            )
            accuracy_target = int(joint["max_correct"])
            same_accuracy = [
                row for row in by_strategy[strategy] if int(row["max_correct"]) >= accuracy_target
            ]
            token_saving = (
                min(int(row["budget_total_tokens"]) for row in same_accuracy) - budget
                if same_accuracy
                else None
            )
            output.append(
                {
                    "joint_budget_total_tokens": budget,
                    "joint_avg_actual_tokens": float(joint["avg_budget_tokens"]),
                    "comparison_strategy": strategy,
                    "matching_rule": "highest accuracy feasible at or below joint total-token budget; no interpolation",
                    "comparison_tokens_used": int(matched["budget_total_tokens"]),
                    "joint_accuracy": float(joint["accuracy"]),
                    "comparison_accuracy": float(matched["accuracy"]),
                    "accuracy_gain_joint_minus_comparison": float(joint["accuracy"])
                    - float(matched["accuracy"]),
                    "token_saving_at_at_least_joint_accuracy": token_saving,
                }
            )
    return output


def _percentile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("percentile requires observations")
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def paired_problem_bootstrap(
    values_a: Mapping[Any, float],
    values_b: Mapping[Any, float],
    *,
    resamples: int = BOOTSTRAP_RESAMPLES,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    """Bootstrap the paired mean difference B-A by resampling problem units."""

    units = sorted(set(values_a) & set(values_b))
    if not units:
        raise ValueError("paired bootstrap requires common problems")
    if resamples <= 0:
        raise ValueError("resamples must be positive")
    differences = [float(values_b[unit]) - float(values_a[unit]) for unit in units]
    estimate = fmean(differences)
    rng = random.Random(seed)
    replicates = [
        fmean(differences[rng.randrange(len(differences))] for _ in differences)
        for _ in range(resamples)
    ]
    return {
        "num_problems": len(units),
        "estimate": estimate,
        "bootstrap_95_ci_low": _percentile(replicates, 0.025),
        "bootstrap_95_ci_high": _percentile(replicates, 0.975),
        "bootstrap_resamples": resamples,
        "bootstrap_seed": seed,
    }


def build_bootstrap_uncertainty(
    strategy_rows: Sequence[Mapping[str, Any]],
    selections_by_name: Mapping[str, Mapping[tuple[str, int], Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    fixed_best = _best_summary([row for row in strategy_rows if row["strategy"] == "FIXED"])
    breadth_best = _best_summary(
        [row for row in strategy_rows if row["strategy"] == "BREADTH_ONLY"]
    )
    depth_best = _best_summary(
        [row for row in strategy_rows if row["strategy"] == "DEPTH_ONLY"]
    )
    names = {
        "BEST_FIXED": f"FIXED_{int(fixed_best['fixed_k'])}x{int(fixed_best['fixed_L'])}",
        "BREADTH_ONLY": f"BREADTH_ONLY_L{int(breadth_best['fixed_L'])}",
        "DEPTH_ONLY": f"DEPTH_ONLY_k{int(depth_best['fixed_k'])}",
    }
    joint = selections_by_name["JOINT"]
    output: list[dict[str, Any]] = []

    def problem_means(
        selections: Mapping[tuple[str, int], Mapping[str, Any]], field: str
    ) -> dict[str, float]:
        grouped: dict[str, list[float]] = defaultdict(list)
        for (problem_id, repetition_id), row in selections.items():
            value = float(_truthy(row[field])) if field == "final_correct" else float(row[field])
            grouped[problem_id].append(value)
        return {problem_id: fmean(values) for problem_id, values in grouped.items()}

    for label, name in names.items():
        baseline = selections_by_name[name]
        for metric, field in (
            ("accuracy_difference", "final_correct"),
            ("avg_actual_generated_tokens_difference", "actual_generated_tokens"),
        ):
            a_values = problem_means(baseline, field)
            b_values = problem_means(joint, field)
            output.append(
                {
                    "comparison": f"JOINT_MINUS_{label}",
                    "baseline_selection": name,
                    "metric": metric,
                    **paired_problem_bootstrap(a_values, b_values),
                    "interpretation": (
                        "positive favors JOINT"
                        if metric == "accuracy_difference"
                        else "negative means JOINT uses fewer realized tokens"
                    ),
                }
            )
    return output


def build_iso_budget_extended(
    config_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    included = included_config_rows(config_rows)
    output: list[dict[str, Any]] = []
    for profile in ((4, 512), (2, 1024), (1, 2048)):
        rows = [row for row in included if _profile(row) == profile]
        total_samples = sum(
            int(row["valid_answer_count"]) + int(row["invalid_answer_count"]) for row in rows
        )
        agreements = [float(row["agreement"]) for row in rows if row.get("agreement") not in (None, "")]
        output.append(
            {
                "profile": _label(profile),
                "k": profile[0],
                "L": profile[1],
                "num_evaluated_problems": len(rows),
                "nominal_allocated_budget": profile[0] * profile[1],
                "accuracy": sum(_truthy(row["final_correct"]) for row in rows) / len(rows),
                "avg_actual_generated_tokens": fmean(int(row["actual_generated_tokens"]) for row in rows),
                "median_actual_generated_tokens": median(int(row["actual_generated_tokens"]) for row in rows),
                "avg_latency_ms": fmean(float(row["sum_sample_latency_ms"]) for row in rows),
                "truncation_rate": sum(int(row["sample_truncation_count"]) for row in rows)
                / total_samples,
                "avg_valid_answer_fraction": fmean(float(row["valid_answer_fraction"]) for row in rows),
                "avg_agreement": fmean(agreements) if profile[0] > 1 and agreements else None,
            }
        )
    return output


def build_cost_accounting(config_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    included = included_config_rows(config_rows)
    output: list[dict[str, Any]] = []
    for profile in PROFILE_ORDER:
        rows = [row for row in included if _profile(row) == profile]
        if not rows:
            continue
        correct = sum(_truthy(row["final_correct"]) for row in rows)
        total_actual = sum(int(row["actual_generated_tokens"]) for row in rows)
        avg_allocated = fmean(int(row["allocated_token_budget"]) for row in rows)
        avg_actual = fmean(int(row["actual_generated_tokens"]) for row in rows)
        output.append(
            {
                "k": profile[0],
                "L": profile[1],
                "num_evaluated_problems": len(rows),
                "correct_count": correct,
                "accuracy": correct / len(rows),
                "avg_allocated_budget": avg_allocated,
                "avg_actual_generated_tokens": avg_actual,
                "actual_to_allocated_ratio": avg_actual / avg_allocated,
                "avg_latency_ms": fmean(float(row["sum_sample_latency_ms"]) for row in rows),
                "tokens_per_correct_answer": total_actual / correct if correct else None,
            }
        )
    return output


def build_failure_analysis(
    raw_records: Sequence[Mapping[str, Any]],
    config_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    included_units = {
        (str(row["problem_id"]), int(row.get("repetition_id", 0)))
        for row in included_config_rows(config_rows)
    }
    pools: dict[tuple[str, int, int], list[Mapping[str, Any]]] = defaultdict(list)
    for row in raw_records:
        unit = (str(row["problem_id"]), int(row.get("repetition_id", 0)))
        if unit in included_units:
            pools[(unit[0], int(row["L"]), unit[1])].append(row)
    config_index = {
        (str(row["problem_id"]), int(row["L"]), int(row.get("repetition_id", 0)), int(row["k"])): row
        for row in included_config_rows(config_rows)
    }
    output: list[dict[str, Any]] = []
    for profile in PROFILE_ORDER:
        k, length = profile
        selected_samples: list[Mapping[str, Any]] = []
        for (problem_id, pool_l, repetition_id), pool in pools.items():
            if pool_l == length:
                selected_samples.extend(derive_shared_prefix(pool, k))
        counts = Counter(str(row.get("failure_type")) for row in selected_samples)
        configs = [
            row
            for (problem_id, row_l, repetition_id, row_k), row in config_index.items()
            if row_l == length and row_k == k
        ]
        total = len(selected_samples)
        record: dict[str, Any] = {
            "k": k,
            "L": length,
            "evaluated_problems": len(configs),
            "total_samples": total,
        }
        for failure_type in (
            "truncated_before_answer",
            "truncated_after_reasoning",
            "wrong_answer",
            "parse_failure",
            "generation_error",
        ):
            record[f"{failure_type}_count"] = counts[failure_type]
            record[f"{failure_type}_rate"] = counts[failure_type] / total if total else None
        no_valid = sum(int(row["valid_answer_count"]) == 0 for row in configs)
        record["no_valid_majority_count"] = no_valid
        record["no_valid_majority_rate"] = no_valid / len(configs) if configs else None
        output.append(record)
    return output


def generate_phase1_5_plots(
    output_dir: Path,
    preference_rows: Sequence[Mapping[str, Any]],
    depth_rows: Sequence[Mapping[str, Any]],
    frontier_rows: Sequence[Mapping[str, Any]],
    iso_rows: Sequence[Mapping[str, Any]],
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = [str(row["profile"]) for row in preference_rows]
    counts = [int(row["preferred_problem_count"]) for row in preference_rows]
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.bar(labels, counts, color="#4C78A8")
    ax.set_ylabel("Problems")
    ax.set_title("Cheapest-correct joint-oracle profile preferences")
    ax.tick_params(axis="x", rotation=35)
    fig.tight_layout()
    fig.savefig(output_dir / "profile_preference_distribution.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    lengths = [int(row["L"]) for row in depth_rows]
    for k, marker in ((2, "o"), (4, "s")):
        axes[0].plot(
            lengths,
            [float(row[f"k{k}_rescue_rate_among_k1_incorrect"]) for row in depth_rows],
            marker=marker,
            label=f"k=1 to k={k}",
        )
    for k in (1, 2, 4):
        axes[1].plot(
            lengths,
            [float(row[f"k{k}_avg_valid_answer_fraction"]) for row in depth_rows],
            marker="o",
            label=f"k={k}",
        )
        axes[2].plot(
            lengths,
            [float(row[f"k{k}_sample_truncation_rate"]) for row in depth_rows],
            marker="o",
            label=f"k={k}",
        )
    axes[0].set_title("Breadth rescue among k=1 failures")
    axes[1].set_title("Valid-answer availability")
    axes[2].set_title("Sample truncation")
    for ax in axes:
        ax.set_xlabel("L")
        ax.set_ylim(-0.03, 1.03)
        ax.legend(fontsize=8)
    fig.suptitle("Exploratory evidence for a depth-before-breadth hypothesis")
    fig.tight_layout()
    fig.savefig(output_dir / "depth_before_breadth.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5.5))
    for strategy in ("FIXED", "BREADTH_ONLY", "DEPTH_ONLY", "JOINT"):
        rows = sorted(
            (row for row in frontier_rows if row["strategy"] == strategy),
            key=lambda row: float(row["avg_budget_tokens"]),
        )
        ax.step(
            [float(row["avg_budget_tokens"]) for row in rows],
            [float(row["accuracy"]) for row in rows],
            where="post",
            marker="o",
            markersize=3,
            label=strategy,
        )
    ax.set_xlabel("Average realized generated tokens")
    ax.set_ylabel("Oracle accuracy upper bound")
    ax.set_ylim(-0.03, 1.03)
    ax.set_title("Budget-constrained oracle frontiers (no skip option)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "oracle_budget_frontier.png", dpi=180)
    plt.close(fig)

    labels = [str(row["profile"]) for row in iso_rows]
    actual = [float(row["avg_actual_generated_tokens"]) for row in iso_rows]
    accuracy = [float(row["accuracy"]) for row in iso_rows]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.bar(labels, actual, color="#4C78A8", label="Actual generated tokens")
    ax.axhline(2048, color="gray", linestyle="--", label="Nominal k x L = 2048")
    ax.set_ylabel("Tokens per problem")
    second = ax.twinx()
    second.plot(labels, accuracy, color="#E45756", marker="o", label="Accuracy")
    second.set_ylabel("Accuracy")
    second.set_ylim(0, 1)
    handles, names = ax.get_legend_handles_labels()
    handles2, names2 = second.get_legend_handles_labels()
    ax.legend(handles + handles2, names + names2, loc="upper right")
    ax.bar_label(bars, fmt="%.0f")
    ax.set_title("Same nominal budget, different realized behavior")
    fig.tight_layout()
    fig.savefig(output_dir / "iso_budget_2048_extended.png", dpi=180)
    plt.close(fig)


def _markdown_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> list[str]:
    return [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
        *("| " + " | ".join(str(value) for value in row) + " |" for row in rows),
    ]


def build_phase1_5_report(
    *,
    manifest: Mapping[str, Any],
    preference_distribution: Sequence[Mapping[str, Any]],
    depth_rows: Sequence[Mapping[str, Any]],
    cost_rows: Sequence[Mapping[str, Any]],
    strategy_rows: Sequence[Mapping[str, Any]],
    frontier_rows: Sequence[Mapping[str, Any]],
    headroom_rows: Sequence[Mapping[str, Any]],
    bootstrap_rows: Sequence[Mapping[str, Any]],
    iso_rows: Sequence[Mapping[str, Any]],
    failure_rows: Sequence[Mapping[str, Any]],
) -> str:
    evaluated = int(cost_rows[0]["num_evaluated_problems"])
    solved = int(preference_distribution[0]["solved_problem_count"])
    nonzero_preferences = [
        row
        for row in preference_distribution
        if row["profile"] != "UNSOLVED" and int(row["preferred_problem_count"]) > 0
    ]
    max_joint = min(
        (row for row in frontier_rows if row["strategy"] == "JOINT"),
        key=lambda row: (-float(row["accuracy"]), int(row["budget_total_tokens"])),
    )
    max_joint_matches = [
        row
        for row in headroom_rows
        if int(row["joint_budget_total_tokens"]) == int(max_joint["budget_total_tokens"])
    ]
    lines = [
        "# Phase 1.5 — Oracle headroom, cost, and robustness",
        "",
        "## 1. Experimental context",
        "",
        f"This offline analysis uses `{manifest['experiment_id']}`: {manifest['num_problems']} sampled "
        f"GSM8K problems, one repetition, and the 3x3 `(k,L)` grid. After the manual dataset-quality "
        f"exclusion, {evaluated} problems are evaluated. No model inference is performed here.",
        "",
        "All adaptive selections below are retrospective oracle upper bounds, not deployable policies.",
        "",
        "## 2. Key results from the original 3x3 grid",
        "",
        *_markdown_table(
            ["Profile", "Accuracy", "Avg actual tokens", "Avg allocated", "Avg latency (s)"],
            [
                [
                    _label((int(row["k"]), int(row["L"]))),
                    f"{float(row['accuracy']):.3f}",
                    f"{float(row['avg_actual_generated_tokens']):.1f}",
                    f"{float(row['avg_allocated_budget']):.0f}",
                    f"{float(row['avg_latency_ms']) / 1000:.1f}",
                ]
                for row in cost_rows
            ],
        ),
        "",
        "Observed accuracy rises strongly from L=512 to L=1024 at every k. Existing paired tests "
        "support those three directional depth comparisons after Holm correction. Breadth changes are "
        "descriptively positive but statistically inconclusive in the current 29-problem evaluation.",
        "",
        "## 3. Per-problem profile preference",
        "",
        f"The joint cheapest-correct oracle solves {solved}/{evaluated} problems. "
        f"Solved problems select {len(nonzero_preferences)} distinct profiles; raw counts are:",
        "",
        *_markdown_table(
            ["Profile", "Preferred count", "% of solved"],
            [
                [
                    row["profile"],
                    row["preferred_problem_count"],
                    "—"
                    if row["percentage_of_solved_problems"] in (None, "")
                    else f"{100 * float(row['percentage_of_solved_problems']):.1f}%",
                ]
                for row in preference_distribution
            ],
        ),
        "",
        "This distribution describes observed hindsight preferences only; no threshold is imposed for "
        "calling the diversity meaningful.",
        "",
        "## 4. Depth-before-breadth exploratory analysis",
        "",
        *_markdown_table(
            ["L", "k=1 failures", "Rescued by k=2", "Rescued by k=4", "k=4 valid fraction", "k=4 truncation"],
            [
                [
                    row["L"],
                    row["k1_incorrect_count"],
                    f"{int(row['k2_rescue_count'])} ({100 * float(row['k2_rescue_rate_among_k1_incorrect']):.1f}%)",
                    f"{int(row['k4_rescue_count'])} ({100 * float(row['k4_rescue_rate_among_k1_incorrect']):.1f}%)",
                    f"{float(row['k4_avg_valid_answer_fraction']):.3f}",
                    f"{float(row['k4_sample_truncation_rate']):.3f}",
                ]
                for row in depth_rows
            ],
        ),
        "",
        "These are exploratory observations consistent or inconsistent with a depth-before-breadth "
        "hypothesis; they are not proof that depth must precede breadth.",
        "",
        "## 5. Cost accounting",
        "",
        "Allocated budget (`k*L`), realized generated tokens, and latency are retained as separate metrics. "
        "The frontier uses realized generated tokens as its primary constraint; latency is secondary context.",
        "",
        "## 6. Fixed vs breadth-only vs depth-only vs joint oracle",
        "",
        *_markdown_table(
            ["Strategy", "Anchor", "Solved", "Accuracy", "Avg actual", "Median actual", "Avg latency (s)"],
            [
                [
                    row["strategy"],
                    f"k={row['fixed_k']}" if row.get("fixed_k") not in (None, "") and row.get("fixed_L") in (None, "")
                    else f"L={row['fixed_L']}" if row.get("fixed_L") not in (None, "") and row.get("fixed_k") in (None, "")
                    else _label((int(row["fixed_k"]), int(row["fixed_L"])))
                    if row.get("fixed_k") not in (None, "")
                    else "all profiles",
                    row["solved_count"],
                    f"{float(row['accuracy']):.3f}",
                    f"{float(row['avg_actual_generated_tokens']):.1f}",
                    f"{float(row['median_actual_generated_tokens']):.1f}",
                    f"{float(row['avg_latency_ms']) / 1000:.1f}",
                ]
                for row in strategy_rows
            ],
        ),
        "",
        "All three breadth anchors and all three depth anchors are reported. Any 'best' anchor used in "
        "bootstrap summaries is selected by accuracy first and then observed cost, and is not silently "
        "substituted for the full anchor table.",
        "",
        "## 7. Budget-constrained oracle frontier",
        "",
        "The exact multiple-choice knapsack analysis selects exactly one allowed profile per problem. "
        "There is no zero-compute skip option. FIXED is the nondominated envelope of the nine global fixed "
        "profiles; breadth-only and depth-only are envelopes over their explicitly reported anchors.",
        "",
        *_markdown_table(
            ["Strategy", "Frontier points", "Maximum observed accuracy", "Actual tokens at first maximum"],
            [
                [
                    strategy,
                    len(rows),
                    f"{max(float(row['accuracy']) for row in rows):.3f}",
                    min(
                        int(row["budget_total_tokens"])
                        for row in rows
                        if float(row["accuracy"]) == max(float(item["accuracy"]) for item in rows)
                    ),
                ]
                for strategy in ("FIXED", "BREADTH_ONLY", "DEPTH_ONLY", "JOINT")
                for rows in [[row for row in frontier_rows if row["strategy"] == strategy]]
            ],
        ),
        "",
        "Comparable-point differences are stored in `oracle_headroom.csv`. At each joint budget, the "
        "comparison uses the highest-accuracy point feasible at or below that total realized-token budget; "
        "no interpolation or extrapolation is used.",
        "",
        f"At the cheapest joint point reaching its maximum observed accuracy "
        f"({float(max_joint['accuracy']):.3f} at {float(max_joint['avg_budget_tokens']):.1f} actual "
        "tokens/problem), the compute-matched comparisons are:",
        "",
        *_markdown_table(
            ["Comparison", "Accuracy at or below joint budget", "Joint accuracy gain", "Tokens saved at >= joint accuracy"],
            [
                [
                    row["comparison_strategy"],
                    f"{float(row['comparison_accuracy']):.3f}",
                    f"{float(row['accuracy_gain_joint_minus_comparison']):+.3f}",
                    row["token_saving_at_at_least_joint_accuracy"],
                ]
                for row in max_joint_matches
            ],
        ),
        "",
        "These are hindsight frontier differences, not estimates of a learned controller's performance.",
        "",
        "## 8. Iso-budget comparison",
        "",
        *_markdown_table(
            ["Profile", "Nominal", "Accuracy", "Avg actual", "Median actual", "Truncation", "Valid fraction"],
            [
                [
                    row["profile"],
                    row["nominal_allocated_budget"],
                    f"{float(row['accuracy']):.3f}",
                    f"{float(row['avg_actual_generated_tokens']):.1f}",
                    f"{float(row['median_actual_generated_tokens']):.1f}",
                    f"{float(row['truncation_rate']):.3f}",
                    f"{float(row['avg_valid_answer_fraction']):.3f}",
                ]
                for row in iso_rows
            ],
        ),
        "",
        "The observed result is that the same nominal budget does not imply the same inference behavior. "
        "It does not establish that depth is universally better than breadth.",
        "",
        "## 9. Failure analysis",
        "",
        *_markdown_table(
            ["Profile", "Before answer", "After reasoning", "Wrong", "Parse", "Generation", "No valid majority"],
            [
                [
                    _label((int(row["k"]), int(row["L"]))),
                    row["truncated_before_answer_count"],
                    row["truncated_after_reasoning_count"],
                    row["wrong_answer_count"],
                    row["parse_failure_count"],
                    row["generation_error_count"],
                    row["no_valid_majority_count"],
                ]
                for row in failure_rows
            ],
        ),
        "",
        "Increasing L changes the observed mix from budget-truncated responses toward completed responses; "
        "strict parse failures and genuinely wrong answers remain distinguishable in the CSV.",
        "",
        "## 10. Limitations",
        "",
        f"- Only {evaluated} evaluated problems and one stochastic repetition are available.",
        "- Oracle choices use ground-truth outcomes retrospectively and cannot be deployed directly.",
        "- Bootstrap intervals resample whole problems and are conditional on the anchors selected from this dataset.",
        "- Optimized frontier points are post-hoc discrete upper bounds; no confidence interval is attached to the full frontier.",
        "- Shared sample prefixes couple k profiles by design; paired analysis is required.",
        "- Results concern this model revision, prompt, parser, dataset subset, and sampling configuration.",
        "",
        "## 11. Decision options for Phase 2",
        "",
        "The evidence should be read through `phase2_decision.md`. A joint controller is justified only if "
        "the joint frontier supplies additional accuracy or token savings over both restricted action spaces "
        "at comparable realized compute. The existence of a joint oracle alone is not sufficient.",
        "",
        "## Bootstrap uncertainty",
        "",
        *_markdown_table(
            ["Comparison", "Metric", "Estimate", "Bootstrap 95% CI"],
            [
                [
                    row["comparison"],
                    row["metric"],
                    f"{float(row['estimate']):.3f}",
                    f"[{float(row['bootstrap_95_ci_low']):.3f}, {float(row['bootstrap_95_ci_high']):.3f}]",
                ]
                for row in bootstrap_rows
            ],
        ),
        "",
    ]
    return "\n".join(lines)


def build_phase2_decision_report(
    preference_distribution: Sequence[Mapping[str, Any]],
    depth_rows: Sequence[Mapping[str, Any]],
    strategy_rows: Sequence[Mapping[str, Any]],
    bootstrap_rows: Sequence[Mapping[str, Any]],
) -> str:
    nonzero = [
        row
        for row in preference_distribution
        if row["profile"] != "UNSOLVED" and int(row["preferred_problem_count"]) > 0
    ]
    joint = next(row for row in strategy_rows if row["strategy"] == "JOINT")
    best_depth = _best_summary([row for row in strategy_rows if row["strategy"] == "DEPTH_ONLY"])
    best_breadth = _best_summary([row for row in strategy_rows if row["strategy"] == "BREADTH_ONLY"])
    bootstrap = {(row["comparison"], row["metric"]): row for row in bootstrap_rows}
    return "\n".join(
        [
            "# Phase 2 decision scenarios",
            "",
            "This document presents evidence for three possible directions. It deliberately does not make "
            "the thesis decision for the researcher.",
            "",
            "## Scenario A — Joint controller justified",
            "",
            "Evidence to require: diverse cheapest-correct `(k,L)` preferences and a joint budget frontier "
            "materially above both restricted frontiers at comparable realized token cost.",
            "",
            f"Current observations: {len(nonzero)} profiles have at least one cheapest-correct selection. "
            f"The unconstrained joint oracle accuracy is {float(joint['accuracy']):.3f}. "
            f"The best depth-only and breadth-only anchor accuracies are {float(best_depth['accuracy']):.3f} "
            f"and {float(best_breadth['accuracy']):.3f}. The budget-matched evidence must be judged from "
            "`oracle_budget_frontier.csv` and `oracle_headroom.csv`, not from these unconstrained values alone.",
            "",
            "Suggested direction if the frontier evidence is compelling: a lightweight `x -> (k,L)` joint controller.",
            "",
            "## Scenario B — Depth dominates",
            "",
            "Evidence to require: depth-only recovers nearly all joint headroom at comparable cost, while "
            "breadth rescue remains limited across L.",
            "",
            "Current breadth rescue observations among k=1 failures: "
            + "; ".join(
                f"L={row['L']}: k=2 {100 * float(row['k2_rescue_rate_among_k1_incorrect']):.1f}%, "
                f"k=4 {100 * float(row['k4_rescue_rate_among_k1_incorrect']):.1f}%"
                for row in depth_rows
            )
            + ". These rates are descriptive and must be read with valid-answer availability and truncation.",
            "",
            "Suggested direction if restricted-frontier performance is close to joint: adaptive depth or depth-first allocation.",
            "",
            "## Scenario C — Evidence insufficient",
            "",
            "Evidence: uncertainty intervals include small or zero gaps, frontier differences are inconsistent, "
            "or one repetition leaves stochastic sensitivity unresolved.",
            "",
            "Current conditional bootstrap gaps for joint versus restricted oracles are:",
            "",
            *_markdown_table(
                ["Comparison", "Accuracy gap (95% CI)", "Actual-token gap (95% CI)"],
                [
                    [
                        label,
                        f"{float(bootstrap[(label, 'accuracy_difference')]['estimate']):.3f} "
                        f"[{float(bootstrap[(label, 'accuracy_difference')]['bootstrap_95_ci_low']):.3f}, "
                        f"{float(bootstrap[(label, 'accuracy_difference')]['bootstrap_95_ci_high']):.3f}]",
                        f"{float(bootstrap[(label, 'avg_actual_generated_tokens_difference')]['estimate']):.1f} "
                        f"[{float(bootstrap[(label, 'avg_actual_generated_tokens_difference')]['bootstrap_95_ci_low']):.1f}, "
                        f"{float(bootstrap[(label, 'avg_actual_generated_tokens_difference')]['bootstrap_95_ci_high']):.1f}]",
                    ]
                    for label in (
                        "JOINT_MINUS_BEST_FIXED",
                        "JOINT_MINUS_BREADTH_ONLY",
                        "JOINT_MINUS_DEPTH_ONLY",
                    )
                ],
            ),
            "",
            "Suggested action if uncertainty remains decision-relevant: run the confirmatory dataset-scale or "
            "stochastic-robustness experiment before implementing a controller.",
            "",
            "## Researcher decision",
            "",
            "Choose the Phase 2 direction only after reviewing the comparable-cost frontier and its discrete "
            "headroom table. A joint oracle's existence is not evidence that a learnable joint allocator will work.",
            "",
        ]
    )
