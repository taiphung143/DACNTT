# Maximum-budget force-answer: frozen Test-100 protocol

Date declared: 2026-11-20, before any Test-100 generation using
`force_answer_v2`.

## Status and selection disclosure

This is a supplementary, post-Validation evaluation of the decoding control.
The intervention was selected after positive GSM8K and MATH-500 Validation-20
results. In addition, the standard-thinking Test-100 results were already known
from the primary thesis experiment. Therefore this evaluation is not presented
as a pristine preregistered confirmatory study. It is a frozen, paired robustness
evaluation whose intervention and analysis are fixed before its own Test
generation.

The primary thesis Test-100 results remain unchanged. This protocol adds one
decoding control and does not reopen controller selection, redefine the Research
Question, or authorize additional Test-driven tuning.

## Frozen intervention

- Model: `Qwen/Qwen3-0.6B`, revision
  `c1899de289a04d12100db370d81485cdf75e47ca`.
- Decoding: `force_answer_v2`; no suffix, reserve, prompt, parser, seed, or
  sampling change is permitted.
- Sampling: temperature 0.7, top-p 0.95, global seed 42, one repetition, and
  the existing deterministic nested sample seeds.
- Breadth profiles: `k={1,2,4}` using one shared four-sample pool.
- GSM8K: frozen Test-100, `L=512`, answer reserve `R=128`, V4 parser. The V4
  generation prompt is byte-identical to the existing V3 prompt.
- MATH-500: frozen Test-100, `L=1024`, answer reserve `R=256`, exact V2 parser.
- Each dataset requires 400 unique force-answer generations. Existing standard
  generations are reused only as paired comparators; they are never regenerated.

Only the constrained profile is evaluated because the reviewer-facing concern
is the hard-cap artifact. The broader two-length sweep has already been
completed on Validation and is not repeated on Test.

## Comparator integrity

- GSM8K standard comparator:
  `qwen3_0_6b_gsm8k_test_n100_contract_v3`, deterministically replayed under
  `gsm8k_numeric_v4` without new model generation.
- MATH-500 standard comparator:
  `qwen3_0_6b_math500_test_n100_contract_v1`.
- Pairing requires identical problem IDs, model revision, problem-level prompt
  hashes, sample seeds, temperature, top-p, and parser.
- Every force grid must have 400 unique identities, zero generation errors,
  zero over-cap rows, an immutable manifest, and no standard-generation cache
  reuse.

## Analysis fixed before generation

For each dataset and each `k`, report:

1. exact accuracy and Wilson 95% intervals;
2. paired accuracy gap, discordant counts, two-sided exact McNemar p-value, and
   Holm correction across `k={1,2,4}` within the dataset;
3. mean actual generated tokens and relative token saving;
4. parse-failure, truncation, and forced-transition rates; and
5. all generation errors, duplicates, cache hits, and cap violations.

Failure to reject is not equivalence or non-inferiority. A positive point
estimate is not called an accuracy improvement unless the paired comparison is
significant after Holm correction. The descriptive robustness conclusion is
classified as:

- `SUPPORTED_ACROSS_DATASETS` only if both datasets reduce the targeted
  parse/truncation failure and have no negative observed accuracy gap at any
  registered `k`;
- `MIXED` if effects differ by dataset or any accuracy gap is negative; or
- `NOT_SUPPORTED` if the control fails to reduce the targeted failures on both
  datasets.

## Execution order and stopping

Run GSM8K first and MATH-500 second for operational safety. MATH-500 must still
run regardless of the scientific direction of GSM8K; stopping is allowed only
for a technical integrity failure. No Test output may be used to alter
`force_answer_v2`, reserves, parsers, prompts, profiles, or decision rules. No
additional Test variant is authorized by this protocol.

## Completed execution record

Both Test grids completed with 400/400 unique generation identities, zero
duplicates, zero generation errors, zero over-cap rows, and zero cache hits.
The paired integrity audit passed for both datasets.

The frozen decision is `SUPPORTED_ACROSS_DATASETS`: all six observed accuracy
gaps are non-negative, token cost falls by 16.1--16.4% on GSM8K and 19.9--20.2%
on MATH-500, and the targeted parse/truncation failures fall sharply. GSM8K
`k=1` and all three MATH-500 accuracy gains are significant after within-dataset
Holm correction. Full results and limitations are recorded in
`docs/BUDGET_FORCING_TEST_RESULT_2026-11-20.md`.
