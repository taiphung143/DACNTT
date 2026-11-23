# Final Revision Report — 2026-11-21

## Scope and source of truth

The audited manuscript is `paper/paper_current_revised.tex`, which builds the
current review PDF. Verification used existing code and artifacts only; no LLM
generation, policy retuning, split change, or raw-record edit was performed.
The reproducible checks are implemented in
`scripts/final_scientific_audit.py`, with outputs in `paper/audit_outputs/`.

## Issue-by-issue disposition

| Issue | Finding from code/data | Revision and evidence | Status |
|---|---|---|---|
| P0.1 depth monotonicity | Prefix reuse guarantees monotonic correctness only for `k=1`. With valid-only voting, `k>1` can flip a correct short-cap vote to an incorrect long-cap vote. All six historical adjacent-depth pairs nevertheless have observed A-only = 0. | Corrected Historical Characterization and Appendix A caption. Added unit counterexample and exhaustive two-sample-stopping invariant test. `historical_paired_verification.csv` reproduces all 15 historical comparisons. | Fixed |
| P0.2 two-sample ESC-style stopping | `choose_agreement_stopping_breadth` stops only when samples 0–1 are valid and equal; aggregation uses lowest-index tie-breaking. In all six dataset/cap pools, every adaptive prediction equals fixed `k=4`. | Preserved as a structural invariant, not an empirical accuracy contribution. `primary_policy_verification.csv` verifies prediction equality on 600/600 problem-policy pairs and records stopping counts/token savings. | Fixed |
| P0.3 joint heuristic description | Prompt tokens are tokenizer input IDs after Qwen chat templating. Inclusive Train tertiles and equality handling are implemented in `policy_replay.py`. | Added exact GSM8K/MATH thresholds, depth mappings, equality rule, stopping logic, voting, and realized-cost accounting as Algorithm 1. | Fixed |
| P0.4 oracle frontier | `phase1_5.py` implements a multiple-choice knapsack: exactly one allowed profile per problem, integer realized-token state, deterministic profile-count tie-break, and post-problem dominance pruning. | Existing paper description was consistent; retained with explicit restricted action-space wording. | Fixed |
| P0.5 McNemar/Holm audit | Historical 6/6/3 families and both 13-comparator Test families reproduce exactly. Thinking/non-thinking and force-answer 3-test families also reproduce exactly from prediction-level config rows. | Exported `historical_paired_verification.csv`, `primary_policy_verification.csv`, and `supplementary_control_verification.csv`. | Fixed |
| P1.1 Wilson/bootstrap interpretation | Stored Wilson and 10,000-resample paired bootstrap values match the analysis code. GSM8K bootstrap CI [1,12] pp excludes zero while Holm-adjusted McNemar is inconclusive. | Added explanation that the unadjusted percentile CI and multiplicity-controlled discordance test answer different questions; McNemar–Holm remains the primary significance decision. | Fixed |
| P0.6 public source claim | GitHub HEAD resolves to the cited commit. The commit contains core code and split definitions, but not the large primary raw results/freeze directories or later force-answer implementation. | Narrowed Artifact Availability; no claim that all artifacts are public. No push or publication was performed. | Fixed |
| P0.7 freeze evidence | Local freeze files are dated 2026-11-12 and 2026-11-14; every referenced frozen/replay file hash rechecks. The dates lack an independent immutable timestamp. | Paper now distinguishes internally consistent author-maintained manifests from independent registration. | Partially Fixed |
| P1.2 parsers/exclusion | GSM8K has explicit-marker parsing; MATH uses last balanced box/hash marker plus conservative normalization; neither uses unrestricted last-number fallback. `gsm8k-test-01309` was versioned in the manual audit before the historical run. Direct arithmetic is 2,180 versus official 2,280. | Added objective reason and sensitivity result: all profile correct counts stay unchanged; denominators change from 99 to 100. | Fixed |
| P1.3 result reconciliation | All headline policy counts and mean tokens match `policy_summary.csv`; every primary paired statistic and Holm value matches prediction-level recomputation. | No outcome number was changed. Audit outputs preserve the reconciliation. | Fixed |
| P1.4 parse/truncation categories | Parse failure and truncation overlap. Exclusive status counts were reconstructed for each 400-trajectory cap. | Added all six exclusive four-way tuples and explicitly stated that published parse/truncation rates are overlapping diagnostics. | Fixed |
| P1.5 primary vs supplementary | Non-thinking is Validation-only. Force-answer is a post-Validation Test control selected after primary Test results were known. | Existing separation retained; source hashes and paired statistics rechecked. | Fixed |
| P1.6–P1.7 scope/contribution | MATH rejects only the evaluated prompt-tertile heuristic; it does not reject joint allocation as a method family. Agreement accuracy equality is structural. | Existing scoped claims retained and terminology tightened from “registered” to “frozen/recorded.” | Fixed |
| P1.8 compute scope | Generated tokens omit prefill, KV-cache, batching/scheduling, and hardware effects. | Added caveat in Metrics and Limitations; latency remains secondary. | Fixed |
| P1.9 visuals/LaTeX | The final source builds without undefined references, overfull boxes, or missing figures. | The 17-page PDF was rendered at 1.6x and every page was inspected; no overlap, clipping, abnormal blank page, or missing figure/table was found. | Fixed |
| P1.10 references | The previously checked [5] and [8] page ranges remain 6919–6932 and 14291–14305. | No unsupported metadata change made. | Fixed |
| P1.11 length/page limit | LNCS class is used, but no official target-conference page limit is identified in the supplied materials. | Important content was not deleted merely to shorten the paper. | Unresolved |

## Files changed or added

- `paper/paper_current_revised.tex`: scientific and reporting corrections.
- `scripts/final_scientific_audit.py`: GPU-free artifact reconciliation.
- `tests/test_aggregation.py`: monotonicity counterexample and breadth invariant.
- `README.md`: audit reproduction and artifact-availability disclosure.
- `paper/audit_outputs/*`: machine-readable validation evidence.
- Final reports: this file, `SCIENTIFIC_VALIDATION.md`,
  `PAPER_READINESS_AUDIT.md`, and `CHANGELOG_FINAL.md`.

## Remaining evidence limits

The paper still has one stochastic generation seed, 100 Test problems per
dataset, no independent timestamp proving the local freeze dates, and no public
release of the complete primary/supplementary result artifacts. These are
reported limitations rather than silently treated as resolved.

## Final validation evidence

- GPU-free audit script: passed; all reported reconciliation flags are `true`.
- Relevant scientific tests: 61 passed.
- Full test suite: 205 passed; five third-party scikit-learn/SciPy deprecation
  warnings only.
- LaTeX: successful Tectonic build; no undefined references/citations,
  overfull boxes, missing files, or TeX errors.
- PDF: 17 pages, all visually inspected after the final build.
