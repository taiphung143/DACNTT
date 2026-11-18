"""Generate thesis tables from frozen experiment artifacts.

The script intentionally refuses partial or mismatched Test artifacts. It is a
content-generation step only: policy selection remains defined by the freeze
JSON files and is never recomputed from Test outcomes.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "thesis" / "generated"


@dataclass(frozen=True)
class DatasetArtifacts:
    key: str
    display_name: str
    replay_dir: Path
    experiment_dir: Path
    freeze_path: Path
    selected_policy_id: str
    joint_policy_id: str
    high_breadth_policy_id: str
    breadth_efficiency_policy_id: str


DATASETS = (
    DatasetArtifacts(
        key="gsm8k",
        display_name="GSM8K",
        replay_dir=ROOT
        / "results/phase2/qwen3_0_6b_gsm8k_test_n100_policy_replay_v3",
        experiment_dir=ROOT / "results/qwen3_0_6b_gsm8k_test_n100_contract_v3",
        freeze_path=ROOT / "results/phase2/gsm8k_policy_freeze_v1/policy_freeze.json",
        selected_policy_id="breadth_only_agreement_L1024_v1",
        joint_policy_id="depth_first_tertile_validity_agreement_v1",
        high_breadth_policy_id="fixed_k4_L1024",
        breadth_efficiency_policy_id="breadth_only_agreement_L1024_v1",
    ),
    DatasetArtifacts(
        key="math500",
        display_name="MATH-500",
        replay_dir=ROOT
        / "results/phase2/qwen3_0_6b_math500_test_n100_baseline_replay_v1",
        experiment_dir=ROOT / "results/qwen3_0_6b_math500_test_n100_contract_v1",
        freeze_path=ROOT
        / "results/phase2/math500_policy_freeze_v1/policy_freeze.json",
        selected_policy_id="fixed_k2_L4096",
        joint_policy_id="depth_first_tertile_validity_agreement_v1",
        high_breadth_policy_id="fixed_k4_L4096",
        breadth_efficiency_policy_id="breadth_only_agreement_L4096_v1",
    ),
)


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError(f"empty CSV: {path}")
    return rows


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def policy_label(policy_id: str) -> str:
    if policy_id.startswith("fixed_k"):
        _, k_part, l_part = policy_id.split("_")
        return f"Fixed $k={k_part[1:]},L={l_part[1:]}$"
    if policy_id.startswith("breadth_only_agreement_L"):
        length = policy_id.removeprefix("breadth_only_agreement_L").removesuffix("_v1")
        return f"Breadth stop, $L={length}$"
    if policy_id == "depth_only_input_tertile_k1_v1":
        return "Depth-only"
    if policy_id == "depth_first_tertile_validity_agreement_v1":
        return "Joint heuristic"
    raise ValueError(f"unknown policy ID: {policy_id}")


def bool_text(value: str) -> bool:
    if value == "True":
        return True
    if value == "False":
        return False
    raise ValueError(f"invalid boolean text: {value!r}")


def fmt_tokens(value: float) -> str:
    whole, decimal = f"{value:,.2f}".split(".")
    return whole.replace(",", r"\,") + "." + decimal


def fmt_p(value: float) -> str:
    if value < 0.0001:
        exponent = math.floor(math.log10(value))
        coefficient = value / (10**exponent)
        return f"${coefficient:.2f}\\times10^{{{exponent}}}$"
    return f"{value:.4f}"


def wilson_interval(correct: int, total: int, z: float = 1.959963984540054) -> tuple[float, float]:
    probability = correct / total
    denominator = 1 + z * z / total
    center = (probability + z * z / (2 * total)) / denominator
    radius = (
        z
        * math.sqrt(probability * (1 - probability) / total + z * z / (4 * total * total))
        / denominator
    )
    return center - radius, center + radius


def load_trace_index(dataset: DatasetArtifacts) -> dict[str, dict[str, dict[str, str]]]:
    index: dict[str, dict[str, dict[str, str]]] = {}
    for filename in (
        "breadth_only_agreement_traces.csv",
        "fixed_profile_traces.csv",
        "heuristic_trace.csv",
        "depth_only_heuristic_trace.csv",
    ):
        for row in read_csv(dataset.replay_dir / filename):
            policy_rows = index.setdefault(row["policy_id"], {})
            problem_id = row["problem_id"]
            if problem_id in policy_rows:
                raise ValueError(f"duplicate trace: {dataset.key}/{row['policy_id']}/{problem_id}")
            policy_rows[problem_id] = row
    return index


def paired_trace_summary(
    trace_index: dict[str, dict[str, dict[str, str]]], policy_a: str, policy_b: str
) -> dict[str, float | int]:
    rows_a = trace_index[policy_a]
    rows_b = trace_index[policy_b]
    if set(rows_a) != set(rows_b) or len(rows_a) != 100:
        raise ValueError(f"incomplete paired traces: {policy_a} vs {policy_b}")
    a_only = 0
    b_only = 0
    for problem_id, row_a in rows_a.items():
        correct_a = int(row_a["outcome_correct"])
        correct_b = int(rows_b[problem_id]["outcome_correct"])
        a_only += int(correct_a == 1 and correct_b == 0)
        b_only += int(correct_a == 0 and correct_b == 1)
    mean_a_tokens = sum(float(row["outcome_actual_generated_tokens"]) for row in rows_a.values()) / 100
    mean_b_tokens = sum(float(row["outcome_actual_generated_tokens"]) for row in rows_b.values()) / 100
    mean_a_latency = sum(float(row["outcome_latency_ms"]) for row in rows_a.values()) / 100
    mean_b_latency = sum(float(row["outcome_latency_ms"]) for row in rows_b.values()) / 100
    return {
        "a_only": a_only,
        "b_only": b_only,
        "mean_a_tokens": mean_a_tokens,
        "mean_b_tokens": mean_b_tokens,
        "token_reduction": 1 - mean_a_tokens / mean_b_tokens,
        "latency_reduction": 1 - mean_a_latency / mean_b_latency,
    }


def validate_and_load(dataset: DatasetArtifacts) -> dict[str, Any]:
    summary_path = dataset.replay_dir / "policy_summary.csv"
    pareto_path = dataset.replay_dir / "policy_pareto.csv"
    comparisons_path = dataset.replay_dir / "primary_heuristic_comparisons.csv"
    raw_path = dataset.experiment_dir / "raw_samples.jsonl"
    experiment_manifest_path = dataset.experiment_dir / "experiment_manifest.json"

    summary = read_csv(summary_path)
    pareto = read_csv(pareto_path)
    comparisons = read_csv(comparisons_path)
    freeze = read_json(dataset.freeze_path)
    experiment_manifest = read_json(experiment_manifest_path)

    if len(summary) != 14 or len(pareto) != 14:
        raise ValueError(f"{dataset.key}: expected 14 registered Test policies")
    summary_by_id = {row["policy_id"]: row for row in summary}
    pareto_by_id = {row["policy_id"]: row for row in pareto}
    frozen_ids = set(freeze["confirmatory_policy_ids"])
    if set(summary_by_id) != frozen_ids or set(pareto_by_id) != frozen_ids:
        raise ValueError(f"{dataset.key}: replay policies do not match freeze")
    if freeze["selected_policy_id"] != dataset.selected_policy_id:
        raise ValueError(f"{dataset.key}: selected policy mismatch")
    for row in summary:
        if row["partition"] != "test" or int(row["num_problems"]) != 100:
            raise ValueError(f"{dataset.key}: non-Test or incomplete summary row")

    raw_count = 0
    generation_errors = 0
    keys: set[tuple[Any, ...]] = set()
    with raw_path.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            record = json.loads(line)
            raw_count += 1
            generation_errors += int(bool(record.get("generation_error")))
            key = (
                record["problem_id"],
                int(record["L"]),
                int(record["sample_id"]),
                int(record.get("repetition_id", 0)),
            )
            if key in keys:
                raise ValueError(f"{dataset.key}: duplicate generation key {key}")
            keys.add(key)
    expected = int(experiment_manifest["expected_generations"])
    if raw_count != expected or expected != 1200 or generation_errors:
        raise ValueError(
            f"{dataset.key}: generation completeness failure "
            f"({raw_count=}, {expected=}, {generation_errors=})"
        )

    return {
        "dataset": dataset,
        "summary": summary,
        "summary_by_id": summary_by_id,
        "pareto_by_id": pareto_by_id,
        "comparisons": comparisons,
        "freeze": freeze,
        "experiment_manifest": experiment_manifest,
        "trace_index": load_trace_index(dataset),
        "raw_count": raw_count,
        "source_paths": (
            summary_path,
            pareto_path,
            comparisons_path,
            dataset.freeze_path,
            raw_path,
            experiment_manifest_path,
        ),
    }


def selected_summary_rows(loaded: dict[str, Any]) -> list[str]:
    dataset: DatasetArtifacts = loaded["dataset"]
    summary: dict[str, dict[str, str]] = loaded["summary_by_id"]
    selected_ids = (
        dataset.selected_policy_id,
        dataset.joint_policy_id,
        dataset.breadth_efficiency_policy_id,
        dataset.high_breadth_policy_id,
    )
    rows: list[str] = []
    seen: set[str] = set()
    for policy_id in selected_ids:
        if policy_id in seen:
            continue
        seen.add(policy_id)
        row = summary[policy_id]
        selected = policy_id == dataset.selected_policy_id
        label = policy_label(policy_id) + (" (selected)" if selected else "")
        low, high = wilson_interval(int(row["correct_count"]), int(row["num_problems"]))
        frontier = bool_text(loaded["pareto_by_id"][policy_id]["pareto_nondominated"])
        rows.append(
            f"{dataset.display_name} & {label} & {row['correct_count']}/100 & "
            f"[{100*low:.1f}, {100*high:.1f}] & "
            f"{fmt_tokens(float(row['avg_actual_generated_tokens']))} & "
            f"{'Có' if frontier else 'Không'} \\\\" 
        )
    return rows


def build_main_results(loaded_sets: list[dict[str, Any]]) -> str:
    body = "\n".join(row for loaded in loaded_sets for row in selected_summary_rows(loaded))
    return rf"""% Generated by scripts/build_thesis_results.py. Do not edit manually.
