from pathlib import Path

import pytest

from adaptive_compute.config import ExperimentConfig
from adaptive_compute.dataset import GSM8KProblem
from adaptive_compute.experiment_runner import (
    derive_shared_prefix,
    latest_checkpoint_records,
    run_shared_sample_pool,
    stable_sample_seed,
)
from adaptive_compute.models.base import GenerationResult, ModelAdapter


class FakeAdapter(ModelAdapter):
    resolved_revision = "test-revision"
    device = "cpu"
    dtype_name = "float32"

    def __init__(self) -> None:
        self.calls: list[tuple[int, int | None]] = []

    def generate(self, prompt: str, max_new_tokens: int, temperature: float, seed: int | None = None) -> GenerationResult:
        self.calls.append((max_new_tokens, seed))
        return GenerationResult("#### 7", 10, max_new_tokens // 2, 5.0, "stop")


class StopRun(BaseException):
    pass


class InterruptingAdapter(FakeAdapter):
    def generate(self, prompt: str, max_new_tokens: int, temperature: float, seed: int | None = None) -> GenerationResult:
        if len(self.calls) == 2:
            raise StopRun()
        return super().generate(prompt, max_new_tokens, temperature, seed)


class FailingAdapter(FakeAdapter):
    def generate(self, prompt: str, max_new_tokens: int, temperature: float, seed: int | None = None) -> GenerationResult:
        self.calls.append((max_new_tokens, seed))
        raise RuntimeError("synthetic failure")


def _problem() -> GSM8KProblem:
    return GSM8KProblem("gsm8k-test-00001", "What is 3 + 4?", "7", "#### 7", 1)


def _config(tmp_path: Path) -> ExperimentConfig:
    return ExperimentConfig(
        num_problems=1,
        model_revision="test-revision",
        k_values=(1, 2, 4),
        l_values=(8,),
        results_dir=tmp_path,
    )


def test_shared_pool_prefixes_are_nested() -> None:
    pool = [{"sample_id": value} for value in (3, 1, 0, 2)]
    assert [row["sample_id"] for row in derive_shared_prefix(pool, 1)] == [0]
    assert [row["sample_id"] for row in derive_shared_prefix(pool, 2)] == [0, 1]
    assert [row["sample_id"] for row in derive_shared_prefix(pool, 4)] == [0, 1, 2, 3]


def test_sample_seed_is_stable_and_has_no_depth_input() -> None:
    first = stable_sample_seed(42, "p1", 0)
    assert first == stable_sample_seed(42, "p1", 0)
    assert first != stable_sample_seed(42, "p1", 1)
    assert first != stable_sample_seed(43, "p1", 0)


def test_resume_skips_completed_samples(tmp_path: Path) -> None:
    raw_path = tmp_path / "raw.jsonl"
    config = _config(tmp_path)
    first_adapter = FakeAdapter()
    first = run_shared_sample_pool(
        config=config,
        problems=[_problem()],
        adapter=first_adapter,
        experiment_id="test",
        raw_samples_path=raw_path,
        audit_entries={},
    )
    second_adapter = FakeAdapter()
    second = run_shared_sample_pool(
        config=config,
        problems=[_problem()],
        adapter=second_adapter,
        experiment_id="test",
        raw_samples_path=raw_path,
        audit_entries={},
        resume=True,
    )
    assert first == {"generated": 4, "cache_hits": 0, "skipped": 0, "failed": 0}
    assert second == {"generated": 0, "cache_hits": 0, "skipped": 4, "failed": 0}
    assert second_adapter.calls == []
    assert len(latest_checkpoint_records(raw_path)) == 4


def test_partial_run_resumes_only_missing_samples(tmp_path: Path) -> None:
    raw_path = tmp_path / "raw.jsonl"
    config = _config(tmp_path)
    with pytest.raises(StopRun):
        run_shared_sample_pool(
            config=config,
            problems=[_problem()],
            adapter=InterruptingAdapter(),
            experiment_id="test",
            raw_samples_path=raw_path,
            audit_entries={},
        )
    assert len(latest_checkpoint_records(raw_path)) == 2
    resumed_adapter = FakeAdapter()
    stats = run_shared_sample_pool(
        config=config,
        problems=[_problem()],
        adapter=resumed_adapter,
        experiment_id="test",
        raw_samples_path=raw_path,
        audit_entries={},
        resume=True,
    )
    assert stats["generated"] == 2
    assert stats["skipped"] == 2
    assert len(latest_checkpoint_records(raw_path)) == 4


def test_failures_are_checkpointed_and_only_retried_explicitly(tmp_path: Path) -> None:
    raw_path = tmp_path / "raw.jsonl"
    config = _config(tmp_path)
    failed = run_shared_sample_pool(
        config=config,
        problems=[_problem()],
        adapter=FailingAdapter(),
        experiment_id="test",
        raw_samples_path=raw_path,
        audit_entries={},
    )
    assert failed == {"generated": 4, "cache_hits": 0, "skipped": 0, "failed": 4}
    assert all(
        row["failure_type"] == "generation_error"
        for row in latest_checkpoint_records(raw_path).values()
    )

    skipped = run_shared_sample_pool(
        config=config,
        problems=[_problem()],
        adapter=FakeAdapter(),
        experiment_id="test",
        raw_samples_path=raw_path,
        audit_entries={},
        resume=True,
    )
    assert skipped["skipped"] == 4
    retried = run_shared_sample_pool(
        config=config,
        problems=[_problem()],
        adapter=FakeAdapter(),
        experiment_id="test",
        raw_samples_path=raw_path,
        audit_entries={},
        resume=True,
        retry_errors=True,
    )
    assert retried["generated"] == 4
    assert all(
        row["failure_type"] == "correct"
        for row in latest_checkpoint_records(raw_path).values()
    )
