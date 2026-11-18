# Recommended Paper Outline

Target: a complete LNCS-style paper that preserves the current thesis scope and clearly separates completed evidence, proposed method, and final evaluation.

## 1. Abstract

### Content

- fixed-compute problem and resource constraint;
- narrowed gap: verifier-free sequential coordination of token caps and selective resampling;
- proposed policy and observability boundary;
- datasets and primary model;
- strongest held-out accuracy/token/latency result;
- direct conclusion: joint gains, depth-only pivot, or bounded negative result.

### Needed before final writing

- selected controller and policy freeze;
- held-out GSM8K and MATH results;
- primary paired effect size and uncertainty.

Do not finalize the abstract from oracle or Validation-only evidence.

## 2. Introduction

### Content

1. Fixed test-time compute can waste resources on easy problems and truncate hard ones.
2. Breadth `k` and token cap `L` are operationally different and not interchangeable.
3. Prior work already covers adaptive sampling and adaptive token budgets; the bounded gap is external, verifier-free, sequential joint control for small open-weight models.
4. State Main RQ, RQ2, and the cross-dataset part of RQ3.
5. Summarize method and evidence status.
6. List contributions without claiming priority beyond verified literature.

### Figures/tables

- optional one-panel motivation figure: fixed versus adaptive allocation under a shared average-cost budget.

### Needed evidence

- literature position;
- final scope and claims;
- final controller result for the contribution list.

## 3. Related Work

### Subsections

1. Test-Time Scaling and Self-Consistency
2. Adaptive Sampling and Agreement Stopping
3. Adaptive Token Budgets and Early Stopping
4. Difficulty-Aware and Marginal-Utility Allocation
5. Joint Parallel-Sequential Compute Allocation
6. Small Open-Weight Reasoning Models and Resource-Constrained Inference

### Content

Group prior work by allocation axis, observability, verifier/training requirement, and cost metric. End with a comparison paragraph or compact table that positions the study as black-box, external, hard-cap, sequential, and actual-cost evaluated.

### Figures/tables

- prior-work comparison table with columns: breadth, token/depth, sequential, black-box, verifier, training, models, datasets, cost.

### Needed evidence

- final dated literature refresh;
- no unverified novelty claim.

## 4. Problem Formulation

### Content

- define problem `x`, samples, `k`, token cap `L`, valid-only voting, actual token cost, and latency;
- state that `L` is not semantic reasoning depth;
- define fixed and adaptive policies;
- define policy state and permitted observations;
- define accuracy-cost Pareto dominance and success/non-inferiority criteria;
- distinguish oracle hindsight from deployable policy information.

### Figures/tables

- notation table;
- compact policy-state/action diagram if not placed in Method.

### Needed evidence

- frozen action spaces and cost rules;
- approved success criterion.

## 5. Oracle Characterization

### Content

- historical Qwen3-1.7B GSM8K grid as motivating evidence;
- equal nominal budget comparison;
- truncation and realized-cost behavior;
- per-problem preferences and oracle headroom;
- current Qwen3-0.6B MATH depth-pilot evidence;
- explicit model separation and development status.

### Figures/tables

- GSM8K accuracy heatmap;
- iso-budget table/plot;
- oracle Pareto frontier;
- MATH cap/truncation table;
- evidence-status table.

### Needed evidence

- already available; update only with versioned 0.6B characterization.

This section motivates the method but does not prove it works.

## 6. Proposed Adaptive Allocation Method

### Content

1. input feature extractor;
2. initial cap decision;
3. post-sample state construction;
4. `k=1 -> 2` and `k=2 -> 4` decisions;
5. marginal-utility targets and allowed labels;
6. logistic model and heuristic fallback;
7. answer aggregation;
8. complete policy cost accounting;
9. controller serialization and trace format.

### Figures/tables

- one Adaptive Inference Engine architecture figure;
- one stage/state transition figure or algorithm;
- feature/observability table marking input, paid state, and forbidden data.

### Needed evidence

- implemented policy;
- frozen feature schema and thresholds;
- controller training procedure.

Do not inflate this section with a web interface, multi-agent framework, or unrelated infrastructure.

## 7. Experimental Setup

### Content

