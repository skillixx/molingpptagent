[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectRoot,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^template_[1-9][0-9]*$')]
    [string]$TemplateId,

    [string]$RegistrationFile = 'backend/main_api/main.py',
    [string]$TemplateDir = 'backend/main_api/template',
    [string]$ExpectedName
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

function Resolve-ProjectPath {
    param([string]$Root, [string]$Value)
    if ([System.IO.Path]::IsPathRooted($Value)) {
        return [System.IO.Path]::GetFullPath($Value)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $Root $Value))
}

function Write-Result {
    param([string]$Status, [array]$Errors, [array]$Warnings, [hashtable]$Details, [int]$Code)
    [ordered]@{
        script = 'verify-template-registration'
        status = $Status
        errors = @($Errors)
        warnings = @($Warnings)
        details = $Details
    } | ConvertTo-Json -Depth 20
    exit $Code
}

try {
    $root = [System.IO.Path]::GetFullPath($ProjectRoot)
    $registrationPath = Resolve-ProjectPath -Root $root -Value $RegistrationFile
    $templatePath = Resolve-ProjectPath -Root $root -Value $TemplateDir
    $errors = [System.Collections.Generic.List[string]]::new()
    $warnings = [System.Collections.Generic.List[string]]::new()

    if (-not (Test-Path -LiteralPath $registrationPath -PathType Leaf)) {
        $errors.Add('模板注册文件不存在')
    }
    if (-not (Test-Path -LiteralPath $templatePath -PathType Container)) {
        $errors.Add('模板目录不存在')
    }
    if ($errors.Count -gt 0) {
        Write-Result -Status 'FAIL' -Errors $errors -Warnings $warnings -Details @{ template_id = $TemplateId } -Code 2
    }

    # 只解析未被整行注释的注册字典，避免把历史注释当成有效注册。
    $activeLines = [System.IO.File]::ReadAllLines($registrationPath, [System.Text.Encoding]::UTF8) |
        Where-Object { -not $_.TrimStart().StartsWith('#') }
    $matchingLines = @($activeLines | Where-Object { $_ -match "['`"]$([regex]::Escape($TemplateId))['`"]" })
    $registrations = @()
    foreach ($line in $matchingLines) {
        $nameMatch = [regex]::Match($line, "['`"]name['`"]\s*:\s*['`"](?<value>[^'`"]+)['`"]")
        $idMatch = [regex]::Match($line, "['`"]id['`"]\s*:\s*['`"](?<value>[^'`"]+)['`"]")
        $coverMatch = [regex]::Match($line, "['`"]cover['`"]\s*:\s*['`"](?<value>[^'`"]+)['`"]")
        if ($idMatch.Success -and $idMatch.Groups['value'].Value -eq $TemplateId) {
            $registrations += [ordered]@{
                name = if ($nameMatch.Success) { $nameMatch.Groups['value'].Value } else { $null }
                id = $idMatch.Groups['value'].Value
                cover = if ($coverMatch.Success) { $coverMatch.Groups['value'].Value } else { $null }
            }
        }
    }

    if ($registrations.Count -ne 1) {
        $errors.Add('目标模板必须在主 API 中唯一注册一次')
    }
    if ($registrations.Count -eq 1) {
        if ($registrations[0].cover -ne "/api/data/$TemplateId.jpg") {
            $errors.Add('模板封面注册路径不符合 /api/data/<template-id>.jpg')
        }
        if ($ExpectedName -and $registrations[0].name -ne $ExpectedName) {
            $errors.Add('模板注册名称与预期不一致')
        }
        if (-not $registrations[0].name) {
            $errors.Add('模板注册缺少可读名称')
        }
    }

    $jsonPath = Join-Path $templatePath "$TemplateId.json"
    $coverPath = Join-Path $templatePath "$TemplateId.jpg"
    if (-not (Test-Path -LiteralPath $jsonPath -PathType Leaf)) {
        $errors.Add('注册对应的模板 JSON 不存在')
    }
    if (-not (Test-Path -LiteralPath $coverPath -PathType Leaf)) {
        $errors.Add('注册对应的模板封面不存在')
    }

    $details = [ordered]@{
        template_id = $TemplateId
        registration_count = $registrations.Count
        registrations = $registrations
        json_exists = Test-Path -LiteralPath $jsonPath -PathType Leaf
        cover_exists = Test-Path -LiteralPath $coverPath -PathType Leaf
        registration_file = [System.IO.Path]::GetRelativePath($root, $registrationPath)
    }
    if ($errors.Count -gt 0) {
        Write-Result -Status 'FAIL' -Errors $errors -Warnings $warnings -Details $details -Code 2
    }
    Write-Result -Status 'PASS' -Errors @() -Warnings $warnings -Details $details -Code 0
}
catch {
    [Console]::Error.WriteLine("脚本异常：$($_.Exception.GetType().Name)")
    Write-Result -Status 'ERROR' -Errors @('脚本执行发生未知错误') -Warnings @() -Details @{ template_id = $TemplateId } -Code 1
}
