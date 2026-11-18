# Research Questions and Contribution Revision

Status: recommended revision produced by the literature audit. It preserves the thesis topic and operational terminology (`k` breadth; `L=max_new_tokens` token cap/operational depth) while narrowing claims that current literature no longer supports.

## Research-gap assessment

Original candidate gap:

> Lightweight per-problem joint allocation of sampling breadth and generation-token budget for Small Reasoning Models remains underexplored.

Assessment: **B. Partially true but must be narrowed.**

The generic gap “adaptive per-query test-time compute” is already well covered. Input-adaptive allocation, adaptive self-consistency, adaptive token budgets, hidden-state early stopping and constrained action learning all have direct precedents. In particular, Zhai et al. (2026 preprint) already use a Lagrangian oracle and a lightweight classifier from cheap text features to allocate per-query sample budgets on GSM8K/MATH; Damani et al. (ICLR 2025) learn where marginal computation is valuable; Han et al. (ACL Findings 2025) adapt token budgets; and several peer-reviewed works adapt the number of self-consistency samples.

The remaining defensible space is narrower: external black-box control, small open-weight reasoning models, hard generation caps, sequential use of already-paid-for inference signals, joint rather than single-axis decisions, and whole-system actual-token/latency evaluation.

### Revised gap

> Existing work provides strong evidence for per-query adaptive sampling or adaptive reasoning length, but evidence remains limited on whether a low-overhead, verifier-free external policy can *sequentially coordinate both* generation-token caps and selective resampling for small open-weight reasoning models. This is especially insufficiently characterized under actual generated-token and latency accounting, strong depth-only/adaptive-sampling baselines, and distribution shifts across reasoning datasets. The thesis tests this constrained setting rather than claiming the first adaptive compute allocator.

This wording is a literature-bounded statement, not proof of novelty by absence.

