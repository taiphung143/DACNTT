# Controller Readiness Check

> Update (2026-11-12): the original audit below predates the completed
> Qwen3-0.6B GSM8K `n=79` Train grid. Sequential labels are now reproducibly
> materialized, but every stage remains below the 30-positive Train floor.
> The current evidence and decision are recorded in
> `SEQUENTIAL_LABEL_AUDIT_N79_2026-11-12.md`. The active decision remains
> **NEED MORE DATA / HEURISTIC BREADTH; do not fit or evaluate the learned
> joint controller and do not open Test**.

Audit date: 2026-11-11  
Intended primary model: `Qwen/Qwen3-0.6B` revision
`c1899de289a04d12100db370d81485cdf75e47ca`

## Decision

**Choice B -- NO: first complete controller training data.**

Do not implement or train the joint controller now. The historical 1.7B depth
baseline proves that the pipeline can train a leakage-safe small model; it does
not supply valid labels for the intended 0.6B policy.

## Readiness Matrix

| Requirement | Status | Repository evidence | Blocker / required action |
|---|---|---|---|
| Frozen problem-level split | PARTIAL / usable for GSM8K | `phase2_gsm8k_split_v1.json`: 79/20/100, hashes and disjointness tests | Reuse IDs for 0.6B; expand development scale and create a separate frozen MATH development/test design |
| Oracle outcomes for intended model | NO | 0.6B has only 30 MATH items at `k=1` | Generate 0.6B GSM8K and MATH shared sample pools including breadth |
| Labels derived without Test leakage | DESIGN READY, DATA MISSING | Depth builder materializes only Train/Validation; Test unopened | New sequential builder must preserve this rule and never materialize Test targets during development |
| Input feature extraction | YES | 37 allowlisted `feature_*` columns; deterministic tests | Revalidate tokenizer-dependent prompt count under the pinned 0.6B revision |
| Paid-state feature extraction | PARTIAL | Raw/config artifacts contain tokens, truncation, validity and agreement | Define one stage-aware feature schema and prohibit future/unpaid samples |
| Label imbalance measured | NO for intended model | Historical 1.7B: only 13/83 solved cases need `k>1`; depth classes are measured | Measure 0.6B per-stage positives before fitting; require 30 Train positives per learned stage |
| Training target formally defined | PARTIAL | Marginal utility is recommended in design docs | Freeze lambda grid, action semantics and label construction in protocol v2 |
| Cost target formally defined | YES at metric level | Actual Generated Tokens and latency are logged; all acquired samples are charged | Freeze utility scaling and whether latency is secondary only |
| Validation metric defined | YES | Policy accuracy, actual tokens, Pareto and go/pivot rules exist | Expand Validation before extensive selection; keep datasets separate |
| Deployment policy defined | PARTIAL | Stages `initial L`, `1->2`, `2->4` are specified | Implemented state machine and trace contract do not exist |
| Depth-only baseline | NO for intended model | 1.7B historical logistic baseline only | Refit using 0.6B labels after data readiness |
| Breadth-only baseline | NO | No deployable breadth policy module | Implement before the joint policy |
| Heuristic baseline | NO | Rules discussed only in documents | Freeze and implement before the joint policy |
| Held-out access control | YES | Frozen GSM8K Test and loader integrity checks | Keep Test blocked until policy freeze; add equivalent MATH control |

## Training Data Readiness

Current valid 0.6B data:

- 30 MATH-500 development problems;
- `k=1` only;
- `L={1024,2048,4096}`;
- 90/90 records and zero generation errors;
- one stochastic repetition.

This data can support token-cap feasibility analysis. It cannot train breadth
decisions, estimate joint utility, or validate cross-dataset policy behavior.

Required before training:

1. at least 200 usable 0.6B GSM8K development problems;
2. at least 100 usable MATH development problems across the final development
   design;
3. nested samples sufficient to reconstruct `k=1`, `k=2`, and `k=4` actions;
4. at least 30 Train-positive cases for each learned escalation stage;
5. a repeated-seed spot check for ambiguous labels;
6. no held-out Test materialized into the controller table.

## Label Readiness

