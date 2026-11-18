# Reference Paper Analysis

Audit date: 2026-11-11  
Reference role: local quality and reporting standard only. No wording, method, figure, table, or claim is reused.

## 1. Bibliographic information

- **Title:** *Academic Query Orchestration: An AI Agent Framework Utilizing RAG and Text-to-SQL*
- **Authors:** Dinh-Hong Vu, Duy Minh Vo, and Vinh The Truong
- **Length:** 15 pages including references
- **Format:** Springer LNCS-style conference paper
- **Core domain:** hybrid question answering over unstructured documents and relational databases in higher education
- **Stated method:** Academic Query Orchestration (AQO), an LLM agent that plans and coordinates a RAG retriever, a safety-constrained SQL executor, and an answer synthesizer

The PDF does not identify a conference decision, publication status, DOI, artifact repository, or released implementation. It is therefore treated as a supervisor-provided manuscript rather than independently verified publication evidence.

## 2. Research problem

The paper addresses a practical information-access problem: university questions may require policy text, private structured records, or both. Existing conversational systems commonly handle only one source type and therefore fail on hybrid questions that require evidence from both modalities (Introduction, pp. 1-2).

## 3. Research gap

The gap is framed as the lack of a flexible, end-to-end agent that can select, sequence, and combine RAG and Text-to-SQL for hybrid university queries. The Related Work section moves through four directions: higher-education chatbots, RAG, Text-to-SQL, and tool-using agents/hybrid architectures (pp. 2-4).

The gap is clear but not expressed as an explicit research question or hypothesis. More importantly, the central hybrid claim is not directly isolated by the reported experiments. WikiEval and HotpotQA evaluate the retrieval/QA path, while Spider evaluates Text-to-SQL. The paper provides practical hybrid examples, but no quantitative hybrid benchmark result appears in Sections 4-5. This does not invalidate the system, but it weakens the evidence for the paper's most distinctive claim.

## 4. Proposed approach

AQO follows a perception-brain-action architecture (Fig. 1, p. 4):

1. A Query Analyst interprets and decomposes the user query.
2. An LLM Orchestrator creates a structured action plan.
3. A Knowledge Retriever handles unstructured evidence.
4. A safety layer validates SQL before an SQL Executor accesses relational data.
5. A Synthesizer combines intermediate results.
6. A feedback loop supplies execution errors or insufficient-answer signals to the planner for up to a bounded number of retries.

The core orchestration logic is controlled by a structured meta-prompt. Table 1 describes role, context, reasoning instructions, and a JSON output constraint (pp. 5-6). Tables 2 and 3 give pseudocode for action-plan generation and execution/self-repair (pp. 6-8).

The method is **prompt- and rule-driven**, not a trained routing model. Gemini 2.5 Flash and Gemini 2.5 Pro serve as interchangeable base LLMs within the same architecture (p. 10).

## 5. Contribution stack

The paper's contribution is substantial mainly because several layers reinforce one another:

1. **Problem formulation:** hybrid academic questions require structured and unstructured evidence.
2. **Method:** an LLM orchestrator creates validated machine-readable plans and invokes appropriate tools.
3. **System architecture:** modular query analysis, retrieval, safe SQL execution, synthesis, and retry logic.
4. **Algorithmic specification:** two pseudocode procedures describe planning and action execution.
5. **Experimental breadth:** three public benchmarks cover RAG faithfulness, multi-hop QA, and Text-to-SQL.
6. **Model comparison:** the same system is tested with Gemini 2.5 Flash and Pro.
7. **Application layer:** three university scenarios illustrate SQL-only, RAG-only, and hybrid use (Fig. 3, p. 14).

### If reduced to only its ML model

Little distinctive contribution would remain. AQO does not introduce or train a new ML model. Its contribution is the composition of a prompted LLM, tool interfaces, validation, feedback, and evaluation. The system and evaluation layers are therefore essential, not decorative.

## 6. System architecture

The architecture is the paper's strongest presentational element. Fig. 1 makes data sources, tool selection, error feedback, and output synthesis visible in one diagram (p. 4). The method section then maps the diagram to component descriptions and pseudocode.

