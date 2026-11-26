"""Create the publication-cleanup inventory from a Git revision.

The inventory is intentionally based on the committed tree, so files already
missing from the working tree are still accounted for.  It does not modify the
index or the working tree.
"""

from __future__ import annotations

import argparse
import csv
import subprocess
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[2]
PROJECT_PREFIX = "oracle_experiment/"


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, encoding="utf-8")


def classify(path: str) -> dict[str, str]:
    relative = path.removeprefix(PROJECT_PREFIX)
    suffix = PurePosixPath(relative).suffix.lower() or "[none]"
    fields = {
        "extension": suffix,
        "file_category": "UNKNOWN_REQUIRES_REVIEW",
        "source_or_generated": "unknown",
        "reproducible": "unknown",
        "referenced_by_another_script": "not_evaluated",
        "scientific_evidence": "unknown",
        "recommended_action": "manual_review",
        "risk_level": "medium",
    }

    if relative.startswith(".artifact_work/"):
        root_utility = PurePosixPath(relative).parent == PurePosixPath(".artifact_work") and suffix in {
            ".py", ".ps1"
        }
        fields.update(
            file_category="LOCAL_ONLY" if root_utility else "GENERATED_TEMPORARY",
            source_or_generated="source_utility" if root_utility else "generated",
            reproducible="no" if root_utility else "yes",
            referenced_by_another_script="no",
            scientific_evidence="no",
            recommended_action="untrack_keep_local",
            risk_level="medium" if root_utility else "low",
        )
    elif relative.startswith("tmp/"):
        fields.update(
            file_category="GENERATED_TEMPORARY",
            source_or_generated="generated",
            reproducible="yes",
            referenced_by_another_script="no",
            scientific_evidence="no",
            recommended_action="untrack_keep_local",
            risk_level="low",
        )
    elif relative.startswith(".chart-data-"):
        fields.update(
            file_category="DUPLICATE",
            source_or_generated="generated",
            reproducible="yes",
            referenced_by_another_script="no",
            scientific_evidence="no",
            recommended_action="untrack_keep_local",
            risk_level="low",
        )
    elif relative == "download.txt":
        fields.update(
            file_category="SENSITIVE",
            source_or_generated="reviewer_material",
            reproducible="no",
            referenced_by_another_script="no",
            scientific_evidence="no",
            recommended_action="untrack_keep_local_do_not_publish",
            risk_level="high",
        )
    elif relative.startswith("paper/build/"):
        fields.update(
            file_category="GENERATED_TEMPORARY",
            source_or_generated="generated",
            reproducible="yes",
            referenced_by_another_script="no",
            scientific_evidence="no",
            recommended_action="untrack",
            risk_level="low",
        )
    elif relative.startswith("output/pdf/"):
        fields.update(
            file_category="FINAL_DELIVERABLE",
            source_or_generated="generated_from_source",
            reproducible="yes",
            referenced_by_another_script="no",
            scientific_evidence="yes",
            recommended_action="keep_tracked",
            risk_level="low",
        )
    elif relative.startswith("release/"):
        fields.update(
            file_category="RELEASE_ARTIFACT",
            source_or_generated="curated_release",
            reproducible="yes",
            referenced_by_another_script="yes",
            scientific_evidence="yes",
            recommended_action="keep_tracked_and_verify",
            risk_level="medium",
        )
    elif relative.startswith(("adaptive_compute/", "scripts/", "tests/")):
        fields.update(
            file_category="ESSENTIAL_SOURCE",
            source_or_generated="source",
            reproducible="not_applicable",
            referenced_by_another_script="not_applicable",
            scientific_evidence="no",
            recommended_action="keep_tracked",
            risk_level="high",
        )
    elif relative.startswith(("data/splits/", "paper/audit_outputs/", "paper/figures/")):
        fields.update(
            file_category="SCIENTIFIC_EVIDENCE",
            source_or_generated="curated_evidence",
            reproducible="yes",
            referenced_by_another_script="yes",
            scientific_evidence="yes",
            recommended_action="keep_tracked",
            risk_level="high",
        )
    elif relative.startswith(("paper/", "docs/", "thesis/")) or relative in {
        "README.md", ".gitignore", "requirements.txt", "pytest.ini"
    }:
        fields.update(
            file_category="ESSENTIAL_SOURCE",
            source_or_generated="source_documentation",
            reproducible="not_applicable",
            referenced_by_another_script="not_applicable",
            scientific_evidence="yes" if relative.startswith("paper/") else "no",
            recommended_action="keep_tracked",
            risk_level="medium",
        )
    elif relative.startswith(("deliverables/", "slides/")) or relative == "baocao.pdf":
        fields.update(
            file_category="FINAL_DELIVERABLE",
            source_or_generated="document_artifact",
            reproducible="unknown",
            referenced_by_another_script="no",
            scientific_evidence="no",
            recommended_action="author_review_before_public_snapshot",
            risk_level="medium",
        )
    elif relative.startswith("results/"):
        fields.update(
            file_category="SCIENTIFIC_EVIDENCE",
            source_or_generated="research_result",
            reproducible="unknown",
            referenced_by_another_script="yes",
            scientific_evidence="yes",
            recommended_action="keep_private_or_curate_into_release",
            risk_level="high",
        )
    return fields


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--revision", default="HEAD")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    lines = git("ls-tree", "-r", "-l", args.revision, "--", "oracle_experiment").splitlines()
    rows: list[dict[str, str | int]] = []
    for line in lines:
        metadata, path = line.split("\t", 1)
        mode, object_type, object_id, size_text = metadata.split()
        if object_type != "blob":
            continue
        local_path = ROOT / Path(path)
        try:
            worktree_state = "yes" if local_path.is_file() else "no"
        except OSError:
            worktree_state = "inaccessible"
        row: dict[str, str | int] = {
            "path": path,
            "size_bytes": int(size_text),
            "git_object": object_id,
            "git_tracked_at_revision": "yes",
            "exists_in_worktree": worktree_state,
        }
        row.update(classify(path))
        rows.append(row)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0])
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"revision={git('rev-parse', args.revision).strip()}")
    print(f"inventory_rows={len(rows)}")
    print(f"output={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
