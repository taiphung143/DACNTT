# Recommended Paper Scope

Status: recommendation for the current Qwen3-0.6B development track. Historical Qwen3-1.7B evidence remains separate and is not relabelled or pooled.  
Time constraint: 12-14 week undergraduate thesis.  
Primary verdict: **MODIFY CONTROLLER DESIGN, THEN IMPLEMENT.**

## 1. Final Research Questions

The revised RQs already approved by the project audit remain appropriate. The reference-paper comparison and updated literature check do not justify redefining them.

### Main RQ

> For small open-weight reasoning models, can a verifier-free lightweight sequential policy that allocates generation-token caps and selectively adds independent samples improve the held-out accuracy-actual-generated-token Pareto frontier over fixed profiles and depth-only or breadth-only adaptive baselines?

### RQ2

> Under matched actual generated-token budgets, when does selective breadth provide statistically reliable utility beyond adaptive depth, and which observable input or early-inference signals predict that utility?

### RQ3

> How stable are the controller's gains, decisions and cost estimates across GSM8K and a harder mathematical reasoning dataset, and to what extent do the findings transfer to a second small-model family?

RQ3 has two levels: cross-dataset evidence is required; cross-model evidence is reduced and secondary. `L` remains `max_new_tokens`, an operational cap rather than semantic reasoning depth.

## 2. Method recommendation

Frame the method as a **verifier-free sequential adaptive inference framework**, not as a profile classifier.

```text
problem x
  -> input features
  -> choose initial token cap L
  -> generate sample 1
  -> observe paid state: length, utilization, truncation, parse validity
  -> stop or acquire sample 2
  -> observe agreement and valid-answer fraction
  -> stop or acquire samples 3-4
  -> valid-only majority aggregation
  -> log all tokens, latency, actions, and outcomes
```

The policy should optimize or approximate marginal utility:

```text
Delta utility = Delta correctness - lambda * Delta actual generated tokens
```

Correctness and oracle actions are training labels only. They are forbidden test-time signals.

## 3. Controller formulation decision

| Formulation | Scientific value | Data/implementation risk | Decision |
|---|---|---|---|
| A. Flat `x -> (k,L)` classifier | low under current class imbalance; ignores acquired state | low code effort, high validity risk | reject as primary; keep only as ablation |
| B. Depth-first hierarchical controller | aligns with observed action sequence and available signals | manageable | **primary design** |
| C. Marginal-utility controller | strongest objective alignment | requires careful labels and lambda sensitivity | use as the training target inside B |
| D. Rule-based adaptive inference | interpretable and low-data | may underfit | required heuristic baseline/fallback |
| E. Generic sequential stop/escalate policy | valid abstraction | can become over-general | use only through the concrete stages in B |

Primary learner: regularized logistic regression per decision stage.  
Secondary ablation: shallow gradient-boosted trees only after each learned escalation has at least 30 positive Train events.  
Do not introduce RL, a process reward model, neural routing, or end-to-end fine-tuning.

## 4. Dataset scope

### Minimum viable suite: two datasets

| Dataset | Reasoning type | Inclusion reason | Parsing difficulty | Expected compute | Overlap with GSM8K | Cross-dataset value |
|---|---|---|---|---|---|---|
| GSM8K | grade-school arithmetic word problems | preserves historical characterization, frozen IDs, and existing parser | low; strict numeric answer | moderate | primary source domain | in-domain policy development and frozen test |
| MATH-500 | competition mathematics across subjects and difficulty levels | tests harder symbolic/numeric reasoning and longer trajectories | medium-high; fractions, radicals, sets, symbolic forms | high; current 0.6B pilot averages 985-2,804 tokens at caps 1024-4096 | complementary rather than redundant | required distribution shift and action-space stress test |

Minimum data target remains at least 300 usable development problems across the two datasets, including at least 100 from MATH-500 and at least 30 positive examples for every learned escalation decision.

The completed 30-problem MATH-500 run is a development pilot, not the required final second-dataset sample.

