param([int]$WebPort = 3010, [int]$ApiPort = 8010, [string]$Session = 'demo12-live-20261024')
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$logs = Join-Path $root "outputs/$Session/server"
New-Item -ItemType Directory -Force -Path $logs | Out-Null
foreach ($port in @($WebPort, $ApiPort)) {
    if (Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue) {
        throw "Port $port is occupied; no existing service was changed."
    }
}
$env:STATE_STORE_MODE = 'memory'
$env:DATABASE_DSN = ''
$env:LANGGRAPH_CHECKPOINT_DSN = ''
$env:API_CORS_ORIGINS = "http://localhost:$WebPort,http://127.0.0.1:$WebPort"
$env:NEXT_PUBLIC_API_BASE_URL = "http://localhost:$ApiPort"
$env:NEXT_DIST_DIR = ".next-$Session"
# Model credentials are loaded by Settings from the existing .env, never printed.
$api = Start-Process -FilePath (Join-Path $root '.venv/Scripts/python.exe') -ArgumentList @('-m', 'uvicorn', 'services.api.app.main:app', '--host', '127.0.0.1', '--port', "$ApiPort") -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logs 'api.out.log') -RedirectStandardError (Join-Path $logs 'api.err.log') -PassThru
$web = Start-Process -FilePath (Get-Command node).Source -ArgumentList @('node_modules/next/dist/bin/next', 'dev', '--webpack', '--hostname', '127.0.0.1', '--port', "$WebPort") -WorkingDirectory (Join-Path $root 'apps/web') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logs 'web.out.log') -RedirectStandardError (Join-Path $logs 'web.err.log') -PassThru
Write-Output "API PID $($api.Id); Web PID $($web.Id); http://localhost:$WebPort; real configured provider, isolated memory session."
