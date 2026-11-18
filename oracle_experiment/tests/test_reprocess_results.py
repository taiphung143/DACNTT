import hashlib
import json
from pathlib import Path

from adaptive_compute.answer_parser import (
    GSM8K_ANSWER_PARSER_V2_NAME,
    MATH500_ANSWER_PARSER_NAME,
)
from adaptive_compute.cli.reprocess_results import (
    reprocess_experiment,
    reprocess_record,
)


def test_reprocessing_corrects_old_false_last_number_parse() -> None:
    old = {
        "problem_id": "p1",
        "L": 512,
        "raw_response": "<think>We compute 430 + 750 + 700 + 300.",
        "parsed_answer": "300",
        "ground_truth": "2280",
        "generated_tokens": 512,
        "finish_reason": "length",
    }

    updated = reprocess_record(old, questions={"p1": "How much in total?"})

    assert updated["question"] == "How much in total?"
    assert updated["parsed_answer"] is None
    assert updated["truncated"] is True
    assert updated["failure_type"] == "truncated_before_answer"
    assert updated["token_budget_utilization"] == 1.0
    assert updated["dataset_quality_flag"] is None


def test_reprocessing_upgrades_math_ground_truth_and_parser_version() -> None:
    old = {
        "problem_id": "math500-test-137",
        "L": 4096,
        "raw_response": r"\boxed{204}",
        "ground_truth": "2045",
        "ground_truth_raw": r"204_5",
        "generated_tokens": 100,
        "finish_reason": "stop",
        "answer_parser_name": "math500_exact_v1",
    }

    updated = reprocess_record(
        old, answer_parser_name=MATH500_ANSWER_PARSER_NAME
    )

    assert updated["answer_parser_name"] == "math500_exact_v2"
    assert updated["ground_truth"] == "204"
    assert updated["parsed_answer"] == "204"
    assert updated["correct"] is True


def test_reprocess_experiment_preserves_prompt_and_records_provenance(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target_parser_v2"
    source.mkdir()
    raw_path = source / "raw_samples.jsonl"
    raw_path.write_text(
        json.dumps(
            {
                "experiment_id": "source",
                "problem_id": "p1",
                "L": 512,
                "sample_id": 0,
                "repetition_id": 0,
                "raw_response": "<think>done</think>\n#### <numeric answer> 42",
                "ground_truth": "42",
                "generated_tokens": 20,
                "finish_reason": "stop",
                "answer_parser_name": "gsm8k_numeric_v1",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (source / "experiment_manifest.json").write_text(
        json.dumps(
            {
                "experiment_id": "source",
                "prompt_template_name": "gsm8k_cot_v1",
                "answer_parser_name": "gsm8k_numeric_v1",
                "config": {
                    "prompt_template_name": "gsm8k_cot_v1",
                    "answer_parser_name": "gsm8k_numeric_v1",
                },
            }
        ),
        encoding="utf-8",
    )

    count = reprocess_experiment(
        source_dir=source,
        output_dir=target,
        answer_parser_name=GSM8K_ANSWER_PARSER_V2_NAME,
        audit_entries={},
    )

    assert count == 1
    manifest = json.loads((target / "experiment_manifest.json").read_text())
    record = json.loads((target / "raw_samples.jsonl").read_text())
    assert manifest["prompt_template_name"] == "gsm8k_cot_v1"
    assert manifest["answer_parser_name"] == GSM8K_ANSWER_PARSER_V2_NAME
    assert manifest["derived_from"]["experiment_id"] == "source"
    assert manifest["derived_from"]["raw_samples_sha256"] == hashlib.sha256(
        raw_path.read_bytes()
    ).hexdigest()
    assert record["source_experiment_id"] == "source"
    assert record["experiment_id"] == target.name
    assert record["parsed_answer"] == "42"
