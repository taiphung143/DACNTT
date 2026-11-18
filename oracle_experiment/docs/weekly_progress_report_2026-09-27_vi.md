# BÁO CÁO TIẾN ĐỘ KHÓA LUẬN - TUẦN HIỆN TẠI

## Adaptive Test-Time Compute for Small Reasoning Models

**Thời điểm cập nhật:** 27/09/2026  
**Mục tiêu của tuần:** Chuyển từ kết quả khảo sát oracle của tuần trước sang quy trình phát triển controller có kiểm soát rò rỉ dữ liệu, xây dựng baseline đầu tiên và viết paper đến phần thực nghiệm.

---

## 1. Điểm xuất phát từ báo cáo tuần trước

Tuần trước, nhóm đã hoàn thành khảo sát Phase 1 trên Qwen3-1.7B với 99 bài GSM8K hợp lệ và lưới cấu hình:

- breadth: `k in {1, 2, 4}`;
- generation-token cap: `L in {512, 1024, 2048}`;
- tổng cộng 1.200 lượt sinh, không có lỗi thực thi;
- phân tích accuracy, actual generated tokens, latency, truncation và valid-answer rate;
- xác định depth/token cap là yếu tố chi phối trong cấu hình đã khảo sát;
- xác định breadth có ích chọn lọc nhưng lợi ích biên giảm khi `L` tăng;
- xác định joint-oracle headroom: cùng mức accuracy 83,84%, joint oracle dùng trung bình 1.023,5 token/bài, so với 4.246,7 token/bài của fixed `4 x 2048`.

Ở thời điểm đó, nhóm **chưa có controller triển khai thực tế**. Kế hoạch tiếp theo trong báo cáo tuần trước là khóa Train/Validation/Test, xây dựng depth-only baseline và sau đó phát triển joint controller.

---

## 2. Những công việc mới đã hoàn thành trong tuần này

### 2.1. Tái cấu trúc và kiểm thử lại mã nguồn

Nhóm đã tổ chức lại mã nguồn thành package `adaptive_compute`, tách rõ các thành phần:

- `analysis`: tổng hợp kết quả, kiểm định thống kê, oracle và Pareto analysis;
- `cli`: các lệnh chạy grid, tái xử lý kết quả, tạo split và huấn luyện baseline;
- `controller`: chuẩn bị dữ liệu và mô hình depth-only;
- `models`: giao diện model và adapter Transformers;
- `tests`: kiểm thử parser, aggregation, dataset, cache, experiment runner, statistics và controller.

Kết quả kiểm thử sau refactor:

- **111 automated tests passed**;
- không phát hiện regression chức năng trong các thành phần đã được kiểm thử;
- dữ liệu sinh bằng GPU và các artifact kết quả cũ được giữ nguyên.

Đây là kiểm thử phần mềm trên CPU. Nhóm chưa chạy lại toàn bộ 1.200 lượt sinh bằng GPU vì refactor không thay đổi checkpoint, prompt, decoding configuration hoặc dữ liệu kết quả đã sinh. GPU vẫn cần cho các thực nghiệm controller và dataset mới ở giai đoạn tiếp theo.

### 2.2. Khóa quy trình chia dữ liệu Phase 2 và kiểm soát leakage

Nhóm đã tạo split manifest có version và hash để ngăn rò rỉ oracle label giữa các partition:

| Partition | Số bài | Vai trò |
|---|---:|---|
| Train | 79 | Huấn luyện controller |
| Validation | 20 | Chọn mô hình và threshold |
| Test | 100 | Đánh giá xác nhận cuối cùng |

Các quyết định đã triển khai:

- sử dụng split seed 42;
- Train và Validation lấy từ tập phát triển đã được khảo sát;
- Test gồm 100 bài GSM8K mới, nằm ngoài 100 bài ban đầu;
- loại một bài đã được đánh dấu `manual_review_required` khỏi quá trình phân bổ;
- lưu problem ID, source index, question hash và ground-truth hash;
- pipeline từ chối overlap giữa các partition hoặc thay đổi âm thầm đối với frozen manifest;
- **chưa nạp hoặc đánh giá kết quả trên Test**.

