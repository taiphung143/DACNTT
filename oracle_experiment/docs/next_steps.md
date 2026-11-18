# Next Steps

Audit date: 2026-11-11

## Immediate Decision

The project should not start joint-controller implementation yet.

**Current phase:** Phase 2A -- freeze the Qwen3-0.6B protocol and construct
model-specific controller data.  
**Main blocker:** no 0.6B GSM8K/breadth labels or sequential marginal-utility
training table.  
**Next milestone:** an audited, controller-ready 0.6B two-dataset development
pool with class-balance evidence.

## 1. Next 3 Priorities

Exactly three priorities should be active.

### Priority 1 -- Freeze the Qwen3-0.6B protocol amendment

**Goal:** convert the current recommendations into one versioned executable
contract before more GPU generation.

**Why it comes now:** the repository contains a historical 1.7B protocol and a
0.6B migration amendment, but no single frozen document resolves cap sets,
lambda/thresholds, MATH splits, seed plan and baseline definitions for the
current model.

**Files/modules likely affected:**

- new `docs/PHASE2_PROTOCOL_QWEN3_0_6B_V2.md`;
- `data/splits/` for larger development and untouched MATH manifests;
- later, only if approved, configuration defaults/CLI presets.

**Output artifact:** protocol v2 containing model/dataset revisions, cap sets,
`k` stages, utility grid, `-2 pp` margin, baseline definitions, positive-event
floor, repetition plan and Test access rule.

**Done criterion:** supervisor/team approval, immutable manifest hashes, and a
`--validate-only` plan whose expected generation counts fit the GPU budget.

### Priority 2 -- Generate and audit Qwen3-0.6B controller data

**Goal:** obtain model-specific trajectories and sequential labels without
touching final Test.

**Why it comes now:** every controller target is model-, prompt-, parser-, seed-
and action-space-dependent. Historical 1.7B data cannot supervise 0.6B.

**Files/modules likely affected:**

- `adaptive_compute/cli/run_grid.py` and existing runner/cache, preferably
  without redesign;
- frozen GSM8K/MATH development manifests;
- new results directories for 0.6B development runs;
- later, a stage-aware controller-data builder.

**Output artifact:** complete raw/config results plus a sequential development
table with input features, paid-state features, actions, incremental costs,
marginal-utility labels and a label-balance report.

**Done criterion:** at least 200 usable GSM8K and 100 usable MATH development
problems overall; no Test outcomes; parser error rate at most 2%; and at least
30 Train positives per learned escalation stage or an explicit heuristic-stage
decision.

### Priority 3 -- Implement and validate the baseline suite

**Goal:** establish fair fixed, 0.6B depth-only, breadth-only and heuristic
frontiers before the joint method.

**Why it comes now:** the scientific claim is only meaningful against strong
single-axis policies. A joint controller tuned before its comparators would
encourage moving thresholds and weak baselines.

**Files/modules likely affected:**

- `adaptive_compute/controller/` for depth/breadth/heuristic policies;
- a policy executor/trace schema;
- CLI evaluation entry point;
- tests for signal availability and complete cost charging.

**Output artifact:** serialized baseline policies, per-problem Validation
traces, accuracy--actual-token frontiers, and paired comparison report.

**Done criterion:** all baselines run end-to-end on expanded Validation using
only permitted signals; traces reconstruct every paid sample; policy metrics
and Pareto points are available; all tests pass.

## 2. Exact Task Sequence

1. Mark the 0.6B migration amendment and 2026-11-11 scope audit as current;
   mark older “1.7B primary” plans as historical.
2. Freeze dataset-specific cap sets. Do not assume the 1.7B GSM8K caps and
   0.6B MATH caps must be identical.
3. Freeze marginal-utility lambda/threshold grid, non-inferiority margin,
   escalation semantics and seed plan.
4. Create/validate larger development manifests and a separate untouched MATH
   held-out manifest.
5. Run a bounded 20--30 item 0.6B GSM8K timing/action-space pilot.
6. Audit validity, truncation, latency, cache identity and positive escalation
   rate before committing the full pool.
7. Generate the checkpointed 0.6B GSM8K development pool; analyze after each
   block rather than waiting for all items.
8. Build sequential state/action records and the marginal-utility label report.
9. If the GSM8K pipeline is end-to-end and label semantics are stable, expand
   MATH-500 development from 30 to at least 100 usable items and add bounded
   breadth samples.
10. Apply the data-readiness gate. If a learned stage has fewer than 30 Train
    positives, simplify it or keep it heuristic.
11. Implement fixed, depth-only, breadth-only and heuristic policies.
12. Run expanded Validation, then decide whether joint-controller training may
    begin.

## 3. What to Postpone

Do not work on the following now:

- Qwen3-1.7B `L=8192` or any full long-cap extension;
- held-out GSM8K Test generation or inspection;
- joint-controller code before data and baselines;
- flat nine-class XGBoost as the primary method;
- boosted-tree tuning before the positive-event floor;
- secondary model family or universal controller;
- SVAMP or a third dataset;
- RL, PRM, verifier training, fine-tuning or neural controllers;
- LangGraph, RAG, multi-agent orchestration, web application or deployment;
- additional paper polishing, slide redesign or result-free figures.

## 4. Dataset Expansion Timing

**Choice B -- expand MATH-500 after a GSM8K controller-data/policy prototype.**

