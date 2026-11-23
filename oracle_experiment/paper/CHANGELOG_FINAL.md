# Final Changelog — 2026-11-21

## Manuscript

- Corrected the false general monotonicity statement in Historical
  Characterization and Appendix A: nested prefix reuse guarantees `k=1`
  monotonicity, not aggregated `k>1` accuracy.
- Preserved the two-sample agreement/fixed-`k=4` theorem after verifying exact
  predictions across all six Test pools.
- Added exact prompt-token definition, Train tertile thresholds, equality
  handling, dataset-specific cap mappings, and Algorithm 1 for the joint policy.
- Added the historical exclusion reason and all-100 sensitivity outcome.
- Clarified why the GSM8K bootstrap interval and Holm-adjusted McNemar decision
  differ, retaining McNemar–Holm as the primary significance decision.
- Added mutually exclusive raw-output status counts and clarified that parse
  failure and truncation rates overlap.
- Added generated-token cost limitations (prefill, KV-cache, batching,
  scheduling, and hardware effects).
- Replaced ambiguous “registered” terminology with “frozen” or “recorded” where
  independent registration evidence is unavailable.
- Narrowed Artifact Availability to the exact contents of the cited public
  commit and disclosed that local freeze dates are not independently timestamped.
- Consolidated the bibliography onto one readable final page; the validated
  paper is 17 pages rather than leaving a sparse 18th page.

## Code and validation

- Added `scripts/final_scientific_audit.py`, which performs a GPU-free
  prediction/statistics/hash audit without modifying experiment records.
- Added machine-readable outputs under `paper/audit_outputs/`.
- Added an aggregation counterexample showing why `k>1` cap monotonicity does
  not follow from nested reuse.
- Added an exhaustive unit test for the two-sample agreement invariant over all
  two-answer/invalid extensions used by the proof.
- Added README instructions for reproducing the final scientific audit and an
  explicit public-artifact limitation.
- Rebuilt the PDF, ran all 205 tests, and visually inspected all 17 final pages.

## Deliberately unchanged

- No experimental outcomes, policies, splits, raw responses, seeds, freeze
  dates, or benchmark labels were modified.
- Qwen3-1.7B and Qwen3-0.6B remain separate evidence strata.
- No repository push, publication, or artifact deletion was performed.
