# Paper revision report

## 1. Output and non-destructive editing

- Revised manuscript: `paper_current_revised.tex`
- Preserved manuscript: `progress_paper.tex`
- Format: Springer LNCS LaTeX, matching the current paper project
- Revision type: research-in-progress restructuring; no completed result was invented

The new manuscript treats the repository as the evidence source. The reference
paper was used only as a quality benchmark for organization, system exposition,
figure/table density, and separation of method from results. Its wording,
research problem, and claims were not copied.

## 2. Original paper structure

The canonical source found was `progress_paper.tex`. Its section order was:

1. Abstract
2. Introduction
3. Related Work
4. Problem Formulation
5. Methodology
6. Experimental Setup
7. Preliminary Results
8. Discussion
9. Limitations
10. Planned Confirmatory Evaluation
11. Conclusion

The main structural issue was not missing content, but evidence-status mixing:
the implemented grid, a selected depth-only development baseline, the proposed
joint controller, and future confirmatory protocol appeared at similar levels.

## 3. Evidence base used

The revision was grounded in the following project artifacts:

- `results/qwen3_1_7b_gsm8k_n100_r1/grid_summary.csv`
- `results/qwen3_1_7b_gsm8k_n100_r1/iso_budget_2048.csv`
- `results/qwen3_1_7b_gsm8k_n100_r1/oracle_comparison.csv`
- `results/qwen3_1_7b_gsm8k_n100_r1/oracle_anchor_evaluation.csv`
- `results/qwen3_1_7b_gsm8k_n100_r1/paired_comparisons.csv`
- `results/qwen3_1_7b_gsm8k_n100_r1/statistical_report.md`
- `results/phase2/depth_baseline_v1/development_report.md`
- `results/phase2/depth_baseline_v1/validation_policy_summary.csv`
- `results/qwen3_0_6b_math500_depth_pilot_v1/config_results.csv`
- `results/qwen3_0_6b_math500_depth_pilot_v1/paired_comparisons.csv`
- `results/qwen3_0_6b_math500_depth_pilot_v1/statistical_report.md`
- `data/splits/phase2_gsm8k_split_v1.json`
- `data/splits/math500_pilot_v2.json`
- `docs/MODEL_MIGRATION_QWEN3_0_6B.md`
- `docs/MATH500_PARSER_V2_AMENDMENT.md`
- `docs/PHASE2_PROTOCOL.md`
- `docs/paper_readiness_audit/*`

## 4. Reference-paper lessons applied

The reference paper was stronger as a readable system paper than as a direct
methodological template. The following presentation lessons were applied:

- show the system/data flow visually before detailed results;
- organize sections so the reader can separate framework, method, experiments,
  results, and limitations;
- use figures and compact tables to anchor central empirical claims;
- maintain a clear narrative from problem motivation to system design and
  evaluation status;
- keep the conclusion aligned with evidence actually shown.

The reference paper's domain-specific architecture, wording, claims, and
evaluation design were not reused. Where its evaluation was weaker than this
project's requirements (for example, limited ablation or significance
analysis), the current paper retains the thesis's stricter paired tests,
realized-cost accounting, and leakage controls.

## 5. Main structural changes

| Area | Previous manuscript | Revised manuscript | Reason |
|---|---|---|---|
| Title | Emphasized a preliminary controller study | Emphasizes breadth--token-cap characterization and sequential allocation framework | The joint controller is not yet implemented; the title should not imply an evaluated controller contribution |
| Abstract | Included many pilot, feasibility, and statistical details | Focuses on problem, completed core evidence, method direction, and unfinished evaluation | Improves readability and prevents development evidence from appearing equivalent to final evidence |
| Introduction | Six contribution bullets, including preliminary pilots | Four scoped contributions, with the controller explicitly framed as pre-specified ongoing work | Aligns contributions with what is currently defensible |
| Related work | Four broad subsections | Adds difficulty-aware learned allocation, joint parallel--sequential compute, and small-model efficiency | Makes the novelty boundary and required baselines clearer |
| Method organization | `Methodology` mixed completed pipeline and proposed controller | Separates `Experimental Framework`, `Oracle Breadth--Depth Characterization`, and `Adaptive Allocation Framework` | Distinguishes implemented evidence from future method claims |
| Results | All evidence under `Preliminary Results` | Core oracle characterization has its own section; policy and MATH pilots remain explicitly preliminary | Gives the strongest completed study appropriate prominence without overstating controller maturity |
| Status signaling | Evidence status appeared mainly in prose/table | Status convention is stated in source comments, architecture caption, status table, results, limitations, and conclusion | Reduces ambiguity about completed versus future work |
| Planned work | One long confirmatory section | `Ongoing Work and Planned Evaluation` gives data targets, freeze points, baselines, go/pivot criteria, and robustness scope | Converts future work into an auditable protocol |

### Sections rewritten

- Abstract
- Introduction and contribution statement
- Related Work and novelty positioning
- Problem Formulation
- Experimental Framework
- Adaptive Allocation Framework
- Experimental Results
- Discussion
- Limitations
- Ongoing Work and Planned Evaluation
- Conclusion
- Bibliography entries and citation metadata

### Sections moved or split

- `Methodology` was split into `Experimental Framework`, `Oracle
  Breadth--Depth Characterization`, and `Adaptive Allocation Framework`.
- Completed oracle/grid results were promoted out of the generic `Preliminary
  Results` section into a dedicated characterization section.
- The depth-only controller and 0.6B MATH pilot remain in `Experimental
  Results` with development qualifiers.
- `Planned Confirmatory Evaluation` became `Ongoing Work and Planned
  Evaluation`, retaining incomplete but structurally useful future content.

## 6. Scientific changes

### 4.1 Claims narrowed

