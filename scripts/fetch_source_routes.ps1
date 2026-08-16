[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$RouteConfig,

    [Parameter(Mandatory = $true)]
    [string]$OutputDir,

    [ValidateRange(1, 120)]
    [int]$TimeoutSeconds = 25
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Net.Http
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12

function Resolve-RouteUrl {
    param([object]$Route)
    $offset = 0
    if ($null -ne $Route.date_offset_days) {
        $offset = [int]$Route.date_offset_days
    }
    $routeDate = (Get-Date).Date.AddDays($offset)
    return ([string]$Route.request_url_template).
        Replace("{yyyy}", $routeDate.ToString("yyyy")).
        Replace("{yyyy-MM-dd}", $routeDate.ToString("yyyy-MM-dd")).
        Replace("{MM}", $routeDate.ToString("MM")).
        Replace("{dd}", $routeDate.ToString("dd")).
        Replace("{MMdd}", $routeDate.ToString("MMdd")).
        Replace("{yyyyMMdd}", $routeDate.ToString("yyyyMMdd"))
}

$configPath = [System.IO.Path]::GetFullPath($RouteConfig)
$outputPath = [System.IO.Path]::GetFullPath($OutputDir)
$snapshotDir = Join-Path $outputPath "route-snapshots"
[System.IO.Directory]::CreateDirectory($snapshotDir) | Out-Null

$config = Get-Content -Raw -Encoding UTF8 -LiteralPath $configPath | ConvertFrom-Json
$handler = New-Object System.Net.Http.HttpClientHandler
$handler.AllowAutoRedirect = $true
$handler.AutomaticDecompression = [System.Net.DecompressionMethods]::GZip -bor [System.Net.DecompressionMethods]::Deflate
$client = New-Object System.Net.Http.HttpClient($handler)
$client.Timeout = [TimeSpan]::FromSeconds($TimeoutSeconds)
$client.DefaultRequestHeaders.UserAgent.ParseAdd("Mozilla/5.0 CodexNewsValidation/1.0")

$generatedAt = [DateTimeOffset]::Now.ToString("o")
$results = @()
try {
    foreach ($route in $config.routes) {
        $requestUrl = Resolve-RouteUrl $route
        $snapshotPath = Join-Path $snapshotDir ([string]$route.snapshot_name)
        try {
            $response = $client.GetAsync($requestUrl).GetAwaiter().GetResult()
            $bytes = $response.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult()
            [System.IO.File]::WriteAllBytes($snapshotPath, $bytes)
            $sha256 = [System.BitConverter]::ToString(
                [System.Security.Cryptography.SHA256]::Create().ComputeHash($bytes)
            ).Replace("-", "").ToLowerInvariant()
            $ready = [bool]($response.IsSuccessStatusCode -and $bytes.Length -gt 0)
            $results += [ordered]@{
                source_id = [string]$route.source_id
                route = [string]$route.route
                request_url = $requestUrl
                http_status = [int]$response.StatusCode
                content_type = if ($null -ne $response.Content.Headers.ContentType) { [string]$response.Content.Headers.ContentType } else { $null }
                bytes = [int64]$bytes.Length
                snapshot_path = [System.IO.Path]::GetFullPath($snapshotPath)
                sha256 = $sha256
                route_ready = $ready
                error = if ($ready) { $null } else { "HTTP response was not successful or body was empty" }
            }
            $response.Dispose()
        }
        catch {
            $results += [ordered]@{
                source_id = [string]$route.source_id
                route = [string]$route.route
                request_url = $requestUrl
                http_status = $null
                content_type = $null
                bytes = 0
                snapshot_path = $null
                sha256 = $null
                route_ready = $false
                error = $_.Exception.Message
            }
        }
    }
}
finally {
    $client.Dispose()
    $handler.Dispose()
}

$readyCount = @($results | Where-Object { $_.route_ready }).Count
$coverage = [ordered]@{
    schema_version = "1.0.0"
    generated_at = $generatedAt
    route_ready_count = $readyCount
    route_total_count = @($results).Count
    results = $results
}
$coveragePath = Join-Path $outputPath "source-route-coverage.json"
$coverage | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 -LiteralPath $coveragePath
$coverage | ConvertTo-Json -Depth 4 -Compress | Write-Output

if ($readyCount -ne @($results).Count) {
    exit 1
}
