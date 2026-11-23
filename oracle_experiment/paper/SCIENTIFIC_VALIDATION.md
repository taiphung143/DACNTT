# Scientific Validation — 2026-11-21

## Valid mathematical properties

1. **Two-sample agreement stopping.** If samples 0 and 1 are both valid and
   normalize to answer `a`, the stopping policy returns `a`. In any four-sample
   extension, `a` already has two votes. Two later samples can at most create a
   2–2 tie, which the lowest-index rule resolves to sample 0 (`a`). If stopping
   does not occur, the adaptive and fixed policies evaluate the same four
   samples. Therefore their final predictions are identical for every complete
   sample pool satisfying the implementation contract.

2. **`k=1` cap monotonicity under nested reuse.** A response completed at a
   shorter cap is identical at a larger cap. A shorter response that reaches
   the cap without a strict final answer cannot be correct. Thus a `k=1`
   correct short-cap result remains correct at the larger cap.

3. **No general `k>1` cap monotonicity.** Counterexample for `k=2`: the short
   cap has answers `[invalid, A]` and returns correct `A`; the long cap has
   `[B, A]`, whose 1–1 tie returns lower-index `B`. Prefix dependence does not
   imply monotonic aggregated correctness.

4. **No general monotonicity from `k=2` to `k=4`.** New valid samples can alter
   the plurality/majority. The special `k=1`→`k=2` property holds only because
   a valid sample 0 always wins a disagreement tie; `k=2` differs from `k=1`
   only when sample 0 is invalid.

## Prediction-level statistical verification

- Historical Qwen3-1.7B/GSM8K: all 15 planned comparisons (six depth, six
  breadth, three equal-budget) reproduce their A-only/B-only counts, two-sided
  exact McNemar p-values, and within-family Holm values.
- Primary Qwen3-0.6B: both 13-comparator families reproduce paired counts,
  exact p-values, and within-dataset Holm values.
- Supplementary controls: all six thinking/non-thinking Validation comparisons
  and all six standard/force-answer Test comparisons reproduce paired counts,
  exact p-values, and three-test within-dataset Holm values.
- The GSM8K selected-versus-joint result remains inferentially inconclusive
  after Holm (`p=0.4922`), despite the unadjusted paired bootstrap interval
  `[1,12]` pp. No significance claim is inferred from the bootstrap interval.

Machine-readable evidence:

- `audit_outputs/historical_paired_verification.csv`
- `audit_outputs/primary_policy_verification.csv`
- `audit_outputs/supplementary_control_verification.csv`

## Experimental-data consistency

- GSM8K selected breadth stop: 76/100, 1,994.52 mean tokens.
- GSM8K fixed `4x1024`: 76/100, 2,535.17 mean tokens.
- GSM8K joint heuristic: 70/100, 1,449.46 mean tokens.
- MATH selected fixed `2x4096`: 66/100, 5,141.50 mean tokens.
- MATH joint heuristic: 36/100, 5,788.81 mean tokens.
- MATH breadth stop `L=4096`: 73/100, 8,191.12 mean tokens.
- MATH fixed `4x4096`: 73/100, 10,233.17 mean tokens.

All six breadth-stop pools have prediction equality with fixed `k=4` (600/600
comparisons). The empirical quantities are stopping frequency and realized
token savings, not accuracy preservation.

## Raw-output categorization

For each cap, the exclusive tuple is `(truncated during thinking, truncated
after thinking, completed unparseable, completed valid)`:

| Data | L | Counts (n=400) |
|---|---:|---:|
| GSM8K | 512 | (217, 7, 13, 163) |
| GSM8K | 1024 | (94, 0, 21, 285) |
| GSM8K | 2048 | (49, 0, 24, 327) |
| MATH-500 | 1024 | (292, 51, 0, 57) |
| MATH-500 | 2048 | (194, 38, 0, 168) |
| MATH-500 | 4096 | (116, 11, 0, 273) |

The existing `parse_error` and `truncated` flags overlap and are intentionally
reported separately from these exclusive categories.

## Excluded historical record

The manual audit entry for `gsm8k-test-01309` predates the September historical
generation in version control. The question's four amounts sum to 2,180, while
the retained benchmark label is 2,280. Under the unmodified label the record is
incorrect for every profile. Including it therefore changes only denominators:
for example, the best profile becomes 83/100 instead of 83/99. Raw data and the
original label were not edited.

## Integrity and reproducibility

- All checked local freeze/replay artifact SHA-256 values match their manifests.
- All supplementary source experiment/config/raw hashes match their comparison
  manifests.
- The cited public GitHub HEAD resolves to commit
  `cd55d239a8ac1bb3f403bc70f5a611986c2ee321`.
- That commit does not include the large result directories; local freeze dates
  are author-maintained and are not independent timestamp evidence.

## Unresolved limitations

- One stochastic seed; no generation-seed robustness estimate.
- Small Test-100 and Validation-20 partitions.
- Primary evidence covers one 0.6B model; 1.7B evidence is historical GSM8K only.
- Full raw and force-answer artifacts are not public at the cited commit.
- Generated tokens are not full hardware compute: prefill, KV-cache, batching,
  scheduling, and device behavior are outside the primary cost metric.
