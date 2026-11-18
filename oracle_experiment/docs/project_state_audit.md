# Project State Audit

Audit date: 2026-11-11  
Project: Adaptive Test-Time Compute for Small Reasoning Models  
Current direction: Joint Breadth--Depth Adaptive Test-Time Compute

## 1. Executive Summary

The project has a strong and reproducible empirical foundation, but it is not
yet ready for joint-controller training or final evaluation.

The completed foundation is: a tested inference/analysis pipeline, a
Qwen3-1.7B/GSM8K breadth--token-cap grid, paired statistical analysis, oracle
headroom analysis, a frozen GSM8K 79/20/100 split, a historical 1.7B
depth-only development baseline, and a completed Qwen3-0.6B/MATH-500 depth
pilot. The central deployable method is still missing: there is no 0.6B
GSM8K oracle-labelled development pool, no sequential marginal-utility label
builder, no breadth-only policy, no simple adaptive heuristic implementation,
and no joint controller.

**We are currently at Phase 2 -- Primary-model protocol and controller-data
construction, specifically Phase 2A.** We are not yet at controller training.
The current bottleneck is not model architecture; it is the absence of
Qwen3-0.6B model-specific trajectories and stage labels under a frozen 0.6B
protocol.

The single most important next milestone is:

> Produce an audited, frozen Qwen3-0.6B development dataset for the selected
> GSM8K and MATH-500 action spaces, with sequential state/action records,
> marginal-utility labels, class-balance statistics, and no held-out Test
> access.

Until that milestone is complete, joint-controller code would be trained
against the wrong model, an unfrozen target, or too few breadth-positive
events.

## 2. Current Research State

The current research questions remain appropriate. Repository evidence does
not justify redefining them.

**Main RQ**

> Can a lightweight per-problem controller jointly allocate generation budget
> and sampling breadth to achieve a better accuracy--compute trade-off than
> fixed-budget and single-axis adaptive strategies?

**RQ2** examines depth-first execution with selective breadth escalation.
**RQ3** examines whether inexpensive input-level and already-paid inference
signals predict the utility of more breadth. Cross-dataset evidence is required
for the final thesis; cross-family model transfer is a secondary extension.

Operational terms are stable:

- `k` is the number of independent samples (breadth).
- `L` is `max_new_tokens` per sample (generation cap / operational depth).
- `L` is not semantic reasoning depth.
- Primary cost is all actual generated tokens consumed by a deployed policy.

The current working interpretation, “Depth First, Breadth Selectively,” is
supported only as a design hypothesis under the completed 1.7B/GSM8K setting.

## 3. Project State Map

