# Recommended Thesis Scope

> Historical recommendation written before the observed 8192-token latency on
> the available RTX 4060. The compute-driven model change is versioned in
> `MODEL_MIGRATION_QWEN3_0_6B.md`; completed 1.7B evidence remains valid only
> for its original model-specific claims.

Status: research-audit recommendation, not an implemented protocol. This document does not invalidate the completed GSM8K/Qwen3-1.7B evidence. It identifies the smallest defensible extension before joint-controller implementation continues.

## Recommendation in one sentence

Implement **Version 2, constrained**: use Qwen3-1.7B as the primary development model, GSM8K plus a stratified MATH/MATH-500 subset as the two required datasets, a lightweight sequential controller and strong single-axis baselines, then perform a reduced external validation with one different small model if hardware permits.

## Evidence status

- **Completed evidence:** a 3 x 3 `(k,L)` grid on 99 usable GSM8K problems with Qwen3-1.7B and one stochastic repetition; oracle analysis; a frozen GSM8K Phase-2 split; and a development-only depth logistic baseline.
- **Working hypotheses:** per-query allocation is useful; sufficient `L` should usually precede extra samples in this specific regime; a minority of problems benefits from `k>1`.
- **Proposed methods:** two-dataset characterization, hierarchical marginal-utility controller, multi-seed validation, and secondary-model external validation.
- **Future evaluation:** no held-out controller result exists yet. The frozen 100-problem GSM8K test set must remain unopened until the revised protocol and policy are locked.

## Is one dataset and one model enough?

No, not for the thesis claim as currently worded.

- It is enough for a proof of concept and for a careful model–dataset case study.
- It is borderline for a basic undergraduate thesis if all claims are explicitly restricted to Qwen3-1.7B on GSM8K.
- It is not enough for a strong thesis or workshop-style claim about “small reasoning models” or adaptive reasoning generally.

The principal threats are lexical and format shortcuts, GSM8K-specific truncation behavior, model-specific oracle labels, and a failure to demonstrate that controller signals survive a change in problem distribution. A single additional dataset addresses the largest immediate weakness. A secondary model is valuable but should be smaller in scope than the primary study.

## Minimum recommended dataset set

| Dataset | Role | Reasoning and format | Difficulty | Transfer value | Preprocessing and evaluation | Expected compute | Access/licensing caution |
|---|---|---|---|---|---|---|---|
| GSM8K | Primary in-domain dataset | Grade-school arithmetic word problems; numeric exact answer | Easy-to-medium for reasoning models | Preserves all completed evidence and supports controlled continuation | Existing strict numeric parser; low complexity | Known from the completed run | Verify the redistributed dataset card/license in the exact source used; preserve source hashes |
| MATH-500 or a frozen stratified 500-problem subset of MATH | Required distribution shift | Competition mathematics across subjects; symbolic/numeric boxed answers | Materially harder and more varied | Tests whether allocation signals transfer beyond short arithmetic word problems | Medium complexity: normalize fractions, radicals, sets, intervals and symbolic forms; manual audit needed | Higher tokens per problem; start with 100–150 characterization items | MATH paper and official repository are public; record exact subset source and license |

The required minimum is therefore **GSM8K + MATH-500/stratified MATH**. This is intentionally two datasets, not a broad benchmark suite.

### Nice-to-have datasets

| Dataset | Value | Why it is not required |
|---|---|---|
| SVAMP | Low-cost arithmetic distribution shift built from controlled variations; numeric answers are easy to score | It remains close to GSM8K and may add less scientific diversity than MATH. Use it as a cheap transfer sanity check if time remains. |
| ARC-Challenge | Multiple-choice grade-school science; simple exact letter scoring; tests a non-math format | Knowledge and retrieval limitations confound reasoning compute, so a failure is difficult to interpret. Add only after the math study is complete. |

Do not add StrategyQA or GPQA in the minimum scope. StrategyQA introduces evidence/retrieval and disputed annotation issues; GPQA is difficult, knowledge-heavy, and likely too expensive for stable small-model controller labels. AQuA-RAT is possible but overlaps mathematical word reasoning while adding multiple-choice artifacts. ASDiv is useful but less complementary than MATH.

