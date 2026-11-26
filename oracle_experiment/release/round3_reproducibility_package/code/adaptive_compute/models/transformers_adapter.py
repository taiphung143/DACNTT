"""Local Hugging Face Transformers implementation of ``ModelAdapter``."""

from __future__ import annotations

import time
from typing import Any

from adaptive_compute.models.base import GenerationResult, ModelAdapter


FORCED_ANSWER_SUFFIX = "</think>\n\nFinal answer:"


class TransformersModelAdapter(ModelAdapter):
    """Run one causal language model locally with normalized measurements.

    Sampling controls other than ``temperature`` are fixed at construction time
    so an experiment changes only breadth ``k`` and depth ``L``. CPU fallback is
    opt-in: the default raises if CUDA is unavailable, preventing accidental
    multi-hour CPU runs.
    """

    def __init__(
        self,
        model_id: str,
        *,
        revision: str = "main",
        device: str = "cuda",
        dtype: str = "bfloat16",
        top_p: float = 0.95,
        use_chat_template: bool = True,
        enable_thinking: bool = True,
        decoding_strategy: str = "standard",
        answer_reserve_tokens: int = 0,
        allow_cpu: bool = False,
    ) -> None:
        if not 0 < top_p <= 1:
            raise ValueError("top_p must be in (0, 1]")
        if decoding_strategy not in {"standard", "force_answer"}:
            raise ValueError("unsupported decoding_strategy")
        if answer_reserve_tokens < 0:
            raise ValueError("answer_reserve_tokens must be non-negative")
        if decoding_strategy == "standard" and answer_reserve_tokens != 0:
            raise ValueError("standard decoding requires answer_reserve_tokens=0")
        if decoding_strategy == "force_answer":
            if not enable_thinking:
                raise ValueError("force_answer decoding requires thinking mode")
            if answer_reserve_tokens <= 0:
                raise ValueError("force_answer decoding requires a positive answer reserve")

        try:
            import torch
            import transformers

            # Standard autoregressive generation uses neither scikit-learn nor
            # SciPy. Recent Transformers versions nevertheless import them for
            # optional assisted-generation calibration and object-detection
            # losses. Treat those optional features as unavailable so their
            # installation cannot block the causal-LM path used here.
            transformers.utils.is_sklearn_available = lambda: False
            transformers.utils.is_scipy_available = lambda: False
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError(
                "Transformers inference dependencies are missing. "
                "Install requirements in the oracle_slm environment."
            ) from exc

        if device.startswith("cuda") and not torch.cuda.is_available():
            if not allow_cpu:
                raise RuntimeError(
                    "CUDA was requested but is unavailable; refusing implicit CPU fallback"
                )
            device = "cpu"

        dtype_map = {
            "bfloat16": torch.bfloat16,
            "float16": torch.float16,
            "float32": torch.float32,
        }
        if dtype not in dtype_map:
            raise ValueError(f"unsupported dtype: {dtype}")
        if device == "cpu" and dtype == "float16":
            raise ValueError("float16 CPU inference is not supported by this adapter")
        if device.startswith("cuda") and dtype == "bfloat16" and not torch.cuda.is_bf16_supported():
            raise RuntimeError("the selected CUDA device does not support bfloat16")

        self.model_id = model_id
        self.revision = revision
        self.device = torch.device(device)
        self.dtype_name = dtype
        self.top_p = top_p
        self.use_chat_template = use_chat_template
        self.enable_thinking = enable_thinking
        self.decoding_strategy = decoding_strategy
        self.answer_reserve_tokens = answer_reserve_tokens
        self._torch = torch

        self.tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_id,
            revision=revision,
            dtype=dtype_map[dtype],
            low_cpu_mem_usage=True,
        )
        self.model.to(self.device)
        self.model.eval()

        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token_id = self.tokenizer.eos_token_id

    @property
    def resolved_revision(self) -> str | None:
        """Commit hash resolved by Hugging Face, when exposed by model config."""

        return getattr(self.model.config, "_commit_hash", None)

    def _encode_prompt(self, prompt: str) -> dict[str, Any]:
        if not prompt.strip():
            raise ValueError("prompt must not be empty")
        if self.use_chat_template:
            encoded = self.tokenizer.apply_chat_template(
                [{"role": "user", "content": prompt}],
                add_generation_prompt=True,
                tokenize=True,
                return_dict=True,
                return_tensors="pt",
                enable_thinking=self.enable_thinking,
            )
        else:
            encoded = self.tokenizer(prompt, return_tensors="pt")
        return {key: value.to(self.device) for key, value in encoded.items()}

    def generate(
        self,
        prompt: str,
        max_new_tokens: int,
        temperature: float,
        seed: int | None = None,
    ) -> GenerationResult:
        if max_new_tokens <= 0:
            raise ValueError("max_new_tokens must be positive")
        if temperature < 0:
            raise ValueError("temperature must be non-negative")
        if (
            self.decoding_strategy == "force_answer"
            and self.answer_reserve_tokens >= max_new_tokens
        ):
            raise ValueError("answer reserve must be smaller than max_new_tokens")

        torch = self._torch
        inputs = self._encode_prompt(prompt)
        prompt_tokens = int(inputs["input_ids"].shape[-1])
        do_sample = temperature > 0

        if seed is not None:
            torch.manual_seed(seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(seed)

        generation_kwargs: dict[str, Any] = {
            "max_new_tokens": max_new_tokens,
            "do_sample": do_sample,
            "pad_token_id": self.tokenizer.pad_token_id,
            "eos_token_id": self.tokenizer.eos_token_id,
            "use_cache": True,
        }
        if do_sample:
            generation_kwargs.update(temperature=temperature, top_p=self.top_p)

        if self.device.type == "cuda":
            torch.cuda.synchronize(self.device)
        start = time.perf_counter()
        with torch.inference_mode():
            if self.decoding_strategy == "force_answer":
                result = self._generate_with_forced_answer(
                    inputs=inputs,
                    max_new_tokens=max_new_tokens,
                    generation_kwargs=generation_kwargs,
                )
            else:
                output_ids = self.model.generate(**inputs, **generation_kwargs)
                generated_ids = output_ids[0, prompt_tokens:]
                result = (
                    generated_ids,
                    generated_ids,
                    False,
                    0,
                    max_new_tokens,
                )
        if self.device.type == "cuda":
            torch.cuda.synchronize(self.device)
        latency_ms = (time.perf_counter() - start) * 1000.0

        generated_ids, text_ids, forced_transition, injected_tokens, final_cap = result
        generated_tokens = int(generated_ids.shape[-1])
        text = self.tokenizer.decode(text_ids, skip_special_tokens=True).strip()
        finish_reason = infer_finish_reason(
            generated_ids=generated_ids,
            generated_tokens=generated_tokens,
            max_new_tokens=final_cap,
            eos_token_id=self.tokenizer.eos_token_id,
        )
        return GenerationResult(
            text=text,
            prompt_tokens=prompt_tokens,
            generated_tokens=generated_tokens,
            latency_ms=latency_ms,
            finish_reason=finish_reason,
            forced_transition=forced_transition,
            injected_control_tokens=injected_tokens,
        )

    def _generate_with_forced_answer(
        self,
        *,
        inputs: dict[str, Any],
        max_new_tokens: int,
        generation_kwargs: dict[str, Any],
    ) -> tuple[Any, Any, bool, int, int]:
        """Reserve answer tokens and close an unfinished Qwen3 thinking block.

        The total number of model-generated tokens remains bounded by
        ``max_new_tokens``. Injected control tokens are recorded separately and
        are included in parser-visible text, but not counted as generated cost.
        """

        torch = self._torch
        answer_reserve = self.answer_reserve_tokens
        thinking_cap = max_new_tokens - answer_reserve
        phase1_kwargs = {**generation_kwargs, "max_new_tokens": thinking_cap}
        phase1_output = self.model.generate(**inputs, **phase1_kwargs)
        prompt_tokens = int(inputs["input_ids"].shape[-1])
        phase1_ids = phase1_output[0, prompt_tokens:]
        phase1_tokens = int(phase1_ids.shape[-1])
        phase1_finish = infer_finish_reason(
            generated_ids=phase1_ids,
            generated_tokens=phase1_tokens,
            max_new_tokens=thinking_cap,
            eos_token_id=self.tokenizer.eos_token_id,
        )
        if phase1_finish != "length":
            return phase1_ids, phase1_ids, False, 0, thinking_cap

        phase1_text = self.tokenizer.decode(phase1_ids, skip_special_tokens=True)
        if "</think>" in phase1_text:
            control_ids = torch.empty((0,), dtype=phase1_ids.dtype, device=self.device)
        else:
            encoded_control = self.tokenizer(
                FORCED_ANSWER_SUFFIX,
                add_special_tokens=False,
                return_tensors="pt",
            )["input_ids"][0]
            control_ids = encoded_control.to(self.device)

        context_ids = torch.cat(
            [inputs["input_ids"][0], phase1_ids, control_ids], dim=0
        ).unsqueeze(0)
        continuation_inputs = {
            "input_ids": context_ids,
            "attention_mask": torch.ones_like(context_ids),
        }
        phase2_kwargs = {**generation_kwargs, "max_new_tokens": answer_reserve}
        phase2_output = self.model.generate(**continuation_inputs, **phase2_kwargs)
        phase2_ids = phase2_output[0, context_ids.shape[-1] :]
        generated_ids = torch.cat([phase1_ids, phase2_ids], dim=0)
        text_ids = torch.cat([phase1_ids, control_ids, phase2_ids], dim=0)
        return (
            generated_ids,
            text_ids,
            True,
            int(control_ids.shape[-1]),
            max_new_tokens,
        )


def infer_finish_reason(
    *,
    generated_ids: Any,
    generated_tokens: int,
    max_new_tokens: int,
    eos_token_id: int | list[int] | None,
) -> str:
    """Map generated token state to a provider-neutral finish reason."""

    if generated_tokens >= max_new_tokens:
        return "length"
    if generated_tokens == 0:
        return "empty"
    eos_ids = (
        set(eos_token_id)
        if isinstance(eos_token_id, list)
        else {eos_token_id} if eos_token_id is not None else set()
    )
    last_token_id = int(generated_ids[-1])
    return "stop" if last_token_id in eos_ids else "unknown"
