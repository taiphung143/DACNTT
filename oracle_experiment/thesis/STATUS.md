# Thesis authoring status

Updated: 2026-11-20

The current 68-page TDTU-formatted complete draft was built successfully with
Tectonic. The final log contains no overfull boxes, undefined references, or
undefined citations. All 68 pages were rendered and visually inspected.
Deliverable: `output/pdf/thesis_tdtu_formatted_2026-11-20.pdf` (SHA-256
`054573143966F98AAC34A4AF4ADEB6C25BD8DFE12E773C2BC6BD0BBA2E42B0FF`).
The synchronized 18-page paper is
`output/pdf/paper_forceanswer_2026-11-20.pdf` (SHA-256
`7D59A5560CC55D5BE96AE3EB29214EABC635DC00F47D21805DB928A689EFC1FF`).

## Completed in the current draft

- modular XeLaTeX thesis source and TDTU A4 layout (Times New Roman 13 pt,
  1.5-line spacing, institutional margins, and top-centred page numbers);
- official TDTU logo, outer and inner cover, acknowledgements, declaration,
  transparent AI-use disclosure, bilingual abstracts, contents, lists of
  figures/tables, and abbreviations;
- Vietnamese and English titles and abstracts synchronized with frozen
  Test-100 results;
- Chapter 1: motivation, formulation, frozen RQ, objectives, scope, completed
  contributions, methodology overview, and thesis structure;
- Chapter 2: test-time scaling background, adaptive breadth/depth literature,
  learned/joint allocation, small-model setting, and explicit research gap;
- Chapter 3: paired shared-pool design, notation, strict parsing, valid-only
  aggregation, fixed/depth/breadth/joint policy definitions, oracle boundary,
  freeze protocol, metrics, and statistical plan;
- Chapter 4: code architecture, model adapter, immutable manifests,
  checkpoint/cache identity, replay, artifacts, tests, environment, and known
  implementation limits;
- Chapter 5: frozen datasets and splits, Qwen3-0.6B generation settings, action
  spaces, 14-policy registries, Validation selection, freeze decisions, and
  raw-grid completeness checks;
- Chapter 6: historical 1.7B evidence kept separate, two real figures, main
  Test-100 results, Wilson intervals, paired McNemar/Holm comparisons, all 14
  policies for each dataset, and evidence limitations;
- Chapter 7: interpretation of the two resource axes, failure analysis of the
  joint heuristic, implications for small local models, threats to construct,
  internal, external, and conclusion validity, and prioritized evaluations;
- Chapter 8: direct answer to the revised RQ, supported and unsupported claim
  components, completed contributions, practical recommendations, realistic
  future work, and final conclusion;
- result tables generated directly by `scripts/build_thesis_results.py` from
  frozen CSV/JSON artifacts, with source/output hashes stored in
  `thesis/generated/results_generation_manifest.json`;
- cross-document claim audit recorded in
  `docs/THESIS_CLAIM_AUDIT_2026-11-18.md` and checked against the abstracts,
  results, discussion, conclusion, paper, and frozen result artifacts;
- reproducibility appendix tied to the validated Miniconda/CUDA environment;
- complete 22-source bibliography and verified cross-references.
- a Vietnamese 9:40 defense rehearsal script covering all 13 slides, 18 likely
  examiner questions with evidence-bounded answers, claim traps, and a
  pre-defense checklist in `slides/DEFENSE_REHEARSAL_AND_QA_VI.md`.
- a Train-only pooled hierarchical-controller feasibility implementation with
  problem-grouped OOF prediction, complete policy replay, leakage audit and a
  versioned V5 artifact. Learned breadth passes the development gate; the
  hybrid joint candidate remains conditional. This is development evidence
  and has not been added to the frozen Test-100 claims.
- a pre-Validation frozen, one-shot replay of the V5 learned-breadth candidate
  on GSM8K Validation-20 and MATH-500 Validation-20. It reduced mean tokens by
  42.27% and 26.61%, respectively, versus agreement-high, but lost 5 percentage
  points on GSM8K and therefore failed the pre-declared cross-dataset gate.
  Decision: `PIVOT_NO_RESERVE_FOR_THIS_CONTROLLER`; Test/reserve evaluation is
  not authorized. See `docs/LEARNED_BREADTH_VALIDATION_RESULT_2026-11-18.md`.
- a completed paired non-thinking control on both frozen Validation-20
  partitions. It saves 78.03--96.83% of generated tokens but has lower accuracy
  in all six high-L/k profiles; the GSM8K losses are significant after Holm
  correction. This is supplementary development evidence and is not promoted
  to Test-100. See `docs/NON_THINKING_VALIDATION_RESULT_2026-11-19.md`.
- a versioned maximum-budget force-answer implementation with total-budget
  accounting, answer-token reserve, intervention-aware cache identity, and
  immutable manifest fields. Clean Train-3 GPU smokes passed on both datasets:
  GSM8K had 11/12 parse-valid rows and MATH-500 had 12/12, with zero generation
  errors, zero over-cap rows, and zero length-truncated rows. The subsequent
  paired Validation-20 comparisons on both datasets reduced token cost and
  sharply reduced parse/truncation failures. Observed accuracy gaps are
  non-negative in all 12 profiles, including +15--25 percentage points for
  MATH-500 at `L=1024`, but none is significant after Holm correction on 20
  problems. The frozen decision is
  `VALIDATION_PASS_CONFIRMATORY_PROTOCOL_REQUIRED`; this remains supplementary
  evidence and does not authorize Test-100. See
  `docs/BUDGET_FORCING_VALIDATION_RESULT_2026-11-20.md`.