Do aggregate behavior của 100 bài ban đầu đã được quan sát, Validation 20 bài chỉ được xem là tập chọn mô hình, không phải bằng chứng held-out hoàn toàn. Chỉ Test 100 bài mới có vai trò confirmatory.

### 2.3. Xây dựng depth-only controller baseline đầu tiên

Nhóm đã triển khai baseline logistic regression chỉ sử dụng các đặc trưng có thể quan sát trước khi sinh, ví dụ:

- độ dài câu hỏi và prompt token count;
- số lượng chữ số, số thập phân, phân số và toán tử;
- số câu, dấu câu và một số shallow lexical indicators.

Baseline dự đoán mức `L` trong `{512, 1024, 2048}`. Mô hình được fit trên Train và lựa chọn trên Validation. Candidate được chọn là:

```text
C = 1, class_weight = balanced, decision_quantile = 0.9
```

Kết quả trên 20 bài Validation:

| Policy | Accuracy | Correct | Avg. actual generated tokens |
|---|---:|---:|---:|
| Fixed `L=512` | 10,0% | 2/20 | 499,00 |
| Fixed `L=1024` | 45,0% | 9/20 | 843,65 |
| Fixed `L=2048` | 65,0% | 13/20 | 1.213,05 |
| Selected depth logistic | **65,0%** | **13/20** | **1.059,45** |

Depth-only controller đạt cùng accuracy với fixed `L=2048` và giảm **12,7% actual generated tokens trung bình**. Exact depth-target classification accuracy là 50,0%.

Đây là **development/model-selection result**, chưa phải kết quả tổng quát hóa. Candidate được chọn trên chính Validation 20 bài, do đó kết quả có thể lạc quan và không được trình bày như held-out Test performance.

### 2.4. Chốt bản đề xuất Research Questions và protocol v2

Từ kết quả tuần trước và rà soát related work, nhóm đã cụ thể hóa câu hỏi chính theo hướng:

> Với small open-weight reasoning models, một verifier-free lightweight sequential policy phân bổ generation-token cap và chỉ tăng số sample khi cần có cải thiện được Pareto frontier accuracy - actual generated tokens trên dữ liệu held-out so với fixed, depth-only và breadth-only baselines hay không?

Nhóm đồng thời đề xuất protocol v2:

- dataset tối thiểu: GSM8K và một subset MATH/MATH-500 được đóng băng;
- Qwen3-1.7B là model phát triển chính;
- external validation trên model thứ hai là mục tiêu giảm quy mô nếu GPU cho phép;
- tối thiểu 300 oracle-characterized development problems, trong đó ít nhất 100 bài từ dataset thứ hai;
- tối thiểu 30 positive escalation events cho mỗi quyết định breadth học được;
- `L=512` được giữ làm diagnostic/ablation; action space chính có thể dùng `L in {1024, 2048}` nếu được thầy phê duyệt;
- cost chính là toàn bộ actual generated tokens mà policy tiêu thụ, bao gồm các rollout thăm dò.

Các điểm trên là **đề xuất cần được giảng viên hướng dẫn phê duyệt trước khi chạy confirmatory experiment**, chưa phải thay đổi ngầm đối với thiết kế nghiên cứu.

### 2.5. Hoàn thiện thiết kế joint controller ở mức phương pháp

Kiến trúc được đề xuất là hierarchical, depth-first và sequential:

```text
Input features
    -> chọn initial L
    -> sinh sample 1
    -> dừng ở k=1 hoặc sinh sample 2
    -> nếu cần, dừng ở k=2 hoặc tăng lên k=4
    -> valid-only majority vote
```

Controller chỉ được sử dụng:

- đặc trưng đầu vào có trước inference;
- validity, truncation, cap utilization và độ dài của các sample đã trả chi phí;
- normalized-answer agreement sau khi có ít nhất hai sample.

Controller không được sử dụng ground truth, correctness, oracle label hoặc trajectory chưa được policy sinh ra tại Test time.

