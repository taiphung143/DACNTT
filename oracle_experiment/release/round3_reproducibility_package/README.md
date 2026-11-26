# Round-3 reproducibility package

This local package supports GPU-free verification of the paper's policy replay
and round-3 reviewer checks. It was prepared from existing frozen artifacts;
no model generation or Test-dependent policy tuning was performed.

Contents:

- `code/`: inference, parsing, aggregation, replay, statistics, and audit code.
- `manifests/`: frozen dataset splits and policy/replay metadata.
- `results/`: machine-readable policy summaries, prediction-level replay
  traces, paired controls, and force-answer comparison metadata.
- `audit_outputs/`: paper-facing verification tables.
- `REPLAY_GUIDE.md`: commands for GPU-free verification.
- `MISSING_OR_RESTRICTED_ARTIFACTS.md`: explicit reproducibility limits.
- `SOURCE_PROVENANCE.json`: base Git revision and hashes of packaged source.
- `MANIFEST_SHA256.csv`: path, size, and SHA-256 for every packaged file.

The package verifies reproducibility Level 1 (checksums) and Level 2
(CSV/trace-based paper results). It does not provide Level 3 replay from full
raw generations. The package is not a public release. Dataset redistribution
rights and raw-model-output distribution must be checked before publication.
