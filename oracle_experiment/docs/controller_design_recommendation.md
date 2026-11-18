# Controller Design Recommendation

Status: proposed method after research audit. No new controller has been implemented by this audit.

## Primary recommendation

Use a **hierarchical, budget-constrained marginal-utility controller** with a depth-first execution order:

```text
input features
    -> choose initial L in {1024, 2048}
    -> generate sample 1 and parse it
    -> estimate value of one additional sample
       -> stop at k=1 or generate sample 2
    -> if sample 2 was generated, estimate value of two additional samples
       -> stop at k=2 or generate samples 3–4
    -> valid-only majority vote over paid-for samples
```

Keep `L=512` as a diagnostic and action-space ablation unless new data reverse the current 85–88% truncation and zero cheapest-correct observations. The thesis terminology remains unchanged: `L` is a `max_new_tokens` cap, not semantic reasoning depth.

This controller is not claimed to be a novel idea by architecture alone. Its defensible scientific role is to test whether inexpensive, black-box, sequential signals can coordinate token caps and conditional resampling for small reasoning models under whole-policy cost accounting.

## Why this design

The completed GSM8K/Qwen3 evidence supports, but does not prove, the design order:

- all six planned depth comparisons were significant after Holm correction;
- at equal nominal budget, `1x2048` was more accurate and used fewer actual generated tokens than `2x1024` and `4x512`;
- `L=512` truncated approximately 85–88% of samples;
- 70 of 83 solved problems had a cheapest-correct `k=1` profile, while 13 required `k>1`;
- the joint oracle nevertheless retained approximately 13.13 percentage points of compute-matched headroom over the depth-only oracle.

The evidence therefore justifies preserving breadth as a conditional action rather than discarding it. It does not justify calling depth-first a universal principle.

## Comparison of formulations

Scores are qualitative for this thesis: 1 is poor/high-risk and 5 is strong/low-risk.

| Design | Scientific value | Complexity | Data efficiency | Interpretability | Risk | Fit to evidence | Verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| A. Flat 9-class profile classifier | 2 | 2 | 1 | 3 | 1 | 1 | Reject as primary. Empty/tiny classes and hindsight labels make it unstable and misaligned with sequential deployment. |
| B. Hierarchical `x -> L`, then `state -> k` | 4 | 4 | 4 | 5 | 4 | 5 | Strong structural backbone. It matches what information is available at each decision. |
| C. Fully online stop/more-depth/more-breadth policy | 5 | 2 | 2 | 3 | 2 | 3 | Too ambitious as primary because increasing depth after a hard cap may require continuation semantics or regeneration that are not yet validated. |
| D. Two-stage difficulty and uncertainty buckets | 3 | 5 | 4 | 5 | 4 | 4 | Good heuristic baseline, but “difficulty” is not directly observed and bucket labels can be arbitrary. |
| E. Budget-constrained utility prediction over profiles | 5 | 3 | 3 | 4 | 3 | 5 | Use its objective/targets inside B rather than deploy it as a flat profile selector. |

The recommendation combines **B’s staged policy** with **E’s cost-sensitive objective**. It is more scientifically aligned than a nine-class classifier and more feasible than a general reinforcement-learning policy.

## Decision targets

### Do not use cheapest-correct profile as the sole target

Option A is deterministic after observing outcomes, but it has three problems:

1. It treats all incorrect profiles alike and ignores how much accuracy is bought by extra cost.
2. It converts stochastic one-repetition outcomes into brittle categorical labels.
3. Current labels are severely imbalanced: only 13 of 83 solved problems require `k>1`, and `L=512` has no cheapest-correct examples.

### Recommended target

For an action `a` from state `s`, define a validation utility at trade-off value `lambda`:

```text
U_lambda(a | s) = Pr(correct after a | s) - lambda * E[additional actual tokens | s,a]
```

Train two kinds of small predictors:

1. **Initial-depth preference:** pairwise preference between `L=1024` and `L=2048`, or expected utility for each depth, using input-only features.
2. **Breadth marginal utility:** whether the next escalation has positive net utility, using only signals that the deployed policy has already paid to observe.

