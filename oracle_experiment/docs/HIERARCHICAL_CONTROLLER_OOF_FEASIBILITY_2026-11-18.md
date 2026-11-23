# Hierarchical Controller Train-Only OOF Feasibility

Date: 2026-11-18  
Primary artifact: `results/phase2/qwen3_0_6b_pooled_hierarchical_controller_oof_v5`  
Evidence status: completed development evidence; not Validation or Test evidence

## Decision

The pooled controller implementation is operational and leakage-audited. The
learned selective-breadth candidate at the dataset-specific high token cap
passes the predeclared Train-OOF feasibility gate and may advance to the
untouched Validation stage. The hybrid joint depth--breadth candidate does not
meet the token-saving gate and must not advance to reserve evaluation in its
current form.

- Learned breadth/high-cap decision: **GO TO FROZEN VALIDATION**.
- Hybrid joint decision: **CONDITIONAL / MORE DATA OR PIVOT**.
- GPU decision: **do not generate a new reserve set yet**.

These decisions do not alter the frozen Test-100 results or the current thesis
claims.

## Completed implementation

The feasibility pipeline now provides:

- a shared class-balanced logistic depth model and a shared class-balanced
  logistic breadth model;
- dataset, normalized stage/cap and allowlisted input features;
- paid-state breadth features including token utilization, validity,
  truncation and answer agreement;
- safety rules that force continuation after an invalid/truncated first sample
  and stop after two matching valid answers;
- five-fold `StratifiedGroupKFold` OOF prediction grouped by
  `dataset + problem_id`;
- policy-level replay with complete actual-token charging;
- strong fixed-high and agreement-high comparator reconstruction;
- a versioned threshold sweep, model bundle, traces, summaries, fold audit,
  decision artifact and source/output hashes.

No `label_*`, `outcome_*`, correctness, ground truth or unpaid future sample is
admitted to the model feature allowlist.

## Data and OOF integrity

The study uses only the frozen Train sequential-label artifacts:

| Dataset | Problems |
|---|---:|
| GSM8K | 79 |
| MATH-500 | 80 |
| Total | 159 |

At primary `lambda=0.05`, the pooled tables contain 318 depth rows with 51
positive escalation labels and 954 breadth rows with 59 positives. The three
lambda settings from the source artifacts are not counted as independent
examples.

All five folds report zero overlap between Train and OOF problem groups. Each
problem's repeated cap/stage rows remain in one fold. The already-opened
Test-100 artifacts are not input sources and `held_out_test_used=false` is
recorded in the manifest.

OOF discrimination is moderate rather than conclusive:

| Family | Scope | ROC-AUC | Average precision |
|---|---|---:|---:|
| Depth | pooled | 0.656 | 0.305 |
| Breadth | pooled | 0.761 | 0.187 |
| Breadth | GSM8K | 0.839 | 0.308 |
| Breadth | MATH-500 | 0.676 | 0.103 |

The low MATH breadth average precision is a material risk and must remain in
the interpretation.

## Policy-level OOF results

### Learned selective breadth at high cap

Candidate: `d=0|b=0.005`. Here `d=0` always chooses the dataset-specific high
cap; therefore this candidate is not a joint depth--breadth result.

| Dataset | Learned breadth | Agreement-high | Token change |
|---|---:|---:|---:|
| GSM8K | 64/79, 1,513.66 tokens | 62/79, 2,249.68 tokens | -32.72% |
| MATH-500 | 50/80, 7,070.53 tokens | 51/80, 8,730.08 tokens | -19.01% |

The MATH accuracy difference is -1/80 = -1.25 percentage points, within the
development non-inferiority margin of -2 points. This is an OOF development
observation, not a powered non-inferiority conclusion.

### Hybrid joint candidate

Candidate: `d=0.005|b=0`. The depth router sends five GSM8K and five MATH
problems to the middle cap; breadth falls back to the registered agreement
rule.

| Dataset | Hybrid joint | Agreement-high | Token change |
|---|---:|---:|---:|
| GSM8K | 62/79, 2,267.30 tokens | 62/79, 2,249.68 tokens | +0.78% |
| MATH-500 | 50/80, 8,415.00 tokens | 51/80, 8,730.08 tokens | -3.61% |

Accuracy stays within the development margin, but token savings are neither at
least 10% nor positive on both datasets. The current joint candidate therefore
does not justify reserve generation.

## Scientific interpretation

The completed evidence supports a narrower next step than originally hoped:

1. A learned breadth gate has a credible Train-OOF signal and should be tested
   once on the untouched existing Validation partitions.
2. The current input-only depth router does not add a stable efficiency gain.
3. Passing Validation for learned breadth would establish an implemented
   controller candidate, but it would still not prove a successful joint
   controller.
4. If Validation fails, this controller must be retained as a negative
   development result and GPU effort should move to decoding controls and
   extra-seed robustness.

Thresholds were explored on OOF Train predictions. They must not be tuned
again after reading Validation outcomes. Before Validation replay, the exact
candidate role, feature contract, thresholds, model hashes and selection rule
must be frozen.

## Software validation and environment note

The repository test suite passes with the new implementation: 183 tests
passed. The feasibility artifact was built with Python 3.12.6,
scikit-learn 1.6.1, SciPy 1.14.1 and joblib 1.4.2; these versions are recorded
in the V5 manifest.

The `oracle_slm` Miniconda environment currently fails while importing SciPy's
`_propack` DLL, including when invoked through `conda run`. This is an
environment regression relative to the 2026-11-16 validation, not a controller
test failure. No package was reinstalled or mutated during this task. Repair or
revalidate that environment before the next GPU experiment.

## Authorized next step

Materialize sequential labels for the already generated GSM8K Validation-20
and MATH-500 Validation-20 grids without reading Test, freeze the V5 model and
candidate definitions, and perform one Validation replay. Do not create or
open a new reserve split until that gate is complete.

