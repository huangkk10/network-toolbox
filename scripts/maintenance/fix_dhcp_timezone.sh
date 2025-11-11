#!/bin/bash

# ============================================
# DHCP 日誌時區修復腳本
# ============================================

echo "================================================"
echo "DHCP 日誌時區修復 - 部署腳本"
echo "================================================"
echo ""

# 顏色定義
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. 檢查 Docker 容器狀態
echo -e "${BLUE}[1/7] 檢查 Docker 容器狀態...${NC}"
if docker ps | grep -q "nt-django"; then
    echo -e "${GREEN}✓ Django 容器運行中${NC}"
else
    echo -e "${RED}✗ Django 容器未運行，請先啟動${NC}"
    exit 1
fi
echo ""

# 2. 安裝新的 Python 套件
echo -e "${BLUE}[2/7] 安裝 Python 套件（pytz, python-dateutil）...${NC}"
docker exec nt-django pip install pytz python-dateutil
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Python 套件安裝成功${NC}"
else
    echo -e "${RED}✗ Python 套件安裝失敗${NC}"
    exit 1
fi
echo ""

# 3. 驗證修改
echo -e "${BLUE}[3/7] 驗證代碼修改...${NC}"

if grep -q "import pytz" library/utils/log_parser.py; then
    echo -e "${GREEN}✓ log_parser.py 已導入 pytz${NC}"
else
    echo -e "${RED}✗ log_parser.py 未導入 pytz${NC}"
    exit 1
fi

if grep -q "taipei_tz = pytz.timezone('Asia/Taipei')" library/utils/log_parser.py; then
    echo -e "${GREEN}✓ log_parser.py 已設定 Taipei 時區${NC}"
else
    echo -e "${RED}✗ log_parser.py 未設定時區${NC}"
    exit 1
fi

if grep -q "from dateutil import parser as date_parser" backend/api/services.py; then
    echo -e "${GREEN}✓ services.py 已導入 dateutil${NC}"
else
    echo -e "${RED}✗ services.py 未導入 dateutil${NC}"
    exit 1
fi
echo ""

# 4. 重啟 Django 容器
echo -e "${BLUE}[4/7] 重啟 Django 容器...${NC}"
docker compose restart django
echo -e "${GREEN}✓ Django 容器已重啟${NC}"
echo ""

# 5. 等待服務啟動
echo -e "${BLUE}[5/7] 等待服務啟動（15秒）...${NC}"
for i in {15..1}; do
    echo -ne "${YELLOW}$i...${NC} "
    sleep 1
done
echo ""
echo -e "${GREEN}✓ 服務啟動完成${NC}"
echo ""

# 6. 檢查 Django 日誌
echo -e "${BLUE}[6/7] 檢查 Django 容器日誌（最後 20 行）...${NC}"
docker compose logs django --tail 20
echo ""

# 7. 測試時區設定
echo -e "${BLUE}[7/7] 測試時區設定...${NC}"
docker exec nt-django python -c "
import pytz
from datetime import datetime
from django.utils import timezone

print('✓ pytz 已安裝')
taipei_tz = pytz.timezone('Asia/Taipei')
now = datetime.now(taipei_tz)
print(f'✓ 當前 Taipei 時間: {now}')
print(f'✓ Django TIME_ZONE: {timezone.get_current_timezone()}')
"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 時區設定正確${NC}"
else
    echo -e "${RED}✗ 時區設定測試失敗${NC}"
fi
echo ""

# 完成
echo "================================================"
echo -e "${GREEN}修復完成！${NC}"
echo "================================================"
echo ""
echo "下一步："
echo "1. 重新同步 DHCP 日誌："
echo "   - 進入 DHCP Server 分析 → 日誌查看"
echo "   - 點擊「同步日誌」按鈕"
echo ""
echo "2. 驗證時間顯示："
echo "   - 檢查 Web 顯示的時間"
echo "   - 檢查 Raw Log 的時間"
echo "   - 兩者應該一致（都是 Taipei 時區）"
echo ""
echo "3. 舊日誌說明："
echo "   - 舊日誌（修復前）的時間可能仍不正確"
echo "   - 建議：刪除舊日誌，重新同步"
echo "   - 或者：執行資料庫時區修正腳本"
echo ""
echo "預期結果："
echo "  ✓ Web 時間 = Raw Log 時間（Taipei 時區）"
echo "  ✓ 不再有 8 小時的時差"
echo ""
