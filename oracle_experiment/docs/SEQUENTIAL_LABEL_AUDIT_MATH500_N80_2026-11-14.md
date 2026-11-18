# Sequential Label Audit: Qwen3-0.6B MATH-500 Train n=80

Audit date: 2026-11-14  
Status: completed Train evidence; Validation and Test remain unopened

## Decision

The frozen MATH-500 Train run passes the provenance, completeness,
parser-contract, leakage, and sequential-label construction checks. It does
not pass the pre-registered 30-positive floor for any learned sequential
decision.

- Data-pipeline decision: **PASS**.
- Learned per-stage joint-controller decision: **NEED MORE DATA / KEEP RARE
  BREADTH STAGES HEURISTIC**.
- Method direction: **continue with the registered depth-first policy and
  strong fixed/depth/breadth/heuristic replay baselines before fitting a joint
  learner**.
- Validation decision: **do not use MATH Validation for threshold or policy
  selection until the applicable policy definitions and replay contract are
  frozen**.
- Test decision: **DO NOT OPEN**.

## Completed evidence

Source experiment:
`results/qwen3_0_6b_math500_train_n80_contract_v1`

Derived label artifact:
`results/phase2/qwen3_0_6b_math500_train_n80_sequential_labels_v1`

Frozen contract:

- model `Qwen/Qwen3-0.6B`, revision
  `c1899de289a04d12100db370d81485cdf75e47ca`;
- prompt `math500_cot_v1` and parser `math500_exact_v2`;
- `k in {1,2,4}`, `L in {1024,2048,4096}`;
- utility reference `T_ref=4096` and
  `lambda in {0.02,0.05,0.10}`;
- split manifest `data/splits/math500_split_v1.json`.

Integrity checks:

- 80/80 frozen Train problems;
- 960/960 unique raw generation records and 720/720 configuration rows;
- zero generation errors, missing expected keys, or duplicate keys;
- 480 unique depth-label rows and 1,440 unique breadth-label rows;
- all derived rows are Train rows; no Validation or Test rows are materialized;
- zero overlap between allowed features and forbidden labels/outcomes;
- hashes recorded for raw samples, configuration results, experiment
  manifest, split manifest, label tables, balance report, and feature schema.

## Output-contract audit

There are 562 truncated samples among 960 generations. Every one of the 562
parse failures is truncated, while all 398 non-truncated samples are parsed
successfully. Thus, the observed invalid-answer burden is explained by the
frozen hard cap rather than a parser-contract defect.

Raw truncation by cap is 259/320 (80.9%) at `L=1024`, 179/320 (55.9%) at
`L=2048`, and 124/320 (38.8%) at `L=4096`. This is a model/action-space
outcome and is retained in paid-state features; it is not grounds for a
post-hoc action-space change.

## Sequential label balance

Counts below are reported once per stage. The three lambda rows are
sensitivity settings derived from the same outcomes and are not independent
training examples. Positive counts are identical across the registered
lambda grid for this run.

| Stage | Positive | Regression | Unchanged | Positive rate | Wilson 95% interval | Meets 30-positive floor |
|---|---:|---:|---:|---:|---:|---:|
| Depth `L1024 -> L2048` | 22 | 0 | 58 | 27.5% | 18.9--38.1% | No |
| Depth `L2048 -> L4096` | 8 | 0 | 72 | 10.0% | 5.2--18.5% | No |
| Breadth `L1024, k1 -> k2` | 10 | 0 | 70 | 12.5% | 6.9--21.5% | No |
| Breadth `L1024, k2 -> k4` | 2 | 0 | 78 | 2.5% | 0.7--8.7% | No |
| Breadth `L2048, k1 -> k2` | 2 | 0 | 78 | 2.5% | 0.7--8.7% | No |
| Breadth `L2048, k2 -> k4` | 6 | 0 | 74 | 7.5% | 3.5--15.4% | No |
| Breadth `L4096, k1 -> k2` | 4 | 0 | 76 | 5.0% | 2.0--12.2% | No |
| Breadth `L4096, k2 -> k4` | 5 | 0 | 75 | 6.2% | 2.7--13.8% | No |

Point-estimate sample sizes required to observe 30 positives range from about
110 problems for `L1024 -> L2048` to 1,200 for the two rarest breadth stages.
These are planning projections, not guaranteed requirements. Expanding solely
to satisfy every rare breadth stage is outside the undergraduate thesis
budget and would not be scientifically justified by the current evidence.

## Interpretation

This is completed Train evidence, not held-out controller performance. The
labels show substantial depth opportunity at the first cap transition and
sparse, stage-dependent breadth opportunity. They support the working
hypothesis that a depth-first policy is the most feasible primary direction,
but they do not establish that any learned policy can predict the positive
cases.

The retrospective oracle and these marginal-utility labels use correctness to
construct targets. Correctness, future samples, label columns, and outcome
columns remain forbidden at deployment time.

## Authorized next work

1. Generalize the replayable fixed-profile and registered depth-first
   heuristic baselines to the MATH-500 cap set.
2. Verify that fixed replay exactly reproduces all nine Train grid endpoints
   and charges every generated token.
3. Freeze the MATH policy trace/schema and heuristic parameters without using
   Validation outcomes.
4. Only then generate/replay the frozen MATH Validation-20 partition for
   threshold/model selection.
5. Keep rare breadth stages heuristic unless a versioned data expansion is
   approved; do not fit per-stage joint classifiers from the current n=80.
6. Keep the MATH Test-100 partition unopened until the complete policy bundle
   is frozen and hashed.
