#!/bin/bash

# =============================================================================
# DHCP 租約自動同步 - 啟動與測試腳本
# =============================================================================
# 功能：
#   1. 檢查 Docker 服務狀態
#   2. 重啟 celery-worker 和 celery-beat
#   3. 顯示定時任務配置
#   4. 手動觸發一次測試同步
#   5. 顯示即時日誌（20 秒）
# =============================================================================

# 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 專案根目錄
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  DHCP 租約自動同步 - 啟動與測試${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# =============================================================================
# 步驟 1：檢查 Docker 服務
# =============================================================================
echo -e "${YELLOW}[步驟 1/5]${NC} 檢查 Docker 服務狀態..."

if ! docker compose ps &> /dev/null; then
    echo -e "${RED}❌ Docker 服務未運行或 docker-compose.yml 有誤${NC}"
    exit 1
fi

# 檢查關鍵容器
REQUIRED_SERVICES=("celery-worker" "celery-beat" "django" "redis")
MISSING_SERVICES=()

for service in "${REQUIRED_SERVICES[@]}"; do
    if ! docker compose ps "$service" 2>/dev/null | grep -q "Up"; then
        MISSING_SERVICES+=("$service")
    fi
done

if [ ${#MISSING_SERVICES[@]} -ne 0 ]; then
    echo -e "${RED}❌ 以下服務未運行：${MISSING_SERVICES[*]}${NC}"
    echo -e "${YELLOW}   正在啟動服務...${NC}"
    docker compose up -d "${MISSING_SERVICES[@]}"
    sleep 3
fi

echo -e "${GREEN}✅ Docker 服務正常運行${NC}"
echo ""

# =============================================================================
# 步驟 2：重啟 Celery 服務
# =============================================================================
echo -e "${YELLOW}[步驟 2/5]${NC} 重啟 Celery Worker 和 Beat..."

docker compose restart celery-worker celery-beat

# 等待服務啟動
echo -e "${YELLOW}   等待服務啟動（5 秒）...${NC}"
sleep 5

# 檢查服務狀態
if docker compose ps celery-worker celery-beat | grep -q "Up"; then
    echo -e "${GREEN}✅ Celery 服務已重啟${NC}"
else
    echo -e "${RED}❌ Celery 服務啟動失敗${NC}"
    docker compose ps celery-worker celery-beat
    exit 1
fi
echo ""

# =============================================================================
# 步驟 3：顯示定時任務配置
# =============================================================================
echo -e "${YELLOW}[步驟 3/5]${NC} 顯示定時任務配置..."
echo ""
echo -e "${BLUE}已配置的定時任務：${NC}"
echo -e "  ${GREEN}1. 日誌同步${NC}     - 每 10 分鐘同步所有伺服器的日誌"
echo -e "  ${GREEN}2. 租約同步${NC}     - 每 15 分鐘同步所有伺服器的租約 ⭐"
echo -e "  ${GREEN}3. Scope 同步${NC}   - 每天凌晨 4 點同步 Scope 資訊"
echo -e "  ${GREEN}4. 日誌清理${NC}     - 每天凌晨 3 點清理舊日誌（保留 7 天）"
echo -e "  ${GREEN}5. OUI 更新${NC}     - 每月 1 號更新 MAC 地址製造商資料庫"
echo -e "  ${GREEN}6. NAS 檢測${NC}     - 每 5 分鐘檢測 NAS 連線狀態"
echo -e "  ${GREEN}7. IPXE 檢測${NC}    - 每 5 分鐘檢測 IPXE 網路品質"
echo ""

# 從容器內查看 Beat 排程（可選）
echo -e "${BLUE}Celery Beat 排程確認：${NC}"
docker compose logs celery-beat --tail 10 | grep -E "Scheduler: Sending|lease" || echo "  （等待下次排程...）"
echo ""

# =============================================================================
# 步驟 4：手動觸發測試同步
# =============================================================================
echo -e "${YELLOW}[步驟 4/5]${NC} 手動觸發租約批次同步測試..."
echo ""

# 創建測試腳本
TEST_SCRIPT="/tmp/test_sync_leases_$(date +%s).py"

cat > "$TEST_SCRIPT" << 'PYTHON_EOF'
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.tasks import sync_all_dhcp_leases_task

print('=' * 60)
print('📡 手動觸發 DHCP 租約批次同步任務')
print('=' * 60)

try:
    result = sync_all_dhcp_leases_task.delay()
    print(f'\n✅ 任務已提交成功！')
    print(f'   Task ID: {result.id}')
    print(f'\n💡 同步過程需要 1-5 分鐘（取決於伺服器數量）')
    print(f'   使用以下命令查看即時日誌：')
    print(f'   docker compose logs celery-worker -f')
    print('\n' + '=' * 60)
except Exception as e:
    print(f'\n❌ 任務提交失敗：{str(e)}')
    print('=' * 60)
    exit(1)
PYTHON_EOF

# 執行測試
docker exec nt-django python "$TEST_SCRIPT"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 測試任務已觸發${NC}"
else
    echo -e "${RED}❌ 測試任務觸發失敗${NC}"
    rm -f "$TEST_SCRIPT"
    exit 1
fi

# 清理測試腳本
rm -f "$TEST_SCRIPT"
echo ""

# =============================================================================
# 步驟 5：顯示即時日誌
# =============================================================================
echo -e "${YELLOW}[步驟 5/5]${NC} 顯示即時日誌（20 秒）..."
echo -e "${BLUE}------------------------------------------------${NC}"
echo ""

# 使用 timeout 命令限制時間
timeout 20s docker compose logs celery-worker -f 2>&1 || true

echo ""
echo -e "${BLUE}------------------------------------------------${NC}"
echo -e "${GREEN}✅ 日誌顯示完成${NC}"
echo ""

# =============================================================================
# 完成提示
# =============================================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}🎉 租約自動同步已啟動！${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo -e "${YELLOW}📋 重要資訊：${NC}"
echo -e "  • 自動同步頻率：每 ${GREEN}15 分鐘${NC} 執行一次"
echo -e "  • 同步範圍：所有 ${GREEN}online${NC} 狀態的 DHCP Server"
echo -e "  • 同步內容：租約資訊（IP、MAC、主機名、狀態等）"
echo ""

echo -e "${YELLOW}📊 查看日誌：${NC}"
echo -e "  docker compose logs celery-worker -f        # 即時追蹤"
echo -e "  docker compose logs celery-worker --tail 50 # 最新 50 行"
echo -e "  docker compose logs celery-beat --tail 20   # 排程日誌"
echo ""

echo -e "${YELLOW}🔧 管理命令：${NC}"
echo -e "  docker compose restart celery-worker        # 重啟 Worker"
echo -e "  docker compose restart celery-beat          # 重啟 Beat"
echo -e "  docker compose stop celery-beat             # 停用自動同步"
echo -e "  docker compose start celery-beat            # 啟用自動同步"
echo ""

echo -e "${YELLOW}📖 文檔：${NC}"
echo -e "  詳細說明：${BLUE}docs/features/AUTO_SYNC_DHCP_LEASES.md${NC}"
echo -e "  快速參考：${BLUE}QUICKSTART_AUTO_SYNC_LEASES.md${NC}"
echo ""

echo -e "${YELLOW}🌐 監控介面（可選）：${NC}"
echo -e "  Flower: ${BLUE}http://localhost:5555${NC}"
echo -e "  （需先執行：docker compose up -d flower）"
echo ""

echo -e "${GREEN}✨ 祝使用愉快！${NC}"
echo ""
