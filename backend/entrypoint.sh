#!/bin/bash
# Django 容器啟動腳本
# 1. 掛載 NAS
# 2. 使用 Supervisor 啟動所有服務（Celery Worker, Celery Beat, Django）

set -e

echo "========================================="
echo "Django 容器啟動中..."
echo "========================================="

# 執行 NAS 掛載
if [ -f "/app/mount_nas.sh" ]; then
    echo "🔗 執行 NAS 掛載..."
    bash /app/mount_nas.sh || echo "⚠️  NAS 掛載失敗，繼續啟動服務..."
else
    echo "⚠️  找不到 mount_nas.sh，跳過 NAS 掛載"
fi

echo ""
echo "🚀 使用 Supervisor 啟動所有服務..."
echo "   - Celery Worker（異步任務處理）"
echo "   - Celery Beat（定時任務調度器）"
echo "   - Django 開發伺服器"
echo ""

# 啟動 Supervisor（管理所有進程）
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
