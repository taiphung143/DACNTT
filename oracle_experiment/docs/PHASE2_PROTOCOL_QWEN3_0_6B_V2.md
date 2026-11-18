# Phase 2 Protocol v2: Qwen3-0.6B

Status: **frozen for pilot and controller-data construction**  
Freeze date: 2026-11-11  
Supersedes: the current-model portions of `PHASE2_PROTOCOL.md` and the
provisional steps in `MODEL_MIGRATION_QWEN3_0_6B.md`

Active amendment: `GSM8K_PROMPT_V3_AMENDMENT.md`. All new GSM8K generations
use prompt `gsm8k_cot_v3` and parser `gsm8k_numeric_v3`. The completed
prompt-v1 pilot, parser-v2 derivative, and failed prompt-v2 smoke remain
immutable and separately reported.

## 1. Scope and Model Decision

All new characterization, controller-data generation, policy fitting, model
selection, and confirmatory evaluation use:

- model: `Qwen/Qwen3-0.6B`;
- revision: `c1899de289a04d12100db370d81485cdf75e47ca`;
- backend: Transformers, CUDA, bfloat16;
- chat template and thinking mode enabled;
- temperature `0.7`, top-p `0.95`, global seed `42`.

Qwen3-0.6B is the final primary model for this thesis. Qwen3-1.7B artifacts
remain valid historical characterization only. Its outcomes, oracle labels,
controller parameters, thresholds, and latency estimates must not supervise or
be pooled with the 0.6B study. A second model is outside the core thesis and
may be added only after the minimum thesis is complete.

This protocol operationalizes the existing research questions; it does not
change their wording or the meaning of breadth, token cap, or actual compute.

## 2. Dataset Roles and Access Control

The required datasets are GSM8K and MATH-500.

- Development target: at least 200 usable GSM8K problems and 100 usable
  MATH-500 problems across Train and Validation.
- The existing frozen GSM8K problem identities may be reused, but every 0.6B
  trajectory and model-dependent label must be regenerated.
- The frozen 100-problem GSM8K Test partition remains unopened until the final
  policy, features, parser, thresholds, and baselines are serialized and
  hashed.
- A versioned MATH-500 Train/Validation/Test design must be frozen before the
  MATH development pool is expanded. The existing 30-item pilot is development
  evidence, not a final Test set.
- Protocol and action-space pilots use Train problems only. Validation is used
  for model/threshold selection, never for feature or label redesign after
  seeing final outcomes.
- No final-Test trajectory may enter training, calibration, ablation, or
  debugging.

## 3. Frozen Action Spaces

### GSM8K

- breadth: `k in {1, 2, 4}`;
- generation-token cap: `L in {512, 1024, 2048}`.

### MATH-500

- breadth: `k in {1, 2, 4}`;
- generation-token cap: `L in {1024, 2048, 4096}`;
- `L=8192` is excluded on feasibility grounds.

`L` always means `max_new_tokens`, not semantic reasoning depth. For each
problem and cap, generate one nested pool of four samples; the `k=1`, `k=2`,
and `k=4` policies use prefixes `[0]`, `[0,1]`, and `[0,1,2,3]`. Every policy
is charged for all trajectories it actually generated.

An action-space change requires a named protocol amendment supported by pilot
evidence. It must never be made after looking at final-Test performance.

## 4. Bounded GSM8K Pilot

Before scale-up, run exactly the first 30 problems of the frozen Train
partition under the GSM8K action space. This pilot checks the data path and
compute envelope; it is not a paper-level accuracy estimate.

The pilot must report:

- 360 expected unique generations (`30 problems x 3 caps x max(k)=4`);
- generation/parser errors and valid-answer rate;
- accuracy, actual generated tokens, latency, and truncation by `(k,L)`;
- incremental correctness from depth and breadth;
- cache hits, skipped records, and manifest/config hashes;
- projected runtime for 100 and 200 development problems.

Scale beyond 30 only if all records are checkpointed, generation errors are at
most 2%, parser/manual-audit issues are at most 2%, the maximum cap does not
show a protocol-breaking truncation pattern, and the projected workload fits
the thesis schedule. Otherwise issue a versioned amendment before scaling.

## 5. Sequential Policy and Training Target

The policy is hierarchical and depth-first:

1. choose an initial dataset-specific token cap from input-only features;
2. generate sample 1;
3. stop or escalate from `k=1` to `k=2` using only paid state;
4. stop or escalate from `k=2` to `k=4` using only paid state.

