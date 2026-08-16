param(
    [string]$PreferredPython = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($PreferredPython)) {
    $userProfilePath = [Environment]::GetFolderPath("UserProfile")
    $PreferredPython = Join-Path $userProfilePath ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
}

$resolvedPython = [System.IO.Path]::GetFullPath($PreferredPython)
if (-not [System.IO.File]::Exists($resolvedPython)) {
    [Console]::Error.WriteLine("bundled Python does not exist: $resolvedPython")
    exit 2
}

$probe = & $resolvedPython -c "import json, sys; from PIL import Image; print(json.dumps({'executable': sys.executable, 'pillow': Image.__version__}))" 2>&1
if ($LASTEXITCODE -ne 0) {
    [Console]::Error.WriteLine("bundled Python dependency probe failed: $probe")
    exit 3
}

$probeResult = $probe | ConvertFrom-Json
[ordered]@{
    status = "ready"
    python = $resolvedPython
    pillow = [string]$probeResult.pillow
} | ConvertTo-Json -Compress
