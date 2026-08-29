[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^https?://')]
    [string]$BaseUrl,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^template_[1-9][0-9]*$')]
    [string]$TemplateId,

    [string]$ExpectedName,
    [ValidatePattern('^https?://')]
    [string]$FrontendBaseUrl,
    [ValidateRange(1, 120)]
    [int]$TimeoutSeconds = 15
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

function Write-Result {
    param([string]$Status, [array]$Errors, [array]$Warnings, [hashtable]$Details, [int]$Code)
    [ordered]@{
        script = 'verify-template-api'
        status = $Status
        errors = @($Errors)
        warnings = @($Warnings)
        details = $Details
    } | ConvertTo-Json -Depth 30
    exit $Code
}

function Assert-SafeBaseUri {
    param([string]$Value)
    $uri = [Uri]$Value
    if ($uri.Scheme -notin @('http', 'https') -or $uri.UserInfo -or $uri.Query -or $uri.Fragment) {
        throw [System.ArgumentException]::new('Base URL 不能包含凭据、查询或片段')
    }
    return $Value.TrimEnd('/')
}

function Invoke-ReadOnlyGet {
    param([System.Net.Http.HttpClient]$Client, [string]$Url)
    $response = $Client.GetAsync($Url).GetAwaiter().GetResult()
    $bytes = $response.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult()
    return [ordered]@{
        status = [int]$response.StatusCode
        content_type = if ($response.Content.Headers.ContentType) { $response.Content.Headers.ContentType.MediaType } else { $null }
        bytes = $bytes.Length
        body = $bytes
    }
}

try {
    Add-Type -AssemblyName System.Net.Http
    $apiBase = Assert-SafeBaseUri -Value $BaseUrl
    $frontendBase = if ($FrontendBaseUrl) { Assert-SafeBaseUri -Value $FrontendBaseUrl } else { $null }
    $client = [System.Net.Http.HttpClient]::new()
    $client.Timeout = [TimeSpan]::FromSeconds($TimeoutSeconds)
    try {
        $errors = [System.Collections.Generic.List[string]]::new()
        $warnings = [System.Collections.Generic.List[string]]::new()
        $details = [ordered]@{ template_id = $TemplateId; main_api = [ordered]@{} }

        $templatesResponse = Invoke-ReadOnlyGet -Client $client -Url "$apiBase/templates"
        $details.main_api['templates'] = [ordered]@{
            status = $templatesResponse.status
            content_type = $templatesResponse.content_type
            bytes = $templatesResponse.bytes
        }
        if ($templatesResponse.status -ne 200) {
            $errors.Add('主 API 模板列表未返回 200')
            $items = @()
        } else {
            try {
                $payload = [System.Text.Encoding]::UTF8.GetString($templatesResponse.body) | ConvertFrom-Json
                $items = @($payload.data)
            } catch {
                $errors.Add('主 API 模板列表不是有效 JSON')
                $items = @()
            }
        }
        $targets = @($items | Where-Object { $_.id -eq $TemplateId })
        $uniqueIds = @($items | ForEach-Object { $_.id } | Sort-Object -Unique)
        $details.main_api['target_count'] = $targets.Count
        $details.main_api['all_ids_unique'] = ($uniqueIds.Count -eq $items.Count)
        if ($targets.Count -ne 1) { $errors.Add('主 API 模板列表中目标模板不是唯一一项') }
        if ($uniqueIds.Count -ne $items.Count) { $errors.Add('主 API 模板列表存在重复 ID') }
        if ($ExpectedName -and $targets.Count -eq 1 -and $targets[0].name -ne $ExpectedName) {
            $errors.Add('主 API 模板名称与预期不一致')
        }

        $jsonResponse = Invoke-ReadOnlyGet -Client $client -Url "$apiBase/data/$TemplateId.json"
        $details.main_api['json'] = [ordered]@{
            status = $jsonResponse.status
            content_type = $jsonResponse.content_type
            bytes = $jsonResponse.bytes
        }
        $template = $null
        if ($jsonResponse.status -ne 200) {
            $errors.Add('模板 JSON 未返回 200')
        } else {
            try {
                $template = [System.Text.Encoding]::UTF8.GetString($jsonResponse.body) | ConvertFrom-Json
                if ($template.id -ne $TemplateId) { $errors.Add('运行时模板 JSON 的 id 不一致') }
            } catch {
                $errors.Add('运行时模板 JSON 无法解析')
            }
        }

        $coverResponse = Invoke-ReadOnlyGet -Client $client -Url "$apiBase/data/$TemplateId.jpg"
        $details.main_api['cover'] = [ordered]@{
            status = $coverResponse.status
            content_type = $coverResponse.content_type
            bytes = $coverResponse.bytes
        }
        if ($coverResponse.status -ne 200 -or $coverResponse.content_type -notlike 'image/*' -or $coverResponse.bytes -le 0) {
            $errors.Add('模板封面响应无效')
        }

        $assetNames = @()
        if ($template) {
            $assetNames = @($template.slides | ForEach-Object { $_.elements } |
                Where-Object { $_.type -eq 'image' -and $_.src -like '/api/data/*' } |
                ForEach-Object { [System.IO.Path]::GetFileName($_.src) } | Sort-Object -Unique)
        }
        $assetResults = @()
        foreach ($assetName in $assetNames) {
            if ($assetName -notlike "$TemplateId`_asset_*") {
                $errors.Add('运行时模板引用了其他模板命名空间')
                continue
            }
            $assetResponse = Invoke-ReadOnlyGet -Client $client -Url "$apiBase/data/$assetName"
            $assetResults += [ordered]@{
                filename = $assetName
                status = $assetResponse.status
                content_type = $assetResponse.content_type
                bytes = $assetResponse.bytes
            }
            if ($assetResponse.status -ne 200 -or $assetResponse.content_type -notlike 'image/*' -or $assetResponse.bytes -le 0) {
                $errors.Add("外置素材不可访问：$assetName")
            }
        }
        $details.main_api['assets'] = $assetResults

        if ($frontendBase) {
            $details['frontend_proxy'] = [ordered]@{}
            $proxyTemplates = Invoke-ReadOnlyGet -Client $client -Url "$frontendBase/api/templates"
            $details.frontend_proxy['templates'] = [ordered]@{ status = $proxyTemplates.status; bytes = $proxyTemplates.bytes }
            if ($proxyTemplates.status -ne 200) {
                $errors.Add('前端模板代理未返回 200')
            } else {
                try {
                    $proxyPayload = [System.Text.Encoding]::UTF8.GetString($proxyTemplates.body) | ConvertFrom-Json
                    $proxyTargets = @($proxyPayload.data | Where-Object { $_.id -eq $TemplateId })
                    $details.frontend_proxy['target_count'] = $proxyTargets.Count
                    if ($proxyTargets.Count -ne 1) { $errors.Add('前端模板代理中目标模板不是唯一一项') }
                } catch {
                    $errors.Add('前端模板代理响应不是有效 JSON')
                }
            }
            foreach ($filename in @("$TemplateId.json", "$TemplateId.jpg") + $assetNames) {
                $proxyResource = Invoke-ReadOnlyGet -Client $client -Url "$frontendBase/api/data/$filename"
                if ($proxyResource.status -ne 200 -or $proxyResource.bytes -le 0) {
                    $errors.Add("前端资源代理不可访问：$filename")
                }
            }
            $details.frontend_proxy['resources_checked'] = 2 + $assetNames.Count
        }

        if ($errors.Count -gt 0) {
            Write-Result -Status 'FAIL' -Errors $errors -Warnings $warnings -Details $details -Code 2
        }
        Write-Result -Status 'PASS' -Errors @() -Warnings $warnings -Details $details -Code 0
    }
    finally {
        $client.Dispose()
    }
}
catch [System.ArgumentException] {
    Write-Result -Status 'BLOCKED' -Errors @($_.Exception.Message) -Warnings @() -Details @{ template_id = $TemplateId } -Code 3
}
catch [System.Net.Http.HttpRequestException] {
    [Console]::Error.WriteLine('API 连接不可用')
    Write-Result -Status 'INCONCLUSIVE' -Errors @('API 或代理不可连接') -Warnings @() -Details @{ template_id = $TemplateId } -Code 4
}
catch [System.Threading.Tasks.TaskCanceledException] {
    [Console]::Error.WriteLine('API 请求超时')
    Write-Result -Status 'INCONCLUSIVE' -Errors @('API 或代理请求超时') -Warnings @() -Details @{ template_id = $TemplateId } -Code 4
}
catch {
    [Console]::Error.WriteLine("脚本异常：$($_.Exception.GetType().Name)")
    Write-Result -Status 'ERROR' -Errors @('脚本执行发生未知错误') -Warnings @() -Details @{ template_id = $TemplateId } -Code 1
}
