# Kịch bản bảo vệ và bộ câu hỏi phản biện

Ngày cập nhật: 2026-11-18  
Deck tương ứng: `output/slides/thesis_defense_qwen3_0_6b_2026-11-18.pptx`  
Thời lượng mục tiêu: 9 phút 30 giây đến 10 phút

## 1. Thông điệp trung tâm

Khóa luận đánh giá việc phân bổ test-time compute trên hai trục: số quỹ đạo suy
luận độc lập `k` và giới hạn token sinh `L`. Trong phạm vi Qwen3-0.6B, một model
revision, một seed và hai Test pool gồm 100 câu, agreement-based breadth
stopping giữ nguyên vector đúng--sai so với fixed high-breadth và giảm khoảng
20% token tại hai điểm vận hành đã kiểm tra. Heuristic kết hợp depth và breadth
không ổn định giữa hai dataset và thất bại rõ trên MATH-500.

Câu kết luận ngắn nên nhớ:

> Bằng chứng hiện tại hỗ trợ selective breadth tại các điểm vận hành đã kiểm
> tra, nhưng không hỗ trợ một joint heuristic có khả năng khái quát qua hai
> dataset.

## 2. Phân bổ thời gian

| Slide | Nội dung | Mốc kết thúc | Thời lượng |
|---:|---|---:|---:|
| 1 | Giới thiệu đề tài | 00:35 | 0:35 |
| 2 | Bài toán và hai trục tài nguyên | 01:15 | 0:40 |
| 3 | Research Question và phạm vi | 02:00 | 0:45 |
| 4 | Thiết kế phương pháp | 02:45 | 0:45 |
| 5 | Protocol Train--Validation--Test | 03:30 | 0:45 |
| 6 | Thiết lập thực nghiệm | 04:05 | 0:35 |
| 7 | Toàn cảnh hai Test-100 | 04:35 | 0:30 |
| 8 | Kết quả GSM8K | 05:25 | 0:50 |
| 9 | Kết quả MATH-500 | 06:20 | 0:55 |
| 10 | Kết quả âm của joint heuristic | 07:10 | 0:50 |
| 11 | Đóng góp | 08:00 | 0:50 |
| 12 | Giới hạn và hướng tiếp theo | 09:05 | 1:05 |
| 13 | Kết luận | 09:40 | 0:35 |

Khoảng 20 giây còn lại dùng làm vùng đệm. Khi gần hết giờ, bỏ bớt phần mô tả
chi tiết ở slide 6 và slide 11, nhưng không bỏ slide 8--10 hoặc phần giới hạn.

Hiệu chuẩn văn bản: các đoạn nói chính có 776 từ, tương đương khoảng 6 phút 12
giây ở 125 từ/phút hoặc 7 phút 03 giây ở 110 từ/phút. Phần thời gian còn lại
dành cho chuyển slide, chỉ vào hình/bảng, ngắt nhịp và xử lý độ trễ khi trình
chiếu. Trong lần luyện thật, mục tiêu hợp lý là kết thúc trong 9:00--9:40 thay
vì cố kéo đúng 10 phút.

## 3. Kịch bản theo từng slide

### Slide 1 -- Giới thiệu

> Kính thưa thầy cô và các bạn. Nhóm em trình bày khóa luận về phân bổ
> test-time compute thích ứng cho mô hình suy luận cỡ nhỏ. Nghiên cứu tập trung
> vào Qwen3-0.6B và đánh giá sự đánh đổi giữa độ chính xác với số token thực tế
> đã sinh.

Chuyển ý: “Trước hết, nhóm xin trình bày lý do cần phân bổ compute theo từng
bài toán.”

### Slide 2 -- Bài toán nghiên cứu

> Một cấu hình cố định cấp cùng lượng compute cho cả bài dễ và bài khó. Nhóm
> xét hai trục tài nguyên. `k` là số quỹ đạo độc lập, còn `L` là giới hạn token
> cho mỗi quỹ đạo. Chính sách có thể lấy thêm mẫu hoặc dừng sớm dựa trên thông
> tin đã quan sát. Chi phí được đo bằng token thực tế đã sinh.

