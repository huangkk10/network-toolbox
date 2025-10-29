# Celery 定時任務快速參考

## 🚀 當前運行的定時任務

### 每 5 分鐘執行
1. **DHCP 日誌同步** - `sync-dhcp-logs-every-5-minutes`
   - 任務: `api.tasks.sync_dhcp_logs_task`
   - 參數: `server_id=1, limit=500`

2. **NAS 連線檢測** - `check-nas-connection-every-5-minutes`
   - 任務: `api.tasks.check_nas_connection_task`
   - 監測 NAS 連接狀態、速度測試

3. **IPXE 網路品質檢測** - `check-ipxe-network-quality-every-5-minutes`
   - 任務: `api.tasks.check_ipxe_network_quality_task`
   - 參數: `server_id=1`
   - 監測 Ping、HTTP、SSH、下載速度

### 每天執行
4. **DHCP 日誌清理** - `cleanup-old-dhcp-logs-daily`
   - 任務: `api.tasks.cleanup_old_logs_task`
   - 時間: 每天 03:00
   - 參數: `days=7` (清理 7 天前的日誌)

### 每月執行
5. **OUI 資料庫更新** - `update-oui-database-monthly`
   - 任務: `api.tasks.update_oui_database_task`
   - 時間: 每月 1 號 02:00
   - 參數: `source=0, backup=True`

---

## 📊 監控命令

### 查看所有正在運行的任務
```bash
docker compose logs celery_worker --tail 100 | grep "Task.*received"
```

### 查看定時任務觸發日誌
```bash
docker compose logs celery_beat --tail 50 | grep "Scheduler:"
```

### 查看特定任務的日誌
```bash
# NAS 檢測
docker compose logs celery_worker | grep "check_nas_connection"

# IPXE 網路品質
docker compose logs celery_worker | grep "check_ipxe_network_quality"

# DHCP 日誌同步
docker compose logs celery_worker | grep "sync_dhcp_logs"
```

### 實時監控 Worker
```bash
docker compose logs celery_worker -f
```

### 實時監控 Beat
```bash
docker compose logs celery_beat -f
```

---

## 🛠️ 常用操作

### 重啟 Celery 服務
```bash
# 重啟 Worker（任務執行器）
docker compose restart celery_worker

# 重啟 Beat（任務調度器）
docker compose restart celery_beat

# 重啟所有 Celery 服務
docker compose restart celery_worker celery_beat celery_flower
```

### 手動執行任務

#### 方法 1: Django Shell
```bash
docker exec -it nt-django python manage.py shell
```
```python
# IPXE 網路品質檢測
from api.tasks import check_ipxe_network_quality_task
result = check_ipxe_network_quality_task.delay(1)
print(result.get())

# NAS 連線檢測
from api.tasks import check_nas_connection_task
result = check_nas_connection_task.delay()
print(result.get())

# DHCP 日誌同步
from api.tasks import sync_dhcp_logs_task
result = sync_dhcp_logs_task.delay(server_id=1, limit=500)
print(result.get())
```

#### 方法 2: Celery Flower Web UI
1. 訪問: http://localhost:5555
2. 點擊 "Tasks" 標籤
3. 選擇任務並點擊 "Execute"

### 查看任務執行結果

#### 使用 Django Admin
1. 訪問: http://localhost/admin/
2. 進入 "PERIODIC TASKS" 部分
3. 查看 "Task results"

#### 使用 Python 查詢
```python
from django_celery_results.models import TaskResult
from datetime import timedelta
from django.utils import timezone

# 查看最近 1 小時的任務結果
recent_results = TaskResult.objects.filter(
    date_created__gte=timezone.now() - timedelta(hours=1)
).order_by('-date_created')

for result in recent_results:
    print(f"{result.task_name}: {result.status} - {result.date_created}")
```

---

## 🔧 任務配置

### 修改任務排程
編輯文件: `/backend/network_toolbox/celery.py`

```python
app.conf.beat_schedule = {
    'check-ipxe-network-quality-every-5-minutes': {
        'task': 'api.tasks.check_ipxe_network_quality_task',
        'schedule': crontab(minute='*/5'),  # 修改這裡
        'kwargs': {
            'server_id': 1,
        },
        'options': {
            'expires': 150,
        }
    },
}
```

