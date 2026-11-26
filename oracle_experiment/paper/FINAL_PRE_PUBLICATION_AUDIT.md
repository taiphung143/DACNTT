# Final pre-publication audit

Date: 2026-11-26

## Technical corrections completed

- Removed the inaccurate “second small-model family” phrase. The manuscript now
  limits the supporting question to the two evaluated reasoning datasets; 0.6B
  and 1.7B evidence remain explicitly within Qwen3 and are not pooled.
- Corrected supplementary numbering to Sections S1–S4, Figures S1–S2, and
  Tables S1–S4. Main-paper references now agree with rendered captions.
- Increased separation among `Standard`, `Force`, and `Delta` in Table 2 without
  changing any value.
- Confirmed Figure 2 contains all 14 policies per dataset, readable labels,
  vector input, and no overlap in the LNCS page layout.
- Confirmed the historical supplementary figures are vector and readable.

No primary result, split, seed, model revision, threshold, parser outcome,
stored p-value, or provenance hash was changed.

## PDF verification

| Artifact | Pages | Size | SHA-256 |
|---|---:|---:|---|
| Main manuscript | 15 | 139,899 bytes | `BCC77EFCEF588BC65E502807C0BC04054880A703C47205EDB0EE296424DA732D` |
| Supplementary | 3 | 67,826 bytes | `9373B981C41C64E0C5F5B8C35E06EC91D6077DBFAF67B12744A093FEEA300A08` |

The abstract contains 193 mechanically counted words. Tectonic reported no
overfull boxes, missing images, undefined citations/references, or fatal errors.
All 18 pages were rendered at 2x and visually checked; no clipping, overlap,
blank page, broken glyph, or missing figure was observed. Remaining underfull
box warnings are non-fatal and visually acceptable.

## Scientific validation

- Unit tests: 205 passed, 0 failed, 5 dependency deprecation warnings.
- `final_scientific_audit.py`: all stored/recomputed values and hashes matched.
- `round3_reviewer_audit.py`: all checks passed, including six stopping rows,
  600/600 structural prediction equalities, parse reconciliation, split
  relationships, escalation counts, and effective top-k provenance.

## Editorial issue list for author action

The following are not automatically rewritten because final conference prose
must be authored and approved by the authors:

1. Re-read Sections 4.4, 7.1–7.3, 8, and 10 for repeated explanations of the
   structural agreement invariant, frozen/Test provenance, and limitations.
2. Shorten any sentence whose logic the authors cannot defend orally; preserve
   the evidence boundary between primary Test, historical, Validation, and
   post-hoc force-answer results.
3. Confirm the Artifact Availability statement only after the final public
   repository/tag/DOI exists; the current statement correctly says the repo is
   not public.
4. Independently verify every citation and authorship/affiliation detail in the
   camera-ready source.

## Venue-policy blocker

The official ICCIES 2026 page specifies LNCS/LNAI style, 12–15 pages, and one
submitted PDF; the main manuscript meets the page/style constraints. A separate
supplementary PDF must not be assumed acceptable. The same page strictly
prohibits AI-generated text. The existing disclosure must not be removed to
hide assistance, but disclosure does not override that prohibition. Before any
ICCIES submission, the authors must confirm the actual venue/deadline and must
personally rewrite/verify all paper prose to satisfy the policy. ICCIES 2026 was
held in April 2026, so applicability to a new submission in November 2026 also
requires explicit confirmation from the venue or supervisor.

Status: technically publication-ready PDF, but **not submission-ready** until
the author-led prose/policy review and public-artifact decision are complete.
