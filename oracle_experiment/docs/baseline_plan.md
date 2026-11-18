# Baseline Plan

Audit date: 2026-11-11

## Baseline-First Decision

Yes. Implement and validate the depth-only, breadth-only, and heuristic
policies before the joint controller. Fixed profiles and retrospective oracles
already exist, but the three deployable comparators do not exist for the
intended Qwen3-0.6B track.

## Fairness Contract

All policies must use:

- the same pinned model revision, prompts, parser and generation settings;
- the same frozen problem partitions and nested sample pool;
- only signals available at the moment of each decision;
- the same dataset-specific action space;
- identical valid-only aggregation and tie breaking;
- complete charging of all generated samples, including failed or discarded
  trajectories;
- thresholds selected on Train/Validation only;
- per-dataset results and the same paired evaluation code.

Do not compare the joint policy only with the most expensive fixed profile.
The primary comparator is learned depth-only at matched actual tokens.

## B0. Fixed Profiles

**Definition:** apply the same `(k,L)` to every problem. Report every relevant
profile and the best fixed accuracy at or below each realized-token budget.

**Inputs:** none beyond the problem and fixed configuration.  
**Output:** answer, actual tokens, latency, truncation and validity.  
**Status:** evaluation code exists; regenerate 0.6B outcomes.  
**Role:** lower-complexity anchor and source for compute matching.

## B1. Depth-Only Learned Controller

**Policy:**

```text
input-only features -> choose L
k is fixed at 1
generate one trajectory -> return parsed answer
```

**Features:** only the existing input feature allowlist.  
**Target:** initial-cap marginal utility under the frozen lambda grid.  
**Learner:** standardized regularized logistic regression or ordinal/pairwise
logistic decisions.  
**Action space:** dataset-specific cap set frozen by protocol.  
**Selection:** maximize Validation policy accuracy, then minimize actual tokens
under the pre-registered non-inferiority/matched-cost rule.  
**Fairness:** no validity, truncation or agreement signals, because they occur
after the single depth choice.  
**Status:** historical 1.7B version exists; 0.6B version must be rebuilt.

## B2. Breadth-Only Learned Controller

**Policy:**

```text
fixed dataset-specific L
generate sample 1
state_1 -> stop or acquire sample 2
state_2 -> stop or acquire samples 3-4
valid-only vote over acquired samples
```

`L` is fixed for every problem and selected on Validation before final Test.
The policy adapts only `k`, which isolates breadth utility.

**Stage-1 features:** input features plus sample-1 tokens, utilization,
truncation, finish reason and answer validity. Agreement is forbidden at
`k=1`.  
**Stage-2 features:** the above plus two-sample agreement, valid-answer fraction
and cumulative paid cost.  
**Target:** marginal utility of the next breadth action.  
**Learner:** one regularized logistic model per stage if the 30-positive floor
is met; otherwise a frozen heuristic for that stage.  
**Required comparison:** an agreement-stopping variant that always reaches
`k=2` and stops on two matching valid answers, otherwise reaches `k=4`.

## B3. Pre-Registered Heuristic Adaptive Policy

This policy provides a low-data, interpretable comparator and fallback.

### Initial cap rule

Compute prompt-token-length tertiles on Train only. Map short, medium and long
prompts to the ordered low, middle and high caps in the frozen dataset-specific
action space. If only two caps are retained, use the Train median.

### Breadth rules

1. After sample 1, stop only if the response has a valid final answer and did
   not terminate by the token cap; otherwise acquire sample 2.
2. After sample 2, stop if there are two matching valid normalized answers.
3. Otherwise acquire samples 3--4 and apply valid-only majority vote.

The rule uses no correctness signal and no threshold fitted to Test. Report a
second `k=1` input-only heuristic if needed for compute matching, but do not
post-hoc change rules after Validation.

## B4. Joint Sequential Controller (Method, Not Baseline)

The joint policy uses the same stage learners as B2 but also selects initial
`L`. It may begin only after B1--B3 are operational. Its incremental value is
the improvement over both B1 and B2 under matched actual tokens.

## B5. Retrospective Oracles

Report fixed, depth-only, breadth-only and joint oracle frontiers using ground
truth after inference. They are upper bounds and never deployable baselines.
Oracle accuracy must not be compared as if it were controller accuracy.

## Required Artifacts Per Policy

- serialized policy/configuration;
- feature schema and forbidden-field list;
- per-problem action trace;
- paid sample IDs, actual tokens and latency;
- final answer and validity;
- aggregate accuracy/cost table;
- paired difference and Pareto report;
- manifest hashes and model/parser versions.

## Done Criteria

Baseline phase is complete when:

1. B0--B3 run end-to-end on expanded Validation;
2. replayed actions reconstruct exactly the charged sample pool;
3. no forbidden signal appears in feature schemas or traces;
4. all policy tests pass;
5. accuracy, actual tokens, latency, validity and truncation are reported;
6. the depth-only frontier is available as the primary joint-policy comparator.

## What Not to Add

- RL or policy gradients;
- process reward models or external verifiers;
- neural controllers;
- a flat nine-class profile classifier as the primary method;
- boosted trees before the positive-event floor is met;
- Test-dependent threshold tuning.
