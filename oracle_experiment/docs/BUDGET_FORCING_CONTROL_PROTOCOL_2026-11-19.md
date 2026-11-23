# Qwen3-0.6B maximum-budget forcing control protocol

Date declared: 2026-11-19, before any generation with this decoding strategy.

## Purpose and evidence status

This supplementary control tests whether hard token caps understate accuracy
because a response is cut before Qwen3 can leave its thinking block and state
an answer. It addresses the maximum-budget branch of budget forcing described
by s1: when the thinking allowance is exhausted, append the end-of-thinking
delimiter and allow the model to produce its current best answer. It does not
extend short traces with `Wait`, train a controller, reopen the primary
Test-100 evaluation, or redefine the thesis Research Question.

The installed Qwen3-0.6B chat template exposes `enable_thinking` only. Passing
`thinking_budget` has no effect on the rendered prompt, so a native Qwen3
thinking-budget control is unavailable for this pinned checkpoint and
Transformers path. This is recorded as a compatibility finding, not a negative
model result.

## Frozen intervention

- Model: `Qwen/Qwen3-0.6B`, revision
  `c1899de289a04d12100db370d81485cdf75e47ca`.
- Generation remains in thinking mode with temperature 0.7, top-p 0.95, seed
  42, the existing prompts, parsers, problem IDs, and nested `k={1,2,4}` pool.
- Total model-generated tokens remain bounded by the original cap `L`.
- The first phase receives `L-R` generated tokens. If it ends normally, the
  output is unchanged. If it reaches `L-R`, generation continues for at most
  `R` answer tokens. When `</think>` is absent, the pipeline injects exactly
  `</think>\n\n` before the continuation.
- Injected control tokens are parser-visible but are not counted as
  model-generated tokens. Their count and whether the forced transition was
  applied are recorded in every raw row.
- `decoding_strategy` and `answer_reserve_tokens` are part of the experiment
  manifest and global cache identity, preventing reuse of standard generations.

## Staged execution

1. GSM8K Train-3 smoke: `L=512`, `R=128`, 12 unique generations.
2. MATH-500 Train-3 smoke: `L=1024`, `R=256`, 12 unique generations.
3. Proceed only if each smoke has all 12 identities, zero generation errors,
   immutable manifests with the correct strategy/reserve, and successful
   parser/analysis output. At least one low-cap row should exercise the forced
   transition; otherwise the implementation path has not been tested.
4. If both smokes pass, run frozen Validation-20 only:
   - GSM8K: `L={512,1024}`, `R=128`;
   - MATH-500: `L={1024,4096}`, `R=256`.
5. Test-100 remains unopened for this control regardless of Validation outcome
   unless a separate confirmatory protocol is declared before Test access.

## Evaluation

For each `(dataset,k,L)`, compare the forcing control with the matching
standard-thinking policy on the same problems and sample seeds. Report exact
accuracy, mean actual generated tokens, parse-valid rate, truncation rate,
forced-transition rate, mean injected control tokens, paired McNemar tests,
and Holm correction within each dataset. Failure to reject is not evidence of
equivalence or non-inferiority.

## Go/pivot criteria

- Go to Validation only after both smoke gates pass.
- Retain the control as useful if it materially reduces unparseable truncated
  outputs or improves paired accuracy at a low cap without exceeding `L`.
- If it only changes formatting without improving correctness, report that
  negative result and do not promote it to Test.
- If forced rows remain parser-invalid because the model cannot state an answer
  within `R`, inspect raw outputs on Train only. Any change to `R`, prompt, or
  parser requires a new experiment ID and a protocol amendment before
  Validation.

## Train-smoke amendment 1: explicit answer cue

The first MATH-500 Train-3 smoke
(`qwen3_0_6b_math500_train_smoke3_forceanswer_L1024_R256_v1`) completed all
12 unique generations with zero generation errors and zero over-cap rows, and
all 12 rows exercised the forced transition. However, only 4/12 rows were
parse-valid; the other eight consumed the full 256-token answer reserve and
remained truncated. Raw Train outputs showed that after the injected
`</think>` delimiter, Qwen restarted a long answer explanation instead of
stating the requested boxed answer.

Before any Validation generation, the forced suffix is therefore amended from
`</think>\n\n` to `</think>\n\nFinal answer:`. This follows the explicit
answer-cue option in the s1 inference recipe for early exit. It does not insert
an answer or use ground truth. The reserve, prompts, parsers, sampling settings,
problem IDs, and total cap remain unchanged. Both dataset smokes must be rerun
under new `v2` experiment IDs; the `v1` artifacts remain immutable engineering
evidence and are excluded from Validation comparison.

