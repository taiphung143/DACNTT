import fs from "node:fs/promises";
import path from "node:path";
import { Workbook } from "@oai/artifact-tool";

const rows = [
  ["Problem significance", 4, 4, "1-5", "Clear higher-education information-access problem (Introduction, pp. 1-2).", "Resource-efficient reasoning is relevant and measurable."],
  ["Research gap", 4, 3, "1-5", "Clear structured/unstructured integration gap, but central hybrid claim is not directly tested (Related Work, pp. 2-4; Experiments, pp. 9-13).", "Defensible only after narrowing to verifier-free sequential joint allocation."],
  ["RQ clarity", 3, 5, "1-5", "No explicit research questions or hypotheses in the Introduction (pp. 1-2).", "Revised Main RQ, RQ2, and RQ3 are explicit and falsifiable."],
  ["Method novelty", 4, 3, "1-5", "Integrated prompted orchestration system; novelty not isolated by ablation (Secs. 3-4, pp. 4-13).", "Sequential joint formulation is plausible, but generic adaptive allocation has strong prior art."],
  ["Technical depth", 4, 3, "1-5", "Architecture, structured meta-prompt, validation, and two algorithms (Fig. 1; Tables 1-3, pp. 4-8).", "Strong formulation and characterization; central joint controller is not implemented."],
  ["Engineering depth", 4, 4, "1-5", "Modular agent, RAG, safe SQL, synthesis, and retry architecture (Fig. 1 and Table 3, pp. 4, 7-8).", "Adapters, cache, manifests, parsers, runner, controller data, and statistics are implemented."],
  ["Dataset coverage", 5, 2, "1-5", "WikiEval, HotpotQA, and Spider (Sec. 4.1, pp. 9-10).", "GSM8K historical evidence plus a 30-problem MATH development depth pilot; no two-dataset policy test."],
  ["Model coverage", 4, 2, "1-5", "Gemini 2.5 Flash and Pro (Sec. 4.2, p. 10).", "Qwen3-1.7B historical and Qwen3-0.6B current; same family and no cross-family controller result."],
  ["Baseline quality", 4, 3, "1-5", "Several literature baselines and standalone Gemini comparisons (Tables 5, 7, and 8, pp. 11-13).", "Fixed/oracle and historical depth baselines exist; breadth-only and joint baselines remain planned."],
  ["Statistical rigor", 1, 4, "1-5", "No intervals, significance tests, or seed analysis in the reported results (Sec. 4.2, pp. 10-13).", "Wilson intervals, exact McNemar, Holm correction, and paired-bootstrap protocol."],
  ["Efficiency evaluation", 2, 5, "1-5", "Latency is mentioned but not shown in the result tables (Sec. 4.2, pp. 10-13).", "Actual tokens, nominal budget, latency, truncation, and full-policy cost are explicit."],
  ["Ablation readiness", 1, 3, "1-5", "No component ablation is reported in Secs. 3-4 (pp. 4-13).", "Ablations are specified and infrastructure is ready, but controller ablations are not run."],
  ["Generalization", 3, 1, "1-5", "Three task types and two model variants, but no explicit transfer study (Sec. 4, pp. 9-13).", "No controller-level cross-dataset or cross-model result."],
  ["Failure analysis", 2, 4, "1-5", "Only brief discussion of difficult Spider subsets and future work (pp. 12-14).", "Detailed truncation/parser/oracle risks and objective pivot rules; final policy failure cases pending."],
  ["Reproducibility", 2, 5, "1-5", "Limited prompts/configuration and no artifact link visible in Secs. 3-4 (pp. 4-13).", "Pinned revisions, hashes, deterministic seeds, manifests, cache, checkpointing, and 134 passing tests."],
  ["Paper completeness", 4, 3, "1-5", "Complete submission-shaped manuscript through Conclusion and References (pp. 1-15).", "Substantial draft, but the central method and held-out evaluation are unfinished."],
  ["Overall submission readiness", 7.0, 5.5, "0-10", "Complete and broad, with important rigor and evidence gaps.", "Strong foundation; blocker-adjusted score reflects missing joint controller and held-out two-dataset results."]
];

function csvEscape(value) {
  const text = String(value ?? "");
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

const header = ["dimension", "reference_score", "current_thesis_score", "scale", "reference_evidence", "current_thesis_evidence"];
const csv = [header, ...rows].map(row => row.map(csvEscape).join(",")).join("\r\n") + "\r\n";

const workbook = await Workbook.fromCSV(csv, { sheetName: "Readiness scorecard" });
const sheet = workbook.worksheets.getItem("Readiness scorecard");
sheet.getRange("A1:F18").format.font = { name: "Arial", size: 10 };
sheet.getRange("A1:F1").format = {
  fill: "#1F4E78",
  font: { name: "Arial", size: 10, bold: true, color: "#FFFFFF" },
  wrapText: true,
};
sheet.getRange("A2:A18").format.font = { name: "Arial", size: 10, bold: true };
sheet.getRange("B2:C18").format.numberFormat = "0.0";
sheet.getRange("A1:F18").format.verticalAlignment = "center";
sheet.getRange("E2:F18").format.wrapText = true;
sheet.getRange("A1:F18").format.borders = { preset: "inside", style: "thin", color: "#D9E2F3" };
sheet.getRange("A1:F18").format.autofitColumns();
sheet.getRange("A1:A18").format.columnWidth = 28;
sheet.getRange("B1:D18").format.columnWidth = 18;
sheet.getRange("E1:F18").format.columnWidth = 48;
sheet.getRange("A1:F18").format.autofitRows();
sheet.showGridLines = false;
sheet.freezePanes.freezeRows(1);
workbook.recalculate();

const inspection = await workbook.inspect({
  kind: "table",
  range: "Readiness scorecard!A1:F18",
  include: "values,formulas",
  tableMaxRows: 20,
  tableMaxCols: 6,
});
console.log(inspection.ndjson);

const projectRoot = path.resolve("../..");
const outputDir = path.join(projectRoot, "docs/paper_readiness_audit");
await fs.mkdir(outputDir, { recursive: true });
await fs.writeFile(path.join(outputDir, "paper_readiness_scorecard.csv"), csv, "utf8");

const preview = await workbook.render({
  sheetName: "Readiness scorecard",
  range: "A1:F18",
  scale: 1,
  format: "png",
});
await fs.writeFile(
  path.resolve("paper_readiness_scorecard_preview.png"),
  new Uint8Array(await preview.arrayBuffer())
);
