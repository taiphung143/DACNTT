"""Verify the round-3 package using only Python's standard library."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def close(actual: float, expected: float, tolerance: float = 1e-9) -> None:
    if abs(actual - expected) > tolerance:
        raise AssertionError(f"{actual} != {expected}")


def verify_manifest(package: Path) -> int:
    manifest_path = package / "MANIFEST_SHA256.csv"
    entries = read_csv(manifest_path)
    expected_paths = {row["path"] for row in entries}
    actual_paths = {
        str(path.relative_to(package)).replace("\\", "/")
        for path in package.rglob("*")
        if path.is_file() and path != manifest_path
    }
    if expected_paths != actual_paths:
        raise AssertionError(
            f"manifest path mismatch: missing={sorted(actual_paths - expected_paths)}, "
            f"stale={sorted(expected_paths - actual_paths)}"
        )
    for row in entries:
        path = package / row["path"]
        if path.stat().st_size != int(row["size_bytes"]):
            raise AssertionError(f"size mismatch: {row['path']}")
        if sha256(path) != row["sha256"]:
            raise AssertionError(f"digest mismatch: {row['path']}")
    return len(entries)


def verify_source_provenance(package: Path) -> int:
    provenance = json.loads((package / "SOURCE_PROVENANCE.json").read_text(encoding="utf-8"))
    hashes: dict[str, str] = provenance["packaged_source_sha256"]
    for relative, expected in hashes.items():
        path = package / "code" / relative
        if sha256(path) != expected:
            raise AssertionError(f"source digest mismatch: {relative}")
    return len(hashes)


def verify_breadth_metrics(package: Path) -> int:
    audit_rows = read_csv(package / "audit_outputs" / "round3_breadth_stopping_rates.csv")
    datasets = {
        "GSM8K": package / "results" / "qwen3_0_6b_gsm8k_test_n100_policy_replay_v3",
        "MATH-500": package / "results" / "qwen3_0_6b_math500_test_n100_baseline_replay_v1",
    }
    verified = 0
    for expected in audit_rows:
        root = datasets[expected["dataset"]]
        length = int(expected["L"])
        adaptive = [
            row
            for row in read_csv(root / "breadth_only_agreement_traces.csv")
            if int(row["decision_selected_L"]) == length
        ]
        fixed = [
            row
            for row in read_csv(root / "fixed_profile_traces.csv")
            if row["policy_id"] == f"fixed_k4_L{length}"
        ]
        if len(adaptive) != 100 or len(fixed) != 100:
            raise AssertionError(f"unexpected trace length: {expected['dataset']} L={length}")
        stop_count = sum(int(row["decision_selected_k"]) == 2 for row in adaptive)
        correct = sum(int(row["outcome_correct"]) for row in adaptive)
        fixed_correct = sum(int(row["outcome_correct"]) for row in fixed)
        adaptive_tokens = sum(float(row["outcome_actual_generated_tokens"]) for row in adaptive) / 100
        fixed_tokens = sum(float(row["outcome_actual_generated_tokens"]) for row in fixed) / 100
        prediction_equal = sum(
            left["outcome_final_answer"] == right["outcome_final_answer"]
            for left, right in zip(
                sorted(adaptive, key=lambda row: row["problem_id"]),
                sorted(fixed, key=lambda row: row["problem_id"]),
            )
        )
        assert stop_count == int(expected["stopped_at_k2_n"])
        assert correct == int(expected["breadth_stop_correct_n"])
        assert fixed_correct == int(expected["fixed_k4_correct_n"])
        assert prediction_equal == int(expected["prediction_equal_n"])
        close(adaptive_tokens, float(expected["breadth_stop_mean_actual_tokens"]), 1e-6)
        close(fixed_tokens, float(expected["fixed_k4_mean_actual_tokens"]), 1e-6)
        close(1 - adaptive_tokens / fixed_tokens, float(expected["mean_actual_token_saving_fraction"]), 1e-12)
        verified += 1
    return verified


def verify_primary_summaries(package: Path) -> int:
    expected = {
        ("gsm", "breadth_only_agreement_L1024_v1"): (76, 1994.52),
        ("gsm", "fixed_k4_L1024"): (76, 2535.17),
        ("gsm", "depth_first_tertile_validity_agreement_v1"): (70, 1449.46),
        ("math", "fixed_k2_L4096"): (66, 5141.50),
        ("math", "depth_first_tertile_validity_agreement_v1"): (36, 5788.81),
        ("math", "breadth_only_agreement_L4096_v1"): (73, 8191.12),
        ("math", "fixed_k4_L4096"): (73, 10233.17),
    }
    roots = {
        "gsm": package / "results" / "qwen3_0_6b_gsm8k_test_n100_policy_replay_v3",
        "math": package / "results" / "qwen3_0_6b_math500_test_n100_baseline_replay_v1",
    }
    summaries = {
        dataset: {row["policy_id"]: row for row in read_csv(root / "policy_summary.csv")}
        for dataset, root in roots.items()
    }
    for (dataset, policy), (correct, tokens) in expected.items():
        row = summaries[dataset][policy]
        assert int(row["correct_count"]) == correct
        close(float(row["avg_actual_generated_tokens"]), tokens, 1e-6)
    return len(expected)


def verify_paired_table(package: Path) -> int:
    path = (
        package
        / "results"
        / "qwen3_0_6b_forceanswer_test_comparison_v1"
        / "paired_decoding_strategy_comparison.csv"
    )
    rows = read_csv(path)
    if len(rows) != 6:
        raise AssertionError("force-answer paired table must contain six comparisons")
    for row in rows:
        assert int(row["both_correct"]) + int(row["both_wrong"]) + int(
            row["standard_only_correct"]
        ) + int(row["force_only_correct"]) == int(row["problems"])
        assert int(row["standard_correct"]) == int(row["both_correct"]) + int(
            row["standard_only_correct"]
        )
        assert int(row["force_correct"]) == int(row["both_correct"]) + int(
            row["force_only_correct"]
        )
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    package = args.package.resolve()
    print(f"manifest_files={verify_manifest(package)}")
    print(f"source_files={verify_source_provenance(package)}")
    print(f"breadth_rows={verify_breadth_metrics(package)}")
    print(f"primary_summaries={verify_primary_summaries(package)}")
    print(f"paired_rows={verify_paired_table(package)}")
    print("release_verification=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
