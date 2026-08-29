[CmdletBinding()]
param(
    [string]$ProjectRoot = (Get-Location).Path,
    [int[]]$Ports = @(),
    [int]$HealthTimeoutSeconds = 2
)

$ErrorActionPreference = "Stop"

function Write-Result {
    param([object]$Payload, [int]$ExitCode)
    $Payload | ConvertTo-Json -Depth 8 -Compress
    exit $ExitCode
}

function Protect-CommandLine {
    param([string]$Value)
    if (-not $Value) { return $Value }
    $keyNames = 'token|password|passwd|secret|api[_-]?key|database[_-]?url|db[_-]?url|cookie|authorization'
    $protected = $Value -replace "(?i)(--(?:$keyNames)\s+)(\S+)", '$1<redacted>'
    $protected = $protected -replace "(?i)((?:$keyNames)=)([^\s&]+)", '$1<redacted>'
    $protected = $protected -replace '(?i)(authorization\s*:\s*bearer\s+)(\S+)', '$1<redacted>'
    $protected = $protected -replace '(?i)(bearer\s+)([A-Za-z0-9._-]{8,})', '$1<redacted>'
    $protected = $protected -replace '(?i)([a-z][a-z0-9+.-]*://[^:/\s]+:)([^@/\s]+)(@)', '$1<redacted>$3'
    return $protected
}

function Get-HealthSummary {
    param([string]$Name, [string]$Uri)
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Uri -TimeoutSec $HealthTimeoutSeconds
        return [ordered]@{ name = $Name; uri = $Uri; status = [int]$response.StatusCode; reachable = $true }
    }
    catch {
        $statusCode = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { -1 }
        return [ordered]@{ name = $Name; uri = $Uri; status = $statusCode; reachable = $false }
    }
}

try {
    $root = (Resolve-Path -LiteralPath $ProjectRoot).Path
    if (-not (Test-Path -LiteralPath (Join-Path $root ".git"))) {
        throw "目标目录不是 Git 工作区"
    }

    # 只读取公开端口键，禁止把 .env 其他配置带入输出。
    if ($Ports.Count -eq 0) {
        $portConfig = [ordered]@{
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
                    $portConfig[$Matches[1]] = [int]$Matches[2]
                }
            }
        }
        $Ports = @($portConfig.Values) + @(13306, 19000, 19001)
    }
    else {
        $portConfig = [ordered]@{
            FRONTEND_PORT = if (5778 -in $Ports) { 5778 } else { $null }
            MAIN_API_PORT = if (6800 -in $Ports) { 6800 } else { $null }
            OUTLINE_API_PORT = if (10001 -in $Ports) { 10001 } else { $null }
            CONTENT_API_PORT = if (10011 -in $Ports) { 10011 } else { $null }
            PERSONALDB_PORT = if (9100 -in $Ports) { 9100 } else { $null }
        }
    }

    $listeners = @()
    if (Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue) {
        foreach ($listener in Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue) {
            if ($listener.LocalPort -notin $Ports) { continue }
            $process = Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)" -ErrorAction SilentlyContinue
            $listeners += [ordered]@{
                address = $listener.LocalAddress
                port = $listener.LocalPort
                pid = $listener.OwningProcess
                parent_pid = $process.ParentProcessId
                name = $process.Name
                executable = $process.ExecutablePath
                command_line = Protect-CommandLine $process.CommandLine
                created_at = if ($process.CreationDate) { $process.CreationDate.ToString("o") } else { $null }
            }
        }
    }

    $workerProcesses = @(
        Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
            Where-Object { $_.CommandLine -match 'backend\.main_api\.workers\.main' } |
            ForEach-Object {
                [ordered]@{
                    pid = $_.ProcessId
                    parent_pid = $_.ParentProcessId
                    name = $_.Name
                    command_line = Protect-CommandLine $_.CommandLine
                    created_at = if ($_.CreationDate) { $_.CreationDate.ToString("o") } else { $null }
                }
            }
    )

    $docker = [ordered]@{ available = $false; containers = @() }
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        $docker.available = $true
        $docker.containers = @(
            & docker ps --format '{{.ID}}|{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}' 2>$null |
                ForEach-Object {
                    $parts = $_ -split '\|', 5
                    [ordered]@{
                        id = $parts[0]
                        name = $parts[1]
                        image = $parts[2]
                        status = $parts[3]
                        ports = $parts[4]
                    }
                }
        )
    }

    $head = (& git -C $root rev-parse HEAD 2>$null).Trim()
    $health = @()
    if ($portConfig.FRONTEND_PORT) { $health += Get-HealthSummary "frontend" "http://127.0.0.1:$($portConfig.FRONTEND_PORT)/" }
    if ($portConfig.MAIN_API_PORT) { $health += Get-HealthSummary "main_api" "http://127.0.0.1:$($portConfig.MAIN_API_PORT)/healthz" }
    if ($portConfig.OUTLINE_API_PORT) { $health += Get-HealthSummary "outline" "http://127.0.0.1:$($portConfig.OUTLINE_API_PORT)/.well-known/agent.json" }
    if ($portConfig.CONTENT_API_PORT) { $health += Get-HealthSummary "content" "http://127.0.0.1:$($portConfig.CONTENT_API_PORT)/.well-known/agent.json" }
    if ($portConfig.PERSONALDB_PORT) { $health += Get-HealthSummary "personaldb" "http://127.0.0.1:$($portConfig.PERSONALDB_PORT)/healthz" }
    Write-Result ([ordered]@{
        status = "PASS"
        project_root = $root
        git_head = $head
        candidate_ports = @($Ports | Sort-Object -Unique)
        listeners = @($listeners | Sort-Object port, pid)
        health = $health
        worker_processes = $workerProcesses
        docker = $docker
        mutations = @()
    }) 0
}
catch {
    Write-Result ([ordered]@{
        status = "INCONCLUSIVE"
        error = $_.Exception.Message
        mutations = @()
    }) 4
}
