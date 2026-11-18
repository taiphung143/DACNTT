# Cross-Dataset GO/PIVOT Decision

Decision date: 2026-11-14  
Status: frozen before MATH-500 Test access

## Decision

**Do not promote the joint controller as the primary method. Pivot to the
registered depth-first/single-axis interpretation and dataset-specific frozen
baselines.**

This decision does not change the Research Question. It records that the
current evidence answers the proposed joint-policy hypothesis negatively at
the Validation stage.

## Evidence used

Only frozen Train and Validation artifacts are used for this decision.
Existing GSM8K Test results are not used to select or modify the policies.
MATH-500 Test outcomes remain unopened.

### GSM8K Validation

- selected policy: agreement stopping at `L=1024`;
- accuracy: 15/20 = 75%;
- mean actual generated tokens: 2,095.85;
- the joint heuristic also reaches 75% but uses 2,149.05 tokens;
- the historical GSM8K freeze already records `joint_go_status` as not met.

### MATH-500 Validation

- fixed `2x4096`: 13/20 = 65% at 4,700.50 mean tokens;
- joint depth-first heuristic: 10/20 = 50% at 5,935.55 tokens;
- agreement stopping at `L=4096`: 13/20 = 65% at 7,564.65 tokens;
- every adaptive policy is point-Pareto-dominated by fixed profiles;
- the selected MATH policy is fixed `2x4096`.

## Gate assessment

`GO JOINT` is not satisfied because:

1. no learned joint stage reaches the registered 30-positive Train floor;
2. the joint heuristic is dominated on MATH Validation;
3. the required benefit direction does not agree across the two datasets;
4. no joint operating point demonstrates the registered accuracy/cost gain
   over strong single-axis comparators on both datasets.

The appropriate protocol outcome is
`PIVOT_DEPTH_FIRST_AND_DATASET_SPECIFIC_FIXED_BASELINES`. This is a valid
negative thesis result: aggregate test-time compute helps, but the tested
cheap input and paid-state heuristics do not allocate it robustly across
datasets.

## Frozen selections

| Dataset | Frozen policy | Validation accuracy | Mean actual tokens | Selection status |
|---|---|---:|---:|---|
| GSM8K | breadth agreement `L=1024` | 75% | 2,095.85 | historical pre-Test freeze |
| MATH-500 | fixed `2x4096` | 65% | 4,700.50 | transparent post-Validation pivot |

The MATH selection rule is explicitly recorded after observing that every
adaptive Validation point was dominated. It must not be described as a
pre-registered policy choice.

## Claim boundary

Completed evidence supports:

- reproducible two-dataset compute characterization;
- strong aggregate depth effects on Train and Validation point estimates;
- sparse, stage-dependent breadth gains;
- failure of the current joint heuristic to generalize as a cross-dataset
  Pareto improvement;
- value of strong fixed and single-axis baselines.

It does not support universal controller superiority, learned joint-policy
effectiveness, or MATH Test performance. Validation `n=20` is insufficient to
claim population-level equivalence when observed accuracies match.

## Freeze and next authorized work

The immutable MATH bundle is
`results/phase2/math500_policy_freeze_v1/policy_freeze.json`, SHA-256
`79163f652a451af43380fab32a8f1ef3c4885c9f7fbebef014f5ecce595974b4`.

The machine-readable cross-dataset decision is
`results/phase2/cross_dataset_decision_v1/decision.json`.

Before MATH Test generation:

1. verify the decision and freeze hashes;
2. calculate the exact GPU envelope for the one-shot confirmatory run;
3. execute only the frozen command, without parser, action-space, threshold,
   or policy changes;
4. report all registered comparators and do not retune after Test.
