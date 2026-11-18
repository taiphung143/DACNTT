# Thesis claim-to-artifact audit

Date: 2026-11-18

Scope: primary claims used in the thesis abstract, Chapters 1, 5--8, and the
current paper. The audit distinguishes completed evidence from hypotheses and
future evaluation.

## Primary evidence identity

| Field | GSM8K | MATH-500 |
|---|---|---|
| Model | Qwen/Qwen3-0.6B | Qwen/Qwen3-0.6B |
| Full revision | `c1899de289a04d12100db370d81485cdf75e47ca` | same |
| Test experiment | `qwen3_0_6b_gsm8k_test_n100_contract_v3` | `qwen3_0_6b_math500_test_n100_contract_v1` |
| Raw records | 1,200 | 1,200 |
| Generation errors | 0 | 0 |
| Duplicate generation keys | 0 | 0 |
| Registered replay policies | 14 | 14 |
| Selected policy | `breadth_only_agreement_L1024_v1` | `fixed_k2_L4096` |

Primary source artifacts:

- `results/qwen3_0_6b_gsm8k_test_n100_contract_v3/experiment_manifest.json`
- `results/qwen3_0_6b_gsm8k_test_n100_contract_v3/raw_samples.jsonl`
- `results/phase2/qwen3_0_6b_gsm8k_test_n100_policy_replay_v3/policy_summary.csv`
- `results/phase2/qwen3_0_6b_gsm8k_test_n100_policy_replay_v3/primary_heuristic_comparisons.csv`
- `results/phase2/gsm8k_policy_freeze_v1/policy_freeze.json`
- `results/qwen3_0_6b_math500_test_n100_contract_v1/experiment_manifest.json`
- `results/qwen3_0_6b_math500_test_n100_contract_v1/raw_samples.jsonl`
- `results/phase2/qwen3_0_6b_math500_test_n100_baseline_replay_v1/policy_summary.csv`
- `results/phase2/qwen3_0_6b_math500_test_n100_baseline_replay_v1/primary_heuristic_comparisons.csv`
- `results/phase2/math500_policy_freeze_v1/policy_freeze.json`

## Claim audit

| Claim | Artifact result | Evidence status | Allowed wording |
|---|---|---|---|
| GSM8K selected breadth policy reaches 76% | 76/100, Wilson [66.8%, 83.3%], 1,994.52 tokens | Completed primary evidence | State as held-out Test-100 result. |
| GSM8K breadth stopping saves 21.33% tokens vs fixed k=4, L=1024 | 1,994.52 vs 2,535.17 tokens; paired correctness identical (0/0 discordant) | Completed paired evidence | May state same observed correctness vector and lower mean tokens. Do not claim population equivalence. |
| MATH selected policy reaches 66% | 66/100, Wilson [56.3%, 74.5%], 5,141.50 tokens | Completed primary evidence | State as Validation-selected held-out estimate. |
| Joint heuristic fails on MATH-500 | 36/100, 5,788.81 tokens; selected-vs-joint 33/3 discordant; Holm p=2.50e-6 | Completed paired evidence | May state significantly worse and point-dominated. |
| MATH breadth stopping saves 19.96% tokens vs fixed k=4, L=4096 | 8,191.12 vs 10,233.17 tokens; both 73/100 with 0/0 discordant | Completed registered secondary evidence | Call it a comparator/secondary result, not the selected primary estimate. |
| One joint rule improves both datasets | Contradicted by MATH result | Unsupported | State that the cross-dataset joint hypothesis is not supported. |
| Learned controller was implemented and evaluated | Training gate was not met | Not completed | Describe only the interface/data path; do not claim learned-controller results. |
| Oracle is an attainable policy | Oracle uses ground truth and all observed profiles | Forbidden interpretation | Call it a one-seed opportunity bound only. |
| Token cap measures semantic reasoning depth | Hard max_new_tokens also controls completion/truncation | Unsupported construct claim | Use “token cap” or operational shorthand “depth”; explicitly retain the limitation. |
| Results generalize across seeds/models/domains | One seed, one primary revision, two math datasets | Future evaluation | Limit conclusions to tested conditions. |

## Cross-document consistency checks

- The Vietnamese and English abstracts use 76%, 66%, 36%, 21.3%, and
  approximately 20%, consistent with frozen summaries.
- Chapter 1 contributions, Chapter 6 results, Chapter 7 discussion, Chapter 8
  conclusion, and the paper all reject a general cross-dataset joint claim.
- The MATH 73% breadth result is consistently labelled a registered comparator,
  while fixed k=2, L=4096 remains the Validation-selected primary policy.
- Qwen3-1.7B is consistently historical/pilot evidence and is not pooled with
  the Qwen3-0.6B primary study.
- `gsm8k-test-01309` belongs to the historical pilot exclusion and is absent
  from the primary Qwen3-0.6B Test-100 manifest.
- Non-thinking mode, native Qwen3 thinking-budget control, budget forcing,
  repeated seeds, learned controller fitting, and second-family evaluation are
  consistently labelled future evaluation.

## Reproduction guard

`scripts/build_thesis_results.py` validates raw-grid completeness, policy IDs,
freeze selection, Test partition size, and source hashes before regenerating
the thesis tables. Its output manifest is
`thesis/generated/results_generation_manifest.json`.

