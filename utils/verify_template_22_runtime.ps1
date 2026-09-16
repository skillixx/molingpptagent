param(
    [string]$RepositoryRoot = ""
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($RepositoryRoot)) {
    # 默认从脚本位置解析仓库，避免换目录或 worktree 后误验其他 checkout。
    $RepositoryRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
}
$repository = (Resolve-Path -LiteralPath $RepositoryRoot).Path
$evidenceRoot = Join-Path $repository "doc\assets\template_22_qa\runtime"
$templateCover = Join-Path $repository "backend\main_api\template\template_22.jpg"
$templateJson = Join-Path $repository "backend\main_api\template\template_22.json"
New-Item -ItemType Directory -Path $evidenceRoot -Force | Out-Null

function Get-Sha256Hex([byte[]]$Bytes) {
    return [Convert]::ToHexString([System.Security.Cryptography.SHA256]::HashData($Bytes)).ToLowerInvariant()
}

function Get-HttpResult([string]$Url) {
    $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -SkipHttpErrorCheck -TimeoutSec 15
    return [ordered]@{
        url = $Url
        status = [int]$response.StatusCode
        bytes = [int]$response.RawContentLength
        body = if ($response.Headers["Content-Type"] -like "application/json*") { $response.Content } else { $null }
    }
}

$branch = (& git -C $repository branch --show-current).Trim()
$head = (& git -C $repository rev-parse HEAD).Trim()
$expectedPorts = 5778, 6800
$listeners = @(Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in $expectedPorts })
foreach ($port in $expectedPorts) {
    $matches = @($listeners | Where-Object { $_.LocalPort -eq $port })
    if ($matches.Count -ne 1) {
        throw "端口 $port 的监听进程数量不是 1：$($matches.Count)"
    }
}
$processIds = @($listeners | Select-Object -ExpandProperty OwningProcess -Unique)
$processes = @(Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -in $processIds })
$frontendProcess = $processes | Where-Object { $_.ProcessId -eq ($listeners | Where-Object LocalPort -eq 5778).OwningProcess }
$apiProcess = $processes | Where-Object { $_.ProcessId -eq ($listeners | Where-Object LocalPort -eq 6800).OwningProcess }
if ($frontendProcess.CommandLine -notlike "*$repository\frontend*") {
    throw "5778 监听进程不属于当前仓库前端"
}
$expectedApiEntry = Join-Path $repository "backend\main_api\main.py"
if ($apiProcess.CommandLine -notlike "*$expectedApiEntry*") {
    throw "6800 监听进程没有使用当前仓库的绝对主 API 入口"
}

$health = Get-HttpResult "http://127.0.0.1:6800/healthz"
$ready = Get-HttpResult "http://127.0.0.1:6800/readyz"
$templatesApi = Get-HttpResult "http://127.0.0.1:6800/templates"
$templatesProxy = Get-HttpResult "http://127.0.0.1:5778/api/templates"
if ($health.status -ne 200 -or $templatesApi.status -ne 200 -or $templatesProxy.status -ne 200) {
    throw "模板运行入口 HTTP 检查失败"
}
$templatePayload = $templatesApi.body | ConvertFrom-Json
$entries = @($templatePayload.data | Where-Object { $_.id -eq "template_22" })
if ($entries.Count -ne 1 -or $entries[0].name -ne "桃夭墨韵商务汇报") {
    throw "template_22 注册项不唯一或名称不正确"
}

