from reprocess_results import reprocess_record


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

