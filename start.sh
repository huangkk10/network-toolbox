#!/bin/bash

# Network Toolbox 啟動腳本

echo "=========================================="
echo "  🌐 Network Toolbox 啟動中..."
echo "=========================================="

# 檢查 Docker 是否運行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker 未運行，請先啟動 Docker"
    exit 1
fi

# 建構並啟動所有服務（包含 PostgreSQL）
echo "📦 建構 Docker 映像..."
docker compose build

echo "🚀 啟動服務（包含 PostgreSQL）..."
docker compose up -d

# 等待 PostgreSQL 容器就緒
echo "⏳ 等待 PostgreSQL 啟動..."
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if docker compose exec -T postgres pg_isready -U postgres 2>/dev/null | grep -q "accepting connections"; then
        echo "✓ PostgreSQL 已就緒"
        break
    fi
    attempt=$((attempt + 1))
    echo "  等待中... ($attempt/$max_attempts)"
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo "❌ PostgreSQL 啟動超時"
    exit 1
fi

# 等待 Django 容器就緒
echo "⏳ 等待 Django 服務啟動..."
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if docker compose exec -T django python -c "import django" 2>/dev/null; then
        echo "✓ Django 服務已就緒"
        break
    fi
    attempt=$((attempt + 1))
    echo "  等待中... ($attempt/$max_attempts)"
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo "❌ Django 服務啟動超時"
    exit 1
fi

# 執行資料庫遷移
echo "🗄️  執行資料庫遷移..."
docker compose exec -T django python manage.py migrate

# 顯示服務狀態
echo ""
echo "✅ 服務啟動完成！"
echo ""
docker compose ps

echo ""
echo "=========================================="
echo "  📍 訪問網址"
echo "=========================================="
echo "🌐 主要網站: http://localhost"
echo "🔧 API 文檔: http://localhost/api/"
echo "👨‍💼 管理後台: http://localhost/admin/"
echo "📊 資料庫管理: http://localhost:9092"
echo "🐳 容器管理: http://localhost:9000 (系統已有)"
echo "=========================================="
