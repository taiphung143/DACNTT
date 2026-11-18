# Single-Axis Comparator Replay: GSM8K Train/Validation

Replay date: 2026-11-12  
Status: completed development comparison; Test remains unopened

## Added frozen comparators

Two low-data comparator families were added without new generation:

1. `depth_only_input_tertile_k1_v1`: use the Train prompt-token tertiles to
   choose `L`, always use one sample;
2. `breadth_only_agreement_L{512,1024,2048}_v1`: hold `L` fixed, always
   acquire two samples, stop for two matching valid answers, otherwise acquire
   samples 3--4.

The active replay artifacts are schema v3:

- Train: `qwen3_0_6b_gsm8k_n79_baseline_replay_v3`;
- Validation: `qwen3_0_6b_gsm8k_validation_n20_baseline_replay_v3`.

The Validation artifact uses the byte-identical Train policy config and does
not fit thresholds or stopping rules. Fixed endpoint reconstruction remains
exact, Test overlap is zero, and the full software suite passes 160 tests.

## Train results

| Adaptive policy | Accuracy | Mean actual tokens |
|---|---:|---:|
| Depth-only input tertile | 62.0% | 650.2 |
| Joint depth-first heuristic | 75.9% | 1,307.1 |
| Breadth-only agreement, `L=512` | 64.6% | 1,523.0 |
| Breadth-only agreement, `L=1024` | 73.4% | 1,799.8 |
| Breadth-only agreement, `L=2048` | 78.5% | 2,249.7 |

The joint heuristic is non-dominated on Train. This is development evidence,
not an independent estimate.

## Validation results

| Adaptive policy | Correct | Accuracy | Mean actual tokens | Point-frontier status |
|---|---:|---:|---:|---|
| Depth-only input tertile | 13/20 | 65% | 921.5 | non-dominated |
| Joint depth-first heuristic | 15/20 | 75% | 2,149.1 | dominated |
| Breadth-only agreement, `L=512` | 11/20 | 55% | 1,441.7 | dominated |
| Breadth-only agreement, `L=1024` | 15/20 | 75% | 2,095.9 | non-dominated |
| Breadth-only agreement, `L=2048` | 15/20 | 75% | 3,114.8 | dominated |

The joint heuristic and breadth-only `L=1024` policy are correct on exactly
the same 15 Validation problems. The breadth-only policy uses 53.2 fewer mean
tokens (2.5%), so it point-dominates the joint heuristic. The paired token
bootstrap interval is wide (`-713.4` to `+913.2`), so this small difference is
not statistically resolved.

Relative to depth-only, the joint heuristic gains two correct problems
(`+10 pp`, bootstrap interval `[0,+25]`) but consumes 1,227.6 additional mean
tokens (`+133%`, token interval `[+353.2,+2,225.3]`). Relative to breadth-only
`L=2048`, it has identical per-problem correctness and uses 31.0% fewer mean
tokens with a paired token interval wholly below zero.

After Holm correction, no adaptive-policy accuracy comparison is significant.

## Development decision

The pre-registered `GO JOINT` condition is not met: the joint heuristic does
not improve the Validation point frontier over the single-axis breadth-only
`L=1024` comparator. Because every learned stage also remains below 30
positive Train examples, a learned joint controller is not authorized.

Applying the development selection rule "maximize Validation accuracy, then
minimize mean actual generated tokens" to the frozen adaptive policies selects
`breadth_only_agreement_L1024_v1` as the deployable candidate. This selection
is optimistic because it uses only 20 Validation problems and must not be
revisited after Test.

The joint heuristic remains a frozen research-hypothesis comparator, allowing
the final study to report whether the Validation dominance persists. This is
an evidence-driven negative result about the tested joint heuristic, not proof
that joint breadth--depth allocation is universally ineffective.

## Next gate

Before any Test generation:

1. serialize a policy-freeze bundle containing selected candidate, joint
   comparator, all baseline definitions, model/prompt/parser/action-space
   hashes, Train thresholds, source manifests, and decision rule;
2. verify the bundle is immutable and Test has not been materialized;
3. run the frozen 100-problem Test once, replay every frozen policy, and do not
   retune from Test outcomes.

