# Oracle Grid Experiment

Phase 1 of **Difficulty-Aware Adaptive Test-Time Compute for Small Reasoning
Models** characterized how breadth `k` and generation-token cap `L` affect
Qwen3-1.7B on fixed GSM8K subsets. Those results remain completed historical
evidence. Because long-cap inference on the available RTX 4060 was too slow,
the permanent primary model for the remaining thesis is Qwen3-0.6B under the
frozen protocol in
[`docs/PHASE2_PROTOCOL_QWEN3_0_6B_V2.md`](docs/PHASE2_PROTOCOL_QWEN3_0_6B_V2.md).
The migration rationale remains in
[`docs/MODEL_MIGRATION_QWEN3_0_6B.md`](docs/MODEL_MIGRATION_QWEN3_0_6B.md).
Phase 1 and Phase 1.5 are retrospective oracle characterization; they are not
an adaptive allocator. The historical 1.7B Phase 2 protocol is retained in
[`docs/PHASE2_PROTOCOL.md`](docs/PHASE2_PROTOCOL.md); all new runs follow the
0.6B v2 protocol above.

## Experiment design

- `k`: number of independent samples used by valid-only majority vote.
- `L`: `max_new_tokens` for each sample; it is a limit, not measured reasoning depth.
- Default grid: `k = [1, 2, 4]`, `L = [512, 1024, 2048]`.
- Current default for new runs: `Qwen/Qwen3-0.6B`, revision
  `c1899de289a04d12100db370d81485cdf75e47ca`, CUDA/BF16, thinking enabled.
- Completed 1.7B results are retained as a separate model-specific track and
  must not be relabelled, pooled, or used as 0.6B controller targets.
- Dataset: a manifest-verified 30-item pilot extended to a 100-item GSM8K test
  subset with the original 30 items preserved as an exact prefix. One audited
  item is excluded from main evaluation metrics, leaving 99 evaluated items.

Only `max(k)=4` generations are made for each problem and `L`. Configurations
reuse a nested shared pool:

```text
k=1 -> sample 0
k=2 -> samples 0,1
k=4 -> samples 0,1,2,3
```

For `N` problems, the full grid needs `N × 3 × 4` generations rather than
independently regenerating samples for every `k`. The completed n=100 run
contains 1,200 generation records.
The sample seed is the first 63 bits of
`SHA256(global_seed|problem_id|repetition_id|sample_id)`. It excludes both `k`
and `L`, giving paired stochastic seeds across depth budgets.

## Setup

Python 3.10+ is required. Install the CUDA build of PyTorch appropriate for the
machine, followed by:

```bash
python -m pip install -r requirements.txt
```

Run commands from the `oracle_experiment` directory.

Verify the complete environment after installation:

```bash
python -m pip check
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
```

The validated Windows/RTX 4060 environment and its test evidence are recorded
in `docs/environment_validation_2026-11-16.md`.

## Project layout

```text
adaptive_compute/          Python package
  analysis/                aggregation, statistics, oracle and plots
  cli/                     executable experiment and analysis entry points
  models/                  inference backend contracts and adapters
data/                      researcher-authored audit data
  splits/                  frozen Phase-2 problem-level data partitions
docs/                      runbook and frozen research protocols
paper/                     version-controlled LNCS manuscript source
results/                   reproducible experiment artifacts (Git-ignored)
tests/                     unit and end-to-end sanity tests
```

## Validate without loading a model

```bash
python -m adaptive_compute.cli.run_grid --num-problems 3 --k-values 1 2 4 \
  --l-values 512 1024 2048 --seed 42 --validate-only
```

The plan reports 36 unique generations for the three-question stage.

## MATH-500 development pilot

The second-dataset adapter uses the pinned `HuggingFaceH4/MATH-500` revision,
a deterministic subject/level-stratified 30-problem development manifest, a
separate boxed-answer prompt, and a conservative exact-answer parser. Validate
the initial 0.6B `k=1`, `L in {1024,2048,4096}` pilot plan with:

```bash
python -m adaptive_compute.cli.run_grid --dataset-name math500 \
  --dataset-manifest data/splits/math500_pilot_v2.json \
  --num-problems 30 --k-values 1 --l-values 1024 2048 4096 \
  --experiment-id qwen3_0_6b_math500_depth_pilot_v1 --validate-only
```

See [`docs/MATH500_PILOT_PROTOCOL.md`](docs/MATH500_PILOT_PROTOCOL.md) before
launching GPU inference. This pilot is development evidence, not a held-out
MATH result.

The subsequent 0.6B study uses the frozen split
`data/splits/math500_split_v1.json`: 80 Train, 20 Validation, and 100 unopened
Test problems. Its first 30 Train problems are exactly the completed pilot.
Create or validate it with:

