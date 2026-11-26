# Repository cleanup audit

Date: 2026-11-26  
Repository root: `C:/Users/taiph/OneDrive/Desktop/DATN`  
Base HEAD: `98127d80d7589ee6a8c54a0f3fee3f6b70e300e7` (`main`)

## Outcome

The cleanup changed the Git index only. It did not delete primary experiments,
frozen manifests, source code, tests, paper source, figures, final PDFs, or
release evidence. Generated/local trees remain on disk and are now ignored.

| Metric | Before (HEAD) | Cleanup index | Change |
|---|---:|---:|---:|
| Tracked files | 21,971 | 374 | -21,597 |
| Tracked blob bytes | 1,339,371,061 | 17,384,095 | -1,321,986,966 |
| Tracked content | 1,277.32 MiB | 16.58 MiB | -98.70% |

The after count is the staged cleanup index before the new audit reports and
verification scripts are added. No commit was created.

## Untracked safely

- `.artifact_work/`: 20,562 files, 1,042.31 MiB. It contains downloaded
  dependencies, render products, binaries, and four old document utilities.
  The utilities remain local-only because no canonical source/script reference
  was found; no physical deletion occurred.
- `tmp/`: 1,019 files, 216.14 MiB, consisting of PDF dependencies and temporary
  render state.
- Five `.chart-data-*` trees: 10 generated PPTX/snapshot files.
- `paper/build/`: reproducible LaTeX auxiliary/build outputs. Final deliverables
  remain in `output/pdf/`.
- `download.txt`: reviewer material with unclear redistribution permission. It
  remains local and is excluded from public candidates.

Existing working-tree deletions of dependency files were not restored. They are
now part of the deliberate generated-tree untracking operation.

## Ignore rules and verification

Both repository and project `.gitignore` files now cover Python caches, local
environments, secrets/key material, editor state, `.artifact_work/`, `tmp/`,
`.chart-data-*`, `paper/build/`, `download.txt`, and local `results/`.
`git check-ignore -v` verified every project-specific rule. Broad rules for
JSON, CSV, TeX, PDF, Markdown, `paper/`, and `release/` were intentionally not
added.

## Preserved material

- `adaptive_compute/`, `scripts/`, `tests/`, and `data/splits/`.
- `paper/audit_outputs/`, `paper/figures/`, paper source, and final PDFs.
- Frozen policy/replay manifests and all local primary raw generation files.
- `release/round3_reproducibility_package/` and release documentation.

The full baseline inventory is `docs/repository_cleanup_inventory.csv` (21,970
project rows; root `.gitignore` is outside the project inventory).

## Physical deletion

No pre-existing project data was physically deleted. Three temporary directories
created during this audit (one clean-room copy and two PDF-render directories)
were removed after verification.

## Remaining Git actions

The index contains the staged untracking operation; paper, documentation,
release-package, ignore-rule, and script changes remain uncommitted. The author
must review `git diff --cached --stat`, `git diff`, and untracked files before
deciding whether to add/commit. No push was performed.
