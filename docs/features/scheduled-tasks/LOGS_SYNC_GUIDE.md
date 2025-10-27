# DHCP 日誌同步指南

## 📌 重要說明

### Windows DHCP Server 日誌機制
- Windows DHCP Server 使用 **週循環日誌**
- 日誌檔案：`DhcpSrvLog-Mon.log` 到 `DhcpSrvLog-Sun.log`（7 個檔案）
- **每週覆蓋**：本週一的日誌會覆蓋上週一的日誌
- **只保留本週數據**：無法從 Windows Server 讀取上週或更早的日誌

### 資料庫 7 天滾動視窗
- 資料庫會保存最近 7 天的日誌
- **每天定時同步**可以累積歷史數據
- **即使 Windows Server 覆蓋了舊日誌，資料庫中仍有備份**

## ⚙️ 設定定時同步

### 方法 1：使用 Cron（推薦）

編輯 crontab：
```bash
crontab -e
```

添加以下行：
```cron
# 每 5 分鐘同步一次日誌
*/5 * * * * docker exec nt-django python manage.py sync_dhcp_logs --server 1 --limit 500

# 每天凌晨 3 點清理 7 天前的日誌
0 3 * * * docker exec nt-django python manage.py clean_old_logs --days 7
```

### 方法 2：使用 systemd timer

創建服務文件 `/etc/systemd/system/dhcp-log-sync.service`：
```ini
[Unit]
Description=DHCP Log Sync Service
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/bin/docker exec nt-django python manage.py sync_dhcp_logs --server 1 --limit 500
User=owner
```

創建定時器文件 `/etc/systemd/system/dhcp-log-sync.timer`：
```ini
[Unit]
Description=DHCP Log Sync Timer
Requires=dhcp-log-sync.service

[Timer]
OnBootSec=5min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
```

啟用定時器：
```bash
sudo systemctl daemon-reload
sudo systemctl enable dhcp-log-sync.timer
sudo systemctl start dhcp-log-sync.timer
```

## 📊 數據累積時程表

| 時間 | Windows Server | 資料庫 | 說明 |
|------|----------------|--------|------|
| 第 1 天 | 1 天 | 1 天 | 首次同步 |
| 第 2 天 | 2 天 | 2 天 | 累積中 |
| 第 7 天 | 7 天 | 7 天 | 達到完整 7 天 |
| 第 8 天 | 7 天（週循環）| 7 天 | 開始清理第 1 天的數據 |
| 第 14 天 | 7 天（週循環）| 7 天 | 穩定狀態（滾動視窗）|

## 🔍 驗證同步狀態

### 查看資料庫中的日誌分佈
```bash
docker exec nt-django python manage.py shell << 'EOF'
from api.models import DHCPLog
from django.db.models import Count
from django.db.models.functions import TruncDate

logs = DHCPLog.objects.all()
print(f'總日誌數: {logs.count()}')

by_date = logs.annotate(date=TruncDate('timestamp')).values('date').annotate(count=Count('id')).order_by('date')
print('\n按日期統計:')
for item in by_date:
    print(f'  {item["date"]}: {item["count"]} 筆')
EOF
```

### 查看最近一次同步結果
```bash
docker exec nt-django python manage.py sync_dhcp_logs --server 1 --limit 1000
```

## 🚨 常見問題

### Q: 為什麼資料庫只有今天的日誌？
A: 首次同步時，Windows Server 上可能只有今天的數據。需要持續同步幾天後，資料庫才會累積歷史數據。

### Q: 如何手動補充歷史數據？
A: 無法從 Windows Server 讀取已被覆蓋的日誌。建議：
   - 立即啟用定時同步
   - 等待 7 天讓資料庫自然累積

### Q: 同步頻率建議？
A: 
   - **生產環境**：每 5 分鐘（避免遺漏數據）
   - **測試環境**：每 15-30 分鐘

### Q: 清理頻率建議？
A:
   - 每天一次即可（凌晨 3 點）
   - 使用 `--dry-run` 參數測試

## 📈 監控建議

監控以下指標：
- ✅ 每次同步新增的日誌數量
- ✅ 資料庫中總日誌數量
- ✅ 最早和最新日誌的時間
- ✅ 磁碟空間使用情況（預期 1.74 MB / 7 days）

## 🎯 最佳實踐

1. **立即啟用定時同步**（不要等待）
2. **每 5 分鐘同步一次**（確保不遺漏數據）
3. **監控同步狀態**（檢查日誌文件）
4. **定期備份資料庫**（PostgreSQL dump）
5. **測試清理腳本**（使用 --dry-run）

---

**建立日期**：2025-10-28  
**維護者**：Network Toolbox Team
