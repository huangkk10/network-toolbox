#!/bin/bash
# ============================================================================
# NTP 自動同步系統配置檢查腳本
# 用途：驗證 NTP 時間同步系統的安裝和配置狀態
# 創建日期：2025-11-23
# ============================================================================

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "========================================================================"
echo "🕐 NTP 自動同步系統配置檢查"
echo "========================================================================"
echo ""

# ============================================================================
# 1. 檢查 ntpdate 安裝
# ============================================================================
echo -e "${BLUE}📦 1. 檢查 ntpdate 安裝${NC}"
echo "------------------------------------------------------------------------"

NTPDATE_PATH=$(docker exec nt-django which ntpdate 2>/dev/null || echo "NOT_FOUND")

if [ "$NTPDATE_PATH" != "NOT_FOUND" ]; then
    echo -e "${GREEN}✅ ntpdate 已安裝${NC}"
    echo "   路徑: $NTPDATE_PATH"
    
    # 檢查版本
    VERSION=$(docker exec nt-django ntpdate --version 2>&1 | head -1 || echo "無法取得版本")
    echo "   版本: $VERSION"
else
    echo -e "${RED}❌ ntpdate 未安裝！${NC}"
fi
echo ""

# ============================================================================
# 2. 檢查 sudo 配置
# ============================================================================
echo -e "${BLUE}🔐 2. 檢查 sudo 配置${NC}"
echo "------------------------------------------------------------------------"

SUDOERS_FILE=$(docker exec nt-django ls -l /etc/sudoers.d/ntpdate 2>/dev/null || echo "NOT_FOUND")

if echo "$SUDOERS_FILE" | grep -q "ntpdate"; then
    echo -e "${GREEN}✅ sudo 配置檔案已創建${NC}"
    echo "   $SUDOERS_FILE"
    
    # 檢查權限
    PERMISSIONS=$(echo "$SUDOERS_FILE" | awk '{print $1}')
    if echo "$PERMISSIONS" | grep -q "r--r-----"; then
        echo -e "${GREEN}   ✅ 權限正確（0440）${NC}"
    else
        echo -e "${YELLOW}   ⚠️  權限可能不正確${NC}"
    fi
    
    # 檢查配置內容
    echo ""
    echo "   配置內容:"
    docker exec nt-django cat /etc/sudoers.d/ntpdate | sed 's/^/   | /'
    
    # 驗證語法
    SYNTAX_CHECK=$(docker exec nt-django visudo -c 2>&1)
    if echo "$SYNTAX_CHECK" | grep -q "parsed OK"; then
        echo -e "${GREEN}   ✅ sudoers 語法正確${NC}"
    else
        echo -e "${RED}   ❌ sudoers 語法錯誤！${NC}"
    fi
else
    echo -e "${RED}❌ sudo 配置檔案不存在！${NC}"
fi
echo ""

# ============================================================================
# 3. 測試 sudo 權限
# ============================================================================
echo -e "${BLUE}🧪 3. 測試 sudo 權限${NC}"
echo "------------------------------------------------------------------------"

echo "測試查詢模式（不修改時間）..."
QUERY_TEST=$(docker exec nt-django sudo ntpdate -q 10.10.10.51 2>&1)

if echo "$QUERY_TEST" | grep -q "10.10.10.51"; then
    echo -e "${GREEN}✅ sudo ntpdate 查詢成功${NC}"
    echo "$QUERY_TEST" | head -1 | sed 's/^/   /'
    
    # 提取偏移量
    OFFSET=$(echo "$QUERY_TEST" | grep -oP '(?<= )-?\d+\.\d+(?= \+)' | head -1)
    ABS_OFFSET=$(echo "$OFFSET" | awk '{print ($1<0)?-$1:$1}')
    OFFSET_MS=$(echo "$ABS_OFFSET * 1000" | bc)
    
    echo "   當前偏移: ${OFFSET_MS%.000000} ms"
    
    if (( $(echo "$OFFSET_MS < 50" | bc -l) )); then
        echo -e "${GREEN}   狀態: 🟢 正常（<50ms）${NC}"
    elif (( $(echo "$OFFSET_MS < 100" | bc -l) )); then
        echo -e "${GREEN}   狀態: 🟢 良好（<100ms）${NC}"
    elif (( $(echo "$OFFSET_MS < 200" | bc -l) )); then
        echo -e "${YELLOW}   狀態: 🟡 警告（<200ms）${NC}"
    else
        echo -e "${RED}   狀態: 🔴 需要同步（>200ms）${NC}"
    fi