The implementation depth is less clear than the architecture suggests. The paper does not fully specify retriever/index settings, SQL safety rules, prompt text, database schemas, inference parameters, retry statistics, cost, or deployment details. It presents a system design and benchmarked pipeline, but not a deployed production system.

## 7. Experimental setup

### Datasets

| Dataset | Role | Metrics | Location |
|---|---|---|---|
| WikiEval | RAG factual grounding | faithfulness, answer relevancy, context precision, context recall | Sec. 4.1, pp. 9-10 |
| HotpotQA | multi-hop retrieval and synthesis | EM, F1, precision, recall | Sec. 4.1, pp. 9-10 |
| Spider | cross-domain Text-to-SQL | execution accuracy, exact match | Sec. 4.1, p. 10 |

### Models

- Gemini 2.5 Flash
- Gemini 2.5 Pro

### Baselines

The paper uses different baselines for different benchmark blocks:

- WikiEval: RAG_Mistral-FP16 and RAG_Llama3 from prior work (Table 5, p. 11).
- HotpotQA: SAE-large and HGN from prior work (Table 7, p. 12).
- Spider: standalone Gemini Flash/Pro, N-best Rerankers + PICARD, and G3R + LGESQL + ELECTRA (Table 8, p. 13).

These are useful contextual comparisons, but there is no single consistent baseline suite across all experiments.

### Scope summary

- **Number of datasets:** 3
- **Number of base models:** 2, both from the Gemini 2.5 family
- **Major experimental blocks:** 3
- **Ablation study:** none reported
- **Statistical evaluation:** no confidence intervals, significance tests, multiple-seed analysis, or uncertainty analysis reported
- **Cross-domain validation:** yes for Spider's databases and across three task types, but no quantitative cross-dataset transfer experiment
- **Deployed prototype:** no deployment evidence; only a system architecture and practical examples
- **Trained or rule-based:** prompted/rule-based orchestration; no router training

## 8. Main results

- On WikiEval, both AQO variants report faithfulness above 0.98. Pro has higher context precision/recall, while Flash has higher answer relevancy (Tables 4-5, p. 11).
- On HotpotQA, Pro reaches 0.6310 EM and 0.7587 F1; Flash reaches 0.6017 EM and 0.7334 F1. Both trail the two specialized supervised comparison systems (Tables 6-7, pp. 11-12).
- On Spider, AQO improves execution accuracy over the corresponding standalone Gemini configuration: Flash 0.552 to 0.615 and Pro 0.778 to 0.800. AQO + Pro is competitive with the cited 0.806 execution-accuracy result (Fig. 2 and Table 8, pp. 12-13).

The paper states that accuracy and latency were recorded (p. 10), but the reported result tables do not include latency. It also does not quantify error-recovery frequency or the incremental value of the self-repair loop.

## 9. Paper structure and relative emphasis

Approximate section lengths are based on extracted text and page occupancy.

| Section | Approx. share | Purpose | Evidence/visuals |
|---|---:|---|---|
| Abstract | 171 words | problem, gap, solution, mechanism, evaluation, high-level result | no numbers |
| Introduction | 8% of main text | application motivation, modality gap, proposed framework | no explicit contribution list or paper organization |
| Related Work | 13% | connect chatbots, RAG, Text-to-SQL, and agents to the gap | literature synthesis, no comparison table |
| Methodology | 29% | specify architecture, meta-prompt, plan validation, tool execution, feedback | Fig. 1; Tables 1-3 |
| Experiments and Results | 33% | benchmark three capabilities and compare two models/baselines | Tables 4-8; Fig. 2 |
| Practical Examples | 5% | demonstrate intended SQL/RAG/hybrid usage | Fig. 3 |
| Conclusion | 3% | restate method, findings, limitations/future work | short prose |
| References | remaining pages | 19 sources | bibliography |

The expected supervisor-facing pattern appears to be: clear applied problem, integrated system diagram, technically explicit method, several public benchmark blocks, comparative tables, practical examples, and a complete submission-shaped manuscript.

## 10. Abstract analysis

