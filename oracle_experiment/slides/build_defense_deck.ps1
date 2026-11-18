$ErrorActionPreference = 'Stop'

$projectRoot = (Resolve-Path '.').Path
$buildDir = Join-Path $projectRoot '.artifact_work\defense_deck'
$renderDir = Join-Path $buildDir 'rendered'
$outputDir = Join-Path $projectRoot 'output\slides'
$candidatePath = Join-Path $buildDir 'candidate.pptx'
$finalPath = Join-Path $outputDir 'thesis_defense_qwen3_0_6b_2026-11-18.pptx'
$reviewPdfPath = Join-Path $buildDir 'review.pdf'
$logoPath = Join-Path $projectRoot 'thesis\assets\tdtu_logo.png'
$crossPlot = Join-Path $projectRoot 'paper\figures\cross_dataset_test_policy_pareto.png'
$gsmPlot = Join-Path $projectRoot 'paper\figures\gsm8k_test_policy_pareto.png'
$mathPlot = Join-Path $projectRoot 'paper\figures\math500_test_policy_pareto.png'

New-Item -ItemType Directory -Force -Path $buildDir, $renderDir, $outputDir | Out-Null
if (Test-Path $candidatePath) { Remove-Item -LiteralPath $candidatePath -Force }
if (Test-Path $finalPath) { Remove-Item -LiteralPath $finalPath -Force }
if (Test-Path $reviewPdfPath) { Remove-Item -LiteralPath $reviewPdfPath -Force }
Get-ChildItem -LiteralPath $renderDir -File -ErrorAction SilentlyContinue | Remove-Item -Force

$script:slideW = 960.0
$script:slideH = 540.0
$script:fontBody = 'Aptos'
$script:fontDisplay = 'Aptos Display'

function Rgb([int]$r, [int]$g, [int]$b) {
    return $r + ($g * 256) + ($b * 65536)
}

$script:navy = Rgb 12 35 64
$script:navy2 = Rgb 20 55 91
$script:orange = Rgb 232 119 34
$script:teal = Rgb 0 145 150
$script:cream = Rgb 248 247 242
$script:white = Rgb 255 255 255
$script:ink = Rgb 28 36 44
$script:muted = Rgb 91 103 113
$script:lightGray = Rgb 225 230 233
$script:red = Rgb 183 54 54
$script:green = Rgb 37 124 84

function Add-Rect($slide, [double]$left, [double]$top, [double]$width, [double]$height, [int]$color) {
    $shape = $slide.Shapes.AddShape(1, $left, $top, $width, $height)
    $shape.Fill.ForeColor.RGB = $color
    $shape.Fill.Solid()
    $shape.Line.Visible = 0
    return $shape
}

function Add-Text($slide, [string]$text, [double]$left, [double]$top, [double]$width, [double]$height,
                  [double]$fontSize = 18, [int]$color = 0, [bool]$bold = $false,
                  [string]$font = '', [int]$align = 1, [int]$vertical = 1) {
    if ($color -eq 0) { $color = $script:ink }
    if ([string]::IsNullOrWhiteSpace($font)) { $font = $script:fontBody }
    $shape = $slide.Shapes.AddTextbox(1, $left, $top, $width, $height)
    $shape.Line.Visible = 0
    $shape.Fill.Visible = 0
    $shape.TextFrame.MarginLeft = 0
    $shape.TextFrame.MarginRight = 0
    $shape.TextFrame.MarginTop = 0
    $shape.TextFrame.MarginBottom = 0
    $shape.TextFrame.WordWrap = -1
    $shape.TextFrame.AutoSize = 0
    $shape.TextFrame.VerticalAnchor = $vertical
    $range = $shape.TextFrame.TextRange
    $range.Text = $text
    $range.Font.Name = $font
    $range.Font.Size = $fontSize
    $range.Font.Color.RGB = $color
    $range.Font.Bold = $(if ($bold) { -1 } else { 0 })
    $range.ParagraphFormat.Alignment = $align
    return $shape
}

