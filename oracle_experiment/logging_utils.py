"""Logging setup shared by command-line entry points."""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def read_json_records(path: Path) -> list[dict[str, Any]]:
    """Read a JSON object/array or JSONL file."""

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if path.suffix.lower() == ".jsonl":
        records = [json.loads(line) for line in text.splitlines() if line.strip()]
    else:
        payload = json.loads(text)
        records = payload if isinstance(payload, list) else [payload]
    if not all(isinstance(record, dict) for record in records):
        raise ValueError(f"{path} must contain JSON objects")
    return records


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    """Atomically write records in append-friendly JSONL format."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    temporary.replace(path)


def append_jsonl_record(path: Path, record: dict[str, Any]) -> None:
    """Durably append one checkpoint record and flush it to disk immediately."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