Nhấn mạnh: policy không dùng verifier, hidden state, đáp án chuẩn hoặc tín hiệu
từ tương lai.

### Slide 3 -- Research Question và phạm vi

> Câu hỏi nghiên cứu xem xét liệu một policy tuần tự nhẹ có thể phân bổ token
> cap và selective breadth để cải thiện biên Pareto accuracy--token so với
> fixed, depth-only và breadth-only. Phạm vi chính là Qwen3-0.6B trên GSM8K và
> MATH-500. Kết luận hiện tại giới hạn ở một revision và một seed.

Không rút gọn RQ thành “joint có tốt hơn hay không”, vì RQ so sánh đầy đủ fixed
và hai baseline thích ứng một trục.

### Slide 4 -- Thiết kế phương pháp

> Mỗi bài toán có một shared sample pool. Mọi policy replay các mẫu theo cùng
> thứ tự và cùng seed, nên so sánh accuracy và token được ghép cặp. Mỗi dataset
> có 14 policy: chín fixed, một depth-only, ba breadth-only và một joint
> heuristic tất định. Parser, aggregation và cost accounting đều được
> version hóa.

Chuyển ý: “Để tránh chọn policy theo kết quả Test, nhóm tách rõ ba vai trò dữ
liệu.”

### Slide 5 -- Protocol Train--Validation--Test

> Train chỉ dùng để đặt ngưỡng. Validation dùng để chọn policy. Test chỉ được
> mở sau khi policy đã đóng băng. Mỗi Test grid có 1.200 generation records,
> gồm 100 bài, ba mức `L` và bốn sample index. Hai grid đều hoàn tất, không có
> generation error và không có generation key trùng.

Nhấn mạnh: không thay selected policy sau khi đọc Test.

### Slide 6 -- Thiết lập thực nghiệm

> Mô hình chính là Qwen3-0.6B chạy bfloat16 trên RTX 4060 Laptop GPU. GSM8K
> dùng `L` bằng 512, 1024 và 2048. MATH-500 dùng 1024, 2048 và 4096. Cả hai dùng
> `k` bằng 1, 2 hoặc 4. Thinking mode, temperature 0,7, top-p 0,95 và seed 42
> được giữ cố định.

Nói rõ trong một câu: non-thinking, native thinking budget, budget forcing và
seed bổ sung chưa được chạy, nên thuộc phần giới hạn.

### Slide 7 -- Toàn cảnh kết quả

> Hình này biểu diễn toàn bộ 14 policy của mỗi dataset. Vòng tròn đen là policy
> đã chọn trên Validation trước khi mở Test. Đường nét đứt là biên Pareto mô tả
> trong tập policy đã đăng ký. Nhóm không dùng hình này để chọn lại policy.

Không giải thích từng điểm. Chuyển ngay sang hai kết quả chính.

### Slide 8 -- GSM8K

> Trên GSM8K, selected breadth stopping tại `L=1024` đạt 76 trên 100 với
> 1.994,52 token trung bình. Fixed `k=4` tại cùng `L` cũng đạt 76 trên 100 nhưng
> dùng 2.535,17 token. Hai policy có cùng vector đúng--sai trên 100 câu và
> breadth stopping giảm 21,33% token trong quan sát này.

Câu giới hạn bắt buộc:

> Kết quả này không chứng minh hai policy tương đương trên quần thể. Nó chỉ cho
> thấy cùng kết quả ghép cặp trên Test-100 đã quan sát.

### Slide 9 -- MATH-500

> Policy selected trước Test trên MATH-500 là fixed `k=2, L=4096`, đạt 66 trên
> 100 với 5.141,50 token. Một comparator breadth đã đăng ký đạt 73 trên 100,
> bằng fixed `k=4` tại cùng `L`, đồng thời giảm 19,96% token. Comparator này là
> kết quả phụ và không thay thế selected policy.

Chuyển ý: “Điểm quan trọng tiếp theo là joint heuristic không giữ được hành vi
ổn định khi chuyển sang MATH-500.”

### Slide 10 -- Joint heuristic

