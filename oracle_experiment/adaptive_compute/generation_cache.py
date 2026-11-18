"""Global, experiment-independent cache for deterministic model generations."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from adaptive_compute.logging_utils import append_jsonl_record


CACHE_SCHEMA_VERSION = 1
CACHE_IDENTITY_FIELDS = (
    "model_revision",
    "prompt_hash",
    "problem_id",
    "L",
    "repetition_id",
    "sample_id",
    "seed",
    "temperature",
    "top_p",
    "enable_thinking",
)


def generation_cache_key(record: Mapping[str, Any]) -> tuple[Any, ...]:
    """Return an exact generation identity; breadth k is deliberately absent."""

    missing = [field for field in CACHE_IDENTITY_FIELDS if field not in record]
    if missing:
        raise ValueError(f"generation cache identity is missing: {', '.join(missing)}")
    return (
        str(record["model_revision"]),
        str(record["prompt_hash"]),
        str(record["problem_id"]),
        int(record["L"]),
        int(record["repetition_id"]),
        int(record["sample_id"]),
        int(record["seed"]),
        float(record["temperature"]),
        float(record["top_p"]),
        bool(record["enable_thinking"]),
    )


def load_generation_cache(path: Path | None) -> dict[tuple[Any, ...], dict[str, Any]]:
    """Load the latest valid record for every cache identity."""

    if path is None or not path.exists():
        return {}
    records: dict[tuple[Any, ...], dict[str, Any]] = {}
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            if index == len(lines) - 1:
                break
            raise ValueError(f"corrupt generation cache record at line {index + 1}: {path}")
        if not isinstance(record, dict):
            raise ValueError(f"generation cache line {index + 1} is not a JSON object")
        if record.get("failure_type") == "generation_error":
            continue
        records[generation_cache_key(record)] = record
    return records


def cacheable_generation_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Materialize the fields needed to reuse and audit one generation."""

    generation_cache_key(record)  # validate the complete identity
    return {
        "cache_schema_version": CACHE_SCHEMA_VERSION,
        **{field: record[field] for field in CACHE_IDENTITY_FIELDS},
        "text": record.get("text", ""),
        "raw_response": record.get("raw_response", record.get("text", "")),
        "prompt_tokens": int(record.get("prompt_tokens", 0)),
        "generated_tokens": int(record.get("generated_tokens", 0)),
        "latency_ms": float(record.get("latency_ms", 0.0)),
        "finish_reason": record.get("finish_reason", "stop"),
        "source_experiment_id": record.get("experiment_id"),
        "source_device": record.get("device"),
        "source_dtype": record.get("dtype"),
        "failure_type": record.get("failure_type"),
    }


def add_generation_to_cache(
    path: Path | None,
    record: Mapping[str, Any],
    cache: dict[tuple[Any, ...], dict[str, Any]],
) -> bool:
    """Append a successful unseen generation to cache and update the index."""

    if path is None or record.get("failure_type") == "generation_error":
        return False
    payload = cacheable_generation_record(record)
    key = generation_cache_key(payload)
    if key in cache:
        return False
    append_jsonl_record(path, payload)
    cache[key] = payload
    return True


def populate_generation_cache(
    path: Path,
    records: Sequence[Mapping[str, Any]],
) -> dict[str, int]:
    """Seed a global cache from existing raw artifacts without altering them."""

    cache = load_generation_cache(path)
    added = skipped = 0
    for record in records:
        if add_generation_to_cache(path, record, cache):
            added += 1
        else:
            skipped += 1
    return {"cache_added": added, "cache_skipped": skipped, "cache_size": len(cache)}