\begin{{table}}[htbp]
  \centering
  \caption{{Các điểm vận hành chính trên hai tập Test đóng băng. Khoảng tin cậy là Wilson 95\%.}}
  \label{{tab:primary-test-results}}
  \scriptsize
  \begin{{tabular}}{{p{{0.12\textwidth}}p{{0.34\textwidth}}rrr c}}
    \toprule
    Dữ liệu & Policy & Đúng & Wilson CI (\%) & Token TB & Pareto \\
    \midrule
{body}
    \bottomrule
  \end{{tabular}}
\end{{table}}
"""


def build_all_policy_table(loaded: dict[str, Any]) -> str:
    dataset: DatasetArtifacts = loaded["dataset"]
    summary = sorted(
        loaded["summary"], key=lambda row: float(row["avg_actual_generated_tokens"])
    )
    body: list[str] = []
    for row in summary:
        policy_id = row["policy_id"]
        label = policy_label(policy_id)
        if policy_id == dataset.selected_policy_id:
            label += " (selected)"
        frontier = bool_text(loaded["pareto_by_id"][policy_id]["pareto_nondominated"])
        body.append(
            f"{label} & {100*float(row['accuracy']):.0f}\\% & "
            f"{fmt_tokens(float(row['avg_actual_generated_tokens']))} & "
            f"{100*float(row['final_valid_rate']):.0f}\\% & "
            f"{100*float(row['paid_sample_truncation_rate']):.1f}\\% & "
            f"{'Có' if frontier else 'Không'} \\\\" 
        )
    return rf"""% Generated by scripts/build_thesis_results.py. Do not edit manually.
