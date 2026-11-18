# Sequential Label Audit: Qwen3-0.6B GSM8K Train n=79

Audit date: 2026-11-12  
Status: completed Train evidence; Validation and Test remain unopened

## Decision

The full frozen GSM8K Train partition passes the generation, parser-contract,
provenance, and label-construction gates. It does **not** pass the
pre-registered 30-positive floor for any learned sequential decision.

- Data-pipeline decision: **PASS**.
- Learned joint-controller decision: **NEED MORE DATA / KEEP BREADTH
  HEURISTIC**.
- Validation decision: **do not use it for joint-model selection before the
  policy and baseline definitions are frozen**.
- Test decision: **DO NOT OPEN**.

The next implementation task is policy replay for fixed profiles and the
pre-registered depth-first heuristic. Fitting a per-stage learned joint
controller is not authorized by the current evidence.

## Completed evidence

Source experiment:
`results/qwen3_0_6b_gsm8k_train_n79_contract_v3`

Derived label artifact:
`results/phase2/qwen3_0_6b_gsm8k_n79_sequential_labels_v1`

Integrity checks:

- 79/79 frozen Train problems;
- 948/948 unique generation records;
- 711/711 unique configuration rows;
- 360 exact cache hits and 588 new GPU generations;
- zero generation errors;
- prompt `gsm8k_cot_v3`, parser `gsm8k_numeric_v3`, and the pinned
  Qwen3-0.6B revision;
- 474 depth-label rows and 1,422 breadth-label rows;
- zero held-out Test rows, zero duplicated stage/lambda keys, and zero overlap
  between allowed features and forbidden label/outcome columns;
- hashes recorded for raw samples, configuration results, experiment
  manifest, and frozen split manifest.

## Output-contract audit

Among 685 non-truncated generations, 667 were parseable: 97.37%, above the
pre-registered 90% gate. Across all 948 generations, 18 (1.90%) were
non-truncated but unparseable.

Manual inspection of all 18 cases found:

- 12 explicit final lines used English number words (`Eight` or
  `Three hundred fifty pesos`) instead of the required numeric form;
- 6 final-response lines contained no number, although the hidden reasoning
  contained the correct number.

Parser v3 behaved according to its frozen numeric-only contract. These outputs
remain invalid rather than being silently relabelled after outcome inspection.
No parser amendment is made from this audit. Some breadth rescues therefore
reflect recovery from an invalid answer format, which is a real system-level
benefit but must not be described solely as improved mathematical reasoning.

Raw truncation was 159/316 at `L=512`, 68/316 at `L=1024`, and 36/316 at
`L=2048`.

## Profile and oracle characterization

| Profile | Accuracy | Mean actual generated tokens |
|---|---:|---:|
| `1x512` | 45.6% | 445.0 |
| `1x1024` | 64.6% | 605.6 |
| `1x2048` | 72.2% | 779.3 |
| `2x512` | 54.4% | 890.3 |
| `2x1024` | 70.9% | 1,213.7 |
| `2x2048` | 75.9% | 1,553.8 |
| `4x512` | 64.6% | 1,784.6 |
| `4x1024` | 73.4% | 2,430.9 |
| `4x2048` | 78.5% | 3,058.8 |

The retrospective joint oracle reaches 82.3% at 836.2 mean actual tokens.
This is hindsight opportunity, not deployable-controller evidence.

After family-wise Holm correction, `1x512 -> 1x1024`, `2x512 -> 2x1024`,
and `2x512 -> 4x512` are significant directional comparisons. Other planned
pairwise comparisons are inconclusive and must not be presented as equivalent.

## Sequential label balance

Counts are reported once per stage. The three lambda rows are sensitivity
settings derived from the same outcomes and are not independent examples.

| Stage | Positive | Regression | Unchanged | Positive rate | Wilson 95% interval | Meets 30-positive floor |
|---|---:|---:|---:|---:|---:|---:|
| Depth `L512 -> L1024` | 15 | 0 | 64 | 19.0% | 11.9--29.0% | No |
| Depth `L1024 -> L2048` | 6 | 0 | 73 | 7.6% | 3.5--15.6% | No |
| Breadth `L512, k1 -> k2` | 7 | 0 | 72 | 8.9% | 4.4--17.2% | No |
| Breadth `L512, k2 -> k4` | 8 | 0 | 71 | 10.1% | 5.2--18.7% | No |
| Breadth `L1024, k1 -> k2` | 5 | 0 | 74 | 6.3% | 2.7--14.0% | No |
| Breadth `L1024, k2 -> k4` | 3 | 1 | 75 | 3.8% | 1.3--10.6% | No |
| Breadth `L2048, k1 -> k2` | 3 | 0 | 76 | 3.8% | 1.3--10.6% | No |
| Breadth `L2048, k2 -> k4` | 4 | 2 | 73 | 5.1% | 2.0--12.3% | No |

The point-estimate sample sizes needed to observe 30 positives range from about
158 problems for `L512 -> L1024` to 790 for the rarest breadth stages. These
are planning projections from observed rates, not guaranteed requirements.

Three of the eight positive `L512, k2 -> k4` cases occur among the manually
audited output-format cases. Corresponding format-related rescues also appear
at higher caps. This strengthens the case for including already-paid validity
signals, while weakening any claim that every breadth gain represents a new
reasoning solution.

## Interpretation and authorized next work

Update: item 1 below was completed on 2026-11-12. See
`BASELINE_REPLAY_TRAIN_N79_2026-11-12.md`; the active replay artifact is
`qwen3_0_6b_gsm8k_n79_baseline_replay_v2`.

Completed evidence supports a stable depth effect and sparse, stage-dependent
breadth gains. It does not establish predictability or a deployable Pareto
improvement.

1. Implement replayable fixed-profile and pre-registered depth-first heuristic
   policies with complete actual-token charging.
2. Freeze their trace schema and verify replay exactly reproduces the fixed
   grid endpoints.
3. Prepare a versioned development expansion while preserving the current
   100-problem Test partition untouched.
4. Reassess whether rare breadth stages should remain heuristic, be merged, or
   be removed only through an explicit protocol amendment.
5. Do not fit learned per-stage classifiers, tune on Validation, or inspect
   Test until the applicable readiness gate is satisfied.
