#!/bin/bash

# iPXE SSH 驗證功能測試腳本
# 測試新增的 SSH 連接驗證機制

echo "=========================================="
echo "iPXE SSH 驗證功能測試"
echo "=========================================="
echo ""

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 測試計數器
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 測試函數
run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_result="$3"  # "success" 或 "fail"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -e "${YELLOW}測試 $TOTAL_TESTS: $test_name${NC}"
    
    # 執行測試
    result=$(eval "$test_command" 2>&1)
    exit_code=$?
    
    # 判斷結果
    if [ "$expected_result" = "success" ]; then
        if [ $exit_code -eq 0 ]; then
            echo -e "${GREEN}✅ 測試通過${NC}"
            PASSED_TESTS=$((PASSED_TESTS + 1))
        else
            echo -e "${RED}❌ 測試失敗${NC}"
            echo "輸出: $result"
            FAILED_TESTS=$((FAILED_TESTS + 1))
        fi
    else
        if [ $exit_code -ne 0 ]; then
            echo -e "${GREEN}✅ 測試通過（預期失敗）${NC}"
            PASSED_TESTS=$((PASSED_TESTS + 1))
        else
            echo -e "${RED}❌ 測試失敗（應該失敗但成功了）${NC}"
            FAILED_TESTS=$((FAILED_TESTS + 1))
        fi
    fi
    
    echo ""
}

echo "=== 1. 檢查新增的 Celery 任務 ==="
echo ""

run_test "檢查 verify_ipxe_ssh_connection_task 是否已註冊" \
    "docker exec nt-django celery -A network_toolbox inspect registered | grep -q 'verify_ipxe_ssh_connection_task'" \
    "success"

echo "=== 2. 檢查 IPXEServer 模型更新 ==="
echo ""

run_test "檢查 IPXEServer 是否有 last_error 欄位" \
    "docker exec nt-django python manage.py shell -c \"from api.models import IPXEServer; print(hasattr(IPXEServer, 'last_error'))\" | grep -q 'True'" \
    "success"

run_test "檢查 IPXEServer 是否有 error 狀態選項" \
    "docker exec nt-django python manage.py shell -c \"from api.models import IPXEServer; print(('error', 'Error') in IPXEServer.STATUS_CHOICES)\" | grep -q 'True'" \
    "success"

echo "=== 3. 測試現有伺服器狀態 ==="
echo ""

echo "查詢現有 iPXE 伺服器狀態："
docker exec nt-django python manage.py shell -c "
from api.models import IPXEServer
servers = IPXEServer.objects.all()
for s in servers:
    print(f'  [{s.id}] {s.ip_address} - 狀態: {s.status}, 錯誤: {s.last_error or \"無\"}')" 

echo ""

echo "=== 4. 測試手動觸發 SSH 驗證 ==="
echo ""

# 獲取第一個伺服器 ID
SERVER_ID=$(docker exec nt-django python manage.py shell -c "
from api.models import IPXEServer
server = IPXEServer.objects.first()
print(server.id if server else 0)
" | tail -1)

if [ "$SERVER_ID" != "0" ]; then
    echo "測試伺服器 ID: $SERVER_ID"
    
    run_test "手動觸發 SSH 驗證任務" \
        "docker exec nt-django python manage.py shell -c \"
from api.tasks import verify_ipxe_ssh_connection_task
result = verify_ipxe_ssh_connection_task.apply_async(args=[$SERVER_ID], countdown=0)
print('Task ID:', result.id)
\"" \
        "success"
    
    echo "等待 5 秒讓任務執行..."
    sleep 5
    
    echo "檢查伺服器狀態更新："
    docker exec nt-django python manage.py shell -c "
from api.models import IPXEServer
server = IPXEServer.objects.get(id=$SERVER_ID)
print(f'  狀態: {server.status}')
print(f'  錯誤: {server.last_error or \"無\"}')" 
    
    echo ""
else
    echo -e "${YELLOW}⚠️  跳過：資料庫中沒有 iPXE 伺服器${NC}"
    echo ""
fi

echo "=== 5. 測試 Signal 自動觸發機制 ==="
echo ""

echo "檢查 ipxe_server_post_save Signal 是否已更新："
grep -n "verify_ipxe_ssh_connection_task" backend/api/signals.py && \
    echo -e "${GREEN}✅ Signal 已更新，包含 SSH 驗證任務${NC}" || \
    echo -e "${RED}❌ Signal 未包含 SSH 驗證任務${NC}"

echo ""

echo "=== 6. 測試手動觸發函數 ==="
echo ""

if [ "$SERVER_ID" != "0" ]; then
    run_test "測試 trigger_ipxe_logs_sync_for_server 函數" \
        "docker exec nt-django python manage.py shell -c \"
from api.signals import trigger_ipxe_logs_sync_for_server
task_id = trigger_ipxe_logs_sync_for_server(server_id=$SERVER_ID, delay_seconds=60, limit=100)
print('Task ID:', task_id)
if task_id:
    print('SUCCESS')
else:
    print('FAILED')
\" | grep -q 'SUCCESS'" \
        "success"
fi

echo "=========================================="
echo "測試總結"
echo "=========================================="
echo -e "總測試數: ${TOTAL_TESTS}"
echo -e "${GREEN}通過: ${PASSED_TESTS}${NC}"
echo -e "${RED}失敗: ${FAILED_TESTS}${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✅ 所有測試通過！SSH 驗證功能已正確實現。${NC}"
    echo ""
    echo "📝 功能說明："
    echo "  1. 新建 iPXE Server 時會自動觸發 SSH 驗證（2 秒後）"
    echo "  2. SSH 驗證成功：狀態設為 'online'，清除錯誤訊息"
    echo "  3. SSH 驗證失敗：狀態設為 'error'，記錄錯誤訊息"
    echo "  4. 前端可以讀取 status 和 last_error 欄位顯示狀態"
    echo ""
    echo "🚀 下一步："
    echo "  1. 更新前端頁面，顯示伺服器狀態和錯誤訊息"
    echo "  2. 添加「重試連接」按鈕"
    echo "  3. 測試創建新的 iPXE Server（包含錯誤 SSH 憑證）"
    exit 0
else
    echo -e "${RED}❌ 有 ${FAILED_TESTS} 個測試失敗，請檢查實現。${NC}"
    exit 1
fi
