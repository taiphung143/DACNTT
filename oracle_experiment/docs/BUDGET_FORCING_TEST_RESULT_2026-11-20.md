# Maximum-budget force-answer: paired Test-100 result

Date: 2026-11-20

## Evidence status and disclosure

This is the frozen supplementary Test-100 evaluation declared in
`BUDGET_FORCING_TEST_PROTOCOL_2026-11-20.md`. The intervention was selected
after positive Validation-20 results, and the primary standard-thinking
Test-100 results were already known. It is therefore a post-Validation
robustness evaluation, not a pristine preregistered confirmatory study. The
intervention and analysis were nevertheless fixed before any
`force_answer_v2` Test generation, and no Test-dependent tuning was performed.

The primary thesis policy-selection results remain unchanged.

## Integrity audit

For each dataset, the force-answer grid contains 400 unique identities, zero
duplicates, zero generation errors, zero over-cap rows, and zero cache hits.
Pairing matches all 100 problem IDs, model revision, sample seeds, prompt
hashes, parser, temperature, top-p, and `(k,L)` profiles. The GSM8K standard
grid was deterministically replayed with the V4 parser; its generation prompt
is byte-identical to V3 and no standard output was regenerated.

## Paired results

| Dataset | k,L | Standard acc. | Force acc. | Gap | Token saving | Parse failure S/F | Truncation S/F | Standard-only / force-only | Exact p | Holm p |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GSM8K | 1,512 | 42% | 52% | +10 pp | 16.2% | 54.0% / 9.0% | 55.0% / 1.0% | 1 / 11 | 0.00635 | 0.0190 |
| GSM8K | 2,512 | 47% | 54% | +7 pp | 16.4% | 59.0% / 10.5% | 57.5% / 1.5% | 3 / 10 | 0.0923 | 0.1846 |
| GSM8K | 4,512 | 53% | 56% | +3 pp | 16.1% | 58.2% / 10.5% | 56.0% / 1.5% | 4 / 7 | 0.5488 | 0.5488 |
| MATH-500 | 1,1024 | 13% | 42% | +29 pp | 20.2% | 86.0% / 1.0% | 86.0% / 6.0% | 0 / 29 | 3.73e-9 | 7.45e-9 |
| MATH-500 | 2,1024 | 15% | 43% | +28 pp | 20.2% | 86.5% / 1.5% | 86.5% / 6.5% | 0 / 28 | 7.45e-9 | 7.45e-9 |
| MATH-500 | 4,1024 | 17% | 49% | +32 pp | 19.9% | 85.8% / 1.5% | 85.8% / 7.2% | 0 / 32 | 4.66e-10 | 1.40e-9 |

At GSM8K `k=1`, force-answer improves paired accuracy after Holm correction.
The `k=2` and `k=4` point estimates are positive but not significant. All three
MATH-500 improvements are significant after Holm correction. Wilson intervals
and exact unrounded statistics are stored in the comparison CSV.

## Frozen decision

Decision: `SUPPORTED_ACROSS_DATASETS`.

Both datasets show large reductions in the targeted parse/truncation failure,
lower realized token cost, and no negative observed accuracy gap at any
registered `k`. This satisfies the exact descriptive rule declared before Test
generation. The strongest supported conclusion is specific to constrained
hard-cap profiles: forcing a transition to an answer prevents hard-cap
evaluation artifacts and improves the accuracy--cost trade-off for this
Qwen3-0.6B setup.

The result does not establish equivalence at non-significant profiles, does
not show that force-answer is best at larger token caps, and does not erase the
post-Validation selection history. No further Test variant or tuning is
authorized.

## Immutable artifact

`results/phase2/qwen3_0_6b_forceanswer_test_comparison_v1/`

