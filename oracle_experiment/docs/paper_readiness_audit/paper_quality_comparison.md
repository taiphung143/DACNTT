# Paper Quality Comparison

Audit date: 2026-11-11  
Comparison target: supervisor-provided AQO reference paper versus the current Adaptive Test-Time Compute (TTC) thesis project.

## Executive comparison

The reference paper is broader and more submission-shaped. The current thesis is stronger in experimental controls, cost accounting, statistical discipline, and reproducible engineering, but its central deployable method is not yet implemented or evaluated. The largest gap is therefore not prose. It is missing controller-level evidence across the two required datasets.

## Side-by-side assessment

| Dimension | Reference paper | Current Adaptive TTC thesis | Gap | Recommendation |
|---|---|---|---|---|
| Research question | Implicit hybrid-query question; no explicit RQs (Introduction, pp. 1-2) | Revised Main RQ and RQ2/RQ3 are explicit and falsifiable | TTC is stronger in formulation | Preserve revised RQs; do not revert to generic adaptive-compute wording |
| Research gap | RAG and Text-to-SQL are usually separate (Related Work, pp. 2-4) | Narrowed to verifier-free, external, sequential joint `k+L` control under actual-token accounting | TTC gap is more literature-sensitive | Retain bounded claim and update overlap matrix before submission |
| Method | Prompted LLM orchestrator with tools and retry (Fig. 1, p. 4; Tables 1-3, pp. 5-8) | Proposed hierarchical marginal-utility controller; historical depth baseline exists | Central TTC method remains proposed | Implement simplest sequential logistic/heuristic policy first |
| System | Clear query-agent-tool architecture (Fig. 1, p. 4) | Modular adapters, cache, runner, parsers, controller data, statistics; no single framework figure | TTC engineering exists but is under-presented | Add one architecture figure and policy-state trace |
| Dataset scope | 3 public benchmarks (Sec. 4.1, pp. 9-10) | Completed GSM8K historical grid; 30-problem 0.6B MATH development depth pilot | No two-dataset controller evaluation yet | Minimum final suite: GSM8K + MATH-500 |
| Model scope | 2 Gemini 2.5 variants (Sec. 4.2, p. 10) | 1.7B historical and 0.6B current, same Qwen3 family | No cross-family controller evidence | Keep 0.6B primary; reduced second-family validation is desirable, not allowed to delay core evaluation |
| Experimental scope | RAG, multi-hop QA, Text-to-SQL (Tables 4-8, pp. 11-13) | breadth-depth grid, oracle/cost analysis, depth-only validation, MATH depth pilot | TTC is deep but currently fragmented across model-specific tracks | Regenerate 0.6B GSM8K labels and evaluate one coherent final policy |
| Statistical rigor | No uncertainty or significance testing in the reported results (Sec. 4.2, pp. 10-13) | Wilson intervals, exact McNemar, Holm correction, paired bootstrap design | TTC is stronger | Keep named comparisons and separate problem/seed uncertainty |
| Baselines | Literature baselines plus standalone Gemini on Spider (Tables 5, 7, and 8, pp. 11-13) | fixed/oracles completed; depth-only historical; breadth-only and joint planned | Strong final baseline suite not complete | Implement Adaptive-Consistency-style breadth and simple heuristic before final test |
| Ablations | None reported in Method or Experiments (Secs. 3-4, pp. 4-13) | Parser versions and action-space diagnostics exist; controller ablations planned | Neither has final component ablations | Must ablate input-only vs early-inference signals and sequential vs flat formulation |
| Generalization | Three task types and two model variants; no explicit transfer study (Sec. 4, pp. 9-13) | No controller-level cross-dataset or cross-model result | Reference appears broader | Require two-dataset evaluation; cross-model remains reduced/secondary |
| Efficiency evaluation | Mentions latency but reports mainly quality metrics (Sec. 4.2, pp. 10-13) | Actual tokens, allocated budget, latency, truncation, caching | TTC is stronger | Make actual tokens primary and latency secondary/hardware-conditioned |
| Failure analysis | Brief discussion of difficult Spider subsets (pp. 12-13) | Parser failures, truncation states, oracle learnability, pivot rules | TTC is stronger in readiness | Add final controller false-escalation/missed-escalation cases |
| Reproducibility | Limited configuration and no artifact link visible in Secs. 3-4 (pp. 4-13) | pinned revisions, hashes, manifests, cache identity, 134 passing tests | TTC is materially stronger | Preserve immutable final-policy/config hashes and test-access rule |
| Paper narrative | Complete applied system story with practical examples (Fig. 3, p. 14) | Strong characterization story, incomplete final method story | TTC paper still reads partly as progress report | Recenter final paper on observation -> oracle opportunity -> learnable policy -> held-out result |
| Contribution strength | Broad integration + evaluation + use cases | rigorous characterization + proposed controller + research system | Current completed contribution stops before central method | Paper-ready only after controller and frozen evaluation |