> Trên GSM8K, chênh lệch selected so với joint chưa có ý nghĩa sau hiệu chỉnh
> Holm. Trên MATH-500, joint chỉ đạt 36 trên 100 và dùng 5.788,81 token, trong
> khi selected đạt 66 trên 100 với chi phí thấp hơn. Bảng ghép cặp có 33 câu
> chỉ selected đúng và 3 câu chỉ joint đúng. Holm-adjusted p bằng
> `2,50 × 10^-6`.

Kết luận đúng mức:

> Kết quả bác bỏ joint heuristic cụ thể đã đóng băng. Nó không bác bỏ mọi
> phương pháp joint depth--breadth có thể được thiết kế trong tương lai.

### Slide 11 -- Đóng góp

> Đóng góp thứ nhất là pipeline có manifest bất biến, cache append-only,
> checkpoint, parser versioned và policy replay. Đóng góp thứ hai là protocol
> held-out có policy freeze và phân tích ghép cặp trên hai Test-100. Đóng góp
> thực nghiệm gồm bằng chứng selective breadth tại các điểm đã kiểm tra và một
> kết quả âm có giá trị về joint heuristic.

Không gọi joint heuristic là learned controller.

### Slide 12 -- Giới hạn và hướng tiếp theo

> Kết quả hiện tại giới hạn ở một model revision, một seed và hai Test pool 100
> câu. Các decoding controls chưa hoàn tất. Joint hiện tại là heuristic, chưa
> phải learned controller. Nếu tiếp tục thực nghiệm, ưu tiên là lặp selected
> policy và comparator ở seed mới, sau đó chạy non-thinking, native budget và
> budget forcing trên một split hoặc reserve set mới.

Nguyên tắc cần nói rõ: mọi đánh giá mới phải tách khỏi Test-100 đã đóng băng và
không được dùng để retune kết quả chính.

### Slide 13 -- Kết luận

> Tóm lại, selective breadth giảm 21,33% token trên GSM8K và 19,96% trên
> MATH-500 comparator khi so với fixed high-breadth tương ứng, với cùng vector
> đúng--sai trong từng Test-100. Joint heuristic không khái quát qua hai
> dataset. Vì vậy, bằng chứng hiện tại hỗ trợ breadth adaptation tại các điểm
> đã kiểm tra, nhưng chưa hỗ trợ một joint policy ổn định.

Kết thúc: “Nhóm em xin cảm ơn thầy cô và sẵn sàng trả lời câu hỏi.”

## 4. Câu hỏi phản biện và câu trả lời đề xuất

### 1. Đóng góp mới của khóa luận là gì?

Đóng góp không nằm ở một thuật toán controller học máy mới. Khóa luận đóng góp
một pipeline đánh giá có thể tái lập và kiểm toán, một protocol freeze rõ ràng,
đánh giá 14 policy trên hai Test-100, bằng chứng ghép cặp cho breadth stopping
và kết quả âm về joint heuristic. Cần trình bày đúng phạm vi này.

### 2. Vì sao controller học máy chưa được triển khai?

Pipeline và giao diện controller đã được chuẩn bị, nhưng Train data không có đủ
escalation events dương để fit một joint controller đáng tin cậy. Việc vẫn
huấn luyện trong điều kiện đó sẽ tạo một kết quả thiếu ổn định. Nhóm chuyển sang
đánh giá heuristic tất định và ghi learned controller là hướng tương lai.

### 3. Vì sao đổi từ Qwen3-1.7B sang Qwen3-0.6B?

Qwen3-1.7B được dùng trong pilot để khảo sát lưới ban đầu. Chi phí chạy toàn bộ
protocol hai dataset không phù hợp với RTX 4060 và thời gian còn lại. Nhóm chốt
Qwen3-0.6B trước thực nghiệm chính để hoàn thành đầy đủ Train--Validation--Test,
baseline và thống kê. Kết quả 1.7B được giữ riêng, không gộp với bằng chứng
0.6B.

### 4. Vì sao chỉ dùng một seed?

Giới hạn đến từ ngân sách GPU. Shared sample pool vẫn giúp so sánh các policy
trong cùng seed bằng dữ liệu ghép cặp, nhưng không đo được biến thiên giữa các
seed. Vì vậy kết luận chỉ áp dụng cho seed và revision đã chạy. Extra-seed
robustness là ưu tiên thực nghiệm tiếp theo.

