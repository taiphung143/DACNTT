import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { FileBlob, Presentation, PresentationFile } from "@oai/artifact-tool";

const ROOT = "C:\\Users\\taiph\\OneDrive\\Desktop\\DATN\\oracle_experiment";
const TMP_DIR = path.join(ROOT, ".artifact_work", "ppt_build");
const PREVIEW_DIR = path.join(TMP_DIR, "previews");
const FINAL_PPTX = path.join(ROOT, "deliverables", "Trinh_bay_DATN_Adaptive_Test_Time_Compute_v3.pptx");
const SKILL_DIR = "C:\\Users\\taiph\\.codex\\plugins\\cache\\openai-primary-runtime\\presentations\\26.1022.11436\\skills\\presentations";
const RUNTIME_PYTHON = "C:\\Users\\taiph\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe";

const C = {
  navy: "#163B57",
  navy2: "#0D2B3E",
  teal: "#168C89",
  tealLight: "#DDF1EF",
  orange: "#E17A36",
  orangeLight: "#FCEBDE",
  ink: "#18232F",
  muted: "#5D6A75",
  pale: "#F4F7F9",
  line: "#D5DEE5",
  white: "#FFFFFF",
  green: "#2E7D5B",
  greenLight: "#E4F2EA",
  red: "#B64A4A",
  redLight: "#F8E4E4",
  amber: "#A56A19",
  amberLight: "#F7EDD9",
};

const FONT = "Arial";
const W = 1280;
const H = 720;

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

async function readImageBlob(imagePath) {
  const bytes = await fs.readFile(imagePath);
  return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
}

function addShape(slide, geometry, position, fill = "none", lineFill = "none", lineWidth = 0, radius) {
  const cfg = {
    geometry,
    position,
    fill,
    line: { style: "solid", fill: lineFill, width: lineWidth },
  };
  if (radius) cfg.borderRadius = radius;
  return slide.shapes.add(cfg);
}

function addText(slide, text, position, opts = {}) {
  const shape = addShape(slide, "textbox", position, opts.fill ?? "none", opts.lineFill ?? "none", opts.lineWidth ?? 0);
  shape.text = text;
  shape.text.style = {
    typeface: opts.fontFamily ?? FONT,
    fontSize: opts.fontSize ?? 22,
    color: opts.color ?? C.ink,
    bold: opts.bold ?? false,
    italic: opts.italic ?? false,
  };
  return shape;
}

function addRect(slide, position, fill, lineFill = "none", lineWidth = 0, radius) {
  return addShape(slide, radius ? "roundRect" : "rect", position, fill, lineFill, lineWidth, radius);
}

function addSlideBase(pres, title, index, section = "DATN") {
  const slide = pres.slides.add();
  slide.background.fill = C.white;
  addRect(slide, { left: 0, top: 0, width: W, height: 10 }, C.teal);
  addText(slide, title, { left: 62, top: 38, width: 1080, height: 52 }, { fontSize: 42, bold: true, color: C.navy2 });
  addText(slide, section, { left: 64, top: 672, width: 400, height: 20 }, { fontSize: 13, bold: true, color: C.muted });
  addText(slide, String(index).padStart(2, "0"), { left: 1170, top: 669, width: 48, height: 22 }, { fontSize: 14, bold: true, color: C.teal });
  return slide;
}

function addNotes(slide, text) {
  slide.speakerNotes.text = text;
  slide.speakerNotes.setVisible(true);
}

function addMetric(slide, value, label, x, y, color = C.navy) {
  addText(slide, value, { left: x, top: y, width: 250, height: 68 }, { fontSize: 54, bold: true, color });
  addText(slide, label, { left: x + 2, top: y + 67, width: 270, height: 58 }, { fontSize: 20, color: C.muted });
}

function addBand(slide, y, color, label, text, height = 78) {
  addRect(slide, { left: 70, top: y, width: 10, height }, color);
  addText(slide, label, { left: 104, top: y + 8, width: 250, height: 30 }, { fontSize: 21, bold: true, color });
  addText(slide, text, { left: 365, top: y + 5, width: 825, height: height - 8 }, { fontSize: 20, color: C.ink });
}

async function addImage(slide, imagePath, position, alt) {
  slide.images.add({
    blob: await readImageBlob(imagePath),
    contentType: "image/png",
    alt,
    fit: "contain",
    position,
  });
}

