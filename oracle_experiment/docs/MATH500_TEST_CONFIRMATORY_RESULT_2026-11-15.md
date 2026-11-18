# MATH-500 Test-100 Confirmatory Result

Date: 2026-11-15

## Evidence status

This document reports completed held-out Test evidence. The evaluated policies, action space, split, model revision, prompt, parser, and selection rule were frozen before Test access. No policy was fitted or retuned using Test outcomes.

## Execution integrity

- Model: `Qwen/Qwen3-0.6B`, revision `c1899de289a04d12100db370d81485cdf75e47ca`
- Dataset: MATH-500, frozen Test partition of 100 problems
- Frozen split SHA-256: `60211c797b68c9c24f097288cd4300ec63536b539eac89bd368ff68fff8b3459`
- Policy-freeze SHA-256: `79163f652a451af43380fab32a8f1ef3c4885c9f7fbebef014f5ecce595974b4`
- Generation result: 1,200/1,200 unique generations, 0 failures, 0 missing or extra Test IDs
- Fixed configuration reconstruction: 900/900 rows, exact
- Frozen replay result: 14/14 unique policy summaries and 13/13 registered joint-heuristic comparisons
- All replay artifact hashes match `replay_manifest.json`

## Confirmatory results

| Policy | Accuracy | Mean actual generated tokens | Mean latency (ms) | Test Pareto status |
|---|---:|---:|---:|---|
| `fixed_k1_L1024` | 0.13 | 984.67 | 35,866.35 | nondominated |
| `fixed_k1_L2048` | 0.40 | 1,699.27 | 60,505.88 | nondominated |
| `fixed_k1_L4096` | 0.58 | 2,600.28 | 97,994.66 | nondominated |
| `fixed_k2_L4096` (pre-Test selected) | 0.66 | 5,141.50 | 193,698.88 | nondominated |
| `depth_first_tertile_validity_agreement_v1` (joint hypothesis) | 0.36 | 5,788.81 | 213,978.13 | dominated |
| `breadth_only_agreement_L4096_v1` | 0.73 | 8,191.12 | 310,189.65 | nondominated |
| `fixed_k4_L4096` | 0.73 | 10,233.17 | 385,062.41 | dominated |

The full 14-policy table is in `results/phase2/qwen3_0_6b_math500_test_n100_baseline_replay_v1/policy_summary.csv`.

## Statistical interpretation

The frozen joint heuristic achieved 36% accuracy. Against the pre-Test selected `fixed_k2_L4096`, its paired accuracy difference was -30 percentage points (two-sided exact McNemar Holm-adjusted p = 2.50e-6) while using 12.6% more tokens. It was also point-dominated by `fixed_k1_L4096`, which achieved 58% accuracy using 2,600.28 tokens. Therefore, the completed Test evidence does not support the joint depth-and-breadth heuristic.

The breadth-only stopping policy at L=4096 achieved the same 73% accuracy as `fixed_k4_L4096` while reducing mean actual generated tokens by 19.96% and mean latency by 19.44%. This is positive evidence for adaptive breadth stopping at high depth on MATH-500. It does not establish a successful joint controller and must not be presented as the pre-Test selected primary policy.

The pre-Test selected MATH policy `fixed_k2_L4096` achieved 66%, close to its Validation estimate of 65%. It remains the selection-rule outcome and must be reported as such; `breadth_only_agreement_L4096_v1` is a separately registered comparator whose stronger Test accuracy is reported without post-Test reselection.

## Decision

- Joint-controller claim: not supported on MATH-500 Test-100.
- Cross-dataset joint `GO`: remains not met.
- Registered pivot: supported. Report dataset-specific fixed baselines as the primary reliable policies.
- Secondary result: report the MATH-500 breadth-only L=4096 efficiency gain as a registered comparator result.
- Prohibited next action: no Test-dependent policy retuning or replacement of the frozen selected policy.

## Remaining work

The empirical run is complete. Remaining work is reporting: integrate the frozen protocol, full Test table, paired inference, limitations, and the distinction between the selected fixed policy and the breadth-only comparator into the paper. Any new learned controller must be treated as future work or evaluated on a new untouched split.
