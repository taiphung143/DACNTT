import json
from pathlib import Path
from typing import Any

import pytest

from adaptive_compute.answer_parser import (
    MATH500_ANSWER_PARSER_NAME,
    normalize_math_answer,
    parse_math500_ground_truth,
    parse_math500_response_answers,
)
from adaptive_compute.config import ExperimentConfig
from adaptive_compute.evaluate import answers_equal, evaluate_response
from adaptive_compute.experiment_runner import run_shared_sample_pool
from adaptive_compute.math500 import (
    MATH500_HF_DATASET_ID,
    Math500Problem,
    load_math500_subset,
    select_stratified_math500_indices,
)
from adaptive_compute.models.base import GenerationResult, ModelAdapter
from adaptive_compute.prompts import MATH500_PROMPT_TEMPLATE_NAME


def _records() -> list[dict[str, Any]]:
    subjects = ("Algebra", "Geometry", "Number Theory")
    return [
        {
            "problem": f"Problem {index}",
            "solution": rf"Work. \boxed{{{index + 1}}}",
            "answer": str(index + 1),
            "subject": subjects[index % len(subjects)],
            "level": index % 5 + 1,
            "unique_id": f"test/{subjects[index % len(subjects)].lower()}/{index}.json",
        }
        for index in range(15)
    ]


def _loader_factory(records: list[dict[str, Any]]):
    def load_dataset(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        assert args == (MATH500_HF_DATASET_ID,)
        assert kwargs["split"] == "test"
        assert kwargs["revision"] == "test-revision"
        return records

    return load_dataset


def test_stratified_selection_is_deterministic_and_unique() -> None:
    records = _records()
    first = select_stratified_math500_indices(records, num_problems=10, seed=42)
    second = select_stratified_math500_indices(records, num_problems=10, seed=42)

    assert first == second
    assert len(first) == len(set(first)) == 10
    assert len({records[index]["subject"] for index in first}) == 3
    assert len({records[index]["level"] for index in first}) == 5


def test_math500_loader_creates_and_reuses_frozen_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "math500.json"
    loader = _loader_factory(_records())
    first = load_math500_subset(
        num_problems=10,
        seed=42,
        revision="test-revision",
        manifest_path=manifest,
        dataset_loader=loader,
    )
    second = load_math500_subset(
        num_problems=10,
        seed=42,
        revision="test-revision",
        manifest_path=manifest,
        dataset_loader=loader,
    )

    assert first == second
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["status"] == "frozen"
    assert payload["selection_policy"] == "subject-level-round-robin-v1"
    assert sum(payload["subject_counts"].values()) == 10
    assert all("answer_sha256" in row for row in payload["problems"])


def test_math500_manifest_detects_changed_record(tmp_path: Path) -> None:
    records = _records()
    manifest = tmp_path / "math500.json"
    loader = _loader_factory(records)
    selected = load_math500_subset(
        num_problems=5,
        seed=42,
        revision="test-revision",
        manifest_path=manifest,
        dataset_loader=loader,
    )
    records[selected[0].source_index]["answer"] = "changed"

    with pytest.raises(ValueError, match="record changed"):
        load_math500_subset(
            num_problems=5,
            seed=42,
            revision="test-revision",
            manifest_path=manifest,
            dataset_loader=loader,
        )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (r"\frac{14}{3}", "14/3"),
        (r"\frac14", "1/4"),
        (r"\frac1{16}", "1/16"),
        ("14/3", "14/3"),
        (r"90^\circ", "90"),
        (r"204_5", "204"),
        (r"204_{5}", "204"),
        ("3, 5, 7", "3,5,7"),
        ("3,5,7", "3,5,7"),
        ("1,234", "1234"),
        (r"\text{Evelyn}", "evelyn"),
        (r"\left( 3, \frac{\pi}{2} \right)", r"(3,\frac{\pi}{2})"),
    ],
)
def test_math_answer_normalization(raw: str, expected: str) -> None:
    assert normalize_math_answer(raw) == expected


def test_nested_boxed_answer_is_extracted_from_final_response() -> None:
    parsed = parse_math500_response_answers(
        r"<think>work \boxed{1}</think>Therefore \boxed{\frac{14}{3}}"
    )

    assert parsed.reasoning_answer == "1"
    assert parsed.final_response_answer == "14/3"
    assert parsed.reasoning_final_disagreement is True


def test_math_parser_requires_box_or_hash_marker() -> None:
    assert parse_math500_response_answers("The answer is 42.").final_response_answer is None


def test_math_ground_truth_and_evaluation_use_dataset_specific_parser() -> None:
    truth = parse_math500_ground_truth(r"\frac{14}{3}")
    assert answers_equal(
        "14/3", truth, answer_parser_name=MATH500_ANSWER_PARSER_NAME
    )
    result = evaluate_response(
        r"\boxed{14/3}",
        truth,
        answer_parser_name=MATH500_ANSWER_PARSER_NAME,
    )
    assert result.correct is True
    assert result.parsed_answer == "14/3"


def test_math_base_annotation_matches_digits_in_requested_base() -> None:
    truth = parse_math500_ground_truth(r"204_5")
    result = evaluate_response(
        r"\boxed{204}",
        truth,
        answer_parser_name=MATH500_ANSWER_PARSER_NAME,
    )

    assert truth == "204"
    assert result.correct is True


def test_math_numeric_list_is_not_collapsed_into_one_integer() -> None:
    truth = parse_math500_ground_truth("3, 5, 7")
    result = evaluate_response(
        r"\boxed{3,5,7}",
        truth,
        answer_parser_name=MATH500_ANSWER_PARSER_NAME,
    )

    assert truth == "3,5,7"
    assert result.correct is True


class _Math500Adapter(ModelAdapter):
    resolved_revision = "test-model-revision"
    device = "cpu"
    dtype_name = "float32"

    def generate(
        self,
        prompt: str,
        max_new_tokens: int,
        temperature: float,
        seed: int | None = None,
    ) -> GenerationResult:
        assert r"\boxed{<final answer>}" in prompt
        return GenerationResult(r"\boxed{\frac{14}{3}}", 20, 8, 1.0, "stop")


def test_math500_problem_runs_through_shared_experiment_pipeline(tmp_path: Path) -> None:
    config = ExperimentConfig(
        dataset_name="math500",
        dataset_id=MATH500_HF_DATASET_ID,
        dataset_revision="test-dataset-revision",
        num_problems=1,
        model_revision="test-model-revision",
        k_values=(1,),
        l_values=(32,),
        prompt_template_name=MATH500_PROMPT_TEMPLATE_NAME,
        answer_parser_name=MATH500_ANSWER_PARSER_NAME,
        results_dir=tmp_path,
    )
    problem = Math500Problem(
        problem_id="math500-test-002",
        question="Evaluate a rational expression.",
        ground_truth="14/3",
        ground_truth_raw=r"\frac{14}{3}",
        source_index=2,
        subject="Algebra",
        level=3,
        unique_id="test/algebra/2584.json",
    )
    output = tmp_path / "raw_samples.jsonl"

    stats = run_shared_sample_pool(
        config=config,
        problems=[problem],
        adapter=_Math500Adapter(),
        experiment_id="math500-sanity",
        raw_samples_path=output,
        audit_entries={},
    )
    row = json.loads(output.read_text(encoding="utf-8"))

    assert stats["generated"] == 1
    assert row["correct"] is True
    assert row["answer_parser_name"] == MATH500_ANSWER_PARSER_NAME
    assert row["dataset_subject"] == "Algebra"