Historical depth labels use “lowest observed correct `L`, else maximum `L`.”
That label is useful for the old depth-only baseline but is not the recommended
joint target. Cheapest-correct profile labels are also too brittle and
imbalanced for a sequential policy.

### Recommended training target: C -- marginal utility of extra compute

For each state `s` and permitted next action `a`, define:

```text
DeltaU_lambda(s,a)
  = DeltaCorrect(s,a) - lambda * DeltaActualGeneratedTokens(s,a)
```

The binary stage target is:

```text
escalate(s,a) = 1 if DeltaU_lambda(s,a) > 0 else 0
```

For the initial cap decision, select the cap with maximum observed utility
under the same pre-registered lambda. This remains one target family: marginal
utility under a cost trade-off.

Why this target:

- it aligns with the thesis endpoint rather than profile classification;
- it maps directly to sequential stop/escalate actions;
- it charges the incremental cost of every acquired trajectory;
- it supports several pre-registered lambda values and an accuracy--cost
  frontier;
- it avoids a sparse nine-class target.

Required labels per problem/state:

- correctness after the current paid state;
- correctness after the candidate next action;
- incremental actual generated tokens and latency;
- action availability and stage identity;
- dataset, model revision, parser version, seed and source hashes for
  provenance (dataset identity need not be a model feature).

Expected data issue: positive escalation labels will be the minority. Use
class weighting only on Train. Do not manufacture balance by duplicating
examples across splits. If fewer than 30 positives exist, keep the stage
heuristic or merge actions.

Evaluation must use policy-level accuracy, actual generated tokens, latency and
paired Pareto comparisons. Classification accuracy, macro-F1, AUROC and
calibration are diagnostics, not the thesis success criterion.

## Feature Readiness

### Ready now

- question/prompt length;
- number, fraction, operator and lexical counts;
- deterministic input-only feature allowlist;
- leakage rejection tests.

### Must be materialized by stage

- first-sample actual token count and cap utilization;
- finish reason and explicit truncation state;
- valid final-answer availability and format validity;
- after two samples: normalized-answer agreement and valid-answer fraction;
- cumulative tokens/latency already paid;
- stage/action identity.

### Forbidden

- ground truth or correctness at deployment;
- oracle or marginal-utility label;
- outcomes from trajectories not yet generated;
- aggregate Test statistics;
- 1.7B labels or controller coefficients used as 0.6B targets.

## Split Readiness

GSM8K split integrity is strong, but its current 79/20 development size was
designed for the historical n100 run and is too small for the intended joint
policy. Frozen IDs may be reused, but more disjoint 0.6B development IDs are
needed. The existing 100 Test IDs must remain untouched.

MATH-500 currently has a frozen 30-item development pilot, not a final
development/test split. Create a larger development manifest and an untouched
held-out manifest before controller fitting.

## Target Readiness

The mathematical form is recommended but not frozen. The following must be
approved before label generation:

- dataset-specific `L` action spaces;
- whether `L=512` is diagnostic-only on GSM8K;
- lambda/threshold grid;
- `-2 pp` non-inferiority margin;
- `k=1 -> 2` and `k=2 -> 4` action semantics;
- repeated-seed subset;
- rule for unsolved-by-all-actions cases.

## Baseline Readiness

Fixed profile evaluation code exists. The deployable depth, breadth, and
heuristic baselines for 0.6B do not. They should be implemented and validated
before the joint controller so that the joint method cannot be tuned against a
weak comparator.

## Evaluation Readiness

Metrics, paired statistics and go/pivot thresholds are specified. Evaluation
is not operationally ready because the selected 0.6B policy, expanded
Validation data, MATH held-out split and policy-freeze bundle do not exist.

## Gate to Begin Controller Training

Training may begin only when all conditions hold:

1. protocol v2 and action spaces are frozen;
2. 0.6B Train/Validation trajectories are complete and audited;
3. sequential state rows and marginal-utility labels are reproducible;
4. per-stage label balance is reported;
5. every learned stage has at least 30 Train positives, otherwise it is marked
   heuristic;
6. depth, breadth and heuristic baseline definitions are frozen;
7. final Test remains unopened.

## Final Readiness Decision

**READY FOR CONTROLLER TRAINING: NO**
