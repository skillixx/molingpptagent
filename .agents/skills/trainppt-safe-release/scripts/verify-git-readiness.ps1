[CmdletBinding()]
param(
    [string]$ProjectRoot = (Get-Location).Path,
    [string]$BaseRef = "origin/main",
    [string]$FeatureRef = "HEAD",
    [string]$TestEvidencePath = "",
    [switch]$AllowMissingTestEvidence,
    [switch]$AllowDirty
)

$ErrorActionPreference = "Stop"

function Write-Result {
    param([object]$Payload, [int]$ExitCode)
    $Payload | ConvertTo-Json -Depth 8 -Compress
    exit $ExitCode
}

function Test-SecretLine {
    param([string]$Value, [string]$SecretPattern, [string]$PlaceholderPattern)
    foreach ($match in [regex]::Matches($Value, $SecretPattern)) {
        # 只豁免具体命中的示例值，不能因同一行其他位置出现 example 而跳过真实秘密。
        if ($match.Value -notmatch $PlaceholderPattern) { return $true }
    }
    return $false
}

try {
    $root = (Resolve-Path -LiteralPath $ProjectRoot).Path
    & git -C $root rev-parse --is-inside-work-tree 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "目标目录不是 Git 工作区" }

    $baseSha = (& git -C $root rev-parse $BaseRef 2>$null).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $baseSha) { throw "无法解析基线引用 $BaseRef" }
    $featureSha = (& git -C $root rev-parse $FeatureRef 2>$null).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $featureSha) { throw "无法解析功能引用 $FeatureRef" }

    & git -C $root merge-base --is-ancestor $BaseRef $FeatureRef 2>$null
    $baseIsAncestor = $LASTEXITCODE -eq 0

    $counts = (& git -C $root rev-list --left-right --count "$BaseRef...$FeatureRef" 2>$null) -split '\s+'
    $behind = if ($counts.Count -ge 1) { [int]$counts[0] } else { -1 }
    $ahead = if ($counts.Count -ge 2) { [int]$counts[1] } else { -1 }
    $worktree = @(& git -C $root status --short)
    $currentBranch = (& git -C $root branch --show-current 2>$null).Trim()

    $testEvidence = $null
    if ($TestEvidencePath) {
        $candidate = if ([System.IO.Path]::IsPathRooted($TestEvidencePath)) { $TestEvidencePath } else { Join-Path $root $TestEvidencePath }
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            $evidenceFile = Get-Item -LiteralPath $candidate
            $testEvidence = [ordered]@{
                path = $evidenceFile.FullName
                modified_at = $evidenceFile.LastWriteTimeUtc.ToString("o")
                sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $evidenceFile.FullName).Hash.ToLowerInvariant()
            }
        }
        else {
            $testEvidence = [ordered]@{ path = $candidate; missing = $true }
        }
    }

    $mergeBase = (& git -C $root merge-base $BaseRef $FeatureRef 2>$null).Trim()
    $mergePreview = @(& git -C $root merge-tree $mergeBase $BaseRef $FeatureRef 2>$null)
    $hasConflict = [bool]($mergePreview -match '^<<<<<<< ')

    $secretPatterns = '(?i)(bearer\s+[A-Za-z0-9._-]{12,}|sk-[A-Za-z0-9]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN .*PRIVATE KEY-----|[a-z][a-z0-9+.-]*://[^:/\s]+:[^@/\s]+@|\b(?:password|passwd|secret|token|authorization|cookie|database_url|db_url)\b\s*[:=]\s*["'']?[^<\s"'']{8,})'
    $placeholderPatterns = '(?i)(<redacted>|example|placeholder|dummy|abcdefghijklmnopqrstuvwxyz|SENSITIVE_VALUE_RE|secretPatterns\s*=|\.\*)'
    # 同时扫描分支差异、暂存区、未暂存区和未跟踪文本，避免新凭据绕过分支 diff。
    $diffLines = @(& git -C $root diff "$BaseRef...$FeatureRef" --unified=0 --no-color)
    $diffLines += @(& git -C $root diff --cached --unified=0 --no-color)
    $diffLines += @(& git -C $root diff --unified=0 --no-color)
    $secretHits = @(
        $diffLines |
            Where-Object { $_ -match '^\+' -and $_ -notmatch '^\+\+\+' -and (Test-SecretLine $_ $secretPatterns $placeholderPatterns) } |
            Select-Object -First 20
    )
    $untrackedSecretCount = 0
    foreach ($relativePath in @(& git -C $root ls-files --others --exclude-standard)) {
        $candidate = Join-Path $root $relativePath
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
        $file = Get-Item -LiteralPath $candidate -ErrorAction SilentlyContinue
        if ($null -eq $file) { continue }
        if ($file.Length -gt 2MB) { continue }
        try {
            $bytes = [System.IO.File]::ReadAllBytes($candidate)
            if ($bytes -contains 0) { continue }
            $strictUtf8 = [System.Text.UTF8Encoding]::new($false, $true)
            $text = $strictUtf8.GetString($bytes)
            foreach ($line in $text -split "`r?`n") {
                if (Test-SecretLine $line $secretPatterns $placeholderPatterns) {
                    $untrackedSecretCount += 1
                    break
                }
            }
        }
        catch {
            # 无法安全读取的候选文本不应被静默认定为干净。
            $untrackedSecretCount += 1
        }
    }
    $credentialFindingCount = $secretHits.Count + $untrackedSecretCount

    $blocking = @()
    if (-not $baseIsAncestor) { $blocking += "base_not_ancestor" }
    if ($hasConflict) { $blocking += "merge_conflict" }
    if ($credentialFindingCount -gt 0) { $blocking += "credential_pattern" }
    if (-not $AllowMissingTestEvidence -and ($null -eq $testEvidence -or $testEvidence.missing -eq $true)) {
        $blocking += "missing_test_evidence"
    }
    if (-not $AllowDirty -and $worktree.Count -gt 0) { $blocking += "dirty_worktree" }

    $status = if ($blocking.Count -eq 0) { "PASS" } else { "FAIL" }
    Write-Result ([ordered]@{
        status = $status
        project_root = $root
        current_branch = $currentBranch
        base_ref = $BaseRef
        base_sha = $baseSha
        feature_ref = $FeatureRef
        feature_sha = $featureSha
        base_is_ancestor = $baseIsAncestor
        ahead = $ahead
        behind = $behind
        merge_conflict = $hasConflict
        worktree = $worktree
        test_evidence = $testEvidence
        credential_finding_count = $credentialFindingCount
        blocking = $blocking
        mutations = @()
    }) $(if ($status -eq "PASS") { 0 } else { 2 })
}
catch {
    Write-Result ([ordered]@{
        status = "INCONCLUSIVE"
        error = $_.Exception.Message
        mutations = @()
    }) 4
}
