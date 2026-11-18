# Unsupported claims audit

## Status definitions

- **Supported**: directly backed by current repository artifacts.
- **Development-only**: backed by Train/Validation or a small pilot, but not by
  a frozen held-out evaluation.
- **Hypothesis**: motivated by completed evidence but not established.
- **Proposed**: method is specified but not yet implemented/evaluated.
- **Unsupported / prohibited**: must not appear as a factual conclusion.

## Claim-level audit

| Claim | Status | Evidence or issue | Manuscript action |
|---|---|---|---|
| The Qwen3-1.7B GSM8K grid contains 99 usable problems and nine `(k,L)` profiles | Supported | `grid_summary.csv`, experiment manifest, manual audit | Retained as completed characterization |
| Accuracy rises with the tested token cap at every breadth | Supported in this setting | Grid table and six Holm-corrected adjacent depth comparisons | Retained with setting and repetition qualifiers |
| Depth is universally better than breadth | Unsupported | Only one main dataset/model/repetition; 13 oracle-solved cases require breadth | Explicitly rejected |
| Equal nominal `kL` implies equal compute or accuracy | Contradicted by evidence | `iso_budget_2048.csv` | Replaced by measured realized-token comparison |
| One `1x2048` trajectory outperforms `4x512` at nominal budget 2048 | Supported in this setting | 70.71% vs 28.28%; 1,079.1 vs 1,988.9 tokens | Retained, not generalized beyond the setting |
| The joint oracle reaches 83.84% at 1,023.5 average generated tokens | Supported as hindsight analysis | `oracle_comparison.csv`, `oracle_anchor_evaluation.csv` | Retained and repeatedly labeled retrospective/non-deployable |
| The joint oracle proves a joint controller will work | Unsupported | Oracle uses ground truth and all counterfactual outcomes | Explicitly rejected |
| The compute-matched joint-oracle gap over depth-only is 13.13 percentage points | Supported as retrospective opportunity | Exact constrained frontier: 83 vs 70 solved of 99 | Retained only as an opportunity estimate |
| Most solved problems prefer `k=1` under cheapest-correct selection | Supported in observed pool | 70 of 83 oracle-solved problems | Retained with sample-pool qualification |
| “Depth first, breadth selectively” is a validated general rule | Hypothesis only | Consistent with grid/oracle pattern, but no held-out policy test | Written as working hypothesis |
| The 1.7B depth logistic policy saves 12.7% tokens with unchanged Validation accuracy | Development-only | 13/20 for both policies; 1,059.45 vs 1,213.05 tokens | Retained with same-Validation selection warning |
| The depth logistic policy improves held-out efficiency | Unsupported | Frozen Test has not been evaluated | Not claimed |
| Exact profile-label accuracy is the primary success metric | Methodologically inappropriate | Thesis question concerns policy accuracy/cost; class labels are imbalanced | Relegated to a diagnostic metric |
| The Qwen3-0.6B MATH pilot contains 30 problems and 90 successful records | Supported development evidence | Pilot manifest, raw records, statistical report | Retained as a pilot |
| Qwen3-0.6B accuracy is 10.0%, 36.7%, and 50.0% at 1024/2048/4096 | Supported development evidence | `config_results.csv` | Retained with sample-size qualifier |
| The 1024-to-2048 MATH gain is significant after Holm correction | Supported development evidence | exact McNemar `p=0.0078125`, adjusted `p=0.015625` | Retained as within-pilot evidence |
| The 2048 and 4096 caps are equivalent | Unsupported | Corrected comparison is inconclusive (`p=0.125`) | Explicitly rejected; “inconclusive” used |
| Qwen3-0.6B is better than Qwen3-1.7B | Unsupported | One seed and mixed cap-dependent directions | Not claimed; tracks remain separate |
| An 8192-token profile has a measured accuracy | Unsupported | Only two stopped/truncated trajectories | Excluded from accuracy analysis |
| The 8192 diagnostic demonstrates feasibility on current hardware | Contradicted | 11.63 and 27.10 minutes for two still-truncated trajectories | Used only to justify the feasibility amendment |
| Existing 1.7B controller labels transfer to 0.6B | Unsupported and unsafe | Labels depend on model outputs, prompt, parser, and seed | Explicitly prohibited |
| The sequential joint controller has been implemented | Unsupported | No completed controller artifact or evaluation | Labeled proposed/ongoing |
| The sequential joint controller improves the Pareto frontier | Unsupported central future claim | Requires frozen baseline and held-out comparison | Reserved for future evaluation |
| Controller generalization across GSM8K and MATH is established | Unsupported | No completed joint controller on either dataset | Not claimed |
| Controller generalization across model families is established | Unsupported | Only Qwen3 sizes; no secondary family controller evidence | Not claimed |
| Current latency measurements are hardware-independent | Unsupported | Latency depends on RTX 4060 and execution conditions | Qualified as hardware-specific |
| `L` measures semantic reasoning depth | Unsupported terminology inference | `L` is `max_new_tokens` only | Explicit operational definition retained |
| The pipeline is reproducible and tested | Supported as engineering evidence | Frozen manifests, versioned artifacts, and 134 passing non-GPU tests at last validation | Retained as a system contribution, not a performance result |

## Unsupported or premature wording replacements

