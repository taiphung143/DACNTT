"""Researcher-authored dataset audit flags; never mutates dataset labels."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from adaptive_compute.config import MANUAL_AUDIT_PATH
from adaptive_compute.evaluate import DATASET_QUALITY_FLAGS


@dataclass(frozen=True)
class ManualAuditEntry:
    status: str
    note: str


def load_manual_audit(path: Path = MANUAL_AUDIT_PATH) -> dict[str, ManualAuditEntry]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("manual audit file must contain a JSON object")
    entries: dict[str, ManualAuditEntry] = {}
    for problem_id, raw_entry in payload.items():
        if not isinstance(raw_entry, Mapping):
            raise ValueError(f"invalid manual audit entry for {problem_id}")
        status = raw_entry.get("status")
        note = raw_entry.get("note", "")
        if status is None or status not in DATASET_QUALITY_FLAGS:
            raise ValueError(f"invalid manual audit status for {problem_id}: {status}")
        entries[str(problem_id)] = ManualAuditEntry(str(status), str(note))
    return entries


def get_dataset_quality_flag(
    problem_id: str, entries: Mapping[str, ManualAuditEntry]
) -> str | None:
    entry = entries.get(problem_id)
    return entry.status if entry is not None else None