- Qwen3-0.6B revision, prompt, decoding, thinking mode, hardware;
- Qwen3-1.7B historical stratum boundaries;
- GSM8K and MATH manifests/splits;
- parser contracts and audit;
- Train/Validation/Test access rule;
- baseline implementations;
- metrics and full-policy cost;
- seeds and uncertainty;
- go/pivot protocol.

### Figures/tables

- dataset/split table;
- action-space table by dataset;
- baseline definition table;
- hyperparameter/threshold table;
- compute environment table.

### Needed evidence

- frozen protocol;
- generation plan and policy hashes;
- final baseline implementations.

## 8. Results

### Content

Organize by RQ rather than by artifact chronology.

### RQ1: Does joint allocation improve the frontier?

- per-dataset policy accuracy, actual tokens, latency;
- Pareto frontier and primary paired comparison;
- GO JOINT or PIVOT DEPTH-FIRST outcome.

### RQ2: When is breadth useful?

- action frequencies and incremental utility;
- breadth-positive event counts;
- stage prediction and policy effects;
- false and missed escalation analysis.

### RQ3: Stability and transfer

- GSM8K versus MATH results;
- source-only versus pooled training;
- repeated-seed stability;
- reduced secondary model only if completed.

### Figures/tables

- main Pareto plot per dataset;
- main policy comparison table;
- paired difference/interval plot;
- action-frequency and stage-utility table;
- transfer/stability table.

### Needed evidence

- frozen held-out runs;
- all required baselines;
- paired statistical analysis.

## 9. Ablation and Analysis

### Content

- input-only versus early-inference signals;
- sequential versus flat controller;
- heuristic versus logistic policy;
- threshold/utility sensitivity;
- optional tree ablation;
- parser/truncation and cap analysis;
- representative controller traces.

### Figures/tables

- ablation table with accuracy, tokens, and latency;
- threshold sensitivity/frontier plot;
- small case-trace table.

### Needed evidence

- required ablation runs;
- selected failure cases under a pre-declared sampling rule.

## 10. Discussion

### Content

- how much oracle headroom was captured;
- whether “Depth First, Breadth Selectively” survived testing;
- differences between datasets and model strata;
- why actual tokens and latency may diverge;
- implications for external controllers on small models;
- meaning of a negative joint result.

### Needed evidence

- final results and ablations;
- no universal depth-over-breadth claim.

## 11. Limitations

### Content

- model-family and hardware dependence;
- hard cap versus semantic depth;
- parser and benchmark limitations;
- generation-seed coverage;
- development sample size and positive-event rarity;
- latency portability;
- oracle dependence on model, prompt, parser, and seed;
- any omitted cross-family validation.

### Needed evidence

- final scope decisions and unresolved risks.

## 12. Reproducibility and System Artifact

### Content

- adapter interfaces, seed policy, cache identity;
- immutable manifests and revisions;
- checkpoint/resume and append-only traces;
- parser tests and policy serialization;
- commands/configuration needed to reproduce tables and plots.

### Figures/tables

- artifact inventory or reproducibility checklist.

### Needed evidence

- final policy/config hashes;
- clean non-GPU test run;
- documented GPU commands.

This can be a subsection of Experimental Setup if page limits are strict.

## 13. Conclusion

### Content

- one direct answer per RQ;
- quantitative held-out outcome;
- bounded contribution statement;
- one concise future-work direction.

### Needed evidence

- final results only.

## Suggested page emphasis

For a 14-16 page LNCS-style manuscript including references:

| Section group | Approx. pages |
|---|---:|
| Abstract + Introduction | 2 |
| Related Work | 1.5-2 |
| Formulation + Oracle Characterization | 2.5-3 |
| Method | 2-2.5 |
| Experimental Setup | 1.5-2 |
| Results + Ablation | 3-4 |
| Discussion + Limitations + Conclusion | 1.5-2 |

The method and final results should occupy at least as much space as the historical characterization. Otherwise the paper will continue to read as an oracle study with a proposed controller rather than a completed controller paper.

## Minimum figure/table set

1. Adaptive Inference Engine architecture.
2. Oracle characterization/Pareto figure.
3. Final held-out policy Pareto figure.
4. Notation/action-space table.
5. Baseline definitions and evidence-status table.
6. Main policy results table.
7. Ablation table.
8. Transfer/seed-stability table or compact appendix table.

Every final abstract, conclusion, and contribution claim must trace to one of these result tables or figures.
