# Model Migration Amendment: Qwen3-0.6B

## Final Decision

Future characterization, controller training, and confirmatory experiments use
`Qwen/Qwen3-0.6B` at revision
`c1899de289a04d12100db370d81485cdf75e47ca`.

This model choice was made permanent for the core thesis on 2026-11-11. The
frozen operational protocol is now
`PHASE2_PROTOCOL_QWEN3_0_6B_V2.md`; this migration document remains the record
of the feasibility evidence that motivated the decision. Qwen3-1.7B is not a
fallback primary model.

This is the closest smaller model in the same Qwen3 family and preserves the
chat template and thinking-mode interface used by the current pipeline. The
requested exact 0.5B alternative would be Qwen2.5-class rather than Qwen3 and
would introduce a larger methodological change.

## Evidence motivating the change

The completed Qwen3-1.7B MATH-500 development pilot showed useful accuracy
gains through `L=4096`, but 46.7% of trajectories still truncated. A bounded
`L=8192` diagnostic was then attempted on the same 30 problems. It was stopped
for compute feasibility after two complete 8192-token trajectories:

- `math500-test-444`: 8192 tokens, 11.63 minutes, truncated before answer;
- `math500-test-177`: 8192 tokens, 27.10 minutes, truncated before answer.

These two observations are insufficient for an accuracy estimate, but they are
direct system-cost evidence that completing the planned data target with 1.7B
and long caps is infeasible on the available RTX 4060 within the thesis
schedule.

## Scientific boundary

- Existing Qwen3-1.7B raw outputs, tables, paper results, and model-specific
  claims remain unchanged.
- The partial 1.7B `L=8192` run is retained but excluded from aggregate accuracy
  and statistical claims.
- Generation cache entries are revision-keyed; 1.7B outputs cannot be reused as
  0.6B generations.
- Cheapest-correct labels, oracle actions, escalation targets, controller
  coefficients, thresholds, and latency estimates are model-specific and must
  be regenerated for 0.6B.
- Frozen problem selections and parser contracts may be reused because they do
  not contain model outcomes. Results from different models are reported in
  separate strata and are not pooled.

## Initial 0.6B protocol

1. Run a short adapter smoke test to verify the pinned revision, chat template,
   thinking mode, CUDA, and bfloat16.
2. Run a three-problem timing/quality pilot on MATH-500 at `k=1` and
   `L in {1024,2048,4096}` using
   `data/splits/math500_smoke3_v1.json` (SHA-256
   `0330f3bcef72e3d65c1469abfd85217bb71c787ea893b52307770dfe388d5152`).
3. If there are no generation/parser errors, run the frozen 30-problem MATH-500
   development pilot with the same grid.
4. Audit accuracy, valid-answer rate, truncation, actual tokens, and latency.
5. Freeze the 0.6B MATH action space from this evidence. Do not include 8192 by
   default.
6. Regenerate the GSM8K characterization/controller labels required by the
   selected 0.6B action space before fitting any controller.

## Technical verification

The pinned 0.6B snapshot loaded successfully through the project adapter with
CUDA, bfloat16, and thinking mode. A warm 256-token micro-benchmark on the same
prompt and GPU measured 22.26 tokens/s for Qwen3-0.6B and 22.45 tokens/s for
Qwen3-1.7B. This short-context measurement shows no throughput improvement.
The three-problem pilot below therefore evaluates end-to-end feasibility and
output-length behavior separately from raw decoding throughput.

The revised model is intended to improve feasibility. It does not guarantee
faster end-to-end generation, adequate accuracy, or controller learnability.

## Completed three-problem pilot (2026-11-03)

The planned smoke pilot completed at
`results/qwen3_0_6b_math500_smoke3_v1` with 9/9 unique generations, zero cache
hits, zero skipped records, and zero generation errors. The run used the pinned
model and dataset revisions, CUDA, bfloat16, parser `math500_exact_v2`, seed 42,
and the frozen smoke manifest.

| L | Correct | Truncated | Mean generated tokens | Mean latency |
|---:|---:|---:|---:|---:|
| 1024 | 0/3 | 3/3 | 1024.0 | 45.6 s |
| 2048 | 1/3 | 2/3 | 1793.3 | 78.2 s |
| 4096 | 2/3 | 1/3 | 2968.7 | 129.8 s |

The two solved trajectories provide development evidence that additional depth
can help on this model: one problem first became correct at 2048 and another at
4096. The sample is deliberately too small for an accuracy claim; all profile
estimates and paired comparisons are marked `insufficient_sample` by the
analysis pipeline.

On the same three problems, token throughput was not consistently higher than
for 1.7B. At `L=1024`, aggregate throughput was 22.47 tokens/s for 0.6B versus
24.54 tokens/s for 1.7B; at `L=2048`, it was 22.93 versus 24.98 tokens/s. The
0.6B pilot nevertheless had lower end-to-end latency at larger caps because two
trajectories stopped after producing valid answers instead of consuming the
full cap. This is output-length behavior, not evidence that the smaller model
has intrinsically higher decoding throughput.

The technical go criterion is satisfied: the adapter, parser, checkpointing,
and analysis completed without error, and the grid produced non-degenerate
depth behavior. The next authorized development run is therefore the frozen
30-problem MATH-500 pilot at `L in {1024,2048,4096}`. `L=8192` remains excluded.
