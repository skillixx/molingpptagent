$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$source = Join-Path $root 'doc/assets/template_30_qa/source-images/image32.emf'
$target = Join-Path $root 'backend/main_api/template/template_30_asset_phone_frame_v1.png'
Add-Type -AssemblyName System.Drawing
$metafile = [System.Drawing.Imaging.Metafile]::new($source)
$bitmap = [System.Drawing.Bitmap]::new(717, 1500, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
try {
    # 使用原生 GDI+ 渲染原稿矢量设备框，透明画布上不绘制任何业务照片。
    $graphics.Clear([System.Drawing.Color]::Transparent)
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $graphics.DrawImage($metafile, [System.Drawing.Rectangle]::new(0, 0, 717, 1500))
    $bitmap.Save($target, [System.Drawing.Imaging.ImageFormat]::Png)
    Get-Item -LiteralPath $target | Select-Object FullName, Length
}
finally {
    $graphics.Dispose()
    $bitmap.Dispose()
    $metafile.Dispose()
}
