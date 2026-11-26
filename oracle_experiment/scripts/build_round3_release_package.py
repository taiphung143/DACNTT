"""Build the round-3 reproducibility package through a verified staging tree."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE_ROOT = ROOT / "release"
PACKAGE = RELEASE_ROOT / "round3_reproducibility_package"
STAGING = RELEASE_ROOT / ".round3_reproducibility_package.staging"
BACKUP = RELEASE_ROOT / ".round3_reproducibility_package.backup"


def _assert_safe_release_path(path: Path, expected_name: str) -> None:
    resolved_parent = path.resolve().parent
    if resolved_parent != RELEASE_ROOT.resolve() or path.name != expected_name:
        raise RuntimeError(f"unsafe release path: {path}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, encoding="utf-8").strip()


def copy_file(package: Path, relative: str, destination_root: str) -> Path:
    source = ROOT / relative
    if not source.is_file():
        raise FileNotFoundError(source)
    destination = package / destination_root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination


def write_manifest(package: Path) -> int:
    manifest_path = package / "MANIFEST_SHA256.csv"
    packaged = [
        path for path in sorted(package.rglob("*")) if path.is_file() and path != manifest_path
    ]
    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "size_bytes", "sha256"])
        writer.writeheader()
        for path in packaged:
            writer.writerow(
                {
                    "path": str(path.relative_to(package)).replace("\\", "/"),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
    return len(packaged)


def verify_manifest(package: Path) -> None:
    manifest_path = package / "MANIFEST_SHA256.csv"
    with manifest_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    expected = {row["path"] for row in rows}
    actual = {
        str(path.relative_to(package)).replace("\\", "/")
        for path in package.rglob("*")
        if path.is_file() and path != manifest_path
    }
    if expected != actual:
        raise RuntimeError("staging manifest does not describe the complete package")
    for row in rows:
        path = package / row["path"]
        if path.stat().st_size != int(row["size_bytes"]) or sha256(path) != row["sha256"]:
            raise RuntimeError(f"staging checksum mismatch: {row['path']}")


def populate(package: Path) -> int:
    package.mkdir(parents=True, exist_ok=False)
    code_files = [
        *(
            str(path.relative_to(ROOT))
            for path in sorted((ROOT / "adaptive_compute").rglob("*.py"))
            if "__pycache__" not in path.parts
        ),
        "scripts/final_scientific_audit.py",
        "scripts/round3_reviewer_audit.py",
        "scripts/verify_round3_release.py",
    ]
    source_hashes: dict[str, str] = {}
    for relative in code_files:
        destination = copy_file(package, relative, "code")
        source_hashes[relative.replace("\\", "/")] = sha256(destination)

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
        copy_file(package, relative, "manifests")

    replay_directories = [
        ROOT / "results" / "phase2" / "qwen3_0_6b_gsm8k_test_n100_policy_replay_v3",
        ROOT / "results" / "phase2" / "qwen3_0_6b_math500_test_n100_baseline_replay_v1",
        ROOT / "results" / "phase2" / "qwen3_0_6b_forceanswer_test_comparison_v1",
        ROOT / "results" / "phase2" / "qwen3_0_6b_nonthinking_validation_comparison_v1",
    ]
    allowed_suffixes = {".csv", ".json", ".sha256", ".md"}
    for directory in replay_directories:
        target = package / "results" / directory.name
        target.mkdir(parents=True, exist_ok=True)
        for source in sorted(directory.iterdir()):
            if source.is_file() and source.suffix.lower() in allowed_suffixes:
                shutil.copy2(source, target / source.name)

    audit_target = package / "audit_outputs"
    audit_target.mkdir(parents=True, exist_ok=True)
    for source in sorted((ROOT / "paper" / "audit_outputs").iterdir()):
        if source.is_file() and source.suffix.lower() in {".csv", ".json"}:
            shutil.copy2(source, audit_target / source.name)

    # Documentation is an explicit allowlist; unrelated stale files cannot survive.
    for name in ("README.md", "REPLAY_GUIDE.md", "MISSING_OR_RESTRICTED_ARTIFACTS.md"):
        source = PACKAGE / name
        if not source.is_file():
            raise FileNotFoundError(source)
        shutil.copy2(source, package / name)

    snapshot_lines = [f"{path}\t{digest}" for path, digest in sorted(source_hashes.items())]
    snapshot_id = hashlib.sha256("\n".join(snapshot_lines).encode("utf-8")).hexdigest()
    status = git("status", "--porcelain=v1", "--untracked-files=no")
    provenance = {
        "schema_version": 1,
        "base_git_commit": git("rev-parse", "HEAD"),
        "worktree_clean": not bool(status),
        "uncommitted_modifications_present": bool(status),
        "source_snapshot_sha256": snapshot_id,
        "packaged_source_sha256": source_hashes,
        "reproducibility_level": 2,
        "level_definition": "checksum plus CSV/trace-based result verification",
        "full_raw_generation_replay_available": False,
    }
    (package / "SOURCE_PROVENANCE.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    count = write_manifest(package)
    verify_manifest(package)
    return count


def publish_verified_staging() -> None:
    _assert_safe_release_path(PACKAGE, "round3_reproducibility_package")
    _assert_safe_release_path(STAGING, ".round3_reproducibility_package.staging")
    _assert_safe_release_path(BACKUP, ".round3_reproducibility_package.backup")
    if BACKUP.exists():
        raise RuntimeError(f"manual review required for existing backup: {BACKUP}")
    PACKAGE.rename(BACKUP)
    try:
        STAGING.rename(PACKAGE)
    except Exception:
        BACKUP.rename(PACKAGE)
        raise
    shutil.rmtree(BACKUP)


def main() -> int:
    RELEASE_ROOT.mkdir(parents=True, exist_ok=True)
    _assert_safe_release_path(STAGING, ".round3_reproducibility_package.staging")
    if STAGING.exists():
        shutil.rmtree(STAGING)
    count = populate(STAGING)
    publish_verified_staging()
    print(f"packaged_files={count}")
    print(f"manifest={PACKAGE / 'MANIFEST_SHA256.csv'}")
    print(f"base_git_commit={git('rev-parse', 'HEAD')}")
    print("staging_manifest_verification=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