| Area | Status | Evidence in repository | What works | What is missing | Risk | Next action |
|---|---|---|---|---|---|---|
| Experiment infrastructure | DONE | `adaptive_compute/experiment_runner.py`, cache, manifests, CLI, 134 passing tests | Nested sample reuse, deterministic seeds, append-only checkpointing, resume, revision-keyed cache | Deployed policy trace/replay layer | Low | Preserve; extend only for explicit policy actions |
| GSM8K data pipeline | DONE | `dataset.py`, manual audit, n100 and expanded-pool manifests, Phase-2 split tests | Deterministic selection, hashes, one audited exclusion, disjoint partitions | 0.6B outcomes on Train/Validation IDs | Low | Reuse frozen IDs; generate new 0.6B trajectories |
| Qwen3-1.7B oracle grid | DONE | `results/qwen3_1_7b_gsm8k_n100_r1/`, 1,200 records | Full `k={1,2,4}`, `L={512,1024,2048}` characterization on 99 usable items | Repeated generation seeds | Medium for generalization | Keep as historical evidence; do not regenerate by default |
| Statistical analysis | DONE | Wilson intervals, exact paired McNemar, Holm correction, bootstrap code and reports | Planned comparisons and problem-level uncertainty | Generation-seed uncertainty for final policy | Medium | Reuse for policy-level paired comparisons |
| Oracle analysis | DONE | fixed/depth/breadth/joint oracle and exact token-budget frontiers | Quantifies hindsight headroom and cost | Deployable learnability evidence | High if overinterpreted | Retain only as upper bound |
| Paper/manuscript | PARTIAL | `paper/paper_current_revised.tex` and revision audits | Structurally complete research-in-progress paper; honest status separation | Joint policy, strong baselines, held-out and cross-dataset results | High for final submission | Update only after new evidence; avoid cosmetic rewriting now |
| Controller design | PARTIAL | design recommendation, risk/gates, paper-readiness scope | Hierarchical stages, allowed signals, marginal-utility objective are specified | One frozen 0.6B protocol with dataset-specific action spaces, lambda/threshold grid, seed plan | Medium | Write and approve a versioned 0.6B protocol amendment |
| Controller implementation | PARTIAL | `controller/depth_data.py`, `controller/depth_baseline.py` | Historical input-only depth data builder and logistic policy | Sequential state builder, breadth decisions, policy executor, trace schema | High | Do not extend until 0.6B protocol/data are ready |
| Qwen3-0.6B labels | PLANNED | Only 0.6B MATH depth-pilot outcomes exist | Model adapter and pinned revision work | GSM8K labels; breadth outcomes; sequential utility labels; label balance | Critical | Generate development trajectories after protocol freeze |
| MATH-500 pipeline | PARTIAL | adapter, prompt, parser v2, manifests, 3- and 30-item 0.6B runs | 90/90 records, zero generation errors, stratified pilot, parser fixes | At least 100 usable development items, breadth samples, separate held-out design | High | Expand after the GSM8K end-to-end prototype works |
| Depth-only baseline | PARTIAL | 1.7B 79/20 logistic result | Leakage-safe features; 13/20 Validation at 12.7% fewer tokens than fixed 2048 | 0.6B-specific labels, action space, fit and expanded Validation | High if transferred | Rebuild from 0.6B data; keep 1.7B result historical |
| Breadth-only baseline | PLANNED | Oracle analysis only; no deployable policy module | Aggregation and state signals exist in artifacts | Fixed-L sequential breadth policy, labels, thresholds, tests | Critical comparator | Implement before joint controller |
| Heuristic adaptive policy | PLANNED | Design described in docs only | Required signals can be computed | Frozen rules, policy executor, cost accounting, tests | Medium | Implement before joint controller |
| Joint controller | PLANNED | Paper/design specification only | Staged design is coherent | Training records, learners, thresholds, execution and evaluation | Central risk | Begin only after data and baselines pass readiness gates |
| Held-out evaluation | BLOCKED | Frozen 100-problem GSM8K Test manifest remains unopened | Integrity checks prevent accidental partition mixing | Frozen selected policy and MATH held-out split | Leakage risk | Keep blocked until Validation gate and policy hash |
| Multi-seed evaluation | PLANNED | Seed policy is deterministic; only one repetition in main evidence | Infrastructure supports repetitions | Bounded repeated-seed subset and stability analysis | High for noisy labels | Run after first viable Validation policy |
| Cross-dataset controller evaluation | PARTIAL | MATH pipeline/pilot only | Second data format and parser are operational | MATH breadth labels, controller data, per-dataset comparisons | High | Expand MATH after GSM8K prototype, before final policy freeze |
| Secondary model evaluation | PLANNED | 1.7B historical stratum is same family, not independent validation | Model adapter is generic | Different-family model, feasibility pilot, frozen reduced protocol | Medium, optional | Postpone until core two-dataset result is complete |
| Reproducibility/tests | DONE | 134 tests passed; 14 dependency deprecation warnings | Good coverage of parser, data, cache, runner, analysis, split and depth baseline | No tests yet for breadth/joint policy because code does not exist | Low now | Add policy tests with each new module |
| 1.7B `L=8192` extension | OBSOLETE | 11/120 partial records; two 8192 trajectories took 11.63 and 27.10 minutes and truncated | Provides feasibility evidence only | Complete result is intentionally absent | Severe compute waste | Do not resume |
| Older reports/slides | OBSOLETE | October Word/PPT files still say 1.7B primary or “finish 8192” | Useful historical narrative | Do not reflect migration or completed 0.6B pilot | Directional confusion | Replace only when a new presentation is needed |

