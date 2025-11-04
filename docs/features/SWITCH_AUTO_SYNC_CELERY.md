# Switch 自動識別 - Celery 定時任務配置指南

## 📋 功能概述

Network Toolbox 現在支援使用 **Celery** 定時自動識別和更新 Switch 資訊！

### ✨ 主要功能

- ✅ **自動識別**：根據 MAC 地址製造商自動識別 Switch 設備
- ✅ **定時更新**：每小時自動執行，保持資料最新
- ✅ **多 Server 支援**：自動處理所有 DHCP Server
- ✅ **失敗重試**：自動重試機制，確保任務成功
- ✅ **詳細日誌**：完整的執行日誌和統計資訊

## 🚀 快速開始

### 1. 確認所有服務正在運行

```bash
# 確認服務狀態
docker-compose ps

# 應該看到以下服務都在 Up 狀態：
# - nt-django (Django Web 服務)
# - nt-celery-worker (Celery 任務執行器)  
# - nt-celery-beat (Celery 排程器)
# - nt-postgres (PostgreSQL 資料庫)
# - nt-redis (Celery Broker)
# - nt-nginx (反向代理)
```

**✅ 已完成部署！自動識別功能已啟用，每小時自動執行。**

### 2. 查看 Celery 狀態

```bash
# 查看 Worker 狀態
docker exec nt-celery-worker celery -A network_toolbox inspect active

# 查看已註冊的任務
docker exec nt-celery-worker celery -A network_toolbox inspect registered

# 查看排程任務
docker exec nt-celery-beat celery -A network_toolbox inspect scheduled
```

### 3. 查看執行日誌

```bash
# 查看 Celery Worker 日誌（任務執行記錄）
docker logs -f nt-celery-worker

# 查看 Celery Beat 日誌（排程記錄）
docker logs -f nt-celery-beat

# 過濾 Switch 相關日誌
docker logs nt-celery-worker 2>&1 | grep -A 10 "Switch"

# 查看最近的任務執行結果
docker logs --tail 50 nt-celery-worker | grep "Switch 自動識別完成"
```

**範例輸出**：
```
[2025-11-02 13:22:40] [Celery] 開始自動識別 Switch - Server ID: All
[2025-11-02 13:22:41] [Celery] Server 10.250.71.1 完成 - 創建: 0, 更新: 0
[2025-11-02 13:22:41] [Celery] Server 10.250.130.1 完成 - 創建: 0, 更新: 13
[2025-11-02 13:22:41] [Celery] Server 10.250.50.1 完成 - 創建: 0, 更新: 9
[2025-11-02 13:22:41] [Celery] Switch 自動識別完成 - 處理: 3 | 創建: 0 | 更新: 22
```

## ⏰ 定時任務配置

### 任務排程

已在 `backend/network_toolbox/celery.py` 中配置：

```python
'auto-identify-switches-hourly': {
    'task': 'api.tasks.auto_identify_switches_task',
    'schedule': crontab(minute=0),  # 每小時整點執行
    'kwargs': {
        'server_id': None  # None 表示處理所有 Server
    },
    'options': {
        'expires': 540,    # 任務超時 9 分鐘
    }
}
```

### 執行時間

- **頻率**：每小時整點執行（例如：00:00, 01:00, 02:00...）
- **範圍**：自動處理所有 DHCP Server
- **超時**：9 分鐘（如果超時會自動重試）

### 修改排程頻率

如果您想調整執行頻率，編輯 `backend/network_toolbox/celery.py`：

```python
# 每 30 分鐘執行一次
'schedule': crontab(minute='*/30'),

# 每天凌晨 2 點執行
'schedule': crontab(hour=2, minute=0),

# 每週一凌晨 3 點執行
'schedule': crontab(day_of_week=1, hour=3, minute=0),
```

修改後重啟 Celery Beat：

```bash
docker-compose restart nt-celery-beat
```

## 🔧 手動執行任務

### 透過 Django Shell

```bash
docker exec -it nt-django python manage.py shell
```

```python
from api.tasks import auto_identify_switches_task

# 立即執行（所有 Server）
result = auto_identify_switches_task.delay()

# 執行特定 Server
result = auto_identify_switches_task.delay(server_id=2)

# 查看任務 ID
print(result.id)

# 查看任務狀態
print(result.status)

# 等待任務完成並獲取結果（最多等待 600 秒）
result_data = result.get(timeout=600)
print(result_data)
```

### 透過 Celery 命令

```bash
# 立即執行任務（所有 Server）
docker exec nt-celery-worker celery -A network_toolbox call api.tasks.auto_identify_switches_task

# 執行特定 Server
docker exec nt-celery-worker celery -A network_toolbox call api.tasks.auto_identify_switches_task --kwargs='{"server_id": 2}'
```

### 透過 Python 腳本（推薦用於測試）