function Add-Bullets($slide, [string[]]$items, [double]$left, [double]$top, [double]$width, [double]$height,
                     [double]$fontSize = 19, [int]$color = 0, [double]$spaceAfter = 9) {
    if ($color -eq 0) { $color = $script:ink }
    $shape = Add-Text $slide ($items -join "`r") $left $top $width $height $fontSize $color $false $script:fontBody 1 1
    $shape.TextFrame.Ruler.Levels.Item(1).FirstMargin = 12
    $shape.TextFrame.Ruler.Levels.Item(1).LeftMargin = 24
    for ($i = 1; $i -le $items.Count; $i++) {
        $paragraph = $shape.TextFrame.TextRange.Paragraphs($i, 1)
        $paragraph.ParagraphFormat.Bullet.Visible = -1
        $paragraph.ParagraphFormat.Bullet.Type = 1
        $paragraph.ParagraphFormat.Bullet.Character = 8226
        $paragraph.ParagraphFormat.SpaceAfter = $spaceAfter
    }
    return $shape
}

function Add-ImageFit($slide, [string]$path, [double]$left, [double]$top, [double]$width, [double]$height) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Missing image: $path" }
    $image = $slide.Shapes.AddPicture($path, 0, -1, $left, $top, -1, -1)
    $scale = [Math]::Min($width / $image.Width, $height / $image.Height)
    $image.LockAspectRatio = -1
    $image.Width = $image.Width * $scale
    $image.Height = $image.Height * $scale
    $image.Left = $left + (($width - $image.Width) / 2)
    $image.Top = $top + (($height - $image.Height) / 2)
    return $image
}

function Add-SlideTitle($slide, [string]$title, [int]$number, [string]$section = '') {
    Add-Text $slide $title 54 35 820 48 28 $script:navy $true $script:fontDisplay 1 1 | Out-Null
    Add-Rect $slide 54 91 52 4 $script:orange | Out-Null
    if (-not [string]::IsNullOrWhiteSpace($section)) {
        Add-Text $slide $section.ToUpperInvariant() 720 42 180 18 10 $script:muted $true $script:fontBody 3 1 | Out-Null
    }
    Add-Text $slide ([string]$number) 892 504 22 16 10 $script:muted $false $script:fontBody 3 1 | Out-Null
}

function Add-Notes($slide, [string]$notes) {
    try {
        $placeholder = $slide.NotesPage.Shapes.Placeholders.Item(2)
        $placeholder.TextFrame.TextRange.Text = $notes
    } catch {
        Write-Warning "Could not add speaker notes to slide $($slide.SlideIndex): $($_.Exception.Message)"
    }
}

function Add-Table($slide, [object[][]]$data, [double]$left, [double]$top, [double]$width, [double]$height,
                   [double[]]$colFractions, [double]$fontSize = 15) {
    $rows = $data.Count
    $cols = $data[0].Count
    $shape = $slide.Shapes.AddTable($rows, $cols, $left, $top, $width, $height)
    $table = $shape.Table
    for ($c = 1; $c -le $cols; $c++) {
        $table.Columns.Item($c).Width = $width * $colFractions[$c - 1]
    }
    for ($r = 1; $r -le $rows; $r++) {
        for ($c = 1; $c -le $cols; $c++) {
            $cell = $table.Cell($r, $c).Shape
            $cell.TextFrame.TextRange.Text = [string]$data[$r - 1][$c - 1]
            $cell.TextFrame.TextRange.Font.Name = $script:fontBody
            $cell.TextFrame.TextRange.Font.Size = $fontSize
            $cell.TextFrame.TextRange.Font.Color.RGB = $(if ($r -eq 1) { $script:white } else { $script:ink })
            $cell.TextFrame.TextRange.Font.Bold = $(if ($r -eq 1) { -1 } else { 0 })
            $cell.TextFrame.TextRange.ParagraphFormat.Alignment = 2
            $cell.TextFrame.VerticalAnchor = 3
            $cell.Fill.ForeColor.RGB = $(if ($r -eq 1) { $script:navy } elseif ($r % 2 -eq 0) { $script:cream } else { $script:white })
            $cell.Fill.Solid()
            for ($borderIndex = 1; $borderIndex -le 4; $borderIndex++) {
                $border = $table.Cell($r, $c).Borders.Item($borderIndex)
                $border.ForeColor.RGB = $script:lightGray
                $border.Weight = 0.75
            }
            $cell.TextFrame.MarginLeft = 5
            $cell.TextFrame.MarginRight = 5
            $cell.TextFrame.MarginTop = 3
            $cell.TextFrame.MarginBottom = 3
        }
    }
    return $shape
}