## 4. Completed Components

1. Reproducible experiment engine, dataset/model adapters, parser,
   aggregation, cost accounting, cache/checkpoint/resume, and analysis suite.
2. Qwen3-1.7B/GSM8K n100 grid with 99 usable problems and one repetition.
3. Full statistical and oracle analysis, including the 13.13 percentage-point
   compute-matched joint-oracle headroom over depth-only.
4. Frozen GSM8K 79 Train / 20 Validation / 100 Test problem split; Test remains
   unopened.
5. Historical 1.7B depth-only data builder and logistic baseline, with explicit
   leakage controls and artifact hashes.
6. Qwen3-0.6B model migration, smoke run, and completed 30-problem MATH-500
   depth pilot at `L={1024,2048,4096}`.
7. Research audit, paper-readiness audit, revised manuscript, and explicit
   unsupported-claim audit.

## 5. Partial Components

- The controller design is specified, but its 0.6B target and action spaces are
  not frozen in one executable protocol.
- Input-only features exist; paid-state sequential features are logged in raw
  artifacts but not materialized by a controller-data contract.
- MATH-500 is operational only as a 30-item depth pilot; it is not a full
  controller or held-out dataset.
- A depth-only baseline exists only for the historical 1.7B track.
- The paper is a rigorous progress manuscript, not a final empirical paper.

## 6. Missing Components

- Qwen3-0.6B GSM8K development trajectories under the frozen action space.
- Qwen3-0.6B breadth outcomes and per-stage marginal-utility labels.
- A measured 0.6B escalation-positive distribution.
- Breadth-only and rule-based adaptive baselines.
- Sequential joint policy executor, trace format and stage learners.
- Expanded MATH-500 development and held-out partitions.
- Expanded Validation, repeated-seed stability, policy freeze and one-shot Test.
- Policy-level cross-dataset evidence and required ablations.

## 7. Obsolete / Deferred Components

### Obsolete or superseded

- Resuming Qwen3-1.7B at `L=8192`.
- Reusing 1.7B controller labels/coefficients for 0.6B.
- Treating `docs/recommended_scope.md` or the September research audit's
  “1.7B primary” recommendation as current; the 0.6B migration amendment and
  2026-11-11 paper-readiness scope supersede that model decision.
- Parser-v1 MATH aggregates when parser-v2 reprocessed artifacts are available.
- n3/n30 GSM8K runs as scientific evidence after n100 completion.
- October slides that list `L=8192` completion as the next task.

### Deferred

- Secondary model family.
- SVAMP or any third dataset.
- boosted-tree ablation until every learned stage has enough positive events.
- dashboard/web interface and presentation polishing.

## 8. Project Phases

