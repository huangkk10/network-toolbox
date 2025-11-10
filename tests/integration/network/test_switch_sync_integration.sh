#!/bin/bash
# 快速測試自動 Switch 同步功能

set -e

echo "=========================================="
echo "自動 Switch 同步功能測試"
echo "=========================================="
echo ""

# 顏色定義
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 檢查服務狀態
check_services() {
    echo -e "${YELLOW}[1/6] 檢查服務狀態...${NC}"
    
    if docker compose ps | grep -q "nt-django.*Up"; then
        echo -e "${GREEN}✅ Django 服務運行中${NC}"
    else
        echo -e "${RED}❌ Django 服務未運行${NC}"
        exit 1
    fi
    
    if docker compose ps | grep -q "nt-celery.*Up"; then
        echo -e "${GREEN}✅ Celery 服務運行中${NC}"
    else
        echo -e "${RED}❌ Celery 服務未運行${NC}"
        exit 1
    fi
    
    echo ""
}

# 創建測試 Server
create_test_server() {
    echo -e "${YELLOW}[2/6] 創建測試 DHCP Server...${NC}"
    
    SERVER_ID=$(docker exec nt-django python manage.py shell -c "
from api.models import DHCPServer
import sys

# 刪除舊的測試 Server
DHCPServer.objects.filter(name='TEST-AUTO-SYNC').delete()

# 創建新的測試 Server
server = DHCPServer.objects.create(
    name='TEST-AUTO-SYNC',
    ip_address='10.250.200.1',
    ssh_username='admin',
    ssh_password='test123',
    ssh_port=22,
    status='online',
    os_type='windows',
    dhcp_service_type='isc-dhcp'
)

sys.stdout.write(str(server.id))
" 2>/dev/null)
    
    if [ -n "$SERVER_ID" ]; then
        echo -e "${GREEN}✅ 測試 Server 已創建 (ID: $SERVER_ID)${NC}"
    else
        echo -e "${RED}❌ 創建 Server 失敗${NC}"
        exit 1
    fi
    
    echo ""
}

# 檢查信號觸發
check_signal() {
    echo -e "${YELLOW}[3/6] 檢查 Django 信號觸發...${NC}"
    
    sleep 2
    
    # 檢查最近 10 秒的日誌
    if docker compose logs django --since 10s 2>/dev/null | grep -q "\[Signal\].*TEST-AUTO-SYNC"; then
        echo -e "${GREEN}✅ 信號已觸發${NC}"
        docker compose logs django --since 10s 2>/dev/null | grep "\[Signal\].*TEST-AUTO-SYNC"
    else
        echo -e "${RED}❌ 未檢測到信號觸發${NC}"
    fi
    
    echo ""
}

# 等待 Switch 識別任務
wait_for_task() {
    echo -e "${YELLOW}[4/6] 等待 Switch 識別任務執行...${NC}"
    echo "（任務延遲 60 秒執行，請稍候...）"
    
    # 顯示倒數計時
    for i in {60..1}; do
        printf "\r等待中... %2d 秒" $i
        sleep 1
    done
    printf "\n"
    
    # 再等待 10 秒確保任務完成
    echo "等待任務完成..."
    sleep 10
    
    echo ""
}

# 檢查 Celery 任務執行
check_celery_task() {
    echo -e "${YELLOW}[5/6] 檢查 Celery 任務執行...${NC}"
    
    if docker compose logs celery --since 90s 2>/dev/null | grep -q "auto_identify_switches"; then
        echo -e "${GREEN}✅ Switch 識別任務已執行${NC}"
        docker compose logs celery --since 90s 2>/dev/null | grep -A 5 "auto_identify_switches"
    else
        echo -e "${YELLOW}⚠️ 未在日誌中找到任務執行記錄${NC}"
    fi
    
    echo ""
}

# 驗證結果
verify_result() {
    echo -e "${YELLOW}[6/6] 驗證 Switch 創建結果...${NC}"
    
    RESULT=$(docker exec nt-django python manage.py shell -c "
from api.models import DHCPServer, NetworkSwitch

try:
    server = DHCPServer.objects.get(name='TEST-AUTO-SYNC')
    switches = NetworkSwitch.objects.filter(dhcp_server=server)
    
    print(f'Server: {server.name} (ID: {server.id})')
    print(f'Switch 數量: {switches.count()}')
    
    for sw in switches:
        print(f'  - {sw.name} ({sw.ip_address}): {sw.connected_devices} devices')
        
except DHCPServer.DoesNotExist:
    print('❌ Server 不存在')
" 2>/dev/null)
    
    echo "$RESULT"
    
    if echo "$RESULT" | grep -q "Switch 數量: [1-9]"; then
        echo -e "${GREEN}✅ 測試成功！Switch 已自動創建${NC}"
    else
        echo -e "${YELLOW}⚠️ 未找到 Switch（可能租約中沒有 Switch 設備）${NC}"
    fi
    
    echo ""
}

# 清理測試數據
cleanup() {
    echo -e "${YELLOW}清理測試數據...${NC}"
    
    docker exec nt-django python manage.py shell -c "
from api.models import DHCPServer

# 刪除測試 Server（會級聯刪除相關數據）
deleted = DHCPServer.objects.filter(name='TEST-AUTO-SYNC').delete()
print(f'已刪除: {deleted[0]} 筆記錄')
" 2>/dev/null
    
    echo -e "${GREEN}✅ 清理完成${NC}"
    echo ""
}

# 主程序
main() {
    check_services
    create_test_server
    check_signal
    wait_for_task
    check_celery_task
    verify_result
    
    echo "=========================================="
    echo -e "${GREEN}測試完成！${NC}"
    echo "=========================================="
    echo ""
    
    # 詢問是否清理
    read -p "是否清理測試數據？(y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cleanup
    else
        echo "測試數據已保留"
    fi
}

# 執行主程序
main
