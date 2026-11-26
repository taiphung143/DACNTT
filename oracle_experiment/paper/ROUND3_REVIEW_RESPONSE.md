# Round-3 reviewer response

Date: 2026-11-25

## Major comments

| ID | Reviewer concern | Evidence and interpretation | Exact changes | Validation | Status / remaining limit |
|---|---|---|---|---|---|
| M1 | Repository returned 404 although the paper claimed public availability. | Unauthenticated HTTP returned 404. Commit `cd55d...` exists locally and is an ancestor of HEAD `42d1b...`, but later code and artifacts are absent from it. | Artifact Availability now states the repository is not public. Added `release/round3_reproducibility_package/`, checksum manifest, replay guide, missing-artifact list, and Zenodo guide. | 110 packaged files hashed; no raw JSONL, cache, model weight, or credential included. | **PARTIALLY_ADDRESSED**: the false claim is fixed and a local package exists; public access/DOI require author authorization. |
| M2 | Paper was 17 pages; abstract was about 265 words; repeated freeze/Test language. | Official ICCIES 2026 guidance states 12--15 pages. It does not exempt references. | Abstract rewritten; related work and historical Section 5 compressed; detailed historical figures/tables and non-thinking table moved to supplementary; repetition removed. | Main PDF: 15 pages; abstract: 200 words; supplementary: 3 pages. | **FIXED** for the stated page/abstract limits. Venue AI policy remains an author compliance issue. |
| M3 | Only one of six breadth stopping frequencies was reported. | Raw replay traces give complete stop decisions and token costs. | Added all six rates/savings to Section 7.3 and Supplementary Table S4; added `round3_breadth_stopping_rates.csv`. | Six rows present; prediction equality 600/600; all values recomputed from traces. | **FIXED**. |
| M4 | Low-cap conclusions did not reflect force-answer; hard truncation was conflated with reasoning inability. | At MATH k=1,L=1024, force-answer changes 13% to 42% while saving 20.2% tokens. | Abstract labels the control post-hoc; Discussion now separates hard-cap completion failure from reasoning limits and states that policy ranking could change under another decoder. | Stored paired counts, McNemar/Holm values, and source hashes all match. | **FIXED**; no unmeasured 14-policy force-answer ranking is claimed. |
| M5 | `top_k` was unspecified. | Adapter passes temperature/top-p but not top-k. Pinned generation config gives top-k=20. | Section 4.1 now reports top-k=20, temperature=0.7, top-p=0.95, sampling/thinking mode, and provenance. | Local pinned file hash recorded; both Test manifests use the same revision/settings. | **FIXED**. |

## Minor comments

| ID | Reviewer concern | Evidence and interpretation | Exact changes | Validation | Status / remaining limit |
|---|---|---|---|---|---|
| m1 | GSM8K L512 parse failure appeared inconsistent with category counts and rounding. | 233/400 are parse failures. Of seven after-thinking truncations, four are parseable. | Section 7.3 explains overlap and reports two-decimal rates; added parse cross-tab CSV. | Cross-tab sums to 400; 233 parse failures and 224 truncations. | **FIXED**. |
| m2 | Historical 99 versus Train/Validation relationship was unclear. | Historical valid-99 equals Train-79 union Validation-20; the excluded ID is `gsm8k-test-01309`; Test has zero ID/hash overlap. | Added explicit provenance paragraph and partition relationship JSON. | All set/hash overlap checks pass. | **FIXED**. |
| m3 | Actual positive escalation-event counts were omitted. | Per-stage counts range 2--22, all below 30. Labels are marginal-utility targets; correctness changes are separate fields. | Added counts to Policy Selection and a machine-readable CSV. | Recomputed from lambda=0.05 label rows without tripling sensitivity settings. | **FIXED**. |
| m4 | Suggested page corrections for [5]/[8], and missing metadata for [14]/[22]. | Official ACL metadata confirms the manuscript's existing [5]/[8] pages. Certaindex v1 is 2024; MATH has arXiv:2103.03874. | Kept [5]/[8]; changed Certaindex year to 2024; added MATH arXiv locator; created reference report. | Official ACL Anthology and arXiv records checked. | **VERIFIED_NO_CHANGE_NEEDED** for [5]/[8]; **FIXED** for [14]/[22]. |
| m5 | Raster historical figures, small labels, tight Force/delta columns, and layout issues. | Plot sources and CSV data were available. | Historical figures rebuilt as vector PDFs and moved to supplementary; Test Pareto font sizes increased; force-answer table columns separated and delta unit moved to header. | Full 15+3 pages rendered and inspected; no clipping, overflow, blank page, or unreadable label found. | **FIXED**. |
| m6 | Acknowledgements thanked the faculty for supervision while the supervisor is a co-author. | No verified grant/support statement was available. | Removed the acknowledgement; retained conflict-of-interest and AI-use disclosures. | Final PDF inspected. | **FIXED**; authors may add only verified support/funding. |

## Additional observations

| Observation | Response | Status |
|---|---|---|
| One stochastic generation seed | Kept in statistical methods and limitations; oracle described as one-seed opportunity. | Preserved limitation |
| MATH parser exact-match limitations | Parser description retains canonicalization scope and explicitly excludes unrestricted symbolic equivalence. | Preserved limitation |
| Validation n=20 | Policy-selection uncertainty remains explicit. | Preserved limitation |
| Scientific evidence boundaries | Primary Test, historical, Validation control, and post-hoc force-answer evidence remain separated. | Verified |
| Repetitive AI-like writing | Related work and Discussion were rewritten; repeated frozen/pre-Test/structural phrasing was reduced. | Addressed |
| Repository reproducibility | Local replay package and hashes prepared; no public claim remains. | Partial until public release |
| Historical 1.7B vs primary 0.6B | Section 5 is shortened but explicitly remains a separate evidence stratum. | Verified |

## Validation performed

- `python -m pytest -q`: 205 passed, 0 failed, 5 third-party deprecation warnings.
- `python scripts/final_scientific_audit.py`: all reconciliation/hash flags true.
- `python scripts/round3_reviewer_audit.py`: all round-3 checks true.
- Tectonic build: main 15 pages; supplementary 3 pages; no overfull box, missing figure, undefined citation, or undefined reference.

## Final pre-publication addendum (2026-11-26)

- Removed the remaining same-family overclaim (“second small-model family”).
- Corrected supplementary numbering to S1–S4 for sections/tables/figures.
- Rebuilt and visually inspected all 15 main and 3 supplementary pages.
- Rechecked Table 2 spacing and Figure 2 readability without changing data.
- Confirmed 205 tests pass and both scientific audits pass after repository cleanup.
- Venue-policy compliance remains author-controlled: ICCIES prohibits AI-generated
  text and accepts a single PDF, so separate supplementary acceptance and final
  prose compliance require explicit confirmation.
- Visual inspection: all 18 pages rendered; tables, figures, headers, footers, page numbers, and references are readable and unclipped.
