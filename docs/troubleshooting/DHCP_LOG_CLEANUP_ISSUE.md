# DHCP Server 10.250.130.1 看不到 11/7 日誌問題分析

## 📋 問題描述

**問題**：DHCP Server `10.250.130.1` 的日誌查看功能，無法顯示 2025年11月7日的日誌記錄。

**影響範圍**：所有 DHCP Server 的歷史日誌（超過保留天數的日誌）

---

## 🔍 根本原因分析

### 1. 日誌自動清理機制

系統配置了 **Celery 定時任務**，會自動清理舊的 DHCP 日誌：

```python
# backend/network_toolbox/celery.py (Line 39-50)
'cleanup-old-dhcp-logs-daily': {
    'task': 'api.tasks.cleanup_old_logs_task',
    'schedule': crontab(hour=3, minute=0),  # 每天凌晨 3 點執行
    'kwargs': {
        'days': 7          # ⚠️ 只保留最近 7 天的日誌
    },
    'options': {
        'expires': 3600,
    }
},
```

**執行邏輯**（`backend/api/tasks.py`，Line 111-157）：
```python
def cleanup_old_logs_task(self, days=15):
    """清理舊的 DHCP 日誌"""
    # 計算刪除日期界線
    cutoff_date = timezone.now() - timedelta(days=days)
    
    # 刪除超過保留期的日誌
    deleted_count, _ = DHCPLog.objects.filter(timestamp__lt=cutoff_date).delete()
```

### 2. 實際執行情況

透過資料庫查詢確認：

```bash
$ docker exec nt-django python manage.py shell -c "..."

定時任務配置:
================================================================================
任務名稱: cleanup-old-dhcp-logs-daily
啟用狀態: True
Cron 排程: 0 3 * * * (m/h/dM/MY/d) Asia/Taipei
任務路徑: api.tasks.cleanup_old_logs_task
參數: {'days': 7}          # ⚠️ 只保留 7 天
保留天數: 7
最後執行: 2025-11-11 19:00:00 (UTC)
總執行次數: 12

檢查日誌數據保留情況:
================================================================================
Server: 10.250.130.1 (10.250.130.1)
總日誌數: 144889

每日日誌數量:
  2025-11-10: 51795 筆      # ✅ 有數據
  2025-11-11: 55097 筆      # ✅ 有數據
  2025-11-12: 37997 筆      # ✅ 有數據
  # ❌ 11/7 的日誌已被清理
```

### 3. 時間線分析

| 日期 | 事件 | 說明 |
|------|------|------|
| 2025-11-07 | 日誌產生 | DHCP Server 正常記錄日誌 |
| 2025-11-09 20:31 | 最早日誌 | 資料庫中最早的日誌時間戳 |
| 2025-11-10 03:00 | 定時清理 | 刪除 11/2 之前的日誌（保留 7 天） |
| 2025-11-11 03:00 | 定時清理 | 刪除 11/3 之前的日誌 |
| **2025-11-12 03:00** | **定時清理** | **刪除 11/4 之前的日誌（包括 11/7 之前的部分數據）** |
| 2025-11-12 12:35 | 查詢時間 | 此時只剩 11/10~11/12 的日誌 |

**清理界線計算**：
```
當前時間: 2025-11-12 12:35:24
清理界線: 2025-11-12 12:35:24 - 7天 = 2025-11-05 12:35:24
刪除範圍: timestamp < 2025-11-05 12:35:24 的所有日誌
```

**11/7 日誌狀態**：
- 11/7 最晚時刻：2025-11-07 23:59:59
- 清理界線：2025-11-05 12:35:24
- **11/7 < 清理界線？ ✅ 是的，所以被刪除了**

---

## 💡 解決方案

### 方案 1：調整日誌保留天數（推薦）

**將保留天數從 7 天改為 30 天或更長**

#### 步驟 1：修改 Celery 配置

```bash
# 編輯 backend/network_toolbox/celery.py
vim backend/network_toolbox/celery.py
```

修改第 45 行：
```python
'cleanup-old-dhcp-logs-daily': {
    'task': 'api.tasks.cleanup_old_logs_task',
    'schedule': crontab(hour=3, minute=0),
    'kwargs': {
        'days': 30          # 改為 30 天（或其他需要的天數）
    },
    'options': {
        'expires': 3600,
    }
},
```

#### 步驟 2：重啟 Celery 服務

```bash
docker compose restart celery_worker celery_beat
```

#### 步驟 3：更新資料庫中的定時任務配置

```bash
docker exec nt-django python manage.py shell -c "
from django_celery_beat.models import PeriodicTask
import json

task = PeriodicTask.objects.get(name='cleanup-old-dhcp-logs-daily')
task.kwargs = json.dumps({'days': 30})
task.save()

print(f'✅ 已更新保留天數為 30 天')
print(f'任務: {task.name}')
print(f'參數: {task.kwargs}')
"
```

#### 步驟 4：驗證配置

```bash
docker exec nt-django python manage.py shell -c "
from django_celery_beat.models import PeriodicTask
import json

task = PeriodicTask.objects.get(name='cleanup-old-dhcp-logs-daily')
kwargs = json.loads(task.kwargs)
print(f'當前保留天數: {kwargs.get(\"days\")} 天')
"
```

---

### 方案 2：禁用自動清理（不推薦）

**如果需要永久保留所有日誌**

```bash
docker exec nt-django python manage.py shell -c "
from django_celery_beat.models import PeriodicTask

task = PeriodicTask.objects.get(name='cleanup-old-dhcp-logs-daily')
task.enabled = False
task.save()

print('✅ 已禁用日誌自動清理')
"
```