```bash
# 使用現有的腳本
docker exec -it nt-django python auto_identify_switches.py

# 這個腳本會：
# 1. 立即執行（不需要等待排程）
# 2. 顯示詳細的進度和結果
# 3. 可以指定特定的 Server ID
```

## 📊 監控和日誌

### 查看任務執行歷史

```bash
# 查看最近的 Switch 識別任務日誌
docker exec nt-django python manage.py shell -c "
from django_celery_results.models import TaskResult
from datetime import timedelta
from django.utils import timezone

# 最近 24 小時的任務
recent_tasks = TaskResult.objects.filter(
    task_name='api.tasks.auto_identify_switches_task',
    date_done__gte=timezone.now() - timedelta(hours=24)
).order_by('-date_done')

for task in recent_tasks:
    print(f'{task.date_done}: {task.status} - {task.result[:100]}...')
"
```

### Django 日誌

任務執行記錄會寫入 Django 日誌：

```bash
# 查看今天的日誌
tail -f logs/django.log | grep "Switch"

# 查看錯誤日誌
tail -f logs/django_error.log
```

### 日誌格式

任務執行時會產生以下日誌：

```
[INFO] [Celery] 開始自動識別 Switch - Server ID: None
[INFO] [Celery] 處理 Server: 10.250.130.1 (ID: 2)
[INFO] [Celery] 找到 218 個活動租約
[INFO] [Celery] 識別到 13 台 Switch
[INFO] [Celery] 創建 Switch: VN53KYC0TB (10.250.133.12)
[INFO] [Celery] Server 10.250.130.1 完成 - 創建: 2, 更新: 11
[INFO] [Celery] Switch 自動識別完成 - 處理: 3 | 創建: 5 | 更新: 17
```

## 🎯 任務結果結構

任務完成後返回的結果格式：

```python
{
    'success': True,                    # 是否成功
    'servers_processed': 3,             # 處理的 Server 數量
    'total_switches_created': 5,        # 新創建的 Switch 數量
    'total_switches_updated': 17,       # 更新的 Switch 數量
    'results': [                        # 每個 Server 的詳細結果
        {
            'server_id': 2,
            'server_name': '10.250.130.1',
            'switches_found': 13,
            'switches_created': 2,
            'switches_updated': 11,
            'success': True
        },
        # ... 其他 Server
    ],
    'timestamp': '2025-11-02T12:00:00+08:00'
}
```

## 🔍 故障排查

### 任務沒有執行

1. **檢查 Celery Beat 是否運行**：
   ```bash
   docker-compose ps nt-celery-beat
   ```

2. **檢查 Celery Worker 是否運行**：
   ```bash
   docker-compose ps nt-celery-worker
   ```

3. **檢查 Redis 是否運行**：
   ```bash
   docker-compose ps redis
   ```

4. **重啟 Celery 服務**：
   ```bash
   docker-compose restart nt-celery-beat nt-celery-worker
   ```

### 任務執行失敗

1. **查看詳細錯誤日誌**：
   ```bash
   docker-compose logs nt-celery-worker | grep ERROR
   ```

2. **檢查 Django 錯誤日誌**：
   ```bash
   tail -50 logs/django_error.log
   ```

3. **手動執行測試**：
   ```bash
   docker exec -it nt-django python auto_identify_switches.py
   ```

### Redis 連接問題

```bash
# 測試 Redis 連接
docker exec nt-celery-worker python -c "
from celery import Celery
app = Celery('test', broker='redis://redis:6379/0')
print('Redis connection: OK')
"
```

## 📈 性能優化

### 調整 Worker 數量

如果有大量 DHCP Server，可以增加 Worker 數量：

編輯 `docker-compose.yml`：

```yaml
celery-worker:
  command: celery -A network_toolbox worker --loglevel=info --concurrency=4
```

重啟：

```bash
docker-compose up -d --force-recreate nt-celery-worker
```

### 調整任務超時

編輯 `backend/network_toolbox/celery.py`：

```python
@shared_task(
    time_limit=1200,  # 硬限制 20 分鐘
    soft_time_limit=1080  # 軟限制 18 分鐘
)
```

## 🎉 使用建議

1. **初次使用**：
   - 先手動執行一次確認功能正常
   - 檢查日誌確認 Switch 正確識別
   - 查看 Web 介面確認資料顯示正確

2. **日常使用**：
   - 讓 Celery 自動執行即可
   - 定期（每週）檢查日誌確認無錯誤
   - 新增 DHCP Server 後會自動被處理

3. **測試環境**：
   - 可以暫停定時任務：停止 `nt-celery-beat` 容器
   - 使用手動腳本測試新功能
   - 完成測試後重啟 Beat 容器

## 📞 需要協助？

如果遇到問題：

1. 檢查日誌檔案（`logs/` 目錄）
2. 查看 Celery Worker 輸出
3. 執行手動測試腳本確認功能
4. 檢查網路連接和權限設定

---

**文檔版本**：v1.0  
**最後更新**：2025-11-02  
**維護者**：Network Toolbox Team
