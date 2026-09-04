# Oracle Grid Experiment

Phase 1 of **Difficulty-Aware Adaptive Test-Time Compute for Small Reasoning
Models** characterizes how breadth `k` and depth budget `L` affect Qwen3-1.7B
on a fixed GSM8K pilot subset. This is exploratory oracle characterization;
it is not an adaptive allocator.

## Experiment design

- `k`: number of independent samples used by valid-only majority vote.
- `L`: `max_new_tokens` for each sample; it is a limit, not measured reasoning depth.
- Default grid: `k = [1, 2, 4]`, `L = [512, 1024, 2048]`.
- Model: `Qwen/Qwen3-1.7B`, pinned revision, CUDA/BF16, thinking enabled.
- Dataset: a manifest-verified 30-item GSM8K test subset selected with seed 42.

Only `max(k)=4` generations are made for each problem and `L`. Configurations
reuse a nested shared pool:

```text
k=1 -> sample 0
k=2 -> samples 0,1
k=4 -> samples 0,1,2,3
```

The full run therefore needs `30 × 3 × 4 = 360` generations rather than 630.
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

## Validate without loading a model

```bash
python run_grid.py --num-problems 3 --k-values 1 2 4 \
  --l-values 512 1024 2048 --seed 42 --validate-only
```

The plan reports 36 unique generations for the three-question stage.

## Staged execution

Three-question checkpoint and plotting sanity run:

```bash
python run_grid.py --num-problems 3 --k-values 1 2 4 \
  --l-values 512 1024 2048 --seed 42
```

The command prints its deterministic `experiment_id`. Resume the identical run:

```bash
python run_grid.py --num-problems 3 --k-values 1 2 4 \
  --l-values 512 1024 2048 --seed 42 --resume
```

Each generation outcome is appended and flushed immediately. Its checkpoint key
is `experiment_id × problem_id × L × sample_id × repetition × model_revision ×
prompt_hash`; `k` is deliberately absent. Recorded generation errors are treated
as completed unless `--retry-errors` is supplied.

After the three-item stage succeeds, run the 10-item mini-demo:

```bash
python run_grid.py --num-problems 10 --k-values 1 2 4 \
  --l-values 512 1024 2048 --seed 42
```

The 3/10-item stages use prefixes of the existing fixed 30-item manifest. Do not
start the 30-item run until runtime and artifact quality have been checked.

## Rerun analysis without GPU inference

Inference automatically runs analysis when the grid finishes. It can be rebuilt
independently using either an experiment ID or directory:

```bash
python analyze_grid.py --experiment <experiment_id>
python -m analysis.aggregate --experiment <experiment_id>
python -m analysis.plots --experiment <experiment_id>
python -m analysis.oracle --experiment <experiment_id>
```

Phase 1.5 is isolated under the source experiment and is also GPU-free:

```bash
python analyze_phase1_5.py --experiment qwen3_1_7b_gsm8k_n30
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

Confirmatory runs are intentionally not launched by analysis. After the n30
cache has been populated by `analyze_phase1_5.py`, the planned commands are:

```bash
# Dataset scale-up: 840 new generations; 360 reused from n30.
python run_grid.py --num-problems 100 --num-repetitions 1 \
  --k-values 1 2 4 --l-values 512 1024 2048 --seed 42 \
  --dataset-manifest results/raw/gsm8k_subset_manifest_n100.json \
  --extend-dataset-manifest-from results/raw/gsm8k_subset_manifest.json \
  --experiment-id qwen3_1_7b_gsm8k_n100_r1

# Stochastic robustness: 720 new generations; repetition 0 reuses 360.
python run_grid.py --num-problems 30 --num-repetitions 3 \
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

The parser accepts only explicit numeric final-answer forms such as GSM8K
`####`, `\boxed{}`, or `Final answer:`. It never falls back to the last number
in free-form reasoning. Answers inside a completed `<think>` block are retained
only as diagnostics; strict accuracy and voting use the user-facing final response.

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

## Interpretation limits

Results may describe effects observed on this pilot subset: completion,
truncation, voting, realized compute, profile heterogeneity, and oracle headroom.
They must not be presented as proof of generalization, causality, true reasoning
depth, “overthinking,” novelty, or an already implemented adaptive allocator.

The 3/10-item stages are engineering pilots, not inferential experiments. The
statistical report requires at least 20 clean evaluated problems before it labels
results inferentially ready. The fixed 30-item run leaves 29 problems after the
known flagged item is excluded and can detect large paired effects; subtle
differences may still be inconclusive and require a larger preregistered sample.