### Strong but feasible suite: three datasets

Add **SVAMP** only after the two-dataset controller evaluation is operational.

| Dataset | Reasoning type | Reason for optional inclusion | Parsing | Compute | Value |
|---|---|---|---|---|---|
| SVAMP | controlled arithmetic word-problem variations | low-cost check that the controller is not tied to GSM8K wording/templates | easy numeric exact match | lower than MATH | useful transfer sanity check, but less diverse than MATH |

Do not add ARC-Challenge, StrategyQA, GPQA, RAG tasks, or code benchmarks in the minimum paper. They introduce knowledge, retrieval, scoring, or compute confounds that do not directly answer the RQs.

## 5. Model scope

### Primary development model

Use `Qwen/Qwen3-0.6B` at the pinned revision already recorded in the migration amendment. It is the current feasible model, and all new controller labels must be generated for it.

### Historical robustness stratum

Keep Qwen3-1.7B GSM8K and MATH results as historical model-specific characterization. They show that several depth/truncation patterns recur within the Qwen3 family, but they do not validate a 0.6B controller and must not be pooled.

### Secondary model

One model is enough to develop and test a model-specific controller, but not enough for unrestricted plural claims about small reasoning models.

Preferred paper plan:

- core success requirement: Qwen3-0.6B on GSM8K and MATH-500;
- reduced secondary validation: one different small-model family on a small frozen subset and a reduced action space, only after the core result is complete;
- if hardware makes this infeasible, omit the cross-family claim, retain the 1.7B historical stratum, and state that the controller is Qwen3-specific.

A universal or model-agnostic learned controller is outside scope. Fit one controller per model if secondary calibration is attempted.

## 6. Baselines

The final evaluation must include:

1. all relevant fixed `(k,L)` profiles;
2. best fixed policy at or below each evaluated actual-token budget;
3. compute-matched prompt/input heuristic;
4. learned depth-only controller;
5. Adaptive-Consistency-style breadth-only stopping;
6. simple depth-first heuristic;
7. learned sequential joint controller;
8. retrospective fixed, depth-only, breadth-only, and joint oracles, labelled as upper bounds.

The primary comparator is depth-only at matched actual generated tokens. Comparing only with the most expensive fixed profile would be scientifically inadequate.

## 7. Evaluation contract

Report every policy by dataset and operating point:

- final-answer accuracy;
- all actual generated tokens paid by the policy;
- wall-clock latency with hardware and batching conditions;
- nominal `kL` separately from realized cost;
- truncation rate, parse-validity rate, and valid-answer fraction;
- policy action frequencies and stage-specific escalation precision/recall;
- paired 95% intervals for accuracy and token differences;
- Pareto frontier rather than one selected point.

Use exact McNemar for named paired accuracy comparisons and paired bootstrap intervals for policy accuracy/cost differences. Keep problem-sampling and generation-seed uncertainty separate. Inconclusive results are not equivalence.

## 8. System contribution

The system layer is scientifically justified because it executes and audits the policy:

- dataset adapters and normalized answer contracts;
- input and paid-state feature extraction;
- serialized controller and explicit state machine;
- model adapter and inference executor;
- stop/escalation and budget accounting;
- strict parser and valid-only aggregator;
- append-only traces, cache, checkpoint/resume, and provenance manifests;
- policy replay/evaluation and paired statistics.

This architecture makes the project more defensible without artificial scope inflation. A GUI, web service, RAG module, multi-agent framework, or LangGraph pipeline is optional and not recommended before the experiments are complete.

## 9. Required ablations

Minimum ablations:

1. input-only features versus input + paid early-inference signals;
2. hierarchical sequential controller versus flat profile classifier;
3. depth-only versus breadth-only versus joint policy under matched actual tokens;
4. heuristic versus logistic policy;
5. threshold or `lambda` sensitivity at pre-registered values;
6. one-seed labels versus repeated-seed stability on a bounded validation/test subset;
7. MATH action-space sensitivity, especially the role of `L=4096`.

