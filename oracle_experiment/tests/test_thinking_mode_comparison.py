from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from adaptive_compute.analysis.thinking_mode_comparison import compare_dataset_modes


def _experiment(path: Path, *, thinking: bool, correct: tuple[bool, bool], tokens: float) -> None:
    path.mkdir()
    problem_ids = ["p0", "p1"]
    manifest = {
        "model": "model",
        "model_revision": "revision",
        "dataset_partition": "validation",
        "problem_ids": problem_ids,
        "enable_thinking": thinking,
        "prompt_hash": "same-prompt",
        "answer_parser_name": "parser",
    }
    (path / "experiment_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    config_rows = []
    for problem_id, outcome in zip(problem_ids, correct, strict=True):
        for k in (1, 2, 4):
            config_rows.append(
                {
                    "problem_id": problem_id,
                    "k": k,
                    "L": 2048,
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
            for sample_id in range(4):
                handle.write(
                    json.dumps(
                        {
                            "problem_id": problem_id,
                            "L": 2048,
                            "sample_id": sample_id,
                            "repetition_id": 0,
                            "generation_error": None,
                            "parse_error": False,
                            "truncated": False,
                        }
                    )
                    + "\n"
                )


def test_compare_dataset_modes_is_paired_and_cost_aware(tmp_path: Path) -> None:
    thinking = tmp_path / "thinking"
    nonthinking = tmp_path / "nonthinking"
    _experiment(thinking, thinking=True, correct=(True, True), tokens=100.0)
    _experiment(nonthinking, thinking=False, correct=(True, False), tokens=50.0)

    rows, source = compare_dataset_modes(
        dataset="gsm8k",
        thinking_dir=thinking,
        nonthinking_dir=nonthinking,
        length=2048,
    )

    assert len(rows) == 3
    assert rows[0]["thinking_correct"] == 2
    assert rows[0]["nonthinking_correct"] == 1
    assert rows[0]["accuracy_gap_nonthinking_minus_thinking"] == -0.5
    assert rows[0]["token_saving_nonthinking_vs_thinking"] == 0.5
    assert source["partition"] == "validation"


def test_compare_dataset_modes_rejects_prompt_mismatch(tmp_path: Path) -> None:
    thinking = tmp_path / "thinking"
    nonthinking = tmp_path / "nonthinking"
    _experiment(thinking, thinking=True, correct=(True, True), tokens=100.0)
    _experiment(nonthinking, thinking=False, correct=(True, False), tokens=50.0)
    manifest_path = nonthinking / "experiment_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["prompt_hash"] = "different"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="byte-identical prompts"):
        compare_dataset_modes(
            dataset="gsm8k",
            thinking_dir=thinking,
            nonthinking_dir=nonthinking,
            length=2048,
        )
