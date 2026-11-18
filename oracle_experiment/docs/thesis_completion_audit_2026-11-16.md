# Thesis Completion Audit — 2026-11-16

## Decision

The current research evidence is sufficient to begin the final thesis
manuscript. The existing 17-page paper is the authoritative scientific source.
The older Vietnamese aggregate Word report is useful as explanatory material
and a defense script, but it is not a final thesis: it predates the completed
Qwen3-0.6B Test-100 evaluation and still frames the joint controller and Test
evaluation as future work.

## Completed evidence

- frozen Qwen3-0.6B Train, Validation, and Test partitions for GSM8K and
  MATH-500;
- complete one-seed Test-100 generation grids for both datasets;
- replay of 14 registered policies per dataset;
- realized-token and latency accounting;
- Wilson intervals, paired McNemar/Holm comparisons, and problem-level replay
  traces;
- frozen Pareto figures and complete policy tables;
- negative cross-dataset result for the tested joint heuristic;
- positive held-out efficiency results for agreement-based breadth stopping;
- 180/180 repository tests passing in one Python environment;
- explicit limitations and generative-AI-use declaration in the paper.

## Existing document roles

### Research paper

`paper/paper_current_revised.tex` is the scientific source of truth. It already
contains the research question, related work, formalization, experimental
protocol, held-out results, discussion, limitations, appendices, references,
and disclosure statements.

### Vietnamese aggregate Word report

`deliverables/Bao_cao_tong_hop_DATN_Adaptive_Test_Time_Compute.docx` contains
13 explanatory/demo sections, 19 tables, and 5 figures. It is useful for
Vietnamese explanations, architecture description, demo flow, and defense
questions. It should not be submitted unchanged because it was produced before
the final Test evidence and includes outdated sections such as “joint
controller not yet run”, “paper status”, and “next plan”.

## Required final thesis structure

The institution's official cover/front-matter template should control the
format when available. The content should be organized as follows.

1. Front matter: Vietnamese and English titles, author/supervisor information,
   declaration, acknowledgements, Vietnamese abstract, English abstract, table
   of contents, lists of figures/tables, and abbreviation list.
2. Introduction: motivation, problem statement, objectives, revised research
   question and supporting questions, scope, contributions, and chapter map.
3. Background and related work: test-time scaling, self-consistency, adaptive
   stopping, token-budget methods, difficulty-aware allocation, and the precise
   gap addressed by this study.
4. Methodology: breadth and token-cap terminology, cost model, oracle
   definition, parser/aggregation contract, policy families, leakage controls,
   statistics, and evidence-status rules.
5. System design and implementation: package architecture, adapters,
   deterministic seed construction, nested sample reuse, cache/resume,
   manifests, replay, artifact hashes, and test strategy.
6. Experimental design: model revision, hardware/software environment,
   prompts/parsers, dataset splits, action spaces, policy selection, metrics,
   and held-out protocol.
7. Results: historical 1.7B characterization kept separate from the primary
   0.6B evidence; complete GSM8K and MATH-500 held-out results; paired tests;
   compute frontiers; and cross-dataset comparison.
8. Discussion: what is directly observed, plausible explanations, why the
   joint heuristic fails to transfer, and implications for small local models.
9. Threats to validity and limitations: one seed, Test-100 size, single primary
   model family, noisy Validation-20 selection, token cap versus semantic
   depth, one-seed oracle optimism, hardware-specific latency, and missing
   decoding controls.
10. Conclusion and future work: answer the research question narrowly and
    separate completed contributions from proposed repeated-seed, decoding,
    and learned-controller work.
11. Appendices: complete policy tables, statistical comparisons, commands,
    environment validation, frozen artifacts, and reproducibility checklist.

## Content still missing from the final thesis

- institution-specific front matter and formatting;
- a Vietnamese abstract synchronized with the final English abstract;
- a full implementation chapter rather than a short paper methods section;
- consolidated experimental configuration tables;
- a reproducibility appendix based on the new environment validation and
  artifact inventory;
- updated Vietnamese results and discussion based on both frozen Test sets;
- decoding-control results, if completed within the remaining schedule;
- final visual page-by-page QA, reference QA, and defense deck update.

## Claim discipline

### May be claimed as completed

- the implemented evaluation/replay pipeline;
- the two frozen Test-100 evaluations;
- the registered policy comparisons and statistical results;
- the GSM8K and MATH agreement-stopping efficiency observations;
- the failure of the tested joint heuristic to generalize across datasets.

### Must remain interpretation or hypothesis

- why prompt length causes the MATH heuristic failure;
- whether “depth before breadth” remains true after truncation-aware decoding;
- whether the same behavior holds across seeds or model families.

### Must remain future evaluation until run

- non-thinking, native thinking-budget, and budget-forcing controls;
- additional generation seeds;
- a learned joint breadth/token-cap controller;
- Qwen3-1.7B MATH-500 or another model family.

## Immediate authoring order

1. Obtain or identify the official thesis template; until then, author content
   in modular chapter files so formatting can be swapped without rewriting.
2. Draft the introduction, background, methodology, and implementation chapters
   from the frozen paper and repository documentation.
3. Generate experimental tables directly from the frozen CSV/JSON artifacts.
4. Insert the completed Test results and figures, then write discussion and
   limitations around the evidence rather than around the original plan.
5. Add robustness controls only after the primary manuscript is stable enough
   that a failed GPU run cannot endanger submission.