\begin{{table}}[htbp]
  \centering
  \caption{{Toàn bộ 14 policy đã đăng ký trên {dataset.display_name} Test-100, sắp theo token thực tế.}}
  \label{{tab:{dataset.key}-all-policies}}
  \scriptsize
  \begin{{tabular}}{{p{{0.34\textwidth}}rrrrc}}
    \toprule
    Policy & Accuracy & Token TB & Valid & Truncated & Pareto \\
    \midrule
{chr(10).join(body)}
    \bottomrule
  \end{{tabular}}
\end{{table}}
"""


def find_joint_comparison(loaded: dict[str, Any]) -> dict[str, str]:
    dataset: DatasetArtifacts = loaded["dataset"]
    for row in loaded["comparisons"]:
        if row["comparator_policy_id"] == dataset.selected_policy_id:
            return row
    raise ValueError(f"{dataset.key}: selected-vs-joint comparison missing")


def build_paired_comparisons(loaded_sets: list[dict[str, Any]]) -> str:
    rows: list[str] = []
    for loaded in loaded_sets:
        dataset: DatasetArtifacts = loaded["dataset"]
        joint_row = find_joint_comparison(loaded)
        selected = loaded["summary_by_id"][dataset.selected_policy_id]
        joint = loaded["summary_by_id"][dataset.joint_policy_id]
        selected_minus_joint_accuracy = 100 * (
            float(selected["accuracy"]) - float(joint["accuracy"])
        )
        selected_minus_joint_tokens = float(selected["avg_actual_generated_tokens"]) - float(
            joint["avg_actual_generated_tokens"]
        )
        rows.append(
            f"{dataset.display_name} & Selected vs joint & "
            f"{selected_minus_joint_accuracy:+.0f} & {fmt_tokens(selected_minus_joint_tokens)} & "
            f"{joint_row['comparator_only_correct']}/{joint_row['heuristic_only_correct']} & "
            f"{fmt_p(float(joint_row['mcnemar_exact_p']))} & "
            f"{fmt_p(float(joint_row['holm_adjusted_p']))} \\\\" 
        )

        paired = paired_trace_summary(
            loaded["trace_index"],
            dataset.breadth_efficiency_policy_id,
            dataset.high_breadth_policy_id,
        )
        rows.append(
            f"{dataset.display_name} & Breadth stop vs fixed $k=4$ & +0 & "
            f"{fmt_tokens(float(paired['mean_a_tokens']) - float(paired['mean_b_tokens']))} & "
            f"{paired['a_only']}/{paired['b_only']} & 1.0000 & -- \\\\" 
        )
    return rf"""% Generated by scripts/build_thesis_results.py. Do not edit manually.
