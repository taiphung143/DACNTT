# Research Audit: Adaptive Test-Time Compute for Small Reasoning Models

Audit date: 2026-09-19  
Scope: literature and research-design audit only  
Implementation status: frozen during this audit

## 1. Executive Summary

**Verdict: C. REFRAME BEFORE CONTROLLER DEVELOPMENT.**

The thesis direction is substantial enough for an undergraduate CS/IT thesis, but the current claim and evaluation scope are not yet defensible. The completed experiment is a strong characterization study: it uses an explicit `(k,L)` grid, separates nominal from realized compute, reports paired tests, and exposes a meaningful joint-oracle upper bound. However, adaptive sampling, adaptive token allocation, difficulty-aware compute allocation, and even cheap-feature classifiers trained to imitate budget-constrained oracle actions already have direct prior art. The novelty cannot be “a lightweight classifier chooses test-time compute.”

The defensible question is narrower: whether a **verifier-free, black-box, sequential controller** can coordinate a hard generation-token cap `L` with conditional resampling `k` for **small open-weight reasoning models**, using only inexpensive input features and signals from trajectories already paid for, while improving a held-out accuracy–**actual generated token** Pareto frontier over strong depth-only and adaptive-breadth baselines.

One dataset and one model are too narrow for that claim. They are enough for a proof of concept and possibly a tightly bounded case study, but not for statements about small reasoning models or adaptive reasoning generally. The minimum recommended scope is:

- primary model: Qwen3-1.7B;
- required datasets: GSM8K plus MATH-500 or a frozen stratified MATH subset;
- secondary model: reduced validation with Phi-4-mini-reasoning (3.8B), hardware permitting;
- primary method: hierarchical sequential controller with a cost-sensitive marginal-utility objective;
- data: at least 300 oracle-characterized development problems, preferably 400–500 if breadth-positive cases remain near 10–20%;
- final tests: the already frozen 100 new GSM8K problems plus 75–100 untouched MATH problems;
- required baselines: fixed profiles, compute-matched fixed/heuristic, learned depth-only, Adaptive-Consistency-style breadth-only, simple depth-first heuristic, joint sequential controller, and retrospective restricted/joint oracles.

The phrase “Depth First, Breadth Selectively” is currently an empirical observation and a hypothesis/design prior, not a general principle. If the joint controller fails, the thesis remains valid as a rigorous negative result explaining why joint oracle headroom did not translate into learnable gains and establishing a reproducible adaptive-depth system.

**Controller implementation should not continue now.** Freeze the existing prototype. First obtain supervisor approval for the revised RQs, two-dataset protocol, data target, controller objective, baselines and quantitative go/pivot rules.

## 2. Current Thesis Assessment

### 2.1 Completed evidence

The following statements are completed evidence from the existing repository/handover, not future claims:

- Model: Qwen3-1.7B in thinking mode.
- Dataset: 100 selected GSM8K items; 99 usable after one audited exclusion.
- One stochastic repetition.
- Grid: `k in {1,2,4}`, `L in {512,1024,2048}` with valid-only majority voting.
- Accuracy:

| k | L=512 | L=1024 | L=2048 |
|---:|---:|---:|---:|
| 1 | 9.09% | 53.54% | 70.71% |
| 2 | 17.17% | 65.66% | 81.82% |
| 4 | 28.28% | 71.72% | 83.84% |

- All 6/6 planned depth comparisons are significant after Holm correction; 4/6 breadth comparisons are significant in the current handover evidence.
- At equal nominal `kL=2048`, `1x2048` achieves about 70.71% at 1079.1 actual tokens, versus 65.66% at 1616.0 for `2x1024` and 28.28% at 1988.9 for `4x512`.
- `L=512` truncation is approximately 85–88%.
- Joint cheapest-correct oracle: 83/99 solved; 70/83 choose `k=1`; 13/83 require `k>1`; 55/83 choose `L=2048`; none choose `L=512`.
- Best fixed `4x2048`: 83/99 at about 4246.7 actual tokens/problem.
- Joint oracle: 83/99 at about 1023.5 actual tokens/problem.
- At approximately this realized cost, the restricted oracle comparison is joint 83/99, depth-only 70/99, breadth-only 69/99 and fixed 53/99.
- A development-only logistic depth controller was selected on 79 Train / 20 Validation problems. It achieved 13/20, matching fixed `L=2048`, with 1059.45 versus 1213.05 actual tokens (12.7% lower). This is model-selection evidence, not held-out evidence; exact target accuracy was 50%.
- A 100-problem new GSM8K held-out partition exists and has not been evaluated.

