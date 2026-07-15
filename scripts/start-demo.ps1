$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Runtime = Join-Path $Root ".runtime"
New-Item -ItemType Directory -Force -Path $Runtime | Out-Null

function Test-Http([string]$Url) {
    try {
        Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2 | Out-Null
        return $true
    } catch {
        return $false
    }
}

Write-Host "[1/4] Starting Docker Desktop..." -ForegroundColor Cyan
$DockerRoot = Join-Path $env:LOCALAPPDATA "Programs\DockerDesktop"
$DockerDesktop = Join-Path $DockerRoot "Docker Desktop.exe"
$DockerBin = Join-Path $DockerRoot "resources\bin"
$Docker = Join-Path $DockerBin "docker.exe"
if (-not (Test-Path -LiteralPath $Docker)) {
    throw "Docker CLI not found: $Docker"
}
$env:PATH = "$DockerBin;$env:PATH"
docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Start-Process -FilePath $DockerDesktop -WindowStyle Hidden
    $Deadline = (Get-Date).AddMinutes(2)
    do {
        Start-Sleep -Seconds 3
        docker info *> $null
    } while ($LASTEXITCODE -ne 0 -and (Get-Date) -lt $Deadline)
    if ($LASTEXITCODE -ne 0) { throw "Docker Desktop startup timeout" }
}

Write-Host "[2/4] Starting PostgreSQL..." -ForegroundColor Cyan
docker compose --project-directory $Root up -d postgres
$Deadline = (Get-Date).AddMinutes(1)
do {
    Start-Sleep -Seconds 2
    $DbHealth = docker inspect --format "{{.State.Health.Status}}" agent_v01-postgres-1 2>$null
} while ($DbHealth -ne "healthy" -and (Get-Date) -lt $Deadline)
if ($DbHealth -ne "healthy") { throw "PostgreSQL health check timeout" }

Write-Host "[3/4] Starting FastAPI on 8010..." -ForegroundColor Cyan
if (-not (Test-Http "http://127.0.0.1:8010/v1/health")) {
    $Uv = (Get-Command uv -ErrorAction Stop).Source
    $ApiOut = Join-Path $Runtime "api.stdout.log"
    $ApiErr = Join-Path $Runtime "api.stderr.log"
    $Api = Start-Process -FilePath $Uv `
        -ArgumentList @("run", "python", "-m", "services.api.run") `
        -WorkingDirectory $Root -WindowStyle Hidden `
        -RedirectStandardOutput $ApiOut -RedirectStandardError $ApiErr -PassThru
    Set-Content -LiteralPath (Join-Path $Runtime "api.pid") -Value $Api.Id
    $Deadline = (Get-Date).AddSeconds(45)
    do { Start-Sleep -Seconds 2 } while (
        -not (Test-Http "http://127.0.0.1:8010/v1/health") -and (Get-Date) -lt $Deadline
    )
    if (-not (Test-Http "http://127.0.0.1:8010/v1/health")) {
        Get-Content -LiteralPath $ApiErr -Tail 80
        throw "FastAPI startup timeout"
    }
}

Write-Host "[4/4] Starting Next.js on 3000..." -ForegroundColor Cyan
if (-not (Test-Http "http://127.0.0.1:3000")) {
    $Corepack = Join-Path $env:ProgramFiles "nodejs\corepack.cmd"
    $WebOut = Join-Path $Runtime "web.stdout.log"
    $WebErr = Join-Path $Runtime "web.stderr.log"
    $Web = Start-Process -FilePath $Corepack `
        -ArgumentList @("pnpm", "--dir", "apps/web", "dev") `
        -WorkingDirectory $Root -WindowStyle Hidden `
        -RedirectStandardOutput $WebOut -RedirectStandardError $WebErr -PassThru
    Set-Content -LiteralPath (Join-Path $Runtime "web.pid") -Value $Web.Id
    $Deadline = (Get-Date).AddSeconds(45)
    do { Start-Sleep -Seconds 2 } while (
        -not (Test-Http "http://127.0.0.1:3000") -and (Get-Date) -lt $Deadline
    )
    if (-not (Test-Http "http://127.0.0.1:3000")) {
        Get-Content -LiteralPath $WebErr -Tail 80
        throw "Next.js startup timeout"
    }
}

Write-Host ""
Write-Host "Demo 3 is ready: http://localhost:3000" -ForegroundColor Green
Write-Host "API health:       http://localhost:8010/v1/health" -ForegroundColor Green
Write-Host "Logs:             $Runtime" -ForegroundColor DarkGray
