#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PID_FILE="$ROOT/logs/server.pid"

cd "$ROOT"

mkdir -p logs

if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "服务器已在运行（PID $OLD_PID）。如需重启请先执行 scripts/stop.sh"
        exit 1
    else
        rm -f "$PID_FILE"
    fi
fi

if [ ! -d ".venv" ]; then
    echo "虚拟环境不存在，正在创建..."
    uv venv
fi

echo "正在启动 Lab MVP 服务器..."
uv run python app.py &
SERVER_PID=$!
echo "$SERVER_PID" > "$PID_FILE"
echo "服务器已启动（PID $SERVER_PID），日志输出到 logs/server.log"
echo "访问地址：http://127.0.0.1:8765"
