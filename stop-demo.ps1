$ErrorActionPreference = "Continue"
$Root = $PSScriptRoot
$Runtime = Join-Path $Root ".runtime"

foreach ($Port in @(3000, 8010)) {
    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}

$DockerBin = Join-Path $env:LOCALAPPDATA "Programs\DockerDesktop\resources\bin"
if (Test-Path -LiteralPath (Join-Path $DockerBin "docker.exe")) {
    $env:PATH = "$DockerBin;$env:PATH"
    docker compose --project-directory $Root stop postgres
}

Write-Host "Office Agent Demo 3 stopped." -ForegroundColor Green