The MATH adapter and 30-item depth pilot already exist, so no new dataset
engineering should delay GSM8K. First prove that the 0.6B GSM8K path can
generate trajectories, construct sequential labels and replay one simple
policy end-to-end. Then expand MATH before final controller selection and
before any held-out evaluation.

Why not A: expanding MATH before verifying the label/policy contract risks
spending expensive GPU time on unusable trajectories.  
Why not C or D: waiting until all baselines or GSM8K Test would make the method
dataset-specific and would delay parser/action-space corrections until too
late.

## 5. Model Strategy

- **Use now:** Qwen3-0.6B at the pinned revision.
- **New oracle labels:** required for every intended 0.6B controller action.
- **Reusable from 1.7B:** code, frozen problem IDs, parser contracts, feature
  ideas, statistical methods and historical context.
- **Not reusable from 1.7B:** generations, correctness outcomes, oracle labels,
  coefficients, thresholds or latency estimates.
- **Secondary model:** only after the two-dataset core result and policy freeze;
  use a small frozen subset and a reduced action space. Omit it if it threatens
  held-out rigor or the thesis deadline.

## 6. Entry and Exit Criteria

### Enter data generation

- protocol v2 approved;
- manifests and action spaces frozen;
- expected GPU hours reviewed;
- Test access rule recorded;
- smoke/validate-only checks pass.

### Exit controller-data construction

- 200+ usable GSM8K and 100+ usable MATH development problems;
- raw and derived artifacts complete and hashed;
- parser/manual-audit failures at most 2%;
- stage-label distribution and repeated-seed spot check reported;
- 30 positives per learned stage or a documented heuristic fallback.

### Enter joint-controller implementation

- baseline definitions frozen;
- depth-only, breadth-only and heuristic policies run end-to-end;
- feature availability contract enforced by tests;
- expanded Validation exists;
- final Test still unopened.

### Exit Validation

- complete Pareto frontiers and paired uncertainty;
- GO JOINT, PIVOT DEPTH-FIRST, NEED MORE DATA or ABANDON decision recorded;
- selected policy, parser, features, thresholds, manifests and revisions
  serialized and hashed.

### Enter final Test

- selected policy bundle immutable;
- no unresolved parser/data issue;
- one-shot test command and analysis plan reviewed;
- both GSM8K and MATH held-out manifests frozen.

## 7. Go / Pivot Gates

### GO TO JOINT CONTROLLER TRAINING

Only if controller data, paid-state features and baselines are ready, and every
learned breadth stage has at least 30 Train positives. Otherwise remain in
Phase 2/3.

### GO JOINT AS PRIMARY METHOD

On expanded Validation, joint must either:

- improve accuracy over depth-only by at least 3 percentage points at actual
  tokens within +/-10%; or
- reduce actual tokens by at least 10% while satisfying the frozen `-2 pp`
  accuracy non-inferiority rule.

It must not be Pareto-dominated by breadth-only or the heuristic, and the
benefit direction must agree across GSM8K and MATH.

### PIVOT DEPTH-FIRST

Pivot if joint is Pareto-dominated by depth-only at every registered point, or
if breadth produces less than 2 pp gain and less than 5% token saving on each
dataset after adequate data. Retain breadth as a heuristic/negative finding.

### NEED MORE DATA

Do not select a method when a stage has fewer than 30 positives, the key
accuracy-difference interval is wider than 10 pp, repeated-seed target
agreement is below 0.70, or parser issues affect more than 2% of items.

### ABANDON LEARNED CONTROLLER

After at least 300 usable two-dataset development problems, pivot to a rigorous
characterization thesis if learned depth and joint policies remain dominated
by fixed or heuristic policies across two seeds and no data defect explains
the failure.

## 8. Minimum Viable Thesis

A defensible minimum thesis contains:

1. the reproducible inference, parsing, caching and evaluation system;
2. the completed 1.7B/GSM8K breadth--token-cap characterization;
3. Qwen3-0.6B development data on GSM8K and MATH-500;
4. strong fixed, depth-only, breadth-only and heuristic baselines;
5. a sequential joint controller **or** a pre-registered depth-first pivot;
6. one frozen held-out evaluation on both datasets;
7. paired accuracy/actual-token analysis and an honest positive or negative
   conclusion.

A secondary model, web application and complex learner are not required.

## 9. Strongest Realistic Thesis

After the minimum version is secure, add extras in this order of research
value:

1. repeated-seed robustness on ambiguous/Validation and bounded Test subsets;
2. input-only versus paid-state feature ablation;
3. sequential versus flat/heuristic formulation ablation;
4. cross-dataset training analysis (GSM-only, pooled, dataset-specific);
5. lambda/threshold sensitivity and calibration;
6. reduced different-family model validation;
7. shallow boosted-tree comparison;
8. optional read-only demonstration.

The strongest realistic result is a two-dataset, cost-matched held-out study
with a sequential policy, strong baselines, repeated-seed and feature
ablations, plus a small different-family validation if GPU/time remain.

## 10. First Task Tomorrow

Do not launch a large GPU run. Draft and freeze the one-page decision table in
`PHASE2_PROTOCOL_QWEN3_0_6B_V2.md`: per-dataset caps, development/test counts,
lambda/threshold grid, seed plan, baseline definitions, positive-event floor
and final-Test access rule. Then run `--validate-only` to calculate the exact
generation count and GPU-hour envelope for the 20--30 problem GSM8K pilot.