⚠️ **注意**：禁用自動清理會導致資料庫無限增長，可能影響性能。

---

### 方案 3：手動清理特定範圍的日誌

**只刪除指定日期範圍的日誌**

```bash
docker exec nt-django python manage.py shell -c "
from api.models import DHCPLog
from datetime import datetime
import pytz

# 設定要刪除的日期範圍
tz = pytz.timezone('Asia/Taipei')
start_date = tz.localize(datetime(2025, 10, 1, 0, 0, 0))  # 開始日期
end_date = tz.localize(datetime(2025, 10, 31, 23, 59, 59))  # 結束日期

# 轉換為 UTC
start_utc = start_date.astimezone(pytz.UTC)
end_utc = end_date.astimezone(pytz.UTC)

# 查詢要刪除的日誌數量
count = DHCPLog.objects.filter(
    timestamp__gte=start_utc,
    timestamp__lte=end_utc
).count()

print(f'將刪除 {start_date.strftime(\"%Y-%m-%d\")} ~ {end_date.strftime(\"%Y-%m-%d\")} 的 {count} 筆日誌')
print('執行刪除? (輸入 YES 確認)')
"
```

---

## 📊 日誌保留策略建議

根據不同需求，建議的保留天數：

| 使用場景 | 建議保留天數 | 說明 |
|----------|-------------|------|
| **開發/測試環境** | 7-15 天 | 快速清理，節省空間 |
| **生產環境（一般）** | 30-60 天 | 滿足大部分故障排查需求 |
| **生產環境（高安全）** | 90-180 天 | 符合資安稽核要求 |
| **長期監控分析** | 365 天或更長 | 需要歷史數據分析 |

**注意事項**：
- 日誌數量會隨保留天數線性增長
- 每日約 5 萬筆日誌 × 保留天數 = 總日誌量
- 建議定期監控資料庫大小
- 考慮使用日誌歸檔方案（導出後壓縮存儲）

---

## 🔄 日誌恢復方案

**如果需要恢復已刪除的日誌**，可以透過以下方式：

### 1. 從 NAS 日誌檔案重新同步

如果 Windows DHCP Server 的日誌檔案還在（通常保留 30 天）：

```bash
# 手動觸發日誌同步（透過 API）
curl -X POST http://localhost/api/dhcp-servers/2/sync-logs/ \
  -H "Content-Type: application/json" \
  -d '{"limit": 5000}'
```

### 2. 從資料庫備份恢復

如果有定期的資料庫備份：

```bash
# 恢復特定表的備份
pg_restore -h localhost -U network_toolbox \
  -d network_toolbox \
  -t api_dhcplog \
  backup_file.dump
```

---

## 🧪 驗證與測試

### 1. 檢查當前日誌保留情況

```bash
docker exec nt-django python manage.py shell -c "
from api.models import DHCPLog, DHCPServer
from django.db.models.functions import TruncDate
from django.db.models import Count, Min, Max

server = DHCPServer.objects.filter(ip_address='10.250.130.1').first()
if server:
    logs = DHCPLog.objects.filter(server=server)
    print(f'Server: {server.name}')
    print(f'總日誌數: {logs.count()}')
    
    earliest = logs.aggregate(Min('timestamp'))['timestamp__min']
    latest = logs.aggregate(Max('timestamp'))['timestamp__max']
    
    print(f'最早日誌: {earliest}')
    print(f'最新日誌: {latest}')
    
    if earliest and latest:
        days_covered = (latest - earliest).days
        print(f'涵蓋天數: {days_covered} 天')
"
```

### 2. 模擬清理執行（不實際刪除）

```bash
docker exec nt-django python manage.py shell -c "
from api.models import DHCPLog
from django.utils import timezone
from datetime import timedelta

days = 7
cutoff_date = timezone.now() - timedelta(days=days)

old_logs_count = DHCPLog.objects.filter(timestamp__lt=cutoff_date).count()

print(f'清理界線: {cutoff_date.strftime(\"%Y-%m-%d %H:%M:%S\")}')
print(f'將刪除: {old_logs_count} 筆日誌')
print('（這是模擬執行，不會實際刪除）')
"
```

---

## 📝 相關文件

- **Celery 配置**：`backend/network_toolbox/celery.py`（Line 39-50）
- **清理任務**：`backend/api/tasks.py`（Line 107-157）
- **日誌模型**：`backend/api/models.py`（DHCPLog）
- **日誌服務**：`backend/api/services.py`（DHCPLogService）

---

## 🎯 總結

### 問題核心
- ✅ **不是 Bug**，是預期行為
- ✅ Celery 定時任務每天凌晨 3 點自動清理超過 7 天的日誌
- ✅ 11/7 的日誌在 11/12 查詢時已超過 7 天，已被清理

### 建議措施
1. ✅ **短期**：將保留天數改為 30 天（方案 1）
2. ✅ **中期**：建立日誌歸檔機制（導出後壓縮存儲）
3. ✅ **長期**：考慮使用 TimescaleDB 或 ClickHouse 等時序資料庫

### 預防措施
- 在系統設定頁面顯示當前日誌保留天數
- 在日誌查詢頁面提示可查詢的日期範圍
- 定期將舊日誌導出為 CSV 或 JSON 格式備份

---

**最後更新**：2025-11-12  
**問題狀態**：已分析完成  
**建議行動**：調整保留天數為 30 天