Key sources: [Adaptive-Consistency, EMNLP 2023](https://aclanthology.org/2023.emnlp-main.761/), [Learning How Hard to Think, ICLR 2025](https://openreview.net/forum?id=6qUUgw9bAZ), [Token-Budget-Aware LLM Reasoning, ACL Findings 2025](https://aclanthology.org/2025.findings-acl.1274/), [Difficulty-Adaptive Self-Consistency, NAACL Findings 2025](https://aclanthology.org/2025.findings-naacl.383/), and [Adaptive Test-Time Compute Allocation via Constrained Policy Optimization, arXiv 2026](https://arxiv.org/abs/2604.14853).

## Current RQ assessment

Current RQ:

> Can a lightweight per-problem controller jointly allocate reasoning depth and sampling breadth for a small reasoning model to achieve a better accuracy–compute trade-off than fixed-budget and single-axis adaptive strategies?

| Dimension | Score (1–5) | Assessment |
|---|---:|---|
| Clarity | 4 | The action axes and comparison are understandable, but “reasoning depth” must always be operationalized as `max_new_tokens`, not cognitive depth. |
| Falsifiability | 5 | Held-out accuracy and cost comparisons can disconfirm it. |
| Novelty | 2 | Generic adaptive allocation and cheap-feature action classification are already covered; joint sequential black-box `k+L` is the narrower opportunity. |
| Measurability | 4 | Accuracy and generated tokens are measurable; “better trade-off” needs a pre-registered Pareto/non-inferiority definition. |
| Scope | 3 | Feasible after narrowing; one model/dataset makes the language too broad. |
| Undergraduate feasibility | 4 | Logistic/heuristic policies and two datasets are feasible; RL/PRM is not. |
| Risk | 3 | Breadth-positive events are rare and the joint policy may not beat depth-only. A valid negative result is possible. |
| Independence from one dataset/model | 2 | The existing evidence is entirely Qwen3-1.7B/GSM8K. |
| Meaningful negative result | 5 | A rigorous result that depth-only dominates under this regime remains valuable if baselines and costs are strong. |

The current RQ is scientifically valid in structure but insufficiently specific about observability, model class, cost metric, and generalization. It should be revised before more controller development.

## Recommended final RQ set

### Main RQ

> For small open-weight reasoning models, can a verifier-free lightweight sequential policy that allocates generation-token caps and selectively adds independent samples improve the held-out accuracy–actual-generated-token Pareto frontier over fixed profiles and depth-only or breadth-only adaptive baselines?

### RQ2

> Under matched actual generated-token budgets, when does selective breadth provide statistically reliable utility beyond adaptive depth, and which observable input or early-inference signals predict that utility?

### RQ3

> How stable are the controller’s gains, decisions and cost estimates across GSM8K and a harder mathematical reasoning dataset, and to what extent do the findings transfer to a second small-model family?

These questions are measurable and falsifiable. RQ3 deliberately separates required cross-dataset evidence from reduced/optional cross-model evidence so the thesis remains feasible.

## Hypotheses to pre-register

- **H1:** The joint sequential policy is non-dominated by learned depth-only and breadth-only policies on at least one held-out operating point and is not materially worse on the second dataset.
- **H2:** Conditional breadth improves accuracy for a minority of questions after an adequate token cap, but unconditional breadth is compute-inefficient in the tested small-model regime.
- **H3:** Input-only features explain initial token-cap need better than breadth need; post-generation validity/truncation/agreement signals improve breadth-escalation decisions.

H2 and H3 are working hypotheses, not completed findings.

## What the thesis is and is not claiming

It may claim:

- a controlled empirical characterization of breadth and token-cap interactions for small reasoning models;
- a lightweight black-box sequential controller evaluated against strong single-axis baselines;
- whole-policy cost accounting using actual generated tokens and latency;
- evidence about cross-dataset robustness and limited external model validation;
- a reproducible research software system.

It must not claim:

- the first adaptive test-time compute controller;
- the first difficulty-aware sampler;
- that `max_new_tokens` measures semantic reasoning depth;
- generalization to all small language models from one or two checkpoints;
- that oracle headroom proves a deployable policy will work;
- that depth is universally superior to breadth.

## Contributions if the joint controller succeeds

1. A reproducible breadth–token-cap characterization showing how allocated budget, actual tokens, latency, truncation and accuracy interact in a small-model regime.
2. A verifier-free sequential controller that uses only cheap input and already-paid-for inference signals to coordinate initial `L` and conditional `k`.
3. A fair held-out comparison against fixed, compute-matched, depth-only and adaptive-breadth baselines on two datasets, plus reduced secondary-model validation.
4. Open experiment infrastructure for adapters, caching, checkpoint/resume, policy traces, cost accounting and paired evaluation.

The contribution is the constrained empirical/system result—not merely “we trained a classifier.”

## Contributions if joint does not beat depth-only

1. A rigorous negative result delimiting when joint allocation fails to convert oracle breadth headroom into deployable gains.
2. Evidence that adaptive depth is the dominant controllable axis under the tested small-model, parser and budget regime, together with conditions where breadth remains useful or too rare to learn.
3. A benchmark and evaluation framework that distinguishes oracle opportunity, learnability, actual token cost and latency.
4. A validated depth-first system and objective go/pivot criteria that prevent overclaiming from post-hoc oracle results.

This is a valid thesis if the experimental protocol is frozen in advance and the negative result is reported transparently.

## Candidate thesis titles

1. **Conservative:** *Evaluating Adaptive Test-Time Compute Allocation for Small Reasoning Models*
2. **Research-oriented:** *Depth First, Breadth Selectively? Joint Test-Time Compute Allocation for Small Reasoning Models*
3. **System-oriented:** *A Reproducible Framework for Budget-Aware Inference in Small Reasoning Models*

The question mark in title 2 is intentional: it frames the phrase as an evaluated hypothesis, not a foregone conclusion.

## Final position

The RQ remains viable only in revised form. The thesis should no longer present cheap-feature allocation or adaptive sample count as its novelty. It should test a specifically defined black-box, sequential, joint `k+L` policy and be designed so that a depth-only outcome remains publishable and academically honest.