Optional ablations:

- logistic regression versus shallow boosted trees;
- dataset-specific versus pooled controller;
- leave-one-feature-group-out analysis;
- reduced cross-model calibration.

## 10. Success criteria

Proceed with the joint method on expanded Validation only if there are at least 30 positive Train events for the relevant escalation stage and the joint policy either:

- improves accuracy over depth-only by at least 3 percentage points at actual-token cost within +/-10%; or
- reduces actual generated tokens by at least 10% while the paired accuracy difference satisfies the frozen -2 percentage-point non-inferiority rule.

The joint policy must not be Pareto-dominated by the breadth-only or simple heuristic baseline. The benefit should have the same sign on both required datasets, even if one interval is inconclusive.

## 11. Fallback result

If joint allocation is dominated or breadth-positive events remain too rare:

1. pivot to adaptive depth as the primary deployable method;
2. report the joint oracle as opportunity, not achieved performance;
3. analyze why oracle breadth headroom was not learnable from permitted signals;
4. retain selective breadth as a heuristic or future-work direction;
5. present the negative result with the same held-out and cost-accounting rigor.

This fallback remains a defensible thesis because it answers the RQ negatively and separates hindsight headroom from deployable learnability.

## 12. Contribution assessment

| Contribution | Status now | Required final evidence |
|---|---|---|
| C1. Breadth-token-cap characterization | completed historical evidence | model-separated replication/context |
| C2. Nominal and realized compute differ | completed historical evidence | retain cost-matched analysis |
| C3. Lightweight joint allocation method | proposed | implementation and frozen held-out result |
| C4. Strong baseline comparison | partial/planned | depth, breadth, heuristic, joint, oracles |
| C5. Generalization | preliminary MATH depth evidence only | two-dataset controller evaluation; reduced second model optional |

With C1-C4 completed on two datasets, the stack is **adequate to strong**. Adding reduced C5 makes it **strong**. Requiring full multi-model training would be **over-scoped**.

## 13. Recommended final paper story

1. **Problem:** fixed test-time compute either wastes tokens or truncates useful reasoning.
2. **Observation:** breadth and token caps are not interchangeable under equal nominal budgets.
3. **Opportunity:** different problems prefer different actions and a joint oracle exposes headroom.
4. **Risk:** hindsight actions may be rare, noisy, and unlearnable.
5. **Method:** a verifier-free sequential policy first allocates a cap, then selectively acquires additional samples from paid-state signals.
6. **Evaluation:** compare fixed, depth-only, breadth-only, heuristic, joint, and oracle strategies on GSM8K and MATH-500 using actual tokens and latency.
7. **Conclusion:** quantify how much oracle headroom is captured, or show why adaptive depth dominates when breadth utility is not learnable.

This story is stronger than “run grid, train XGBoost, report accuracy” because it makes characterization, learnability, policy execution, and negative outcomes part of one falsifiable study.

## 14. Final verdict

**MODIFY, then implement.**

Do not expand the scope before controller work merely to imitate the reference paper. The current action is to preserve the revised RQs, implement the sequential marginal-utility design, regenerate 0.6B controller data, and complete the two-dataset baseline evaluation. Cross-family validation comes after the core result and may be omitted with appropriately narrow claims.

Recent overlap checks reinforce this bounded positioning: Adaptive-Consistency already covers model-agnostic adaptive breadth; Token-Budget-Aware LLM Reasoning covers adaptive token allocation; Learning How Hard to Think and the 2026 constrained allocation preprint cover input-adaptive compute and cheap-feature oracle imitation. The defensible contribution is the external verifier-free sequential coordination of hard caps and selective resampling under rigorous actual-cost accounting, not the generic idea of adaptive compute.

Primary literature links:

- https://aclanthology.org/2023.emnlp-main.761/
- https://openreview.net/forum?id=6qUUgw9bAZ
- https://aclanthology.org/2025.findings-acl.1274/
- https://arxiv.org/abs/2604.14853