$directCoverResponse = Invoke-WebRequest -Uri "http://127.0.0.1:6800/data/template_22.jpg" -UseBasicParsing -TimeoutSec 15
$proxyCoverResponse = Invoke-WebRequest -Uri "http://127.0.0.1:5778/api/data/template_22.jpg" -UseBasicParsing -TimeoutSec 15
$directJsonResponse = Invoke-WebRequest -Uri "http://127.0.0.1:6800/data/template_22.json" -UseBasicParsing -TimeoutSec 15
$proxyJsonResponse = Invoke-WebRequest -Uri "http://127.0.0.1:5778/api/data/template_22.json" -UseBasicParsing -TimeoutSec 15
$httpClient = [System.Net.Http.HttpClient]::new()
try {
    # Invoke-WebRequest 会按内容类型把 JSON 解码成字符串；哈希必须读取原始响应字节。
    $directCoverBytes = $httpClient.GetByteArrayAsync("http://127.0.0.1:6800/data/template_22.jpg").GetAwaiter().GetResult()
    $proxyCoverBytes = $httpClient.GetByteArrayAsync("http://127.0.0.1:5778/api/data/template_22.jpg").GetAwaiter().GetResult()
    $directJsonBytes = $httpClient.GetByteArrayAsync("http://127.0.0.1:6800/data/template_22.json").GetAwaiter().GetResult()
    $proxyJsonBytes = $httpClient.GetByteArrayAsync("http://127.0.0.1:5778/api/data/template_22.json").GetAwaiter().GetResult()
}
finally {
    $httpClient.Dispose()
}
$diskCoverBytes = [System.IO.File]::ReadAllBytes($templateCover)
$diskJsonBytes = [System.IO.File]::ReadAllBytes($templateJson)
$diskCoverHash = Get-Sha256Hex $diskCoverBytes
$directCoverHash = Get-Sha256Hex $directCoverBytes
$proxyCoverHash = Get-Sha256Hex $proxyCoverBytes
$diskJsonHash = Get-Sha256Hex $diskJsonBytes
$directJsonHash = Get-Sha256Hex $directJsonBytes
$proxyJsonHash = Get-Sha256Hex $proxyJsonBytes
if ($diskCoverHash -ne $directCoverHash -or $diskCoverHash -ne $proxyCoverHash) {
    throw "运行中接口返回的 template_22 封面与候选文件不一致"
}
if ($diskJsonHash -ne $directJsonHash -or $diskJsonHash -ne $proxyJsonHash) {
    throw "运行中接口返回的 template_22 JSON 与候选文件不一致"
}

$browserSummaryPath = Join-Path $evidenceRoot "runtime-summary.json"
if (-not (Test-Path -LiteralPath $browserSummaryPath)) {
    throw "缺少浏览器运行入口验收摘要"
}
$browserSummary = Get-Content -LiteralPath $browserSummaryPath -Raw | ConvertFrom-Json
if ($browserSummary.status -ne "PASS") {
    throw "浏览器运行入口验收未通过"
}

$summary = [ordered]@{
    schemaVersion = 1
    templateId = "template_22"
    status = "PASS"
    branch = $branch
    head = $head
    repositoryRoot = $repository
    listeners = @($listeners | Sort-Object LocalPort | ForEach-Object {
        $process = $processes | Where-Object ProcessId -eq $_.OwningProcess
        [ordered]@{
            address = $_.LocalAddress
            port = $_.LocalPort
            pid = $_.OwningProcess
            executable = $process.ExecutablePath
            commandLine = $process.CommandLine
        }
    })
    endpoints = [ordered]@{
        health = $health
        ready = $ready
        templatesApi = $templatesApi
        templatesProxy = $templatesProxy
        coverApiStatus = [int]$directCoverResponse.StatusCode
        coverProxyStatus = [int]$proxyCoverResponse.StatusCode
        jsonApiStatus = [int]$directJsonResponse.StatusCode
        jsonProxyStatus = [int]$proxyJsonResponse.StatusCode
    }
    templateRegistration = [ordered]@{
        count = $entries.Count
        name = $entries[0].name
        cover = $entries[0].cover
    }
    candidateCoverSha256 = $diskCoverHash
    servedCoverSha256 = $directCoverHash
    proxiedCoverSha256 = $proxyCoverHash
    candidateJsonSha256 = $diskJsonHash
    servedJsonSha256 = $directJsonHash
    proxiedJsonSha256 = $proxyJsonHash
    verifiedApiEntry = $expectedApiEntry
    controlledLaunchWorkingDirectory = $repository
    selectorUrl = "http://127.0.0.1:5778/app"
    editorUrl = "http://127.0.0.1:5778/editor"
    browserSelection = $browserSummary.templateSelected
    browserEditorEntry = $browserSummary.editorEntryVisible
    runtimeProfile = "development-validation-no-persistence-no-sso-no-billing"
    knownLimitations = @(
        "readyz 返回 503，因为本次候选验收未启动 Outline、Content 和 PersonalDB；真实 Handler/Worker 已通过固定上游和隔离 SQLite 单独验证。"
    )
}
$outputPath = Join-Path $evidenceRoot "runtime-process-summary.json"
$summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $outputPath -Encoding utf8
$summary | ConvertTo-Json -Depth 8
