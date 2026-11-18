# Six-Week Macro Roadmap

This roadmap prioritizes a defensible result over breadth of implementation.
Each week ends with a gate; a failed gate changes the next week rather than
being ignored.

| Week | Goal | Deliverable | Go/Pivot checkpoint |
|---|---|---|---|
| 1 | Freeze the Qwen3-0.6B protocol and validate a bounded GSM8K pilot | Protocol v2, manifest hashes, GPU-hour estimate, pilot audit, sequential label schema | GO if parser/action space/data builder are valid; otherwise revise before scaling |
| 2 | Produce the first controller-ready 0.6B GSM8K block | 100+ audited development problems, stage-label balance, policy replay, fixed/heuristic traces | SCALE if positive-event projection and compute are acceptable; simplify breadth if not |
| 3 | Complete GSM8K development target and strong baselines | Toward 200 usable GSM8K items; 0.6B depth-only, breadth-only and heuristic Validation frontiers | Baselines must run end-to-end before joint work; NEED MORE DATA if stages lack positives |
| 4 | Expand MATH-500 and test the same policy contract under distribution shift | At least 100 usable MATH development items, parser audit, bounded breadth labels, per-dataset balance | Continue learned stages only where the 30-positive floor holds; otherwise use heuristic stage |
| 5 | Train/evaluate the simplest joint policy and run robustness checks | Logistic stage models, full Validation Pareto curves, feature ablation, repeated-seed subset | Apply GO JOINT / PIVOT DEPTH-FIRST / NEED MORE DATA / ABANDON gate; no Test yet |
| 6 | Freeze the selected policy and, only if ready, perform one-shot held-out evaluation | Immutable policy bundle; GSM8K and MATH held-out results; paired statistics; updated manuscript sections | No retuning after Test. If freeze conditions are not met, remain in Validation and defer Test |

## Week 1 Details

**Goal:** eliminate conflicting historical plans.  
**Deliverable:** one current protocol naming 0.6B as primary, with dataset-
specific caps, lambda/threshold grid, baselines, seeds and Test rule.  
**Checkpoint:** do not launch a large run until expected generation count and
GPU time are reviewed.

## Week 2 Details

**Goal:** determine whether the planned sequential labels are observable and
non-degenerate on GSM8K.  
**Deliverable:** stage rows and balance report, not a polished controller.  
**Checkpoint:** if paid-state labels cannot be reproduced without future
samples, fix the data contract before any learning.

## Week 3 Details

**Goal:** establish the primary comparator.  
**Deliverable:** 0.6B depth-only, breadth-only and heuristic policies with
complete cost accounting.  
**Checkpoint:** joint implementation remains blocked until these policies are
testable on the same Validation records.

## Week 4 Details

**Goal:** meet the minimum two-dataset thesis scope without consuming final
tests.  
**Deliverable:** expanded MATH development pool and parser audit, reported
separately from GSM8K.  
**Checkpoint:** if MATH compute threatens the core schedule, reduce optional
seeds/model validation before reducing parser rigor or held-out separation.

## Week 5 Details

**Goal:** answer whether joint allocation adds Validation utility beyond
depth-only.  
**Deliverable:** simplest regularized logistic stages, complete Pareto curves,
signal ablation and bounded seed stability.  
**Checkpoint:** select one method outcome. Do not keep tuning indefinitely.

## Week 6 Details

**Goal:** obtain confirmatory evidence only after an immutable freeze.  
**Deliverable:** one-shot per-dataset Test artifacts and manuscript update, or
a documented decision to defer Test because the policy is not ready.  
**Checkpoint:** unfavorable Test results are reported; thresholds are not
changed.

## End-of-Six-Week Success States

Any one of the following is acceptable:

1. **GO JOINT:** a frozen joint policy improves the Validation frontier and has
   a one-shot two-dataset Test result.
2. **PIVOT DEPTH-FIRST:** depth-only is the selected deployable method and the
   thesis reports why oracle breadth headroom was not learnable.
3. **CHARACTERIZATION PIVOT:** learned policies fail after adequate data, but
   the project provides a rigorous oracle-versus-learnable study, strong
   heuristics and reproducible failure evidence.

The unacceptable state is continuing to tune controller complexity without
enough labels, without baselines, or after looking at Test.