### 2.2 What those results establish

They establish that compute placement matters for this model/dataset/prompt/decoder, that low `L` frequently prevents a valid completion, that returns to breadth diminish at larger `k`, and that a hindsight joint action space contains substantial opportunity at comparable realized cost.

They do not establish that:

- oracle actions can be predicted;
- depth-first is universally optimal;
- one-seed oracle labels are stable;
- a controller generalizes across datasets or models;
- `L` measures semantic reasoning depth;
- the approach is novel relative to current literature.

### 2.3 Thesis significance

The project is more than “train one classifier” only if the final artifact includes the characterization, a well-defined sequential policy, strong single-axis baselines, leakage-safe held-out evaluation, cost accounting, cross-dataset evidence and a reproducible system. With only GSM8K/Qwen3 and a flat classifier, it would look like a narrow benchmark-specific experiment.

## 3. Literature Survey

The survey prioritized original OpenReview, ACL Anthology, PMLR, official dataset/model pages, and arXiv for work without a confirmed peer-reviewed version. Preprints are labelled as such.

### 3.1 Foundational breadth and budget-aware evaluation

1. **Self-Consistency Improves Chain of Thought Reasoning in Language Models** — Xuezhi Wang, Jason Wei, Dale Schuurmans, Quoc V. Le, Ed H. Chi, Sharan Narang, Aakanksha Chowdhery and Denny Zhou; ICLR 2023, peer-reviewed. It establishes fixed repeated reasoning samples plus answer marginalization/majority voting. It is the breadth baseline, not an adaptive allocator. [OpenReview](https://openreview.net/forum?id=1PL1NIMMrw)

2. **Let's Sample Step by Step: Adaptive-Consistency for Efficient Reasoning and Coding with LLMs** — Pranjal Aggarwal, Aman Madaan, Yiming Yang and Mausam; EMNLP 2023, peer-reviewed. It dynamically stops self-consistency using answer agreement, evaluates 17 reasoning/coding datasets and three models, and reports up to 7.9x sample reduction with an average accuracy drop below 0.1%. It is direct prior art for black-box adaptive breadth. [ACL Anthology](https://aclanthology.org/2023.emnlp-main.761/)

3. **Reasoning in Token Economies: Budget-Aware Evaluation of LLM Reasoning Strategies** — Junlin Wang, Siddhartha Jain, Dejiao Zhang, Baishakhi Ray, Varun Kumar and Ben Athiwaratkun; EMNLP 2024, peer-reviewed. It shows why compute-matched simple baselines are necessary and why nominally sophisticated reasoning strategies may benefit mainly from spending more compute. [ACL Anthology](https://aclanthology.org/2024.emnlp-main.1112/)

4. **Large Language Monkeys: Scaling Inference Compute with Repeated Sampling** — Bradley Brown, Jordan Juravsky, Ryan Ehrlich, Ronald Clark, Quoc V. Le, Christopher Ré and Azalia Mirhoseini; arXiv 2024, preprint. It characterizes repeated-sampling scaling and the gap between coverage and practical answer selection. It motivates breadth scaling but does not allocate `k` or `L` per query. [arXiv](https://arxiv.org/abs/2407.21787)

### 3.2 Input-adaptive compute and token budgets

5. **Scaling LLM Test-Time Compute Optimally Can Be More Effective than Scaling Model Parameters** — Charlie Snell, Jaehoon Lee, Kelvin Xu and Aviral Kumar; ICLR 2025, peer-reviewed. It allocates test-time compute based on prompt difficulty and studies search/distribution-update procedures, often with process reward models. This is strong conceptual precedent, but it is not the proposed cheap black-box small-model controller. [OpenReview](https://openreview.net/forum?id=4FWaWZtd2n)

6. **Learning How Hard to Think: Input-Adaptive Allocation of LM Computation** — Mehul Damani, Idan Shenfeld, Andi Peng, Andreea Bobu and Jacob Andreas; ICLR 2025, peer-reviewed. It predicts reward distributions across computation budgets and allocates compute where marginal benefit is expected. It uses hidden representations/reward signals and substantially more training data. It strongly threatens a generic “learn to allocate compute by difficulty” claim. [OpenReview](https://openreview.net/forum?id=6qUUgw9bAZ)

7. **Token-Budget-Aware LLM Reasoning** — Tingxu Han, Zhenting Wang, Chunrong Fang, Shiyu Zhao, Shiqing Ma and Zhenyu Chen; Findings of ACL 2025, peer-reviewed. It dynamically assigns reasoning-token budgets by problem complexity. This is direct prior art for adaptive depth/token allocation. [ACL Anthology](https://aclanthology.org/2025.findings-acl.1274/)

8. **Thought Calibration: Efficient and Confident Test-Time Scaling** — Menghua Wu, Cai Zhou, Stephen Bates and Tommi Jaakkola; EMNLP 2025, peer-reviewed. It uses lightweight probes over hidden representations to terminate reasoning dynamically, reporting token reductions across in- and out-of-distribution evaluations. It is white-box depth stopping, not black-box joint `k+L`. [ACL Anthology](https://aclanthology.org/2025.emnlp-main.722/)

9. **Think Smarter not Harder: Adaptive Reasoning with Inference Aware Optimization** — Zishun Yu et al.; ICML 2025, peer-reviewed. It trains models with Inference Budget-Constrained Policy Optimization, so it overlaps in utility framing but requires fine-tuning rather than an external controller. [PMLR](https://proceedings.mlr.press/v267/yu25s.html)

10. **Optimizing Test-Time Compute via Meta Reinforcement Finetuning** — Yuxiao Qu, Matthew Y. R. Yang, Amrith Setlur, Lewis Tunstall, Edward Emanuel Beeching, Ruslan Salakhutdinov and Aviral Kumar; ICML 2025, peer-reviewed. It casts efficient test compute as meta-RL and uses information-gain rewards. It is scientifically relevant but far beyond undergraduate compute and implementation scope. [PMLR](https://proceedings.mlr.press/v267/qu25g.html)

### 3.3 Adaptive sampling and breadth stopping

11. **Make Every Penny Count: Difficulty-Adaptive Self-Consistency for Cost-Efficient Reasoning** — Xinglin Wang, Shaoxiong Feng, Yiwei Li, Peiwen Yuan, Yueqi Zhang, Chuyi Tan, Boyuan Pan, Yao Hu and Kan Li; Findings of NAACL 2025, peer-reviewed. It combines prior difficulty and posterior sample evidence to allocate sampling. It is direct prior art for difficulty-aware adaptive breadth. [ACL Anthology](https://aclanthology.org/2025.findings-naacl.383/)

12. **Reasoning Aware Self-Consistency: Leveraging Reasoning Paths for Efficient LLM Sampling** — Guangya Wan, Yuqi Wu, Jie Chen and Sheng Li; NAACL 2025, peer-reviewed. It evaluates rationales and answer consistency for weighted voting and adaptive stopping, reporting roughly 70% sample reduction while maintaining accuracy. [ACL Anthology](https://aclanthology.org/2025.naacl-long.184/)

13. **Reasoning under Uncertainty: Efficient LLM Inference via Unsupervised Confidence Dilution and Convergent Adaptive Sampling** — Zhenning Shi et al.; EMNLP 2025, peer-reviewed. It uses diversity/confidence signals for weighted sampling and convergence-based stopping, again covering adaptive breadth rather than `k+L`. [ACL Anthology](https://aclanthology.org/2025.emnlp-main.1638/)

14. **Interpretable Adaptive Sampling for LLM Test-Time Scaling** — Mobina Kashaniyan and Ali Jannesari; arXiv 2026, preprint. It uses a fuzzy controller from prompt complexity and confidence to choose per-query sample budgets. Its breadth-only result overlaps with “lightweight interpretable controller” language. [arXiv](https://arxiv.org/abs/2608.03961)

### 3.4 Closest 2026 overlap and broader breadth/depth systems

15. **Adaptive Test-Time Compute Allocation for Reasoning LLMs via Constrained Policy Optimization** — Zhiyuan Zhai, Bingcong Li, Bingnan Xiao, Ming Li and Xin Wang; arXiv 2026, preprint. It formulates average-budget allocation, solves a Lagrangian per-instance oracle, and trains a lightweight classifier on cheap features. It evaluates MATH and GSM8K with three models. The reported experiments vary sample count rather than token cap, so they do not close the exact sequential joint `k+L` question; nevertheless, this is the highest novelty threat to the planned classifier/oracle framing. [arXiv](https://arxiv.org/abs/2604.14853)

16. **PaCoRe: Learning to Scale Test-Time Compute with Parallel Coordinated Reasoning** — Jingcheng Hu et al.; ACL 2026 long paper, peer-reviewed. It combines parallel exploration and multi-round coordination with end-to-end RL at up to multi-million-token effective compute. It shows breadth/depth coordination is not untouched territory, but it uses an entirely different scale, training regime and architecture. [ACL Anthology](https://aclanthology.org/2026.acl-long.1253/)

17. **When More Thinking Hurts: Overthinking in LLM Test-Time Compute Scaling** — Shu Zhou, Rui Ling, Junan Chen, Xin Wang, Tao Fan and Hao Wang; Findings of ACL 2026, peer-reviewed. It reports diminishing marginal returns and varying optimal thinking lengths. It supports non-uniform depth allocation but does not supply this external joint controller. [ACL Anthology](https://aclanthology.org/2026.findings-acl.1199/)

18. **Test-Time Scaling in Reasoning LLMs: Inference Regimes, Evaluation, and Reproducibility** — Mohsen Hariri, Weicong Chen, Nahal Shahini, Vikash Singh, Kai Ye, Amirhossein Samandar, Debargha Ganguly, Sreehari Sankar, Yanyan Zhang, Shouren Wang, Jerry Peng, Biyao Zhang, Michael Hinczewski and Vipin Chaudhary; arXiv 2026, preprint (v2, 31 August 2026). It distinguishes sequential, leaf-level and prefix-level scaling and emphasizes protocol-matched cost and reproducibility. It supports keeping the thesis terminology and whole-system cost precise. [arXiv](https://arxiv.org/abs/2608.04001)

### 3.5 Literature synthesis

The literature clearly answers the broad questions “should compute be adaptive?” and “can sample counts/token budgets be varied per query?” with yes in multiple settings. It does not make the present project redundant because the exact constraints differ, but it removes broad novelty.

The thesis can still add value by jointly testing:

- small open-weight reasoning models rather than frontier/API-only settings;
- a black-box external policy rather than hidden-state probes, PRMs or model fine-tuning;
- hard `max_new_tokens` choices plus sequential sample escalation;
- actual-token and latency accounting for every paid trajectory;
- cross-dataset validation and a limited cross-model check;
- a reproducible, inspectable system suitable for resource-constrained deployment.

## 4. Prior-Work Comparison Matrix

The complete machine-readable matrix is in [literature_overlap_matrix.csv](literature_overlap_matrix.csv). It records model scale, datasets, adaptation axes, verifier/hidden-state/training requirements, black-box compatibility, cost metrics, overlap and novelty threat.

Condensed view:

| Work | Adaptive breadth | Adaptive token/depth | Joint breadth-depth | Key dependency | Novelty threat |
|---|---|---|---|---|---|
| Adaptive-Consistency (2023) | Yes | No | No | Agreement stopping | HIGH |
| Learning How Hard to Think (2025) | Yes | Yes | General compute allocation | Hidden state/reward predictor | HIGH |
| Token-Budget-Aware Reasoning (2025) | No | Yes | No | Complexity-conditioned budget | HIGH |
| Difficulty-Adaptive Self-Consistency (2025) | Yes | No | No | Prior + posterior difficulty | HIGH |
| Thought Calibration (2025) | No | Yes | No | Hidden-state probes | HIGH |
| Zhai et al. (2026 preprint) | Yes | No in experiments | Generic action formalism only | Cheap-feature oracle imitation | HIGH |
| PaCoRe (2026) | Parallel | Multi-round | Coordinated but not discrete `k+L` | End-to-end RL, huge compute | MEDIUM |
| Proposed narrowed thesis | Yes | Hard token caps | Yes, staged | Cheap black-box signals | Defensible only with narrowed claims |

No novelty claim should rely solely on this finite search. The matrix should be updated again before paper submission.

## 5. Research Gap Validation

Assessment of the proposed gap: **B. Partially true but must be narrowed.**

“Lightweight” and “per-problem” are not novel. Adaptive sample counts are mature enough to require an Adaptive-Consistency-style baseline. Adaptive token budgets and hidden-state stopping are already peer-reviewed. Cheap features plus oracle-action classification appeared in a highly relevant 2026 preprint.

Defensible revised gap:

> Existing methods largely adapt sampling breadth, reasoning length, or verifier-guided search separately, and many rely on hidden states, learned verifiers, model fine-tuning, or large compute. Limited evidence exists on whether a low-overhead, verifier-free external policy can sequentially coordinate hard generation-token caps and selective resampling for small open-weight reasoning models, and whether such a policy survives dataset shift while improving actual-token/latency trade-offs over strong single-axis baselines.

This is an empirical gap, not a claim that no prior work jointly considers breadth and depth.

## 6. RQ Assessment

| Dimension | Score | Reason |
|---|---:|---|
| Clarity | 4/5 | Clear axes; “depth” needs explicit operational definition. |
| Falsifiability | 5/5 | Held-out paired comparisons can reject the claim. |
| Novelty | 2/5 | Broad version is substantially covered; narrowed sequential black-box version remains plausible. |
| Measurability | 4/5 | Metrics exist; “better trade-off” needs frozen thresholds/Pareto definition. |
| Scope | 3/5 | Feasible with two datasets and one main controller; too narrow as one-dataset, too broad if universal. |
| Undergraduate feasibility | 4/5 | Feasible with logistic/tree/heuristic methods, not RL/PRM. |
| Risk | 3/5 | Rare breadth benefit and noisy one-seed labels are substantial risks. |
| Independence from one dataset/model | 2/5 | Current evidence depends entirely on Qwen3/GSM8K. |
| Meaningful negative result | 5/5 | A depth-only outcome remains useful under a rigorous protocol. |

Recommended Main RQ:

> For small open-weight reasoning models, can a verifier-free lightweight sequential policy that allocates generation-token caps and selectively adds independent samples improve the held-out accuracy–actual-generated-token Pareto frontier over fixed profiles and depth-only or breadth-only adaptive baselines?

RQ2:

> Under matched actual generated-token budgets, when does selective breadth provide statistically reliable utility beyond adaptive depth, and which observable input or early-inference signals predict that utility?

RQ3:

> How stable are the controller’s gains, decisions and cost estimates across GSM8K and a harder mathematical reasoning dataset, and to what extent do the findings transfer to a second small-model family?

## 7. Dataset Scope Assessment

### Explicit answer

**Yes. A controller trained only on GSM8K for Qwen3-1.7B is too narrow for the current thesis wording.**

It is adequate for:

- proof of concept: yes;
- basic undergraduate thesis: only with claims restricted to a Qwen3/GSM8K case study;
- strong undergraduate thesis: no;
- workshop-style research paper: generally no, because benchmark/model-specific shortcuts and unstable labels are unresolved.

### Specific risks

- GSM8K wording and numeric format can make lexical features appear more general than they are.
- Related problem templates or variants can leak across random splits.
- Truncation at `L=512` may be a Qwen3 thinking-mode artifact rather than a general compute regime.
- Oracle labels depend on model revision, prompt, decoding seed, parser and voting rule.
- A controller could learn dataset formatting rather than marginal compute utility.
- A single domain cannot support claims about adaptive reasoning as a framework.

### Minimum and nice-to-have sets

Minimum: **GSM8K + MATH-500/frozen stratified MATH subset**. MATH contains 12,500 competition problems with worked solutions and supplies harder, multi-subject, symbolic/numeric reasoning: [MATH dataset paper](https://datasets-benchmarks-proceedings.neurips.cc/paper/2021/hash/be83ab3ecd0db773eb2dc1b0a17836a1-Abstract-round2.html).

Nice to have, in priority order:

1. **SVAMP**: 1,000 controlled arithmetic variations, reliable numeric scoring, low extra compute, but limited domain diversity. [NAACL 2021 paper](https://aclanthology.org/2021.naacl-main.168/)
2. **ARC-Challenge**: public-domain grade-school science multiple choice, easy scoring and a non-math format, but knowledge confounds the interpretation of reasoning compute. [ARC paper](https://arxiv.org/abs/1803.05457)

Do not add datasets merely to raise a count. Parser reliability and interpretability are more important than a wide suite.

## 8. Model Scope Assessment

One model is enough to develop and debug a model-specific controller but not to support plural “small reasoning models” claims.

- **Primary:** Qwen3-1.7B. Preserve the completed characterization and frozen split. The official card reports 1.7B parameters, 32,768 context and Apache-2.0 licensing. [Official model card](https://huggingface.co/Qwen/Qwen3-1.7B)
- **Secondary external validation:** Phi-4-mini-reasoning, 3.8B, MIT licensed, a different architecture/family. [Official model card](https://huggingface.co/microsoft/Phi-4-mini-reasoning)
- **Backup:** DeepSeek-R1-Distill-Qwen-1.5B if GPU memory blocks Phi, with the explicit limitation that its Qwen2.5 backbone weakens family-transfer evidence. [Official model card](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B)

Use one controller per model for primary evaluation because oracle labels are model-specific. Zero-shot cross-model transfer is an exploratory result, not a success requirement. A universal controller is over-scoped.

## 9. Controller Design Assessment

### Recommended design

Use a hierarchical sequential controller with budget-constrained marginal utility:

1. input-only features choose initial `L`;
2. generate one sample;
3. already-observed validity/truncation/length signals decide stop or `k=2`;
4. after two samples, agreement and valid-answer fraction decide stop or `k=4`;
5. every trajectory is included in cost.

Regularized logistic regression is the primary learner. A shallow gradient-boosted tree is a secondary ablation only after enough positive events exist.

### Alternatives

- Flat 9-class classifier: reject as primary due to empty/tiny classes, label imbalance and mismatch with sequentially available information.
- Hierarchical controller: best structural fit and interpretability.
- Fully online stop/more-depth/more-breadth: high scientific value but requires unvalidated continuation/regeneration semantics; too risky now.
- Two-stage difficulty/uncertainty buckets: retain as a transparent heuristic baseline.
- Utility prediction for every profile: useful training objective, but a flat deployment ignores signals acquired after sample 1.

### “Depth First, Breadth Selectively”

Frame it as:

> an empirical observation on the current Qwen3-1.7B/GSM8K characterization and a pre-registered hypothesis/design prior for the next study.

Do not frame it as an established principle. Prior work shows adaptive breadth can be highly effective, and PaCoRe shows parallel coordinated reasoning can scale in other regimes.

## 10. Training Target Recommendation

Do not train primarily on cheapest-correct 9-class labels. Current data have only 13 breadth-required solved problems and no `L=512` cheapest-correct class. A classifier can obtain misleading accuracy by predicting majority actions.

Recommended target:

```text
utility_lambda(profile) = final_correct - lambda * actual_generated_tokens
```

Train pairwise/next-action decisions:

- `L=1024` versus `L=2048` from input features;
- stop versus acquire sample 2 from state after sample 1;
- stop versus acquire samples 3–4 from state after sample 2.

Equivalently, predict whether incremental compute has positive marginal utility. Evaluate several pre-registered `lambda` values to obtain a Pareto curve. Correctness is a training label only; it can never be a test-time feature.

## 11. Evaluation Protocol

### 11.1 Data partitioning

- Split by stable problem ID, never by generated trajectory.
- Group known template/variant families so close variants cannot cross Train/Validation/Test.
- Freeze source indices, question/answer hashes, model revision, prompt, parser, sampling settings and seeds.
- Keep the existing 100 new GSM8K test problems untouched.
- Create a separately frozen MATH development/test manifest before generation.
- If data are pooled across datasets, report each dataset separately and macro-average only as secondary context.

### 11.2 In-domain evaluation

Train and select on development partitions; evaluate the frozen policy once on untouched problems from the same datasets. Use paired policy execution from cached base trajectories where causally valid, and charge all actions the policy would execute.

### 11.3 Cross-dataset evaluation

Required analysis:

- train/tune on GSM8K development only, freeze, test on MATH without retraining;
- compare with a pooled two-dataset controller;
- optional reverse direction if data/compute allow.

This distinguishes domain transfer from simply fitting both formats.

### 11.4 Optional cross-model evaluation

- First evaluate the frozen Qwen policy/heuristic zero-shot on the secondary model as exploratory evidence.
- If a small calibration pool exists, fit a separate controller with the same features and hyperparameters.
- Do not reuse Qwen oracle labels as Phi ground truth.

### 11.5 Seeds and uncertainty

- The current one-repetition grid gives problem uncertainty but not generation-seed uncertainty.
- Use at least three generation seeds on the final validation/test subset if full repeated characterization is unaffordable.
- Report seed-level variability and problem-level paired bootstrap intervals separately.
- Use exact McNemar tests for named paired accuracy comparisons and Holm correction for pre-specified comparison families.
- Do not interpret a non-significant difference as equivalence; use the frozen `-2 pp` non-inferiority margin if approved.

### 11.6 Controller training versus policy evaluation

Controller training may use oracle/correctness labels on Train. Hyperparameters, thresholds and `lambda` may use Validation. Policy evaluation uses only signals available at inference; final Test correctness is accessed solely to score the frozen policy.

## 12. Generalization Strategy

The current ~100 problems are too few for a joint controller. The 13 breadth-required successes are particularly limiting.

- Logistic regression/simple decision tree: 300 total development problems is the minimum, with at least 30 positives per binary stage.
- Gradient-boosted trees: prefer 400–500 problems and nested validation because they can overfit sparse lexical partitions.
- Neural controller: not justified at this scale.
- RL: not justified technically or scientifically; it would overwhelm the thesis with reward/training confounds.

If 300 examples still yield fewer than 30 breadth-positive events, more data or a heuristic breadth rule is required. Do not manufacture class balance by duplicating positives across splits.

Generalization evidence should form a ladder:

1. new problems, same dataset/model;
2. new dataset, same model;
3. reduced second model;
4. universal model transfer only as future work.

## 13. IT/CS Project Architecture

The completed thesis should be both an empirical study and a usable research system:

```text
Dataset adapters
    -> normalized Problem / Answer contracts
    -> pre-generation feature extractor
    -> adaptive controller
       -> initial L decision
       -> post-sample stopping/escalation decisions
    -> model adapter / inference executor
    -> strict answer parser
    -> valid-only aggregator
    -> append-only trace logger and generation cache
    -> checkpoint/resume and provenance manifests
    -> token/latency/correctness evaluation
    -> paired statistics, Pareto plots and reports
```

Required artifacts:

- model and dataset adapter interfaces;
- deterministic seed/cache identity;
- strict answer-normalization contracts and parser tests;
- controller state/action trace;
- checkpoint/resume;
- actual-token, nominal-budget and latency accounting;
- reproducible benchmark runner;
- statistical report/figure generation;
- versioned configuration and frozen test access.

An API or small read-only demo is optional after experiments. RAG, PRM, multi-agent orchestration and a large deployment stack add no necessary thesis value.

### LangGraph

**DO NOT USE.** The controller is a compact deterministic state machine. Ordinary Python is easier to test, profile, serialize and reproduce. LangGraph adds engineering complexity without research value. If used later for a demo, it must remain replaceable orchestration infrastructure and not a contribution.

## 14. Risk Analysis

The detailed register is in [risk_and_go_pivot_plan.md](risk_and_go_pivot_plan.md). Highest risks are:

| Risk | Probability | Impact | Primary mitigation |
|---|---|---|---|
| Joint does not beat depth-only | High | High | Pre-register a valid depth-only negative-result path |
| GSM8K overfitting | High | High | Require MATH validation and grouped splits |
| Rare/unstable breadth labels | High | High | 300–500 examples; pairwise targets; 30-positive minimum; repeated seeds |
| GPU cost | Medium-high | High | Pilot, cache, nested reuse, transparent action pruning |
| Cross-model failure | High | Medium | Treat model-specific controllers as primary and transfer as limited evidence |
| Parser errors | Medium-high | High | Dataset contracts, unit tests and blind manual audit |
| Token savings do not reduce latency | Medium | Medium-high | Report controlled latency separately |

## 15. Go/Pivot Criteria

### GO JOINT

On expanded validation, require at least 30 positive escalation cases and either:

- at least +3 percentage points accuracy versus depth-only at actual-token cost within ±10%; or
- at least 10% fewer actual tokens while the paired 95% interval for accuracy difference remains above a frozen `-2 pp` non-inferiority margin.

Additionally, the policy must not be dominated by adaptive breadth/simple heuristic; the gain must have the same sign on both required datasets; and repeated-seed behavior must not be grossly unstable.

### PIVOT DEPTH-FIRST

Pivot if joint adds under 2 points on both datasets and saves under 5%, is Pareto-dominated by depth-only, or breadth is selected under 10% with no positive net utility. A successful depth-only policy should save at least 10% tokens versus fixed `L=2048` within the non-inferiority margin.

### NEED MORE DATA

Require more data if a stage has fewer than 30 positive events, key accuracy-difference interval width exceeds 10 points, seed label agreement is below 0.70, Train–Validation gap exceeds 10 points, or parser failure exceeds 2%.

### ABANDON CONTROLLER

After at least 300 usable two-dataset development problems, abandon a learned controller if every learned policy is validation-Pareto-dominated by fixed or simple heuristic policies across two seeds and no data/parser defect explains the result. Pivot to a characterization and reproducibility thesis.

## 16. Recommended Thesis Scope

### Version 1: current narrow scope

- Academic depth: medium-low.
- Engineering depth: medium.
- Risk: low compute risk, high overclaim/generalization risk.
- Time: shortest.
- Defensibility: proof of concept or bounded case study only.

### Version 2: recommended constrained expansion

- Two datasets: GSM8K and MATH-500/stratified MATH.
- Qwen3 primary development; reduced Phi secondary validation.
- Hierarchical marginal-utility controller plus fixed, depth-only and adaptive-breadth baselines.
- 300 minimum, preferably 400–500, oracle-characterized development problems.
- Academic depth: high for undergraduate work.
- Engineering depth: high and coherent.
- Risk: moderate with explicit fallbacks.
- Time: feasible in 12–14 weeks if staged and cached.
- Defensibility: strong undergraduate thesis; potentially workshop-quality if held-out results and reporting are solid.

### Version 3: over-scoped

- Many datasets/models plus LangGraph, RAG, RL, PRM, agents and deployment stack.
- Academic coherence: low because too many variables.
- Engineering/compute/time risk: unacceptable.
- Defensibility: weak if breadth prevents complete controlled experiments.

**Implement Version 2, constrained.**

Possible titles:

1. *Evaluating Adaptive Test-Time Compute Allocation for Small Reasoning Models*
2. *Depth First, Breadth Selectively? Joint Test-Time Compute Allocation for Small Reasoning Models*
3. *A Reproducible Framework for Budget-Aware Inference in Small Reasoning Models*

## 17. Final Verdict

**C. REFRAME BEFORE CONTROLLER DEVELOPMENT.**

Rationale:

1. **Literature:** the broad adaptive-compute and lightweight-classifier idea is already substantially covered. Adaptive breadth, adaptive token budget, marginal-utility allocation and oracle imitation all have direct precedents.
2. **Current evidence:** the grid is rigorous and reveals real joint-oracle headroom, but only on 99 usable GSM8K problems, one model and one stochastic repetition. The current learned depth result is selected on 20 validation examples and is not confirmatory.
3. **Scope:** one dataset/model cannot sustain the general claim. Two carefully chosen datasets and a reduced second-model validation are the minimum defensible expansion.
4. **Method:** a flat 9-class classifier is scientifically weak under the observed imbalance. A hierarchical sequential policy with cost-sensitive marginal-utility targets is better aligned with deployment and data scale.
5. **Feasibility:** regularized logistic models, exact parsers, caching and staged evaluation are realistic in 12–14 weeks. RL, PRM, LangGraph, RAG and multi-agent additions are not.
6. **Failure value:** if joint does not beat depth-only, the project still yields a valid thesis through negative evidence, a validated depth policy and a reproducible evaluation system.

### Final answers to the implementation gate

1. Is the RQ defensible? **Yes, after narrowing and operationalizing “better trade-off.”**
2. Is one dataset/model too narrow? **Yes for the current claim; adequate only for a bounded case study.**
3. Minimum scope? **GSM8K + MATH; Qwen3 primary + reduced Phi validation if feasible.**
4. Controller formulation? **Hierarchical sequential policy with marginal-utility/cost-sensitive targets.**
5. Oracle-labelled data? **300 minimum; 400–500 preferred when breadth positives remain rare.**
6. Baselines? **Fixed and compute-matched profiles, depth-only, Adaptive-Consistency-style breadth-only, simple depth-first heuristic, joint policy and restricted/joint oracles.**
7. Thesis success? **Held-out Pareto improvement or at least 10% cost reduction under a frozen `-2 pp` non-inferiority criterion, plus cross-dataset evidence and a reproducible system.**
8. Fallback? **Pivot to adaptive depth and report why joint oracle headroom was not learnable.**

**Controller implementation should not continue now.**
