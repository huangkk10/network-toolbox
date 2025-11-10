# DHCP 日誌保留策略

## 📋 概述

本系統對 DHCP Server 日誌實施了**自動清理機制**，以確保資料庫不會無限增長，同時保留足夠的歷史數據供分析使用。

---

## ⏰ 保留策略

### 📅 保留時間
- **保留天數**: **15 天**
- **刪除界線**: 早於 15 天前的日誌會被自動刪除
- **當前界線**: 2025-10-26（自動計算）

### 🕐 清理排程
- **執行時間**: 每天凌晨 **3:00 AM**（Asia/Taipei 時區）
- **執行頻率**: 每日一次
- **任務名稱**: `cleanup-old-dhcp-logs-daily`

---

## 🔧 技術實現

### 1. 資料庫模型

**檔案**: `backend/api/models.py`

```python
class DHCPLog(models.Model):
    """DHCP 日誌模型 - 15天滾動視窗"""
    
    server = models.ForeignKey(DHCPServer, ...)
    timestamp = models.DateTimeField(db_index=True)  # ✅ 已建立索引，加速查詢
    level = models.CharField(max_length=10, db_index=True)
    message = models.CharField(max_length=200)
    raw = models.TextField()
    client_type = models.CharField(max_length=20, db_index=True)
    # ... 其他欄位
```

### 2. Celery 清理任務

**檔案**: `backend/api/tasks.py`

```python
@shared_task(
    bind=True,
    name='api.tasks.cleanup_old_logs_task',
    time_limit=3600,      # 硬限制 1 小時
    soft_time_limit=3300  # 軟限制 55 分鐘
)
def cleanup_old_logs_task(self, days=15):
    """清理舊的 DHCP 日誌"""
    
    # 計算刪除界線
    cutoff_date = timezone.now() - timedelta(days=days)
    
    # 刪除舊日誌
    deleted_count, _ = DHCPLog.objects.filter(
        timestamp__lt=cutoff_date
    ).delete()
    
    logger.info(f'清理完成 - 刪除: {deleted_count} 筆')
    
    return {
        'deleted_count': deleted_count,
        'cutoff_date': cutoff_date.strftime('%Y-%m-%d %H:%M:%S'),
        'days': days
    }
```

### 3. 定期任務配置

**任務資訊**:
- **名稱**: `cleanup-old-dhcp-logs-daily`
- **Celery 任務**: `api.tasks.cleanup_old_logs_task`
- **啟用狀態**: ✅ 已啟用
- **排程**: `0 3 * * *` (Cron 表達式)
  - 分鐘: 0
  - 小時: 3 (凌晨 3 點)
  - 每天執行

**配置位置**: Django Celery Beat 定期任務表

---

## 📊 當前統計（2025-11-10）

### 資料庫狀態

| Server | 總日誌數 | 保留範圍內 | 待清理 | 最舊日誌 | 最新日誌 |
|--------|---------|-----------|--------|---------|---------|
| 10.250.120.1 | 5,234 | 5,234 | 0 | 2025-11-09 20:23 | 2025-11-10 00:29 |
| 10.250.71.1 | 936 | 936 | 0 | 2025-11-06 22:15 | 2025-11-10 00:15 |
| 10.250.130.1 | 11,999 | 11,999 | 0 | 2025-11-09 20:31 | 2025-11-10 00:30 |
| 10.250.50.1 | 2,012 | 2,012 | 0 | 2025-11-09 17:25 | 2025-11-10 00:25 |

**總計**: 20,181 筆日誌（全部在保留範圍內）

### 刪除界線
- **當前界線**: 2025-10-26 00:36:27
- **說明**: 早於此時間的日誌會在下次清理任務執行時被刪除

---

## 🔍 監控與驗證

### 1. 檢查定期任務狀態

```bash
docker exec nt-django python manage.py shell -c "
from django_celery_beat.models import PeriodicTask
task = PeriodicTask.objects.get(name='cleanup-old-dhcp-logs-daily')
print(f'任務: {task.task}')
print(f'啟用: {task.enabled}')
print(f'排程: {task.crontab}')
"
```

### 2. 查看清理日誌