The primary training target is **marginal utility of extra compute**, not a
flat nine-profile class and not the hindsight cheapest-correct profile.

For action `a` from state `s`, define normalized realized utility as:

```text
U_lambda(a | s) = correctness_after_action
                  - lambda * additional_actual_tokens / T_ref(dataset)
```

where `T_ref(GSM8K)=2048` and `T_ref(MATH-500)=4096`. An escalation label is
positive when its paired change in utility is greater than zero. The
pre-registered sensitivity grid is `lambda in {0.02, 0.05, 0.10}`. Lambda and
decision thresholds are selected using Validation policy frontiers only;
classification accuracy is diagnostic, not the primary success measure.

Because one stochastic realization creates noisy utility labels, ambiguous
Validation cases receive repeated seeds before final policy freeze. At least
three seeds are required on the bounded repeated-seed subset. Target agreement
below 0.70 triggers `NEED MORE DATA` or a heuristic fallback.

## 6. Features and Leakage Boundary

Input-only features may include question length, prompt-token count, numerical
quantity counts, operator counts, and pre-registered lexical indicators.
Paid-state features may include generated-token count, cap utilization,
finish/truncation state, parser validity, answer agreement, and valid-answer
fraction after the samples already generated.

Forbidden inputs include ground truth, correctness, oracle/cheapest-correct
labels, future samples, outcomes from actions not yet paid for, Validation/Test
aggregate outcomes, and all 1.7B model-specific labels.

Every training table must distinguish input features, paid-state features,
actions, realized costs, outcomes, and labels. Automated leakage tests are
required before controller fitting.

## 7. Baseline-First Requirement

The following policies must run end-to-end on the same 0.6B trajectories
before the joint controller is trained:

1. all fixed `(k,L)` profiles;
2. pre-registered depth-first heuristic;
3. learned depth-only controller;
4. breadth-only adaptive stopping;
5. retrospective depth, breadth, and joint oracles as upper bounds only.

The primary comparator is the strongest depth-only or heuristic policy at
comparable actual generated-token cost, not merely the most expensive fixed
profile.

## 8. Controller-Readiness Gate

Controller training may begin only when:

1. Train/Validation manifests and this protocol are frozen;
2. required 0.6B trajectories are complete and audited;
3. sequential states and marginal-utility labels are reproducible;
4. per-stage label balance is reported;
5. every learned stage has at least 30 positive Train events, otherwise that
   stage is explicitly heuristic;
6. fixed, depth-only, breadth-only, and heuristic definitions are frozen;
7. final Test remains unopened.

Until all seven conditions hold: **READY FOR CONTROLLER TRAINING: NO**.

## 9. Evaluation and Go/Pivot Rules

Primary outcomes are final-answer accuracy and actual generated tokens.
Secondary outcomes are latency, nominal `kL`, truncation, parser validity, and
valid-answer fraction. Comparisons are paired by problem and include
problem-level uncertainty intervals.

`GO JOINT` requires that the joint policy is not dominated by fixed,
depth-only, breadth-only, or heuristic policies and achieves at least one of:

- at least +3 percentage points accuracy at cost within +/-10%; or
- at least 10% fewer actual tokens with accuracy no worse than -2 percentage
  points.

The benefit direction must agree on GSM8K and MATH-500. Use `NEED MORE DATA`
when a learned stage has fewer than 30 positives, accuracy-difference interval
width exceeds 10 percentage points, target agreement is below 0.70, or parser
issues exceed 2%.

Use `PIVOT DEPTH-FIRST` when breadth/joint policies are consistently dominated
or breadth is rarely selected without positive net utility. A rigorous
negative result remains a valid thesis outcome. Abandon the learned-controller
centerpiece only after at least 300 usable two-dataset development problems,
two-seed confirmation, and elimination of data/parser defects.

## 10. Immediate Authorized Run

The next authorized run is the 30-problem GSM8K Train-prefix pilot:

```powershell
python -m adaptive_compute.cli.run_grid `
  --phase2-split-manifest data/splits/phase2_gsm8k_split_v1.json `
  --phase2-partition train --phase2-limit 30 --num-problems 30 `
  --k-values 1 2 4 --l-values 512 1024 2048 --seed 42 `
  --experiment-id qwen3_0_6b_gsm8k_train_pilot_n30_v2 `
  --results-dir results --validate-only
```

Remove `--validate-only` only after verifying the printed model revision,
partition, cap grid, and expected generation count. Use `--resume` to continue
an interrupted run; never start a second experiment ID for the same pilot.
