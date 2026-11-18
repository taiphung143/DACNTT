# Paper Results Integration Report

Date: 2026-11-15

## Scope

Updated `paper_current_revised.tex` from the 2026-11-11 progress state to the completed frozen Qwen3-0.6B two-dataset empirical state. The thesis Research Question, breadth/token-cap terminology, action spaces, and freeze decisions were not redefined.

## Evidence integrated

- GSM8K frozen Test-100 generation and 14-policy replay.
- MATH-500 frozen Test-100 generation and 14-policy replay.
- Pre-Test selections and the registered cross-dataset `PIVOT` decision.
- Paired McNemar/Holm results, Wilson intervals, realized-token costs, latency reductions, and descriptive Test Pareto status.
- The failed learned-controller readiness gate and the negative joint-heuristic result.
- Reproducible Test Pareto figures generated directly from the frozen replay CSV files.
- Complete 14-policy GSM8K and MATH-500 result tables in the paper appendix.
- Wilson 95% intervals for all nine historical grid profiles and the complete
  15-row exact McNemar/Holm comparison table.
- Related work requested by the supervisor: s1, L1, ESC, Inference Scaling
  Laws, Certaindex, and *When More is Less*.

## Claim boundaries preserved

- `fixed_k2_L4096` remains the selected MATH policy; the stronger Test breadth comparator is not used for post-Test reselection.
- The GSM8K joint-versus-selected accuracy comparison is described as inconclusive.
- The MATH joint heuristic is reported as significantly worse than the selected fixed policy and point-dominated.
- Historical Qwen3-1.7B evidence remains a separate stratum.
- Repeated-seed and second-family studies remain future robustness work.
- Budget forcing, Qwen3 native thinking budgets, and non-thinking mode are
  explicitly reported as unevaluated controls rather than implied results.
- The unused lambda-weighted controller objective was removed; the evaluated
  policies are described as deterministic rules.
- Oracle cost now explicitly includes an unsolved-problem fallback and is
  described as conditional on the realized one-seed sample pool.

## Validation

- All 14 policy rows and 13 registered comparisons exist for each frozen replay.
- Reported policy accuracy/token values were cross-checked against the replay CSV files.
- LaTeX labels, references, citations, environments, and braces pass static consistency checks.
- Tectonic 0.15.0 completed with exit code 0 after three reference passes.
- The final PDF contains 17 pages, has no overfull boxes or undefined references, and the revised method, result, appendix, disclosure, and reference pages were visually inspected after rendering at high resolution.
- The complete test set covers 180 tests. On 2026-11-16, all 180 passed
  in the single `oracle_slm` environment after the analysis/controller
  dependencies were installed; see
  `docs/environment_validation_2026-11-16.md`.
- Remaining underfull warnings are non-clipping LNCS page/bibliography spacing warnings.

## Outputs

- Source: `paper/paper_current_revised.tex`
- Figure generator: `adaptive_compute/cli/plot_policy_pareto.py`
- Figure manifest: `paper/figures/policy_pareto_figure_manifest.json`
- Compiled deliverable: `output/pdf/52300058_52300059.pdf`
