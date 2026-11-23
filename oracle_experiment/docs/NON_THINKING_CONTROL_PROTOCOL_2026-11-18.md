# Qwen3-0.6B non-thinking control protocol

Date declared: 2026-11-18, before generation or outcome inspection.

## Purpose and evidence status

This supplementary control tests whether the observed cost/accuracy behavior
depends on Qwen3's thinking mode. It does not redefine the frozen research
question, replace the primary Test-100 results, or reopen the failed learned
controller gate.

## Frozen configuration

- Model: `Qwen/Qwen3-0.6B`, revision
  `c1899de289a04d12100db370d81485cdf75e47ca`.
- Decoding: native chat-template non-thinking mode
  (`enable_thinking=false`), temperature 0.7, top-p 0.95, seed 42.
- Problems: existing frozen Phase-2 partitions; no new item selection.
- Breadth: shared sample pool with `k={1,2,4}`.
- Depth: one dataset-specific high cap only: GSM8K `L=2048`, MATH-500
  `L=4096`.
- Aggregation, parser, prompt, and cost accounting remain identical to the
  corresponding primary experiment.
- Generation artifacts use new experiment IDs and cache identities; existing
  thinking-mode artifacts are immutable.

## Staged execution

1. GPU smoke test on the first three frozen Train items of each dataset.
2. Proceed only if all expected records exist, no generation error occurs,
   manifests record `enable_thinking=false`, and parsing/analysis completes.
3. Run the full existing Validation-20 partitions once. Test-100 remains
   unopened for this control unless a separate pre-result confirmatory rule is
   declared.

For one high-L shared pool, each three-item smoke run requires 12 unique
generations and each Validation-20 run requires 80 unique generations.

## Evaluation

Report fixed `k=1`, `k=2`, and `k=4` accuracy, mean actual generated tokens,
truncation rate, parse-valid rate, and paired differences against the matching
thinking-mode high-L policies on the same problem IDs. Validation results are
supplementary development evidence. No threshold or controller training is
part of this control.

## Train-smoke parser amendment (before Validation)

The first GSM8K Train-3 smoke produced all 12 expected records with zero
generation errors, zero truncations, and `enable_thinking=false`. Two outputs
contained the correct explicit conclusion but placed explanatory numbers on
the same physical line as `Final answer:`, which the V3 unique-number rule
rejected. Before any Validation generation, the control therefore adopts
`gsm8k_cot_v4` / `gsm8k_numeric_v4`. The prompt text is byte-identical to V3.
The parser preserves all V3 decisions and, only after V3 fails, inspects the
suffix after the last `Final answer:` marker. It accepts one numeric candidate
there, or the numeric right-hand side of a terminal equality. It does not use
an unmarked last-number fallback. The existing Train-3 generations are replayed
under V4; they are not regenerated or selected by correctness.

## Execution record

- GSM8K Train-3 smoke, parser-V4 derivative: 12/12 unique generations,
  zero generation errors, zero truncations, and 12/12 parse-valid samples.
- MATH-500 Train-3 clean smoke: 12/12 unique generations, zero generation
  errors, zero truncations, and 12/12 parse-valid samples. The earlier V1
  directory is excluded because an OS-level timeout left a child process alive
  and a concurrent resume produced duplicate identities; only
  `qwen3_0_6b_math500_train_smoke3_nonthinking_highL_v2_clean` is valid.
- GSM8K Validation-20: complete, 80/80 unique generations, zero generation
  errors, zero truncations. Fixed k=1, k=2, and k=4 each achieve 1/20 accuracy;
  mean per-sample generation is 35.91 tokens. This is completed supplementary
  development evidence and strongly disfavors non-thinking as a competitive
  GSM8K accuracy comparator under the frozen prompt.
- MATH-500 Validation-20 completed after a checkpointed resume following an
  unexpected machine shutdown: 80/80 unique generations, zero generation
  errors, zero truncations, and 80/80 parse-valid samples. No duplicate key was
  introduced by the resume.
- The paired cross-mode result is recorded in
  `docs/NON_THINKING_VALIDATION_RESULT_2026-11-19.md`. Non-thinking saves
  78.03--96.83% of tokens but has lower accuracy in all six dataset/k profiles;
  it is therefore not promoted to Test-100.

After the final paired-comparison module and tests were added, the complete
automated suite reports 192 passed and 0 failed.
