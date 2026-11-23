# Maximum-budget force-answer: GSM8K Validation-20 result

Date: 2026-11-19

## Evidence status

This is supplementary development evidence on the frozen GSM8K Validation-20
partition. It does not use Test-100 and does not modify the primary thesis
claims. The intervention and go/pivot criteria were declared in
`BUDGET_FORCING_CONTROL_PROTOCOL_2026-11-19.md` before Validation generation.

## Pairing and audit

The comparison pairs standard thinking generation with `force_answer_v2` on
the same 20 problems, model revision, sample seeds, byte-identical prompts,
GSM8K V4 parser, and `(k,L)` profiles. The standard source is the immutable V3
generation grid replayed with the V4 parser; V3 and V4 deliberately use the
same generation prompt. All 160 force-answer generation identities are unique,
with zero generation errors, zero over-cap rows, and no cache hits. Test-100 was
not accessed.

## Paired results

| k | L | Standard accuracy | Force accuracy | Gap | Standard tokens | Force tokens | Token saving | Parse failure S/F | Truncation S/F | Exact p | Holm p |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 512 | 10/20 | 12/20 | +10 pp | 462.25 | 386.40 | 16.4% | 50.0% / 10.0% | 50.0% / 0.0% | 0.625 | 1.0 |
| 2 | 512 | 11/20 | 12/20 | +5 pp | 901.40 | 760.50 | 15.6% | 50.0% / 10.0% | 47.5% / 2.5% | 1.0 | 1.0 |
| 4 | 512 | 11/20 | 12/20 | +5 pp | 1792.70 | 1515.20 | 15.5% | 51.2% / 6.2% | 50.0% / 1.2% | 1.0 | 1.0 |
| 1 | 1024 | 12/20 | 13/20 | +5 pp | 683.35 | 636.80 | 6.8% | 40.0% / 5.0% | 40.0% / 0.0% | 1.0 | 1.0 |
| 2 | 1024 | 13/20 | 14/20 | +5 pp | 1318.15 | 1230.05 | 6.7% | 40.0% / 5.0% | 37.5% / 0.0% | 1.0 | 1.0 |
| 4 | 1024 | 15/20 | 15/20 | 0 pp | 2574.90 | 2424.20 | 5.9% | 32.5% / 3.8% | 31.2% / 0.0% | 1.0 | 1.0 |

No accuracy difference is statistically significant after Holm correction.
With only 20 paired problems, this absence of significance is not evidence of
equivalence. The directional accuracy result is non-negative in all six
profiles, while the large reductions in parse failure and truncation directly
address the registered low-budget failure mode.

## Registered decision

Decision: `GO_TO_MATH500_VALIDATION`.

The control passes the pre-declared usefulness gate on GSM8K: at `L=512` it
reduces mean generated tokens by 15.5--16.4%, reduces truncation from
47.5--50.0% to 0.0--2.5%, and improves observed paired accuracy by 5--10
percentage points. This authorizes the already-declared MATH-500 Validation-20
run at `L={1024,4096}` with a 256-token answer reserve. It does not authorize
Test-100.

## Immutable artifacts

- Comparison: `results/phase2/qwen3_0_6b_gsm8k_forceanswer_validation_comparison_v1/`
- Standard source: `results/qwen3_0_6b_gsm8k_validation_n20_contract_v3_parser_v4/`
- Force source: `results/qwen3_0_6b_gsm8k_validation_n20_forceanswer_v2/`

