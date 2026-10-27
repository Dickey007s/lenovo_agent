#!/usr/bin/env bash
# macOS / Linux 启动脚本（仓库原脚本为 Windows .ps1/.cmd，这里补齐 Unix 侧入口）
# 用法:
#   ./scripts/start-demo-mac.sh          # 启动 API(8010) + 前端(3000)
#   ./scripts/start-demo-mac.sh stop     # 停止
#   ./scripts/start-demo-mac.sh status   # 查看状态
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
RUNTIME="$ROOT/.runtime"
mkdir -p "$RUNTIME"

API_URL="http://127.0.0.1:8010/v1/health"
WEB_URL="http://127.0.0.1:3000"

# 本机若设置了 HTTP(S)_PROXY，访问 127.0.0.1 必须绕过，否则会被代理拒绝
probe() { curl -s --noproxy '*' -o /dev/null -m 2 -w '%{http_code}' "$1" 2>/dev/null || true; }
alive() { lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1; }

stop() {
  for f in "$RUNTIME/api.pid" "$RUNTIME/web.pid"; do
    [[ -f $f ]] && kill "$(cat "$f")" 2>/dev/null || true
    rm -f "$f"
  done
  pkill -f "services.api.run" 2>/dev/null || true
  pkill -f "next dev" 2>/dev/null || true
  echo "已停止"
}

status() {
  if alive 8010; then echo "API   8010  运行中  $(probe $API_URL)"; else echo "API   8010  未运行"; fi
  if alive 3000; then echo "WEB   3000  运行中  $(probe $WEB_URL)"; else echo "WEB   3000  未运行"; fi
}

if [[ ${1:-start} == "stop" ]]; then stop; exit 0; fi
if [[ ${1:-start} == "status" ]]; then status; exit 0; fi

if [[ ! -f .env ]]; then echo "缺少 .env，请先从 .env.example 复制并填写"; exit 1; fi

echo "[1/2] 启动 FastAPI (8010)..."
if alive 8010; then
  echo "      8010 已在监听，跳过"
else
  uv run python -m services.api.run >"$RUNTIME/api.log" 2>&1 &
  echo $! >"$RUNTIME/api.pid"
  for _ in $(seq 1 30); do [[ $(probe $API_URL) == "200" ]] && break; sleep 2; done
  [[ $(probe $API_URL) == "200" ]] || { echo "API 启动超时，日志: $RUNTIME/api.log"; tail -30 "$RUNTIME/api.log"; exit 1; }
  echo "      OK"
fi

echo "[2/2] 启动 Next.js (3000)..."
if alive 3000; then
  echo "      3000 已在监听，跳过"
else
  (cd apps/web && pnpm dev) >"$RUNTIME/web.log" 2>&1 &
  echo $! >"$RUNTIME/web.pid"
  for _ in $(seq 1 30); do [[ $(probe $WEB_URL) =~ ^(200|30[0-9])$ ]] && break; sleep 2; done
  [[ $(probe $WEB_URL) =~ ^(200|30[0-9])$ ]] || { echo "前端启动超时，日志: $RUNTIME/web.log"; tail -30 "$RUNTIME/web.log"; exit 1; }
  echo "      OK"
fi

echo ""
echo "工作台:    http://localhost:3000"
echo "API 健康:  http://localhost:8010/v1/health"
echo "日志目录:  $RUNTIME"
