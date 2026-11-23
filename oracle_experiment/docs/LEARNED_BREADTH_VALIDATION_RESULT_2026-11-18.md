# Frozen learned-breadth controller: Validation-20 result

Date: 2026-11-18

## Evidence status

This is a one-shot replay on the pre-registered GSM8K Validation-20 and
MATH-500 Validation-20 partitions. The controller, feature schema, thresholds,
comparison policy, and gate were frozen before the Validation labels were
materialized. No held-out Test-100 artifact was loaded. These results are
development/model-selection evidence, not final confirmatory evidence.

Frozen policy: `learned_breadth_high_v1` (`depth_threshold=0`,
`breadth_threshold=0.005`). It always uses the dataset-specific high token
limit and adaptively selects breadth. The comparator is `agreement_high`.

## Result

| Dataset | Learned controller | Agreement-high | Accuracy gap | Token saving | Gate |
|---|---:|---:|---:|---:|---:|
| GSM8K | 14/20 (70%), 1,798.25 tokens | 15/20 (75%), 3,114.80 tokens | -5 pp | 42.27% | Fail accuracy; pass cost |
| MATH-500 | 13/20 (65%), 5,551.90 tokens | 13/20 (65%), 7,564.65 tokens | 0 pp | 26.61% | Pass |
| Pooled, descriptive only | 27/40 (67.5%), 3,675.08 tokens | 28/40 (70%), 5,339.73 tokens | -2.5 pp | 31.17% | Not used for gate |

The frozen gate required, separately on both datasets, an accuracy gap of at
least -2 percentage points and a token saving of at least 10%. McNemar's exact
paired p-value is 1.0 on each dataset; with only 20 items per dataset this does
not establish equivalence or non-inferiority.

## Decision

**`PIVOT_NO_RESERVE_FOR_THIS_CONTROLLER`**.

The MATH-500 result supports the working hypothesis that selective breadth can
retain the agreement comparator's observed accuracy while reducing generated
tokens. The GSM8K result does not pass the pre-declared accuracy margin despite
large token savings. Therefore this particular learned controller is not
authorized for reserve/Test evaluation. Its threshold must not be retuned on
these Validation outcomes and its result must not be presented as a final
held-out controller contribution.

The negative cross-dataset gate is itself useful feasibility evidence: the
Train-OOF breadth signal did not transfer uniformly to the frozen Validation
partitions. The already frozen Test-100 results for deterministic policies
remain the thesis's primary evidence and are unchanged.

## Reproducibility record

- Freeze: `results/phase2/qwen3_0_6b_learned_breadth_validation_freeze_v1/`
- Freeze manifest SHA-256:
  `bbf082f9e0f1dceaf004c7fa1df6ae0a90bd7d115c16fa08603bad1eda794d80`
- Replay: `results/phase2/qwen3_0_6b_learned_breadth_validation_replay_v1/`
- Gate decision: `validation_gate_decision.json`
- Paired rows: `validation_paired_comparison.csv`
- Full automated suite after the replay: 185 passed, 0 failed.

