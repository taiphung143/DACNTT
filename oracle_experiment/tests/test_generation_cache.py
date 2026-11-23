from pathlib import Path

import pytest

from adaptive_compute.config import ExperimentConfig
from adaptive_compute.dataset import GSM8KProblem
from adaptive_compute.experiment_runner import run_shared_sample_pool
from adaptive_compute.generation_cache import (
    CACHE_IDENTITY_FIELDS,
    cacheable_generation_record,
    generation_cache_key,
    load_generation_cache,
)
from adaptive_compute.models.base import GenerationResult, ModelAdapter


class CountingAdapter(ModelAdapter):
    resolved_revision = "revision"
    device = "cpu"
    dtype_name = "float32"

    def __init__(self) -> None:
        self.calls = 0

    def generate(self, prompt: str, max_new_tokens: int, temperature: float, seed: int | None = None) -> GenerationResult:
        self.calls += 1
        return GenerationResult("#### 7", 10, 4, 2.0, "stop")


def _identity() -> dict:
    return {
        "model_revision": "revision",
        "prompt_hash": "prompt",
        "problem_id": "p1",
        "L": 512,
        "repetition_id": 0,
        "sample_id": 0,
        "seed": 42,
        "temperature": 0.7,
        "top_p": 0.95,
        "enable_thinking": True,
        "decoding_strategy": "standard",
        "decoding_strategy_version": "standard_v1",
        "answer_reserve_tokens": 0,
    }


@pytest.mark.parametrize("field", CACHE_IDENTITY_FIELDS)
def test_cache_identity_changes_when_generation_setting_changes(field: str) -> None:
    baseline = _identity()
    changed = dict(baseline)
    value = changed[field]
    if isinstance(value, bool):
        changed[field] = not value
    elif isinstance(value, int):
        changed[field] = value + 1
    elif isinstance(value, float):
        changed[field] = value + 0.01
    else:
        changed[field] = value + "-different"
    assert generation_cache_key(changed) != generation_cache_key(baseline)


def test_legacy_cache_identity_defaults_to_standard_decoding() -> None:
    current = _identity()
    legacy = dict(current)
    legacy.pop("decoding_strategy")
    legacy.pop("decoding_strategy_version")
    legacy.pop("answer_reserve_tokens")

    assert generation_cache_key(legacy) == generation_cache_key(current)


def test_force_answer_cache_version_prevents_stale_suffix_reuse() -> None:
    legacy = _identity()
    legacy["decoding_strategy"] = "force_answer"
    legacy["answer_reserve_tokens"] = 128
    legacy.pop("decoding_strategy_version")
    current = dict(legacy, decoding_strategy_version="force_answer_v2")

    assert generation_cache_key(legacy) != generation_cache_key(current)
    assert cacheable_generation_record(legacy)["decoding_strategy_version"] == (
        "force_answer_v1"
    )


def test_global_cache_reuses_across_experiment_ids(tmp_path: Path) -> None:
    cache_path = tmp_path / "cache.jsonl"
    config = ExperimentConfig(
        num_problems=1,
        model_revision="revision",
        k_values=(1, 2),
        l_values=(8,),
        results_dir=tmp_path,
    )
    problem = GSM8KProblem("p1", "What is 3+4?", "7", "#### 7", 1)
    first_adapter = CountingAdapter()
    first = run_shared_sample_pool(
        config=config,
        problems=[problem],
        adapter=first_adapter,
        experiment_id="first",
        raw_samples_path=tmp_path / "first.jsonl",
        audit_entries={},
        generation_cache_path=cache_path,
    )
    second_adapter = CountingAdapter()
    second = run_shared_sample_pool(
        config=config,
        problems=[problem],
        adapter=second_adapter,
        experiment_id="second",
        raw_samples_path=tmp_path / "second.jsonl",
        audit_entries={},
        generation_cache_path=cache_path,
    )
    assert first == {"generated": 2, "cache_hits": 0, "skipped": 0, "failed": 0}
    assert second == {"generated": 0, "cache_hits": 2, "skipped": 0, "failed": 0}
    assert first_adapter.calls == 2
    assert second_adapter.calls == 0
    assert len(load_generation_cache(cache_path)) == 2
