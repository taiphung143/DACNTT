from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "deliverables"
OUT.mkdir(parents=True, exist_ok=True)
FINAL = OUT / "Bao_cao_tong_hop_DATN_Adaptive_Test_Time_Compute.docx"

NAVY = "183B56"
BLUE = "2F6B9A"
PALE_BLUE = "EAF2F8"
PALE_GRAY = "F3F5F6"
MID_GRAY = "D9D9D9"
TEXT = "1F2933"
WHITE = "FFFFFF"
GREEN = "E8F3E8"
AMBER = "FFF2CC"
RED = "FCE8E6"


def set_font(run, name="Arial", size=11, bold=False, italic=False, color=TEXT):
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = RGBColor.from_string(color)
    return run


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def prevent_row_split(row):
    tr_pr = row._tr.get_or_add_trPr()
    cant_split = OxmlElement("w:cantSplit")
    tr_pr.append(cant_split)


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=100, start=120, bottom=100, end=120):
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for m, v in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{m}"))
        if node is None:
            node = OxmlElement(f"w:{m}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(v))
        node.set(qn("w:type"), "dxa")


def set_cell_border(cell, color=MID_GRAY, size="4"):
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = qn(f"w:{edge}")
        element = borders.find(tag)
        if element is None:
            element = OxmlElement(f"w:{edge}")
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), size)
        element.set(qn("w:color"), color)


def set_cell_width(cell, inches):
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_w = tc_pr.find(qn("w:tcW"))
    if tc_w is None:
        tc_w = OxmlElement("w:tcW")
        tc_pr.append(tc_w)
    tc_w.set(qn("w:w"), str(int(inches * 1440)))
    tc_w.set(qn("w:type"), "dxa")


def set_paragraph_keep(paragraph, keep_next=False, keep_lines=False):
    p_pr = paragraph._p.get_or_add_pPr()
    if keep_next:
        el = OxmlElement("w:keepNext")
        p_pr.append(el)
    if keep_lines:
        el = OxmlElement("w:keepLines")
        p_pr.append(el)


def add_page_number(paragraph):
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
    set_font(run, size=9, color="6B7280")


def add_para(doc, text="", *, bold_lead=None, align=None, space_after=6, italic=False):
    p = doc.add_paragraph()
    if bold_lead and text.startswith(bold_lead):
        set_font(p.add_run(bold_lead), bold=True)
        set_font(p.add_run(text[len(bold_lead):]), italic=italic)
    else:
        set_font(p.add_run(text), italic=italic)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.15
    if align is not None:
        p.alignment = align
    return p


def add_bullets(doc, items, level=0):
    for item in items:
        p = doc.add_paragraph(style="List Bullet" if level == 0 else "List Bullet 2")
        set_font(p.add_run(item))
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.1


def add_numbered(doc, items):
    for item in items:
        p = doc.add_paragraph(style="List Number")
        set_font(p.add_run(item))
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.12


def add_code(doc, lines):
    for line in lines:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.28)
        p.paragraph_format.right_indent = Inches(0.1)
        p.paragraph_format.space_after = Pt(1)
        p.paragraph_format.line_spacing = 1.0
        set_font(p.add_run(line), name="Consolas", size=9.2, color="263238")


def add_heading(doc, text, level=1):
    p = doc.add_heading(text, level=level)
    p.paragraph_format.space_before = Pt(10 if level == 1 else 7)
    p.paragraph_format.space_after = Pt(5)
    set_paragraph_keep(p, keep_next=True, keep_lines=True)
    return p


def add_table(doc, headers, rows, widths=None, alignments=None, status_col=None):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    hdr = table.rows[0]
    set_repeat_table_header(hdr)
    for idx, (cell, value) in enumerate(zip(hdr.cells, headers)):
        set_cell_shading(cell, NAVY)
        set_cell_border(cell)
        set_cell_margins(cell, 120, 120, 120, 120)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        if widths:
            set_cell_width(cell, widths[idx])
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        set_font(p.add_run(str(value)), size=9.4, bold=True, color=WHITE)
    for r_idx, row_values in enumerate(rows):
        row = table.add_row()
        prevent_row_split(row)
        for idx, (cell, value) in enumerate(zip(row.cells, row_values)):
            set_cell_border(cell)
            set_cell_margins(cell, 105, 115, 105, 115)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            if widths:
                set_cell_width(cell, widths[idx])
            if r_idx % 2 == 1:
                set_cell_shading(cell, PALE_BLUE)
            if status_col is not None and idx == status_col:
                v = str(value).lower()
                if "hoàn thành" in v or "đã có" in v:
                    set_cell_shading(cell, GREEN)
                elif "đang" in v or "phát triển" in v or "sơ bộ" in v:
                    set_cell_shading(cell, AMBER)
                elif "chưa" in v or "tương lai" in v:
                    set_cell_shading(cell, RED)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.alignment = alignments[idx] if alignments else WD_ALIGN_PARAGRAPH.LEFT
            set_font(p.add_run(str(value)), size=9.2)
    doc.add_paragraph().paragraph_format.space_after = Pt(1)
    return table


def add_figure(doc, path, caption, width=6.65):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(3)
    p.add_run().add_picture(str(path), width=Inches(width))
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_after = Pt(8)
    set_font(cap.add_run(caption), size=9.3, italic=True, color="4B5563")
    set_paragraph_keep(cap, keep_lines=True)


def configure_styles(doc):
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Arial"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Arial")
    normal.font.size = Pt(11)
    normal.font.color.rgb = RGBColor.from_string(TEXT)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.15
    title = styles["Title"]
    title.font.name = "Arial"
    title._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
    title._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
    title._element.rPr.rFonts.set(qn("w:eastAsia"), "Arial")
    title.font.size = Pt(26)
    title.font.bold = True
    title.font.color.rgb = RGBColor(0, 0, 0)
    title_ppr = title._element.get_or_add_pPr()
    title_border = title_ppr.find(qn("w:pBdr"))
    if title_border is not None:
        title_ppr.remove(title_border)
    for name, size in (("Heading 1", 16), ("Heading 2", 13), ("Heading 3", 11.5)):
        style = styles[name]
        style.font.name = "Arial"
        style._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Arial")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0, 0, 0)
    for name in ("List Bullet", "List Bullet 2", "List Number"):
        styles[name].font.name = "Arial"
        styles[name]._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
        styles[name]._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
        styles[name]._element.rPr.rFonts.set(qn("w:eastAsia"), "Arial")
        styles[name].font.size = Pt(11)


