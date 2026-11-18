# Thesis authoring status

Updated: 2026-11-18

The current 64-page TDTU-formatted complete draft was built successfully with
Tectonic. The final log contains no overfull boxes, undefined references, or
undefined citations. All 64 pages were rendered and visually inspected.
Deliverable: `output/pdf/thesis_tdtu_formatted_2026-11-18.pdf` (SHA-256
`05bc31ab0f481643e1188a9d051f166950b9fc2b22cbf76a75a266e89f2b9b0d`).

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
- Non-thinking mode, native Qwen3 thinking-budget control, budget forcing,
  extra seeds, and a learned controller remain future evaluations rather than
  completed evidence.

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
4. If GPU time remains, run the decoding controls or extra-seed robustness
   checks as separately declared supplementary evaluations; do not overwrite
   or retune the frozen Test-100 evidence.

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