async function build() {
  await fs.mkdir(TMP_DIR, { recursive: true });
  await fs.mkdir(PREVIEW_DIR, { recursive: true });
  await fs.mkdir(path.dirname(FINAL_PPTX), { recursive: true });
  const { finalizePresentation, applyPresentationChartFont } = await import(
    pathToFileURL(path.join(SKILL_DIR, "container_tools", "artifact_tool_utils.mjs")).href,
  );

  const pres = Presentation.create({ slideSize: { width: W, height: H } });

  // 1. Cover
  {
    const s = pres.slides.add();
    s.background.fill = C.navy2;
    addRect(s, { left: 0, top: 0, width: 18, height: H }, C.teal);
    addText(s, "ADAPTIVE TEST-TIME COMPUTE", { left: 76, top: 64, width: 660, height: 28 }, { fontSize: 18, bold: true, color: "#86D1CD" });
    addText(s, "Phối hợp breadth và depth\ncho mô hình suy luận nhỏ", { left: 72, top: 138, width: 850, height: 190 }, { fontSize: 64, bold: true, color: C.white });
    addText(s, "Đặc trưng hóa thực nghiệm, baseline controller và bằng chứng demo", { left: 78, top: 356, width: 810, height: 66 }, { fontSize: 25, color: "#D6E3EA" });
    addRect(s, { left: 78, top: 470, width: 460, height: 3 }, C.orange);
    addText(s, "Đinh Hồng Vũ  ·  Phùng Thế Tài  ·  Bùi Thái Sơn", { left: 78, top: 501, width: 650, height: 32 }, { fontSize: 20, bold: true, color: C.white });
    addText(s, "Đại học Tôn Đức Thắng  |  25.10.2026", { left: 78, top: 545, width: 550, height: 28 }, { fontSize: 18, color: "#AFC1CC" });
    addText(s, "BÁO CÁO TIẾN ĐỘ", { left: 965, top: 610, width: 230, height: 30 }, { fontSize: 16, bold: true, color: "#86D1CD" });
    addNotes(s, "Mở đầu trong khoảng 30 giây. Nêu rõ đây là báo cáo tiến độ có bằng chứng đã hoàn thành, kết quả phát triển và kế hoạch confirmatory. Nguồn nội bộ: paper/progress_paper.tex và báo cáo tổng hợp đi kèm.");
  }

  // 2. Research problem
  {
    const s = addSlideBase(pres, "Bài toán nghiên cứu", 2);
    addText(s, "Một cấu hình cố định phân bổ compute giống nhau cho mọi bài, dù độ khó khác nhau.", { left: 68, top: 118, width: 1040, height: 64 }, { fontSize: 28, bold: true, color: C.ink });
    addText(s, "BREADTH", { left: 105, top: 250, width: 250, height: 35 }, { fontSize: 20, bold: true, color: C.teal });
    addText(s, "k", { left: 100, top: 286, width: 110, height: 95 }, { fontSize: 78, bold: true, color: C.navy });
    addText(s, "số sample độc lập", { left: 102, top: 382, width: 250, height: 32 }, { fontSize: 20, color: C.muted });
    addText(s, "×", { left: 390, top: 285, width: 70, height: 86 }, { fontSize: 68, color: C.orange });
    addText(s, "DEPTH", { left: 500, top: 250, width: 250, height: 35 }, { fontSize: 20, bold: true, color: C.orange });
    addText(s, "L", { left: 500, top: 286, width: 110, height: 95 }, { fontSize: 78, bold: true, color: C.navy });
    addText(s, "max new tokens", { left: 502, top: 382, width: 250, height: 32 }, { fontSize: 20, color: C.muted });
    addRect(s, { left: 790, top: 224, width: 4, height: 250 }, C.line);
    addText(s, "Câu hỏi 1", { left: 842, top: 238, width: 170, height: 28 }, { fontSize: 18, bold: true, color: C.teal });
    addText(s, "Với cùng ngân sách k×L, tăng depth hay breadth hiệu quả hơn?", { left: 840, top: 277, width: 350, height: 94 }, { fontSize: 25, bold: true, color: C.ink });
    addText(s, "Câu hỏi 2", { left: 842, top: 395, width: 170, height: 28 }, { fontSize: 18, bold: true, color: C.orange });
    addText(s, "Có thể cấp compute theo từng bài để giữ accuracy và giảm token thực tế?", { left: 840, top: 434, width: 350, height: 100 }, { fontSize: 25, bold: true, color: C.ink });
    addText(s, "Chi phí chính được báo cáo bằng Actual Generated Tokens, không chỉ dùng k×L danh nghĩa.", { left: 70, top: 590, width: 1110, height: 46 }, { fontSize: 22, color: C.navy, bold: true });
    addNotes(s, "Giải thích k là số sample và L là trần token cho mỗi sample. Nhấn mạnh Actual Generated Tokens mới là chi phí đã phát sinh. Hai câu hỏi này dẫn trực tiếp đến grid GSM8K và controller ở Phase 2. Nguồn nội bộ: docs/PHASE2_PROTOCOL.md và paper/progress_paper.tex.");
  }

  // 3. Timeline
  {
    const s = addSlideBase(pres, "Hành trình từ hạ tầng đến bản thảo", 3);
    addText(s, "Bốn mốc công việc tạo thành một chuỗi bằng chứng có thể truy vết.", { left: 70, top: 112, width: 990, height: 42 }, { fontSize: 25, color: C.muted });
    addRect(s, { left: 130, top: 332, width: 1000, height: 5 }, C.line);
    const xs = [150, 455, 760, 1065];
    const colors = [C.teal, C.navy, C.orange, C.green];
    const months = ["08–09/2026", "09/2026", "10/2026", "24.10.2026"];
    const heads = ["Hệ thống", "Phase 1", "Phase 2 + MATH", "Bản giao"];
    const bodies = [
      "CLI, parser, cache, manifest, tests và shared sample pool",
      "Grid GSM8K breadth × depth, iso-budget và oracle",
      "Depth baseline, split đóng băng, pilot MATH-500 và parser v2",
      "Bản thảo LNCS, Word chi tiết, slide và demo xác thực",
    ];
    for (let i = 0; i < 4; i++) {
      addShape(s, "ellipse", { left: xs[i] - 18, top: 315, width: 38, height: 38 }, colors[i], C.white, 3);
      addText(s, months[i], { left: xs[i] - 70, top: 236, width: 145, height: 30 }, { fontSize: 18, bold: true, color: colors[i] });
      addText(s, heads[i], { left: xs[i] - 72, top: 374, width: 190, height: 70 }, { fontSize: 23, bold: true, color: C.navy2 });
      addText(s, bodies[i], { left: xs[i] - 72, top: 448, width: 225, height: 108 }, { fontSize: 18, color: C.ink });
    }
    addText(s, "Nguyên tắc xuyên suốt: dữ liệu sinh, dữ liệu tái xử lý và kết quả tổng hợp phải tách biệt.", { left: 120, top: 598, width: 1040, height: 42 }, { fontSize: 22, bold: true, color: C.navy });
    addNotes(s, "Dùng slide này để kể mạch công việc thay vì liệt kê file. Hệ thống được xây trước, sau đó mới chạy grid, dựng baseline và mở rộng sang MATH. Bản thảo hiện đã có cấu trúc từ Abstract đến Conclusion cùng 15 tài liệu tham khảo. Nguồn nội bộ: README.md, docs/weekly_progress_report_2026-09-27_vi.md và paper/progress_paper.tex.");
  }

  // 4. Compute and pipeline
  {
    const s = addSlideBase(pres, "Cách hệ thống cấp và đo compute", 4);
    addText(s, "Một request tạo sample pool lớn nhất một lần, rồi các profile tái sử dụng tiền tố sample.", { left: 70, top: 110, width: 1080, height: 44 }, { fontSize: 25, color: C.muted });
    const stages = [
      ["01", "Problem", "Câu hỏi + ground truth"],
      ["02", "Generate", "kmax sample tại mỗi L"],
      ["03", "Parse", "Đáp án, token, finish reason"],
      ["04", "Aggregate", "Vote, accuracy, cost"],
    ];
    for (let i = 0; i < stages.length; i++) {
      const x = 70 + i * 300;
      addText(s, stages[i][0], { left: x, top: 218, width: 72, height: 40 }, { fontSize: 28, bold: true, color: i % 2 ? C.orange : C.teal });
      addText(s, stages[i][1], { left: x, top: 270, width: 220, height: 42 }, { fontSize: 29, bold: true, color: C.navy2 });
      addText(s, stages[i][2], { left: x, top: 324, width: 240, height: 72 }, { fontSize: 20, color: C.ink });
      if (i < stages.length - 1) addRect(s, { left: x + 246, top: 294, width: 32, height: 4 }, C.line);
    }
    addRect(s, { left: 70, top: 456, width: 1120, height: 1 }, C.line);
    addMetric(s, "k×L", "ngân sách danh nghĩa", 95, 490, C.teal);
    addMetric(s, "Σ token", "chi phí sinh thực tế", 440, 490, C.orange);
    addMetric(s, "cache", "truy vết tái sử dụng", 790, 490, C.navy);
    addNotes(s, "Giải thích shared sample pool giúp so sánh profile công bằng hơn và tránh sinh lại không cần thiết. Cache provenance, manifest và raw_samples giữ khả năng truy vết. Khi báo cáo chi phí, nhóm cộng token đã thực sự sinh. Nguồn nội bộ: README.md và mã nguồn adaptive_compute.");
  }

  // 5. Reproducibility
  {
    const s = addSlideBase(pres, "Bằng chứng tái lập", 5);
    addMetric(s, "1.200", "generations trong grid GSM8K", 80, 155, C.navy);
    addMetric(s, "134", "automated tests đã pass", 620, 155, C.teal);
    addMetric(s, "9,66 s", "thời gian test suite CPU", 940, 155, C.orange);
    addRect(s, { left: 72, top: 320, width: 1120, height: 2 }, C.line);
    addText(s, "Artifact chính", { left: 76, top: 357, width: 250, height: 36 }, { fontSize: 26, bold: true, color: C.navy2 });
    const rows = [
      ["experiment_manifest.json", "revision model, seed, grid, expected generations"],
      ["raw_samples.jsonl", "response, token count, parser output, cache provenance"],
      ["grid_summary.csv", "accuracy, token thực tế và truncation theo profile"],
      ["oracle_comparison.csv", "upper bound hồi cứu cho breadth và depth"],
    ];
    rows.forEach((r, i) => {
      const y = 410 + i * 52;
      addText(s, r[0], { left: 78, top: y, width: 360, height: 30 }, { fontSize: 19, bold: true, color: i % 2 ? C.teal : C.navy });
      addText(s, r[1], { left: 470, top: y, width: 710, height: 34 }, { fontSize: 19, color: C.ink });
    });
    addNotes(s, "Có thể chạy test suite ngay khi demo. Kết quả kiểm tra ngày 24 tháng 10 là 134 passed trong 9,66 giây. Nói rõ đây là test logic CPU, không phải chạy lại 1.200 inference. Nguồn nội bộ: thư mục tests và kết quả pytest vừa xác thực.");
  }

  // 6. GSM8K design
  {
    const s = addSlideBase(pres, "Thiết kế thí nghiệm GSM8K", 6);
    addText(s, "Qwen3-1.7B  ·  seed 42  ·  stochastic repetition 1", { left: 70, top: 110, width: 850, height: 36 }, { fontSize: 23, bold: true, color: C.muted });
    addText(s, "Grid profile", { left: 74, top: 183, width: 220, height: 32 }, { fontSize: 25, bold: true, color: C.navy2 });
    const cols = ["L = 512", "L = 1024", "L = 2048"];
    const rows = ["k = 1", "k = 2", "k = 4"];
    for (let c = 0; c < 3; c++) addText(s, cols[c], { left: 250 + c * 210, top: 224, width: 180, height: 32 }, { fontSize: 20, bold: true, color: C.teal });
    for (let r = 0; r < 3; r++) {
      addText(s, rows[r], { left: 90, top: 282 + r * 78, width: 120, height: 36 }, { fontSize: 22, bold: true, color: C.navy });
      for (let c = 0; c < 3; c++) {
        addRect(s, { left: 250 + c * 210, top: 272 + r * 78, width: 164, height: 54 }, r === 2 && c === 2 ? C.orangeLight : C.pale, r === 2 && c === 2 ? C.orange : C.line, 1, "rounded-lg");
        addText(s, `profile ${r * 3 + c + 1}`, { left: 279 + c * 210, top: 286 + r * 78, width: 110, height: 24 }, { fontSize: 17, bold: true, color: C.ink });
      }
    }
    addRect(s, { left: 910, top: 188, width: 3, height: 342 }, C.line);
    addMetric(s, "100", "problem lấy từ GSM8K test", 950, 196, C.navy);
    addMetric(s, "99", "problem dùng cho metric chính", 950, 328, C.teal);
    addText(s, "1 problem bị flag và loại trước khi tổng hợp.", { left: 952, top: 468, width: 240, height: 68 }, { fontSize: 19, color: C.muted });
    addText(s, "Tổng cộng 12 sample pool cho mỗi bài theo thiết kế lồng ghép, tương đương 1.200 generations.", { left: 74, top: 586, width: 1110, height: 45 }, { fontSize: 22, bold: true, color: C.navy });
    addNotes(s, "Nêu model revision đã được ghim trong manifest. Có 100 bài lấy mẫu nhưng một bài bị flag và loại, nên accuracy chính tính trên 99 bài. Grid gồm chín profile và tổng số generation là 1.200. Nguồn nội bộ: results/qwen3_1_7b_gsm8k_n100_r1/experiment_manifest.json và grid_summary.csv.");
  }

  // 7. Heatmap
  {
    const s = addSlideBase(pres, "Accuracy tăng theo cả breadth và depth", 7);
    await addImage(s, path.join(ROOT, "results", "qwen3_1_7b_gsm8k_n100_r1", "plots", "accuracy_heatmap.png"), { left: 58, top: 112, width: 760, height: 520 }, "Heatmap accuracy GSM8K theo k và L");
    addText(s, "83,84%", { left: 875, top: 180, width: 280, height: 84 }, { fontSize: 60, bold: true, color: C.orange });
    addText(s, "profile tốt nhất\nk = 4, L = 2048", { left: 880, top: 275, width: 290, height: 78 }, { fontSize: 25, bold: true, color: C.navy2 });
    addRect(s, { left: 874, top: 388, width: 280, height: 2 }, C.line);
    addText(s, "9,09% → 70,71%", { left: 878, top: 420, width: 300, height: 40 }, { fontSize: 27, bold: true, color: C.teal });
    addText(s, "k = 1 khi tăng L từ 512 lên 2048", { left: 880, top: 470, width: 285, height: 62 }, { fontSize: 20, color: C.ink });
    addText(s, "Depth tạo mức tăng lớn nhất trong grid này.", { left: 880, top: 562, width: 300, height: 56 }, { fontSize: 22, bold: true, color: C.navy });
    addNotes(s, "Đọc heatmap theo hàng k và cột L. Accuracy tăng khi tăng cả breadth và depth, nhưng bước tăng theo L nổi bật hơn. Profile k=4, L=2048 đạt 83,84 phần trăm. Nguồn nội bộ: results/qwen3_1_7b_gsm8k_n100_r1/plots/accuracy_heatmap.png và grid_summary.csv.");
  }

  // 8. Iso budget
  {
    const s = addSlideBase(pres, "Cùng ngân sách 2048, depth tốt hơn breadth", 8);
    await addImage(s, path.join(ROOT, "results", "qwen3_1_7b_gsm8k_n100_r1", "plots", "iso_budget_2048.png"), { left: 55, top: 130, width: 770, height: 470 }, "So sánh iso-budget k nhân L bằng 2048");
    addText(s, "4 × 512", { left: 865, top: 150, width: 180, height: 34 }, { fontSize: 22, bold: true, color: C.muted });
    addText(s, "28,28%", { left: 865, top: 190, width: 250, height: 56 }, { fontSize: 45, bold: true, color: C.red });
    addText(s, "85,4% sample bị truncation", { left: 865, top: 250, width: 300, height: 46 }, { fontSize: 20, color: C.ink });
    addRect(s, { left: 865, top: 324, width: 290, height: 2 }, C.line);
    addText(s, "1 × 2048", { left: 865, top: 350, width: 180, height: 34 }, { fontSize: 22, bold: true, color: C.teal });
    addText(s, "70,71%", { left: 865, top: 390, width: 250, height: 56 }, { fontSize: 45, bold: true, color: C.green });
    addText(s, "18,2% sample bị truncation", { left: 865, top: 450, width: 300, height: 46 }, { fontSize: 20, color: C.ink });
    addText(s, "Nhiều quỹ đạo ngắn không đủ tạo đáp án hợp lệ để vote.", { left: 70, top: 615, width: 1080, height: 36 }, { fontSize: 23, bold: true, color: C.navy });
    addNotes(s, "Ba profile đều có k nhân L bằng 2048. k=4, L=512 chỉ đạt 28,28 phần trăm vì 85,4 phần trăm sample bị cắt ngắn. k=1, L=2048 đạt 70,71 phần trăm. Nguồn nội bộ: iso_budget_2048.png và grid_summary.csv.");
  }

  // 9. Oracle headroom
  {
    const s = addSlideBase(pres, "Oracle cho thấy headroom, chưa phải policy deploy", 9);
    await addImage(s, path.join(ROOT, "results", "qwen3_1_7b_gsm8k_n100_r1", "phase1_5", "oracle_budget_frontier.png"), { left: 45, top: 120, width: 640, height: 455 }, "Oracle budget frontier trên GSM8K");
    await addImage(s, path.join(ROOT, "results", "qwen3_1_7b_gsm8k_n100_r1", "phase1_5", "profile_preference_distribution.png"), { left: 710, top: 120, width: 510, height: 455 }, "Phân bố profile tối thiểu giải đúng bài");
    addText(s, "Joint oracle giữ 83,84% accuracy với 1.023,5 token trung bình.", { left: 62, top: 585, width: 610, height: 52 }, { fontSize: 22, bold: true, color: C.navy });
    addText(s, "Trong 83 bài oracle giải được: 70 bài chọn k=1, 13 bài cần k>1.", { left: 716, top: 585, width: 490, height: 58 }, { fontSize: 22, bold: true, color: C.teal });
    addNotes(s, "Oracle nhìn toàn bộ outcome và ground truth sau khi chạy, nên chỉ đo upper bound hồi cứu. So với fixed k=4, L=2048 dùng 4.246,7 token trung bình, joint oracle dùng 1.023,5 token ở cùng accuracy. Phân bố 70 trên 83 bài chọn k=1 cho thấy depth-first hợp lý, nhưng 13 bài vẫn cần breadth. Nguồn nội bộ: phase1_5/oracle_comparison.csv và hai plot trên slide.");
  }

  // 10. Phase 2 baseline with native chart
  {
    const s = addSlideBase(pres, "Phase 2: depth-only giảm token trên Validation", 10);
    addText(s, "Split đóng băng", { left: 72, top: 116, width: 210, height: 34 }, { fontSize: 24, bold: true, color: C.navy2 });
    addText(s, "79 Train", { left: 74, top: 168, width: 180, height: 42 }, { fontSize: 29, bold: true, color: C.navy });
    addText(s, "20 Validation", { left: 260, top: 168, width: 220, height: 42 }, { fontSize: 29, bold: true, color: C.teal });
    addText(s, "100 Test chưa mở", { left: 495, top: 168, width: 280, height: 42 }, { fontSize: 29, bold: true, color: C.red });
    const chart = s.charts.add("bar", {
      position: { left: 75, top: 270, width: 720, height: 310 },
      categories: ["Fixed L=2048", "Depth baseline"],
      series: [{ name: "Token trung bình", values: [1213.05, 1059.45], fill: C.teal }],
      barOptions: { direction: "bar", grouping: "clustered", gapWidth: 55 },
      hasLegend: false,
      xAxis: { visible: true, min: 0, max: 1400, majorGridlines: { style: "solid", fill: C.line, width: 1 }, textStyle: { fill: C.muted, fontSize: 13 } },
      yAxis: { textStyle: { fill: C.ink, fontSize: 14 }, line: { style: "solid", fill: C.line, width: 1 } },
      dataLabels: { showValue: true, position: "outEnd", textStyle: { fill: C.navy2, fontSize: 14, bold: true } },
    });
    chart.name = "Average generated tokens on validation";
    applyPresentationChartFont(chart, { fontFamily: FONT });
    addText(s, "65%", { left: 885, top: 288, width: 260, height: 78 }, { fontSize: 62, bold: true, color: C.green });
    addText(s, "accuracy của cả hai cấu hình\n13/20 bài", { left: 890, top: 365, width: 280, height: 72 }, { fontSize: 22, color: C.ink });
    addText(s, "12,7%", { left: 885, top: 465, width: 260, height: 66 }, { fontSize: 50, bold: true, color: C.orange });
    addText(s, "token ít hơn trên Validation", { left: 890, top: 530, width: 280, height: 44 }, { fontSize: 21, bold: true, color: C.navy });
    addText(s, "Kết quả phát triển: candidate được chọn trên cùng Validation, cần xác nhận một lần trên frozen Test.", { left: 72, top: 615, width: 1110, height: 40 }, { fontSize: 21, bold: true, color: C.red });
    addNotes(s, "Baseline chọn C bằng 1, class weight balanced và q bằng 0,9. Trên Validation, baseline và fixed L=2048 cùng đúng 13 trên 20 bài, nhưng baseline giảm token trung bình từ 1.213,05 xuống 1.059,45. Đây là kết quả phát triển vì candidate được chọn trên chính Validation. Nguồn nội bộ: results/phase2_depth_baseline_v1/development_report.md và data/splits/phase2_gsm8k_split_v1.json.");
  }

  // 11. MATH pilot
  {
    const s = addSlideBase(pres, "Pilot MATH-500", 11);
    await addImage(s, path.join(ROOT, "results", "qwen3_1_7b_math500_depth_pilot_v2_parser_v2", "plots", "depth_effect.png"), { left: 42, top: 114, width: 810, height: 520 }, "Depth diagnostic của pilot MATH-500");
    addText(s, "30 bài", { left: 895, top: 145, width: 250, height: 60 }, { fontSize: 46, bold: true, color: C.navy });
    addText(s, "development stratified", { left: 900, top: 205, width: 270, height: 38 }, { fontSize: 20, color: C.muted });
    addText(s, "6,7%", { left: 895, top: 280, width: 180, height: 55 }, { fontSize: 42, bold: true, color: C.red });
    addText(s, "L = 1024", { left: 900, top: 337, width: 180, height: 32 }, { fontSize: 20, color: C.ink });
    addText(s, "53,3%", { left: 895, top: 404, width: 200, height: 55 }, { fontSize: 42, bold: true, color: C.green });
    addText(s, "L = 4096", { left: 900, top: 461, width: 180, height: 32 }, { fontSize: 20, color: C.ink });
    addText(s, "2048 → 4096: 8 cải thiện, 0 suy giảm; Holm p = 0,015625", { left: 884, top: 535, width: 310, height: 82 }, { fontSize: 20, bold: true, color: C.teal });
    addNotes(s, "Pilot dùng 30 bài phân tầng và k bằng 1. Accuracy tăng từ 6,7 lên 53,3 phần trăm khi L tăng từ 1024 lên 4096, đồng thời truncation giảm từ 93,3 xuống 46,7 phần trăm. So sánh 2048 với 4096 có tám cải thiện và không có suy giảm. Đây vẫn là pilot development. Nguồn nội bộ: results/qwen3_1_7b_math500_depth_pilot_v2_parser_v2 và depth_effect.png.");
  }

  // 12. Parser audit
  {
    const s = addSlideBase(pres, "Parser v2 được kiểm toán mà không chạy lại model", 12);
    addText(s, "Lỗi phát hiện", { left: 74, top: 120, width: 240, height: 34 }, { fontSize: 25, bold: true, color: C.red });
    addText(s, "204₅ bị đọc thành 2045\nDanh sách 3,5,7 bị ghép thành 357", { left: 75, top: 171, width: 480, height: 102 }, { fontSize: 27, bold: true, color: C.ink });
    addRect(s, { left: 630, top: 118, width: 3, height: 390 }, C.line);
    addMetric(s, "90 → 90", "record nguồn và đích", 690, 132, C.navy);
    addMetric(s, "0", "generation field thay đổi", 690, 270, C.teal);
    addMetric(s, "1", "nhãn correctness thay đổi", 690, 405, C.orange);
    addText(s, "Audit giữ nguyên raw response, seed, token, latency và finish reason.", { left: 74, top: 336, width: 500, height: 70 }, { fontSize: 23, color: C.navy, bold: true });
    addText(s, "Run L = 8192", { left: 74, top: 470, width: 240, height: 38 }, { fontSize: 27, bold: true, color: C.navy2 });
    addText(s, "Mới có 11/120 record, chỉ 2 record ở L=8192. Toàn bộ run bị loại khỏi kết luận hiện tại.", { left: 74, top: 520, width: 520, height: 96 }, { fontSize: 22, color: C.red, bold: true });
    addNotes(s, "Parser v2 sửa hai dạng ground truth: hậu tố cơ số và danh sách số. Nhóm tái xử lý 90 record, không thay đổi bất kỳ generation field nào, và chỉ một nhãn correctness đổi. Run L=8192 chưa hoàn tất nên bị loại. Nguồn nội bộ: docs/MATH500_PARSER_V2_AMENDMENT.md và parser_v2_audit.md.");
  }

  // 13. Demo
  {
    const s = addSlideBase(pres, "Demo đã xác thực", 13);
    addText(s, "1  Validate cấu hình", { left: 72, top: 116, width: 320, height: 34 }, { fontSize: 25, bold: true, color: C.teal });
    addRect(s, { left: 72, top: 160, width: 1120, height: 86 }, C.navy2, C.navy2, 1, "rounded-lg");
    addText(s, "python -m adaptive_compute.cli.run_grid --num-problems 3 --k-values 1 2 4\n--l-values 512 1024 2048 --seed 42 --validate-only", { left: 96, top: 176, width: 1075, height: 60 }, { fontSize: 18, color: C.white, fontFamily: FONT });
    addText(s, "9 profile  ·  shared_pool_max_k = 4  ·  expected_unique_generations = 36", { left: 84, top: 257, width: 1040, height: 32 }, { fontSize: 21, bold: true, color: C.navy });
    addText(s, "2  Test suite", { left: 72, top: 315, width: 280, height: 34 }, { fontSize: 25, bold: true, color: C.orange });
    addRect(s, { left: 72, top: 360, width: 515, height: 74 }, C.navy2, C.navy2, 1, "rounded-lg");
    addText(s, "$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'\npython -m pytest -q", { left: 95, top: 374, width: 470, height: 54 }, { fontSize: 18, color: C.white });
    addText(s, "134 passed in 9,66 s", { left: 625, top: 370, width: 420, height: 54 }, { fontSize: 38, bold: true, color: C.green });
    addText(s, "3  Hai ca cứu lỗi", { left: 72, top: 472, width: 320, height: 34 }, { fontSize: 25, bold: true, color: C.navy });
    addText(s, "Depth rescue  gsm8k-test-00028", { left: 74, top: 521, width: 420, height: 30 }, { fontSize: 20, bold: true, color: C.teal });
    addText(s, "L=512 và 1024 bị cắt; L=2048 trả lời đúng 25 sau 1.093 token.", { left: 74, top: 557, width: 500, height: 65 }, { fontSize: 20, color: C.ink });
    addText(s, "Breadth rescue  gsm8k-test-00013", { left: 660, top: 521, width: 450, height: 30 }, { fontSize: 20, bold: true, color: C.orange });
    addText(s, "Ở L=2048, sample đầu không hợp lệ; sample thứ hai giúp k=2 vote đúng 18.", { left: 660, top: 557, width: 500, height: 65 }, { fontSize: 20, color: C.ink });
    addNotes(s, "Demo theo đúng thứ tự trên slide. Validate-only không tải model, cho thấy hệ thống hiểu chín profile và cần 36 generation duy nhất cho ba bài. Sau đó chạy pytest. Nếu còn thời gian, mở raw_samples hoặc config_results của hai case rescue. Nguồn nội bộ: kết quả validate-only và pytest đã chạy lại ngày 24 tháng 10, cùng raw_samples.jsonl.");
  }

  // 14. Evidence status
  {
    const s = addSlideBase(pres, "Trạng thái bằng chứng và giới hạn", 14);
    addBand(s, 126, C.green, "Đã hoàn thành", "Hạ tầng tái lập, grid GSM8K, oracle analysis, depth baseline và pilot MATH có parser audit.", 78);
    addBand(s, 225, C.teal, "Kết quả phát triển", "Baseline giữ 65% accuracy và giảm 12,7% token trên Validation 20 bài.", 78);
    addBand(s, 324, C.amber, "Đang thực hiện", "Breadth stopping, joint controller và run MATH L=8192 chưa hoàn tất.", 78);
    addBand(s, 423, C.red, "Chưa được kết luận", "Frozen Test chưa mở. Oracle không phải policy deploy. MATH pilot chưa chứng minh generalization.", 88);
    addText(s, "Giới hạn chính", { left: 72, top: 555, width: 250, height: 34 }, { fontSize: 25, bold: true, color: C.navy2 });
    addText(s, "Một model, một stochastic repetition, 99 bài GSM8K và 30 bài MATH development.", { left: 320, top: 553, width: 840, height: 58 }, { fontSize: 22, color: C.ink });
    addText(s, "Thông điệp khi trình bày: nói đúng trạng thái bằng chứng quan trọng hơn cố đưa ra kết luận cuối.", { left: 72, top: 628, width: 1100, height: 34 }, { fontSize: 21, bold: true, color: C.navy });
    addNotes(s, "Slide này giúp trả lời phản biện về độ tin cậy. Tách bốn mức trạng thái, đặc biệt không gọi kết quả Validation là kết quả cuối. Frozen Test chỉ được mở sau khi khóa feature, threshold và cấu hình. Nguồn nội bộ: paper/progress_paper.tex và docs/PHASE2_PROTOCOL.md.");
  }

  // 15. Conclusion
  {
    const s = addSlideBase(pres, "Kết luận và bước tiếp theo", 15);
    addText(s, "Kết luận hiện tại", { left: 72, top: 122, width: 320, height: 38 }, { fontSize: 27, bold: true, color: C.teal });
    addText(s, "Vị trí đặt compute quyết định hiệu quả. Trên GSM8K, depth đủ dài tốt hơn nhiều quỹ đạo ngắn cùng ngân sách, nhưng một nhóm nhỏ vẫn cần breadth chọn lọc.", { left: 72, top: 176, width: 560, height: 160 }, { fontSize: 28, bold: true, color: C.navy2 });
    addRect(s, { left: 670, top: 118, width: 3, height: 430 }, C.line);
    addText(s, "Bước tiếp theo", { left: 720, top: 122, width: 280, height: 38 }, { fontSize: 27, bold: true, color: C.orange });
    const next = [
      "Hoàn tất và audit L=8192",
      "Cài breadth-only và joint controller",
      "Khóa feature, threshold và utility",
      "Mở frozen Test đúng một lần",
    ];
    next.forEach((t, i) => {
      addText(s, String(i + 1), { left: 722, top: 184 + i * 76, width: 44, height: 40 }, { fontSize: 27, bold: true, color: i < 2 ? C.teal : C.orange });
      addText(s, t, { left: 780, top: 184 + i * 76, width: 400, height: 52 }, { fontSize: 23, bold: true, color: C.ink });
    });
    addText(s, "Cảm ơn thầy cô và các bạn", { left: 72, top: 482, width: 520, height: 48 }, { fontSize: 34, bold: true, color: C.navy });
    addText(s, "Q&A", { left: 72, top: 552, width: 280, height: 76 }, { fontSize: 58, bold: true, color: C.teal });
    addText(s, "Bản Word chi tiết chứa kịch bản 12–15 phút và câu trả lời phản biện thường gặp.", { left: 720, top: 540, width: 470, height: 80 }, { fontSize: 21, color: C.muted });
    addNotes(s, "Kết bằng hai câu. Compute placement quan trọng hơn chỉ tăng compute, và depth-first là hướng hợp lý trong bằng chứng hiện tại. Tuy vậy, breadth chọn lọc vẫn có giá trị trên 13 trong 83 bài oracle giải được. Sau Q&A, dùng bảng phản biện trong Word nếu cần. Nguồn nội bộ: toàn bộ artifact đã nêu trong báo cáo tổng hợp.");
  }

  if (pres.slides.items.length !== 15) throw new Error(`Expected 15 slides, got ${pres.slides.items.length}`);

  const stagingDir = path.join(TMP_DIR, ".codex-finalizer");
  await fs.mkdir(stagingDir, { recursive: true });
  const candidatePath = path.join(stagingDir, "candidate.pptx");
  await (await PresentationFile.exportPptx(pres)).save(candidatePath);

  const requirements = {
    explicitTotalSlideCount: 15,
    requiredNativeTableOwnerSlides: [],
    requiredNativeChartOwnerSlides: [10],
    materializeLiteralChartWorkbooks: true,
  };
  const result = await finalizePresentation({
    ...requirements,
    workspaceDir: ROOT,
    candidatePath,
    finalPath: FINAL_PPTX,
    pythonExecutable: RUNTIME_PYTHON,
    integrityValidatorPath: path.join(SKILL_DIR, "container_tools", "inspect_presentation_package_integrity.py"),
    layoutValidatorPath: path.join(SKILL_DIR, "container_tools", "inspect_presentation_layout_geometry.py"),
    layoutArgs: ["--expected-slide-size-emu", "12192000,6858000", "--validate-bullet-geometry", "--validate-heading-fit"],
    requiredNativeTableOwnerSlides: [],
    requiredNativeChartOwnerSlides: [10],
    fontPolicy: { basis: "design", families: [FONT] },
    verifyArtifactToolImport: true,
    receiptPath: path.join(stagingDir, `${path.basename(FINAL_PPTX)}.validation.json`),
  });

  const finalPres = await PresentationFile.importPptx(await FileBlob.load(FINAL_PPTX));
  for (const [i, slide] of finalPres.slides.items.entries()) {
    const png = await finalPres.export({ slide, format: "png", scale: 1 });
    await writeBlob(path.join(PREVIEW_DIR, `slide-${String(i + 1).padStart(2, "0")}.png`), png);
  }
  await writeBlob(path.join(TMP_DIR, "deck-montage.webp"), await finalPres.export({ format: "webp", montage: true }));
  console.log(JSON.stringify({ finalPptx: FINAL_PPTX, slideCount: finalPres.slides.items.length, result }, null, 2));
}

build().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
