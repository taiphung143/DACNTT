# Round-3 final revision report

Date: 2026-11-25

## Outcome

Ten of the eleven reviewer items are fully fixed or verified. M1 is partially
addressed because the manuscript is now truthful and a local release package is
ready, but making the repository public or creating a DOI requires explicit
author authorization. The paper is ready to return to the lecturer for review.

The main manuscript now has 15 pages including references and a 200-word
abstract, matching the official ICCIES 2026 12--15-page statement. A separate
3-page supplementary PDF contains historical diagnostics and the non-thinking
control. Conference submission still requires author review of the venue's
strict AI-text policy and public-artifact decision.

## Main manuscript changes

- Replaced the public-repository claim with the verified 404/private status.
- Reported effective top-k=20 and the provenance of all sampling controls.
- Defined the historical GSM8K relation to Train/Validation/Test exactly.
- Added positive escalation-label counts for every Train stage.
- Added all six breadth stopping frequencies and token savings.
- Reconciled GSM8K L512 parse failure as 233/400 and standardized percentages.
- Rewrote Discussion around standard hard caps versus force-answer decoding.
- Shortened Abstract to 200 words and Related Work substantially.
- Reduced historical Section 5 and moved detailed controls to supplementary.
- Kept official page ranges for references [5] and [8], corrected the arXiv
  year for Certaindex, and added the MATH arXiv locator.
- Rebuilt historical figures as vector PDFs, enlarged the Test Pareto labels,
  and separated the Force/delta table columns.
- Removed the unverifiable/supervision acknowledgement and retained disclosure
  statements.

## Files added or materially updated

- `paper/paper_current_revised.tex`
- `paper/round3_supplementary.tex`
- `adaptive_compute/cli/plot_policy_pareto.py`
- `scripts/round3_reviewer_audit.py`
- `scripts/build_round3_figures.py`
- `scripts/build_round3_release_package.py`
- `paper/audit_outputs/round3_*`
- `paper/figures/*round3.pdf` and regenerated policy Pareto figures
- `paper/ROUND3_REVIEW_RESPONSE.md`
- `paper/ROUND3_SCIENTIFIC_VALIDATION.md`
- `paper/ROUND3_REFERENCE_VERIFICATION.md`
- `release/round3_reproducibility_package/`
- `release/ZENODO_RELEASE_GUIDE.md`
- `README.md`

No raw generation record, label, split, seed, policy threshold, primary
accuracy, token result, or saved p-value was altered.

## Verification

| Check | Result |
|---|---|
| Unit tests | 205 passed; 0 failed; 5 scikit-learn/SciPy deprecation warnings |
| Final scientific audit | All stored/recomputed values and hashes match |
| Round-3 audit | All checks pass |
| Main PDF | 15 pages; Tectonic success |
| Supplementary PDF | 3 pages; Tectonic success |
| Abstract | 200 words |
| LaTeX diagnostics | No overfull boxes, undefined citations/references, missing figures, or errors; underfull spacing warnings only |
| Visual QA | All 18 pages inspected; no clipping, overlap, blank page, table overflow, or unreadable figure label |
| Release package | 110 hashed files plus checksum manifest; no raw generation JSONL or secrets included |

## Remaining author actions

1. Decide whether and when to make a reviewed repository revision public.
2. Decide whether raw outputs may be distributed; then optionally create a
   Zenodo archive and insert the real DOI only after verification.
3. Confirm any factual funding/support statement before adding an
   Acknowledgements paragraph.
4. Ask the intended venue how its prohibition on AI-generated text applies,
   and revise manually as required before conference submission.

Unrelated pre-existing deletions under `.artifact_work/` and `tmp/` and the
untracked `download.txt` were not restored, modified, or included.
