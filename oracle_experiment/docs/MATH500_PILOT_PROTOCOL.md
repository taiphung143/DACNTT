# MATH-500 Pilot Protocol (v1)

> Historical pre-run protocol. The completed pilot exposed two deterministic
> answer-normalization defects. The versioned corrective amendment is recorded
> in `MATH500_PARSER_V2_AMENDMENT.md`; v1 artifacts remain unchanged.

## Status

Dataset adapter, prompt, conservative exact-answer parser, frozen 30-problem
manifest, CLI integration, and unit tests are implemented. GPU inference has
not yet been launched. This pilot is development evidence and must not be mixed
with a future untouched MATH confirmatory partition.

## Frozen source and sample

- Dataset: `HuggingFaceH4/MATH-500`
- Repository revision: `6e4ed1a2a79af7d8630a6b768ec859cb5af4d3be`
- Source split: `test`
- Dataset size: 500
- Pilot size: 30
- Selection seed: 42
- Selection policy: deterministic round-robin over non-empty
  `(subject, level)` strata
- Manifest: `data/splits/math500_pilot_v1.json`
- Manifest SHA-256:
  `8635bbda8c61e1a06e926aec726ea4a7eea34644b3f29fd83e97da19d0e63dd0`

The pilot covers all seven subjects and all five difficulty levels. Its exact
distribution is stored in the frozen manifest. Question and raw-answer hashes
are checked whenever the manifest is reused.

The 30 canonical reference answers contain 21 integer/decimal answers, seven
simple rational answers, one radical, and one interval. This is adequate for a
first parser pilot but does not validate every MATH-500 answer type.

## Parser contract

The MATH-500 prompt requires one final `\boxed{...}` line. The parser accepts
only a balanced `\boxed{...}`, `\fbox{...}`, or explicit `####` final marker.
It handles nested braces and conservatively normalizes presentation variants,
simple exact fractions, degrees, whitespace, and `\left`/`\right`. It does not
claim general symbolic equivalence. Unmatched symbolic forms remain visible as
wrong answers or parse failures and must be audited rather than silently
coerced.

Strict accuracy uses only the user-facing response after a completed
`</think>` tag. Answers inside reasoning are diagnostic only. Every generated
trajectory is charged to actual-token and latency totals.

## Stage A: parser and throughput pilot

The first GPU run uses `k=1` at `L in {1024, 2048}`. It requires 60 unique
generations and is intended to measure parser behavior, truncation, token use,
latency, and whether Qwen3-1.7B has non-trivial accuracy on the selected sample.
It is not a test of breadth or the joint controller.

Validate the immutable plan without loading a model:

```powershell
python -m adaptive_compute.cli.run_grid `
  --dataset-name math500 `
  --dataset-revision 6e4ed1a2a79af7d8630a6b768ec859cb5af4d3be `
  --dataset-manifest data/splits/math500_pilot_v1.json `
  --num-problems 30 --k-values 1 --l-values 1024 2048 `
  --experiment-id qwen3_1_7b_math500_pilot_v1 --validate-only
```

Run on the GPU machine:

```powershell
python -m adaptive_compute.cli.run_grid `
  --dataset-name math500 `
  --dataset-revision 6e4ed1a2a79af7d8630a6b768ec859cb5af4d3be `
  --dataset-manifest data/splits/math500_pilot_v1.json `
  --num-problems 30 --k-values 1 --l-values 1024 2048 `
  --experiment-id qwen3_1_7b_math500_pilot_v1 `
  --device cuda --dtype bfloat16
```

Preflight the Python environment before launching:

```powershell
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"
```

The second value must be `True`. Seeing a GPU in `nvidia-smi` is not sufficient
when the active Python environment contains a CPU-only PyTorch build. Do not use
`--allow-cpu` for the measured pilot because its latency is not comparable to
the existing CUDA/BF16 experiment.

Use `--resume` after an interrupted run. Do not change the prompt, parser,
manifest, model revision, decoding parameters, or experiment ID when resuming.

## Audit before scaling

Before generating breadth samples or increasing the dataset size:

1. Confirm zero unhandled generation errors.
2. Manually inspect all 60 final responses because the pilot is small.
3. For each response, verify whether the parser extracted exactly the answer
   explicitly presented by the model; do not judge reasoning quality as parser
   correctness.
4. Separate parse failure, extraction error, model wrong answer, truncation,
   and dataset ambiguity.
5. Require no systematic answer-type failure and at most one extraction error
   among 60 responses (less than 2%). Otherwise revise and version the parser,
   reprocess the same raw outputs, and repeat the audit before scaling.
6. Report accuracy, actual generated tokens, latency, valid-answer rate, and
   truncation separately for `L=1024` and `L=2048`.

## Decision after Stage A

- Continue to a larger MATH development pool only if parsing is reliable and
  the model produces enough valid answers for controller labels.
- If `L=1024` is dominated by truncation, retain it for the reported ablation
  but reconsider it as an initial action before the larger run.
- If both caps yield near-zero accuracy, do not scale blindly. Inspect prompt,
  model suitability, and answer types first.
- Do not create or inspect the final MATH evaluation partition until the
  controller, baselines, feature contract, and go/pivot thresholds are frozen.
