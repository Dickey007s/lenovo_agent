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

Write-Host "[1/4] Checking durable state backend..." -ForegroundColor Cyan
$DockerRoot = Join-Path $env:LOCALAPPDATA "Programs\DockerDesktop"
$DockerDesktop = Join-Path $DockerRoot "Docker Desktop.exe"
$DockerBin = Join-Path $DockerRoot "resources\bin"
$Docker = Join-Path $DockerBin "docker.exe"
$DockerCommand = Get-Command docker -ErrorAction SilentlyContinue
if ($DockerCommand) {
    $Docker = $DockerCommand.Source
    $DockerBin = Split-Path -Parent $Docker
} else {
    $ProgramDocker = Join-Path $env:ProgramFiles "Docker\Docker\resources\bin\docker.exe"
    if (Test-Path -LiteralPath $ProgramDocker) {
        $Docker = $ProgramDocker
        $DockerBin = Split-Path -Parent $Docker
        $DockerDesktop = Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
    }
}
$UseDockerPostgres = Test-Path -LiteralPath $Docker
$UseConfiguredPostgres = -not [string]::IsNullOrWhiteSpace($env:DATABASE_DSN)
if ($UseDockerPostgres) {
    $env:PATH = "$DockerBin;$env:PATH"
    docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        if (-not (Test-Path -LiteralPath $DockerDesktop)) {
            throw "Docker engine is unavailable and Docker Desktop was not found"
        }
        Start-Process -FilePath $DockerDesktop -WindowStyle Hidden
        $Deadline = (Get-Date).AddMinutes(2)
        do {
            Start-Sleep -Seconds 3
            docker info *> $null
        } while ($LASTEXITCODE -ne 0 -and (Get-Date) -lt $Deadline)
        if ($LASTEXITCODE -ne 0) { throw "Docker Desktop startup timeout" }
    }
} else {
    if ($UseConfiguredPostgres) {
        Write-Host "Using the configured external PostgreSQL state store." -ForegroundColor DarkGray
    } else {
        Write-Warning "Docker and DATABASE_DSN are unavailable; this session will use process-local memory and will not recover after an API restart."
    }
}

Write-Host "[2/4] Preparing state store..." -ForegroundColor Cyan
if ($UseDockerPostgres) {
    docker compose --project-directory $Root up -d postgres
    $Deadline = (Get-Date).AddMinutes(1)
    do {
        Start-Sleep -Seconds 2
        $DbHealth = docker inspect --format "{{.State.Health.Status}}" agent_v01-postgres-1 2>$null
    } while ($DbHealth -ne "healthy" -and (Get-Date) -lt $Deadline)
    if ($DbHealth -ne "healthy") { throw "PostgreSQL health check timeout" }
}

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
    $Corepack = Get-Command corepack -ErrorAction SilentlyContinue
    $Pnpm = Get-Command pnpm -ErrorAction SilentlyContinue
    if ($Corepack) {
        $WebCommand = $Corepack.Source
        $WebArguments = @("pnpm", "--dir", "apps/web", "dev")
    } elseif ($Pnpm) {
        $WebCommand = $Pnpm.Source
        $WebArguments = @("--dir", "apps/web", "dev")
    } else {
        throw "Neither corepack nor pnpm is available"
    }
    $WebOut = Join-Path $Runtime "web.stdout.log"
    $WebErr = Join-Path $Runtime "web.stderr.log"
    $Web = Start-Process -FilePath $WebCommand `
        -ArgumentList $WebArguments `
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
Write-Host "Office Agent is ready: http://localhost:3000" -ForegroundColor Green
Write-Host "API health:       http://localhost:8010/v1/health" -ForegroundColor Green
Write-Host "Logs:             $Runtime" -ForegroundColor DarkGray
