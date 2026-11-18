# Risk and Go/Pivot Plan

Status: proposed decision protocol. Thresholds must be reviewed and frozen before new controller evaluation. They must not be adjusted after inspecting final-test outcomes.

## Risk register

| Risk | Probability | Impact | Mitigation | Fallback |
|---|---|---|---|---|
| Joint controller does not beat depth-only | High | High for the original positive claim | Make depth-only the primary comparator; use marginal-utility targets; validate before test; report complete Pareto curves | Pivot thesis to adaptive depth plus a rigorous negative result about learnable breadth |
| Controller overfits GSM8K | High | High | Require MATH/MATH-500 validation; exclude dataset identity from the general controller; use small feature sets and regularization | Frame a dataset-specific case study or use fixed heuristic if transfer fails |
| Oracle labels are highly imbalanced | High | High | Replace flat 9-class labels with binary/pairwise stage decisions; use class weighting only on Train; require positive-event floors | Merge actions, use a heuristic for rare stages, or remove the unlearnable escalation from the primary policy |
| Breadth benefit is too rare | High | High | Increase characterization pool to 300–500; stratify by dataset/difficulty; preserve all failures, not only solved cases | Pre-register depth-only pivot and report breadth as oracle-only opportunity |
| Controller is model-specific | High | Medium | Treat primary controller as model-specific; use normalized features; perform reduced Phi-family validation | Limit claims to the primary model and report cross-model transfer as negative/exploratory |
| GPU cost exceeds schedule | Medium-high | High | Pilot throughput; cache trajectories; nested sample reuse; checkpoint/resume; transparently prune `L=512` from the main action space after an ablation | Reduce secondary-model sample size before reducing primary held-out rigor; use SVAMP instead of a larger third dataset |
| Latency is inconsistent with token savings | Medium | Medium-high | Log wall time, batch size, device, warm-up and queue conditions separately; run controlled latency repetitions | Make actual generated tokens the primary portable cost and report latency as hardware-specific |
| Multi-dataset parser is unreliable | Medium-high | High | Dataset-specific normalization contracts; unit tests; blind manual audit; record parse failures separately from wrong answers | Restrict the required second dataset to an audited numeric/symbolic subset; do not silently coerce answers |
| Cross-dataset generalization fails | High | Medium-high | Evaluate both pooled and source-only training; calibrate only on validation; analyze feature drift | Report model/dataset-specific policies and treat lack of transfer as a central result |
| One stochastic realization gives noisy labels | High | High | Use repeated seeds on validation/test and on ambiguous training cases; measure label stability | Train on aggregated/expected utility where available; downgrade conclusions to one-seed characterization |
| Validation set is too small for model selection | High now | High | Expand validation before choosing policy/hyperparameters; use nested cross-validation within development data | Keep only a pre-registered heuristic/logistic policy with no extensive tuning |
| Frozen GSM8K test is accidentally inspected | Low | High | Enforce manifest partition checks; separate output directories; do not compute labels before policy lock | Declare contamination and create a new disjoint test manifest |
| New literature removes the novelty claim | Medium | Medium-high | Maintain a dated literature matrix; claim a bounded empirical/system contribution | Reframe as replication, comparative evaluation and reproducible systems study |
| Secondary model does not fit available GPU | Medium | Medium | Benchmark a 3–10 problem pilot before full generation; use quantization only as a separately recorded condition | Use DeepSeek-R1-Distill-Qwen-1.5B as a weaker-family backup or omit cross-model confirmation and narrow claims |
| Token-cap pruning changes the original scope | Medium | Medium | Report `L=512` as a diagnostic/ablation and pre-register the reduced main action space | Retain the full grid on a small subset and state explicitly why controller actions were pruned |

## Metrics and statistical rules

- Primary effectiveness metric: exact final-answer accuracy with valid-only voting.
- Primary cost metric: all actual generated tokens consumed by the deployed policy.
- Secondary cost metrics: latency and nominal allocated `kL`.
- Primary comparison: joint versus depth-only on the same held-out problems.
- Report paired problem-level bootstrap 95% intervals for accuracy and token differences; use paired binary tests such as exact McNemar for a named operating-point accuracy comparison.
- Treat datasets as separate strata. Do not let a large/easy dataset hide degradation on the second dataset.
- A policy is **accuracy-noninferior** when the lower bound of the paired 95% confidence interval for `joint accuracy - baseline accuracy` is above `-2` percentage points. The `-2 pp` margin is proposed and must be approved before test access.
- “Matched compute” means mean actual generated tokens within ±10%, or interpolation-free comparison of the highest-accuracy policy at or below the same total-token budget.

