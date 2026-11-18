# GSM8K Prompt v3 Amendment

Status: **quality gate passed; active contract for GSM8K scale-up**  
Amendment date: 2026-11-12  
Parent protocol: `PHASE2_PROTOCOL_QWEN3_0_6B_V2.md`

## Reason for the Amendment

The prompt-v2 smoke completed all 20 planned generations with zero generation
errors and zero copies of the old `<numeric answer>` placeholder. It still
failed the output-contract gate: none of 16 non-truncated responses produced a
parseable final answer.

Qwen3-0.6B interpreted the character-level instruction inconsistently,
producing forms such as:

```text
# 43
# # # # 15
#105
#15000 #5000 20000
```

These forms are not added to the parser because some contain multiple numbers
and accepting them would require an unsafe last-number or positional guess.
The v2 smoke remains immutable negative prompt-design evidence.

## Prompt v3 Contract

All new GSM8K smoke generations use:

- prompt: `gsm8k_cot_v3`;
- parser: `gsm8k_numeric_v3`.

The final-response instruction now uses the natural marker
`Final answer:`. It prohibits `#` symbols, angle brackets, placeholder words,
and intermediate values on the final line.

The initial prompt-v3 smoke was generated with parser v2 and completed 20/20
records with zero generation errors. It removed all placeholder and hash-based
finals, but parser v2 recognized only 4/16 non-truncated responses because the
model often included units or short prose after the explicit marker. All 12
unparsed, non-truncated cases contained exactly one numeric candidate after
`Final answer:` and no ambiguous case was observed.

Parser v3 therefore adds one conservative rule: after an explicit
`Final answer:` marker, accept a value only when that final line contains
exactly one numeric candidate. It rejects zero candidates, multiple candidates,
unmarked prose, and reasoning-only answers. The 20 existing outputs are
reprocessed in a separate derivative experiment; the original smoke is not
overwritten.

Historical experiments remain reproducible with
`--gsm8k-contract-version v1` or `v2`. New runs default to prompt/parser v3.

## Controlled Comparison

The v3 smoke reuses the same first 10 frozen Train problems, model revision,
seed, decoding parameters, and caps as the failed v2 smoke:

- `k={1}`;
- `L={1024,2048}`;
- 20 unique generations.

Only the versioned prompt changes. Because the prompt hash is part of sample
identity, no v1/v2 generation-cache entry can be reused.

## Quality Gate

Prompt v3 passes only if:

1. all 20 records complete with zero generation errors;
2. no non-truncated response uses placeholder text or a `#`-based final line;
3. at least 90% of non-truncated responses have exactly one parseable final
   answer;
4. the manifest records `gsm8k_cot_v3` and `gsm8k_numeric_v2`;
5. a manual tail audit finds no extraction of intermediate values.

Accuracy is descriptive in this smoke. The decision concerns output-contract
validity, not model quality. Scale-up remains blocked until this gate passes.

## Authorized Command

```powershell
D:\miniconda\envs\oracle_slm\python.exe -m adaptive_compute.cli.run_grid `
  --phase2-split-manifest data/splits/phase2_gsm8k_split_v1.json `
  --phase2-partition train --phase2-limit 10 --num-problems 10 `
  --gsm8k-contract-version v3 --k-values 1 --l-values 1024 2048 `
  --seed 42 --experiment-id qwen3_0_6b_gsm8k_contract_v3_smoke_n10 `
  --results-dir results
```

The command above records parser v3 for all new runs. The completed smoke with
parser v2 is retained as the source for parser-only reprocessing.

## Completed Parser-v3 Gate (2026-11-12)

The parser-only derivative
`qwen3_0_6b_gsm8k_contract_v3_smoke_n10_parser_v3` preserves the 20 original
raw responses and their prompt hash while recording parser v3 and the source
raw SHA-256 in its manifest.

Gate results:

- 20/20 records present, zero generation errors and zero duplicate keys;
- zero placeholder echoes and zero hash-based non-truncated final lines;
- 16/16 non-truncated responses parsed (100%, above the 90% gate);
- all 12 newly recovered cases contained exactly one numeric value after the
  explicit marker;
- manual audit found no intermediate-number extraction;
- descriptive `k=1` accuracy was 50% at `L=1024` and 60% at `L=2048` on the
  10 Train smoke problems.

The output contract is therefore accepted. These accuracy values are smoke
diagnostics, not paper-level estimates. The next authorized inference is a
30-problem Train-prefix breadth--depth pilot using prompt/parser v3 and the
frozen GSM8K action space; final Test remains unopened.

## Active 30-Problem Pilot

The authorized scale-up was launched on 2026-11-12 as
`qwen3_0_6b_gsm8k_train_pilot_n30_contract_v3` with:

- the first 30 problems of the frozen Train partition;
- `k in {1,2,4}` and `L in {512,1024,2048}`;
- 360 expected nested-pool generations;
- Qwen3-0.6B at the pinned revision, CUDA/BF16, seed 42;
- prompt `gsm8k_cot_v3` and parser `gsm8k_numeric_v3`;
- checkpointing and automatic post-run analysis.

After completion, scale-up is permitted only if all 360 keys are present,
generation errors are at most 2%, non-truncated final-answer parse success is
at least 90%, no ambiguous parser-v3 recovery is found in manual audit, and
the runtime/truncation profile remains feasible. Test is not accessed by this
run.
