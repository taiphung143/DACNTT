# Sequential Label Audit: Qwen3-0.6B GSM8K Train Pilot n=30

Audit date: 2026-11-12  
Status: completed development evidence; not held-out controller evidence

## Decision

The pilot passes the technical gate for sequential-label construction, but it
does **not** pass the data-readiness gate for fitting a learned joint
controller.

- Technical decision: **GO TO CONTROLLED SCALE-UP**.
- Learned-controller decision: **NEED MORE DATA / KEEP RARE STAGES
  HEURISTIC**.
- Held-out Test decision: **DO NOT OPEN**.

This decision follows the pre-registered floor of 30 positive Train examples
for every learned escalation stage. No stage currently meets that floor.

## Completed evidence

Source experiment:
`results/qwen3_0_6b_gsm8k_train_pilot_n30_contract_v3`

Derived artifact:
`results/phase2/qwen3_0_6b_gsm8k_n30_sequential_labels_v1`

The artifact contains:

- 30 frozen-Train problems and no Validation or Test problems;
- 180 depth-transition rows: 30 problems x 2 transitions x 3 lambdas;
- 540 breadth-transition rows: 30 problems x 3 caps x 2 transitions x
  3 lambdas;
- input-only question features for depth decisions;
- only already-paid state features for breadth decisions;
- separate label/outcome columns explicitly forbidden as model inputs;
- hashes of the source raw samples, configuration results, experiment
  manifest, and frozen split manifest.

The normalized realized marginal-utility target is

```text
DeltaU = DeltaCorrect - lambda * DeltaActualGeneratedTokens / 2048
escalate = 1 iff DeltaU > 0
```

with the pre-registered lambda grid `{0.02, 0.05, 0.10}`.

## Observed label balance

Counts below are per stage, not summed across lambdas. The same observed
correctness transition is represented at each lambda, so those rows are
sensitivity settings rather than independent examples.

| Stage | Positive gains | Regressions | No correctness change | Positive rate | Wilson 95% interval | Descriptive n projected for 30 positives |
|---|---:|---:|---:|---:|---:|---:|
| Depth `L512 -> L1024` | 4 | 0 | 26 | 13.3% | 5.3--29.7% | 225 |
| Depth `L1024 -> L2048` | 2 | 0 | 28 | 6.7% | 1.9--21.3% | 450 |
| Breadth `L512, k1 -> k2` | 3 | 0 | 27 | 10.0% | 3.5--25.6% | 300 |
| Breadth `L512, k2 -> k4` | 3 | 0 | 27 | 10.0% | 3.5--25.6% | 300 |
| Breadth `L1024, k1 -> k2` | 2 | 0 | 28 | 6.7% | 1.9--21.3% | 450 |
| Breadth `L1024, k2 -> k4` | 2 | 1 | 27 | 6.7% | 1.9--21.3% | 450 |
| Breadth `L2048, k1 -> k2` | 1 | 0 | 29 | 3.3% | 0.6--16.7% | 900 |
| Breadth `L2048, k2 -> k4` | 1 | 1 | 28 | 3.3% | 0.6--16.7% | 900 |

For all three lambda values, the binary positive counts are identical in this
pilot. A one-step correctness rescue is much larger than the registered token
penalty, while additional compute without a correctness gain has negative
utility. Lambda still changes the continuous utility magnitude.

The final column is only `30 / observed rate`, rounded upward. It is a planning
projection from a small pilot, not an inferential claim or a revised target.

## Interpretation

The completed evidence supports three bounded conclusions:

1. The action grid is non-degenerate: both extra depth and extra samples rescue
   some problems.
2. Positive breadth events are rare, especially at `L=2048`; fitting one
   classifier per stage now would be statistically unjustified.
3. The currently frozen GSM8K Train partition contains only 79 problems. If
   the pilot rates persist, completing that partition will improve the rate
   estimate and enable baseline replay, but will not reach 30 positives for
   any stage.

It does **not** show that a deployable controller can predict the rescued
problems, improve a Pareto frontier, or generalize to Validation, Test, MATH,
or another model.

## Next authorized work

1. Complete the remaining frozen GSM8K Train block to `n=79`, reusing the
   existing generation cache, and rerun this audit.
2. Implement replayable fixed-profile and pre-registered depth-first heuristic
   baselines on development data; do not tune a learned joint controller yet.
3. Prepare a versioned development-data expansion that leaves the existing
   100-problem Test partition untouched. Any split expansion must be reviewed
   and hashed before generation.
4. Expand MATH only after the GSM8K replay and state-table contracts pass.
5. Learn a stage only after it reaches 30 Train positives; otherwise retain a
   fixed/heuristic action or merge/remove the rare transition through a
   versioned protocol amendment.

