#!/bin/bash
# IPXE Server 網路品質檢測 Cron 腳本
# 每 5 分鐘執行一次

# 進入專案目錄
cd /home/owner/Codes/network-toolbox

# 在 Django 容器中執行 IPXE 網路品質檢測
# Server ID = 1 (IPXE Server 50: 10.250.50.2)
docker exec nt-django python manage.py shell -c "
from api.ipxe_network_service import record_ipxe_network_quality
record_ipxe_network_quality(server_id=1)
" >> /home/owner/Codes/network-toolbox/logs/ipxe_network_cron.log 2>&1
