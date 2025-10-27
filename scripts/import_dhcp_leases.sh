#!/bin/bash

# ============================================
# DHCP 租約 JSON 匯入腳本
# 用於匯入從 Windows Server 導出的 JSON 文件
# ============================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  DHCP 租約匯入工具${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 檢查參數
if [ "$#" -lt 1 ]; then
    echo -e "${YELLOW}用法: $0 <JSON文件路徑> [DHCP_SERVER_ID]${NC}"
    echo ""
    echo "範例:"
    echo "  $0 /path/to/dhcp_leases.json"
    echo "  $0 /path/to/dhcp_leases.json 1"
    echo ""
    exit 1
fi

JSON_FILE="$1"
SERVER_ID="${2:-1}"  # 預設使用 Server ID 1

# 檢查文件是否存在
if [ ! -f "$JSON_FILE" ]; then
    echo -e "${RED}✗ 文件不存在: $JSON_FILE${NC}"
    exit 1
fi

echo -e "${GREEN}✓ 找到 JSON 文件: $JSON_FILE${NC}"

# 檢查文件大小
FILE_SIZE=$(du -h "$JSON_FILE" | cut -f1)
echo -e "${GREEN}✓ 文件大小: $FILE_SIZE${NC}"
echo ""

# 檢查 Docker 容器
echo -e "${BLUE}[1/3] 檢查 Docker 環境...${NC}"
if ! docker compose ps | grep -q nt-django; then
    echo -e "${RED}✗ Django 容器未運行${NC}"
    echo "請先啟動: docker compose up -d"
    exit 1
fi
echo -e "${GREEN}✓ Docker 容器運行中${NC}"
echo ""

# 複製文件到容器
echo -e "${BLUE}[2/3] 複製文件到 Docker 容器...${NC}"
docker cp "$JSON_FILE" nt-django:/tmp/dhcp_leases.json

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 文件已複製到容器${NC}"
else
    echo -e "${RED}✗ 文件複製失敗${NC}"
    exit 1
fi
echo ""

# 執行匯入
echo -e "${BLUE}[3/3] 匯入租約資料到資料庫...${NC}"
echo ""

# 創建 Python 匯入腳本
cat > /tmp/import_leases.py << 'EOFPYTHON'
import json
import sys
from datetime import datetime
from django.utils import timezone
from api.models import DHCPServer, DHCPLease

def parse_client_id(client_id):
    """解析 Windows ClientId 為標準 MAC"""
    if not client_id:
        return None
    
    try:
        parts = client_id.split('-')
        if len(parts) > 1:
            mac_parts = parts[1:7] if len(parts) >= 7 else parts[1:]
        else:
            mac_parts = parts
        
        mac_address = ':'.join(mac_parts).lower()
        
        if len(mac_address.split(':')) == 6:
            return mac_address
        else:
            return None
    except:
        return None

def parse_lease_expiry(expiry_str):
    """解析租約到期時間"""
    if not expiry_str:
        return timezone.now() + timezone.timedelta(hours=24)
    
    try:
        dt = datetime.strptime(expiry_str, '%Y-%m-%d %H:%M:%S')
        return timezone.make_aware(dt)
    except:
        return timezone.now() + timezone.timedelta(hours=24)

# 讀取參數
server_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
json_file = '/tmp/dhcp_leases.json'

print(f'Server ID: {server_id}')
print(f'JSON 文件: {json_file}')
print('')

# 檢查 Server 是否存在
try:
    server = DHCPServer.objects.get(id=server_id)
    print(f'✓ 找到 DHCP Server: {server.name} ({server.ip_address})')
except DHCPServer.DoesNotExist:
    print(f'✗ DHCP Server ID {server_id} 不存在！')
    print('')
    print('可用的 Server:')
    for s in DHCPServer.objects.all():
        print(f'  - ID {s.id}: {s.name} ({s.ip_address})')
    sys.exit(1)

print('')

# 讀取 JSON 文件
print('[1/2] 讀取 JSON 文件...')
with open(json_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

if isinstance(data, dict):
    data = [data]

print(f'✓ 讀取 {len(data)} 筆租約資料')
print('')

# 匯入租約
print('[2/2] 匯入到資料庫...')

stats = {
    'total': len(data),
    'created': 0,
    'updated': 0,
    'skipped': 0,
    'errors': 0,
}

for i, lease_data in enumerate(data, 1):
    try:
        # 解析 MAC
        client_id = lease_data.get('ClientId', '')
        mac_address = parse_client_id(client_id)
        
        if not mac_address:
            stats['skipped'] += 1
            continue
        
        # 獲取其他資料
        ip_address = lease_data.get('IPAddress', '')
        hostname = lease_data.get('HostName', '') or ''
        state = lease_data.get('AddressState', '').lower()
        
        lease_expiry_str = lease_data.get('LeaseExpiryTime', '')
        lease_end = parse_lease_expiry(lease_expiry_str)
        lease_start = timezone.now()
        
        is_active = (state == 'active' and lease_end > timezone.now())
        
        # 更新或創建
        lease, created = DHCPLease.objects.update_or_create(
            server=server,
            mac_address=mac_address,
            defaults={
                'ip_address': ip_address,
                'hostname': hostname,
                'lease_start': lease_start,
                'lease_end': lease_end,
                'is_active': is_active,
            }
        )
        
        if created:
            stats['created'] += 1
        else:
            stats['updated'] += 1
        
        # 進度顯示
        if i % 100 == 0:
            print(f'  處理進度: {i}/{stats["total"]} ({i*100//stats["total"]}%)')
    
    except Exception as e:
        stats['errors'] += 1
        if stats['errors'] <= 5:  # 只顯示前 5 個錯誤
            print(f'  ✗ 錯誤: {str(e)}')

print('')
print('匯入統計:')
print(f'  總數: {stats["total"]}')
print(f'  新增: {stats["created"]}')
print(f'  更新: {stats["updated"]}')
print(f'  跳過: {stats["skipped"]}')
print(f'  錯誤: {stats["errors"]}')
print('')

# 更新 Server 統計
server.total_leases = DHCPLease.objects.filter(server=server).count()
server.active_leases = DHCPLease.objects.filter(server=server, is_active=True).count()
server.last_sync_at = timezone.now()
server.save()

print(f'✓ Server 統計已更新:')
print(f'  總租約數: {server.total_leases}')
print(f'  活躍租約: {server.active_leases}')
print('')

# 顯示樣本
print('前 5 筆樣本:')
samples = DHCPLease.objects.filter(server=server).order_by('-updated_at')[:5]
for lease in samples:
    print(f'  IP: {lease.ip_address:15} | MAC: {lease.mac_address:17} | Hostname: {lease.hostname or "(無)"}')

print('')
print('✓ 匯入完成！')
EOFPYTHON

# 執行 Python 腳本
docker exec -i nt-django python manage.py shell < /tmp/import_leases.py -- "$SERVER_ID"

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  匯入成功！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${YELLOW}下一步:${NC}"
    echo "  1. 訪問前端: http://localhost"
    echo "  2. 進入「DHCP 分析」頁面"
    echo "  3. 查看租約列表和日誌分析"
    echo ""
    
    # 清理臨時文件
    docker exec nt-django rm -f /tmp/dhcp_leases.json
    rm -f /tmp/import_leases.py
else
    echo ""
    echo -e "${RED}✗ 匯入失敗${NC}"
    exit 1
fi
