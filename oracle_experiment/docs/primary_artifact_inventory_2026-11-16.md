# Primary Artifact Inventory — 2026-11-16

This inventory identifies the frozen artifacts that support the current paper
and the thesis manuscript. SHA-256 values make accidental replacement or
confusion with pilot artifacts detectable.

## Frozen data splits

```text
a052a7e46ec8eb613e63112ed67528c0615a364779b4dac80e3930b69b5bd6e8  data\splits\phase2_gsm8k_split_v1.json
60211c797b68c9c24f097288cd4300ec63536b539eac89bd368ff68fff8b3459  data\splits\math500_split_v1.json
```

## Frozen Test-100 generation evidence

```text
3c06401d38b84465e93e7b65b183a14726aac32de15114a3f523d205ad15c873  results\qwen3_0_6b_gsm8k_test_n100_contract_v3\experiment_manifest.json
6f9cb01039115c810ea1665044c881f42060b4a27b4ceac2d52d6b52aff466f5  results\qwen3_0_6b_gsm8k_test_n100_contract_v3\raw_samples.jsonl
0eb48ce585e64c925ed6a763e62406c94e5b1c2f12629ee6bcc0f58758c1df71  results\qwen3_0_6b_math500_test_n100_contract_v1\experiment_manifest.json
b2d084d86266dfceae8b094f82c374197e5c89622f4c91a69626bcc196fc2095  results\qwen3_0_6b_math500_test_n100_contract_v1\raw_samples.jsonl
```

## Frozen policy replay and statistical evidence

```text
603b74364e36ba5355d36312f90528cda3ebfc17f3690a7e0f9bfb8103b9dafd  results\phase2\qwen3_0_6b_gsm8k_test_n100_policy_replay_v3\replay_manifest.json
9ae6954d209c05571132a46bf5396c600e5e50c2fd5d1213f4095d15f8442c92  results\phase2\qwen3_0_6b_gsm8k_test_n100_policy_replay_v3\policy_summary.csv
0b7895dd2d02d0ed627b280aef06038562b4c3b1320f7e6bc820b80c0be95b99  results\phase2\qwen3_0_6b_gsm8k_test_n100_policy_replay_v3\primary_heuristic_comparisons.csv
68121187ca2d8a87296925f7fc2d7f06df02fbb27b6ece340b42679d63647a54  results\phase2\qwen3_0_6b_math500_test_n100_baseline_replay_v1\replay_manifest.json
20e7f1ab5638123235e804b03737bf1e0b4f2d86fe1b4febe2d4616d8339e901  results\phase2\qwen3_0_6b_math500_test_n100_baseline_replay_v1\policy_summary.csv
e7adc8416546b679c6581ed63cc3221c2b916d770f7e59a6107a75a081b8f6d6  results\phase2\qwen3_0_6b_math500_test_n100_baseline_replay_v1\primary_heuristic_comparisons.csv
```

The complete replay directories also contain trace-level CSV files, policy
configuration, Pareto status, and trace schemas. The hashes above identify the
manifest and the exact files from which the primary paper values are reported.

## Figures and manuscript

```text
a6c7cfee94a88cb8aee98209f6aa89ad60166cbc7b213d409f14111e8c61c9bf  paper\figures\policy_pareto_figure_manifest.json
eccceed0b9265b223c80be53d2a86884e221f0ca55bad7f5ecd6f1add2e0ce26  paper\paper_current_revised.tex
c64e9780e023d75003850e363d55a9d877933eef71dd0bfc67c8c59736f725d5  output\pdf\52300058_52300059.pdf
```

The figure manifest contains hashes for its source replay CSV files and all six
PNG/PDF figure outputs. Test-set Pareto membership is descriptive and must not
be used for post-Test policy reselection.

## Evidence status

- Completed evidence: frozen Test-100 generations, replayed policies,
  statistical comparisons, Pareto figures, and the current 17-page paper.
- Working hypotheses: explanations for dataset-specific breadth/depth behavior
  and the expected effect of truncation-aware decoding.
- Proposed methods: non-thinking, native thinking-budget, and budget-forcing
  controls described in the final two-week plan.
- Future evaluation: additional seeds, other model families, and a learned joint
  controller; these are not completed contributions.