$powerPoint = $null
$presentation = $null
try {
    $powerPoint = New-Object -ComObject PowerPoint.Application
    $powerPoint.Visible = -1
    $presentation = $powerPoint.Presentations.Add()
    $presentation.PageSetup.SlideWidth = $script:slideW
    $presentation.PageSetup.SlideHeight = $script:slideH

    # Slide 1: cover
    $slide = $presentation.Slides.Add(1, 12)
    Add-Rect $slide 0 0 $script:slideW $script:slideH $script:navy | Out-Null
    Add-Rect $slide 0 0 16 $script:slideH $script:orange | Out-Null
    Add-ImageFit $slide $logoPath 744 40 150 112 | Out-Null
    Add-Text $slide 'PHÂN BỔ TEST-TIME COMPUTE THÍCH ỨNG' 62 112 650 62 30 $script:white $true $script:fontDisplay 1 1 | Out-Null
    Add-Text $slide 'CHO MÔ HÌNH SUY LUẬN CỠ NHỎ' 62 176 650 54 30 $script:white $true $script:fontDisplay 1 1 | Out-Null
    Add-Text $slide 'Adaptive Test-Time Compute for Small Reasoning Models' 62 250 680 32 18 (Rgb 197 215 227) $false $script:fontBody 1 1 | Out-Null
    Add-Rect $slide 62 314 90 5 $script:orange | Out-Null
    Add-Text $slide "The-Tai Phung · 52300059`rThai-Son Bui · 52300058" 62 342 390 62 18 $script:white $false $script:fontBody 1 1 | Out-Null
    Add-Text $slide 'Giảng viên hướng dẫn: Dinh-Hong Vu' 516 350 378 28 16 $script:white $false $script:fontBody 3 1 | Out-Null
    Add-Text $slide 'Tôn Đức Thắng University · 2026' 62 474 832 20 12 (Rgb 177 199 214) $false $script:fontBody 1 1 | Out-Null
    Add-Notes $slide "Kính thưa thầy cô và các bạn. Nhóm em trình bày khóa luận về phân bổ test-time compute thích ứng cho mô hình suy luận cỡ nhỏ. Nghiên cứu tập trung vào Qwen3-0.6B, hai trục tài nguyên là số mẫu độc lập và giới hạn token sinh, với mục tiêu đánh giá đánh đổi giữa độ chính xác và chi phí token thực tế."

    # Slide 2: problem
    $slide = $presentation.Slides.Add(2, 12)
    Add-SlideTitle $slide 'Bài toán nghiên cứu' 2 'Động lực'
    Add-Text $slide 'Cấu hình cố định dùng cùng mức compute cho mọi bài toán' 54 126 830 40 24 $script:navy $true $script:fontDisplay 1 1 | Out-Null
    Add-Text $slide 'Hai trục tài nguyên' 54 205 230 28 18 $script:orange $true $script:fontBody 1 1 | Out-Null
    Add-Text $slide 'k' 54 248 50 50 36 $script:teal $true $script:fontDisplay 2 3 | Out-Null
    Add-Text $slide 'Số quỹ đạo suy luận độc lập' 120 251 280 44 20 $script:ink $false $script:fontBody 1 3 | Out-Null
    Add-Text $slide 'L' 54 322 50 50 36 $script:orange $true $script:fontDisplay 2 3 | Out-Null
    Add-Text $slide 'Giới hạn token sinh cho mỗi quỹ đạo' 120 323 330 50 20 $script:ink $false $script:fontBody 1 3 | Out-Null
    Add-Rect $slide 500 194 2 210 $script:lightGray | Out-Null
    Add-Text $slide 'Mục tiêu đánh giá' 546 205 280 28 18 $script:orange $true $script:fontBody 1 1 | Out-Null
    Add-Bullets $slide @(
        'Tăng compute khi bài toán thực sự cần',
        'Dừng lấy mẫu khi đã có đồng thuận đủ mạnh',
        'Đo chi phí bằng token thực tế đã sinh',
        'So sánh trên biên Pareto accuracy–token'
    ) 530 246 356 174 18 $script:ink 10 | Out-Null
    Add-Text $slide 'Ràng buộc: không verifier, không hidden state, không dùng nhãn Test khi quyết định' 54 454 832 38 16 $script:muted $false $script:fontBody 1 1 | Out-Null
    Add-Notes $slide "Động lực xuất phát từ việc một cấu hình cố định áp dụng cùng lượng compute cho bài dễ và bài khó. Nhóm xét hai trục. k là số quỹ đạo độc lập, còn L là giới hạn token cho mỗi quỹ đạo. Chi phí được tính bằng số token thực tế đã sinh. Chính sách chỉ được dùng thông tin quan sát hợp lệ, không dùng verifier, hidden state hay đáp án chuẩn."

    # Slide 3: RQ and scope
    $slide = $presentation.Slides.Add(3, 12)
    Add-SlideTitle $slide 'Câu hỏi nghiên cứu' 3 'Nghiên cứu'
    Add-Text $slide 'Liệu một policy tuần tự nhẹ, không dùng verifier, có thể phân bổ token cap và bổ sung mẫu độc lập để cải thiện biên Pareto accuracy–token so với fixed, depth-only và breadth-only?' 74 132 812 122 25 $script:navy $true $script:fontDisplay 1 3 | Out-Null
    Add-Rect $slide 74 276 812 2 $script:lightGray | Out-Null
    Add-Text $slide 'Phạm vi đã chốt' 74 305 220 28 18 $script:orange $true $script:fontBody 1 1 | Out-Null
    Add-Bullets $slide @(
        'Mô hình chính: Qwen3-0.6B',
        'Hai benchmark: GSM8K và MATH-500',
        'Một model revision, một seed sinh mẫu',
        'Train chọn ngưỡng, Validation chọn policy, Test chỉ báo cáo'
    ) 74 346 812 128 18 $script:ink 6 | Out-Null
    Add-Notes $slide "Đây là câu hỏi nghiên cứu đã chốt. Nhóm kiểm tra liệu một policy tuần tự nhẹ có cải thiện biên Pareto so với cấu hình cố định và các baseline chỉ thích ứng theo một trục hay không. Phạm vi chính là Qwen3-0.6B trên GSM8K và MATH-500. Train, Validation và Test có vai trò tách biệt để tránh điều chỉnh theo Test."

    # Slide 4: method
    $slide = $presentation.Slides.Add(4, 12)
    Add-SlideTitle $slide 'Thiết kế phương pháp' 4 'Phương pháp'
    Add-Text $slide 'Shared sample pool' 58 135 210 30 20 $script:orange $true $script:fontBody 1 1 | Out-Null
    Add-Text $slide 'Mỗi bài có 4 mẫu ứng viên ở từng mức L. Mọi policy replay cùng thứ tự mẫu và cùng seed.' 58 176 350 90 18 $script:ink $false $script:fontBody 1 1 | Out-Null
    Add-Text $slide 'Các policy so sánh' 510 135 260 30 20 $script:orange $true $script:fontBody 1 1 | Out-Null
    Add-Bullets $slide @(
        '9 cấu hình fixed k × L',
        '1 depth-only heuristic',
        '3 breadth agreement-stopping',
        '1 joint heuristic tất định'
    ) 500 176 360 120 18 $script:ink 5 | Out-Null
    Add-Rect $slide 54 310 832 2 $script:lightGray | Out-Null
    Add-Text $slide 'Hợp đồng đánh giá' 58 342 240 30 20 $script:orange $true $script:fontBody 1 1 | Out-Null
    Add-Bullets $slide @(
        'Parser nghiêm ngặt và valid-only aggregation',
        'Accuracy exact-answer và actual generated tokens',
        'Wilson 95%, exact McNemar và Holm correction',
        'Policy được đóng băng trước khi mở Test'
    ) 300 338 560 132 18 $script:ink 5 | Out-Null
    Add-Notes $slide "Thiết kế dùng shared sample pool. Mỗi policy tiêu thụ các mẫu từ cùng một kho theo thứ tự cố định, nhờ đó so sánh accuracy và token được ghép cặp. Mỗi dataset có 14 policy gồm fixed, depth-only, breadth-only và joint heuristic. Parser và quy tắc tổng hợp được version hóa. Policy phải đóng băng trước khi mở Test."

    # Slide 5: protocol table
    $slide = $presentation.Slides.Add(5, 12)
    Add-SlideTitle $slide 'Protocol Train–Validation–Test' 5 'Thực nghiệm'
    $splitData = @(
        @('Dataset', 'Train', 'Validation', 'Test', 'Reserve'),
        @('GSM8K', '79', '20', '100', '0'),
        @('MATH-500', '80', '20', '100', '300')
    )
    Add-Table $slide $splitData 70 136 820 150 @(0.32,0.17,0.17,0.17,0.17) 16 | Out-Null
    Add-Text $slide 'Tính toàn vẹn của Test grid' 70 325 300 30 20 $script:orange $true $script:fontBody 1 1 | Out-Null
    Add-Bullets $slide @(
        '1.200 raw records cho mỗi dataset',
        '14 policy đã đăng ký trước khi báo cáo',
        '0 generation error và 0 duplicate generation key',
        'Không retune hoặc thay selected policy sau khi đọc Test'
    ) 70 365 820 118 18 $script:ink 5 | Out-Null
    Add-Notes $slide "Train chỉ dùng để chọn ngưỡng cho heuristic. Validation chọn policy. Test được mở sau khi freeze. Mỗi Test grid gồm 100 bài, ba mức token cap và bốn sample index, tổng cộng 1.200 raw records. Các kiểm tra toàn vẹn xác nhận không có lỗi sinh và không có khóa generation trùng."

    # Slide 6: setup
    $slide = $presentation.Slides.Add(6, 12)
    Add-SlideTitle $slide 'Thiết lập thực nghiệm chính' 6 'Thực nghiệm'
    Add-Text $slide 'Mô hình và phần cứng' 58 132 300 30 20 $script:orange $true $script:fontBody 1 1 | Out-Null
    Add-Bullets $slide @(
        'Qwen3-0.6B, bfloat16, CUDA',
        'NVIDIA GeForce RTX 4060 Laptop GPU',
        'Thinking mode, temperature 0,7, top-p 0,95, seed 42'
    ) 58 174 380 112 18 $script:ink 7 | Out-Null
    Add-Text $slide 'Không gian hành động' 520 132 300 30 20 $script:orange $true $script:fontBody 1 1 | Out-Null
    $gridData = @(
        @('Dataset', 'k', 'L'),
        @('GSM8K', '1, 2, 4', '512, 1024, 2048'),
        @('MATH-500', '1, 2, 4', '1024, 2048, 4096')
    )
    Add-Table $slide $gridData 500 174 390 120 @(0.34,0.24,0.42) 14 | Out-Null
    Add-Rect $slide 54 322 832 2 $script:lightGray | Out-Null
    Add-Text $slide 'Đối chứng chưa chạy' 58 352 260 30 20 $script:red $true $script:fontBody 1 1 | Out-Null
    Add-Text $slide 'Non-thinking mode, native thinking-budget của Qwen3, budget forcing và seed bổ sung được ghi nhận là giới hạn và công việc tương lai.' 58 394 820 64 18 $script:ink $false $script:fontBody 1 1 | Out-Null
    Add-Notes $slide "Mô hình chính là Qwen3-0.6B chạy bfloat16 trên RTX 4060 Laptop. GSM8K dùng ba mức L từ 512 đến 2048, còn MATH-500 dùng từ 1024 đến 4096. Mỗi dataset dùng k bằng 1, 2 hoặc 4. Các đối chứng decoding mà phản biện yêu cầu chưa được chạy, nên nhóm giữ chúng trong phần giới hạn thay vì trình bày như bằng chứng hoàn tất."

    # Slide 7: overview figure
    $slide = $presentation.Slides.Add(7, 12)
    Add-SlideTitle $slide 'Accuracy–token trên hai Test-100' 7 'Kết quả'
    Add-ImageFit $slide $crossPlot 70 116 820 330 | Out-Null
    Add-Text $slide 'Vòng tròn đen: selected trước Test. Đường nét đứt: biên Pareto mô tả của 14 policy đã đăng ký.' 94 460 772 30 14 $script:muted $false $script:fontBody 2 1 | Out-Null
    Add-Notes $slide "Hình này tổng hợp toàn bộ 14 policy trên mỗi Test-100. Vòng tròn đen đánh dấu policy đã chọn trên Validation trước khi mở Test. Đường Pareto chỉ có ý nghĩa mô tả trong tập policy đã đăng ký. Nhóm không dùng hình này để chọn lại policy sau Test."

    # Slide 8: GSM8K
    $slide = $presentation.Slides.Add(8, 12)
    Add-SlideTitle $slide 'GSM8K: breadth stopping giữ accuracy và giảm 21,33% token' 8 'Kết quả'
    Add-ImageFit $slide $gsmPlot 46 128 520 312 | Out-Null
    Add-Text $slide 'Selected breadth stop' 600 137 290 26 18 $script:orange $true $script:fontBody 1 1 | Out-Null
    Add-Text $slide '76/100' 600 174 210 58 38 $script:navy $true $script:fontDisplay 1 1 | Out-Null
    Add-Text $slide '1.994,52 token trung bình' 600 226 285 28 17 $script:muted $false $script:fontBody 1 1 | Out-Null
    Add-Text $slide 'Fixed k=4, L=1024' 600 282 290 26 18 $script:orange $true $script:fontBody 1 1 | Out-Null
    Add-Text $slide '76/100 · 2.535,17 token' 600 319 290 34 22 $script:navy $true $script:fontDisplay 1 1 | Out-Null
    Add-Text $slide 'Cùng vector đúng–sai trên 100 câu, discordant 0/0' 600 375 290 54 16 $script:ink $false $script:fontBody 1 1 | Out-Null
    Add-Text $slide 'Wilson 95% của selected: [66,8%; 83,3%]' 600 450 290 24 14 $script:muted $false $script:fontBody 1 1 | Out-Null
    Add-Notes $slide "Trên GSM8K, policy breadth stopping được chọn trước Test đạt 76 trên 100 với 1.994,52 token trung bình. Fixed k bằng 4 tại L bằng 1024 cũng đạt 76 trên 100 nhưng dùng 2.535,17 token. Hai policy có cùng vector đúng sai trên 100 câu, tương ứng giảm 21,33 phần trăm token trong quan sát này. Kết quả không chứng minh tương đương trên quần thể."

    # Slide 9: MATH
    $slide = $presentation.Slides.Add(9, 12)
    Add-SlideTitle $slide 'MATH-500: kết quả chính và comparator breadth' 9 'Kết quả'
    Add-ImageFit $slide $mathPlot 44 126 510 314 | Out-Null
    Add-Text $slide 'Selected trước Test' 592 133 286 24 18 $script:orange $true $script:fontBody 1 1 | Out-Null
    Add-Text $slide 'Fixed k=2, L=4096' 592 169 290 30 22 $script:navy $true $script:fontDisplay 1 1 | Out-Null
    Add-Text $slide '66/100 · 5.141,50 token' 592 207 290 28 18 $script:ink $false $script:fontBody 1 1 | Out-Null
    Add-Text $slide 'Comparator breadth stop' 592 269 286 24 18 $script:orange $true $script:fontBody 1 1 | Out-Null
    Add-Text $slide '73/100 · 8.191,12 token' 592 305 290 30 21 $script:navy $true $script:fontDisplay 1 1 | Out-Null
    Add-Text $slide 'Fixed k=4, L=4096: 73/100 · 10.233,17 token' 592 350 292 54 16 $script:ink $false $script:fontBody 1 1 | Out-Null
    Add-Text $slide 'Breadth giảm 19,96% token so với fixed k=4. Đây là secondary result đã đăng ký, không thay selected policy.' 592 418 296 62 15 $script:muted $false $script:fontBody 1 1 | Out-Null
    Add-Notes $slide "Trên MATH-500, policy selected trước Test là fixed k bằng 2, L bằng 4096. Policy này đạt 66 trên 100. Một comparator breadth stopping đã đăng ký đạt 73 trên 100, bằng fixed k bằng 4 tại cùng L, đồng thời giảm 19,96 phần trăm token. Comparator này là kết quả phụ. Nhóm không dùng kết quả Test mạnh hơn để thay policy selected."

    # Slide 10: negative result
    $slide = $presentation.Slides.Add(10, 12)
    Add-SlideTitle $slide 'Joint heuristic không ổn định giữa hai dataset' 10 'Kết quả'
    $jointData = @(
        @('Dataset', 'Selected', 'Joint', 'Δ accuracy', 'Holm p'),
        @('GSM8K', '76%', '70%', '+6 điểm', '0,4922'),
        @('MATH-500', '66%', '36%', '+30 điểm', '2,50 × 10⁻⁶')
    )
    Add-Table $slide $jointData 62 140 836 150 @(0.20,0.19,0.18,0.22,0.21) 15 | Out-Null
    Add-Text $slide 'MATH-500 paired evidence' 62 329 320 28 20 $script:red $true $script:fontBody 1 1 | Out-Null
    Add-Bullets $slide @(
        '33 câu chỉ selected đúng, 3 câu chỉ joint đúng',
        'Joint dùng 5.788,81 token, cao hơn selected 647,31 token',
        'Joint bị point-dominated và kém selected có ý nghĩa sau hiệu chỉnh Holm'
    ) 62 368 836 104 18 $script:ink 6 | Out-Null
    Add-Notes $slide "Kết quả âm quan trọng nằm ở joint heuristic. Trên GSM8K, chênh lệch giữa selected và joint chưa có ý nghĩa sau Holm. Trên MATH-500, joint chỉ đạt 36 trên 100 và còn dùng nhiều token hơn selected fixed. Bảng ghép cặp có 33 câu chỉ selected đúng và 3 câu chỉ joint đúng. Kết quả cho thấy heuristic kết hợp không khái quát ổn định giữa hai dataset."

    # Slide 11: contributions
    $slide = $presentation.Slides.Add(11, 12)
    Add-SlideTitle $slide 'Đóng góp đã hoàn thành' 11 'Đóng góp'
    Add-Text $slide '01' 62 133 64 48 32 $script:teal $true $script:fontDisplay 1 1 | Out-Null
    Add-Text $slide 'Pipeline tái lập' 142 138 280 28 21 $script:navy $true $script:fontDisplay 1 1 | Out-Null
    Add-Text $slide 'Manifest bất biến, append-only cache, checkpoint, parser versioned và policy replay.' 142 171 680 45 17 $script:ink $false $script:fontBody 1 1 | Out-Null
    Add-Text $slide '02' 62 233 64 48 32 $script:teal $true $script:fontDisplay 1 1 | Out-Null
    Add-Text $slide 'Đánh giá held-out có đăng ký' 142 238 360 28 21 $script:navy $true $script:fontDisplay 1 1 | Out-Null
    Add-Text $slide '14 policy trên hai Test-100, policy freeze trước Test và phân tích ghép cặp.' 142 271 680 45 17 $script:ink $false $script:fontBody 1 1 | Out-Null
    Add-Text $slide '03' 62 333 64 48 32 $script:teal $true $script:fontDisplay 1 1 | Out-Null
    Add-Text $slide 'Bằng chứng breadth và kết quả âm của joint' 142 338 500 28 21 $script:navy $true $script:fontDisplay 1 1 | Out-Null
    Add-Text $slide 'Breadth stopping giảm khoảng 20% token so với fixed high-breadth. Joint heuristic thất bại rõ trên MATH-500.' 142 371 700 58 17 $script:ink $false $script:fontBody 1 1 | Out-Null
    Add-Notes $slide "Đóng góp đầu tiên là pipeline có thể tái lập và kiểm toán. Đóng góp thứ hai là protocol held-out với policy freeze và 14 policy trên mỗi dataset. Đóng góp thực nghiệm gồm bằng chứng tích cực cho agreement-based breadth stopping tại các mức L đã xét và một kết quả âm có giá trị về joint heuristic."

    # Slide 12: limitations
    $slide = $presentation.Slides.Add(12, 12)
    Add-SlideTitle $slide 'Giới hạn và đánh giá tiếp theo' 12 'Giới hạn'
    Add-Text $slide 'Giới hạn của bằng chứng hiện tại' 58 132 360 30 20 $script:red $true $script:fontBody 1 1 | Out-Null
    Add-Bullets $slide @(
        'Một model revision và một seed sinh mẫu',
        'Mỗi Test pool gồm 100 câu',
        'Chưa có decoding controls theo yêu cầu phản biện',
        'Joint hiện tại là heuristic, chưa phải learned controller'
    ) 58 174 390 168 18 $script:ink 8 | Out-Null
    Add-Text $slide 'Thứ tự ưu tiên tiếp theo' 526 132 330 30 20 $script:green $true $script:fontBody 1 1 | Out-Null
    Add-Bullets $slide @(
        'Lặp selected policy và comparator ở seed mới',
        'Chạy non-thinking, native budget và budget forcing',
        'Dùng reserve set cho confirmatory evaluation mới',
        'Chỉ huấn luyện controller khi có đủ escalation events'
    ) 510 174 378 168 18 $script:ink 8 | Out-Null
    Add-Rect $slide 54 374 832 2 $script:lightGray | Out-Null
    Add-Text $slide 'Nguyên tắc: mọi đánh giá mới phải tách khỏi Test-100 đã đóng băng và không được dùng để retune kết quả chính.' 74 410 792 62 18 $script:navy $true $script:fontBody 2 3 | Out-Null
    Add-Notes $slide "Bằng chứng hiện tại còn giới hạn ở một revision, một seed và hai Test pool 100 câu. Nhóm chưa chạy các decoding controls và chưa có learned controller. Nếu còn thời gian GPU, ưu tiên đầu tiên là lặp selected policy và comparator ở seed mới. Các đánh giá mới phải dùng split mới hoặc reserve set, không retune Test-100 đã đóng băng."

    # Slide 13: conclusion
    $slide = $presentation.Slides.Add(13, 12)
    Add-Rect $slide 0 0 $script:slideW $script:slideH $script:navy | Out-Null
    Add-Text $slide 'KẾT LUẬN' 62 56 280 36 18 $script:orange $true $script:fontBody 1 1 | Out-Null
    Add-Text $slide 'Selective breadth tiết kiệm compute tại các điểm vận hành đã kiểm tra' 62 123 820 80 31 $script:white $true $script:fontDisplay 1 1 | Out-Null
    Add-Text $slide 'GSM8K' 62 258 150 26 16 (Rgb 177 199 214) $true $script:fontBody 1 1 | Out-Null
    Add-Text $slide '−21,33% token' 62 291 250 44 27 $script:white $true $script:fontDisplay 1 1 | Out-Null
    Add-Text $slide 'MATH-500 comparator' 360 258 230 26 16 (Rgb 177 199 214) $true $script:fontBody 1 1 | Out-Null
    Add-Text $slide '−19,96% token' 360 291 250 44 27 $script:white $true $script:fontDisplay 1 1 | Out-Null
    Add-Text $slide 'Joint heuristic' 676 258 180 26 16 (Rgb 177 199 214) $true $script:fontBody 1 1 | Out-Null
    Add-Text $slide 'Không khái quát' 676 291 220 44 27 $script:orange $true $script:fontDisplay 1 1 | Out-Null
    Add-Rect $slide 62 381 832 2 (Rgb 64 91 117) | Out-Null
    Add-Text $slide 'Cảm ơn thầy cô đã lắng nghe' 62 412 600 36 22 $script:white $true $script:fontDisplay 1 1 | Out-Null
    Add-Text $slide 'Câu hỏi và thảo luận' 62 455 600 26 16 (Rgb 177 199 214) $false $script:fontBody 1 1 | Out-Null
    Add-ImageFit $slide $logoPath 792 406 102 74 | Out-Null
    Add-Notes $slide "Tóm lại, selective breadth tạo ra mức tiết kiệm token quan sát được tại các điểm vận hành đã kiểm tra trên cả hai dataset. Tuy nhiên, joint heuristic không khái quát và thất bại rõ trên MATH-500. Vì vậy, câu trả lời cho Research Question là có bằng chứng hỗ trợ cho breadth adaptation, nhưng chưa có bằng chứng hỗ trợ một policy kết hợp ổn định. Nhóm xin cảm ơn và sẵn sàng trả lời câu hỏi."

    # Save candidate, reopen, and save the final copy.
    $presentation.SaveAs($candidatePath, 24)
    $presentation.Close()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($presentation) | Out-Null
    $presentation = $null

    $presentation = $powerPoint.Presentations.Open($candidatePath, 0, 0, 0)
    if ($presentation.Slides.Count -ne 13) { throw "Expected 13 slides, got $($presentation.Slides.Count)" }
    $presentation.SaveCopyAs($finalPath, 24)
    $presentation.SaveAs($reviewPdfPath, 32)
    for ($i = 1; $i -le $presentation.Slides.Count; $i++) {
        $pngPath = Join-Path $renderDir ("slide-{0:D2}.png" -f $i)
        $presentation.Slides.Item($i).Export($pngPath, 'PNG', 1920, 1080)
    }
    $presentation.Close()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($presentation) | Out-Null
    $presentation = $null
} finally {
    if ($presentation -ne $null) {
        try { $presentation.Close() } catch {}
        [System.Runtime.InteropServices.Marshal]::ReleaseComObject($presentation) | Out-Null
    }
    if ($powerPoint -ne $null) {
        try { $powerPoint.Quit() } catch {}
        [System.Runtime.InteropServices.Marshal]::ReleaseComObject($powerPoint) | Out-Null
    }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}

$hash = (Get-FileHash -LiteralPath $finalPath -Algorithm SHA256).Hash
Write-Output "FINAL=$finalPath"
Write-Output "SHA256=$hash"
Write-Output "SLIDES=13"
Write-Output "RENDER_DIR=$renderDir"
