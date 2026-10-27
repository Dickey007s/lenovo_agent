$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$logs = Join-Path $root 'outputs/demo3-examples-20261026/preview'
New-Item -ItemType Directory -Force -Path $logs | Out-Null
foreach ($port in @(3028, 8028)) {
    if (Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue) {
        throw "Port $port is already occupied. Existing services were not changed."
    }
}
$env:STATE_STORE_MODE = 'memory'
$env:LLM_API_KEY = 'preview-disabled'
$env:LLM_BASE_URL = 'http://127.0.0.1:9'
$env:API_CORS_ORIGINS = 'http://localhost:3028'
$env:NEXT_PUBLIC_API_BASE_URL = 'http://localhost:8028'
$env:NEXT_DIST_DIR = '.next-demo3-examples'
$api = Start-Process -FilePath (Join-Path $root '.venv/Scripts/python.exe') -ArgumentList @('-m', 'uvicorn', 'services.api.app.main:app', '--host', '127.0.0.1', '--port', '8028') -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logs 'api.out.log') -RedirectStandardError (Join-Path $logs 'api.err.log') -PassThru
$web = Start-Process -FilePath (Get-Command node).Source -ArgumentList @('node_modules/next/dist/bin/next', 'dev', '--webpack', '--hostname', '127.0.0.1', '--port', '3028') -WorkingDirectory (Join-Path $root 'apps/web') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logs 'web.out.log') -RedirectStandardError (Join-Path $logs 'web.err.log') -PassThru
Write-Output "API PID: $($api.Id); Web PID: $($web.Id); http://localhost:3028; Demo3 fixed rules, memory-only, models disabled."