Phần joint controller hiện mới ở trạng thái **phương pháp đã thiết kế**, chưa được triển khai và chưa có kết quả thực nghiệm.

### 2.6. Xây dựng go/pivot criteria trước khi mở Test

Nhóm đã đề xuất quy tắc ra quyết định để tránh điều chỉnh kết luận theo kết quả:

- **Go Joint:** joint tăng ít nhất 3 percentage points accuracy ở chi phí trong `+-10%`, hoặc giảm ít nhất 10% token trong khi accuracy giảm không quá biên non-inferiority 2 percentage points;
- **Pivot Depth-First:** joint bị depth-only Pareto-dominate, breadth quá hiếm hoặc không tạo positive net utility;
- **Need More Data:** chưa đủ 30 positive events, confidence interval quá rộng hoặc target không ổn định qua seed;
- **Abandon Learned Controller:** sau tối thiểu 300 bài trên hai dataset, các learned policy vẫn bị fixed/heuristic baseline Pareto-dominate.

Các threshold này đang là đề xuất pre-registration và cần được chốt với giảng viên trước khi sử dụng để ra quyết định cuối cùng.

### 2.7. Viết paper đến phần thực nghiệm hiện tại

Nhóm đã tạo bản thảo paper mới và giữ nguyên file mẫu ban đầu. Bản thảo hiện có:

- Abstract;
- Introduction và Research Questions;
- Related Work;
- Problem Formulation;
- Methodology;
- Experimental Setup;
- Preliminary Results;
- Discussion;
- Limitations;
- Planned Confirmatory Evaluation;
- Conclusion và 15 tài liệu tham khảo.

Bản paper đã đưa vào các kết quả hoàn thành từ grid/oracle và depth-only Validation. Các phần joint controller, MATH, second model và held-out Test được ghi rõ là proposed/future evaluation, chưa trình bày như kết quả đã hoàn thành.

---

## 3. So sánh tiến độ tuần trước và tuần này

| Hạng mục | Trạng thái tuần trước | Tiến độ mới tuần này |
|---|---|---|
| Oracle grid | Đã hoàn thành trên 99 bài GSM8K | Giữ nguyên làm development evidence |
| Oracle headroom | Đã xác định | Chuyển thành baseline/upper-bound contract rõ ràng |
| Data split | Mới là kế hoạch | Đã khóa 79 Train / 20 Validation / 100 Test |
| Leakage control | Chưa triển khai đầy đủ | Đã có manifest, hash và overlap checks |
| Depth-only baseline | Chưa có | Đã triển khai và đánh giá trên Validation |
| Joint controller | Mới nêu định hướng | Đã đặc tả kiến trúc, feature contract và decision stages; chưa code |
| Go/pivot criteria | Chưa có | Đã đề xuất ngưỡng quyết định trước Test |
| Dataset protocol | Chỉ GSM8K | Đã đề xuất v2 với GSM8K + MATH/MATH-500 |
| Mã nguồn | Nhiều file rời ở project root | Đã refactor thành package và CLI rõ ràng |
| Kiểm thử | Chưa có xác nhận sau refactor | 111 tests passed |
| Paper | Mới có Abstract | Đã viết đến phần thực nghiệm và kết quả sơ bộ |

---

## 4. Phân loại trạng thái bằng chứng

### Đã hoàn thành và có artifact

- Phase-1 grid trên 99 bài GSM8K hợp lệ;
- phân tích depth/breadth, iso-budget và retrospective oracle;
- Phase-2 frozen split manifest;
- depth-only logistic development baseline;
- refactor mã nguồn và automated tests;
- bản thảo paper đến Preliminary Results.

### Working hypotheses

- nên cấp đủ token cap trước khi tăng breadth trong chế độ đang khảo sát;
- utility của breadth tập trung ở một nhóm thiểu số bài toán;
- cheap input và early-inference signals có thể dự đoán escalation utility.

### Phương pháp đã đề xuất nhưng chưa có kết quả

- hierarchical joint controller;
- marginal-utility training target;
- Adaptive-Consistency-style breadth baseline;
- protocol hai dataset và reduced second-model validation;
- go/pivot decision protocol.

