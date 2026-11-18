# Recommended Experiments

Audit date: 2026-11-11  
Goal: finish the paper within a 12-14 week undergraduate scope without opening frozen final-test outcomes prematurely.

## Completed evidence, not new work

- Qwen3-1.7B/GSM8K `k={1,2,4}`, `L={512,1024,2048}` characterization on 99 usable problems.
- Cost, truncation, oracle, failure, and paired-statistical analyses for that historical track.
- Historical 79/20 depth-controller development result: 13/20 accuracy with 12.7% fewer actual tokens than fixed `L=2048`; not held-out evidence.
- Frozen 100-problem GSM8K final-test partition; still unopened.
- Qwen3-0.6B/MATH-500 30-problem depth pilot at `L={1024,2048,4096}`.
- Current 0.6B pilot results: 10.0%, 36.7%, and 50.0% accuracy; 90.0%, 60.0%, and 43.3% truncation.
- Significant 1024-to-2048 paired gain after Holm correction; inconclusive 2048-to-4096 comparison.
- Reproducible pipeline with pinned revisions, caching, manifests, strict parsers, and 134 passing tests.

## MUST HAVE

### M1. Freeze the 0.6B protocol amendment

Before generating more labels, record:

- GSM8K and MATH development/test manifests;
- dataset-specific action spaces;
- feature availability contract;
- utility/threshold grid and -2 pp non-inferiority margin;
- exact baseline definitions;
- seed/repetition plan;
- final-test access rule.

Deliverable: one versioned protocol and manifest hashes. Do not silently reuse the historical 1.7B action space if the 0.6B evidence supports a different dataset-specific cap set.

### M2. Regenerate Qwen3-0.6B GSM8K characterization labels

Run the required development pool under the frozen 0.6B action space. Historical 1.7B labels cannot supervise the new controller.

Minimum scale:

- at least 200 usable GSM8K development problems;
- at least 100 usable MATH-500 development problems across the full study;
- at least 30 positive Train events per learned breadth stage.

Use nested sample reuse and the generation cache. Keep the final 100-problem GSM8K Test partition unopened.

### M3. Expand MATH-500 beyond the 30-problem depth pilot

Create a separately frozen development/test design. The 30-problem pilot can inform action-space feasibility but must not serve as the final second-dataset evidence.

Required checks:

- parser audit by answer type;
- subject/difficulty balance;
- accuracy, validity, truncation, actual tokens, and latency by cap;
- bounded breadth generation for controller labels after cap selection.

### M4. Implement baseline policies before the joint policy

Implement and test:

1. fixed profiles;
2. compute-matched input heuristic;
3. learned depth-only allocation;
4. Adaptive-Consistency-style breadth stopping;
5. simple depth-first heuristic.

This prevents the joint method from being compared only with weak or expensive fixed settings.

### M5. Implement the sequential joint controller

Implement explicit stages and trace every action:

- initial `L` choice from input-only features;
- `k=1 -> 2` stop/escalate decision after the first paid sample;
- `k=2 -> 4` stop/escalate decision after two paid samples;
- valid-only aggregation;
- complete token/latency charging.

Train regularized logistic models first. Fit a separate model per decision and keep rare stages heuristic if they do not meet the positive-event floor.

### M6. Validation gate and policy freeze

On expanded Validation:

- compare complete Pareto frontiers;
- apply GO JOINT / PIVOT DEPTH-FIRST / NEED MORE DATA criteria;
- choose thresholds and utility weights without final-test access;
- serialize and hash policy, feature schema, parser, manifests, model revision, and thresholds.

### M7. One-shot held-out evaluation

After the freeze, evaluate:

- frozen GSM8K Test;
- frozen MATH held-out split;
- fixed, heuristic, depth-only, breadth-only, selected joint/depth policy, and retrospective oracles.

Report datasets separately. Do not retune after seeing final outcomes.

### M8. Required statistical and efficiency analysis

- paired 95% bootstrap intervals for accuracy and actual-token differences;
- exact McNemar for pre-specified named accuracy comparisons;
- Holm correction within pre-declared comparison families;
- accuracy-actual-token Pareto plots;
- latency and hardware conditions;
- action frequency, truncation, validity, and false/missed escalation analysis.

## SHOULD HAVE

### S1. Feature ablation

Compare:

- input-only features;
- input + first-sample validity/truncation/length;
- input + paid state + agreement after two samples.

The goal is to test RQ3's signal claim, not to maximize feature count.

### S2. Controller formulation ablation

Compare the primary sequential controller with:

- flat profile classifier;
- simple rule-based policy;
- depth-only controller.

Evaluate policy utility, not only target-classification accuracy.

### S3. Utility and threshold sensitivity

Evaluate a small pre-registered grid of `lambda`/threshold values and show frontier stability. Do not select an isolated post-hoc best point.

### S4. Repeated-seed robustness

Use at least three generation seeds on a bounded Validation/Test subset or on ambiguous decisions if full repeated characterization is unaffordable. Report:

- policy performance variation;
- target/action agreement;
- whether the aggregate method decision changes.

### S5. Cross-dataset training analysis

Compare:

1. GSM8K-only training -> MATH test without retraining;
2. pooled GSM8K + MATH training -> per-dataset tests;
3. dataset-specific controllers as a diagnostic.

This separates transfer from simple pooled fitting.

### S6. Failure analysis and controller traces

Select 4-6 representative cases:

- correct early stop;
- useful depth increase;
- useful breadth escalation;
- wasted breadth;
- missed escalation;
- parser/truncation edge case.

Each trace should show only observable policy state, action, paid cost, and outcome.

## OPTIONAL

### O1. Reduced second-model-family validation

Run a small frozen subset with a different small reasoning model using a reduced action space. Evaluate the frozen heuristic/features first; train a separate calibrated controller only if data permit. Do not delay M1-M8.

### O2. SVAMP transfer check

Use SVAMP as a low-cost arithmetic distribution shift after GSM8K and MATH are complete. It is useful but cannot replace MATH.

### O3. Logistic versus shallow boosted trees

Only after sufficient positive events exist. Use nested validation and report whether extra model complexity changes the policy frontier.

### O4. Read-only demonstration

A CLI trace viewer or small static dashboard may demonstrate the adaptive inference engine after experiments. It is not a research requirement.

## Experiments not recommended

- RL or policy-gradient training;
- process reward models/verifiers;
- universal cross-model controller;
- many-dataset benchmark suite;
- RAG, multi-agent, or LangGraph integration;
- `L=8192` on the current hardware by default;
- post-hoc threshold tuning on final Test.

## Execution order

1. Protocol and manifests.
2. 0.6B GSM8K label generation.
3. MATH development expansion and parser audit.
4. Baseline implementation.
5. Sequential controller implementation.
6. Expanded Validation and go/pivot gate.
7. Policy freeze.
8. Held-out GSM8K and MATH evaluation.
9. Ablations, robustness, and failure analysis.
10. Optional secondary model/SVAMP only if schedule remains.

## Paper-ready stopping condition

The paper is experimentally ready when the selected policy has one frozen held-out evaluation on both required datasets, all primary baselines and costs are reported, the main paired uncertainty analysis is complete, and at least the signal and formulation ablations are available. A positive joint result is not required; a rigorously supported depth-only pivot is sufficient.