For a training record where paired outcomes are available, the ideal action label at a fixed `lambda` is:

```text
argmax_a [correct(a) - lambda * actual_tokens(a)]
```

or, for a binary escalation:

```text
escalate = 1 if Delta_correct - lambda * Delta_actual_tokens > 0
```

Because a single stochastic realization makes `Delta_correct` noisy, train/evaluate at several pre-registered `lambda` values to trace a Pareto curve and use repeated seeds on at least the validation/test subset. Do not select `lambda` on the final test set.

This recommendation uses the logic of Options B, C, D and E: utility-aligned pairwise decisions that deploy as explicit next actions. It avoids training a large policy or claiming that a binary label is a calibrated probability of correctness.

## Model class

- **Primary:** regularized logistic regression for each decision. It is auditable, stable with a few hundred records, and produces coefficients/probabilities that can be calibrated.
- **Secondary ablation:** shallow gradient-boosted trees with tightly limited depth and nested cross-validation.
- **Heuristic baseline:** pre-registered rules using prompt length, first-sample validity/truncation, and answer agreement.
- **Not justified:** neural controller, RL, PRM, or end-to-end fine-tuning.

Do not call XGBoost “better” unless repeated validation shows a stable Pareto improvement. With 100 examples and rare breadth-positive labels, tree ensembles can memorize small partitions.

## Feature contract

### Available before generation

- prompt/model-token count;
- sentence count and word count;
- number/count pattern features;
- arithmetic operator indicators;
- fractions, percentages and units;
- shallow lexical/task-format features.

### Available after paid inference

- actual generated-token count and cap utilization;
- finish reason and explicit truncation state;
- valid final-answer presence and format validity;
- answer value/normalized form, but never correctness;
- agreement and valid-answer fraction after at least two samples;
- elapsed generation time as a logged metric, not necessarily a portable predictor.

### Forbidden at test time

- ground truth or correctness;
- oracle profile/utility labels;
- any trajectory not generated by the deployed policy;
- aggregate information computed from unseen test outcomes;
- dataset identity if the stated goal is cross-dataset generalization, except in an explicitly reported dataset-specific ablation.

## Breadth stages

At `k=1`, agreement is undefined and must not be encoded as perfect confidence. The first breadth decision should use validity, truncation/cap utilization, output length and input features.

At `k=2`, use normalized-answer agreement:

- two matching valid answers is evidence supporting stop;
- disagreement is evidence for escalation but not proof that more samples will help;
- invalid outputs must not vote;
- the policy pays for every generated trajectory even if parsing fails.

The `k=2 -> 4` learner may require a separate target because the marginal return distribution differs from `k=1 -> 2`. Do not pool them unless an explicit stage feature and validation support it.

## Treatment of “Depth First, Breadth Selectively”

Safest wording:

> On the Qwen3-1.7B/GSM8K characterization, sufficient token allowance dominated additional samples under the tested equal nominal budgets. We therefore evaluate depth-first, selective-breadth allocation as a pre-registered hypothesis and design prior, not as a universal law of test-time reasoning.

Use “empirical observation” for the completed grid, “hypothesis” for cross-dataset/model testing, and “proposed heuristic” for the controller order. Do not call it an established design principle until replicated.

## Evaluation contract

For every policy report:

- final-answer accuracy;
- actual generated tokens, including exploratory/intermediate trajectories;
- wall-clock latency and hardware/batching conditions;
- nominal `kL` separately from realized cost;
- valid-answer and truncation rates;
- paired confidence intervals against depth-only and breadth-only baselines;
- a Pareto plot rather than one cherry-picked operating point.

The policy succeeds only if it improves the held-out accuracy–actual-token frontier. Matching an oracle label or achieving high profile-classification accuracy is not the thesis endpoint.

## Implementation gate

Do not extend the current controller implementation yet. First freeze:

1. two-dataset sampling and parser protocol;
2. main action space and the status of `L=512`;
3. `lambda` values/non-inferiority margin;
4. feature availability contract;
5. exact baselines;
6. validation go/pivot thresholds;
7. final-test access rule.

After approval, implement the simplest logistic/heuristic version first. A tree ablation comes only after sufficient minority events exist.
