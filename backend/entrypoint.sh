#!/bin/bash
# Django 容器啟動腳本
# 1. 掛載 NAS
# 2. 啟動 Django 開發伺服器

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
echo "🚀 啟動 Django 開發伺服器..."
exec python manage.py runserver 0.0.0.0:8000
