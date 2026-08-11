[CmdletBinding()]
param(
    [string]$AdminDsn = $env:OFFICE_AGENT_POSTGRES_ADMIN_DSN
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($AdminDsn)) {
    throw "Set OFFICE_AGENT_POSTGRES_ADMIN_DSN to a PostgreSQL 16 maintenance database DSN."
}

$Root = Split-Path -Parent $PSScriptRoot
$PreviousDsn = $env:OFFICE_AGENT_POSTGRES_ADMIN_DSN
$HadPreviousDsn = Test-Path Env:OFFICE_AGENT_POSTGRES_ADMIN_DSN
$LocationPushed = $false

try {
    $env:OFFICE_AGENT_POSTGRES_ADMIN_DSN = $AdminDsn
    $Uv = (Get-Command uv -ErrorAction Stop).Source
    Push-Location $Root
    $LocationPushed = $true
    & $Uv run pytest -q tests/system/test_postgres_api_restart.py -s
    if ($LASTEXITCODE -ne 0) {
        throw "PostgreSQL API restart verification failed with exit code $LASTEXITCODE."
    }
} finally {
    if ($LocationPushed) {
        Pop-Location
    }
    if ($HadPreviousDsn) {
        $env:OFFICE_AGENT_POSTGRES_ADMIN_DSN = $PreviousDsn
    } else {
        Remove-Item Env:OFFICE_AGENT_POSTGRES_ADMIN_DSN -ErrorAction SilentlyContinue
    }
}