**Crontab 格式範例**：
```python
crontab(minute='*/5')              # 每 5 分鐘
crontab(minute=0, hour='*/2')      # 每 2 小時
crontab(hour=3, minute=0)          # 每天 03:00
crontab(day_of_week=1, hour=0)     # 每週一 00:00
crontab(day_of_month=1, hour=2)    # 每月 1 號 02:00
```

修改後重啟：
```bash
docker compose restart celery_beat
```

### 添加新的定時任務

#### 步驟 1: 創建任務函數
編輯: `/backend/api/tasks.py`

```python
@shared_task(
    bind=True,
    name='api.tasks.my_new_task',
    max_retries=3,
    default_retry_delay=60,
    time_limit=300,
    soft_time_limit=270
)
def my_new_task(self):
    """新任務描述"""
    try:
        logger.info('[Celery] 開始執行新任務')
        
        # 執行任務邏輯
        # ...
        
        logger.info('[Celery] 新任務執行完成')
        return {'success': True}
        
    except Exception as exc:
        logger.error('[Celery] 新任務執行失敗', exc_info=True)
        raise self.retry(exc=exc, countdown=60)
```

#### 步驟 2: 添加到排程
編輯: `/backend/network_toolbox/celery.py`

```python
app.conf.beat_schedule = {
    # ... 其他任務 ...
    
    'my-new-task-every-hour': {
        'task': 'api.tasks.my_new_task',
        'schedule': crontab(minute=0, hour='*/1'),  # 每小時
        'options': {
            'expires': 3000,
        }
    },
}
```

#### 步驟 3: 重啟服務
```bash
docker compose restart celery_worker celery_beat
```

---

## 📈 性能優化

### Worker 並發設置
編輯: `docker-compose.yml`

```yaml
celery_worker:
  command: celery -A network_toolbox worker --loglevel=info --concurrency=4  # 增加並發數
```

### 任務優先級隊列
```python
# 在 celery.py 中配置
app.conf.task_routes = {
    'api.tasks.check_ipxe_network_quality_task': {'queue': 'high_priority'},
    'api.tasks.cleanup_old_logs_task': {'queue': 'low_priority'},
}
```

啟動多個 Worker：
```bash
# 高優先級 Worker
celery -A network_toolbox worker -Q high_priority --concurrency=2

# 低優先級 Worker
celery -A network_toolbox worker -Q low_priority --concurrency=1
```

---

## 🚨 故障排查

### Worker 不執行任務
1. 檢查 Worker 是否運行：
   ```bash
   docker compose ps celery_worker
   ```

2. 檢查 Redis 連接：
   ```bash
   docker exec nt-redis redis-cli ping
   # 應該返回: PONG
   ```

3. 檢查任務是否在隊列中：
   ```bash
   docker exec nt-redis redis-cli -n 1 LLEN celery
   ```

4. 重啟 Worker：
   ```bash
   docker compose restart celery_worker
   ```

### Beat 不發送任務
1. 檢查 Beat 日誌：
   ```bash
   docker compose logs celery_beat --tail 100
   ```

2. 檢查數據庫中的定時任務：
   ```bash
   docker exec -it nt-django python manage.py shell
   ```
   ```python
   from django_celery_beat.models import PeriodicTask
   tasks = PeriodicTask.objects.all()
   for task in tasks:
       print(f"{task.name}: enabled={task.enabled}")
   ```

3. 重啟 Beat：
   ```bash
   docker compose restart celery_beat
   ```

### 任務執行失敗
1. 查看詳細錯誤：
   ```bash
   docker compose logs celery_worker | grep "ERROR"
   ```

2. 查看任務追蹤：
   - 訪問 Flower: http://localhost:5555
   - 進入 "Tasks" 標籤
   - 點擊失敗的任務查看詳情

3. 手動執行測試：
   ```python
   from api.tasks import check_ipxe_network_quality_task
   check_ipxe_network_quality_task(1)  # 同步執行
   ```

---

## 📚 相關資源

- **Celery 官方文檔**: https://docs.celeryproject.org/
- **django-celery-beat**: https://github.com/celery/django-celery-beat
- **Flower 監控**: http://localhost:5555
- **Django Admin**: http://localhost/admin/

---

**最後更新**: 2025-10-29
