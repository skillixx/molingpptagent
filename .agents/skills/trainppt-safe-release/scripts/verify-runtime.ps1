[CmdletBinding()]
param(
    [string]$ProjectRoot = (Get-Location).Path,
    [string]$HostName = "127.0.0.1",
    [string]$TemplateId = "",
    [string]$ExpectedCommit = "",
    [string]$ExpectedChannel = "",
    [int]$TimeoutSeconds = 5
)

$ErrorActionPreference = "Stop"

function Invoke-HttpCheck {
    param([string]$Name, [string]$Uri, [int[]]$ExpectedStatus = @(200), [switch]$IncludeReleaseIdentity)
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Uri -TimeoutSec $TimeoutSeconds
        $statusCode = [int]$response.StatusCode
        $result = [ordered]@{ name = $Name; uri = $Uri; status = $statusCode; pass = $statusCode -in $ExpectedStatus; bytes = $response.RawContentLength; content_type = [string]$response.Headers['Content-Type'] }
        if ($IncludeReleaseIdentity) {
            try {
                $body = $response.Content | ConvertFrom-Json
                $result["release_commit"] = [string]$body.release_commit
                $result["release_channel"] = [string]$body.release_channel
            }
            catch {
                $result["release_commit"] = ""
                $result["release_channel"] = ""
            }
        }
        return $result
    }
    catch {
        $statusCode = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { -1 }
        return [ordered]@{ name = $Name; uri = $Uri; status = $statusCode; pass = $statusCode -in $ExpectedStatus; error = $_.Exception.Message }
    }
}

function Write-Result {
    param([object]$Payload, [int]$ExitCode)
    $Payload | ConvertTo-Json -Depth 10 -Compress
    exit $ExitCode
}