else
    echo -e "${RED}❌ sudo ntpdate 查詢失敗！${NC}"
    echo "$QUERY_TEST"
fi
echo ""

# ============================================================================
# 4. 測試 Python 調用
# ============================================================================
echo -e "${BLUE}🐍 4. 測試 Python subprocess 調用${NC}"
echo "------------------------------------------------------------------------"

PYTHON_TEST=$(docker exec nt-django python manage.py shell -c "
import subprocess

cmd = ['sudo', 'ntpdate', '-q', '10.10.10.51']
try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    if result.returncode == 0:
        print('SUCCESS')
        print(result.stdout.strip())
    else:
        print('FAILED')
        print(result.stderr)
except Exception as e:
    print('ERROR')
    print(str(e))
" 2>&1)

if echo "$PYTHON_TEST" | grep -q "SUCCESS"; then
    echo -e "${GREEN}✅ Python 調用 sudo ntpdate 成功${NC}"
    echo "$PYTHON_TEST" | tail -1 | sed 's/^/   /'
else
    echo -e "${RED}❌ Python 調用失敗！${NC}"
    echo "$PYTHON_TEST" | sed 's/^/   /'
fi
echo ""

# ============================================================================
# 5. 檢查 NTP 服務器連通性
# ============================================================================
echo -e "${BLUE}🌐 5. 檢查 NTP 服務器連通性${NC}"
echo "------------------------------------------------------------------------"

echo "測試與 10.10.10.51 的連接..."
NTP_CHECK=$(docker exec nt-django python manage.py shell -c "
from api.ntp_service import NTPService

service = NTPService(ntp_server='10.10.10.51')
result = service.check_sync()

if result['status'] == 'success':
    print(f'SUCCESS')
    print(f'Offset: {result[\"offset\"]:.2f} ms')
    print(f'Stratum: {result.get(\"stratum\", \"N/A\")}')
    print(f'Response Time: {result.get(\"response_time\", \"N/A\")} ms')
else:
    print(f'FAILED')
    print(f'Error: {result.get(\"error\", \"Unknown\")}')
" 2>&1)

if echo "$NTP_CHECK" | grep -q "SUCCESS"; then
    echo -e "${GREEN}✅ NTP 服務器連接正常${NC}"
    echo "$NTP_CHECK" | tail -3 | sed 's/^/   /'
else
    echo -e "${RED}❌ NTP 服務器連接失敗！${NC}"
    echo "$NTP_CHECK" | sed 's/^/   /'
fi
echo ""

# ============================================================================
# 6. 檢查資料庫狀態
# ============================================================================
echo -e "${BLUE}💾 6. 檢查 NTP 資料庫狀態${NC}"
echo "------------------------------------------------------------------------"

DB_CHECK=$(docker exec nt-django python manage.py shell -c "
from api.models import NTPSyncLog
from django.utils import timezone
from datetime import timedelta

# 總記錄數
total = NTPSyncLog.objects.count()
print(f'總記錄數: {total}')

# 最新記錄
latest = NTPSyncLog.objects.order_by('-timestamp').first()
if latest:
    print(f'最新檢測: {latest.timestamp.strftime(\"%Y-%m-%d %H:%M:%S\")}')
    print(f'最新偏移: {latest.offset:.2f} ms')
    print(f'檢測狀態: {latest.status}')

# 最近 1 小時記錄數
one_hour_ago = timezone.now() - timedelta(hours=1)
recent = NTPSyncLog.objects.filter(timestamp__gte=one_hour_ago).count()
print(f'最近 1 小時記錄: {recent} 筆')
" 2>&1)

echo "$DB_CHECK"
echo ""

# ============================================================================
# 總結
# ============================================================================
echo "========================================================================"
echo -e "${GREEN}✅ NTP 配置檢查完成${NC}"
echo "========================================================================"
echo ""
echo "📌 下一步："
echo "   1. ✅ Step 1-2 已完成（安裝 + 配置 sudo）"
echo "   2. ⏳ Step 3: 更新 Dockerfile（持久化配置）"
echo "   3. ⏳ Step 4: 創建 NTPSyncOperation 模型"
echo "   4. ⏳ Step 5: 擴展 NTPSyncService 類"
echo "   5. ⏳ Step 6-9: 創建 Celery 任務和 API"
echo ""
echo "💡 提示："
echo "   - 當前配置在容器重啟後會失效"
echo "   - 需要更新 Dockerfile 以持久化配置"
echo "   - 建議執行 Step 3 before 重啟容器"
echo ""
