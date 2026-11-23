# Qwen3-0.6B non-thinking control: Validation result

Date: 2026-11-19

## Evidence status

This is completed supplementary development evidence on the frozen GSM8K
Validation-20 and MATH-500 Validation-20 partitions. Thinking and non-thinking
use the same model revision, problem IDs, prompts, sampling settings, k values,
and dataset-specific high L. GSM8K generation is evaluated with the same V4
parser in both modes; reprocessing thinking V3 to V4 did not change any high-L
accuracy. MATH-500 uses V2 in both modes. No held-out Test-100 artifact was
loaded for this comparison.

## Paired results

| Dataset | k,L | Thinking accuracy/tokens | Non-thinking accuracy/tokens | Accuracy gap | Token saving | Holm-adjusted p |
|---|---:|---:|---:|---:|---:|---:|
| GSM8K | 1x2048 | 13/20, 986.15 | 1/20, 31.30 | -60 pp | 96.83% | 0.000488 |
| GSM8K | 2x2048 | 14/20, 1,969.70 | 1/20, 84.85 | -65 pp | 95.69% | 0.000488 |
| GSM8K | 4x2048 | 15/20, 3,593.85 | 1/20, 143.65 | -70 pp | 96.00% | 0.000366 |
| MATH-500 | 1x4096 | 11/20, 2,388.70 | 8/20, 471.90 | -15 pp | 80.24% | 1.000 |
| MATH-500 | 2x4096 | 13/20, 4,700.50 | 8/20, 923.40 | -25 pp | 80.36% | 0.375 |
| MATH-500 | 4x4096 | 13/20, 8,979.10 | 11/20, 1,972.50 | -10 pp | 78.03% | 1.000 |

McNemar tests are paired by problem, with Holm correction across k={1,2,4}
within each dataset. The non-significant MATH-500 tests do not establish
equivalence or non-inferiority at n=20.

## Interpretation and decision

Non-thinking mode is much cheaper but is not an accuracy-preserving substitute
for thinking mode under the frozen prompts. The GSM8K degradation is large and
statistically supported. Every MATH-500 point estimate also favors thinking,
although the small Validation sample leaves the paired tests inconclusive.

Decision: do not promote this non-thinking configuration to Test-100. Retain
the result as a completed decoding control that helps explain why low token
cost alone is not sufficient. The thesis's primary frozen Test-100 policies
and claims remain unchanged. Native Qwen thinking-budget control and budget
forcing remain separate future controls.

## Reproducibility record

- Comparison artifact:
  `results/phase2/qwen3_0_6b_nonthinking_validation_comparison_v1/`
- Paired table: `paired_thinking_mode_comparison.csv`
- Source hashes and prompt identities: `comparison_manifest.json`
- Machine-readable report: `comparison_report.md`
