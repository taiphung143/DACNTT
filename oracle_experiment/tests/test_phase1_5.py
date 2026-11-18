from adaptive_compute.analysis.phase1_5 import (
    build_bootstrap_uncertainty,
    build_cost_accounting,
    build_depth_before_breadth,
    build_oracle_strategies,
    build_per_problem_preferences,
    optimize_budget_frontier,
    paired_problem_bootstrap,
)


PROFILES = tuple((k, length) for k in (1, 2, 4) for length in (512, 1024, 2048))


def _row(
    problem: str,
    k: int,
    length: int,
    *,
    correct: bool,
    tokens: int | None = None,
    included: bool = True,
    valid: int | None = None,
) -> dict:
    valid_count = int(correct) if valid is None else valid
    return {
        "problem_id": problem,
        "repetition_id": 0,
        "k": k,
        "L": length,
        "final_correct": correct,
        "evaluation_included": included,
        "majority_answer": "7" if valid_count else "",
        "valid_answer_count": valid_count,
        "invalid_answer_count": k - valid_count,
        "valid_answer_fraction": valid_count / k,
        "agreement": 1.0 if valid_count else "",
        "actual_generated_tokens": tokens if tokens is not None else k * length,
        "allocated_token_budget": k * length,
        "sum_sample_latency_ms": float(tokens if tokens is not None else k * length),
        "sample_truncation_count": k - valid_count,
        "sample_during_thinking_truncation_count": k - valid_count,
        "sample_after_thinking_truncation_count": 0,
    }


def _full_grid() -> list[dict]:
    rows = []
    for problem in ("p1", "p2"):
        for k, length in PROFILES:
            correct = (problem == "p1" and length >= 1024) or (problem == "p2" and k >= 2)
            rows.append(_row(problem, k, length, correct=correct))
    for k, length in PROFILES:
        rows.append(_row("flagged", k, length, correct=True, included=False))
    return rows


def test_cheapest_correct_profile_and_flag_exclusion() -> None:
    rows = _full_grid()
    preferences = build_per_problem_preferences(rows)
    assert {row["problem_id"] for row in preferences} == {"p1", "p2"}
    by_problem = {row["problem_id"]: row for row in preferences}
    assert by_problem["p1"]["minimum_actual_token_correct_profile"] == "1x1024"
    assert by_problem["p2"]["minimum_actual_token_correct_profile"] == "2x512"


def test_all_oracle_anchors_and_joint_are_evaluated() -> None:
    summaries, selections = build_oracle_strategies(_full_grid())
    assert len([row for row in summaries if row["strategy"] == "FIXED"]) == 9
    assert {row["fixed_L"] for row in summaries if row["strategy"] == "BREADTH_ONLY"} == {512, 1024, 2048}
    assert {row["fixed_k"] for row in summaries if row["strategy"] == "DEPTH_ONLY"} == {1, 2, 4}
    joint = [row for row in summaries if row["strategy"] == "JOINT"]
    assert len(joint) == 1
    assert joint[0]["accuracy"] == 1.0
    assert len(selections["JOINT"]) == 2


def test_budget_frontier_is_exact_and_pareto_nondominated() -> None:
    groups = {
        ("p1", 0): [
            _row("p1", 1, 512, correct=False, tokens=1),
            _row("p1", 2, 512, correct=True, tokens=4),
        ],
        ("p2", 0): [
            _row("p2", 1, 512, correct=True, tokens=1),
            _row("p2", 2, 512, correct=True, tokens=4),
        ],
    }
    frontier = optimize_budget_frontier(groups, {(1, 512), (2, 512)})
    assert [(row["budget_total_tokens"], row["max_correct"]) for row in frontier] == [(2, 1), (5, 2)]
    assert all(
        not (
            left["budget_total_tokens"] <= right["budget_total_tokens"]
            and left["max_correct"] >= right["max_correct"]
        )
        for index, left in enumerate(frontier)
        for right in frontier[index + 1 :]
    )


def test_actual_token_cost_accounting_and_zero_correct_guard() -> None:
    rows = [
        _row("p1", 1, 512, correct=False, tokens=100),
        _row("p2", 1, 512, correct=False, tokens=200),
    ]
    result = build_cost_accounting(rows)[0]
    assert result["avg_actual_generated_tokens"] == 150
    assert result["avg_allocated_budget"] == 512
    assert result["tokens_per_correct_answer"] is None


def test_bootstrap_resamples_paired_problem_units_deterministically() -> None:
    a = {("p1", 0): 1.0, ("p2", 0): 2.0}
    b = {("p1", 0): 2.0, ("p2", 0): 5.0}
    first = paired_problem_bootstrap(a, b, resamples=1000, seed=9)
    second = paired_problem_bootstrap(a, b, resamples=1000, seed=9)
    assert first == second
    assert first["estimate"] == 2.0
    assert first["bootstrap_95_ci_low"] == 1.0
    assert first["bootstrap_95_ci_high"] == 3.0


def test_oracle_bootstrap_clusters_repetitions_within_problem() -> None:
    strategy_rows = [
        {"strategy": "FIXED", "fixed_k": 1, "fixed_L": 512, "accuracy": 0.5, "avg_actual_generated_tokens": 10, "avg_latency_ms": 1, "avg_allocated_budget": 512},
        {"strategy": "BREADTH_ONLY", "fixed_k": None, "fixed_L": 512, "accuracy": 0.5, "avg_actual_generated_tokens": 10, "avg_latency_ms": 1, "avg_allocated_budget": 512},
        {"strategy": "DEPTH_ONLY", "fixed_k": 1, "fixed_L": None, "accuracy": 0.5, "avg_actual_generated_tokens": 10, "avg_latency_ms": 1, "avg_allocated_budget": 512},
    ]
    selections = {}
    for name in ("FIXED_1x512", "BREADTH_ONLY_L512", "DEPTH_ONLY_k1", "JOINT"):
        selections[name] = {
            (problem, repetition): {
                "final_correct": problem == "p1",
                "actual_generated_tokens": 10 + repetition,
            }
            for problem in ("p1", "p2")
            for repetition in (0, 1)
        }
    rows = build_bootstrap_uncertainty(strategy_rows, selections)
    assert {row["num_problems"] for row in rows} == {2}


def test_depth_before_breadth_rescue_rates() -> None:
    rows = []
    for problem in ("p1", "p2"):
        rows.extend(
            [
                _row(problem, 1, 512, correct=False, valid=0),
                _row(problem, 2, 512, correct=problem == "p1", valid=2),
                _row(problem, 4, 512, correct=True, valid=4),
            ]
        )
    result = build_depth_before_breadth(rows)[0]
    assert result["k2_rescue_rate_among_k1_incorrect"] == 0.5
    assert result["k4_rescue_rate_among_k1_incorrect"] == 1.0
    assert result["k1_to_k2_wrong_to_correct"] == 1