- a separately declared, post-Validation force-answer Test-100 robustness
  evaluation at the constrained caps. Both 400-generation grids passed the
  integrity audit. Compared with paired standard thinking, force-answer saves
  16.1--16.4% tokens on GSM8K and 19.9--20.2% on MATH-500, sharply reduces
  parse/truncation failures, and has positive accuracy gaps in all six
  profiles. GSM8K `k=1` and all MATH-500 gains remain significant after Holm
  correction. Frozen decision: `SUPPORTED_ACROSS_DATASETS`. This does not
  change the primary policy-selection results and is disclosed as selected on
  Validation. See `docs/BUDGET_FORCING_TEST_RESULT_2026-11-20.md`.
- the repaired Miniconda environment passes all 203 automated tests (five
  third-party deprecation warnings) under Python 3.11.15, and `pip check`
  reports no broken requirements.

## Verified primary evidence

- Each primary Test grid contains exactly 1,200 raw records, with zero
  generation errors and zero duplicate generation keys.
- The GSM8K selected breadth-stopping policy reaches 76/100 at 1,994.52 mean
  tokens, matching fixed k=4, L=1024 while reducing token cost by 21.33%.
- The MATH-500 selected fixed k=2, L=4096 policy reaches 66/100; the joint
  heuristic reaches 36/100 and is significantly worse after Holm correction.
- The MATH-500 breadth-stopping comparator reaches 73/100 and matches fixed
  k=4, L=4096 while reducing token cost by 19.96%.
- The excluded `gsm8k-test-01309` item belongs only to the historical 1.7B
  pilot and is not part of the primary 0.6B Test-100 manifest.

## Evidence-status safeguards retained

- Qwen3-0.6B is the primary model; the Qwen3-1.7B run remains historical
  evidence and is not pooled with the main results.
- The combined policy is consistently named a deterministic heuristic, not a
  learned controller.
- The oracle is defined as a one-seed, ground-truth-aware opportunity bound,
  not a deployable policy.
- Validation selection is explicitly separated from frozen Test reporting.
- The learned-breadth threshold was frozen before the one-shot Validation
  replay. The failed gate is retained without Validation-dependent retuning,
  and no reserve/Test claim is made for this controller.
- The pinned Qwen3-0.6B Hugging Face backend exposes thinking/non-thinking mode
  but no native numeric thinking-budget interface. Maximum-budget force-answer
  has passed Train smokes, both Validation-20 usefulness gates, and a separately
  declared paired Test-100 robustness evaluation at constrained caps. Its
  post-Validation selection history is retained explicitly; extra seeds remain
  future evaluations.
  Non-thinking mode is completed on Validation-20 only and remains outside the
  primary Test claims. The learned controller has completed Train-OOF
  feasibility and frozen Validation evidence, but no confirmatory Test evidence.

## Next completion batch

1. Confirm the exact registered major/program label and the advisor's academic
   title with the faculty; the current draft uses `CÔNG NGHỆ THÔNG TIN` and the
   advisor's name without an academic title.
2. Obtain any faculty-specific cover/declaration wording if it differs from the
   university-wide TDTU format, then change front matter only.
3. Rehearse the completed 13-slide defense deck with a timer using
   `slides/DEFENSE_REHEARSAL_AND_QA_VI.md`; the evidence-bounded answers for
   freeze discipline, paired inference, the negative joint result, and missing
   decoding controls are now prepared.
4. Review the integrated force-answer robustness section in the thesis and
   paper with the advisor. Preserve the post-Validation selection disclosure
   and leave the original primary policy-selection claims unchanged.
5. After the decoding-control decision, use remaining GPU time for extra-seed
   robustness checks as a separately declared supplementary evaluation; do not
   overwrite or retune the frozen Test-100 evidence.
6. Do not evaluate or retune the failed learned-breadth candidate on reserve or
   Test. If controller research continues, declare a substantively new method
   and evaluation protocol before training it; otherwise retain the negative
   Validation result as feasibility evidence and prioritize the missing
   decoding controls or extra-seed robustness checks.

## Defense deck

The editable 13-slide defense deck is available at
`output/slides/thesis_defense_qwen3_0_6b_2026-11-18.pptx` (SHA-256
`f719ac9e788f88effa08a6d679e39c8405b7c04016d055efaae93562135df54c`).
It includes speaker notes for every slide and uses the frozen Test-100 figures
and claim boundaries. Microsoft PowerPoint reopened and rendered the final
deck; package and layout validation reported zero findings, and all 13 final
slide renders were visually inspected.

## Template note

The wrapper now follows the university-wide TDTU presentation requirements and
the front-matter sequence in the current official template. The body runs from
Arabic pages 1--44, exceeding the 40-page minimum before the appendix and
references. Faculty-specific wording still needs confirmation; any such change
must remain isolated to the wrapper/front matter and must not alter frozen
scientific claims.

The provisional Windows build copies Times New Roman temporarily from the
system font directory to `.artifact_work/thesis_fonts/` because fontconfig is
unavailable in the current Tectonic shell. The copied font files are build
inputs only and should not be distributed with the repository. A non-Windows
build should point `fontspec` to a locally licensed equivalent font.
