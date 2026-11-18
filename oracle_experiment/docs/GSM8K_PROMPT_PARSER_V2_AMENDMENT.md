# GSM8K Prompt/Parser v2 Amendment

Status: **superseded by `GSM8K_PROMPT_V3_AMENDMENT.md` after failed smoke**  
Amendment date: 2026-11-12  
Parent protocol: `PHASE2_PROTOCOL_QWEN3_0_6B_V2.md`

## Triggering Evidence

The 30-problem Train-prefix pilot completed all 360 generations with zero
generation errors. Under the original `gsm8k_cot_v1` prompt and
`gsm8k_numeric_v1` parser, 251/360 raw samples had no parsed final answer.
Among these, 120 were not truncated and 61 copied the literal
`<numeric answer>` placeholder from the prompt. Representative observed forms
included:

```text
55 #### <numeric answer>
#### <numeric answer> 55
```

This is direct evidence of a prompt--model compatibility problem for
Qwen3-0.6B. It justifies a versioned amendment before scale-up. It does not
justify silently changing the completed pilot.

## Parser-Only Reprocessing Result

`gsm8k_numeric_v2` adds only two local recovery forms: a number immediately
before or immediately after the copied placeholder. It does not use the last
number in a response and does not promote a reasoning-only answer to a final
answer.

Reprocessing the original 360 records in a separate derivative experiment:

- reduced raw-sample parse errors from 251 to 201;
- increased correct raw samples from 86 to 125;
- changed the best fixed-profile accuracy from 46.7% to 66.7%;
- retained the original prompt name, raw-response hash, and source experiment
  in the derivative manifest.

The derivative is a parser sensitivity analysis, not new model evidence. The
original experiment remains immutable.

## New Generation Contract

All new GSM8K runs use:

- prompt: `gsm8k_cot_v2`;
- parser: `gsm8k_numeric_v2`.

Prompt v2 removes the literal answer placeholder. It instructs the model to
write four `#` characters, one space, and the numeric result on the final line,
and explicitly prohibits angle brackets and placeholder words.

Historical v1 runs can be resumed only with
`--gsm8k-contract-version v1`. The CLI default is v2.

## Required Smoke Before Scale-Up

Run the first 10 frozen Train problems at `k=1` and
`L in {1024, 2048}`. This requires 20 unique generations and is used only to
validate the new output contract.

The contract passes when:

1. all 20 records complete with zero generation errors;
2. no response contains the literal `<numeric answer>` placeholder;
3. at least 90% of non-truncated responses have a parsed final answer;
4. no v2 recovery rule extracts an intermediate last number;
5. the experiment manifest records prompt v2 and parser v2.

If any condition fails, revise the prompt/parser with another named amendment.
Do not scale the 30-problem grid or create controller labels until this gate
passes.

## Authorized Smoke Command

```powershell
D:\miniconda\envs\oracle_slm\python.exe -m adaptive_compute.cli.run_grid `
  --phase2-split-manifest data/splits/phase2_gsm8k_split_v1.json `
  --phase2-partition train --phase2-limit 10 --num-problems 10 `
  --gsm8k-contract-version v2 --k-values 1 --l-values 1024 2048 `
  --seed 42 --experiment-id qwen3_0_6b_gsm8k_contract_v2_smoke_n10 `
  --results-dir results
```
