"""Shared-sample generation, deterministic identity, and JSONL checkpoints."""

from __future__ import annotations

import hashlib
import json
import platform
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any

from config import ExperimentConfig
from dataset import GSM8KProblem
from dataset_audit import ManualAuditEntry, get_dataset_quality_flag
from evaluate import evaluate_response
from logging_utils import append_jsonl_record
from models.base import ModelAdapter
from prompts import GSM8K_PROMPT_TEMPLATE, build_gsm8k_prompt


SAMPLE_SEED_POLICY = (
    "sha256(global_seed|problem_id|repetition_id|sample_id), first 63 bits; "
    "independent of k and L"
)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def stable_sample_seed(
    global_seed: int,
    problem_id: str,
    sample_id: int,
    repetition_id: int = 0,
) -> int:
    """Return a stable paired seed that deliberately excludes both k and L."""

    if sample_id < 0 or repetition_id < 0:
        raise ValueError("sample_id and repetition_id must be non-negative")
    payload = f"{global_seed}|{problem_id}|{repetition_id}|{sample_id}"
    digest = hashlib.sha256(payload.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") & ((1 << 63) - 1)


def prompt_hash(question: str) -> str:
    return sha256_text(build_gsm8k_prompt(question))


def sample_key(record: Mapping[str, Any]) -> tuple[Any, ...]:
    """Identity of one generated sample. Breadth k is intentionally absent."""

    return (
        record.get("experiment_id"),
        record.get("problem_id"),
        int(record["L"]),
        int(record.get("sample_id", 0)),
        int(record.get("repetition_id", 0)),
        record.get("model_revision"),
        record.get("prompt_hash"),
    )


def latest_checkpoint_records(path: Path) -> dict[tuple[Any, ...], dict[str, Any]]:
    """Index a JSONL checkpoint; later retry records supersede earlier failures."""

    if not path.exists():
        return {}
    lines = path.read_text(encoding="utf-8").splitlines()
    records: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            # A process can die between write() and fsync(). Only a malformed
            # final line is safely recognizable as an interrupted append.
            if index == len(lines) - 1:
                break
            raise ValueError(f"corrupt checkpoint record at line {index + 1}: {path}")
        if not isinstance(record, dict):
            raise ValueError(f"checkpoint line {index + 1} is not a JSON object")
        records.append(record)
    return {sample_key(record): record for record in records}


def derive_shared_prefix(
    samples: Sequence[Mapping[str, Any]], k: int
) -> list[Mapping[str, Any]]:
    """Derive k from the first k samples of one shared, ordered sample pool."""

    if k <= 0:
        raise ValueError("k must be positive")
    ordered = sorted(samples, key=lambda item: int(item["sample_id"]))
    expected_ids = list(range(k))
    actual_ids = [int(item["sample_id"]) for item in ordered[:k]]
    if len(ordered) < k or actual_ids != expected_ids:
        raise ValueError(f"shared sample pool is incomplete for k={k}")
    return ordered[:k]


def experiment_identity(config: ExperimentConfig, problem_ids: Sequence[str]) -> dict[str, Any]:
    return {
        "model": config.model_id,
        "model_revision": config.model_revision,
        "dataset": config.dataset_id,
        "problem_ids": list(problem_ids),
        "global_seed": config.global_seed,
        "k_values": list(config.k_values),
        "L_values": list(config.l_values),
        "num_repetitions": config.num_repetitions,
        "temperature": config.temperature,
        "top_p": config.top_p,
        "enable_thinking": config.enable_thinking,
        "prompt_hash": sha256_text(GSM8K_PROMPT_TEMPLATE),
        "sample_seed_policy": SAMPLE_SEED_POLICY,
    }


def default_experiment_id(config: ExperimentConfig, problem_ids: Sequence[str]) -> str:
    identity = experiment_identity(config, problem_ids)
    digest = sha256_text(json.dumps(identity, sort_keys=True, separators=(",", ":")))[:10]
    model_slug = re.sub(r"[^a-z0-9]+", "-", config.model_id.lower()).strip("-")
    return f"{model_slug}_gsm8k_n{len(problem_ids)}_seed{config.global_seed}_{digest}"


def _package_versions() -> dict[str, str | None]:
    versions: dict[str, str | None] = {"python": platform.python_version()}
    for package in ("torch", "transformers", "datasets", "accelerate", "matplotlib"):
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            versions[package] = None
    return versions


def build_experiment_manifest(
    *,
    experiment_id: str,
    config: ExperimentConfig,
    problems: Sequence[GSM8KProblem],
    dataset_manifest_hash: str,
    device: str,
    dtype: str,
) -> dict[str, Any]:
    identity = experiment_identity(config, [item.problem_id for item in problems])
    return {
        "schema_version": 1,
        "experiment_id": experiment_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **identity,
        "dataset_manifest_hash": dataset_manifest_hash,
        "num_problems": len(problems),
        "max_shared_samples": max(config.k_values),
        "expected_generations": (
            len(problems) * len(config.l_values) * max(config.k_values) * config.num_repetitions
        ),
        "device": device,
        "dtype": dtype,
        "library_versions": _package_versions(),
        "config": config.to_dict(),
    }


def create_or_validate_manifest(
    path: Path,
    proposed: Mapping[str, Any],
    *,
    resume: bool,
) -> dict[str, Any]:
    """Create an immutable manifest, or validate it before resuming."""

    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if not resume:
            raise FileExistsError(
                f"experiment already exists at {path.parent}; use --resume"
            )
        for key in (
            "experiment_id",
            "model",
            "model_revision",
            "dataset_manifest_hash",
            "problem_ids",
            "global_seed",
            "sample_seed_policy",
            "prompt_hash",
            "k_values",
            "L_values",
            "temperature",
            "top_p",
            "enable_thinking",
            "device",
            "dtype",
        ):
            if existing.get(key) != proposed.get(key):
                raise ValueError(f"resume manifest mismatch for {key}")
        return existing
    if resume:
        raise FileNotFoundError(f"cannot resume: manifest does not exist at {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(dict(proposed), handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return dict(proposed)


def run_shared_sample_pool(
    *,
    config: ExperimentConfig,
    problems: Sequence[GSM8KProblem],
    adapter: ModelAdapter,
    experiment_id: str,
    raw_samples_path: Path,
    audit_entries: Mapping[str, ManualAuditEntry],
    resume: bool = False,
    retry_errors: bool = False,
) -> dict[str, int]:
    """Generate max(k) samples per problem/L and checkpoint every outcome."""

    if raw_samples_path.exists() and not resume:
        raise FileExistsError(f"raw checkpoint exists: {raw_samples_path}; use --resume")
    completed = latest_checkpoint_records(raw_samples_path) if resume else {}
    generated = skipped = failed = 0
    max_k = max(config.k_values)
    resolved_revision = getattr(adapter, "resolved_revision", None) or config.model_revision

    for repetition_id in range(config.num_repetitions):
        for problem in problems:
            prompt = build_gsm8k_prompt(problem.question)
            per_problem_prompt_hash = sha256_text(prompt)
            quality_flag = get_dataset_quality_flag(problem.problem_id, audit_entries)
            for length in config.l_values:
                for sample_id in range(max_k):
                    identity_record = {
                        "experiment_id": experiment_id,
                        "problem_id": problem.problem_id,
                        "L": length,
                        "sample_id": sample_id,
                        "repetition_id": repetition_id,
                        "model_revision": resolved_revision,
                        "prompt_hash": per_problem_prompt_hash,
                    }
                    key = sample_key(identity_record)
                    previous = completed.get(key)
                    if previous is not None and not (
                        retry_errors and previous.get("failure_type") == "generation_error"
                    ):
                        skipped += 1
                        continue

                    seed = stable_sample_seed(
                        config.global_seed, problem.problem_id, sample_id, repetition_id
                    )
                    generation_error: str | None = None
                    try:
                        generation = adapter.generate(
                            prompt,
                            max_new_tokens=length,
                            temperature=config.temperature,
                            seed=seed,
                        )
                        generation_payload = asdict(generation)
                        evaluation = evaluate_response(
                            generation.text,
                            problem.ground_truth,
                            finish_reason=generation.finish_reason,
                            generated_tokens=generation.generated_tokens,
                            max_new_tokens=length,
                            dataset_quality_flag=quality_flag,
                        )
                    except Exception as exc:  # one failed sample must not abort the grid
                        generation_error = f"{type(exc).__name__}: {exc}"
                        generation_payload = {
                            "text": "",
                            "prompt_tokens": 0,
                            "generated_tokens": 0,
                            "latency_ms": 0.0,
                            "finish_reason": "error",
                        }
                        evaluation = evaluate_response(
                            "",
                            problem.ground_truth,
                            finish_reason="error",
                            generated_tokens=0,
                            max_new_tokens=length,
                            generation_error=generation_error,
                            dataset_quality_flag=quality_flag,
                        )
                        failed += 1

                    record = {
                        **identity_record,
                        "question": problem.question,
                        "dataset": problem.dataset,
                        "model": config.model_id,
                        "seed": seed,
                        **generation_payload,
                        **asdict(evaluation),
                        "ground_truth_raw": problem.ground_truth_raw,
                        "generation_error": generation_error,
                        "device": str(getattr(adapter, "device", config.model_backend)),
                        "dtype": str(getattr(adapter, "dtype_name", config.model_dtype)),
                        "temperature": config.temperature,
                        "top_p": config.top_p,
                        "enable_thinking": config.enable_thinking,
                    }
                    append_jsonl_record(raw_samples_path, record)
                    completed[key] = record
                    generated += 1
    return {"generated": generated, "skipped": skipped, "failed": failed}
