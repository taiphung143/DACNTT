from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".artifact_work" / "docx_deps"))

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


OUTPUT = ROOT / "deliverables" / "Bao_cao_tien_do_tuan_2026-11-04_Qwen3_0_6B.docx"
FIGURE = (
    ROOT
    / "results"
    / "qwen3_0_6b_math500_depth_pilot_v1"
    / "plots"
    / "depth_effect.png"
)

NAVY = "17365D"
PALE_BLUE = "EAF2F8"
LIGHT_GRAY = "D9D9D9"
MID_GRAY = "666666"
BLACK = "000000"
WHITE = "FFFFFF"


def set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def prevent_row_split(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    cant_split = OxmlElement("w:cantSplit")
    tr_pr.append(cant_split)


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=90, start=100, bottom=90, end=100) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for margin, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{margin}"))
        if node is None:
            node = OxmlElement(f"w:{margin}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_borders(table, color: str = LIGHT_GRAY, size: str = "6") -> None:
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.find(qn("w:tblBorders"))
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = qn(f"w:{edge}")
        node = borders.find(tag)
        if node is None:
            node = OxmlElement(f"w:{edge}")
            borders.append(node)
        node.set(qn("w:val"), "single")
        node.set(qn("w:sz"), size)
        node.set(qn("w:space"), "0")
        node.set(qn("w:color"), color)


def set_font(run, name: str = "Arial", size: float | None = None, bold=None, color: str | None = None) -> None:
    run.font.name = name
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:ascii"), name)
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:hAnsi"), name)
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if color is not None:
        run.font.color.rgb = RGBColor.from_string(color)


def add_page_number(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    fld_char1 = OxmlElement("w:fldChar")
    fld_char1.set(qn("w:fldCharType"), "begin")
    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = " PAGE "
    fld_char2 = OxmlElement("w:fldChar")
    fld_char2.set(qn("w:fldCharType"), "end")
    run._r.append(fld_char1)
    run._r.append(instr_text)
    run._r.append(fld_char2)
    set_font(run, size=9, color=MID_GRAY)


def add_paragraph(doc, text: str = "", *, bold_prefix: str | None = None, italic: bool = False):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(5)
    p.paragraph_format.line_spacing = 1.15
    if bold_prefix and text.startswith(bold_prefix):
        r1 = p.add_run(bold_prefix)
        set_font(r1, size=10.5, bold=True)
        r2 = p.add_run(text[len(bold_prefix) :])
        set_font(r2, size=10.5)
        r2.italic = italic
    else:
        r = p.add_run(text)
        set_font(r, size=10.5)
        r.italic = italic
    return p


def add_bullet(doc, text: str, level: int = 0):
    style = "List Bullet" if level == 0 else "List Bullet 2"
    p = doc.add_paragraph(style=style)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.1
    r = p.add_run(text)
    set_font(r, size=10.3)
    return p


def add_numbered(doc, text: str):
    p = doc.add_paragraph(style="List Number")
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.1
    r = p.add_run(text)
    set_font(r, size=10.3)
    return p


def add_table(doc, headers: list[str], rows: list[list[str]], widths: list[float], alignments=None):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_borders(table)
    set_repeat_table_header(table.rows[0])
    prevent_row_split(table.rows[0])
    for i, (cell, header, width) in enumerate(zip(table.rows[0].cells, headers, widths)):
        cell.width = Inches(width)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        set_cell_shading(cell, NAVY)
        set_cell_margins(cell)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        r = p.add_run(header)
        set_font(r, size=9.2, bold=True, color=WHITE)
    for row_index, values in enumerate(rows):
        row = table.add_row()
        prevent_row_split(row)
        for col_index, (cell, value, width) in enumerate(zip(row.cells, values, widths)):
            cell.width = Inches(width)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            set_cell_margins(cell)
            if row_index % 2 == 1:
                set_cell_shading(cell, PALE_BLUE)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.05
            if alignments and alignments[col_index] == "left":
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(str(value))
            set_font(r, size=9.2)
    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_after = Pt(1)
    return table


def configure_document(doc: Document) -> None:
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(0.68)
    section.bottom_margin = Inches(0.65)
    section.left_margin = Inches(0.72)
    section.right_margin = Inches(0.72)

    normal = doc.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = RGBColor.from_string(BLACK)
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Arial")
    normal.paragraph_format.space_after = Pt(5)
    normal.paragraph_format.line_spacing = 1.15

    title = doc.styles["Title"]
    title.font.name = "Arial"
    title.font.size = Pt(21)
    title.font.bold = True
    title.font.color.rgb = RGBColor.from_string(BLACK)
    title._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
    title._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
    title._element.rPr.rFonts.set(qn("w:eastAsia"), "Arial")
    title.paragraph_format.space_after = Pt(8)
    title_p_pr = title._element.get_or_add_pPr()
    title_border = title_p_pr.find(qn("w:pBdr"))
    if title_border is not None:
        title_p_pr.remove(title_border)

    for style_name, size, before, after in (
        ("Heading 1", 14, 12, 5),
        ("Heading 2", 11.5, 8, 3),
    ):
        style = doc.styles[style_name]
        style.font.name = "Arial"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(BLACK)
        style._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Arial")
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True

    header = section.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = header.add_run("Adaptive Test-Time Compute for Small Reasoning Models")
    set_font(run, size=8.5, color=MID_GRAY)
    add_page_number(section.footer.paragraphs[0])


def build_report() -> None:
    doc = Document()
    configure_document(doc)
    doc.core_properties.title = "Báo cáo tiến độ khóa luận tuần 04 tháng 11 năm 2026"
    doc.core_properties.subject = "Adaptive Test-Time Compute for Small Reasoning Models"
    doc.core_properties.author = "The-Tai Phung và Thai-Son Bui"

    title = doc.add_paragraph(style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.add_run("Báo cáo tiến độ khóa luận tuần 04 tháng 11 năm 2026")

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.paragraph_format.space_after = Pt(3)
    r = subtitle.add_run("Adaptive Test-Time Compute for Small Reasoning Models")
    set_font(r, size=13, bold=True)

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta.paragraph_format.space_after = Pt(12)
    r = meta.add_run(
        "Nhóm thực hiện: The-Tai Phung, Thai-Son Bui\n"
        "Giảng viên hướng dẫn: Dinh-Hong Vu"
    )
    set_font(r, size=9.8, color=MID_GRAY)

    doc.add_heading("Tóm tắt tiến độ tuần", level=1)
    add_paragraph(
        doc,
        "Tuần này nhóm đã hoàn tất chuyển track thực nghiệm từ Qwen3-1.7B sang "
        "Qwen3-0.6B vì chi phí của mức L=8192 trên GPU RTX 4060 không phù hợp với "
        "tiến độ khóa luận. Pipeline đã được kiểm chứng lại, pilot 3 bài và full "
        "pilot 30 bài MATH-500 đều hoàn thành không có lỗi. Kết quả mới đã đủ để "
        "đưa vào paper dưới nhãn development evidence, nhưng chưa phải held-out "
        "test hay kết luận cuối cùng của đề tài."
    )

    doc.add_heading("Công việc đã hoàn thành", level=1)
    doc.add_heading("Chuyển sang Qwen3 0 6B", level=2)
    add_paragraph(
        doc,
        "Thử nghiệm L=8192 với Qwen3-1.7B được dừng sau hai trajectory hoàn chỉnh. "
        "Hai lượt này lần lượt mất 11,63 và 27,10 phút nhưng vẫn bị truncation trước "
        "khi có đáp án cuối. Nhóm chọn Qwen3-0.6B thay vì chuyển sang Qwen2.5-0.5B "
        "để giữ cùng họ Qwen3, chat template và thinking mode. Revision được khóa "
        "tại c1899de289a04d12100db370d81485cdf75e47ca."
    )
    add_bullet(doc, "Giữ nguyên toàn bộ artifact 1.7B như bằng chứng lịch sử theo model.")
    add_bullet(doc, "Không gộp accuracy, oracle label, controller target hoặc latency giữa 1.7B và 0.6B.")
    add_bullet(doc, "Loại L=8192 khỏi protocol 0.6B hiện tại; giữ L thuộc {1024, 2048, 4096}.")

    doc.add_heading("Kiểm chứng kỹ thuật sau chuyển model", level=2)
    add_bullet(doc, "Model 0.6B tải thành công trên CUDA với bfloat16 và thinking mode.")
    add_bullet(doc, "Bộ kiểm thử phần mềm hoàn tất với 134 test đạt.")
    add_bullet(doc, "Pilot 3 bài tạo đủ 9 trên 9 generation, không lỗi và không thiếu checkpoint.")
    add_bullet(doc, "Full pilot tạo đủ 90 trên 90 record duy nhất, gồm 81 generation mới và 9 cache hit đúng revision, không có generation error.")
    add_paragraph(
        doc,
        "Microbenchmark 256 token đo được 22,26 token mỗi giây cho 0.6B và 22,45 "
        "token mỗi giây cho 1.7B. Vì vậy nhóm không tuyên bố model nhỏ hơn có raw "
        "decoding throughput cao hơn; lợi ích thực tế cần được đánh giá bằng chi phí "
        "end-to-end và độ dài output."
    )

    doc.add_heading("Kết quả thực nghiệm mới", level=1)
    add_paragraph(
        doc,
        "Thực nghiệm dùng 30 bài MATH-500 đã đóng băng, được phân tầng theo chủ đề "
        "và mức độ khó. Mỗi bài chạy một trajectory tại ba token cap, với temperature "
        "0,7, top-p 0,95, seed 42 và parser math500_exact_v2. Tổng latency generation "
        "của 90 record là 1,79 giờ."
    )
    add_table(
        doc,
        ["L", "Đúng", "Accuracy", "Wilson 95% CI", "Token TB", "Latency TB", "Truncation"],
        [
            ["1024", "3/30", "10,0%", "3,5% - 25,6%", "984,9", "38,4 giây", "90,0%"],
            ["2048", "11/30", "36,7%", "21,9% - 54,5%", "1.764,4", "66,8 giây", "60,0%"],
            ["4096", "15/30", "50,0%", "33,2% - 66,8%", "2.804,0", "109,7 giây", "43,3%"],
        ],
        [0.55, 0.62, 0.82, 1.25, 0.9, 1.05, 0.9],
    )
    add_paragraph(
        doc,
        "Kết quả kiểm định. So sánh ghép cặp L=1024 với L=2048 tăng 26,7 điểm phần "
        "trăm, có ý nghĩa sau Holm correction với p=0,015625. So sánh L=2048 với "
        "L=4096 tăng 13,3 điểm phần trăm nhưng chưa có ý nghĩa thống kê với p=0,125. "
        "Kết quả inconclusive không chứng minh hai mức tương đương."
    )

    if FIGURE.exists():
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.keep_with_next = True
        p.add_run().add_picture(str(FIGURE), width=Inches(6.65))
        cap = doc.add_paragraph()
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap.paragraph_format.space_after = Pt(6)
        r = cap.add_run("Hình 1  Kết quả depth-cap exploratory pilot với Qwen3-0.6B")
        set_font(r, size=9, color=MID_GRAY)
        r.italic = True

    doc.add_heading("So sánh mô tả với track Qwen3 1 7B", level=1)
    add_table(
        doc,
        ["Model", "L", "Accuracy", "Truncation", "Token TB", "Latency TB"],
        [
            ["Qwen3-1.7B", "1024", "6,7%", "93,3%", "1.016,9", "54,1 giây"],
            ["Qwen3-0.6B", "1024", "10,0%", "90,0%", "984,9", "38,4 giây"],
            ["Qwen3-1.7B", "2048", "26,7%", "73,3%", "1.825,2", "104,6 giây"],
            ["Qwen3-0.6B", "2048", "36,7%", "60,0%", "1.764,4", "66,8 giây"],
            ["Qwen3-1.7B", "4096", "53,3%", "46,7%", "3.077,4", "161,9 giây"],
            ["Qwen3-0.6B", "4096", "50,0%", "43,3%", "2.804,0", "109,7 giây"],
        ],
        [1.35, 0.65, 0.95, 1.0, 1.0, 1.15],
    )
    add_paragraph(
        doc,
        "Hai track dùng cùng 30 bài và cùng parser v2 nhưng thuộc hai model revision "
        "khác nhau. 0.6B đạt accuracy cao hơn ở hai cap thấp, thấp hơn 3,3 điểm tại "
        "L=4096 và có latency end-to-end thấp hơn trong pilot này. Do chỉ có một "
        "generation repetition, các số liệu trên chỉ là so sánh mô tả, không phải "
        "bằng chứng model 0.6B tốt hơn 1.7B."
    )

    doc.add_heading("Phân loại trạng thái bằng chứng", level=1)
    add_table(
        doc,
        ["Trạng thái", "Nội dung hiện tại"],
        [
            ["Đã hoàn thành", "Migration có version; smoke pilot 3 bài; full pilot 30 bài Qwen3-0.6B; audit metric và kiểm định; cập nhật paper."],
            ["Bằng chứng lịch sử", "Grid GSM8K, oracle analysis, depth-only Validation và MATH-500 pilot của Qwen3-1.7B."],
            ["Working hypothesis", "Token cap đủ lớn nên được ưu tiên trước khi tăng breadth; tín hiệu depth-benefiting có thể hỗ trợ controller."],
            ["Phương pháp đề xuất", "Sequential joint controller chọn initial L rồi chỉ mua thêm sample khi marginal utility dự đoán vượt chi phí."],
            ["Đánh giá tương lai", "Tái sinh label 0.6B trên GSM8K và MATH; huấn luyện controller; đánh giá Validation và frozen Test."],
        ],
        [1.45, 5.55],
        ["left", "left"],
    )

    doc.add_heading("Nội dung paper đã cập nhật", level=1)
    add_bullet(doc, "Abstract được cập nhật bằng kết quả Qwen3-0.6B và trạng thái kiểm định.")
    add_bullet(doc, "Experimental Setup tách rõ track lịch sử 1.7B và track phát triển 0.6B.")
    add_bullet(doc, "Bảng MATH-500 được thay bằng kết quả 0.6B, đồng thời giữ số liệu 1.7B trong phần so sánh mô tả.")
    add_bullet(doc, "Discussion, Limitations, Planned Evaluation và Conclusion được sửa để không mô tả 0.6B như công việc tương lai đã chưa thực hiện.")
    add_bullet(doc, "Paper ghi rõ nhãn, threshold và controller coefficient của 1.7B không được chuyển sang 0.6B.")

    doc.add_heading("Hạn chế hiện tại", level=1)
    add_bullet(doc, "MATH-500 mới có 30 bài development và một generation seed.")
    add_bullet(doc, "Kết quả 2048 đến 4096 chưa đủ ý nghĩa thống kê dù accuracy tăng 13,3 điểm phần trăm.")
    add_bullet(doc, "43,3% trajectory vẫn truncation tại L=4096, nên action space chưa thể rút gọn chỉ dựa trên pilot này.")
    add_bullet(doc, "Controller và label hiện có thuộc 1.7B; chưa có controller 0.6B hay held-out result.")
    add_bullet(doc, "Hai model đều thuộc họ Qwen3 nên chưa có bằng chứng cross-family generalization.")

    doc.add_heading("Kế hoạch tuần tiếp theo", level=1)
    add_numbered(doc, "Giữ action space MATH-500 của 0.6B tại L thuộc {1024, 2048, 4096}; tiếp tục loại 8192.")
    add_numbered(doc, "Tái sinh characterization và controller label cho Qwen3-0.6B trên frozen GSM8K development split.")
    add_numbered(doc, "Chuẩn bị depth-only baseline 0.6B trước khi triển khai breadth và joint controller.")
    add_numbered(doc, "Theo dõi số positive escalation event; chưa huấn luyện breadth decision nếu chưa đủ dữ liệu.")
    add_numbered(doc, "Chỉ mở frozen Test sau khi model, parser, feature contract, threshold và go/pivot criteria đã được khóa.")

    doc.add_heading("Tóm tắt trình bày với giảng viên", level=1)
    p = add_paragraph(
        doc,
        "Tuần này nhóm xử lý nút thắt compute của Qwen3-1.7B bằng một amendment có "
        "version và chuyển development track sang Qwen3-0.6B. Nhóm đã kiểm chứng "
        "pipeline, chạy đủ 90 cấu hình trên 30 bài MATH-500 và không có lỗi. Accuracy "
        "tăng từ 10,0% ở L=1024 lên 36,7% ở L=2048 và 50,0% ở L=4096; truncation "
        "giảm từ 90,0% xuống 43,3%. Mức tăng 1024 đến 2048 có ý nghĩa sau Holm "
        "correction, còn 2048 đến 4096 chưa kết luận. Nhóm đã cập nhật paper theo "
        "model mới và bước tiếp theo là tái sinh label 0.6B để phát triển controller, "
        "chưa mở frozen Test."
    )
    for run in p.runs:
        run.italic = True

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    build_report()
