# Paper Readiness Audit — 2026-11-21

## Verdict

**CONDITIONALLY READY** for the supervisor's next scientific review.

The paper is not yet fully conference-submission ready because the official
venue/page limit is unknown, the current final changes are not in the cited
public commit, and complete result artifacts are not publicly released. The
remaining scientific limitations (one seed, Test-100, Validation-20) are now
disclosed and should not be hidden by stronger wording.

## Supervisor feedback now addressed

- Held-out evaluation and unsolved-problem cost definition.
- Embedded figures, Wilson intervals, McNemar tables, Holm families, discordant
  counts, and problem-level bootstrap intervals.
- Sampling settings, parser behavior, frontier construction, and raw parse/
  truncation reporting.
- Narrow interpretation of the weak prompt-tertile joint heuristic.
- ESC-style breadth stopping described as a prior-art baseline with a structural
  prediction invariant; only token savings/stopping rate are empirical.
- Corrected mathematical claim: zero historical shorter-only counts are
  observed, not guaranteed for `k>1`.
- Exact joint-policy thresholds and algorithm.
- Exclusion reason and all-100 sensitivity result.
- Public-code claim narrowed to what the cited commit actually contains.
- Generated-token cost caveat and AI-use disclosure.

## Partially addressed feedback

1. **Single seed.** The limitation is explicit, but robustness is not measured.
   New seeds should use a new untouched evaluation design if used for a new
   confirmatory claim.
2. **Freeze provenance.** Local manifests and hashes are internally consistent,
   but no external immutable timestamp proves the claimed dates.
3. **Artifact release.** Core code is public. Primary raw results, local freeze/
   replay directories, and force-answer code/data are not in the cited commit.
4. **Model breadth.** 0.6B and 1.7B remain correctly separated, but the evidence
   does not establish a broad model-family claim.

## Remaining rejection risks

- Contribution may be judged incremental because the deployable breadth rule is
  an ESC/Adaptive-Consistency-style baseline and the joint heuristic fails on
  MATH-500. The defensible contribution is the controlled held-out evaluation,
  realized-cost accounting, invariant analysis, and documented failure mode.
- Test sets of 100 and one generation seed limit external validity.
- The post-Validation force-answer Test control is useful but not pristine
  confirmation; reviewers may discount it.
- The public commit is insufficient for full numerical reproduction without the
  omitted result artifacts.
- A venue could reject the 16+ page manuscript on format/length grounds; no
  official target limit is present in the supplied materials.

## Completed before sending the supervisor

- Revised LaTeX built successfully; all 17 rendered pages were inspected.
- No undefined references/citations, overflow, clipped tables, missing figures,
  or abnormal blank pages were found.
- The revised PDF and `FINAL_REVISION_REPORT.md` are ready to send together so
  the corrected monotonicity claim is explicit.

## Mandatory before conference submission

- Select the exact venue and comply with its official page/anonymity/artifact
  rules.
- Commit and publish the final source revision, or change the paper's commit
  citation to the exact public revision that contains it.
- Release a documented, license-compliant minimal artifact package (manifests,
  policy configs, aggregate/prediction-level tables, and reproduction commands),
  or retain a precise non-public limitation statement.
- Prefer at least one additional independent seed or an untouched robustness
  partition if time and compute permit; do not retune on the current Test sets.

## Optional strengthening work

- Add independent seeds for variance estimation.
- Add another small open model only as a separately frozen replication.
- Evaluate a better joint controller only with more Train escalation events and
  a new untouched Test partition.
