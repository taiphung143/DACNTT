# Phase 2 Experimental Protocol

> Historical frozen protocol for the Qwen3-1.7B track. Its model-specific
> labels and learned controller are not transferable to Qwen3-0.6B. Future
> experiments follow `PHASE2_PROTOCOL_QWEN3_0_6B_V2.md`, which permanently
> fixes Qwen3-0.6B as the primary thesis model and requires regenerated
> characterization labels before controller fitting.

## 1. Objective

Evaluate whether a lightweight per-problem joint controller can outperform
fixed-budget and depth-only strategies on unseen problems at comparable
realized compute.

This protocol operationalizes the existing research questions. It does not
replace or redefine them.

## 2. Data Usage

- The existing `qwen3_1_7b_gsm8k_n100_r1` experiment is development evidence
  and motivating characterization only.
- The existing n=100 problems must not be used as the final held-out controller
  test set.
- Train, validation, and test splits must be disjoint by problem ID.
- Split manifests, seeds, source indices, and dataset hashes must be frozen
  before controller training.
- Controller selection and threshold tuning may use only the training and
  validation splits. The final test split is evaluated after model selection.

### Frozen realization (v1)

The operational split is frozen in
`data/splits/phase2_gsm8k_split_v1.json` using assignment policy
`phase2-problem-split-v1` and split seed 42:

- **Train:** 79 non-flagged problems from the existing n=100 development run.
- **Validation:** 20 other non-flagged problems from that run.
- **Test:** 100 newly selected GSM8K test problems, all outside the original
  n=100 development set.
- `gsm8k-test-01309` is retained in provenance but excluded from allocation
  because it was already marked `manual_review_required`.

The frozen split-manifest SHA-256 is
`a052a7e46ec8eb613e63112ed67528c0615a364779b4dac80e3930b69b5bd6e8`.
It contains problem IDs, source indices, question hashes, and ground-truth
hashes, but not readable ground-truth labels. The implementation refuses
cross-partition overlap, changed records, a changed manual audit, or silent
replacement of an existing frozen manifest.

The Phase 1 analysis has already exposed aggregate behavior over the n=100
development pool, so the 20-problem validation partition is a controller
model-selection split rather than a claim of fully untouched evidence. Only
the new 100-problem test partition is confirmatory. Test generations and test
outcomes must remain unused until feature design, controller choice, and
thresholds have been locked using train and validation only.

## 3. Action Space

- Breadth: `k in {1, 2, 4}`.
- Generation-token cap: `L in {512, 1024, 2048}`.
- `L` is `max_new_tokens`, an operational generation cap rather than semantic
  reasoning depth.
- Any evidence-based pruning of this action space must be reported explicitly
  and evaluated as an ablation; it must not silently change the research scope.

## 4. Controller Design

The primary proposed policy is depth-first and staged:

1. Predict the initial token cap `L` from input-level features available before
   generation.
2. Generate the first reasoning sample.
3. Decide whether to stop at `k=1` or generate another sample using inexpensive
   input-level and early-inference signals.
4. After two samples, decide whether to stop at `k=2` or increase to `k=4`.

### Frozen depth-only baseline (v1)

The pre-generation depth baseline is now operationally fixed as follows before
any held-out test evaluation:

- input data: 79 Train problems for fitting and 20 Validation problems for
  model/hyperparameter selection;
- features: only allowlisted `feature_*` columns computed from the question and
  prompt token count before generation;
- label: the smallest `L` whose observed `k=1` response is correct; if no
  observed `k=1` response is correct, use `L=2048` as a conservative deployable
  fallback and retain a separate `max_depth_fallback_unsolved` status;
- model: standardized multinomial logistic regression;
- candidate grid: `C in {0.1, 1, 10}`, class weight in `{none, balanced}`, and
  ordered target-depth decision quantile in `{0.5, 0.7, 0.9}`;
