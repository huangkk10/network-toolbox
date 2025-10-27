#!/bin/bash

# 快速測試 SSH 同步功能
# 使用方式：./scripts/quick_test_ssh.sh

echo "============================================"
echo "  快速測試 SSH + PowerShell 同步"
echo "============================================"
echo ""

# 檢查容器
if ! docker compose ps | grep -q nt-django; then
    echo "✗ Django 容器未運行"
    exit 1
fi

# 執行測試
docker exec -i nt-django python /app/test_ssh_sync.py
