#!/bin/bash
# NAS 連線檢測 Cron 腳本
# 每 5 分鐘執行一次

# 進入專案目錄
cd /home/owner/Codes/network-toolbox

# 在 Django 容器中執行 NAS 檢測
docker exec nt-django python manage.py shell -c "
from api.nas_service import record_nas_connection
record_nas_connection()
" >> /home/owner/Codes/network-toolbox/logs/nas_cron.log 2>&1