```bash
python -m adaptive_compute.cli.create_math500_splits
```

The MATH action space remains `k={1,2,4}` and
`L={1024,2048,4096}`; `L=8192` is excluded by the current protocol.

## Staged execution

Three-question checkpoint and plotting sanity run:

```bash
python -m adaptive_compute.cli.run_grid --num-problems 3 --k-values 1 2 4 \
  --l-values 512 1024 2048 --seed 42
```

The command prints its deterministic `experiment_id`. Resume the identical run:

```bash
python -m adaptive_compute.cli.run_grid --num-problems 3 --k-values 1 2 4 \
  --l-values 512 1024 2048 --seed 42 --resume
```

Each generation outcome is appended and flushed immediately. Its checkpoint key
is `experiment_id × problem_id × L × sample_id × repetition × model_revision ×
prompt_hash`; `k` is deliberately absent. Recorded generation errors are treated
as completed unless `--retry-errors` is supplied.

After the three-item stage succeeds, run the 10-item mini-demo:

```bash
python -m adaptive_compute.cli.run_grid --num-problems 10 --k-values 1 2 4 \
  --l-values 512 1024 2048 --seed 42
```

The 3/10-item stages use prefixes of the existing fixed 30-item manifest. Do not
start the 30-item run until runtime and artifact quality have been checked.

## Rerun analysis without GPU inference

Inference automatically runs analysis when the grid finishes. It can be rebuilt
independently using either an experiment ID or directory:

```bash
python -m adaptive_compute.cli.analyze_grid --experiment <experiment_id>
python -m adaptive_compute.analysis.aggregate --experiment <experiment_id>
python -m adaptive_compute.analysis.plots --experiment <experiment_id>
python -m adaptive_compute.analysis.oracle --experiment <experiment_id>
```

Phase 1.5 is isolated under the source experiment and is also GPU-free:

```bash
python -m adaptive_compute.cli.analyze_phase1_5 --experiment qwen3_1_7b_gsm8k_n30
```

It adds per-problem preferences, actual-token cost accounting, depth-before-
breadth diagnostics, exact budget-constrained oracle frontiers, paired
problem-level bootstrap summaries, failure analysis, and researcher-facing
decision reports under `results/<experiment_id>/phase1_5/`.

Successful generations are reusable across experiment IDs through
`results/generation_cache.jsonl`. Cache identity includes every generation-
relevant setting and deliberately excludes `k`. To extend the fixed 30-problem
manifest while preserving it as an exact prefix, pass both a new
`--dataset-manifest` and `--extend-dataset-manifest-from`.

Confirmatory runs are intentionally not launched by analysis. The dataset
scale-up command below has been completed as `qwen3_1_7b_gsm8k_n100_r1`; the
multi-repetition stochastic-robustness run remains future evaluation.

```bash
# Dataset scale-up: 840 new generations; 360 reused from n30.
python -m adaptive_compute.cli.run_grid --num-problems 100 --num-repetitions 1 \
  --k-values 1 2 4 --l-values 512 1024 2048 --seed 42 \
  --dataset-manifest results/raw/gsm8k_subset_manifest_n100.json \
  --extend-dataset-manifest-from results/raw/gsm8k_subset_manifest.json \
  --experiment-id qwen3_1_7b_gsm8k_n100_r1

# Stochastic robustness: 720 new generations; repetition 0 reuses 360.
python -m adaptive_compute.cli.run_grid --num-problems 30 --num-repetitions 3 \
  --k-values 1 2 4 --l-values 512 1024 2048 --seed 42 \
  --experiment-id qwen3_1_7b_gsm8k_n30_r3
```

## Artifacts

Every run is isolated under `results/<experiment_id>/`:

- `experiment_manifest.json`: immutable config, hashes, versions, seed policy,
  selected IDs, and expected generation count.
- `raw_samples.jsonl`: one row per generated shared-pool sample. Full responses,
  strict parsing, failures, tokens, latency, seed, audit flag, and identity live here.
- `config_results.csv`: one row per problem/repetition/`(k,L)` derived from sample
  prefixes. It includes agreement, valid-answer fraction, allocated `k×L`, and
  realized token/latency sums.
- `grid_summary.csv`: one row per `(k,L)`, with flagged items excluded from main
  accuracy while remaining counted and visible.
- `depth_diagnostic.csv`, `breadth_diagnostic.csv`, `iso_budget_2048.csv`.
- `behavior_classification.csv`: conservative descriptive labels, not scientific
  ground-truth difficulty classes.
- `oracle_comparison.csv`: Best Fixed, Breadth-only, Depth-only, and Joint Oracle.
- `oracle_anchor_evaluation.csv`: all fixed anchors so anchor selection is explicit.
- `accuracy_intervals.csv`: profile accuracy with Wilson 95% confidence intervals
  and an explicit small-sample guard.
