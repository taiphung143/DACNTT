"""Populate the local round-3 reproducibility package and checksum manifest."""

from __future__ import annotations

import csv
import hashlib
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "release" / "round3_reproducibility_package"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def copy_file(relative: str, destination_root: str) -> None:
    source = ROOT / relative
    if not source.is_file():
        raise FileNotFoundError(source)
    destination = PACKAGE / destination_root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def main() -> int:
    PACKAGE.mkdir(parents=True, exist_ok=True)

    code_files = [
        *(
            str(path.relative_to(ROOT))
            for path in sorted((ROOT / "adaptive_compute").rglob("*.py"))
            if "__pycache__" not in path.parts
        ),
        "scripts/final_scientific_audit.py",
        "scripts/round3_reviewer_audit.py",
    ]
    for relative in code_files:
        source = ROOT / relative
        destination = PACKAGE / "code" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    manifest_files = [
        "data/splits/phase2_gsm8k_split_v1.json",
        "data/splits/math500_split_v1.json",
        "results/raw/gsm8k_subset_manifest_n100.json",
        "results/phase2/gsm8k_policy_freeze_v1/policy_freeze.json",
        "results/phase2/gsm8k_policy_freeze_v1/policy_freeze.sha256",
        "results/phase2/math500_policy_freeze_v1/policy_freeze.json",
        "results/phase2/math500_policy_freeze_v1/policy_freeze.sha256",
        "results/phase2/qwen3_0_6b_gsm8k_test_n100_policy_replay_v3/replay_manifest.json",
        "results/phase2/qwen3_0_6b_math500_test_n100_baseline_replay_v1/replay_manifest.json",
        "results/phase2/qwen3_0_6b_forceanswer_test_comparison_v1/comparison_manifest.json",
    ]
    for relative in manifest_files:
        copy_file(relative, "manifests")

    replay_directories = [
        ROOT / "results" / "phase2" / "qwen3_0_6b_gsm8k_test_n100_policy_replay_v3",
        ROOT / "results" / "phase2" / "qwen3_0_6b_math500_test_n100_baseline_replay_v1",
        ROOT / "results" / "phase2" / "qwen3_0_6b_forceanswer_test_comparison_v1",
        ROOT / "results" / "phase2" / "qwen3_0_6b_nonthinking_validation_comparison_v1",
    ]
    allowed_suffixes = {".csv", ".json", ".sha256", ".md"}
    for directory in replay_directories:
        target = PACKAGE / "results" / directory.name
        target.mkdir(parents=True, exist_ok=True)
        for source in sorted(directory.iterdir()):
            if source.is_file() and source.suffix.lower() in allowed_suffixes:
                shutil.copy2(source, target / source.name)

    audit_target = PACKAGE / "audit_outputs"
    audit_target.mkdir(parents=True, exist_ok=True)
    for source in sorted((ROOT / "paper" / "audit_outputs").iterdir()):
        if source.is_file() and source.suffix.lower() in {".csv", ".json"}:
            shutil.copy2(source, audit_target / source.name)

    manifest_path = PACKAGE / "MANIFEST_SHA256.csv"
    packaged = [
        path
        for path in sorted(PACKAGE.rglob("*"))
        if path.is_file() and path != manifest_path
    ]
    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "size_bytes", "sha256"])
        writer.writeheader()
        for path in packaged:
            writer.writerow(
                {
                    "path": str(path.relative_to(PACKAGE)).replace("\\", "/"),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
    print(f"packaged_files={len(packaged)}")
    print(f"manifest={manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