```bash
# 查看 Django 日誌中的清理記錄
grep "清理 DHCP 舊日誌" logs/django.log

# 查看 Celery 日誌
docker compose logs celery_worker | grep "cleanup_old_logs"
```

### 3. 手動觸發清理任務（測試用）

```bash
docker exec nt-django python manage.py shell -c "
from api.tasks import cleanup_old_logs_task
result = cleanup_old_logs_task.delay(days=15)
print(f'任務 ID: {result.id}')
"
```

### 4. 檢查資料庫日誌統計

```bash
docker exec nt-django python manage.py shell -c "
from api.models import DHCPLog
from django.utils import timezone
from datetime import timedelta

cutoff_date = timezone.now() - timedelta(days=15)
total = DHCPLog.objects.count()
old = DHCPLog.objects.filter(timestamp__lt=cutoff_date).count()

print(f'總日誌數: {total:,}')
print(f'待清理: {old:,}')
print(f'保留: {total - old:,}')
"
```

---

## ⚙️ 調整保留天數

### 方法一：修改任務參數（推薦）

```bash
docker exec nt-django python manage.py shell -c "
from django_celery_beat.models import PeriodicTask
import json

task = PeriodicTask.objects.get(name='cleanup-old-dhcp-logs-daily')

# 修改保留天數（例如改為 30 天）
task.kwargs = json.dumps({'days': 30})
task.save()

print('✅ 保留天數已更新為 30 天')
"
```

### 方法二：修改代碼（需重啟）

**檔案**: `backend/api/tasks.py`

```python
def cleanup_old_logs_task(self, days=30):  # 修改預設值
    """清理舊的 DHCP 日誌"""
    # ...
```

修改後需要重啟 Django 和 Celery：
```bash
docker compose restart django celery_worker celery_beat
```

---

## 📈 效能考量

### 資料庫索引
- ✅ `timestamp` 欄位已建立索引
- ✅ `server` 外鍵自動建立索引
- ✅ `level` 和 `client_type` 欄位已建立索引

### 刪除效能
- **預期刪除速度**: ~1,000 筆/秒（依硬體而定）
- **時間限制**: 軟限制 55 分鐘，硬限制 1 小時
- **建議**: 如果日誌量極大（> 100 萬筆/天），考慮：
  1. 增加清理頻率（每 12 小時一次）
  2. 分批刪除（每次刪除固定數量）
  3. 使用分區表（PostgreSQL Partitioning）

---

## 🚨 故障排查

### 問題 1: 清理任務未執行

**檢查步驟**:
```bash
# 1. 檢查 Celery Beat 是否運行
docker compose ps celery_beat

# 2. 檢查任務是否啟用
docker exec nt-django python manage.py shell -c "
from django_celery_beat.models import PeriodicTask
task = PeriodicTask.objects.get(name='cleanup-old-dhcp-logs-daily')
print(f'啟用: {task.enabled}')
"

# 3. 查看 Celery Beat 日誌
docker compose logs celery_beat --tail 100
```

### 問題 2: 舊日誌未被刪除

**可能原因**:
1. 時區設定錯誤（檢查 `settings.py` 的 `TIME_ZONE`）
2. 日誌時間戳使用 naive datetime（應使用 timezone-aware）
3. 清理任務執行失敗

**檢查**:
```bash
# 手動執行清理任務
docker exec nt-django python manage.py shell -c "
from api.tasks import cleanup_old_logs_task
result = cleanup_old_logs_task(days=15)
print(result)
"
```

### 問題 3: 資料庫空間未釋放

**PostgreSQL 需要 VACUUM**:
```bash
docker exec nt-postgres psql -U network_toolbox -c "VACUUM FULL api_dhcplog;"
```

---

## 📚 相關文檔

- [Celery 定期任務文檔](../scheduled-tasks/README.md)
- [DHCP 日誌時區修復](../../../DHCP_TIMEZONE_FIX.md)
- [資料庫優化指南](../../deployment/DATABASE_OPTIMIZATION.md)

---

## 📝 變更歷史

| 日期 | 版本 | 變更內容 |
|-----|------|---------|
| 2025-11-10 | 1.0 | 初始版本 - 記錄 15 天保留策略 |

---

**維護者**: Network Toolbox Team  
**最後更新**: 2025-11-10
