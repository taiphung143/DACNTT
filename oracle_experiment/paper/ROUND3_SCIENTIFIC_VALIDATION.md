# Round-3 scientific validation

Date: 2026-11-25  
Scope: existing artifacts only; no GPU inference, relabeling, split change, or Test-dependent tuning.

## Audit status

Both `scripts/final_scientific_audit.py` and
`scripts/round3_reviewer_audit.py` completed successfully. All stored/recomputed
paired counts, exact McNemar tests, Holm adjustments, source hashes, freeze
hashes, supplementary controls, and primary policy summaries agree.

## Six breadth-stopping policies

| Dataset | L | Stop at k=2 | Need k=4 | Stop mean tokens | Fixed k4 tokens | Saving | Stop/fixed correct | Prediction equality |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| GSM8K | 512 | 28/100 | 72/100 | 1,601.83 | 1,811.51 | 11.57% | 53/53 | 100/100 |
| GSM8K | 1024 | 54/100 | 46/100 | 1,994.52 | 2,535.17 | 21.33% | 76/76 | 100/100 |
| GSM8K | 2048 | 62/100 | 38/100 | 2,455.01 | 3,240.74 | 24.25% | 76/76 | 100/100 |
| MATH-500 | 1024 | 11/100 | 89/100 | 3,776.01 | 3,933.58 | 4.01% | 17/17 | 100/100 |
| MATH-500 | 2048 | 37/100 | 63/100 | 5,894.19 | 6,772.25 | 12.97% | 50/50 | 100/100 |
| MATH-500 | 4096 | 57/100 | 43/100 | 8,191.12 | 10,233.17 | 19.96% | 73/73 | 100/100 |

Prediction equality is a consequence of nested samples and deterministic
lowest-index tie breaking. Stopping frequency and token saving are the empirical
measurements.

## Effective sampling configuration

- model: `Qwen/Qwen3-0.6B`;
- revision: `c1899de289a04d12100db370d81485cdf75e47ca`;
- thinking mode: enabled;
- sampling: enabled because temperature is positive;
- effective temperature: 0.7, explicitly passed by the experiment;
- effective top-p: 0.95, explicitly passed by the adapter;
- effective top-k: 20, inherited from the pinned revision's
  `generation_config.json` because the adapter does not pass `top_k`.

The model file itself specifies temperature 0.6, top-p 0.95, and top-k 20.
Temperature 0.7 is an experiment override used consistently; no historical
temperature-tuning evidence was found.

## GSM8K L=512 parse-failure reconciliation

Among 400 standard Test trajectories:

- parse failures: 233/400 = 58.25%;
- truncated: 224/400 = 56.00%;
- truncated after thinking: 7;
- of those seven, 4 remain parseable and 3 are unparseable.

Therefore, 237 non-completed-valid category members must not be equated with
237 parse failures. Parse validity and truncation overlap. The manuscript now
reports exact two-decimal rates consistently.

## Dataset relationship

- the historical GSM8K manifest contains 100 IDs;
- `gsm8k-test-01309` is the sole audit exclusion;
- the 99 included historical IDs equal the 79 Train plus 20 Validation IDs;
- held-out Test-100 has zero ID overlap with historical/Train/Validation;
- all Train/Validation/Test question-hash intersections are zero.

## Train escalation labels

Counts use lambda 0.05 once per problem and stage. A positive label is the
implemented marginal-utility escalation target; correctness gains and
regressions are reported separately in the CSV.

- GSM8K depth positives: 15 (`512->1024`) and 6 (`1024->2048`).
- GSM8K breadth positives: 7, 8, 5, 3, 3, 4 across the six stages.
- MATH-500 depth positives: 22 (`1024->2048`) and 8 (`2048->4096`).
- MATH-500 breadth positives: 10, 2, 2, 6, 4, 5.

No stage reaches the predeclared floor of 30 positives.

## Headline primary and supplementary checks

- GSM8K selected: 76/100 at 1,994.52 tokens; fixed k4 comparator 76/100 at 2,535.17.
- GSM8K joint heuristic: 70/100 at 1,449.46 tokens.
- MATH selected: 66/100 at 5,141.50 tokens.
- MATH joint heuristic: 36/100 at 5,788.81 tokens.
- MATH breadth stop L4096: 73/100 at 8,191.12 tokens; fixed k4: 73/100 at 10,233.17.
- GSM selected versus joint: exact McNemar p=0.0703125; Holm p=0.4921875.
- MATH joint versus selected: Holm p approximately 2.50e-6.
- force-answer and non-thinking paired tables, p-values, and source hashes all match their manifests.

## Remaining limits

One generation seed, Test-100, Validation-20, exact-normalized MATH parsing,
one 0.6B primary model, and locally maintained freeze dates remain stated
limitations. The force-answer comparison is supplementary and post-hoc relative
to the primary policy evaluation. Raw generation files are not in the local
release package pending distribution review.