Sources: [MATH dataset paper](https://datasets-benchmarks-proceedings.neurips.cc/paper/2021/hash/be83ab3ecd0db773eb2dc1b0a17836a1-Abstract-round2.html), [SVAMP paper](https://aclanthology.org/2021.naacl-main.168/), [ARC paper](https://arxiv.org/abs/1803.05457), [StrategyQA paper](https://aclanthology.org/2021.tacl-1.21/).

## Minimum recommended model plan

### Primary model

Continue with **Qwen3-1.7B**. It is the only responsible primary choice because the completed oracle grid, parser behavior, latency measurements, and development splits already use it. The official model card identifies 1.7B parameters, a 32,768-token context, thinking/non-thinking modes, and Apache-2.0 licensing: [Qwen3-1.7B model card](https://huggingface.co/Qwen/Qwen3-1.7B).

### Secondary validation model

Prefer **Phi-4-mini-reasoning (3.8B)** if it fits the available GPU. It is a different model family, explicitly reasoning-oriented, MIT licensed, and still in a realistic small-model range: [official model card](https://huggingface.co/microsoft/Phi-4-mini-reasoning).

If 3.8B is operationally infeasible, use **DeepSeek-R1-Distill-Qwen-1.5B** only as a compute-compatible backup. It is MIT licensed, but because it is derived from Qwen2.5, it provides weaker evidence of model-family transfer: [official model card](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B).

### Controller sharing

- **Primary thesis result:** a model-specific controller for Qwen3-1.7B. Oracle labels are model-, prompt-, decoding-, and parser-dependent.
- **Secondary model result:** reduced external validation of the frozen policy features/heuristic and, if enough calibration data exist, a separately calibrated lightweight controller using the same design.
- **Exploratory only:** zero-shot transfer of the Qwen controller to the second model.
- **Do not make a universal cross-model controller the thesis requirement.** That would need substantially more models and training data.

## Data scale

The current 99 usable oracle-labelled problems are insufficient for the joint task. Only 13 solved problems select `k>1`, and no problem selects `L=512` as cheapest-correct. A nine-class classifier would therefore learn from empty and tiny classes, while a 20-problem validation set gives unstable policy selection.

Recommended scale for the primary model:

- **Minimum:** 300 oracle-characterized development problems total, with at least 100 from the second dataset.
- **Preferred:** 400–500 development problems if the observed breadth-positive rate remains near 10–20%.
- **Frozen final tests:** retain the existing 100 new GSM8K test problems and add 75–100 untouched MATH problems. Do not consume final-test outcomes for feature selection.
- **Class-event floor:** at least 30 positive escalation events for each learned binary decision. If this is not achieved, keep that decision heuristic or merge action levels rather than fitting an unstable classifier.

Three hundred is reasonable for regularized logistic regression and shallow/boosted-tree ablations with a small feature set. It is not enough for a neural controller or reinforcement learning. Those methods are outside scope.

## Compute containment

The original full grid uses 12 generated trajectories per problem (`3 L` values x `max(k)=4`, with nested sample reuse). Scaling it blindly is expensive. Apply these constraints transparently:

1. Keep `L=512` in a small diagnostic/ablation because current evidence shows 85–88% truncation and zero cheapest-correct selections.
2. For the main controller, pre-register an evidence-based action space `{L=1024, 2048} x {k=1,2,4}` only after reporting the pruning rule. This is a methodological revision, not a silent redefinition.
3. Use sequential caching so every generated trajectory is reusable across baselines.
4. Run one small pilot on each new dataset/model before committing the full pool.
5. Measure wall-clock latency independently from token count; hardware contention and batching can break their correlation.

## Exact baseline set

The final evaluation must include:

1. Fixed profiles, with all relevant `(k,L)` anchors reported.
2. Best fixed policy under each evaluated average-token budget.
3. Compute-matched fixed heuristic (for example, prompt-length depth buckets with fixed `k=1`).
4. Depth-only learned controller.
5. Breadth-only agreement-stopping controller, implementing an Adaptive-Consistency-style baseline.
6. Simple depth-first heuristic.
7. Proposed joint sequential controller.
8. Retrospective fixed, depth-only, breadth-only and joint oracles, clearly labelled upper bounds.

The joint policy’s primary comparator is the depth-only controller at matched actual generated tokens—not the most expensive fixed profile.

## Version assessment

| Version | Academic depth | Engineering depth | Risk | Compute/time | Defensibility |
|---|---|---|---|---|---|
| V1: 1 model, 1 dataset, oracle plus one controller | Medium-low | Medium | Low operational, high claim risk | Lowest; roughly 4–7 additional weeks | Proof of concept or tightly framed case study; too narrow for broad claims |
| V2: 2 datasets, primary model plus reduced secondary validation, controller and strong baselines | High for undergraduate scope | High | Moderate | Moderate-high; fits 12–14 weeks with staged runs | Recommended; supports both research and IT/CS system contributions |
| V3: many datasets/models plus LangGraph, RAG, RL, PRM, multi-agent and deployment stack | Superficially broad but unfocused | Very high | Very high | Incompatible with 12–14 weeks | Not defensible if core experiments remain incomplete |

## Twelve-to-fourteen-week execution envelope

| Weeks | Outcome |
|---|---|
| 1–2 | Freeze revised RQs, datasets, action-space rule, metrics, success thresholds and paper outline. Implement only dataset/model adapter prerequisites after approval. |
| 3–4 | Audit parsers and run small Qwen3 pilots on MATH; estimate class balance and GPU hours. |
| 5–7 | Generate the primary development pool with checkpoint/resume; train depth, breadth and joint policies without touching final tests. |
| 8–9 | Validation, ablations, repeated-generation subset and go/pivot decision. Freeze controller. |
| 10–11 | One-shot final in-domain and cross-dataset tests; reduced Phi external validation if feasible. |
| 12–14 | Statistical analysis, reproducibility package, figures, thesis/paper writing and demonstration. |

## Final software system

```text
Dataset/API adapter
        |
Normalized problem + answer contract
        |
Input feature extractor
        |
Adaptive compute controller
  initial L -> sample 1 -> stop/escalate -> optional k=4
        |
Model adapter / inference executor
        |
Valid-answer parser and aggregator
        |
Trace logger + checkpoint/cache + token/latency accounting
        |
Evaluation runner -> statistical reports and figures
```

Required engineering artifacts are dataset adapters, model adapters, a deterministic controller interface, orchestration, checkpoint/resume, cache identity, cost accounting, evaluation tests, and reproducible reports. A small CLI or read-only demo is optional after the scientific pipeline is complete. RAG, multi-agent execution, and a deployment platform are not needed.

## LangGraph decision

**DO NOT USE.** The controller is a small deterministic state machine. Plain Python functions/classes make transitions, costs, seeds and cached trajectories easier to test and reproduce. LangGraph would add a dependency and orchestration vocabulary without adding research value. Reconsider only if a later product demo truly needs long-lived asynchronous workflows; even then, it must remain infrastructure, not a contribution.

## Scope decision

Freeze the current prototype and revise the research protocol first. Controller implementation should resume only after the supervisor accepts the narrowed gap, the two-dataset minimum, the model plan, the marginal-utility target, and the go/pivot rules.
