# Oracle Grid Experiment

Phase 1 of **Difficulty-Aware Adaptive Test-Time Compute for Small Reasoning
Models** asks one narrow question: do different GSM8K problems benefit from
different breadth/depth inference profiles?

This repository is currently at **Milestone 3 (one-sample model inference)**.
It loads a reproducible GSM8K subset, parses/evaluates numeric answers, and runs
one local Qwen3 generation through a provider-neutral adapter with measured
tokens and synchronized CUDA latency. Grid execution, aggregation, checkpoint
resume, and analysis remain deferred to later milestones.

## Experiment vocabulary

- `k` (breadth): number of independent reasoning samples generated for one
  problem.
- `L` (depth): maximum number of newly generated tokens for each sample.
- Fixed grid: every selected problem is evaluated at every configured `(k, L)`
  pair while model, prompt, sampling parameters, parser, aggregation method,
  and dataset subset remain fixed.
- Oracle: retrospective analysis that uses ground truth to choose a successful
  profile. It is an analysis tool, not a deployable router.

The experiment will store both allocated budget (`k * L`) and realized compute
(the sum of generated tokens). They are deliberately not treated as equal.

## Environment setup

Python 3.10 or newer is required. The tested Windows setup uses a dedicated
Miniconda environment:

```bash
conda create -n oracle_slm python=3.11 pip -y
conda activate oracle_slm
python -m pip install torch==2.9.1 \
  --index-url https://download.pytorch.org/whl/cu128
python -m pip install -r requirements.txt
```

The CUDA command is specific to the tested RTX 4060 setup. Select the matching
official PyTorch wheel for other hardware. Install CUDA PyTorch before the
requirements file so pip keeps the GPU-enabled local build.

## Model configuration

The tested model is `Qwen/Qwen3-1.7B` in BF16 with thinking mode enabled. Its
exact Hugging Face commit is pinned in `config.py`; all grid profiles must use
the same revision, chat template, thinking mode, temperature, and top-p.

All model integrations implement `models.base.ModelAdapter`. The local backend
is `models.transformers_adapter.TransformersModelAdapter`; experiment logic is
not bound directly to Hugging Face.

## Run the Milestone 3 smoke inference

With `oracle_slm` active, run one generation on the first manifest problem:

```bash
python smoke_inference.py --problem-index 0 --max-new-tokens 512 \
  --temperature 0.7 --top-p 0.95 --seed 42
```

New runs use `results/raw/smoke_L<budget>_seed<seed>.jsonl` unless `--output` is
provided. The original pre-fix artifact remains at
`results/raw/milestone3_smoke.json`. On the tested RTX
4060 run, the model generated all 512 tokens and ended with `finish_reason` set
to `length`; it had not emitted a final answer before truncation. This is a
measurement from one smoke sample, not evidence of depth sensitivity by itself.

## Reliability policy before the pilot grid

Main evaluation never falls back to the last number in free-form reasoning.
Final-answer precedence is: GSM8K `####`, `\boxed{}`, explicit phrases such as
`Final answer:`/`The answer is`, a concluding `Therefore/Thus/Hence, <number>`,
then a response consisting only of one number. Anything else returns `None`.

The parser separates an explicit `reasoning_answer` inside a completed
`<think>...</think>` block from a `final_response_answer` after `</think>`.
`parsed_answer` is a backward-compatible alias for the final-response answer
only. Hidden reasoning answers never enter strict task accuracy or final voting.
`answer_source` records `thinking`, `final_response`, `both`, or `none`, and a
disagreement flag is retained when both answers exist but differ.

`finish_reason` values `length`, `max_tokens`, and `max_length` are normalized
as truncation. An open thinking block is `during_thinking`; truncation after a
closed block is `after_thinking`; a natural finish is `none`. Missing a final
answer during these stages becomes `truncated_before_answer` or
`truncated_after_reasoning`, respectively.

`reasoning_correct` is diagnostic. `final_correct` (also exposed as the legacy
`correct` field) is the only main task-accuracy signal.

Majority voting ignores invalid (`None`) samples. `agreement` and
`agreement_among_valid` use valid parsed answers as the denominator;
`valid_answer_fraction` separately reports valid samples divided by `k`.

Reprocess an existing JSON or JSONL artifact without running the model:

```bash
python reprocess_results.py \
  --input results/raw/milestone3_smoke.json \
          results/raw/milestone3_smoke_fixed.jsonl \
  --output results/processed/pilot_stage_reparsed.jsonl \
  --enrich-gsm8k
```

