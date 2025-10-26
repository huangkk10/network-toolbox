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

# 建構並啟動所有服務
echo "📦 建構 Docker 映像..."
docker compose build

echo "🚀 啟動服務..."
docker compose up -d

# 等待資料庫啟動
echo "⏳ 等待資料庫啟動..."
sleep 10

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
echo "📊 資料庫管理: http://localhost:9090"
echo "🐳 容器管理: http://localhost:9000"
echo "=========================================="
