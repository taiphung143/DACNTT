import json
from pathlib import Path

from analyze_grid import run_analysis
from config import ExperimentConfig
from dataset import GSM8KProblem
from experiment_runner import run_shared_sample_pool
from models.base import GenerationResult, ModelAdapter


class SanityAdapter(ModelAdapter):
    resolved_revision = "sanity-revision"
    device = "cpu"
    dtype_name = "float32"

    def generate(self, prompt: str, max_new_tokens: int, temperature: float, seed: int | None = None) -> GenerationResult:
        assert seed is not None
        answer = "8" if seed % 5 == 0 else "7"
        generated = min(max_new_tokens, 100 + seed % 700)
        finish_reason = "length" if generated == max_new_tokens else "stop"
        return GenerationResult(f"#### {answer}", 20, generated, generated / 10, finish_reason)


def test_simulated_three_problem_pipeline_produces_demo_artifacts(tmp_path: Path) -> None:
    experiment_dir = tmp_path / "sanity"
    experiment_dir.mkdir()
    config = ExperimentConfig(
        num_problems=3,
        model_revision="sanity-revision",
        k_values=(1, 2, 4),
        l_values=(512, 1024, 2048),
        results_dir=tmp_path,
    )
    problems = [
        GSM8KProblem(f"gsm8k-test-{index:05d}", f"Problem {index}: 3+4?", "7", "#### 7", index)
        for index in range(3)
    ]
    stats = run_shared_sample_pool(
        config=config,
        problems=problems,
        adapter=SanityAdapter(),
        experiment_id="sanity",
        raw_samples_path=experiment_dir / "raw_samples.jsonl",
        audit_entries={},
    )
    assert stats["generated"] == 36
    manifest = {
        "experiment_id": "sanity",
        "k_values": [1, 2, 4],
        "L_values": [512, 1024, 2048],
        "config": {"exclude_flagged_dataset_items_from_main_metrics": True},
    }
    (experiment_dir / "experiment_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    run_analysis(experiment_dir)

    required = (
        "config_results.csv",
        "grid_summary.csv",
        "depth_diagnostic.csv",
        "breadth_diagnostic.csv",
        "iso_budget_2048.csv",
        "behavior_classification.csv",
        "oracle_comparison.csv",
        "demo_cases.md",
        "plots/depth_effect.png",
        "plots/breadth_effect.png",
        "plots/accuracy_heatmap.png",
        "plots/generated_tokens_heatmap.png",
        "plots/allocated_vs_realized.png",
        "plots/pareto.png",
        "plots/oracle_pareto.png",
    )
    for relative_path in required:
        path = experiment_dir / relative_path
        assert path.exists() and path.stat().st_size > 0
    assert len((experiment_dir / "raw_samples.jsonl").read_text().splitlines()) == 36
    assert len((experiment_dir / "config_results.csv").read_text().splitlines()) == 28
    assert len((experiment_dir / "grid_summary.csv").read_text().splitlines()) == 10
