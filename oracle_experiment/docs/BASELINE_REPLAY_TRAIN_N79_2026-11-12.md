# Fixed and Heuristic Baseline Replay: GSM8K Train n=79

Replay date: 2026-11-12  
Status: completed Train-only development evidence; not held-out effectiveness evidence

## Completed implementation

The replay module now reconstructs all fixed profiles and the pre-registered
depth-first heuristic directly from the nested raw sample pool. It charges
every generated token and latency value from every sample acquired by the
policy.

Artifact:
`results/phase2/qwen3_0_6b_gsm8k_n79_baseline_replay_v2`

Integrity properties:

- 711/711 fixed-profile endpoints exactly reproduce `config_results.csv`;
- 79 heuristic traces use only frozen Train problems;
- no Validation or Test outcomes are accessed;
- feature availability is separated from outcome columns;
- source raw/config/manifest/split hashes are recorded;
- Validation replay is required by code to load the frozen Train
  `policy_config.json`; it cannot refit tertiles on Validation;
- 10,000-repetition paired bootstrap intervals and exact McNemar tests with
  Holm correction are materialized.

## Frozen heuristic

Train prompt-token tertiles use the inclusive quantile method:

- prompt tokens `<=117`: choose `L=512`;
- `117 <` prompt tokens `<=132`: choose `L=1024`;
- prompt tokens `>132`: choose `L=2048`.

After the first paid sample, stop only for a valid non-truncated final answer.
After two paid samples, stop only for two matching valid answers. Otherwise
acquire samples 3--4 and apply valid-only majority vote.

Observed Train actions:

- selected caps: 27 at `L=512`, 26 at `L=1024`, and 26 at `L=2048`;
- stopped at `k=1`: 57 problems;
- stopped at `k=2`: 0 problems;
- fell back to `k=4`: 22 problems.

The absence of `k=2` stops is an observed behavior of the frozen rule, not a
post-hoc reason to change it before Validation. It shows that the heuristic is
coarse and that the current first-stage validity rule usually makes the second
stage either unnecessary or unable to establish agreement.

## Train results

The heuristic obtains:

- accuracy: 60/79 = 75.95%;
- mean actual generated tokens: 1,307.10;
- mean allocated token budget: 2,022.08;
- mean summed latency: 51,798.5 ms;
- valid final-answer rate: 92.41%.

It is on the descriptive Train Pareto frontier together with fixed `1x512`,
`1x1024`, `1x2048`, and `4x2048`.

Key paired comparisons:

| Fixed comparator | Accuracy difference, heuristic - fixed | Bootstrap 95% interval | Mean token change | Bootstrap 95% interval | Interpretation |
|---|---:|---:|---:|---:|---|
| `2x1024` | +5.06 pp | -2.53 to +12.66 pp | +93.37 (+7.69%) | -194.05 to +427.70 | matched-cost comparison; inconclusive |
| `2x2048` | 0.00 pp | -7.59 to +7.59 pp | -246.72 (-15.88%) | -474.33 to +7.19 | equal point accuracy and lower mean cost; uncertainty still crosses zero for token difference |
| `4x2048` | -2.53 pp | -8.86 to +3.80 pp | -1,751.67 (-57.27%) | -2,050.71 to -1,479.89 | large cost reduction, but accuracy non-inferiority is not established |

After Holm correction, all heuristic-versus-fixed accuracy comparisons remain
inconclusive. The Train point estimates are promising baseline-development
evidence, not proof of superiority or non-inferiority.

## Decision and next authorized step

Update: the authorized 20-problem Validation grid and frozen replay were
completed on 2026-11-12. See
`BASELINE_REPLAY_VALIDATION_N20_2026-11-12.md`. Test remains unopened.

Fixed and heuristic replay is operational. The next authorized experiment is
the 20-problem frozen Validation grid under the unchanged model, prompt,
parser, seed, and action space. Replay must use the Train policy configuration
and its hash; Validation may assess the frozen heuristic but may not redefine
its tertiles or stopping rules.

The learned joint controller remains blocked because no sequential stage has
30 positive Train examples. Test remains unopened.
