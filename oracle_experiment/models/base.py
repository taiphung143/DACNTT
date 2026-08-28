"""Provider-neutral model generation contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class GenerationResult:
    """Normalized metadata returned for one successful generation."""

    text: str
    prompt_tokens: int
    generated_tokens: int
    latency_ms: float
    finish_reason: str | None

    def __post_init__(self) -> None:
        if self.prompt_tokens < 0:
            raise ValueError("prompt_tokens must be non-negative")
        if self.generated_tokens < 0:
            raise ValueError("generated_tokens must be non-negative")
        if self.latency_ms < 0:
            raise ValueError("latency_ms must be non-negative")

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.generated_tokens


class ModelAdapter(ABC):
    """Minimal interface implemented by every inference backend."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        max_new_tokens: int,
        temperature: float,
        seed: int | None = None,
    ) -> GenerationResult:
        """Generate one independent sample and return normalized measurements."""

        raise NotImplementedError

