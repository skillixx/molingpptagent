$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$qa = Join-Path $root 'doc/assets/template_30_qa'
$source = Join-Path $qa 'editor-verified/neon-39-layouts.pptx'
$digest = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLower()
$output = Join-Path $qa ('native-renders/' + $digest.Substring(0,12))
New-Item -ItemType Directory -Path $output -Force | Out-Null
$summaryPath = Join-Path $qa 'native-summary.json'
@{status='RUNNING'; sourceSha256=$digest} | ConvertTo-Json | Set-Content -LiteralPath $summaryPath -Encoding utf8
$app = New-Object -ComObject PowerPoint.Application
$security = $app.AutomationSecurity
$deck = $null
function Read-ShapeTexts($shapes) {
    $texts = @()
    foreach ($shape in $shapes) {
        if ($shape.Type -eq 6) { $texts += Read-ShapeTexts $shape.GroupItems }
        elseif ($shape.HasTextFrame -eq -1 -and $shape.TextFrame.HasText -eq -1) { $texts += [string]$shape.TextFrame.TextRange.Text }
    }
    return $texts
}
try {
    # 通过本机演示软件的 PowerPoint 兼容 COM 接口只读打开候选，不操作用户原稿。
    $app.AutomationSecurity = 3
    $deck = $app.Presentations.Open($source, -1, 0, 0)
    if ($deck.Slides.Count -ne 39) { throw '候选应包含 39 个基础版式与适配变体' }
    $pages = @()
    for ($i=1; $i -le $deck.Slides.Count; $i++) {
        $slide = $deck.Slides.Item($i)
        $slide.Export((Join-Path $output ('slide-{0:D2}.png' -f $i)), 'PNG', 1600, 900)
        $pages += @{number=$i; editableTexts=@(Read-ShapeTexts $slide.Shapes); shapeCount=$slide.Shapes.Count}
    }
    $saved = Join-Path $output 'native-saved.pptx'
    $deck.SaveCopyAs($saved,24)
    @{status='PASS'; applicationName=$app.Name; applicationVersion=$app.Version; renderer='本机 PowerPoint 兼容 COM 接口';
      source=$source; sourceSha256=$digest; slides=$deck.Slides.Count; output=$output; savedCopy=$saved; pages=$pages} |
        ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryPath -Encoding utf8
    @{status='PASS'; slides=$deck.Slides.Count; output=$output} | ConvertTo-Json
}
catch {
    @{status='FAIL'; sourceSha256=$digest; error=$_.Exception.Message} | ConvertTo-Json | Set-Content -LiteralPath $summaryPath -Encoding utf8
    throw
}
finally {
    # 只关闭本脚本打开的候选，保留演示软件及其中可能存在的用户文稿。
    if ($null -ne $deck) { $deck.Close(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($deck) }
    $app.AutomationSecurity = $security
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($app)
}