## Critical experimental-depth comparison

| Dimension | Reference paper | Current thesis evidence | Required final state |
|---|---|---|---|
| Datasets | WikiEval, HotpotQA, Spider (Sec. 4.1, pp. 9-10) | GSM8K historical; MATH-500 30-problem 0.6B depth pilot | GSM8K + MATH-500 controller evaluation |
| Models | Gemini 2.5 Flash and Pro (Sec. 4.2, p. 10) | Qwen3-1.7B historical; Qwen3-0.6B current | 0.6B primary; reduced secondary validation if feasible |
| Baseline types | RAG, HotpotQA, and Spider comparison systems (Tables 5, 7, and 8, pp. 11-13) | fixed profiles/oracles and historical depth-only; breadth-only/joint not done | fixed, compute-matched heuristic, depth-only, breadth-only, joint, oracles |
| Major experiments | 3 benchmark blocks (Sec. 4.2, pp. 10-13) | 1 historical full grid, 1 historical depth controller, 1 current depth pilot | oracle characterization plus held-out policy study on 2 datasets |
| Ablation | none | parser/action diagnostics, no joint-controller ablation | feature, controller structure, and threshold sensitivity |
| Statistical tests | none | paired tests and intervals for completed grids | paired policy intervals and pre-specified named tests |
| Sensitivity | model comparison; Spider difficulty breakdown | depth cap and truncation analyses | utility/threshold sensitivity and seed robustness |
| Generalization | task breadth, no explicit transfer | no policy generalization yet | per-dataset results and source-only vs pooled training |
| Efficiency | quality-first; latency promised but not tabled | detailed actual token and latency accounting | full-policy cost including exploratory trajectories |
| Failure analysis | brief | strong retrospective failure taxonomy | policy decision errors and dataset-stratified cases |
| Case studies | 3 practical scenarios | raw generation/demo cases and oracle profiles | 4-6 controller traces illustrating stop/escalate decisions |

## What is already stronger in the TTC work

The following strengths are supported by repository evidence and exceed what is reported in the reference paper:

- paired exact statistical tests with Holm correction;
- Wilson intervals and planned paired bootstrap intervals;
- explicit separation of nominal `kL`, actual generated tokens, and latency;
- retrospective oracle labels clearly marked as hindsight upper bounds;
- frozen Train/Validation/Test manifests and unopened final test policy;
- pinned model/dataset revisions, prompt/parser hashes, deterministic seeds, checkpoint/resume, and generation cache;
- explicit go/pivot criteria and a valid negative-result path;
- 134 passing non-GPU tests as of this audit;
- careful distinction between `max_new_tokens` and semantic reasoning depth.

These strengths should be presented as scientific and engineering rigor, not as evidence that the controller already works.

## What is currently weaker

### Critical

1. The sequential joint controller has not been implemented or evaluated.
2. The current 0.6B track lacks a complete GSM8K characterization and model-specific controller labels.
3. No held-out joint-versus-depth-only comparison exists.
4. No controller-level cross-dataset evidence exists.

### Important

1. The paper mixes historical 1.7B evidence and current 0.6B development; the final story must keep them in separate strata.
2. The 30-problem MATH pilot is useful for action-space selection but too small for final claims.
3. Breadth-only and simple heuristic baselines are specified but not yet implemented.
4. Generation-seed variability remains unmeasured.
5. The current paper has no single system architecture or controller-state figure.

### Nice-to-have

