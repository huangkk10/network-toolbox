#!/bin/bash
# IPXE Server 網路品質檢測 Cron 腳本
# 每 5 分鐘執行一次

# 進入專案目錄
cd /home/owner/Codes/network-toolbox

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 開始 IPXE 網路品質檢測..." >> /home/owner/Codes/network-toolbox/logs/ipxe_network_cron.log

# 在 Django 容器中執行 IPXE 網路品質檢測（所有 Server）
docker exec nt-django python manage.py shell -c "
from api.models import IPXEServer
from api.ipxe_network_service import record_ipxe_network_quality

# 獲取所有 IPXE Server
servers = IPXEServer.objects.all()
print(f'檢測 {servers.count()} 台 IPXE Server 的網路品質...')

for server in servers:
    print(f'  檢測 Server: {server.name} ({server.ip_address})')
    try:
        record_ipxe_network_quality(server_id=server.id)
        print(f'  ✓ {server.name} 檢測完成')
    except Exception as e:
        print(f'  ✗ {server.name} 檢測失敗: {e}')

print('所有 Server 檢測完成！')
" >> /home/owner/Codes/network-toolbox/logs/ipxe_network_cron.log 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] IPXE 網路品質檢測完成" >> /home/owner/Codes/network-toolbox/logs/ipxe_network_cron.log
echo "" >> /home/owner/Codes/network-toolbox/logs/ipxe_network_cron.log
