param(
    [Parameter(Mandatory=$true)][string]$InputDocx,
    [Parameter(Mandatory=$true)][string]$OutputDir
)

$ErrorActionPreference = 'Stop'
$inputPath = (Resolve-Path -LiteralPath $InputDocx).Path
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
$outputPath = (Resolve-Path -LiteralPath $OutputDir).Path

$word = $null
$doc = $null
$ppt = $null
$pres = $null

try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $word.AutomationSecurity = 3
    $doc = $word.Documents.Open($inputPath, $false, $true, $false)
    $pages = $doc.ComputeStatistics(2)
    Write-Output "pages=$pages"

    $ppt = New-Object -ComObject PowerPoint.Application
    $pres = $ppt.Presentations.Add()
    $pres.PageSetup.SlideWidth = 612
    $pres.PageSetup.SlideHeight = 792

    for ($page = 1; $page -le $pages; $page++) {
        $start = $doc.GoTo(1, 1, $page)
        if ($page -lt $pages) {
            $next = $doc.GoTo(1, 1, $page + 1)
            $end = $next.Start - 1
        } else {
            $end = $doc.Content.End - 1
        }
        $range = $doc.Range($start.Start, $end)
        $range.Select()
        $word.Selection.CopyAsPicture()
        Start-Sleep -Milliseconds 180

        $slide = $pres.Slides.Add($pres.Slides.Count + 1, 12)
        $shapeRange = $slide.Shapes.PasteSpecial(2)
        $shape = $shapeRange.Item(1)
        $shape.LockAspectRatio = 0
        $maxWidth = 576
        $maxHeight = 756
        $originalWidth = $shape.Width
        $originalHeight = $shape.Height
        $scale = [Math]::Min($maxWidth / $originalWidth, $maxHeight / $originalHeight)
        $shape.Width = $originalWidth * $scale
        $shape.Height = $originalHeight * $scale
        $shape.LockAspectRatio = -1
        $shape.Left = (612 - $shape.Width) / 2
        $shape.Top = (792 - $shape.Height) / 2

        $filename = 'page-{0:D2}.png' -f $page
        $pngPath = Join-Path $outputPath $filename
        $slide.Export($pngPath, 'PNG', 1275, 1650)
        Write-Output $filename
    }
}
finally {
    if ($pres -ne $null) { $pres.Close() }
    if ($ppt -ne $null) { $ppt.Quit() }
    if ($doc -ne $null) { $doc.Close($false) }
    if ($word -ne $null) { $word.Quit() }
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
}
