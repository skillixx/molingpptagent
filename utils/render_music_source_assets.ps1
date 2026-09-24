$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$source = Join-Path $root 'doc/assets/template_29_qa/decoration-only-source.pptx'
$target = Join-Path $root 'backend/main_api/template'
$app = New-Object -ComObject PowerPoint.Application
$security = $app.AutomationSecurity
$deck = $null
try {
    # 只读打开已去除示例文字的副本，不保存原稿，也不运行原稿中的媒体。
    $app.AutomationSecurity = 3
    $deck = $app.Presentations.Open($source, -1, 0, 0)
    foreach ($entry in @(@{ slide=1; kind='cover' }, @{ slide=4; kind='content' }, @{ slide=3; kind='section' }, @{ slide=25; kind='end' })) {
        $deck.Slides.Item($entry.slide).Export((Join-Path $target "template_29_asset_bg_$($entry.kind)_v1.jpg"), 'JPG', 1920, 1080)
    }
}
finally {
    # 不退出可能承载用户其他文稿的 Office 应用。
    if ($null -ne $deck) { $deck.Close(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($deck) }
    $app.AutomationSecurity = $security
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($app)
}
