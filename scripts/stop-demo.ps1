$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
$Runtime = Join-Path $Root ".runtime"

foreach ($Port in @(3000, 8010)) {
    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}

$DockerCommand = Get-Command docker -ErrorAction SilentlyContinue
$Docker = if ($DockerCommand) {
    $DockerCommand.Source
} else {
    @(
        (Join-Path $env:LOCALAPPDATA "Programs\DockerDesktop\resources\bin\docker.exe"),
        (Join-Path $env:ProgramFiles "Docker\Docker\resources\bin\docker.exe")
    ) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if ($Docker) {
    & $Docker compose --project-directory $Root stop postgres
}

Write-Host "Office Agent stopped." -ForegroundColor Green