- selection rule: maximize Validation policy accuracy, then minimize Actual
  Generated Tokens, then maximize balanced target accuracy and macro-F1, with
  deterministic simplicity tie-breakers.

Labels and observed outcome columns are explicitly forbidden as model inputs.
This baseline and its selection rule must not be changed in response to the
held-out test results; any later change is a separately named ablation or
manifest revision.

Allowed signals include:

- question length and token count;
- counts of numerical quantities, operators, and simple lexical indicators;
- generated-token count and token-cap utilization;
- finish reason and truncation status;
- whether a valid final answer was parsed;
- agreement and valid-answer fraction after multiple samples.

Forbidden test-time signals include:

- the ground-truth answer;
- final-answer correctness;
- oracle behavior labels;
- the hindsight cheapest-correct profile;
- information from samples that the deployed policy has not paid to generate.

## 5. Baselines

The held-out evaluation must include:

- fixed profiles;
- a strong depth-only controller;
- breadth-only allocation;
- a simple depth-first heuristic;
- the learned joint controller;
- retrospective fixed, depth-only, breadth-only, and joint oracles as upper
  bounds only.

The joint controller must not be evaluated only against the most expensive
fixed profile. The depth-only policy at comparable realized compute is the
primary baseline.

## 6. Evaluation Metrics

Primary outcomes:

- final-answer accuracy using valid-only majority voting;
- Actual Generated Tokens.

Secondary outcomes:

- latency;
- nominal allocated budget `kL`;
- truncation rate;
- valid-answer fraction.

Every generated trajectory, including an exploratory or intermediate rollout,
must contribute its generated tokens and latency to the policy cost. A
sequential policy must not be charged only for its final selected profile.

## 7. Statistical Analysis

- Report accuracy with problem-level uncertainty intervals.
- Use paired problem-level comparisons for policies evaluated on the same test
  problems.
- Report bootstrap confidence intervals for compute and accuracy differences
  where appropriate.
- Keep dataset-level uncertainty separate from generation-level stochastic
  uncertainty.
- Do not interpret an inconclusive comparison as equivalence.

## 8. Success Criterion

The joint controller is successful if, on the frozen held-out test set, it
either:

- achieves higher accuracy than the depth-only controller at comparable
  realized compute; or
- achieves comparable accuracy using fewer Actual Generated Tokens.

Reaching retrospective oracle performance is not required.

If the joint controller does not outperform the strong depth-only baseline,
the supported conclusion is that adaptive depth is the primary mechanism and
breadth is useful only as selective escalation under the tested setting.

## 9. Current Evidence Status

Completed evidence:

- Phase 1 grid characterization on Qwen3-1.7B and GSM8K;
- Phase 1.5 cost, failure, statistical, and oracle-headroom analyses;
- n=100 scale-up with 99 evaluated problems and one stochastic repetition.
- frozen 79/20/100 Phase 2 problem split with record-level integrity checks;
- leakage-safe depth-controller Train/Validation tables from the n=100 run;
- depth-only logistic baseline selected on Validation without loading the
  held-out test partition.

Development-only observation (not held-out evidence):

- the selected depth-only candidate obtains 13/20 Validation accuracy (65%),
  matching fixed `L=2048` on those 20 problems while using 1059.45 versus
  1213.05 average Actual Generated Tokens (12.7% fewer);
- because the candidate was selected on this same 20-problem Validation set,
  this result is optimistic and must not be described as generalization or as
  confirmation of a thesis claim.

Working hypotheses:

- sufficient generation budget should be allocated before adding breadth;
- the utility of additional breadth is concentrated in a minority of problems;
- inexpensive input or early-inference signals may predict that utility.

Future evaluation:

- implement the staged breadth decisions and joint controller;
- evaluate them out of sample on frozen problem splits;
- quantify stochastic robustness;
- consider additional datasets or model families only after the primary
  single-model, single-dataset evaluation is complete.