### 5. Test-100 có đủ lớn không?

Test-100 cho phép một đánh giá held-out khả thi trong ngân sách khóa luận và
được báo cáo cùng Wilson 95%. Nó chưa đủ để đưa ra kết luận tổng quát mạnh, đặc
biệt khi khoảng tin cậy còn rộng. Nhóm giữ giới hạn này trong luận văn và không
biến quan sát 100 câu thành tuyên bố tổng quát.

### 6. Vì sao MATH breadth đạt 73% nhưng selected policy chỉ đạt 66%?

Fixed `k=2, L=4096` được chọn trên Validation và đóng băng trước Test. Breadth
stopping là comparator đã đăng ký nhưng đạt kết quả Test cao hơn. Thay selected
policy sau khi thấy Test sẽ tạo post-Test selection bias. Vì vậy 66% vẫn là
primary selected estimate, còn 73% được báo cáo minh bạch như secondary result.

### 7. Có thể nói breadth stopping “không làm giảm accuracy” không?

Chỉ nên nói hai policy có cùng vector đúng--sai trên Test-100 đã quan sát, với
discordant 0/0. Không nên tuyên bố population equivalence vì nghiên cứu không
thực hiện một thiết kế non-inferiority đủ power trên nhiều seed và nhiều mẫu
hơn.

### 8. Giảm 21,33% và 19,96% được tính như thế nào?

GSM8K dùng `(2535,17 - 1994,52) / 2535,17 = 21,33%`. MATH-500 dùng
`(10233,17 - 8191,12) / 10233,17 = 19,96%`. Mẫu số là mean actual generated
tokens của fixed `k=4` tại cùng `L`.

### 9. Vì sao đo actual generated tokens thay vì chỉ dùng `k × L`?

`k × L` chỉ là ngân sách danh nghĩa. Mẫu có thể kết thúc trước token cap, nên
chi phí thực tế thấp hơn. Actual generated tokens phản ánh tài nguyên mà policy
thực sự tiêu thụ và cho phép tính đúng lợi ích của stopping.

### 10. `L` có thật sự là reasoning depth không?

`L` là token cap vận hành. Nó đồng thời ảnh hưởng lượng suy luận, khả năng hoàn
thành câu trả lời và truncation. Vì vậy luận văn dùng “token cap” trong claim
chính. “Depth” chỉ là cách gọi ngắn trong không gian hành động, không phải khẳng
định rằng `L` đo trực tiếp độ sâu ngữ nghĩa.

### 11. Oracle trong nghiên cứu có ý nghĩa gì?

Oracle dùng ground truth và toàn bộ profile quan sát nên không phải policy có
thể triển khai. Nó chỉ là opportunity bound một seed để cho thấy sample pool có
headroom hay không. Kết luận chính không dùng oracle như một baseline triển
khai.

### 12. Joint heuristic thất bại vì sao?

Joint heuristic dùng prompt-length tertile để chọn `L`, sau đó dùng agreement
để chọn breadth. Prompt length không phản ánh ổn định độ khó suy luận giữa
GSM8K và MATH-500. Trên MATH-500, rule này thường chọn token cap không phù hợp
và tạo kết quả vừa kém accuracy vừa tốn token. Đây là phân tích cơ chế hợp lý,
nhưng không nên trình bày như quan hệ nhân quả đã được chứng minh.

### 13. Vì sao không dùng non-thinking, native thinking budget hoặc budget forcing?

Các đối chứng này chưa được chạy trong protocol chính vì giới hạn thời gian và
compute. Đây là thiếu sót của bằng chứng hiện tại. Nhóm đã ghi rõ trong giới
hạn, không dùng chúng như bằng chứng hoàn tất và xếp chúng vào ưu tiên đánh giá
tiếp theo.

### 14. Kết quả có bị data leakage không?

Manifest khóa danh tính và thứ tự câu hỏi. Train dùng đặt ngưỡng, Validation
dùng chọn policy, và Test chỉ được mở sau freeze. Summary, selected policy ID,
partition và source hash được kiểm tra trước khi sinh bảng. Không có retune dựa
trên Test trong báo cáo chính.