## Objective decision gates

All development decisions use Train/Validation only. Final-test data are used once after the policy and thresholds are frozen.

### GO JOINT

Continue with the joint controller as the primary method only if all conditions below hold on expanded validation:

1. At least 30 Train escalation-positive events exist for `k=1 -> 2`; the `k=2 -> 4` classifier also needs 30 positives or must remain heuristic.
2. At one pre-registered operating point, joint either:
   - improves accuracy over depth-only by at least 3 percentage points at actual-token cost within ±10%; or
   - reduces actual generated tokens by at least 10% while satisfying the `-2 pp` accuracy-noninferiority rule.
3. Joint is not Pareto-dominated by an Adaptive-Consistency-style breadth baseline or the simple depth-first heuristic.
4. The benefit has the same sign on both required datasets, even if one dataset’s confidence interval is inconclusive.
5. Policy behavior is stable enough that changing the generation seed does not reverse the aggregate decision on more than 30% of the repeated validation problems.

### PIVOT DEPTH-FIRST

Make adaptive depth the primary thesis system if any of the following holds after adequate data:

1. Joint’s accuracy gain over depth-only is below 2 percentage points on each required dataset and token saving is below 5%; or
2. joint is Pareto-dominated by depth-only at every pre-registered validation operating point; or
3. breadth is selected for fewer than 10% of validation problems and provides no positive net utility after counting all generated trajectories; or
4. depth-only achieves at least 10% token saving versus fixed `L=2048` while satisfying the `-2 pp` accuracy-noninferiority rule, and joint adds no reliable benefit.

The completed 13/20 validation result is suggestive but cannot trigger this decision because that validation set is too small and was used for model selection.

### NEED MORE DATA

Acquire more oracle-labelled development data before selecting the method if any condition holds:

1. fewer than 30 positive events are available for a learned escalation decision;
2. the minority action rate is below 10% and the estimated rate’s interval remains wide;
3. the 95% interval width for the key validation accuracy difference exceeds 10 percentage points;
4. repeated-seed agreement for training targets is below 0.70;
5. Train-to-Validation accuracy or balanced-accuracy gap exceeds 10 percentage points;
6. a parser/manual-audit failure affects more than 2% of evaluated items;
7. either dataset contributes fewer than 75 usable validation/evaluation problems to the relevant comparison.

The response is to add examples or simplify/merge decisions—not to increase model complexity.

### ABANDON CONTROLLER

Abandon a learned controller as the thesis centerpiece and pivot to empirical characterization if, after at least 300 usable primary-model development problems across two datasets:

1. every learned joint and depth policy is Pareto-dominated on validation by a fixed profile or pre-registered heuristic; and
2. the failure persists across two generation seeds or a repeated-seed subset; and
3. tuning/calibration is not the obvious cause (large Train–Validation gap, broken parser, or missing positive events); and
4. the best controller cannot beat a prompt-length/agreement heuristic on either accuracy at matched cost or cost at noninferior accuracy.

This is not thesis failure. The project becomes a reproducible study of oracle-versus-learnable headroom, budget accounting and failure modes in small-model test-time scaling.

## Final-test interpretation

After the validation gate chooses GO JOINT or PIVOT DEPTH-FIRST:

1. serialize the final policy and hash configuration, features, parser, model revision, datasets and thresholds;
2. run each frozen final test exactly according to protocol;
3. report all primary outcomes and uncertainty, including unfavorable results;
4. do not retune on test; any follow-up is explicitly a post-hoc ablation using a new test set;
5. separate in-domain GSM8K, cross-dataset MATH and cross-model results rather than averaging them into one headline number.

## Decision ownership

The supervisor should approve the action-space revision, data target, non-inferiority margin and go/pivot thresholds. Once approved, they become protocol decisions; future evidence can justify a versioned amendment, but no result-dependent silent change is acceptable.
