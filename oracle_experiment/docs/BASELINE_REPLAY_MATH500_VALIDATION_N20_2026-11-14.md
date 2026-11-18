# Fixed and Heuristic Baseline Replay: MATH-500 Validation n=20

Replay date: 2026-11-14  
Status: completed frozen Validation model-selection evidence; MATH Test remains unopened

## Decision

The Validation replay passes all provenance, endpoint reconstruction,
cost-accounting, and leakage checks. The current joint depth-first heuristic
and all three adaptive breadth policies are Pareto-dominated by fixed profiles
on this Validation sample.

- Validation replay integrity: **PASS**.
- Fixed endpoint reconstruction: **PASS (180/180 exact)**.
- Train policy reuse: **PASS (byte-identical SHA-256)**.
- `GO JOINT`: **NOT MET**.
- Current MATH direction: **PIVOT AWAY FROM THE JOINT HEURISTIC; retain the
  fixed/depth-oriented frontier and report agreement stopping as a negative
  comparator result**.
- Test decision: **DO NOT OPEN until the two-dataset policy bundle and MATH
  freeze mechanism are complete**.

This is Validation evidence used for model/policy selection. It is not final
held-out Test evidence and does not establish population-level equivalence.

## Frozen replay contract

Source grid:
`results/qwen3_0_6b_math500_validation_n20_contract_v1`

Train policy source:
`results/phase2/qwen3_0_6b_math500_train_n80_baseline_replay_v1/policy_config.json`

Validation replay:
`results/phase2/qwen3_0_6b_math500_validation_n20_baseline_replay_v1`

The Train and Validation copies of `policy_config.json` have SHA-256:
`0dc3dc60749fe1895ead7e52f66f2ba7df6dcf09ab4576b75675d0605ead5264`.
The replay did not refit prompt-token tertiles or alter stopping rules.

Integrity checks:

- 20/20 frozen Validation problems and zero Train/Test rows;
- 240/240 raw generations and 180/180 configuration rows;
- zero generation errors, missing keys, unexpected keys, or duplicate keys;
- 180 fixed traces, 20 joint-heuristic traces, 20 depth-only traces, and 60
  breadth-only traces;
- source raw/config/experiment/split hashes and all derived artifact hashes
  recorded;
- fixed replay exactly reproduces correctness, actual tokens, allocated
  budget, validity, truncation, and latency from every configuration endpoint.

## Frozen policy behavior

The Train thresholds `79.3333/109.6667` select:

- `L=1024` for 7 Validation problems;
- `L=2048` for 6;
- `L=4096` for 7.

The joint heuristic stops at `k=1` for 9 problems and falls back to `k=4`
for 11. It again produces no `k=2` stop. These actions are outcomes of the
frozen policy and are not retuned after seeing Validation.

## Validation results

| Policy | Correct | Accuracy | Mean actual tokens | Point-frontier status |
|---|---:|---:|---:|---|
| Fixed `1x1024` | 4/20 | 20% | 958.95 | non-dominated |
| Fixed `1x2048` | 9/20 | 45% | 1,538.05 | non-dominated |
| Fixed `1x4096` | 11/20 | 55% | 2,388.70 | non-dominated |
| Fixed `2x4096` | 13/20 | 65% | 4,700.50 | non-dominated |
| Depth-only input tertile | 7/20 | 35% | 1,994.00 | dominated |
| Joint depth-first heuristic | 10/20 | 50% | 5,935.55 | dominated |
| Agreement stopping, `L=1024` | 6/20 | 30% | 3,619.60 | dominated |
| Agreement stopping, `L=2048` | 12/20 | 60% | 5,223.00 | dominated |
| Agreement stopping, `L=4096` | 13/20 | 65% | 7,564.65 | dominated |

The entire descriptive Validation Pareto frontier consists of fixed profiles.
In particular, fixed `2x4096` has the same point accuracy as agreement stopping
at `L=4096` and uses 2,864.15 fewer mean tokens (37.9% relative to the
agreement-stopping cost).

## Paired interpretation

Agreement stopping at `L=4096` and fixed `2x4096` have identical observed
correct/incorrect outcomes for all 20 problems. Agreement stopping nevertheless
uses 2,864.15 more mean tokens; the paired bootstrap 95% interval for its token
difference is `[+1,393.50, +4,426.15]`.

Agreement stopping at `L=4096` also has identical observed outcomes to fixed
`4x4096`, while saving 1,414.45 mean tokens; the paired token-difference
interval is `[-2,142.25, -762.65]`. Thus, it successfully stops some unnecessary
four-sample acquisitions, but on this Validation set fixed `k=2` already
achieves the same observed outcomes at substantially lower cost.

The joint heuristic is 15 percentage points below fixed `2x4096` and uses
26.3% more mean tokens. Its paired accuracy interval is `[-30, 0]` percentage
points and all Holm-adjusted accuracy comparisons remain inconclusive because
`n=20` is small. Inconclusive inference is not evidence of equivalence; the
Pareto-dominance statements above refer to observed point estimates.

## Scientific interpretation

Completed Train evidence showed strong aggregate benefits from increasing the
token cap, but the prompt-length tertile rule fails to allocate that depth
effectively on MATH-500. Validation also does not support additional breadth
beyond `k=2` at `L=4096` for the tested seed. This is a valid negative result
for the current verifier-free heuristics, not evidence that adaptive compute
is impossible under other signals or larger training data.

No learned joint controller is evaluated because the registered 30-positive
Train floor was not met. Oracle values remain retrospective upper bounds and
must not be compared as deployable policy results.

## Authorized next work

1. Record the cross-dataset `GO JOINT / PIVOT` decision using the completed
   GSM8K and MATH Validation evidence.
2. Generalize the immutable policy-freeze bundle to include dataset identity,
   MATH action space, Train policy hash, Validation replay hash, selected MATH
   fixed comparator, and one-shot Test access rules.
3. Do not open MATH Test while modifying the freeze code or selection record.
4. Run the full test suite and verify the freeze bundle before any MATH Test
   generation.
5. Preserve all adaptive policies as registered comparators in the eventual
   Test report even if the selected MATH policy is fixed `2x4096`.
