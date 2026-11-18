# GSM8K Policy Freeze v1

Freeze date: 2026-11-12  
Status: frozen; held-out Test not yet executed

## Frozen decision

The deployable candidate is `breadth_only_agreement_L1024_v1`. The fixed
selection rule is:

1. consider only frozen non-fixed deployable policies;
2. maximize Validation accuracy;
3. among accuracy ties, minimize mean actual generated tokens;
4. break any remaining tie by lexical policy ID.

On the 20-problem Validation partition, the selected policy solved 15/20
problems (75%) and used 2,095.85 generated tokens per problem on average.
The joint `depth_first_tertile_validity_agreement_v1` comparator also solved
15/20 but used 2,149.05 mean tokens. The breadth-only candidate therefore
won the pre-Test tie-break by 53.2 mean tokens per problem. This small cost
difference is a point estimate, not a statistically resolved advantage.

The joint `GO` condition was not met on Validation. The joint heuristic is
retained as a frozen research-hypothesis comparator, while a learned joint
controller remains disallowed because the Train stages do not contain the
minimum 30 positive events.

## Frozen experimental contract

- Model: `Qwen/Qwen3-0.6B`
- Model revision: `c1899de289a04d12100db370d81485cdf75e47ca`
- Prompt: `gsm8k_cot_v3`
- Answer parser: `gsm8k_numeric_v3`
- Seed: 42
- Action space: `k in {1,2,4}`, `L in {512,1024,2048}`
- Train prompt-token tertiles: 117 and 132 tokens
- Test partition: 100 frozen problems
- Test problem-ID hash:
  `3325f17a2f8ddf928c1c56a789cfdc69aedd68bbacf25b1302d41f1ea5ff1613`

The freeze bundle is stored at `results/phase2/gsm8k_policy_freeze_v1`.
Its manifest SHA-256 is:

`02dc05c1751bac5311fc2565a52dff645503e7f34ef4888e161ecde9ec306aff`

The bundle contains the byte-frozen policy configuration, trace schema,
Validation policy summary, primary comparisons, source hashes, and hashes of
the replay, aggregation, parser, and prompt implementations. The builder
refuses to overwrite an existing freeze directory.

## Verification

- Train and Validation replay manifests use schema v3.
- Model, revision, prompt, parser, and split hashes match across partitions.
- The Validation policy configuration is byte-identical to the Train policy
  configuration.
- Fixed-profile reconstruction is exact in both replay artifacts.
- The four copied artifact hashes and freeze-manifest hash were independently
  recomputed and matched.
- The software suite passes 164 tests.
- No held-out Test outcome is present in the freeze inputs.

## Scientific interpretation

This freeze supports a confirmatory GSM8K evaluation only. Selection from
20 Validation problems is noisy and optimistic. It does not establish that
breadth-only control is universally superior, does not support a learned
joint-controller claim, and does not complete MATH-500 confirmation.

## Next gate

Run the frozen 100-problem GSM8K Test grid once, then replay all 14 frozen
policies without changing thresholds, policy definitions, prompts, parsing,
or selection rules. Test outcomes must be reported as final evaluation and
must not be used for retuning.