try {
    $root = (Resolve-Path -LiteralPath $ProjectRoot).Path
    if ($TemplateId -and $TemplateId -notmatch '^template_[1-9][0-9]*$') {
        throw "TemplateId 格式无效"
    }
    $ports = [ordered]@{
        FRONTEND_PORT = 5778
        MAIN_API_PORT = 6800
        OUTLINE_API_PORT = 10001
        CONTENT_API_PORT = 10011
        PERSONALDB_PORT = 9100
    }
    $envPath = Join-Path $root ".env"
    if (Test-Path -LiteralPath $envPath) {
        foreach ($line in Get-Content -LiteralPath $envPath) {
            if ($line -match '^\s*(FRONTEND_PORT|MAIN_API_PORT|OUTLINE_API_PORT|CONTENT_API_PORT|PERSONALDB_PORT)\s*=\s*(\d+)\s*$') {
                $ports[$Matches[1]] = [int]$Matches[2]
            }
            elseif (-not $ExpectedChannel -and $line -match '^\s*RELEASE_CHANNEL\s*=\s*["'']?([^"''\s#]+)') {
                $ExpectedChannel = $Matches[1]
            }
        }
    }

    $main = "http://${HostName}:$($ports.MAIN_API_PORT)"
    $frontend = "http://${HostName}:$($ports.FRONTEND_PORT)"
    $checks = @(
        Invoke-HttpCheck "frontend" "$frontend/"
        Invoke-HttpCheck "main_health" "$main/healthz" @(200) -IncludeReleaseIdentity
        Invoke-HttpCheck "main_templates" "$main/templates"
        Invoke-HttpCheck "frontend_templates_proxy" "$frontend/api/templates"
        Invoke-HttpCheck "outline_agent_card" "http://${HostName}:$($ports.OUTLINE_API_PORT)/.well-known/agent.json"
        Invoke-HttpCheck "content_agent_card" "http://${HostName}:$($ports.CONTENT_API_PORT)/.well-known/agent.json"
        Invoke-HttpCheck "personaldb_health" "http://${HostName}:$($ports.PERSONALDB_PORT)/healthz"
        Invoke-HttpCheck "auth_boundary" "$main/auth/me" @(401)
        Invoke-HttpCheck "enter_boundary" "$main/enter" @(400)
    )
    if ($TemplateId) {
        $checks += Invoke-HttpCheck "template_json" "$frontend/api/data/$TemplateId.json"
        $checks += Invoke-HttpCheck "template_cover" "$frontend/api/data/$TemplateId.jpg"
    }

    if (-not $ExpectedCommit) {
        $ExpectedCommit = (& git -C $root rev-parse HEAD 2>$null).Trim()
    }
    $mainHealth = $checks | Where-Object { $_.name -eq "main_health" } | Select-Object -First 1
    $releaseIdentity = [ordered]@{
        expected_commit = $ExpectedCommit
        expected_channel = $ExpectedChannel
        actual_commit = if ($mainHealth) { $mainHealth.release_commit } else { "" }
        actual_channel = if ($mainHealth) { $mainHealth.release_channel } else { "" }
        match = $false
    }
    $identityUnverified = @()
    if ($mainHealth -and $mainHealth.pass) {
        if (-not $mainHealth.release_commit) {
            $mainHealth["pass"] = $false
            $mainHealth["error"] = "健康响应缺少 release_commit"
        }
        elseif ($ExpectedCommit -and $mainHealth.release_commit -ne $ExpectedCommit) {
            $mainHealth["pass"] = $false
            $mainHealth["error"] = "运行提交与预期提交不一致"
        }
        elseif (-not $ExpectedChannel) {
            $identityUnverified += "release_channel_expectation"
        }
        elseif (-not $mainHealth.release_channel) {
            $mainHealth["pass"] = $false
            $mainHealth["error"] = "健康响应缺少 release_channel"
        }
        elseif ($mainHealth.release_channel -ne $ExpectedChannel) {
            $mainHealth["pass"] = $false
            $mainHealth["error"] = "运行通道与预期通道不一致"
        }
        else {
            $releaseIdentity["match"] = $true
        }
    }

    $workers = @(
        Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
            Where-Object { $_.CommandLine -match 'backend\.main_api\.workers\.main' } |
            Select-Object -ExpandProperty ProcessId
    )

    $database = [ordered]@{ status = "INCONCLUSIVE"; detail = "未执行数据库查询" }
    $python = Join-Path $root ".venv\Scripts\python.exe"
    if ((Test-Path -LiteralPath $python) -and (Test-Path -LiteralPath $envPath)) {
        $head = (& git -C $root rev-parse HEAD 2>$null).Trim()
        $escapedEnv = $envPath.Replace("'", "''")
        $code = "import os; from dotenv import load_dotenv; load_dotenv(r'$escapedEnv', override=False); " +
            "os.environ['RELEASE_COMMIT']=r'$head'; os.environ['RELEASE_CHANNEL']='production'; " +
            "from backend.main_api.core.config import load_settings; from backend.main_api.core.db import create_verified_database_engine; " +
            "s=load_settings(); " +
            "print('SKIPPED' if not s.persistence_enabled else 'PASS'); " +
            "e=None if not s.persistence_enabled else create_verified_database_engine(s.database_url.get_secret_value()); " +
            "e.dispose() if e is not None else None"
        $dbOutput = @(& $python -c $code 2>$null)
        if ($LASTEXITCODE -eq 0 -and $dbOutput[-1] -in @("PASS", "SKIPPED")) {
            $database = [ordered]@{ status = $dbOutput[-1]; detail = "只读连接检查完成" }
        }
        else {
            $database = [ordered]@{ status = "FAIL"; detail = "数据库只读连接检查失败" }
        }
    }

    $failedChecks = @($checks | Where-Object { -not $_.pass })
    $unverified = @()
    if ($workers.Count -eq 0) { $unverified += "persistent_worker" }
    if ($database.status -ne "PASS") { $unverified += "database" }
    $unverified += $identityUnverified
    $status = if ($failedChecks.Count -gt 0 -or $database.status -eq "FAIL") {
        "FAIL"
    }
    elseif ($unverified.Count -gt 0) {
        "INCONCLUSIVE"
    }
    else {
        "PASS"
    }

    Write-Result ([ordered]@{
        status = $status
        project_root = $root
        ports = $ports
        release_identity = $releaseIdentity
        checks = $checks
        database = $database
        worker_pids = $workers
        unverified = $unverified
        mutations = @()
    }) $(if ($status -eq "PASS") { 0 } elseif ($status -eq "FAIL") { 2 } else { 4 })
}
catch {
    Write-Result ([ordered]@{
        status = "INCONCLUSIVE"
        error = $_.Exception.Message
        mutations = @()
    }) 4
}