### Đánh giá tương lai

- mở rộng development data lên ít nhất 300 bài;
- pilot và audit parser cho MATH;
- thực nghiệm joint controller trên GPU;
- repeated-seed robustness;
- one-shot evaluation trên frozen Test sau khi khóa policy.

---

## 5. Mức độ đáp ứng yêu cầu tiến độ của giảng viên

Yêu cầu:

> “Các em bắt tay thực nghiệm và viết bài báo từ đầu đến phần thực nghiệm, sau khi thực nghiệm xong thì đưa kết quả vào.”

Đánh giá hiện tại:

- **Đã bắt tay thực nghiệm:** Có. Nhóm đã xây dựng và đánh giá depth-only controller baseline trên Train/Validation.
- **Đã viết paper từ đầu đến phần thực nghiệm:** Có. Bản thảo đã có đầy đủ phần mở đầu, related work, phương pháp, experimental setup và preliminary results.
- **Đã có kết quả để đưa vào paper:** Có. Grid/oracle results và depth-only development result đã được đưa vào.
- **Đã hoàn tất thực nghiệm chính:** Chưa. Joint controller, breadth baseline, MATH và frozen Test chưa được chạy.

Vì vậy, tiến độ hiện tại **đủ để báo cáo tuần này**, nhưng chưa phải trạng thái hoàn tất thực nghiệm của đề tài. Cần trình bày depth-only result là kết quả sơ bộ trên Validation và nói rõ thực nghiệm chính tiếp theo cần GPU.

---

## 6. Hạn chế và rủi ro hiện tại

- Validation chỉ có 20 bài và đã được dùng để chọn candidate.
- Evidence hiện tại chủ yếu từ một model, một dataset và một generation seed.
- Breadth-positive examples còn ít nên chưa đủ để huấn luyện ổn định joint controller.
- `L=512` có truncation rất cao và không xuất hiện trong cheapest-correct profiles.
- Joint-oracle headroom chỉ chứng minh cơ hội hindsight, không chứng minh controller có thể học được quyết định.
- Chưa có held-out Test result, nên chưa thể đưa ra kết luận cuối cùng về Research Question.

---

## 7. Kế hoạch công việc tiếp theo

1. Trình giảng viên chốt revised RQs, dataset protocol, action space, data target, baseline set và go/pivot thresholds.
2. Audit answer parser và chạy pilot nhỏ trên MATH bằng Qwen3-1.7B.
3. Mở rộng oracle-characterized development pool, ưu tiên đạt đủ positive escalation events.
4. Triển khai Adaptive-Consistency-style breadth baseline và simple depth-first heuristic.
5. Triển khai joint controller phiên bản đơn giản bằng logistic regression trước; chỉ thử tree model nếu dữ liệu đủ.
6. So sánh joint, depth-only và breadth-only trên Validation theo Pareto frontier.
7. Khóa model, feature contract, thresholds, parser và configuration.
8. Chạy frozen Test một lần, báo cáo uncertainty và đưa kết quả cuối vào paper.

---

## 8. Tóm tắt ngắn để trình bày với giảng viên

> Tuần trước nhóm đã hoàn thành khảo sát breadth-depth và xác định joint-oracle headroom. Tuần này nhóm chuyển sang Phase 2: đã refactor và kiểm thử lại pipeline, khóa split 79 Train - 20 Validation - 100 Test để chống leakage, và triển khai depth-only logistic baseline. Trên 20 bài Validation, baseline giữ accuracy 65% như fixed `L=2048` nhưng giảm 12,7% actual generated tokens; đây mới là development result, chưa phải held-out evidence. Nhóm cũng đã đặc tả joint controller, đề xuất protocol v2 và go/pivot criteria, đồng thời viết paper đến phần thực nghiệm và đưa các kết quả hiện có vào. Bước tiếp theo là chốt protocol với thầy, mở rộng dữ liệu trên GSM8K và MATH, rồi chạy breadth/joint controller và frozen Test bằng GPU.

