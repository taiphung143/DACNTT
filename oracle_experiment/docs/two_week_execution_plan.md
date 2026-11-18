# Final Two-Week Thesis Completion Plan

Updated: 2026-11-16

## Starting point

The Qwen3-0.6B study already has frozen GSM8K and MATH-500 Test-100 results,
policy replay, statistical comparisons, Pareto figures, and a compiled research
paper. The remaining objective is to turn this evidence into a reproducible,
defensible undergraduate thesis. Existing held-out results must not be used to
retune policies.

## Scope that is frozen

- Primary model: Qwen3-0.6B.
- Primary datasets: GSM8K and MATH-500.
- Primary held-out evaluation: the existing frozen 100-item Test partition per
  dataset.
- Primary claims: empirical comparisons among the evaluated fixed and adaptive
  policies, with uncertainty and limitations reported as currently defined.
- No new learned joint controller is promised because the available development
  data do not support a reliable one.
- No Qwen3-1.7B MATH-500 run is required for thesis completion.

## Days 1--2: reproducibility freeze

1. Complete one Python 3.11 environment containing the inference, analysis,
   plotting, controller-baseline, and test dependencies.
2. Run the complete unit-test suite in that environment and retain the test log.
3. Verify checksums and paths for the final paper, figures, manifests, policy
   definitions, raw results, and derived tables.
4. Update setup and artifact documentation so a reviewer can reproduce analysis
   without rerunning GPU inference.

Exit criterion: all tests pass in one environment and the current primary
results can be regenerated from saved artifacts.

## Days 3--6: complete the thesis manuscript

Build the thesis from the current paper and repository evidence. The manuscript
must include:

- motivation, objectives, revised research questions, and contribution list;
- literature review and a clear research gap;
- system design and implementation details;
- frozen data protocol, split integrity, prompts, parsing, token accounting,
  policy definitions, and statistical methods;
- full GSM8K and MATH-500 results with real figures and tables;
- discussion that separates observed evidence from interpretation;
- threats to validity, limitations, ethical/AI-use declaration, conclusion, and
  future work;
- an appendix containing commands, environment versions, configurations, and
  supplementary policy tables.

All numerical statements must be traceable to a versioned result artifact.

## Days 7--9: priority robustness controls

Implement and run only the decoding controls that directly address the main
review concern:

1. non-thinking mode;
2. Qwen3 native thinking-budget control, if the installed Transformers/model
   interface exposes it reliably;
3. budget forcing or an explicit answer-request mechanism when the reasoning
   cap is reached.

Use Qwen3-0.6B and a bounded, predeclared evaluation design. Do not tune these
controls on the existing Test outcomes. If a clean independent subset cannot be
constructed in time, label comparisons against the frozen Test set as
post-hoc/exploratory and do not promote them to primary claims.

Exit criterion: at least non-thinking and one truncation-aware control are
implemented, tested, and reported, or their infeasibility is documented with
technical evidence.

## Days 10--11: final analysis

1. Regenerate tables and figures from machine-readable artifacts.
2. Add confidence intervals and paired tests where assumptions permit them.
3. Check cost charging for solved and unsolved items and distinguish measured
   policy performance from one-seed oracle upper bounds.
4. If compute remains, repeat only selected representative policies with two
   additional seeds; do not repeat the complete grid at the expense of writing.
5. Integrate robustness results without changing the preregistered primary
   evaluation.

## Days 12--13: thesis quality assurance

- cross-check every number between text, tables, figures, and source artifacts;
- verify citations, figure inclusion, captions, equation symbols, and appendix
  references;
- remove progress-report language and unsupported future-tense claims;
- run a final clean build and inspect every page visually;
- prepare an archived submission package with source, PDF, environment file,
  test log, analysis commands, and result manifests.

## Day 14: defense preparation

- prepare a concise slide deck centered on the research questions, method,
  results, limitations, and contributions;
- prepare answers for truncation bias, oracle optimism, Test-set isolation,
  single-seed uncertainty, controller selection, and model-size limitations;
- rehearse a timed presentation and retain backup copies of the PDF and slides.

## Priority order if time is lost

1. Correct, reproducible thesis manuscript and existing primary results.
2. Non-thinking and truncation-aware decoding controls.
3. Selected repeated-seed checks.
4. Presentation polish.

The following are out of scope unless all four priorities are complete: a new
joint learned controller, a broad hyperparameter search, another model family,
the full Qwen3-1.7B MATH-500 grid, and an 8192-token full-grid experiment.

## Completion standard

The thesis is complete when the submitted manuscript makes only claims supported
by saved artifacts, the code and analysis pass in one documented environment,
the principal reviewer concerns are answered by controls or explicit
limitations, and the project can be defended without describing unfinished work
as a contribution.