### 15. Tại sao dùng McNemar thay vì kiểm định accuracy độc lập?

Hai policy được đánh giá trên cùng 100 câu, nên outcome đúng--sai là ghép cặp.
Exact McNemar sử dụng hai ô discordant và phù hợp hơn kiểm định hai tỷ lệ độc
lập. Holm correction kiểm soát family-wise error trong họ so sánh đã đăng ký.

### 16. Tại sao không kết luận joint tốt hơn trên GSM8K khi nó dùng ít token?

Joint đạt 70% với 1.449,46 token, còn selected đạt 76% với 1.994,52 token. Hai
điểm cùng nằm trên Pareto frontier quan sát, nhưng phục vụ hai trade-off khác
nhau. Chênh accuracy ghép cặp chưa có ý nghĩa sau Holm. Vì vậy dữ liệu không
hỗ trợ tuyên bố một policy vượt trội toàn diện.

### 17. Nếu có thêm hai tuần GPU, nhóm sẽ chạy gì trước?

Ưu tiên đầu tiên là lặp selected policy và comparator trực tiếp ở seed mới để
đánh giá độ bền. Tiếp theo là ba decoding controls: non-thinking, native Qwen3
thinking budget và budget forcing. Các chạy mới phải dùng reserve set hoặc một
confirmatory split mới nếu có điều chỉnh policy.

### 18. Câu trả lời cuối cùng cho Research Question là gì?

Bằng chứng hỗ trợ selective breadth so với fixed high-breadth tại các điểm đã
kiểm tra trên hai dataset. Bằng chứng không hỗ trợ joint heuristic cụ thể và
chưa chứng minh một joint policy có khả năng khái quát. Vì vậy câu trả lời là
không đồng nhất giữa các thành phần của RQ: breadth adaptation có tín hiệu tích
cực, còn joint allocation vẫn là vấn đề mở.

## 5. Cụm từ cần tránh khi trả lời

Không nói:

- “Hai policy tương đương” khi chỉ có cùng kết quả trên 100 câu.
- “Joint controller của nhóm” vì chưa có learned controller được fit.
- “Mô hình tự xác định độ khó” vì heuristic chỉ dùng tín hiệu đầu vào đơn giản.
- “Kết quả tổng quát cho mô hình nhỏ” vì mới có một model revision và một seed.
- “Breadth policy được chọn trên MATH” vì selected policy của MATH là fixed
  `k=2, L=4096`.
- “Oracle là upper bound tuyệt đối” vì nó chỉ là opportunity bound trên pool và
  seed đã quan sát.
- “Không giảm accuracy” nếu không thêm phạm vi “trên Test-100 đã quan sát”.

## 6. Checklist trước ngày bảo vệ

- [ ] Xác nhận tên ngành/chương trình chính thức trên bìa.
- [ ] Xác nhận học hàm, học vị của giảng viên hướng dẫn.
- [ ] Kiểm tra PowerPoint trên máy dùng để trình chiếu.
- [ ] Nhúng font hoặc dùng Aptos có sẵn trên máy trình chiếu.
- [ ] Chuẩn bị một bản PDF dự phòng của slide.
- [ ] Luyện ít nhất ba lần có bấm giờ.
- [ ] Một thành viên trình bày, thành viên còn lại theo dõi thời gian và ghi câu hỏi.
- [ ] Ghi nhớ bốn số chính: `76%`, `66%`, `36%`, `21,33% / 19,96%`.
- [ ] Ghi nhớ ranh giới claim: một revision, một seed, hai Test-100.
- [ ] Không mở notebook hoặc chạy code trực tiếp trong phần trình bày chính.

## 7. Cách luyện tập

Lần 1 đọc theo kịch bản để kiểm tra đủ ý. Lần 2 chỉ nhìn tiêu đề slide và nói
bằng từ khóa. Lần 3 mô phỏng bảo vệ thật, dừng ở phút 9:40 và trả lời ngẫu nhiên
năm câu trong Mục 4. Nếu vượt 10 phút, rút gọn slide 4, 6 và 11 trước; không rút
gọn kết quả, giới hạn hoặc ranh giới claim.
