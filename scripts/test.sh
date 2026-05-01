#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$ROOT"

mkdir -p logs

if [ ! -d ".venv" ]; then
    echo "虚拟环境不存在，正在创建..."
    uv venv
fi

echo "正在运行测试..."
uv run --with pytest python -m pytest tests/ -v 2>&1 | tee logs/test.log
echo "测试日志已保存到 logs/test.log"
