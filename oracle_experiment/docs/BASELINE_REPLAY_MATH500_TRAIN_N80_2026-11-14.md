# Fixed and Heuristic Baseline Replay: MATH-500 Train n=80

Replay date: 2026-11-14  
Status: completed Train-only development evidence; not held-out effectiveness evidence

## Decision

The MATH-500 replay implementation passes the reconstruction, cost-accounting,
provenance, and leakage checks.

- Fixed endpoint reconstruction: **PASS (720/720 exact)**.
- Frozen depth-first heuristic on Train: **PARETO-DOMINATED**.
- Agreement-stopping breadth baseline at `L=4096`: **PROMISING TRAIN
  CANDIDATE**, but not yet held-out evidence.
- Validation decision: **AUTHORIZED NEXT under the unchanged Train policy
  config and trace schema**.
- Test decision: **DO NOT OPEN**.

## Completed implementation

Source experiment:
`results/qwen3_0_6b_math500_train_n80_contract_v1`

Replay artifact:
`results/phase2/qwen3_0_6b_math500_train_n80_baseline_replay_v1`

The replay module now auto-detects the frozen GSM8K or MATH-500 split and
selects its registered action space. It verifies question and ground-truth
hashes against the frozen split before replay, reconstructs every fixed
configuration from nested paid prefixes, and records all actual generated
tokens and latency values.

Integrity properties:

- 720/720 fixed-profile traces exactly reproduce `config_results.csv`;
- 80 depth-first heuristic traces, 80 depth-only traces, and 240 breadth-only
  traces use only frozen Train problems;
- no Validation or Test outcome is accessed;
- source raw/config/experiment/split hashes and all derived artifact hashes
  are recorded;
- allowed decision features and outcome columns remain separated;
- 10,000-repetition paired bootstrap intervals and exact McNemar tests with
  Holm correction are materialized;
- all 175 repository tests pass after the dataset-aware extension.

## Frozen MATH policy configuration

Inclusive Train prompt-token tertiles are:

- prompt tokens `<=79.3333`: choose `L=1024`;
- `79.3333 <` prompt tokens `<=109.6667`: choose `L=2048`;
- prompt tokens `>109.6667`: choose `L=4096`.

The depth-first breadth rule is unchanged: stop at `k=1` only for a valid,
non-truncated answer; stop at `k=2` only for two matching valid answers;
otherwise acquire samples 3--4.

Observed Train actions:

- selected caps: 27 at `L=1024`, 26 at `L=2048`, and 27 at `L=4096`;
- stopped at `k=1`: 27 problems;
- stopped at `k=2`: 0 problems;
- fell back to `k=4`: 53 problems.

The zero `k=2` stops are an observed consequence of the frozen rule and model
outputs, not a post-hoc reason to alter the rule before Validation.

## Train results

| Policy | Accuracy | Mean actual tokens | Status |
|---|---:|---:|---|
| Fixed `1x1024` | 15.00% | 983.15 | Pareto |
| Fixed `1x2048` | 42.50% | 1,662.46 | Pareto |
| Fixed `1x4096` | 52.50% | 2,567.90 | Pareto |
| Fixed `2x4096` | 57.50% | 5,185.64 | Pareto |
| Fixed `4x4096` | 63.75% | 10,363.16 | Dominated by breadth stopping |
| Input-tertile depth-only | 30.00% | 2,027.78 | Dominated |
| Depth-first validity/agreement | 50.00% | 6,563.63 | Dominated |
| Agreement stopping, `L=4096` | **63.75%** | **8,730.08** | Pareto |

The depth-first heuristic is dominated by fixed `1x4096`: its point accuracy
is 2.5 percentage points lower while its mean actual-token cost is 155.6%
higher. Relative to fixed `2x4096`, it is 7.5 points lower and 26.6% more
expensive. These are Train development comparisons, not held-out claims.

The breadth-only agreement policy at `L=4096` selects `k=2` for 42 problems
and `k=4` for 38. Relative to fixed `4x4096`:

- all 80 per-problem correctness outcomes are identical;
- mean actual tokens decrease from 10,363.16 to 8,730.08;
- mean saving is 1,633.09 tokens, or 15.76%;
- 42/80 problems save tokens and no problem uses more tokens.

This establishes retrospective Train behavior of the deterministic stopping
rule. It does not establish held-out non-inferiority or generalization.

## Interpretation

Completed evidence does not support the current prompt-length-tertile
depth-first heuristic as the primary MATH policy. It does support evaluating
the already-registered agreement-stopping comparator at `L=4096` on
Validation. This result also reinforces the distinction between the broad
depth effect in the fixed grid and the predictability of per-problem depth:
more depth helps in aggregate, but prompt length alone is not an adequate
difficulty allocator in this Train sample.

No learned joint controller is fitted because the sequential label audit did
not meet the 30-positive floor. The joint policy remains a working hypothesis,
not completed evidence.

## Authorized next work

1. Generate the frozen MATH-500 Validation-20 grid with the same model,
   revision, prompt, parser, seed, and action space.
2. Replay it with the byte-identical Train `policy_config.json`; do not refit
   tertiles or stopping rules on Validation.
3. Compare agreement stopping at `L=4096` against fixed `4x4096`, fixed
   `2x4096`, and the unchanged depth-first heuristic using paired outcomes and
   actual-token cost.
4. Use Validation only for the registered policy-selection decision; do not
   alter the parser, labels, or action space after inspecting outcomes without
   a documented amendment.
5. Keep MATH Test-100 unopened until the complete two-dataset policy bundle is
   selected, frozen, and hashed.
