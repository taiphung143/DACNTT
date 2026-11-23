# Maximum-budget force-answer: cross-dataset Validation result

Date: 2026-11-20

## Evidence status

This is supplementary development evidence on the frozen Validation-20
partitions of GSM8K and MATH-500. It does not use Test-100 and does not modify
the primary thesis results. The intervention, profiles, answer reserves, and
go/pivot criteria were declared before Validation generation in
`BUDGET_FORCING_CONTROL_PROTOCOL_2026-11-19.md`.

## Integrity checks

Each force-answer grid contains 160 unique generation identities, zero
duplicates, zero generation errors, zero over-cap rows, and zero cache hits.
Every paired comparison uses the same problems, model revision, sample seeds,
byte-identical prompts, answer parser, and `(k,L)` profile. Holm adjustment is
applied separately across the six registered profiles within each dataset.

## GSM8K summary

Across `L={512,1024}` and `k={1,2,4}`, force-answer:

- saves 5.9--16.4% mean generated tokens;
- reduces parse failure from 32.5--51.2% to 3.8--10.0%;
- reduces truncation from 31.2--50.0% to 0.0--2.5%; and
- has non-negative observed accuracy gaps in all profiles: +5 to +10
  percentage points in five profiles and zero at `k=4,L=1024`.

No GSM8K accuracy contrast is significant after Holm correction.

## MATH-500 summary

At the constrained `L=1024` profiles, force-answer:

- raises observed accuracy from 20--30% to 40--55%, a gain of 15--25
  percentage points;
- saves 17.7--18.5% mean generated tokens;
- reduces parse failure from 75.0--76.2% to 0.0--2.5%; and
- reduces truncation from 75.0--76.2% to 2.5--6.2%.

At `L=4096`, observed accuracy increases by 5 percentage points for all three
values of `k`, token saving is 2.6--2.7%, parse failure falls from 30.0--35.0%
to 3.8--10.0%, and truncation falls from 30.0--35.0% to 6.2--10.0%.

The smallest unadjusted MATH-500 p-value is 0.0625 at `k=4,L=1024`; its
within-dataset Holm-adjusted p-value is 0.375. None of the six MATH-500
accuracy contrasts is statistically significant.

## Interpretation and decision

Decision: `VALIDATION_PASS_CONFIRMATORY_PROTOCOL_REQUIRED`.

The control passes the registered usefulness criterion on both datasets. The
primary supported Validation claim is that maximum-budget force-answer
substantially removes parse/truncation failures caused by hard caps while
reducing realized token cost. Accuracy is directionally non-negative in all 12
registered profiles, but the 20-problem confidence is insufficient for a
general accuracy-improvement claim. Failure to reject is not evidence of
equivalence or non-inferiority.

No additional tuning of the suffix, reserve, prompt, parser, or profiles is
permitted from these Validation outcomes. Test-100 remains unopened for this
control. Any Test evaluation requires a separate protocol declared before
generation, must retain `force_answer_v2`, and must report this Validation-based
selection history.

## Immutable artifacts

- Combined comparison:
  `results/phase2/qwen3_0_6b_forceanswer_validation_comparison_v1/`
- GSM8K force grid:
  `results/qwen3_0_6b_gsm8k_validation_n20_forceanswer_v2/`
- MATH-500 force grid:
  `results/qwen3_0_6b_math500_validation_n20_forceanswer_v2/`
- GSM8K standard comparator:
  `results/qwen3_0_6b_gsm8k_validation_n20_contract_v3_parser_v4/`
- MATH-500 standard comparator:
  `results/qwen3_0_6b_math500_validation_n20_contract_v1/`

