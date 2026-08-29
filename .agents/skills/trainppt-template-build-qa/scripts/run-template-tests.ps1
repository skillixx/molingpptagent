[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectRoot,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^template_[1-9][0-9]*$')]
    [string]$TemplateId,

    [ValidateSet('template', 'affected', 'backend')]
    [string]$Scope = 'template',

    [string]$PythonPath,
    [switch]$PlanOnly
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

function Write-Result {
    param([string]$Status, [array]$Errors, [array]$Warnings, [hashtable]$Details, [int]$Code)
    [ordered]@{
        script = 'run-template-tests'
        status = $Status
        errors = @($Errors)
        warnings = @($Warnings)
        details = $Details
    } | ConvertTo-Json -Depth 20
    exit $Code
}

try {
    $root = [System.IO.Path]::GetFullPath($ProjectRoot)
    $testsRoot = Join-Path $root 'backend/main_api/tests'
    if (-not (Test-Path -LiteralPath $testsRoot -PathType Container)) {
        Write-Result -Status 'FAIL' -Errors @('后端测试目录不存在') -Warnings @() -Details @{ template_id = $TemplateId } -Code 2
    }

    if ($PythonPath) {
        $python = if ([System.IO.Path]::IsPathRooted($PythonPath)) {
            [System.IO.Path]::GetFullPath($PythonPath)
        } else {
            [System.IO.Path]::GetFullPath((Join-Path $root $PythonPath))
        }
    } else {
        $python = Join-Path $root '.venv/Scripts/python.exe'
    }
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        Write-Result -Status 'INCONCLUSIVE' -Errors @('项目 Python 解释器不存在') -Warnings @() -Details @{ python = $python } -Code 4
    }

    $target = Join-Path $testsRoot "test_$TemplateId.py"
    $renderer = Join-Path $testsRoot 'test_template_renderer.py'
    $assets = Join-Path $testsRoot 'test_template_assets.py'
    $paths = @()
    switch ($Scope) {
        'template' { $paths = @($target, $renderer, $assets) }
        'affected' {
            # 受影响范围使用当前仓库全部模板契约测试，避免写死历史模板编号。
            $paths = @(Get-ChildItem -LiteralPath $testsRoot -Filter 'test_template_*.py' -File |
                Sort-Object Name | ForEach-Object { $_.FullName })
        }
        'backend' { $paths = @($testsRoot) }
    }
    $missing = @($paths | Where-Object { -not (Test-Path -LiteralPath $_) })
    if ($missing.Count -gt 0 -or $paths.Count -eq 0) {
        Write-Result -Status 'FAIL' -Errors @('要求的测试文件不存在或测试集合为空') -Warnings @() -Details @{
            template_id = $TemplateId
            scope = $Scope
            missing = @($missing)
        } -Code 2
    }

    $relativePaths = @($paths | ForEach-Object { [System.IO.Path]::GetRelativePath($root, $_) })
    $details = [ordered]@{
        template_id = $TemplateId
        scope = $Scope
        python = [System.IO.Path]::GetRelativePath($root, $python)
        tests = $relativePaths
        executed = $false
    }
    if ($PlanOnly) {
        $details['note'] = '仅列出安全发现的测试；未执行 pytest'
        Write-Result -Status 'PASS' -Errors @() -Warnings @('PlanOnly 结果不能作为测试通过证据') -Details $details -Code 0
    }

    $arguments = @('-m', 'pytest', '-p', 'no:cacheprovider') + $paths + @('-q')
    $timer = [System.Diagnostics.Stopwatch]::StartNew()
    $testOutput = @(& $python @arguments 2>&1 | ForEach-Object { $_.ToString() })
    $testExitCode = $LASTEXITCODE
    $timer.Stop()
    $details['executed'] = $true
    $details['exit_code'] = $testExitCode
    $details['duration_seconds'] = [Math]::Round($timer.Elapsed.TotalSeconds, 3)
    $details['output_tail'] = @($testOutput | Select-Object -Last 80)
    if ($testExitCode -ne 0) {
        Write-Result -Status 'FAIL' -Errors @('pytest 返回非零退出码') -Warnings @() -Details $details -Code 2
    }
    Write-Result -Status 'PASS' -Errors @() -Warnings @() -Details $details -Code 0
}
catch {
    [Console]::Error.WriteLine("脚本异常：$($_.Exception.GetType().Name)")
    Write-Result -Status 'ERROR' -Errors @('脚本执行发生未知错误') -Warnings @() -Details @{ template_id = $TemplateId } -Code 1
}
