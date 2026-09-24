$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$qa = Join-Path $projectRoot 'doc\assets\template_29_qa'
$source = Join-Path $qa '乐章雅韵音乐主题-18版式样例.pptx'
$output = Join-Path $qa 'native-renders'
New-Item -ItemType Directory -Path $output -Force | Out-Null
$summaryPath = Join-Path $qa 'native-render-summary.json'
@{ status = 'RUNNING' } | ConvertTo-Json | Set-Content -LiteralPath $summaryPath -Encoding utf8
$app = New-Object -ComObject PowerPoint.Application
$previousSecurity = $app.AutomationSecurity
$deck = $null
function Get-NativeTexts($shapes) {
    # 读取原生文本框及分组子项，证明导出后文字仍为可编辑对象。
    $texts = @()
    foreach ($shape in $shapes) {
        if ($shape.Type -eq 6) { $texts += Get-NativeTexts $shape.GroupItems }
        elseif ($shape.HasTextFrame -eq -1 -and $shape.TextFrame.HasText -eq -1) { $texts += [string]$shape.TextFrame.TextRange.Text }
    }
    return $texts
}
try {
    # 禁用宏并只读打开本次导出的样例，不保存或修改用户原稿。
    $app.AutomationSecurity = 3
    $deck = $app.Presentations.Open($source, -1, 0, 0)
    if ($deck.Slides.Count -ne 18) { throw 'PowerPoint 打开的页面数量不是 18' }
    $pages = @()
    for ($i = 1; $i -le $deck.Slides.Count; $i++) {
        $deck.Slides.Item($i).Export((Join-Path $output ('slide-{0:D2}.png' -f $i)), 'PNG', 1280, 720)
        $pages += @{ number=$i; editableTexts=@(Get-NativeTexts $deck.Slides.Item($i).Shapes) }
    }
    @{ status = 'PASS'; source = $source; sourceSha256 = (Get-FileHash -LiteralPath $source).Hash.ToLower();
       slides = $deck.Slides.Count; width = $deck.PageSetup.SlideWidth; height = $deck.PageSetup.SlideHeight;
       renderer = 'PowerPoint COM'; output = $output; pages=$pages } |
        ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryPath -Encoding utf8
    Get-Content -LiteralPath $summaryPath
}
catch {
    @{ status = 'FAIL'; error = $_.Exception.Message } | ConvertTo-Json |
        Set-Content -LiteralPath $summaryPath -Encoding utf8
    throw
}
finally {
    # 只关闭本脚本打开的演示文稿，不退出可能承载其他用户文档的 PowerPoint。
    if ($null -ne $deck) { $deck.Close(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($deck) }
    $app.AutomationSecurity = $previousSecurity
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($app)
}
