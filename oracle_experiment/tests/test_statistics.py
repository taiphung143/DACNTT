from math import isclose

from adaptive_compute.analysis.statistics import (
    build_accuracy_intervals,
    build_paired_comparisons,
    exact_mcnemar_p,
    holm_adjust,
    wilson_interval,
)


def _row(problem: str, k: int, length: int, correct: bool, *, included: bool = True) -> dict:
    return {
        "problem_id": problem,
        "repetition_id": 0,
        "k": k,
        "L": length,
        "final_correct": correct,
        "evaluation_included": included,
    }


def test_wilson_interval_is_bounded_for_perfect_small_sample() -> None:
    lower, upper = wilson_interval(2, 2)
    assert 0.34 < lower < 0.35
    assert upper == 1.0


def test_exact_mcnemar_uses_only_discordant_pairs() -> None:
    assert exact_mcnemar_p(0, 0) == 1.0
    assert isclose(exact_mcnemar_p(0, 5), 0.0625)
    assert exact_mcnemar_p(2, 3) == 1.0


def test_holm_adjustment_preserves_original_order_and_monotonicity() -> None:
    adjusted = holm_adjust([0.04, 0.01, 0.03])
    assert adjusted == [0.06, 0.03, 0.06]


def test_accuracy_intervals_exclude_flagged_and_guard_small_samples() -> None:
    rows = [
        _row("p1", 1, 512, True),
        _row("p2", 1, 512, False),
        _row("flagged", 1, 512, True, included=False),
    ]
    result = build_accuracy_intervals(rows, min_problems=3)[0]
    assert result["num_evaluated_problems"] == 2
    assert result["accuracy"] == 0.5
    assert result["inference_status"] == "insufficient_sample"


def test_paired_comparison_detects_large_directional_effect() -> None:
    rows = []
    for index in range(10):
        problem = f"p{index}"
        rows.extend(
            [
                _row(problem, 1, 512, False),
                _row(problem, 1, 1024, True),
            ]
        )
    comparison = build_paired_comparisons(rows, min_problems=10)[0]
    assert comparison["comparison_family"] == "depth"
    assert comparison["accuracy_difference_b_minus_a"] == 1.0
    assert comparison["a_only_correct"] == 0
    assert comparison["b_only_correct"] == 10
    assert comparison["statistically_significant_0_05"] is True
    assert comparison["inference_status"] == "significant"
