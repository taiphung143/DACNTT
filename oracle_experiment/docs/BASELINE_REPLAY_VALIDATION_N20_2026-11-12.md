# Frozen Baseline Replay: GSM8K Validation n=20

Evaluation date: 2026-11-12  
Status: completed Validation evidence; Test remains unopened

## Protocol integrity

The Validation grid used the unchanged Qwen3-0.6B revision, seed 42,
`gsm8k_cot_v3`, `gsm8k_numeric_v3`, `k={1,2,4}`, and
`L={512,1024,2048}`.

- 240/240 unique generation records;
- 180/180 unique configuration rows;
- zero generation errors;
- 157/160 non-truncated generations parsed (98.13%);
- the three non-truncated parse failures ended with `Final answer: books` and
  were correctly rejected under the frozen numeric-only contract;
- no parser amendment or outcome relabelling was performed;
- no Test problem was loaded.

Replay artifact:
`results/phase2/qwen3_0_6b_gsm8k_validation_n20_baseline_replay_v2`

The Validation replay loaded the Train-fitted policy configuration byte for
byte. Its SHA-256 is
`9a26d39bff4e4e4cb7cc0d3afc6d0aa367e0ae7c7faddfde2833e318c53315a5`.
The code did not refit prompt-length tertiles or change stopping rules.

## Frozen heuristic behavior

The Train thresholds `117/132` selected:

- `L=512` for 6 problems;
- `L=1024` for 4 problems;
- `L=2048` for 10 problems.

The breadth rule stopped at `k=1` for 14 problems and fell back to `k=4` for
6. It again produced no `k=2` stop.

## Validation results

The heuristic achieved:

- accuracy: 15/20 = 75.0%;
- mean actual generated tokens: 2,149.05;
- mean allocated token budget: 2,841.6;
- valid final-answer rate: 90.0%.

It is non-dominated on the descriptive Validation accuracy--actual-token
frontier.

Key paired comparisons:

| Fixed comparator | Fixed accuracy | Heuristic accuracy | Accuracy difference, bootstrap 95% interval | Mean token change | Token-difference bootstrap 95% interval |
|---|---:|---:|---:|---:|---:|
| `2x1024` | 65% | 75% | +10 pp, [0,+25] | +830.9 (+63.0%) | [-94.2,+1,941.8] |
| `2x2048` | 70% | 75% | +5 pp, [0,+15] | +179.4 (+9.1%) | [-554.4,+993.1] |
| `4x1024` | 75% | 75% | 0 pp, [0,0] | -425.9 (-16.5%) | [-1,259.1,+520.6] |
| `4x2048` | 75% | 75% | 0 pp, [0,0] | -1,444.8 (-40.2%) | [-2,054.4,-923.3] |

For `4x1024` and `4x2048`, the heuristic and fixed policy are correct on the
same 15 problems. Against `4x2048`, the paired token interval is wholly below
zero. Against the closer-cost `2x2048` comparator, the heuristic gains one
correct problem at 9.1% higher mean cost, but the small-sample uncertainty is
wide.

After Holm correction, no accuracy comparison is statistically significant.
The result therefore supports a promising frozen heuristic operating point,
not a general superiority claim.

## Decision boundary

Update: the missing single-axis comparators were completed on 2026-11-12.
See `COMPARATOR_REPLAY_VALIDATION_N20_2026-11-12.md`; the active Train and
Validation replay artifacts are schema v3. The breadth-only agreement policy
at `L=1024` point-dominates the joint heuristic on Validation, so `GO JOINT`
is not met. Test remains unopened pending a policy-freeze bundle.

This result does not unblock a learned joint controller: all learned stages
remain below the 30-positive Train floor. It also does not by itself authorize
Test access because the pre-registered breadth-only and depth-only comparator
set is not yet complete.

The next engineering step is to replay the remaining low-data deployable
comparators without new GPU generations:

1. input-tertile depth-only heuristic (`k=1`);
2. agreement-stopping breadth-only heuristic at each fixed cap (always acquire
   two samples, stop on two matching valid answers, otherwise acquire four).

After these comparator definitions and artifacts are frozen, select the
candidate policy on Validation, serialize its hashes, and conduct the
one-time Test evaluation only if the final-test gate is satisfied.
