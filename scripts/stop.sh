#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PID_FILE="$ROOT/logs/server.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "未找到 PID 文件，服务器可能未在运行。"
    exit 0
fi

PID=$(cat "$PID_FILE")

if kill -0 "$PID" 2>/dev/null; then
    echo "正在停止服务器（PID $PID）..."
    kill "$PID"
    rm -f "$PID_FILE"
    echo "服务器已停止。"
else
    echo "PID $PID 对应的进程不存在，清理 PID 文件。"
    rm -f "$PID_FILE"
fi
