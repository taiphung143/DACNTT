# Frozen GSM8K Test Policy Evaluation

Evaluation date: 2026-11-13  
Status: completed one-shot held-out GSM8K evaluation; no Test-dependent retuning

## Confirmatory protocol

The one-time Test grid used 100 frozen GSM8K problems, Qwen3-0.6B revision
`c1899de289a04d12100db370d81485cdf75e47ca`, seed 42, prompt
`gsm8k_cot_v3`, parser `gsm8k_numeric_v3`, and the frozen action space
`k in {1,2,4}`, `L in {512,1024,2048}`. It produced all 1,200 expected
generation records with zero generation errors, missing keys, unexpected keys,
or duplicates.

The replay used the pre-Test freeze manifest with SHA-256
`02dc05c1751bac5311fc2565a52dff645503e7f34ef4888e161ecde9ec306aff`
and the byte-identical policy configuration with SHA-256
`4cdf093321f95c5c0f9c621b52b4001af088063a14f51eb123949b1d9a629111`.
All 900 fixed endpoints were reconstructed exactly. The replay manifest
SHA-256 is
`603b74364e36ba5355d36312f90528cda3ebfc17f3690a7e0f9bfb8103b9dafd`.

## Completed Test evidence

| Policy | Correct | Accuracy | Mean actual tokens | Test frontier |
|---|---:|---:|---:|---|
| Frozen selected breadth stopping, `L=1024` | 76/100 | 76% | 1,994.52 | non-dominated |
| Joint depth-first heuristic | 70/100 | 70% | 1,449.46 | non-dominated |
| Depth-only input-tertile, `k=1` | 61/100 | 61% | 673.67 | dominated |
| Breadth stopping, `L=2048` | 76/100 | 76% | 2,455.01 | dominated |
| Fixed `k=2,L=2048` | 71/100 | 71% | 1,603.00 | non-dominated |
| Fixed `k=4,L=1024` | 76/100 | 76% | 2,535.17 | dominated |
| Fixed `k=4,L=2048` | 76/100 | 76% | 3,240.74 | dominated |

The frozen selected policy stopped at `k=2` on 54 problems and used `k=4`
on 46 problems. Relative to fixed `k=4,L=1024`, it produced the same
correct/incorrect outcome on every one of the 100 problems while using fewer
tokens on 54 and equal tokens on 46. Mean token use fell by 540.65 tokens per
problem, or 21.3%, with no observed accuracy loss. This is the clearest
confirmatory efficiency result.

Relative to the joint heuristic, the selected policy gained 6 percentage
points of accuracy but used 545.06 more tokens per problem (37.6% relative to
the joint cost). The paired correctness discordances were seven problems won
only by the selected policy and one won only by the joint policy. The
two-sided exact McNemar result is `p=0.0703`; it is inconclusive at 0.05 and
also inconclusive after the existing 13-comparison Holm correction. Therefore
the Test data do not support a statistically significant accuracy-superiority
claim over the joint heuristic.

The Validation observation that the selected policy and joint heuristic had
equal accuracy with a small cost advantage for the selected policy did not
replicate. On Test, the selected policy is more accurate at higher cost. Both
remain non-dominated, and the pre-Test selection must not be reopened.

## Replay enablement amendment

At freeze time, `policy_replay.py` intentionally blocked all Test access. Its
frozen SHA-256 was
`2bf71341fe04902ddeddc35e74e936c953e0a2e2d0fb6c7aec867b66cfadf93f`.
After Test generation completed, the access gate was extended to require both
the frozen policy configuration and the pre-Test freeze manifest. No depth
mapping, breadth stopping rule, aggregation rule, cost definition, bootstrap,
or accuracy test was changed. The execution SHA-256 is
`6caea58e75047490e5930d740a43e6fa478a8d5d7670758c111cf7788c4cf619`;
both hashes are recorded in the replay manifest. The complete software suite
passes 165 tests.

## Scientific conclusion and boundaries

The completed GSM8K evidence supports adaptive breadth stopping at fixed
`L=1024` as a practical efficiency improvement over its fixed-`k=4`
counterpart for this model, dataset, and seed. It does not establish that the
tested joint heuristic is inferior: the joint policy occupies a lower-cost,
lower-accuracy Pareto point, and their paired accuracy difference is
inconclusive.

This is a negative result for the proposed `GO JOINT` development hypothesis,
not evidence against all joint breadth--depth methods. No learned joint
controller was fitted because the Train data lacked enough positive events.
Generalization to MATH-500, a second model, and additional stochastic seeds
remains future evaluation and must be reported separately from this completed
GSM8K result.
