#!/bin/bash

# 🔍 Network Toolbox - 完整系統驗證腳本
# 驗證所有 API 端點和功能是否正常運作

echo "╔════════════════════════════════════════════════════════════╗"
echo "║   Network Toolbox - 系統驗證                                ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# 顏色定義
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 計數器
TOTAL=0
PASSED=0
FAILED=0

# 測試函數
test_api() {
    local name=$1
    local url=$2
    local expected_code=${3:-200}
    
    TOTAL=$((TOTAL + 1))
    echo -n "[$TOTAL] 測試 $name ... "
    
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
    
    if [ "$response" -eq "$expected_code" ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $response)"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}✗ FAIL${NC} (HTTP $response, 預期 $expected_code)"
        FAILED=$((FAILED + 1))
    fi
}

test_api_with_data() {
    local name=$1
    local url=$2
    
    TOTAL=$((TOTAL + 1))
    echo -n "[$TOTAL] 測試 $name ... "
    
    response=$(curl -s "$url" 2>/dev/null)
    http_code=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
    
    if [ "$http_code" -eq 200 ]; then
        # 檢查回應是否為有效 JSON
        if echo "$response" | python3 -m json.tool > /dev/null 2>&1; then
            echo -e "${GREEN}✓ PASS${NC} (有效 JSON)"
            PASSED=$((PASSED + 1))
        else
            echo -e "${RED}✗ FAIL${NC} (無效 JSON)"
            FAILED=$((FAILED + 1))
        fi
    else
        echo -e "${RED}✗ FAIL${NC} (HTTP $http_code)"
        FAILED=$((FAILED + 1))
    fi
}

echo -e "${BLUE}📡 檢查服務狀態...${NC}"
echo ""

# 檢查 Docker 容器
echo "🐳 Docker 容器狀態:"
docker compose ps

echo ""
echo -e "${BLUE}🔍 測試 API 端點...${NC}"
echo ""

# 基本 API
test_api "基本 API" "http://localhost/api/"

echo ""
echo -e "${BLUE}📊 DHCP Analytics - OverviewTab APIs${NC}"
echo ""

# OverviewTab APIs
test_api_with_data "概覽統計 API" "http://localhost/api/dhcp-analytics/overview/?server=all"
test_api_with_data "趨勢數據 API" "http://localhost/api/dhcp-analytics/trend/?server=all"
test_api_with_data "狀態分佈 API" "http://localhost/api/dhcp-analytics/status-distribution/?server=all"
test_api_with_data "最近租約 API" "http://localhost/api/dhcp-analytics/recent-leases/?server=all"

echo ""
echo -e "${BLUE}📋 DHCP Analytics - LogsTab APIs${NC}"
echo ""

# LogsTab APIs
test_api_with_data "日誌查詢 API (全部)" "http://localhost/api/dhcp-analytics/logs/?source=local&server=all"
test_api_with_data "日誌查詢 API (ERROR)" "http://localhost/api/dhcp-analytics/logs/?source=local&server=all&level=ERROR"
test_api_with_data "日誌查詢 API (關鍵字)" "http://localhost/api/dhcp-analytics/logs/?source=local&server=all&keyword=DHCP"
test_api_with_data "日誌查詢 API (限制數量)" "http://localhost/api/dhcp-analytics/logs/?source=local&server=all&limit=5"

echo ""
echo -e "${BLUE}🔧 檢查資料庫數據...${NC}"
echo ""

# 檢查租約數量
LEASE_COUNT=$(docker exec nt-django python manage.py shell -c "from api.models import DHCPLease; print(DHCPLease.objects.count())" 2>/dev/null | tail -1)
echo "📦 資料庫租約數量: $LEASE_COUNT"

if [ "$LEASE_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓${NC} 資料庫包含租約數據"
    PASSED=$((PASSED + 1))
else
    echo -e "${YELLOW}⚠${NC} 資料庫沒有租約數據（可執行 create_test_data.py 創建測試數據）"
fi
TOTAL=$((TOTAL + 1))

echo ""
echo -e "${BLUE}📄 檢查日誌檔案...${NC}"
echo ""

# 檢查日誌檔案
if [ -f "logs/dhcp_operations.log" ]; then
    LOG_LINES=$(wc -l < logs/dhcp_operations.log)
    echo -e "${GREEN}✓${NC} 日誌檔案存在: logs/dhcp_operations.log ($LOG_LINES 行)"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗${NC} 日誌檔案不存在"
    FAILED=$((FAILED + 1))
fi
TOTAL=$((TOTAL + 1))

echo ""
echo -e "${BLUE}🌐 檢查前端服務...${NC}"
echo ""

# 檢查前端
test_api "前端首頁" "http://localhost/" 200

echo ""
echo "════════════════════════════════════════════════════════════"
echo -e "${BLUE}📊 測試結果統計${NC}"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "總測試數: $TOTAL"
echo -e "${GREEN}通過: $PASSED${NC}"
echo -e "${RED}失敗: $FAILED${NC}"

PASS_RATE=$((PASSED * 100 / TOTAL))
echo "通過率: $PASS_RATE%"

echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║   ✅ 所有測試通過！系統運作正常！    ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
    exit 0
else
    echo -e "${RED}╔════════════════════════════════════════╗${NC}"
    echo -e "${RED}║   ❌ 有測試失敗，請檢查錯誤訊息      ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════╝${NC}"
    echo ""
    echo "建議檢查："
    echo "1. docker compose logs django"
    echo "2. docker compose logs nginx"
    echo "3. tail -f logs/django_error.log"
    exit 1
fi
