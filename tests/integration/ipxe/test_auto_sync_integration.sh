#!/bin/bash
# iPXE 日誌自動同步功能測試腳本

set -e  # 遇到錯誤立即退出

echo "=========================================="
echo "iPXE 日誌自動同步功能測試"
echo "=========================================="
echo ""

# 顏色定義
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 測試計數器
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 測試結果記錄
test_result() {
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ PASS${NC}: $2"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}❌ FAIL${NC}: $2"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
}

echo "📋 測試 1: 檢查 Celery 任務是否註冊"
echo "-------------------------------------------"

# 檢查 sync_ipxe_logs_task
docker exec nt-celery-worker celery -A network_toolbox inspect registered 2>/dev/null | grep -q "api.tasks.sync_ipxe_logs_task"
test_result $? "sync_ipxe_logs_task 任務已註冊"

# 檢查 sync_all_ipxe_logs_task
docker exec nt-celery-worker celery -A network_toolbox inspect registered 2>/dev/null | grep -q "api.tasks.sync_all_ipxe_logs_task"
test_result $? "sync_all_ipxe_logs_task 任務已註冊"

echo ""
echo "📋 測試 2: 檢查定期任務配置"
echo "-------------------------------------------"

# 檢查定期任務是否存在且啟用
TASK_STATUS=$(docker exec nt-django python manage.py shell -c "
from django_celery_beat.models import PeriodicTask
try:
    task = PeriodicTask.objects.get(name='sync-all-ipxe-logs-every-10-minutes')
    print(f'{task.enabled}|{task.task}')
except:
    print('NOT_FOUND')
" 2>/dev/null)

if echo "$TASK_STATUS" | grep -q "True|api.tasks.sync_all_ipxe_logs_task"; then
    test_result 0 "定期任務已啟用且配置正確"
else
    test_result 1 "定期任務配置異常: $TASK_STATUS"
fi

echo ""
echo "📋 測試 3: 檢查 Signal 是否正確配置"
echo "-------------------------------------------"

# 檢查 signals.py 是否包含 iPXE Signal
if grep -q "ipxe_server_post_save" backend/api/signals.py 2>/dev/null; then
    test_result 0 "iPXE Server Signal 已配置"
else
    test_result 1 "iPXE Server Signal 未找到"
fi

# 檢查手動觸發函數是否存在
if grep -q "trigger_ipxe_logs_sync_for_server" backend/api/signals.py 2>/dev/null; then
    test_result 0 "手動觸發函數已實現"
else
    test_result 1 "手動觸發函數未找到"
fi

echo ""
echo "📋 測試 4: 檢查 Celery 服務狀態"
echo "-------------------------------------------"

# 檢查 Celery Worker
if docker compose ps celery_worker 2>/dev/null | grep -q "Up"; then
    test_result 0 "Celery Worker 運行中"
else
    test_result 1 "Celery Worker 未運行"
fi

# 檢查 Celery Beat
if docker compose ps celery_beat 2>/dev/null | grep -q "Up"; then
    test_result 0 "Celery Beat 運行中"
else
    test_result 1 "Celery Beat 未運行"
fi

echo ""
echo "📋 測試 5: 檢查現有 iPXE Server 狀態"
echo "-------------------------------------------"

# 檢查 Server 10.250.120.2
SERVER_INFO=$(docker exec nt-django python manage.py shell -c "
from api.models import IPXEServer, IPXELog

try:
    server = IPXEServer.objects.get(ip_address='10.250.120.2')
    log_count = IPXELog.objects.filter(server=server).count()
    sync_status = 'synced' if server.last_sync_at else 'never'
    print(f'{server.status}|{sync_status}|{log_count}')
except:
    print('NOT_FOUND')
" 2>/dev/null)

if echo "$SERVER_INFO" | grep -q "online|synced|[1-9]"; then
    LOG_COUNT=$(echo "$SERVER_INFO" | cut -d'|' -f3)
    test_result 0 "Server 10.250.120.2 已同步 (${LOG_COUNT} 條日誌)"
else
    test_result 1 "Server 10.250.120.2 狀態異常: $SERVER_INFO"
fi

echo ""
echo "📋 測試 6: 測試手動觸發功能"
echo "-------------------------------------------"

# 獲取一個 Server ID 進行測試
TEST_SERVER_ID=$(docker exec nt-django python manage.py shell -c "
from api.models import IPXEServer
server = IPXEServer.objects.filter(status='online').first()
print(server.id if server else '')
" 2>/dev/null | tr -d '\n')

if [ -n "$TEST_SERVER_ID" ]; then
    echo "使用 Server ID: $TEST_SERVER_ID 進行測試"
    
    # 手動觸發
    TASK_ID=$(docker exec nt-django python manage.py shell -c "
from api.signals import trigger_ipxe_logs_sync_for_server
task_id = trigger_ipxe_logs_sync_for_server(server_id=${TEST_SERVER_ID}, delay_seconds=0, limit=10)
print(task_id if task_id else '')
" 2>/dev/null | grep -v "^\[" | tail -1 | tr -d '\n')
    
    if [ -n "$TASK_ID" ] && [ "$TASK_ID" != "None" ]; then
        test_result 0 "手動觸發成功 (Task ID: ${TASK_ID})"
    else
        test_result 1 "手動觸發失敗"
    fi
else
    test_result 1 "沒有找到可用的測試伺服器"
fi

echo ""
echo "📋 測試 7: 檢查日誌記錄"
echo "-------------------------------------------"

# 檢查是否有 iPXE 相關日誌
if grep -q "iPXE 日誌同步" logs/django.log 2>/dev/null; then
    test_result 0 "日誌記錄正常"
else
    echo -e "${YELLOW}⚠️  WARNING${NC}: 未找到 iPXE 同步日誌（可能還未執行過）"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
fi

echo ""
echo "=========================================="
echo "測試總結"
echo "=========================================="
echo -e "總測試數: ${TOTAL_TESTS}"
echo -e "${GREEN}通過: ${PASSED_TESTS}${NC}"
echo -e "${RED}失敗: ${FAILED_TESTS}${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}🎉 所有測試通過！iPXE 自動同步功能正常運作。${NC}"
    exit 0
else
    echo -e "${RED}⚠️  有 ${FAILED_TESTS} 個測試失敗，請檢查上述錯誤。${NC}"
    exit 1
fi
