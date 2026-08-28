"""Logging setup shared by command-line entry points."""

from __future__ import annotations

import logging
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


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

