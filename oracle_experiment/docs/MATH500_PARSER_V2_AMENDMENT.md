# MATH-500 Parser v2 Amendment

## Status and reason

This is a versioned development-protocol correction made after auditing the
completed 30-problem depth pilot. It does not change the research questions,
model, prompt, decoding configuration, selected problems, generation seeds, or
raw model outputs.

The audit found two deterministic reference-answer normalization defects:

- the base annotation in `204_5` was interpreted as another digit, producing
  `2045`;
- the numeric list `3, 5, 7` was collapsed into the scalar `357`.

Both defects exceed the pre-registered parser-audit tolerance and therefore
must be corrected before scaling MATH-500 experiments.

## Versioned changes

- Current parser: `math500_exact_v2`.
- Frozen selection manifest: `data/splits/math500_pilot_v2.json`.
- Manifest SHA-256:
  `c9ddee97e3755087b34293b77ff467794a85018a6bf5eb872fb579ee3487ffcc`.
- The v2 manifest preserves the same 30 source indices, question hashes, and
  raw-answer hashes as v1. Only the parser identity and two canonical ground
  truths change.
- Numeric base suffixes such as `204_5` and `204_{5}` canonicalize to the digit
  sequence `204` when the digits are valid in the stated base.
- Explicit comma-separated numeric lists canonicalize to a comma-separated
  list. Conventional unspaced grouped decimals such as `1,234` remain scalar
  numbers.

These are targeted presentation corrections, not unrestricted symbolic
equivalence.

## Reprocessing contract

The original generation artifact remains unchanged at:

`results/qwen3_1_7b_math500_depth_pilot_v2/raw_samples.jsonl`

Its SHA-256 is:

`60149d882dcf204b0fcb0758408fb26a89ae02e31f753276dcd2618b9478a98f`.

The 90 records were deterministically reprocessed without model inference. The
derived artifacts are stored under:

`results/qwen3_1_7b_math500_depth_pilot_v2_parser_v2/`

Audit results:

- 90 source and 90 derived records;
- zero missing identities and zero generation-field differences;
- all records use `math500_exact_v2`;
- six stored ground-truth fields changed, corresponding to the two affected
  problems at three token caps;
- exactly one correctness label changed: `math500-test-137` at `L=4096`, from
  incorrect to correct.

## Corrected completed evidence

| Token cap | Accuracy | Valid-answer rate | Truncation rate |
|---:|---:|---:|---:|
| 1024 | 2/30 = 6.7% | 6.7% | 93.3% |
| 2048 | 8/30 = 26.7% | 26.7% | 73.3% |
| 4096 | 16/30 = 53.3% | 53.3% | 46.7% |

The paired `2048 -> 4096` comparison has eight improvements, zero regressions,
an accuracy difference of +26.7 percentage points, exact McNemar
`p=0.0078125`, and Holm-adjusted `p=0.015625` within the planned depth family.
This remains development evidence from 30 problems, not held-out confirmation.

## Proposed next evaluation

Because 14/30 trajectories still hit the 4096-token cap, a bounded `k=1`,
`L=8192` run on the same development pilot is proposed to measure remaining
right-censoring before the MATH action space is frozen. This run has not yet
been performed and must use the v2 parser and v2 manifest.
