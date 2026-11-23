from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from adaptive_compute.analysis.decoding_strategy_comparison import compare_dataset_strategies


def _experiment(
    path: Path,
    *,
    strategy: str,
    correct: tuple[bool, bool],
    tokens: float,
    prompt_hash: str = "same-prompt",
    partition: str = "validation",
) -> None:
    path.mkdir()
    problem_ids = ["p0", "p1"]
    manifest = {
        "model": "model",
        "model_revision": "revision",
        "dataset_partition": partition,
        "problem_ids": problem_ids,
        "global_seed": 42,
        "sample_seed_policy": "policy",
        "temperature": 0.7,
        "top_p": 0.95,
        "enable_thinking": True,
        "prompt_hash": prompt_hash,
        "answer_parser_name": "parser-v4",
    }
    if strategy == "force_answer":
        manifest.update(
            {
                "decoding_strategy": "force_answer",
                "decoding_strategy_version": "force_answer_v2",
                "answer_reserve_tokens": 128,
            }
        )
    (path / "experiment_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    config_rows = []
    for problem_id, outcome in zip(problem_ids, correct, strict=True):
        for length in (512, 1024):
            for k in (1, 2, 4):
                config_rows.append(
                    {
                        "problem_id": problem_id,
                        "k": k,
                        "L": length,
                        "repetition_id": 0,
                        "final_correct": outcome,
                        "actual_generated_tokens": tokens * k,
                        "evaluation_included": True,
                    }
                )
    with (path / "config_results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(config_rows[0]))
        writer.writeheader()
        writer.writerows(config_rows)
    with (path / "raw_samples.jsonl").open("w", encoding="utf-8") as handle:
        for problem_id in problem_ids:
            for length in (512, 1024):
                for sample_id in range(4):
                    handle.write(
                        json.dumps(
                            {
                                "problem_id": problem_id,
                                "L": length,
                                "sample_id": sample_id,
                                "repetition_id": 0,
                                "seed": f"{problem_id}-{length}-{sample_id}",
                                "prompt_hash": prompt_hash,
                                "generation_error": None,
                                "parse_error": False,
                                "truncated": False,
                                "forced_transition": strategy == "force_answer",
                            }
                        )
                        + "\n"
                    )


def test_compare_decoding_strategies_is_paired_and_cost_aware(tmp_path: Path) -> None:
    standard = tmp_path / "standard"
    forced = tmp_path / "forced"
    _experiment(standard, strategy="standard", correct=(True, True), tokens=100.0)
    _experiment(forced, strategy="force_answer", correct=(True, False), tokens=75.0)

    rows, source = compare_dataset_strategies(
        dataset="gsm8k",
        standard_dir=standard,
        force_dir=forced,
        lengths=(512, 1024),
    )

    assert len(rows) == 6
    assert rows[0]["standard_correct"] == 2
    assert rows[0]["force_correct"] == 1
    assert rows[0]["accuracy_gap_force_minus_standard"] == -0.5
    assert rows[0]["token_saving_force_vs_standard"] == 0.25
    assert source["partition"] == "validation"


def test_compare_decoding_strategies_rejects_prompt_mismatch(tmp_path: Path) -> None:
    standard = tmp_path / "standard"
    forced = tmp_path / "forced"
    _experiment(standard, strategy="standard", correct=(True, True), tokens=100.0)
    _experiment(
        forced,
        strategy="force_answer",
        correct=(True, False),
        tokens=75.0,
        prompt_hash="different",
    )

    with pytest.raises(ValueError, match="byte-identical prompts"):
        compare_dataset_strategies(
            dataset="gsm8k",
            standard_dir=standard,
            force_dir=forced,
            lengths=(512, 1024),
        )


def test_compare_decoding_strategies_allows_explicit_test_partition(tmp_path: Path) -> None:
    standard = tmp_path / "standard"
    forced = tmp_path / "forced"
    _experiment(
        standard,
        strategy="standard",
        correct=(True, True),
        tokens=100.0,
        partition="test",
    )
    _experiment(
        forced,
        strategy="force_answer",
        correct=(True, False),
        tokens=75.0,
        partition="test",
    )

    rows, source = compare_dataset_strategies(
        dataset="gsm8k",
        standard_dir=standard,
        force_dir=forced,
        lengths=(512,),
        partition="test",
    )

    assert len(rows) == 3
    assert source["partition"] == "test"