Inspect failure rates and breakdown by `L`:

```bash
python validate_pilot.py \
  --input results/processed/pilot_stage_reparsed.jsonl
```

List manual-audit candidates without changing GSM8K labels:

```bash
python audit_results.py \
  --input results/processed/pilot_stage_reparsed.jsonl
```

Generate the depth diagnostic table:

```bash
python -m analysis.depth_diagnostics \
  --input results/processed/pilot_stage_reparsed.jsonl
```

Researcher annotations live in `data/manual_audit.json`.
`gsm8k-test-01309` is marked `manual_review_required` because its question
arithmetic and official rationale appear inconsistent. The annotation adds
`dataset_quality_flag` but never changes `ground_truth` or `ground_truth_raw`.
Model disagreement alone never creates a flag.

With `EXCLUDE_FLAGGED_DATASET_ITEMS_FROM_MAIN_METRICS=True`, flagged records are
excluded from final accuracy, reasoning-solved rate, oracle selection, and
Pareto inputs. They remain present in raw data, truncation diagnostics, and
manual audit output. Reports include total, flagged, and main-metric item counts.

## Load and verify the GSM8K pilot subset (Milestone 2)

The first invocation downloads/caches `openai/gsm8k`, selects 30 unique test problems
with seed 42, and creates `results/raw/gsm8k_subset_manifest.json`:

```bash
python dataset.py --num-problems 30 --seed 42 --preview 3
```

Later invocations with the same arguments reuse the exact recorded source
indices and verify question hashes and ground truths. Conflicting settings are
rejected. To intentionally create a different subset, use a different manifest
path rather than overwriting evidence from an existing experiment:

```bash
python dataset.py --num-problems 30 --seed 7 \
  --manifest results/raw/gsm8k_subset_seed7_manifest.json
```

Each loaded problem contains a stable ID, source index, question, raw dataset
answer, and canonical numeric ground truth. Dataset integrity errors raise
immediately; model-output parse failures later return `None` and are evaluated
as incorrect.

## Validate the pilot grid configuration

From this directory:

```bash
python run_grid.py --validate-only \
  --num-problems 30 \
  --k-values 1 2 4 \
  --l-values 512 1024 2048 \
  --seed 42
```

On PowerShell, replace `\` with the backtick continuation character or put the
command on one line. This command only prints the validated plan; it does not
load a dataset or run inference yet.

## Planned execution and resume behavior

In later milestones, the same CLI without `--validate-only` will execute the
grid. Sample-level JSONL records will act as an append-only checkpoint keyed by
`problem × k × L × repetition × sample`, so restarting with the same immutable
experiment settings can skip completed generations.

Planned pilot command:

```bash
python run_grid.py --num-problems 30 --k-values 1 2 4 \
  --l-values 512 1024 2048 --seed 42
```

## Planned analysis

The scripts under `analysis/` will read completed summary records and produce:

- grid-level performance tables;
- per-problem correctness/success-probability matrices;
- accuracy and generated-token heatmaps;
- accuracy-versus-compute/Pareto plots;
- exploratory behavior categories;
- Fixed, Breadth-only, Depth-only, and Joint Oracle comparisons.

The intended interface will be documented when Milestones 6–7 are implemented.

## Output layout

- `results/raw/`: one JSONL row per generation, including raw response, parsed
  answer, token counts, latency, seed, and error state.
- `results/processed/`: configuration summaries, tables, plots, behavior
  analysis, and oracle comparisons.

Both directories are retained in Git through `.gitkeep`; generated artifacts
are ignored by default.

## Tests

```bash
python -m pytest
```

The current tests cover strict parsing, truncated reasoning, thinking tags,
failure classification, utilization, valid-only voting/agreement, reliability
summaries, guarded oracle selection, reprocessing, configuration, dataset
integrity, prompts, and the model adapter contract.

## Known limitations at Milestone 3

- Parser supports the numerical formats required for GSM8K, not arbitrary
  symbolic mathematics or word-form numbers.
- Voting and summary primitives exist, but the full grid runner and generation
  checkpoint/resume loop are not implemented yet.
- No grid execution, plots, behavior heuristics, or oracle analysis yet.
- The adapter is verified on one CUDA/BF16 machine; CPU fallback and quantized
  inference are intentionally not part of the current experiment.
- Token and latency accounting semantics still depend on the selected backend.

No empirical conclusion should be drawn from this skeleton or from a small
pilot alone.
