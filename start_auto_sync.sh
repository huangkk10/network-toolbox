#!/bin/bash
# 啟動並測試 DHCP 日誌自動同步功能
# 使用方式: ./start_auto_sync.sh

echo "=========================================="
echo "啟動 DHCP 日誌自動同步服務"
echo "=========================================="

# 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo ""
echo -e "${YELLOW}步驟 1: 檢查 Docker 服務狀態${NC}"
echo "----------------------------------------"

# 檢查 Docker 是否運行
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}✗ Docker 未運行，請先啟動 Docker${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker 運行中${NC}"

# 檢查容器狀態
echo ""
echo "檢查容器狀態..."
docker compose ps

echo ""
echo -e "${YELLOW}步驟 2: 啟動/重啟 Celery 服務${NC}"
echo "----------------------------------------"

# 重啟 Celery 服務（應用最新代碼）
echo "重啟 Celery Worker 和 Beat..."
docker compose restart celery-worker celery-beat

# 等待服務啟動
echo "等待服務啟動..."
sleep 5

# 檢查 Celery 服務狀態
echo ""
echo "Celery 服務狀態:"
docker compose ps celery-worker celery-beat

# 檢查是否正常運行
WORKER_STATUS=$(docker compose ps celery-worker | grep "Up" | wc -l)
BEAT_STATUS=$(docker compose ps celery-beat | grep "Up" | wc -l)

if [ "$WORKER_STATUS" -eq 1 ] && [ "$BEAT_STATUS" -eq 1 ]; then
    echo -e "${GREEN}✓ Celery 服務啟動成功${NC}"
else
    echo -e "${RED}✗ Celery 服務啟動失敗，請查看日誌${NC}"
    echo ""
    echo "查看日誌命令:"
    echo "  docker compose logs celery-worker --tail 50"
    echo "  docker compose logs celery-beat --tail 50"
    exit 1
fi

echo ""
echo -e "${YELLOW}步驟 3: 查看定時任務配置${NC}"
echo "----------------------------------------"

# 顯示定時任務列表
echo "當前配置的定時任務:"
docker exec nt-celery-beat celery -A network_toolbox inspect scheduled 2>/dev/null | grep -A 5 "sync-all-dhcp-logs" || echo "（定時任務將在下次 Beat 循環時顯示）"

echo ""
echo -e "${YELLOW}步驟 4: 手動測試同步任務${NC}"
echo "----------------------------------------"

echo "手動觸發一次日誌同步任務..."
echo "（這將同步所有在線的 DHCP Server 的日誌）"
echo ""

# 創建測試腳本
cat > /tmp/test_sync.py << 'EOF'
from api.tasks import sync_all_dhcp_logs_task
import sys

print("開始執行同步任務...")
try:
    result = sync_all_dhcp_logs_task.delay(limit=500)
    print(f"✓ 任務已提交，任務 ID: {result.id}")
    print(f"  任務狀態: {result.status}")
    print("")
    print("提示：任務將在背景執行，請使用以下命令查看進度：")
    print("  docker compose logs celery-worker -f")
except Exception as e:
    print(f"✗ 任務提交失敗: {e}")
    sys.exit(1)
EOF

# 執行測試
docker exec nt-django python /tmp/test_sync.py

echo ""
echo -e "${YELLOW}步驟 5: 即時查看同步日誌${NC}"
echo "----------------------------------------"

echo "按 Ctrl+C 停止查看日誌"
echo ""
sleep 2

# 即時顯示 Celery Worker 日誌（顯示 20 秒）
timeout 20 docker compose logs celery-worker -f --tail 50 || true

echo ""
echo ""
echo "=========================================="
echo -e "${GREEN}✓ 自動同步服務已啟動！${NC}"
echo "=========================================="

echo ""
echo "📊 重要資訊:"
echo "  - 定時同步頻率: 每 10 分鐘"
echo "  - 同步範圍: 所有狀態為 'online' 的 DHCP Server"
echo "  - 每次同步數量: 每個伺服器最多 500 筆日誌"
echo ""
echo "📝 查看日誌命令:"
echo "  # 即時查看 Worker 日誌"
echo "  docker compose logs celery-worker -f"
echo ""
echo "  # 即時查看 Beat 日誌（排程器）"
echo "  docker compose logs celery-beat -f"
echo ""
echo "  # 查看 Django 應用日誌"
echo "  tail -f logs/django.log | grep Celery"
echo ""
echo "🛠️  管理命令:"
echo "  # 暫停自動同步"
echo "  docker compose stop celery-beat"
echo ""
echo "  # 恢復自動同步"
echo "  docker compose start celery-beat"
echo ""
echo "  # 重啟 Celery 服務"
echo "  docker compose restart celery-worker celery-beat"
echo ""
echo "  # 手動觸發同步（不影響定時任務）"
echo "  docker exec nt-django python manage.py shell -c 'from api.tasks import sync_all_dhcp_logs_task; sync_all_dhcp_logs_task.delay()'"
echo ""
echo "🌐 Web 監控（如果已啟動 Flower）:"
echo "  http://localhost:5555"
echo ""
echo "📚 詳細文檔:"
echo "  docs/features/AUTO_SYNC_DHCP_LOGS.md"
echo ""
echo "✨ 現在您的 DHCP 日誌將自動更新，無需手動同步！"
echo ""
