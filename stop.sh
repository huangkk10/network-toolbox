#!/bin/bash

# Network Toolbox 停止腳本

echo "=========================================="
echo "  🛑 Network Toolbox 停止中..."
echo "=========================================="

docker compose down

echo "✅ 所有服務已停止"
