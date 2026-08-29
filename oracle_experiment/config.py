"""Typed configuration for the Oracle Grid Experiment.

Only ``k`` and ``L`` vary within one experiment. All other settings belong to
one immutable configuration snapshot persisted beside the results.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


NUM_PROBLEMS = 30
K_VALUES = (1, 2, 4)
L_VALUES = (512, 1024, 2048)
GLOBAL_SEED = 42
NUM_REPETITIONS = 1
TEMPERATURE = 0.7
TOP_P = 0.95
MODEL_ID = "Qwen/Qwen3-1.7B"
MODEL_REVISION = "70d244cc86ccca08cf5af4e1e306ecf908b1ad5e"
MANUAL_AUDIT_PATH = Path("data/manual_audit.json")
EXCLUDE_FLAGGED_DATASET_ITEMS_FROM_MAIN_METRICS = True


@dataclass(frozen=True, order=True)
class GridConfiguration:
    """One fixed breadth/depth profile."""

    k: int
    max_new_tokens: int

    def __post_init__(self) -> None:
        if self.k <= 0:
            raise ValueError("k must be positive")
        if self.max_new_tokens <= 0:
            raise ValueError("max_new_tokens (L) must be positive")

    @property
    def allocated_token_budget(self) -> int:
        return self.k * self.max_new_tokens


@dataclass(frozen=True)
class ExperimentConfig:
    """Immutable settings for one reproducible experiment run."""

    dataset_name: str = "gsm8k"
    dataset_id: str = "openai/gsm8k"
    dataset_config: str = "main"
    dataset_split: str = "test"
    num_problems: int = NUM_PROBLEMS

    model_id: str = MODEL_ID
    model_revision: str = MODEL_REVISION
    model_backend: str = "transformers"
    model_dtype: str = "bfloat16"
    use_chat_template: bool = True
    enable_thinking: bool = True
    manual_audit_path: Path = field(default_factory=lambda: MANUAL_AUDIT_PATH)
    exclude_flagged_dataset_items_from_main_metrics: bool = (
        EXCLUDE_FLAGGED_DATASET_ITEMS_FROM_MAIN_METRICS
    )

    k_values: tuple[int, ...] = K_VALUES
    l_values: tuple[int, ...] = L_VALUES
    temperature: float = TEMPERATURE
    top_p: float = TOP_P

    global_seed: int = GLOBAL_SEED
    num_repetitions: int = NUM_REPETITIONS

    prompt_template_name: str = "gsm8k_cot_v1"
    answer_parser_name: str = "gsm8k_numeric_v1"
    aggregation_method: str = "majority_vote"
    tie_breaking_rule: str = "lowest_sample_index"

    request_timeout_seconds: float = 300.0
    results_dir: Path = field(default_factory=lambda: Path("results"))

    def __post_init__(self) -> None:
        if self.num_problems <= 0:
            raise ValueError("num_problems must be positive")
        if not self.k_values or any(value <= 0 for value in self.k_values):
            raise ValueError("k_values must contain only positive integers")
        if not self.l_values or any(value <= 0 for value in self.l_values):
            raise ValueError("l_values must contain only positive integers")
        if len(set(self.k_values)) != len(self.k_values):
            raise ValueError("k_values must not contain duplicates")
        if len(set(self.l_values)) != len(self.l_values):
            raise ValueError("l_values must not contain duplicates")
        if self.num_repetitions <= 0:
            raise ValueError("num_repetitions must be positive")
        if self.temperature < 0:
            raise ValueError("temperature must be non-negative")
        if not 0 < self.top_p <= 1:
            raise ValueError("top_p must be in (0, 1]")
        if self.request_timeout_seconds <= 0:
            raise ValueError("request_timeout_seconds must be positive")

        # Canonicalize sequences so callers cannot mutate configuration state.
        object.__setattr__(self, "k_values", tuple(self.k_values))
        object.__setattr__(self, "l_values", tuple(self.l_values))
        object.__setattr__(self, "results_dir", Path(self.results_dir))
        object.__setattr__(self, "manual_audit_path", Path(self.manual_audit_path))

    @property
    def grid(self) -> tuple[GridConfiguration, ...]:
        """Return profiles in deterministic k-major, L-minor order."""

        return tuple(
            GridConfiguration(k=k, max_new_tokens=length)
            for k in self.k_values
            for length in self.l_values
        )

    @property
    def raw_results_dir(self) -> Path:
        return self.results_dir / "raw"

    @property
    def processed_results_dir(self) -> Path:
        return self.results_dir / "processed"

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable configuration snapshot."""

        payload = asdict(self)
        payload["results_dir"] = str(self.results_dir)
        payload["manual_audit_path"] = str(self.manual_audit_path)
        return payload
