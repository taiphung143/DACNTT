# Đối chiếu nhận xét và bản sửa ngày 21-11-2026

## Đã sửa trong paper hiện tại

- Mô tả rõ thuật toán frontier: định nghĩa Pareto dominance và dynamic programming dạng multiple-choice knapsack, bắt buộc chọn một profile cho mỗi bài và Pareto-prune sau từng bài.
- Ghi đầy đủ thiết lập lấy mẫu: multinomial sampling, temperature 0.7, top-p 0.95, top-k theo cấu hình backend đã ghim, seed policy, nested sample reuse và một repetition.
- Báo tỷ lệ parse failure/truncation trên Test-100 cho cả ba token cap của GSM8K và MATH-500.
- Mô tả cụ thể parser MATH: lấy biểu thức boxed/fbox cuối cùng có ngoặc cân bằng, chuẩn hóa bảo thủ và không dùng symbolic equivalence hay last-number fallback.
- Định nghĩa từng họ kiểm định Holm; thêm số cặp bất đồng và paired bootstrap 95% CI cho các so sánh chính.
- Sửa diễn giải các kiểm định historical grid: nêu rõ các so sánh depth là lồng nhau theo seed, nên A-only bằng 0 theo thiết kế và p-value chủ yếu đo số trường hợp được cứu khỏi truncation/invalid output.
- Sửa N1: breadth-stop được gọi đúng là ESC-style two-sample agreement stopping. Paper chứng minh prediction equality với fixed k=4 là bất biến do nested samples và lowest-index tie break. Chỉ stopping frequency và token saving được coi là kết quả thực nghiệm.
- Sửa N2: kết luận âm chỉ áp dụng cho prompt-length-tertile heuristic đã thử. Paper ghi rõ depth-only đạt 25% trên MATH, thấp hơn fixed 1x2048 đạt 40%, và không phủ định toàn bộ họ joint controller.
- Bổ sung bằng chứng force-answer Test-100 để xử lý artefact cắt cụt ở cap thấp; vẫn ghi đúng đây là supplementary post-Validation control.
- Vẽ lại Figure 1, bỏ chữ “pilot items” khỏi Figure 2, ghép Figure 2–3 gọn hơn, bỏ đường kẻ dọc trong mọi bảng và sửa running head thành “Dinh-Hong Vu, The-Tai Phung and Thai-Son Bui”.
- Rút bài xuống 16 trang và loại bỏ trang float trống.
- Thêm Artifact Availability với repository và commit cụ thể; freeze dates và SHA-256 provenance được mô tả trong phương pháp.

## Không thay đổi vì bản hiện tại đã đúng

- Trang của tài liệu [5] là 6919–6932 và [8] là 14291–14305. Hai khoảng trang này khớp trực tiếp với PDF chính thức trên ACL Anthology, vì vậy không đổi theo một số trích dẫn thứ cấp có số trang khác.
- Kết quả 1.7B và 0.6B tiếp tục được tách riêng. Đây là quyết định phương pháp đúng vì khác checkpoint, action space và phạm vi dataset; paper không pool chúng thành một model-family claim.

## Còn là giới hạn, chưa được phép tuyên bố đã giải quyết

- Primary Test vẫn chỉ có một generation seed. Paper đã thu hẹp suy luận và ghi rõ bootstrap qua problem không đo được seed-to-seed variability; cần chạy thêm seed nếu muốn khắc phục hoàn toàn.
- Public commit hiện chứa core pipeline và primary policy replay. Phần force-answer bổ sung và raw generations lớn chưa nằm trong tagged public release, nên paper công khai giới hạn này. Cần commit/tag/push artefact bổ sung để đóng hoàn toàn nhận xét “chưa công bố code”.
- Native numeric thinking-budget của Qwen3 chưa được backend đã ghim hỗ trợ; paper không tuyên bố đã thử control này.

## Kiểm tra kỹ thuật

- LaTeX biên dịch thành công; không có overfull box, undefined reference hoặc placeholder hình.
- Render và kiểm tra trực quan đủ 16/16 trang: không chồng chữ, không tràn bảng, running head đúng và các hình đều nhúng trong PDF.
- Test liên quan pipeline/plot: `tests/test_sanity_pipeline.py` đạt 1/1.