- `paired_comparisons.csv`: planned depth, breadth, and iso-budget comparisons
  using exact paired McNemar tests with Holm correction within each family.
- `statistical_report.md`: compact interpretation of the inferential artifacts.
- `demo_cases.md`: compact raw-sample and majority-vote examples.
- `plots/`: depth, breadth, iso-budget, heatmaps, allocated-vs-realized, Pareto,
  and oracle-headroom figures.

The iso-budget comparison explicitly contrasts `4×512`, `2×1024`, and `1×2048`.
Allocated budget is an upper bound; realized generated tokens are reported
separately.

## Evaluation reliability

GSM8K parsing accepts only explicit numeric final-answer forms such as `####`,
`\boxed{}`, or `Final answer:`. MATH-500 uses its own balanced boxed-answer
parser and conservative exact normalization for common LaTeX forms. Neither
parser falls back to the last expression in free-form reasoning. Answers inside
a completed `<think>` block are retained only as diagnostics; strict accuracy
and voting use the user-facing final response.

Truncation is separated into `during_thinking`, `after_thinking`, and `none`.
Voting ignores invalid answers, reports agreement among valid answers, and also
reports `valid_answer_fraction`. Agreement at `k=1` is not interpreted as
consensus.

The manual audit entry for `gsm8k-test-01309` is retained in all raw artifacts
but excluded from main accuracy, Pareto inputs, and oracle comparison. Original
GSM8K labels are never rewritten.

Oracle selection is retrospective. Among correct configurations it minimizes:

1. realized generated tokens;
2. latency;
3. allocated budget;
4. `(k,L)` lexicographically.

Breadth/depth anchor candidates are all written before the best anchor is chosen.
Oracle plots show potential headroom only; they do not demonstrate a learned router.

## Tests

Ordinary tests use fake adapters and require no CUDA:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
```

The environment variable only prevents unrelated globally installed pytest
plugins from interfering with this project.

## Frozen Phase 2 data split

Phase 2 uses the immutable manifest
`data/splits/phase2_gsm8k_split_v1.json`: 79 train, 20 validation, and 100
held-out test problems. Train and validation come from the 99 usable n=100
development items; the test problems are new and disjoint from n100. The one
manually flagged development item is not assigned to a controller partition.

Recreating the manifest is deterministic and idempotent; the command refuses
to overwrite it with different assignments:

```bash
python -m adaptive_compute.cli.create_phase2_splits
```

Validate an intended run without loading the dataset or model:

```bash
python -m adaptive_compute.cli.run_grid --num-problems 79 \
  --phase2-split-manifest data/splits/phase2_gsm8k_split_v1.json \
  --phase2-partition train --validate-only
```

Use `--num-problems 20 --phase2-partition validation` for validation. Do not
generate or inspect the 100-problem test outcomes until the controller and its
thresholds have been frozen. When a Phase 2 partition is loaded, every current
question and ground truth is checked against its frozen hash before inference.

## Phase 2 depth-only development baseline

Build the leakage-safe Train/Validation tables from the completed n100 run:

```bash
python -m adaptive_compute.cli.prepare_depth_controller_data
```

This writes 79 Train and 20 Validation rows under
`results/phase2/depth_controller_data_v1/`. Only columns explicitly listed as
`feature_*` in `feature_schema.json` are permitted as model inputs; labels and
observed outcomes are retained for supervision/evaluation and are marked as
forbidden inputs.

Train and select the fixed depth-only logistic baseline:

```bash
python -m adaptive_compute.cli.train_depth_baseline
```

The selected development candidate uses `C=1`, balanced class weights, and a
0.9 ordered target-depth quantile. On the 20-problem Validation split it matches
fixed `L=2048` accuracy (13/20) with 1059.45 versus 1213.05 average Actual
Generated Tokens. This is model-selection evidence on a small Validation set,
not held-out evidence. The frozen test partition has not been loaded or used.

Detailed local artifacts are written to `results/phase2/depth_baseline_v1/`,
including all 18 candidate metrics, validation predictions, the serialized
model, provenance hashes, and `development_report.md`.

## Interpretation limits

Results may describe effects observed on the characterization subset: completion,
truncation, voting, realized compute, profile heterogeneity, and oracle headroom.
They must not be presented as proof of generalization, causality, true reasoning
depth, “overthinking,” novelty, or an already implemented adaptive allocator.

The 3/10-item stages are engineering pilots, not inferential experiments. The
completed n=100 scale-up leaves 99 problems after the known flagged item is
excluded. It contains only one stochastic repetition, so problem-level
uncertainty does not quantify generation-seed variability. Controller claims
require the frozen out-of-sample Phase 2 evaluation.