1. **Problem:** students face fragmented structured and unstructured information.
2. **Gap:** existing systems usually handle one modality and fail on hybrid questions.
3. **Solution:** AQO, an AI-agent framework.
4. **Mechanism:** a structured prompt coordinates RAG and safe SQL, then self-repairs.
5. **Evaluation:** established public benchmarks for specialized and hybrid reasoning are claimed.
6. **Results:** competitive specialized-task performance and stronger hybrid performance are claimed qualitatively.
7. **Contribution:** autonomous decomposition and heterogeneous evidence fusion.

The abstract is structurally complete, but it lacks concrete result values and appears to promise a quantitative hybrid benchmark that is not visible in the experiment section. This is a cautionary example: completeness of narrative must be matched by traceable evidence.

## 11. Introduction and Related Work quality bar

The Introduction contains motivation, limitations of direct LLM deployment, a modality gap, and a proposed architecture (pp. 1-2). It does not include explicit research questions, a numbered contribution list, or a paper-organization paragraph.

The Related Work covers four coherent directions and uses each to narrow the hybrid gap (pp. 2-4). It is more than a list of summaries, although it does not directly tabulate differences from the proposed system.

For the Adaptive TTC paper to be at least as complete, its Introduction should include:

- why fixed test-time compute wastes resources or under-serves hard problems;
- why breadth and token caps are not interchangeable;
- the narrowed literature gap around verifier-free sequential joint allocation;
- the exact revised RQs and operational definition of `L`;
- a contribution list separated into completed characterization, proposed method, system artifact, and planned evaluation;
- an evidence-status paragraph that prevents preliminary results from being read as final controller evidence.

Recommended Related Work groups are: Test-Time Scaling; Fixed and Adaptive Self-Consistency; Adaptive Token/Reasoning Budgets; Difficulty-Aware and Marginal-Utility Allocation; Early Stopping and Confidence Signals; Joint Parallel-Sequential Allocation; Small Open-Weight Reasoning Models. The section should end with a comparison paragraph stating the thesis's bounded setting, not an unverified first-work claim.

## 12. Strengths

- Clear applied motivation and a coherent end-to-end story.
- Strong visual architecture and method-to-system mapping.
- Three complementary benchmark blocks rather than a single demonstration.
- Two model configurations under the same architecture.
- Concrete algorithms and machine-readable plan constraints.
- Practical use cases that make the system contribution understandable.
- Complete conference-paper shape with method, experiments, results, examples, conclusion, and references.

## 13. Weaknesses

- No explicit RQs or hypotheses.
- No quantitative hybrid benchmark is visible despite hybrid orchestration being the central claim.
- No ablation of the meta-prompt, agent wrapper, self-repair loop, safety layer, or synthesizer.
- No statistical tests, uncertainty intervals, multiple seeds, or sample-size disclosure in the result tables.
- Limited reproducibility detail: prompts, retrieval configuration, SQL safety policy, inference settings, and code availability are absent.
- Latency is described as recorded but not reported in the shown results.
- Practical examples are demonstrations, not evidence of deployment or user evaluation.
- Limitations are only briefly acknowledged in the conclusion.

## 14. Why the paper appears sufficiently substantial

The paper feels substantial because it stacks a real application problem, an integrated architecture, two algorithm descriptions, three benchmark families, two base models, multiple comparison systems, eight tables, three figures, and practical scenarios. Its breadth and presentation compensate for missing ablation and statistics.

This is an important distinction for the thesis audit: the reference is a useful scope and reporting bar, but the current Adaptive TTC work can exceed it in statistical rigor, cost accounting, protocol control, and reproducibility without copying its breadth or system style.

## 15. Lessons applicable to the thesis

1. Present the thesis as an **adaptive inference framework**, not merely a classifier, but include only components already justified by the RQ.
2. Add a single clear architecture figure that maps feature extraction, policy state, inference execution, stopping/escalation, aggregation, logging, and evaluation.
3. Use at least two complementary datasets for the central controller claim.
4. Report baselines in a consistent hierarchy: fixed, heuristic, depth-only, breadth-only, joint, and oracle.
5. Include ablations that isolate the controller's actual contribution; this is where the thesis should be stronger than the reference.
6. Keep completed evidence, proposed method, and future evaluation visibly separated.
7. Report actual generated tokens and latency, not only nominal budgets.
8. Do not promise cross-dataset, cross-model, or hybrid capability in the abstract unless it appears in the final result tables.