## Train-smoke amendment 2: intervention-version cache identity

The attempted GSM8K `v2` rerun produced 12 cache hits from the earlier suffix
because the cache identity recorded strategy and reserve but not the
implementation version. No new model generation occurred, so this artifact is
excluded from evidence. Before Validation, `decoding_strategy_version` is
added to manifests, raw rows, resume validation, and cache identity.
Historical force-answer cache rows without this field are interpreted as
`force_answer_v1`; the amended suffix uses `force_answer_v2`. Clean reruns use
new `v3` experiment IDs. Standard historical cache rows remain backward
compatible as `standard_v1`.

## Completed smoke-gate record

The clean `v3` smokes use `decoding_strategy_version=force_answer_v2` and
contain no cache reuse from either earlier engineering attempt.

- GSM8K Train-3, `L=512`, `R=128`: 12/12 unique rows, zero generation
  errors, zero over-cap rows, 10/12 forced transitions, 8/12 injected suffixes,
  11/12 parse-valid rows, and zero rows ending by length truncation. The one
  parser rejection contains several numbers after the explicit marker; the
  parser is deliberately not relaxed based on this favorable Train output.
- MATH-500 Train-3, `L=1024`, `R=256`: 12/12 unique rows, zero generation
  errors, zero over-cap rows, 12/12 forced transitions, 11/12 injected suffixes,
  12/12 parse-valid rows, and zero rows ending by length truncation. Relative
  to the delimiter-only engineering smoke, parse validity improves from 4/12
  to 12/12, truncation falls from 8/12 to 0/12, mean generated tokens fall from
  971.50 to 789.08, and mean latency falls from 43.04 to 35.43 seconds.

Both technical gates pass. These Train-3 figures validate implementation only;
they are not an accuracy result and must not be promoted to the paper's claims.
The next authorized evaluation is frozen Validation-20 under the staged
configuration above.

## GSM8K Validation-20 execution record

The frozen GSM8K run
`qwen3_0_6b_gsm8k_validation_n20_forceanswer_v2` completed all 160 unique
generation identities with zero generation errors, zero over-cap rows, and no
cache hits. Its paired comparator is the immutable standard-thinking V3 grid
replayed under the V4 parser. The V3 and V4 generation prompts are
byte-identical, and problem IDs, sample seeds, prompt hashes, model revision,
and parser all match.

Across the six registered `(k,L)` profiles, force-answer saves 5.9--16.4% mean
generated tokens, reduces parse failure from 32.5--51.2% to 3.8--10.0%, and
reduces truncation from 31.2--50.0% to 0.0--2.5%. Observed accuracy is never
lower: the paired gap is +5 to +10 percentage points in five profiles and zero
at `k=4,L=1024`. None of the accuracy differences is significant after Holm
correction on 20 problems; this is not treated as evidence of equivalence.

Decision: `GO_TO_MATH500_VALIDATION`. The registered GSM8K usefulness gate is
met because the intervention materially reduces the targeted low-cap
parse/truncation failures while preserving or improving observed accuracy and
reducing generated-token cost. This authorizes MATH-500 Validation-20 only,
not Test-100. Full evidence is recorded in
`docs/BUDGET_FORCING_GSM8K_VALIDATION_RESULT_2026-11-19.md`.

## MATH-500 Validation-20 execution record

The frozen MATH-500 run
`qwen3_0_6b_math500_validation_n20_forceanswer_v2` completed all 160 unique
generation identities with zero duplicates, zero generation errors, zero
over-cap rows, and no cache hits. All paired identities, sample seeds, prompt
hashes, model revision, and parser match the standard-thinking comparator.

At `L=1024`, force-answer improves observed accuracy by 15--25 percentage
points, saves 17.7--18.5% tokens, reduces parse failure from 75.0--76.2% to
0.0--2.5%, and reduces truncation from 75.0--76.2% to 2.5--6.2%. At `L=4096`,
the observed accuracy gap is +5 percentage points for each `k`, with smaller
token savings and continued parse/truncation reductions. No accuracy contrast
is significant after within-dataset Holm correction on 20 problems.

Final Validation decision: `VALIDATION_PASS_CONFIRMATORY_PROTOCOL_REQUIRED`.
The registered usefulness criterion is met on both datasets, but Validation-20
does not support a general accuracy-improvement claim. No further tuning is
allowed. Test-100 remains unauthorized until a separate protocol is declared.
The complete cross-dataset record is in
`docs/BUDGET_FORCING_VALIDATION_RESULT_2026-11-20.md`.