| Original or premature claim | Problem | Evidence available | Recommended replacement |
|---|---|---|---|
| “The proposed controller improves efficiency.” | The sequential joint controller is not implemented or evaluated. | Only a separate depth-only Validation baseline exists. | “The proposed controller has not yet been evaluated; the oracle characterization motivates its design.” |
| “Our adaptive method outperforms fixed and single-axis baselines.” | No frozen joint-policy comparison exists. | Retrospective oracle frontiers and one selected depth-only baseline. | “Retrospective oracle analysis indicates allocation headroom; deployable adaptive superiority is not yet evaluated.” |
| “The controller saves 12.7% tokens without accuracy loss.” | Sounds confirmatory and hides same-set selection. | 13/20 Validation accuracy and 12.7% lower mean tokens after candidate selection on the same 20 problems. | “The selected depth-only development candidate matches fixed-$L=2048$ Validation accuracy while using 12.7% fewer tokens; this optimistic result requires held-out confirmation.” |
| “Depth is better than breadth.” | Overgeneralizes one model/dataset/repetition and ignores breadth-dependent cases. | Equal-budget result plus 13 of 83 oracle-solved cases requiring $k>1$. | “Under the evaluated setting, adequate token cap is usually more valuable than several short truncated samples, while selective breadth remains useful for a minority of problems.” |
| “The joint oracle proves the policy is learnable.” | Oracle uses forbidden ground-truth and counterfactual signals. | 13.13-point compute-matched retrospective gap. | “The joint oracle quantifies opportunity but does not establish learnability.” |
| “Qwen3-0.6B performs better than Qwen3-1.7B.” | One seed, 30 development problems, and cap-dependent directions do not support superiority. | Separate descriptive accuracy/truncation tables. | “The two model-size strata are reported descriptively and separately; no model-superiority claim is made.” |
| “Increasing the MATH cap to 4096 significantly improves accuracy.” | The 2048-to-4096 paired test is inconclusive after correction. | Four improvements, no regressions, adjusted $p=0.125$. | “Accuracy is directionally higher at 4096, but the 2048-to-4096 comparison is inconclusive in the 30-problem pilot.” |
| “The method generalizes across datasets.” | No implemented controller has been evaluated across GSM8K and MATH. | Characterization/pilot evidence only. | “Cross-dataset controller evaluation is planned.” |
| “The method generalizes across models.” | Both reported sizes are from Qwen3 and labels are model-dependent. | Separate 1.7B and 0.6B strata. | “Cross-model and cross-family generalization is not yet evaluated.” |
| “The method reduces latency.” | Current analysis centers on tokens; latency is hardware-specific and no joint policy exists. | Per-profile timing and stopped 8192 feasibility records. | “Latency is reported descriptively for the recorded hardware; policy-level latency reduction is not yet evaluated.” |
| “This is the first adaptive test-time compute method.” | Prior work already adapts samples, token budgets, stopping, and general inference compute. | Related-work audit and verified citations. | “This study examines joint breadth--token-cap allocation under a constrained verifier-free small-model setting.” |
| “The method is optimal / guarantees efficiency.” | Neither optimality nor a theoretical guarantee has been established. | A retrospective cheapest-correct oracle and empirical protocol only. | “The method is designed to improve the empirical held-out accuracy--realized-cost frontier.” |

## Claims that require future evidence before promotion

### Central claim

> A verifier-free sequential joint breadth--token-cap policy improves the
> held-out accuracy--actual-generated-token Pareto frontier over fixed,
> depth-only adaptive, and breadth-only adaptive baselines.

Required evidence:

1. sufficient model-specific oracle data for training and Validation;
2. implemented sequential decisions with complete paid-trajectory accounting;
3. frozen features, parser, controller, thresholds, and baselines;
4. untouched held-out outcomes;
5. paired accuracy and realized-cost comparison with uncertainty;
6. generation-seed sensitivity analysis.

### Selective-breadth claim

> Breadth escalation provides predictable positive marginal utility after an
> adequate first trajectory.

Required evidence:

- enough positive escalation events;
- calibration and discrimination of the escalation model;
- comparison with agreement-only stopping and a simple depth-first heuristic;
- ablation of input-only versus post-first-trajectory signals.

### Generalization claim

> The learned allocation rule transfers across datasets or model families.

Required evidence:

- separate in-domain and cross-domain evaluation;
- no reuse of model-dependent labels across model revisions;
- at least one secondary model family for a cross-family claim;
- reported degradation and uncertainty, not only pooled averages.

## Integrity guardrails for future revisions

1. Do not replace “development”, “pilot”, “retrospective”, or “proposed” with
   final-sounding language until the corresponding freeze/evaluation occurs.
2. Do not report the held-out Test partition during further model or threshold
   selection.
3. Charge all trajectories generated by a sequential policy, including failed,
   exploratory, and discarded samples.
4. Do not use ground truth, oracle labels, future samples, or ungenerated
   outcomes as controller features.
5. Keep 1.7B and 0.6B results separated unless an explicitly designed pooled
   analysis justifies aggregation.
6. Treat statistical non-significance as inconclusive, not equivalence.
7. Version parser changes and reprocess raw outputs without silently mixing
   parser versions.
8. If the joint policy fails the pre-specified go criteria, report the negative
   result and pivot to adaptive depth rather than redefining success post hoc.