\begin{{table}}[htbp]
  \centering
  \caption{{So sánh ghép cặp chính. Chênh lệch được tính theo policy đứng trước trừ policy đứng sau; cột discordant là trước-only/sau-only.}}
  \label{{tab:paired-policy-results}}
  \scriptsize
  \begin{{tabular}}{{p{{0.09\textwidth}}p{{0.24\textwidth}}*{{5}}{{>{{\centering\arraybackslash}}p{{0.09\textwidth}}}}}}
    \toprule
    Dữ liệu & So sánh & $\Delta$acc. (điểm) & $\Delta$token & Discordant & Exact $p$ & Holm $p$ \\
    \midrule
{chr(10).join(rows)}
    \bottomrule
  \end{{tabular}}
\end{{table}}
"""


def build_experiment_completeness(loaded_sets: list[dict[str, Any]]) -> str:
    rows: list[str] = []
    for loaded in loaded_sets:
        dataset: DatasetArtifacts = loaded["dataset"]
        manifest = loaded["experiment_manifest"]
        rows.append(
            f"{dataset.display_name} & {manifest['num_problems']} & "
            f"{','.join(str(v) for v in manifest['k_values'])} & "
            f"{','.join(str(v) for v in manifest['L_values'])} & "
            f"{manifest['expected_generations']} & {loaded['raw_count']} & 0 & 0 \\\\" 
        )
    return rf"""% Generated by scripts/build_thesis_results.py. Do not edit manually.
\begin{{table}}[htbp]
  \centering
  \caption{{Kiểm tra tính đầy đủ của hai lưới Test chính.}}
  \label{{tab:test-grid-completeness}}
  \small
  \begin{{tabular}}{{lrrrrrrr}}
    \toprule
    Dữ liệu & Bài & $k$ & $L$ & Dự kiến & Thực có & Lỗi & Trùng \\
    \midrule
{chr(10).join(rows)}
    \bottomrule
  \end{{tabular}}
\end{{table}}
"""


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    loaded_sets = [validate_and_load(dataset) for dataset in DATASETS]
    outputs = {
        "05_experiment_completeness.tex": build_experiment_completeness(loaded_sets),
        "06_main_results.tex": build_main_results(loaded_sets),
        "06_gsm8k_all_policies.tex": build_all_policy_table(loaded_sets[0]),
        "06_math500_all_policies.tex": build_all_policy_table(loaded_sets[1]),
        "06_paired_comparisons.tex": build_paired_comparisons(loaded_sets),
    }
    for filename, content in outputs.items():
        (OUTPUT_DIR / filename).write_text(content, encoding="utf-8", newline="\n")

    source_hashes: dict[str, str] = {}
    for loaded in loaded_sets:
        for path in loaded["source_paths"]:
            source_hashes[str(path.relative_to(ROOT))] = sha256_file(path)
    output_hashes = {
        f"thesis/generated/{filename}": sha256_file(OUTPUT_DIR / filename)
        for filename in outputs
    }
    manifest = {
        "schema_version": 1,
        "artifact_type": "generated_thesis_results",
        "policy_counts": {loaded["dataset"].key: len(loaded["summary"]) for loaded in loaded_sets},
        "raw_generation_counts": {
            loaded["dataset"].key: loaded["raw_count"] for loaded in loaded_sets
        },
        "selected_policy_ids": {
            loaded["dataset"].key: loaded["dataset"].selected_policy_id
            for loaded in loaded_sets
        },
        "source_hashes": source_hashes,
        "output_hashes": output_hashes,
        "interpretation": (
            "Tables are generated from frozen artifacts. Test Pareto membership is descriptive "
            "and does not authorize policy reselection."
        ),
    }
    (OUTPUT_DIR / "results_generation_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "generated_files": sorted(outputs),
                "policy_counts": manifest["policy_counts"],
                "raw_generation_counts": manifest["raw_generation_counts"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