| Phase | Status | Entry condition | Main tasks | Exit condition | Deliverables |
|---|---|---|---|---|---|
| Phase 0 -- Infrastructure | DONE | Research variables defined | Build adapters, runner, cache, parser, metrics, tests | Reproducible fake and real-model runs pass | Source package, CLI, manifests, tests |
| Phase 1 -- Historical oracle characterization | DONE | Stable 1.7B GSM8K pipeline | n100 grid, statistics, oracle/frontier and failure analysis | All expected records and reports complete | `qwen3_1_7b_gsm8k_n100_r1` |
| Phase 2 -- Primary-model protocol and controller data | **IN PROGRESS** | 0.6B adapter/pilot feasible; frozen IDs available | Freeze 0.6B action spaces/utility; generate GSM8K and expand MATH; build stage records; audit class balance | At least 200 usable GSM8K + 100 usable MATH development items and 30 Train positives per learned stage, or an explicit heuristic fallback | Versioned protocol, manifests, raw pool, sequential dataset, label report |
| Phase 3 -- Strong baselines | PLANNED | Phase-2 data contract stable | Fixed, depth-only, breadth-only and heuristic policies | Every baseline runs end-to-end with complete token charging on Validation | Baseline models, traces, Pareto report |
| Phase 4 -- Joint controller | PLANNED | Baselines operational; stage labels adequate | Logistic stage models; explicit state machine; tests | Joint policy runs reproducibly on Validation without forbidden signals | Serialized policy and trace artifacts |
| Phase 5 -- Validation gate and freeze | PLANNED | All candidate policies operational | Compare frontiers, apply gates, repeated-seed subset, select/pivot | GO JOINT, PIVOT DEPTH-FIRST, NEED MORE DATA, or ABANDON; policy hash frozen | Decision report and immutable policy bundle |
| Phase 6 -- Held-out two-dataset evaluation | BLOCKED | Phase-5 policy frozen; GSM8K and MATH tests frozen | One-shot inference and paired analysis | No retuning; complete per-dataset result tables | Final Test artifacts and statistical report |
| Phase 7 -- Robustness and ablation | PLANNED | Core result exists | Signal/formulation ablation, threshold sensitivity, bounded multi-seed analysis | Claims matched to stability evidence | Ablation and failure-analysis report |
| Phase 8 -- Final paper/thesis | PARTIAL | Phase 6 complete and Phase 7 minimum done | Insert results, revise claims, reproducibility package | Paper answers RQs with positive or negative result | Final manuscript, appendix, presentation |

## 9. Current Phase

**We are currently at Phase 2, specifically Phase 2A: freeze the primary-model
protocol and construct controller training data.**

Why:

- Phase 0 and Phase 1 are complete.
- Qwen3-0.6B is now the intended training/evaluation model.
- The frozen problem IDs and parsers exist, but 0.6B GSM8K and breadth outcomes
  do not.
- The existing 1.7B depth table cannot be used as 0.6B supervision.
- Baselines cannot be fairly fit until the 0.6B action space and outcome table
  exist.

This is not yet Phase 3 or Phase 4. Controller implementation should not start
from historical labels merely because a 1.7B logistic baseline file exists.

## 10. Main Risks

1. Breadth-positive events may remain too rare to learn.
2. One-seed labels may be unstable and encode sampling noise.
3. The current 20-item Validation set is too small for extensive tuning.
4. MATH symbolic parsing may fail on answer types not represented in the pilot.
5. GPU time may encourage premature action-space pruning or Test access.
6. Old 1.7B plans and slides may cause the team to resume obsolete work.
7. A joint policy may be Pareto-dominated by depth-only; this must remain an
   acceptable negative result.

## 11. Current Bottleneck

The bottleneck is **controller data readiness for Qwen3-0.6B**, not software
refactoring and not paper writing. Specifically, the project lacks model-
specific sequential outcomes and labels for `initial L`, `k=1 -> 2`, and
`k=2 -> 4` decisions under a frozen utility/cost contract.

## 12. Recommended Next Milestone

Complete `M0.6-DATA`:

- one approved 0.6B protocol amendment;
- frozen GSM8K and MATH development/test manifests;
- selected dataset-specific cap sets and `k={1,2,4}` policy semantics;
- at least 200 usable GSM8K and 100 usable MATH development problems;
- sequential paid-state rows and marginal-utility labels;
- class balance and repeated-seed spot-check report;
- final Test outcomes still unopened.

If a stage has fewer than 30 positive Train events at this point, it must stay
heuristic or be simplified; model complexity must not be increased to hide the
data limitation.