def build():
    doc = Document()
    configure_styles(doc)
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(0.72)
    section.bottom_margin = Inches(0.68)
    section.left_margin = Inches(0.78)
    section.right_margin = Inches(0.78)
    add_page_number(section.footer.paragraphs[0])

    # Cover
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(72)
    p.paragraph_format.space_after = Pt(14)
    set_font(p.add_run("BÁO CÁO TỔNG HỢP ĐỒ ÁN TỐT NGHIỆP"), size=13, bold=True, color=NAVY)
    title = doc.add_paragraph(style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_after = Pt(15)
    set_font(title.add_run("Phân bổ tài nguyên suy luận thích ứng\ncho mô hình ngôn ngữ suy luận cỡ nhỏ"), size=21, bold=True, color="000000")
    title.paragraph_format.left_indent = Inches(0)
    title.paragraph_format.right_indent = Inches(0)
    title_ppr = title._p.get_or_add_pPr()
    direct_border = title_ppr.find(qn("w:pBdr"))
    if direct_border is not None:
        title_ppr.remove(direct_border)
    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub.paragraph_format.space_after = Pt(34)
    set_font(sub.add_run("Adaptive Test Time Compute for Small Reasoning Models"), size=15, italic=True, color="374151")
    authors = doc.add_paragraph()
    authors.alignment = WD_ALIGN_PARAGRAPH.CENTER
    authors.paragraph_format.space_after = Pt(8)
    set_font(authors.add_run("Dinh Hong Vu   The Tai Phung   Thai Son Bui"), size=12, bold=True)
    inst = doc.add_paragraph()
    inst.alignment = WD_ALIGN_PARAGRAPH.CENTER
    inst.paragraph_format.space_after = Pt(45)
    set_font(inst.add_run("Khoa Công nghệ thông tin  Trường Đại học Tôn Đức Thắng"), size=11, color="4B5563")
    prep = doc.add_paragraph()
    prep.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_font(prep.add_run("Tài liệu chuẩn bị cho buổi trình bày ngày 25 tháng 10 năm 2026"), size=11, bold=True, color=NAVY)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(8)
    set_font(p.add_run("Cập nhật theo mã nguồn và artifact đến ngày 24 tháng 10 năm 2026"), size=10, color="6B7280")
    doc.add_page_break()

    add_heading(doc, "Mục đích của tài liệu", 1)
    add_para(doc, "Tài liệu này giúp nhóm đọc lại toàn bộ quá trình thực hiện đề tài từ khi hình thành bài toán, xây dựng hạ tầng thí nghiệm, chạy khảo sát GSM8K, phát triển baseline Phase 2, mở rộng sang MATH-500 cho đến trạng thái hiện tại. Nội dung được viết theo hướng có thể dùng như bản thuyết minh khi chuẩn bị bài nói, đồng thời chỉ rõ phần nào đã có bằng chứng, phần nào mới là kết quả phát triển và phần nào chưa hoàn thành.")
    add_para(doc, "Kết luận hiện tại: ", bold_lead="Kết luận hiện tại: ")
    # Replace the just-created second run content with the full lead paragraph.
    doc.paragraphs[-1].clear()
    set_font(doc.paragraphs[-1].add_run("Kết luận hiện tại  "), bold=True)
    set_font(doc.paragraphs[-1].add_run("Cách đặt ngân sách suy luận quan trọng hơn chỉ nhìn vào tổng ngân sách danh nghĩa. Trên GSM8K, tăng giới hạn token tạo mức tăng độ chính xác lớn và một quỹ đạo dài có thể tốt hơn nhiều quỹ đạo ngắn cùng ngân sách. Oracle chung cho thấy còn dư địa tiết kiệm lớn, nhưng controller chung chưa được triển khai và chưa có đánh giá held out. Baseline depth-only và pilot MATH-500 cung cấp bằng chứng phát triển để tiếp tục theo hướng cấp đủ độ sâu trước rồi mới tăng breadth có chọn lọc."))
    doc.paragraphs[-1].paragraph_format.space_after = Pt(8)
    add_table(
        doc,
        ["Hạng mục", "Trạng thái", "Bằng chứng chính"],
        [
            ["Lưới breadth depth GSM8K", "Hoàn thành", "1.200 lượt sinh  99 bài được đánh giá"],
            ["Phân tích oracle và chi phí", "Hoàn thành", "83,84 phần trăm tại 1.023,5 token trung bình cho joint oracle"],
            ["Baseline depth only", "Kết quả phát triển", "65,0 phần trăm trên Validation  giảm 12,7 phần trăm token so với fixed L 2048"],
            ["Pilot MATH 500", "Hoàn thành ở mức development", "90 lượt sinh  accuracy tăng từ 6,7 lên 53,3 phần trăm"],
            ["Joint controller", "Chưa triển khai", "Kiến trúc và protocol đã đặc tả"],
            ["Frozen Test", "Chưa mở", "100 bài mới được khóa bằng manifest và hash"],
        ],
        widths=[1.75, 1.55, 3.65],
        alignments=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT],
        status_col=1,
    )

    add_heading(doc, "Mục lục nội dung", 1)
    add_numbered(doc, [
        "Bài toán nghiên cứu và các khái niệm cần biết",
        "Câu hỏi nghiên cứu và phạm vi đã chốt",
        "Dòng thời gian từ khởi tạo đến hiện tại",
        "Kiến trúc phần mềm và quy trình thí nghiệm",
        "Thiết kế thực nghiệm GSM8K",
        "Kết quả GSM8K và ý nghĩa",
        "Phase 2 và baseline depth only",
        "Pilot MATH 500 và kiểm toán parser",
        "Những nội dung có thể demo trực tiếp",
        "Trạng thái bài báo",
        "Giới hạn bằng chứng và kế hoạch tiếp theo",
        "Kịch bản thuyết trình và câu hỏi phản biện",
    ])
    doc.add_page_break()

    add_heading(doc, "1 Bài toán nghiên cứu và các khái niệm cần biết", 1)
    add_heading(doc, "1 1 Vì sao cần phân bổ compute theo từng bài", 2)
    add_para(doc, "Mô hình suy luận thường đạt kết quả tốt hơn khi được phép sinh nhiều token hơn hoặc khi tạo nhiều quỹ đạo rồi lấy biểu quyết. Tuy nhiên, một cấu hình cố định áp dụng cho mọi câu hỏi sẽ lãng phí tài nguyên ở bài dễ và vẫn có thể thiếu compute ở bài khó. Đề tài nghiên cứu cách phân bổ compute ở thời điểm suy luận theo từng bài toán với một mô hình nhỏ, mã nguồn mở và không dùng verifier bên ngoài.")
    add_para(doc, "Hai trục compute được khảo sát là breadth và token cap. Nhóm cố tình dùng thuật ngữ token cap thay vì khẳng định đây là độ sâu suy luận thật, vì L chỉ là giới hạn max new tokens mà hệ thống đặt cho quá trình sinh.")
    add_table(
        doc,
        ["Ký hiệu", "Ý nghĩa", "Cách dùng trong đề tài"],
        [
            ["k", "Số quỹ đạo suy luận độc lập", "k bằng 1  2 hoặc 4  kết quả được valid only majority vote"],
            ["L", "Giới hạn token sinh cho mỗi quỹ đạo", "GSM8K dùng 512  1024  2048  MATH pilot dùng thêm 4096"],
            ["k nhân L", "Ngân sách danh nghĩa tối đa", "Dùng để so các profile có cùng trần compute"],
            ["Actual Generated Tokens", "Số token mô hình thực sự sinh", "Chi phí chính để so Pareto frontier"],
            ["Fixed profile", "Một cấu hình dùng cho mọi bài", "Baseline vận hành đơn giản"],
            ["Oracle", "Chọn cấu hình sau khi đã biết kết quả", "Chỉ đo dư địa hindsight  không thể triển khai"],
            ["Controller", "Chính sách chọn compute từ tín hiệu quan sát được", "Mục tiêu deployable của Phase 2"],
        ],
        widths=[1.25, 2.15, 3.55],
    )
    add_heading(doc, "1 2 Điểm khác nhau giữa breadth và depth", 2)
    add_bullets(doc, [
        "Tăng L cho một quỹ đạo thêm thời gian để hoàn thành chuỗi suy luận và xuất đáp án rõ ràng.",
        "Tăng k tạo thêm quỹ đạo độc lập và có thể cứu các trường hợp mẫu đầu sai hoặc không có đáp án hợp lệ.",
        "Breadth chỉ có tác dụng khi các mẫu tạo ra đủ đa dạng và có đáp án hợp lệ để biểu quyết.",
        "Nếu mỗi quỹ đạo đều bị cắt ngắn vì L quá thấp, tăng k có thể chỉ nhân số lần thất bại và tăng chi phí.",
    ])
    add_heading(doc, "1 3 Cách đánh giá câu trả lời", 2)
    add_para(doc, "Parser chỉ chấp nhận các dạng đáp án cuối rõ ràng như marker GSM8K, boxed answer hoặc trường Final answer. Hệ thống không lấy số cuối cùng trong phần suy luận làm đáp án dự phòng. Với k lớn hơn 1, chỉ những đáp án parse hợp lệ mới được bỏ phiếu. Nếu không có đáp án hợp lệ, profile được tính là sai. Cách làm này bảo thủ nhưng tránh thổi phồng accuracy từ các chuỗi chưa hoàn thành.")

    add_heading(doc, "2 Câu hỏi nghiên cứu và phạm vi đã chốt", 1)
    add_heading(doc, "2 1 Câu hỏi chính", 2)
    add_para(doc, "Đối với mô hình suy luận mã nguồn mở cỡ nhỏ, một chính sách tuần tự nhẹ và không dùng verifier có thể phân bổ giới hạn token rồi chỉ tăng số mẫu khi cần để cải thiện Pareto frontier giữa độ chính xác và số token sinh thực tế so với cấu hình cố định, controller chỉ điều chỉnh depth và controller chỉ điều chỉnh breadth hay không.")
    add_heading(doc, "2 2 Phạm vi nghiên cứu", 2)
    add_bullets(doc, [
        "Mô hình phát triển chính là Qwen3-1.7B với revision được ghim cố định.",
        "Bộ dữ liệu chính là GSM8K  MATH-500 được dùng để mở rộng bằng chứng ở mức development.",
        "Không sử dụng ground truth  oracle label hoặc quỹ đạo chưa sinh tại thời điểm controller ra quyết định.",
        "Chi phí gồm toàn bộ quỹ đạo mà policy đã trả token để sinh  kể cả rollout thăm dò.",
        "Kết quả oracle là upper bound hồi cứu  không được trình bày như hiệu năng controller.",
    ])
    add_heading(doc, "2 3 Đóng góp hiện có", 2)
    add_numbered(doc, [
        "Pipeline breadth depth có cache  checkpoint  resume  manifest và phân tích thống kê tái lập được.",
        "Khảo sát có kiểm soát chín profile trên GSM8K với số token thực tế  latency  truncation và tính hợp lệ.",
        "Phân tích cùng ngân sách cho thấy k nhân L bằng nhau không tạo hành vi tương đương.",
        "Oracle frontier định lượng dư địa của fixed  depth only  breadth only và joint allocation.",
        "Baseline depth-only chống leakage và pilot MATH-500 với parser có version và kiểm toán.",
        "Thiết kế controller tuần tự cùng protocol đánh giá held out cho phần việc tiếp theo.",
    ])

    add_heading(doc, "3 Dòng thời gian từ khởi tạo đến hiện tại", 1)
    add_table(
        doc,
        ["Mốc", "Công việc chính", "Kết quả hoặc artifact"],
        [
            ["28 đến 29 tháng 8", "Khởi tạo pipeline và mô đun phân tích", "Runner  aggregation  oracle  Pareto  plotting"],
            ["4 tháng 9", "Smoke run  pilot 3 và 30 bài  bổ sung kiểm định ghép cặp", "Artifact n3  n30 và statistical report"],
            ["11 đến 19 tháng 9", "Mở rộng n100  Phase 1 5  refactor package", "1.200 generations  99 bài hợp lệ  oracle frontier"],
            ["19 đến 27 tháng 9", "Khóa split Phase 2 và huấn luyện baseline depth only", "79 Train  20 Validation  100 Test  111 tests thời điểm đó"],
            ["19 đến 21 tháng 10", "Adapter và pilot MATH-500  parser v2", "90 generations  ba mức L  audit tái xử lý"],
            ["21 đến 22 tháng 10", "Khởi chạy thử L 8192 và cập nhật paper", "Run mới còn dở  chỉ 11 trên 120 records nên loại khỏi kết quả"],
            ["24 tháng 10", "Kiểm tra lại demo và test suite", "134 tests passed  hai lệnh validate only chạy thành công"],
        ],
        widths=[1.35, 2.7, 2.95],
    )
    add_para(doc, "Dòng thời gian cho thấy đề tài đã đi từ hạ tầng khảo sát đến bằng chứng thực nghiệm và baseline controller. Phần còn thiếu lớn nhất là các quyết định breadth tuần tự và đánh giá một lần trên frozen Test sau khi khóa toàn bộ policy.")

    add_heading(doc, "4 Kiến trúc phần mềm và quy trình thí nghiệm", 1)
    add_heading(doc, "4 1 Cấu trúc mã nguồn", 2)
    add_table(
        doc,
        ["Thành phần", "Vai trò"],
        [
            ["adaptive_compute dataset", "Nạp GSM8K hoặc MATH-500  áp dụng manifest  hash và manual audit"],
            ["adaptive_compute models", "Hợp đồng backend và Transformers adapter cho Qwen"],
            ["adaptive_compute experiment_runner", "Sinh mẫu theo seed xác định  ghi checkpoint và cache"],
            ["adaptive_compute answer_parser", "Tách đáp án cuối  chuẩn hóa và phân loại lỗi"],
            ["adaptive_compute aggregation", "Tạo kết quả cho từng k L bằng shared sample prefix"],
            ["adaptive_compute analysis", "Thống kê  Pareto  oracle  bootstrap  heatmap và báo cáo"],
            ["adaptive_compute controller", "Chuẩn bị bảng feature và huấn luyện baseline depth only"],
            ["adaptive_compute cli", "Các lệnh validate  run  analyze  reprocess và train"],
            ["tests", "Kiểm thử parser  dataset  cache  runner  thống kê  controller và sanity pipeline"],
        ],
        widths=[2.45, 4.5],
    )
    add_heading(doc, "4 2 Luồng xử lý", 2)
    add_table(
        doc,
        ["Bước", "Đầu vào", "Xử lý", "Đầu ra"],
        [
            ["1", "Config và frozen manifest", "Kiểm tra hash  problem ID  partition", "Danh sách bài hợp lệ"],
            ["2", "Bài toán và model revision", "Sinh shared sample pool theo seed xác định", "Raw JSONL append only"],
            ["3", "Raw response", "Parser và trạng thái truncation", "Đáp án chuẩn hóa  failure type"],
            ["4", "Các sample prefix", "Valid only majority vote cho k 1  2  4", "Config results"],
            ["5", "Config results", "Tổng hợp  kiểm định ghép cặp  oracle", "CSV  Markdown và PNG"],
            ["6", "Feature allowlist", "Huấn luyện và chọn controller trên Train Validation", "Model  policy metrics"],
        ],
        widths=[0.55, 1.65, 2.95, 1.85],
        alignments=[WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT],
    )
    add_heading(doc, "4 3 Các cơ chế tái lập", 2)
    add_bullets(doc, [
        "Seed của mỗi sample lấy từ SHA256 của global seed  problem id  repetition id và sample id  không phụ thuộc k hoặc L.",
        "Trong mỗi L  k bằng 1 dùng sample 0  k bằng 2 dùng 0 và 1  k bằng 4 dùng 0 đến 3.",
        "Checkpoint key không chứa k vì k chỉ chọn prefix từ shared pool  nhờ đó tránh sinh lặp.",
        "Generation cache cho phép tái sử dụng đúng những kết quả có cùng model  revision  prompt và tham số sinh.",
        "Experiment manifest lưu cấu hình  version thư viện  model revision  prompt hash và expected generation count.",
        "Run có thể resume  retry lỗi theo yêu cầu và chạy lại toàn bộ phân tích mà không cần GPU.",
    ])
    add_heading(doc, "4 4 Trạng thái kiểm thử", 2)
    add_para(doc, "Ngày 24 tháng 10 năm 2026, nhóm chạy lại toàn bộ test suite ở chế độ không tự nạp plugin pytest bên ngoài. Kết quả là 134 test passed trong 9,66 giây. Các cảnh báo còn lại là deprecation warning từ matplotlib và pyparsing trong sanity test, không phải lỗi chức năng.")

    add_heading(doc, "5 Thiết kế thực nghiệm GSM8K", 1)
    add_heading(doc, "5 1 Thiết lập", 2)
    add_table(
        doc,
        ["Mục", "Giá trị"],
        [
            ["Model", "Qwen Qwen3 1.7B  revision 70d244cc86ccca08cf5af4e1e306ecf908b1ad5e"],
            ["Dataset", "GSM8K test  manifest cố định 100 bài  loại 1 bài manual review khỏi metric chính"],
            ["Breadth", "k bằng 1  2  4"],
            ["Token cap", "L bằng 512  1024  2048"],
            ["Sampling", "temperature 0.7  top p 0.95  thinking enabled"],
            ["Compute", "CUDA và bfloat16"],
            ["Số lượt sinh", "100 bài nhân 3 mức L nhân 4 sample bằng 1.200 records"],
            ["Số lần lặp", "1 stochastic repetition"],
            ["Metric chính", "Final answer accuracy và Actual Generated Tokens"],
        ],
        widths=[1.65, 5.3],
    )
    add_heading(doc, "5 2 Vì sao chỉ cần 1.200 generations", 2)
    add_para(doc, "Nếu sinh độc lập cho từng profile  một bài sẽ cần 1 cộng 2 cộng 4 bằng 7 sample cho mỗi L. Pipeline dùng shared prefix nên chỉ sinh bốn sample cho mỗi L rồi tái sử dụng để tạo ba giá trị k. Với 100 bài và ba mức L  tổng số generation là 100 nhân 3 nhân 4 bằng 1.200. Cách này vừa giảm chi phí vừa giữ các so sánh breadth được ghép cặp trên cùng sample pool.")
    add_heading(doc, "5 3 Một bài dữ liệu bị đánh dấu", 2)
    add_para(doc, "Bài gsm8k-test-01309 được giữ trong raw artifact để bảo toàn nguồn gốc nhưng bị loại khỏi accuracy  Pareto và oracle vì manual audit phát hiện nhãn cần xem lại. Nhóm không sửa ground truth gốc của GSM8K. Do đó các bảng chính dùng 99 bài.")

    add_heading(doc, "6 Kết quả GSM8K và ý nghĩa", 1)
    add_heading(doc, "6 1 Ma trận accuracy", 2)
    add_figure(doc, ROOT / "results/qwen3_1_7b_gsm8k_n100_r1/plots/accuracy_heatmap.png", "Hình 1  Độ chính xác cuối trên chín profile GSM8K  99 bài được đánh giá")
    add_table(
        doc,
        ["k", "L 512", "L 1024", "L 2048"],
        [
            ["1", "9,09 phần trăm", "53,54 phần trăm", "70,71 phần trăm"],
            ["2", "17,17 phần trăm", "65,66 phần trăm", "81,82 phần trăm"],
            ["4", "28,28 phần trăm", "71,72 phần trăm", "83,84 phần trăm"],
        ],
        widths=[0.7, 2.05, 2.05, 2.05],
        alignments=[WD_ALIGN_PARAGRAPH.CENTER] * 4,
    )
    add_para(doc, "Ở mọi k, tăng L làm accuracy tăng mạnh. Cả sáu so sánh depth liền kề đều có ý nghĩa sau hiệu chỉnh Holm. Breadth vẫn hữu ích nhưng lợi ích biên giảm khi L lớn hơn: tại L bằng 2048, tăng k từ 2 lên 4 chỉ thêm 2,02 điểm phần trăm và p Holm bằng 0,5.")
    add_heading(doc, "6 2 Cùng ngân sách danh nghĩa nhưng kết quả khác nhau", 2)
    add_figure(doc, ROOT / "results/qwen3_1_7b_gsm8k_n100_r1/plots/iso_budget_2048.png", "Hình 2  So sánh ba profile cùng ngân sách danh nghĩa 2048 token")
    add_table(
        doc,
        ["Profile", "Accuracy", "Token thực tế trung bình", "Truncation sample"],
        [
            ["4 nhân 512", "28,28 phần trăm", "1.988,9", "85,4 phần trăm"],
            ["2 nhân 1024", "65,66 phần trăm", "1.616,0", "35,9 phần trăm"],
            ["1 nhân 2048", "70,71 phần trăm", "1.079,1", "18,2 phần trăm"],
        ],
        widths=[1.45, 1.55, 2.2, 1.75],
        alignments=[WD_ALIGN_PARAGRAPH.CENTER] * 4,
    )
    add_para(doc, "Kết quả này là điểm giải thích quan trọng nhất của bài: một quỹ đạo dài vừa chính xác hơn vừa dùng ít token thực tế hơn bốn quỹ đạo ngắn trong cấu hình đã thử. Nguyên nhân trực tiếp là 4 nhân 512 tạo rất nhiều sample bị cắt ngắn trước khi có đáp án. Đây là quan sát trong thiết lập hiện tại  không phải quy luật rằng depth luôn tốt hơn breadth.")
    add_heading(doc, "6 3 Breadth vẫn cứu được một nhóm bài", 2)
    add_para(doc, "Trong 83 bài được joint oracle giải, 70 bài chọn k bằng 1 là profile cheapest correct nhưng 13 bài cần k lớn hơn 1 trong sample pool quan sát được. Vì vậy loại bỏ breadth hoàn toàn sẽ mất accuracy tiềm năng ở nhóm thiểu số này.")
    add_figure(doc, ROOT / "results/qwen3_1_7b_gsm8k_n100_r1/phase1_5/profile_preference_distribution.png", "Hình 3  Phân bố profile cheapest correct của joint oracle")
    doc.add_page_break()
    add_heading(doc, "6 4 Oracle headroom", 2)
    add_figure(doc, ROOT / "results/qwen3_1_7b_gsm8k_n100_r1/phase1_5/oracle_budget_frontier.png", "Hình 4  Accuracy upper bound theo ngân sách token thực tế của các họ chiến lược", width=5.65)
    add_table(
        doc,
        ["Chiến lược", "Accuracy", "Token trung bình", "Ý nghĩa"],
        [
            ["Best fixed  4 nhân 2048", "83,84 phần trăm", "4.246,7", "Mốc fixed đạt accuracy cao nhất"],
            ["Breadth only oracle  L 2048", "83,84 phần trăm", "1.270,6", "Chọn k hồi cứu"],
            ["Depth only oracle  k 1", "70,71 phần trăm", "750,5", "Chọn L hồi cứu ở k 1"],
            ["Joint oracle", "83,84 phần trăm", "1.023,5", "Chọn mọi k L hồi cứu"],
        ],
        widths=[2.15, 1.35, 1.45, 2.0],
        alignments=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT],
    )
    add_para(doc, "Joint oracle giữ cùng 83,84 phần trăm accuracy như best fixed nhưng giảm khoảng 75,9 phần trăm token trung bình. So với breadth-only oracle ở cùng accuracy, joint oracle còn giảm khoảng 19,4 phần trăm token. Con số này chỉ chứng minh có cơ hội nếu chọn đúng profile  không chứng minh một controller có thể dự đoán lựa chọn đó.")
    add_heading(doc, "6 5 Ví dụ hai cơ chế cứu lỗi", 2)
    add_table(
        doc,
        ["Trường hợp", "Cấu hình", "Quan sát", "Kết luận demo"],
        [
            ["gsm8k test 00028", "k 1  L 512  1024  2048", "L 512 và 1024 bị cắt trước đáp án  L 2048 trả 25 đúng sau 1.093 token", "Tăng depth cứu một quỹ đạo"],
            ["gsm8k test 00013", "L 2048  k 1  2  4", "k 1 không có đáp án hợp lệ  k 2 và k 4 vote ra 18 đúng", "Breadth cứu thất bại của sample đầu"],
        ],
        widths=[1.4, 1.55, 2.75, 1.25],
    )

    add_heading(doc, "7 Phase 2 và baseline depth only", 1)
    add_heading(doc, "7 1 Frozen split chống leakage", 2)
    add_table(
        doc,
        ["Partition", "Số bài", "Nguồn", "Vai trò"],
        [
            ["Train", "79", "Từ 99 bài development hợp lệ", "Fit controller"],
            ["Validation", "20", "Từ 99 bài development còn lại", "Chọn candidate và threshold"],
            ["Test", "100", "Bài GSM8K mới ngoài n100", "Confirmatory one shot"],
        ],
        widths=[1.25, 0.75, 2.6, 2.35],
        alignments=[WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT],
    )
    add_para(doc, "Manifest v1 lưu problem id  source index  question hash và ground truth hash. Pipeline từ chối overlap  record bị thay đổi hoặc manual audit bị thay thế. Tập Test chưa được nạp và chưa được đánh giá. Validation đã tiếp xúc gián tiếp với phân tích aggregate của n100 nên chỉ là tập model selection  không phải bằng chứng xác nhận cuối.")
    add_heading(doc, "7 2 Feature contract", 2)
    add_bullets(doc, [
        "Chỉ cột có tiền tố feature mới được phép làm input.",
        "Feature gồm độ dài câu hỏi  prompt token count  số lượng số  toán tử  phân số  phần trăm và chỉ báo từ vựng nông.",
        "Correctness  oracle profile  outcome quan sát được và target label bị cấm ở test time.",
        "Target là L nhỏ nhất mà k bằng 1 trả đúng  nếu không có L đúng thì fallback L bằng 2048 và giữ trạng thái unsolved.",
    ])
    add_heading(doc, "7 3 Baseline logistic", 2)
    add_para(doc, "Mô hình là multinomial logistic regression có standardization. Grid lựa chọn gồm C bằng 0,1  1  10  class weight none hoặc balanced và ordered decision quantile bằng 0,5  0,7  0,9. Candidate được chọn theo thứ tự ưu tiên accuracy policy trên Validation  token thực tế  balanced accuracy  macro F1 rồi mới đến tie break đơn giản.")
    add_table(
        doc,
        ["Policy", "Correct", "Accuracy", "Token trung bình"],
        [
            ["Fixed L 512", "2 trên 20", "10,0 phần trăm", "499,00"],
            ["Fixed L 1024", "9 trên 20", "45,0 phần trăm", "843,65"],
            ["Fixed L 2048", "13 trên 20", "65,0 phần trăm", "1.213,05"],
            ["Selected depth logistic", "13 trên 20", "65,0 phần trăm", "1.059,45"],
        ],
        widths=[2.45, 1.25, 1.65, 1.6],
        alignments=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER],
    )
    add_para(doc, "Baseline giữ nguyên 13 trên 20 bài đúng như fixed L bằng 2048 và giảm 153,6 token mỗi bài  tương đương 12,7 phần trăm. Exact depth target classification accuracy là 50 phần trăm. Vì candidate được chọn trên chính 20 bài Validation  đây là development result có thể lạc quan.")
    add_heading(doc, "7 4 Joint controller đã thiết kế nhưng chưa chạy", 2)
    add_numbered(doc, [
        "Dự đoán L ban đầu từ feature trước inference.",
        "Sinh sample 1 và quan sát validity  truncation  token sử dụng và cap utilization.",
        "Dừng ở k bằng 1 hoặc sinh sample 2.",
        "Sau hai sample  dùng thêm agreement và valid answer fraction để dừng ở k bằng 2 hoặc tăng k lên 4.",
        "Tính chi phí trên mọi sample đã sinh rồi mới so với baseline depth only và breadth only.",
    ])

    add_heading(doc, "8 Pilot MATH 500 và kiểm toán parser", 1)
    add_heading(doc, "8 1 Mục tiêu và thiết kế", 2)
    add_para(doc, "Pilot thứ hai kiểm tra liệu độ nhạy với token cap còn xuất hiện ở bộ toán khó hơn hay không và đồng thời kiểm tra adapter  prompt và parser mới. Nhóm chọn xác định 30 bài MATH-500 bằng seed 42  phân tầng theo bảy chủ đề và năm mức độ khó. Đây là tập development  không phải held out MATH benchmark.")
    add_table(
        doc,
        ["L", "Correct", "Accuracy", "Token trung bình", "Truncation"],
        [
            ["1024", "2 trên 30", "6,7 phần trăm", "1.016,9", "93,3 phần trăm"],
            ["2048", "8 trên 30", "26,7 phần trăm", "1.825,2", "73,3 phần trăm"],
            ["4096", "16 trên 30", "53,3 phần trăm", "3.077,4", "46,7 phần trăm"],
        ],
        widths=[0.95, 1.25, 1.6, 1.65, 1.5],
        alignments=[WD_ALIGN_PARAGRAPH.CENTER] * 5,
    )
    add_figure(doc, ROOT / "results/qwen3_1_7b_math500_depth_pilot_v2_parser_v2/plots/depth_effect.png", "Hình 5  MATH-500 cho thấy accuracy tăng và truncation giảm khi L tăng")
    add_para(doc, "So sánh ghép cặp L bằng 2048 lên 4096 có tám trường hợp cải thiện  không có trường hợp suy giảm. Mức tăng 26,7 điểm phần trăm có exact McNemar p bằng 0,0078125 và Holm adjusted p bằng 0,015625 trong họ so sánh depth đã định trước.")
    add_heading(doc, "8 2 Parser v2 và kiểm toán tái xử lý", 2)
    add_para(doc, "Kiểm toán thủ công phát hiện hai lỗi chuẩn hóa ground truth: hậu tố cơ số trong 204 dưới cơ số 5 bị ghép thành 2045  và danh sách 3 5 7 bị ghép thành số 357. Parser exact v2 sửa đúng hai dạng này. Nhóm tái xử lý lại 90 record mà không chạy mô hình.")
    add_table(
        doc,
        ["Kiểm tra", "Kết quả"],
        [
            ["Số record nguồn và đích", "90 và 90"],
            ["Identity thiếu hoặc trùng", "0"],
            ["Raw response  seed  token  latency  finish reason thay đổi", "0"],
            ["Ground truth field thay đổi", "6 record thuộc 2 bài và 3 mức L"],
            ["Nhãn correctness thay đổi", "1 record tại math500 test 137  L 4096"],
        ],
        widths=[3.75, 3.2],
    )
    add_heading(doc, "8 3 Trạng thái thử nghiệm L 8192", 2)
    add_para(doc, "Run qwen3_1_7b_math500_depth_cap_pilot_v3 dự kiến 120 generations cho L bằng 1024  2048  4096  8192. Artifact hiện có 11 record  trong đó chỉ hai record ở L bằng 8192. Vì run chưa hoàn tất  toàn bộ số liệu này bị loại khỏi kết quả báo cáo và slide. Mục tiêu sau khi hoàn thành là xác định liệu trần 4096 còn right censoring quá mạnh trước khi khóa action space MATH.")

    add_heading(doc, "9 Những nội dung có thể demo trực tiếp", 1)
    add_heading(doc, "9 1 Demo kiểm tra cấu hình không cần GPU", 2)
    add_para(doc, "Mục tiêu là cho thấy hệ thống hiểu đúng lưới thí nghiệm  số generation duy nhất và cấu hình được ghim. Lệnh này không tải model và không chạy inference.")
    add_code(doc, [
        "python -m adaptive_compute.cli.run_grid --num-problems 3 --k-values 1 2 4 \\",
        "  --l-values 512 1024 2048 --seed 42 --validate-only",
    ])
    add_para(doc, "Kết quả đã kiểm tra ngày 24 tháng 10: output liệt kê đủ chín profile  shared pool max k bằng 4 và expected unique generations bằng 36.")
    add_heading(doc, "9 2 Demo test suite", 2)
    add_code(doc, [
        "$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'",
        "python -m pytest -q",
    ])
    add_para(doc, "Kết quả đã kiểm tra: 134 passed trong 9,66 giây. Khi demo  cần nói rõ đây là kiểm thử CPU cho logic phần mềm  không phải chạy lại model 1.200 generations.")
    add_heading(doc, "9 3 Demo artifact và biểu đồ", 2)
    add_bullets(doc, [
        "Mở experiment_manifest.json để chỉ model revision  seed  grid và expected generations.",
        "Mở raw_samples.jsonl để chỉ một response  token count  finish reason  parser output và cache provenance.",
        "Mở grid_summary.csv và accuracy_heatmap.png để nối raw output với kết quả tổng hợp.",
        "Mở oracle_comparison.csv và oracle_budget_frontier.png để giải thích headroom hồi cứu.",
        "Mở development_report.md của depth baseline để chỉ rõ status Train Validation và việc Test chưa dùng.",
        "Mở parser_v2_audit.md để chứng minh sửa parser không thay đổi dữ liệu sinh.",
    ])
    add_heading(doc, "9 4 Demo hai ca cụ thể", 2)
    add_para(doc, "Ca depth rescue dùng gsm8k-test-00028. Ở k bằng 1  L 512 và 1024 đều không có đáp án hợp lệ do bị cắt ngắn. Khi L tăng lên 2048  mô hình trả đáp án 25 đúng sau 1.093 token. Ca breadth rescue dùng gsm8k-test-00013. Tại L bằng 2048  sample 0 không hợp lệ  nhưng sample thứ hai trả đáp án 18 nên k bằng 2 cho majority đúng. Hai ca này giúp giải thích vì sao policy hợp lý cần ưu tiên đủ depth nhưng vẫn giữ breadth có chọn lọc.")
    add_heading(doc, "9 5 Thứ tự demo khuyến nghị", 2)
    add_numbered(doc, [
        "Chạy validate only trong khoảng 20 giây trình bày.",
        "Chạy pytest và nói 134 test passed.",
        "Mở accuracy heatmap  iso budget  oracle frontier và MATH depth plot.",
        "Mở hai ca depth rescue và breadth rescue từ config_results hoặc raw_samples.",
        "Kết thúc bằng development report và nhắc frozen Test chưa mở.",
    ])

    add_heading(doc, "10 Trạng thái bài báo", 1)
    add_para(doc, "Bản thảo LNCS hiện có tiêu đề Adaptive Test-Time Compute for Small Reasoning Models  A Breadth Depth Characterization and Preliminary Controller Study. Tác giả gồm Dinh Hong Vu  The Tai Phung và Thai Son Bui. Nội dung đã bao phủ Abstract  Introduction  Related Work  Problem Formulation  Methodology  Experimental Setup  Preliminary Results  Discussion  Limitations  Planned Confirmatory Evaluation  Conclusion và 15 tài liệu tham khảo.")
    add_table(
        doc,
        ["Phần bài báo", "Trạng thái", "Nội dung hiện có"],
        [
            ["Introduction và Related Work", "Hoàn thành bản nháp", "Bối cảnh test time scaling  adaptive sampling và token budget"],
            ["Methodology", "Hoàn thành bản nháp", "Grid  parser  oracle  depth baseline và joint design"],
            ["Experimental Setup", "Hoàn thành bản nháp", "Model  dataset  split  metric và thống kê"],
            ["Preliminary Results", "Đã có số liệu", "GSM8K  depth baseline và MATH pilot"],
            ["Joint controller results", "Chưa có", "Phương pháp mới ở trạng thái proposed"],
            ["Held out Test", "Chưa có", "Phải chờ policy và threshold được đóng băng"],
        ],
        widths=[1.95, 1.75, 3.25],
        status_col=1,
    )
    add_para(doc, "Điểm cần giữ khi trình bày là phân biệt rõ completed evidence  development result  proposed method và future evaluation. Paper hiện không khẳng định controller chung đã hoạt động và không dùng oracle headroom làm bằng chứng triển khai.")

    add_heading(doc, "11 Giới hạn bằng chứng và kế hoạch tiếp theo", 1)
    add_heading(doc, "11 1 Giới hạn hiện tại", 2)
    add_bullets(doc, [
        "Thực nghiệm chính dùng một model và một stochastic repetition.",
        "Metric GSM8K dựa trên 99 bài sau manual exclusion  chưa phải quy mô benchmark đầy đủ.",
        "Validation chỉ có 20 bài và đã dùng để chọn baseline candidate.",
        "MATH-500 chỉ là pilot development 30 bài  chưa đánh giá controller chéo dataset.",
        "Oracle quan sát ground truth sau inference  không thể deploy.",
        "Joint controller và breadth stopping baseline chưa được triển khai.",
        "Generation seed variability chưa được đo đầy đủ.",
        "Run L 8192 chưa hoàn tất và không được dùng trong kết luận.",
    ])
    add_heading(doc, "11 2 Kế hoạch kỹ thuật", 2)
    add_numbered(doc, [
        "Hoàn tất và kiểm toán run MATH L bằng 8192  sau đó khóa action space theo dataset.",
        "Đánh giá số positive escalation event và mở rộng development pool nếu chưa đủ.",
        "Cài breadth-only baseline theo agreement stopping và heuristic depth first.",
        "Cài hai quyết định breadth của joint controller bằng logistic regression trước.",
        "So sánh joint  depth only và breadth only trên Validation theo accuracy và Actual Generated Tokens.",
        "Khóa feature contract  parser  model  threshold và cấu hình.",
        "Mở frozen Test đúng một lần  báo cáo uncertainty và cập nhật paper cuối.",
    ])
    add_heading(doc, "11 3 Tiêu chí go hoặc pivot", 2)
    add_table(
        doc,
        ["Quyết định", "Điều kiện đề xuất", "Cách báo cáo"],
        [
            ["Go Joint", "Tăng ít nhất 3 điểm accuracy ở chi phí trong cộng trừ 10 phần trăm  hoặc giảm ít nhất 10 phần trăm token với accuracy giảm không quá 2 điểm", "Tiếp tục joint policy"],
            ["Pivot Depth First", "Joint bị depth-only Pareto dominate hoặc breadth không tạo utility dương", "Tập trung adaptive depth  báo cáo breadth âm tính"],
            ["Need More Data", "Thiếu 30 positive events  CI rộng hoặc target không ổn định", "Mở rộng development  chưa mở Test"],
            ["Abandon Learned Controller", "Sau tối thiểu 300 bài và hai dataset  policy vẫn bị fixed hoặc heuristic dominate", "Kết luận giới hạn learnability"],
        ],
        widths=[1.35, 3.7, 1.9],
    )

    add_heading(doc, "12 Kịch bản thuyết trình và câu hỏi phản biện", 1)
    add_heading(doc, "12 1 Kịch bản 12 đến 15 phút", 2)
    add_table(
        doc,
        ["Thời lượng", "Nội dung nói", "Điểm phải chốt"],
        [
            ["1 phút", "Bài toán và câu hỏi nghiên cứu", "Một cấu hình cố định lãng phí compute theo từng bài"],
            ["1 phút", "k  L và Actual Generated Tokens", "Phân biệt ngân sách danh nghĩa và chi phí thực"],
            ["1 phút", "Pipeline và reproducibility", "Shared pool  cache  manifest  134 tests"],
            ["2 phút", "Thiết kế GSM8K", "1.200 generations  99 bài metric chính"],
            ["3 phút", "Grid  iso budget và oracle", "Depth chi phối  breadth vẫn cứu nhóm thiểu số"],
            ["2 phút", "Phase 2 baseline", "65 phần trăm với 12,7 phần trăm token ít hơn  chỉ là Validation"],
            ["2 phút", "MATH-500", "6,7 lên 53,3 phần trăm  parser v2 có audit"],
            ["1 đến 2 phút", "Demo", "Validate plan  tests  plots  hai ca cứu lỗi"],
            ["1 phút", "Hạn chế và bước tiếp theo", "Joint chưa chạy  frozen Test chưa mở"],
        ],
        widths=[1.2, 3.05, 2.7],
    )
    add_heading(doc, "12 2 Câu kết luận nên dùng", 2)
    add_para(doc, "Kết quả hiện tại cho thấy vị trí đặt compute quyết định hiệu quả. Trên GSM8K  một quỹ đạo đủ dài tốt hơn nhiều quỹ đạo ngắn cùng ngân sách  nhưng một số bài vẫn cần breadth. Baseline depth-only đã chứng minh có thể tiết kiệm token ở mức development và MATH-500 xác nhận token cap vẫn là nút thắt. Bước tiếp theo là biến headroom hồi cứu thành policy tuần tự  khóa policy rồi mới mở Test.")
    add_heading(doc, "12 3 Câu hỏi phản biện thường gặp", 2)
    qa_rows = [
        ["Oracle tốt như vậy vì sao chưa coi là kết quả chính", "Oracle biết ground truth và toàn bộ outcome sau khi đã chạy mọi profile  nên chỉ đo upper bound  không thể dùng khi triển khai."],
        ["Tại sao 4 nhân 512 tệ hơn 1 nhân 2048 dù cùng ngân sách", "85,4 phần trăm sample ở L 512 bị cắt ngắn  nhiều quỹ đạo không tạo đáp án hợp lệ để vote."],
        ["Breadth có còn cần không", "Có  13 trên 83 bài oracle-solved cần k lớn hơn 1 trong sample pool quan sát được  nhưng phải tăng có chọn lọc."],
        ["Vì sao chưa mở Test", "Mở Test trước khi khóa feature và threshold sẽ tạo leakage từ vòng lặp điều chỉnh  làm mất giá trị confirmatory."],
        ["12,7 phần trăm tiết kiệm có đáng tin không", "Đó là kết quả chọn mô hình trên 20 bài Validation  mang tính phát triển  cần xác nhận trên Test."],
        ["MATH-500 có chứng minh generalization không", "Chưa  pilot chỉ xác nhận độ nhạy token cap và độ tin cậy adapter parser trên 30 bài development."],
        ["Điểm mới so với adaptive sampling", "Đề tài không nhận là allocator đầu tiên  trọng tâm hẹp là phối hợp hard token cap và selective resampling cho mô hình nhỏ  không verifier  với cost token thực tế."],
        ["Vì sao không dùng model lớn hoặc verifier", "Phạm vi nhắm đến inference tiết kiệm trên model nhỏ  đồng thời tách utility của allocation khỏi lợi thế của verifier bên ngoài."],
        ["L có phải reasoning depth không", "Không theo nghĩa ngữ nghĩa  L là max new tokens  nhóm chỉ dùng depth như cách gọi vận hành và luôn nêu giới hạn này."],
        ["Run L 8192 đang cho kết quả gì", "Chưa đủ dữ liệu  chỉ có 11 trên 120 record và hai record ở L 8192  nên không báo cáo kết quả."],
    ]
    add_table(doc, ["Câu hỏi", "Cách trả lời ngắn"], qa_rows, widths=[2.55, 4.4])

    add_heading(doc, "13 Danh mục artifact dùng khi trình bày", 1)
    add_table(
        doc,
        ["Artifact", "Nội dung cần chỉ"],
        [
            ["paper progress_paper.tex", "Bản thảo bài báo LNCS và trạng thái bằng chứng"],
            ["results qwen3 1 7b gsm8k n100 r1", "Grid  raw sample  thống kê  plots và oracle"],
            ["results phase2 depth baseline v1", "Candidate metrics  predictions  model và development report"],
            ["data splits phase2 gsm8k split v1.json", "79 20 100 partition và integrity hash"],
            ["results qwen3 1 7b math500 depth pilot v2 parser v2", "Kết quả 90 generation và parser audit"],
            ["docs MATH500 PARSER V2 AMENDMENT.md", "Lý do sửa parser và reprocessing contract"],
            ["tests", "134 automated tests"],
        ],
        widths=[3.1, 3.85],
    )
    add_para(doc, "Tài liệu này nên được đọc cùng PowerPoint tóm tắt. Khi trình bày  ưu tiên nói đúng trạng thái bằng chứng hơn là cố đưa ra kết luận cuối khi joint controller và frozen Test chưa hoàn thành.")

    props = doc.core_properties
    props.title = "Báo cáo tổng hợp đồ án Adaptive Test Time Compute"
    props.subject = "Tài liệu chuẩn bị trình bày đồ án tốt nghiệp"
    props.author = "Dinh-Hong Vu; The-Tai Phung; Thai-Son Bui"
    props.keywords = "adaptive test-time compute, GSM8K, MATH-500, Qwen3-1.7B"
    props.comments = "Generated from verified local project artifacts"
    doc.save(FINAL)
    print(FINAL)


if __name__ == "__main__":
    build()