1. Reduced validation on a second model family.
2. A small read-only demo or CLI trace viewer.
3. A third low-cost dataset such as SVAMP.

## One-dataset and one-model risk

If the final paper uses only Qwen3 on GSM8K with one trained controller, the classification is:

**D. Insufficient relative to the reference paper's research-quality bar.**

It would still be an acceptable proof of concept (**C** in absolute scope terms) if the title and claims were restricted to one Qwen3/GSM8K case study. It would not support claims about small reasoning models, cross-dataset robustness, or a general adaptive inference framework. The main risks are lexical shortcuts, format-specific parsing, Qwen-specific truncation, and unstable one-seed oracle targets.

The minimum defensible increase is one complementary dataset, not a large benchmark suite. GSM8K plus MATH-500 directly tests the RQ while remaining feasible.

## Is the planned controller technically sufficient?

### Flat feature-to-profile classifier

`features -> XGBoost -> one of nine profiles` is technically too weak as the primary method. The current labels contain empty/tiny classes, correctness is only known retrospectively, and a flat decision cannot use signals acquired after the first paid sample. A high profile-classification score could also hide poor policy utility.

### Sequential controller

The planned hierarchical controller is sufficient for an undergraduate paper if it is framed and evaluated as a complete adaptive inference policy:

1. input features choose initial `L`;
2. one paid sample produces validity, truncation, length, and cap-utilization state;
3. the policy stops or acquires sample 2;
4. agreement/valid-answer state after sample 2 determines stop or samples 3-4;
5. all paid trajectories count toward cost.

Regularized logistic regression is an appropriate primary learner. A shallow boosted-tree model is an ablation, not the contribution. The scientific contribution lies in the sequential formulation, utility-aligned targets, controlled baselines, and held-out Pareto evaluation.

## Does the thesis need a system component?

Yes, but it does not need an artificial product stack. The defensible system is the research infrastructure already implied by the RQ:

```text
Dataset Adapter
  -> Input Feature Extractor
  -> Sequential Compute Controller
  -> Inference Executor and Budget State
  -> Stop/Escalation Policy
  -> Strict Answer Parser and Aggregator
  -> Trace Logger, Cost Accounting, and Evaluation
```

Model adapters, dataset adapters, caching, experiment manifests, and statistical reporting support this core. A web app, RAG layer, multi-agent framework, or LangGraph implementation would inflate scope without strengthening the RQ.

## Reference-paper abstract versus current TTC abstract

The TTC abstract already contains problem motivation, completed characterization, the 0.6B MATH pilot, and a proposed controller. What remains missing for a final abstract is:

- a concrete held-out controller result;
- the exact primary comparison against depth-only and breadth-only;
- final dataset/model scope;
- actual-token and latency effect sizes;
- one sentence on whether breadth added learnable value or the study pivoted to depth-only.

Until these results exist, the abstract should remain explicitly preliminary. It must not promise cross-dataset or cross-model gains.

## Contribution-stack assessment

The proposed contributions are:

- C1: empirical breadth-depth characterization;
- C2: equal nominal budgets can differ in realized cost and accuracy;
- C3: a lightweight adaptive joint policy;
- C4: fixed, depth-only, breadth-only, joint, and oracle comparisons;
- C5: multi-dataset and limited multi-model validation.

Assessment:

- **C1-C4 with two-dataset held-out evaluation:** **ADEQUATE to STRONG** for an undergraduate paper.
- **C1-C5 with reduced second-model validation:** **STRONG** and comparable to the reference quality bar.
- **Full controller training across many models/datasets:** **OVER-SCOPED** for 12-14 weeks.
- **C1-C2 plus a flat classifier on GSM8K only:** **TOO WEAK** relative to the reference.

## Direct answer

**If the paper were finished exactly with the current one-model, one-dataset, one-controller plan, would it meet approximately the same research-quality bar as the reference? NO.**

The current work has stronger rigor and reproducibility, but the reference paper presents a completed method, broader evaluation, two model configurations, and an application layer. The smallest coherent route to parity is not to copy that breadth. It is to finish the sequential policy and evaluate it on GSM8K and MATH-500 against strong single-axis baselines, with an explicit ablation and full cost accounting.