- “Depth first, breadth selectively” is now consistently called a working
  hypothesis supported within the tested setting, not a universal principle.
- The 13.13 percentage-point oracle gap is described as retrospective
  allocation opportunity, not evidence that a controller can learn the policy.
- The 12.7% token reduction is explicitly development-only because selection
  and reporting use the same 20-problem Validation partition.
- The Qwen3-0.6B MATH-500 result is described as a 30-problem development pilot.
- The two Qwen3 sizes are reported as separate strata; no model-superiority or
  cross-model transfer claim is made.
- The stopped 8192-token run is retained only as feasibility evidence and is
  excluded from accuracy conclusions.

### 4.2 Method boundaries clarified

- The implemented depth-only baseline and the proposed joint controller are now
  in separate subsections.
- The sequential policy lists only deployment-available signals: input features
  and features from trajectories already generated and paid for.
- Ground truth, oracle labels, and ungenerated trajectories are explicitly
  forbidden at test time.
- A flat nine-class profile classifier is not presented as the primary method,
  because the observed oracle distribution is highly imbalanced.

### 4.3 Evaluation protocol strengthened

- Primary endpoints are final-answer accuracy and actual generated tokens.
- The primary comparison is against a depth-only policy at comparable realized
  cost, not only the most expensive fixed profile.
- Fixed, input-only heuristic, depth-only, breadth-only, depth-first, joint, and
  oracle baselines are pre-specified.
- Data targets and minimum positive escalation-event counts are stated.
- Parser, manifests, feature contract, controller, utility, thresholds, and
  baseline implementations must be frozen before opening held-out outcomes.
- Go/pivot criteria are stated in policy-level accuracy/cost terms.

## 7. Missing evidence

The revision could not supply the following because no supporting experiment
currently exists:

- sequential joint-controller implementation and policy results;
- regenerated Qwen3-0.6B GSM8K controller labels;
- a frozen held-out controller comparison;
- repeated generation seeds;
- controller-level cross-dataset generalization;
- a second model-family robustness study;
- controller ablations isolating input-only and observed-trajectory features.

Each item is marked as ongoing or planned rather than replaced with expected
results.

## 8. Figures and tables retained, added, or repositioned

1. A new architecture figure explains the frozen data/model inputs, generation
   cache, strict parser, metrics, analysis branch, proposed controller branch,
   and final held-out comparison.
2. The existing completed `accuracy_heatmap.png` is now embedded in the paper.
3. The existing completed `pareto.png` is embedded to show the observed
   fixed-profile accuracy--cost frontier; retrospective oracle anchors remain
   in a separately labeled table.
4. The evidence-status table remains and is tightened.
5. Core numerical tables are retained for the grid, equal-budget comparison,
   oracle anchors, depth-only development result, and 0.6B MATH pilot.

No result figure was synthesized from unrecorded data. The two numerical plots
embedded in the paper are existing repository artifacts.

## 9. Citation changes and integrity checks

The bibliography was checked against primary publication pages where available.
The revised manuscript:

- adds PaCoRe to cover coordinated parallel--sequential test-time computation;
- supplies page ranges and DOI links for Adaptive-Consistency, Make Every Penny
  Count, RASC, Token-Budget-Aware LLM Reasoning, Thought Calibration, and
  Reasoning in Token Economies;
- supplies OpenReview URLs for the two ICLR papers;
- supplies arXiv URLs for preprints and technical reports;
- corrects the scope description of each cited method so it does not imply that
  the current work originated adaptive sampling, difficulty allocation, or
  token-budget control.

Primary metadata sources used for verification include ACL Anthology,
OpenReview, NeurIPS proceedings/OpenReview, and arXiv records. The 2026
constrained-policy paper is still a preprint and is identified as such.

## 10. Future sections explicitly marked

- The architecture caption identifies the joint-controller branch and held-out
  comparison as unfinished.
- `Adaptive Allocation Framework` labels the joint controller as proposed and
  not evaluated.
- The evidence-status table marks every unfinished empirical component.
- `Ongoing Work and Planned Evaluation` contains the future data target,
  baseline suite, freeze procedure, go/pivot criteria, repeated-seed analysis,
  and optional secondary-family extension.
- The conclusion states that the central joint-policy claim is unconfirmed.

## 11. Material intentionally not claimed

The revised paper does **not** claim:

- a working or superior sequential joint controller;
- held-out improvement over depth-only or breadth-only baselines;
- cross-dataset or cross-model controller generalization;
- superiority of Qwen3-0.6B over Qwen3-1.7B;
- equivalence between 2048 and 4096 token caps on MATH-500;
- a valid 8192-token accuracy estimate;
- that an oracle gap proves policy learnability;
- that token cap is semantic reasoning depth.

## 12. What must be updated in the next paper version

After the next experimental stage, update the manuscript in this order:

1. Add the implemented controller algorithm/pseudocode and exact feature/action
   contract.
2. Replace the proposed-controller status row with artifact-backed status.
3. Add Validation comparisons against all frozen baselines at comparable cost.
4. If go criteria are met, evaluate once on the unopened Test partition and add
   paired uncertainty/statistical results.
5. Add repeated-seed sensitivity and controller ablations.
6. Update the abstract, contributions, discussion, limitations, and conclusion
   only after those results exist.
7. If the joint policy fails, revise the central method to adaptive depth and
   report the negative joint result without changing the success criterion.

## 13. Current submission posture

The manuscript is now suitable as a rigorous progress paper or thesis working
draft. It is not yet a final empirical paper because the central deployable
joint-policy claim has not been evaluated on a frozen held-out partition. The
next evidence that should change the manuscript is controller-level Validation
and held-out accuracy--cost data, not more oracle analysis alone.
