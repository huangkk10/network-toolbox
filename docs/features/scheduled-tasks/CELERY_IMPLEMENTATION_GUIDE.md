# 🎯 Celery 實施指南（方案 B）

## ✅ 已完成的配置

以下文件已經全部配置完成：

### 1. Python 依賴 (`backend/requirements.txt`)
```
✅ celery==5.3.4
✅ redis==5.0.1
✅ django-celery-beat==2.5.0
✅ django-celery-results==2.5.1
✅ flower==2.0.1
```

### 2. Celery 配置文件 (`backend/network_toolbox/celery.py`)
- ✅ Celery 應用實例
- ✅ 定時任務排程配置
  - 每 5 分鐘同步 DHCP 日誌
  - 每天凌晨 3 點清理舊日誌
- ✅ Worker 配置

### 3. Django 初始化 (`backend/network_toolbox/__init__.py`)
- ✅ Celery 自動載入配置

### 4. Celery 任務 (`backend/api/tasks.py`)
- ✅ `sync_dhcp_logs_task` - 同步任務（含自動重試）
- ✅ `cleanup_old_logs_task` - 清理任務
- ✅ `get_logs_statistics_task` - 統計任務（示範用）

### 5. Django Settings (`backend/network_toolbox/settings.py`)
- ✅ 添加 `django_celery_beat` 到 INSTALLED_APPS
- ✅ 添加 `django_celery_results` 到 INSTALLED_APPS
- ✅ Redis 連接配置
- ✅ Celery Broker 配置
- ✅ Celery Result Backend 配置
- ✅ DatabaseScheduler 配置

### 6. Docker Compose (`docker-compose.yml`)
- ✅ Redis 服務（port 6379）
- ✅ Celery Beat 服務（定時調度器）
- ✅ Celery Worker 服務（任務執行器）
- ✅ Celery Flower 服務（Web 監控，port 5555）
- ✅ redis_data Volume（數據持久化）

---

## 🚀 剩餘步驟（請手動執行）

### 步驟 1：啟動所有容器

```bash
cd /home/owner/Codes/network-toolbox
docker compose up -d --build
```

**預期結果**：
```
✔ Container nt-postgres          Running
✔ Container nt-redis              Running
✔ Container nt-adminer            Running
✔ Container nt-django             Running
✔ Container nt-react              Running
✔ Container nt-celery-beat        Running
✔ Container nt-celery-worker      Running
✔ Container nt-celery-flower      Running
✔ Container nt-nginx              Running
```

### 步驟 2：執行資料庫遷移（生成 Celery 表）

```bash
# 遷移 django-celery-beat 表（定時任務排程）
docker exec nt-django python manage.py migrate django_celery_beat

# 遷移 django-celery-results 表（任務結果存儲）
docker exec nt-django python manage.py migrate django_celery_results
```

**預期輸出**：
```
Operations to perform:
  Apply all migrations: django_celery_beat
Running migrations:
  Applying django_celery_beat.0001_initial... OK
  Applying django_celery_beat.0002_... OK
  ...
```

### 步驟 3：驗證容器運行狀態

```bash
# 查看所有容器狀態
docker compose ps

# 查看 Celery Worker 日誌
docker compose logs celery_worker --tail 50

# 查看 Celery Beat 日誌
docker compose logs celery_beat --tail 50

# 查看 Redis 日誌
docker compose logs redis --tail 20
```

**預期 Celery Worker 日誌**：
```
celery@... ready.
Connected to redis://redis:6379/1
```

**預期 Celery Beat 日誌**：
```
DatabaseScheduler: Schedule changed.
Scheduler: Sending due task sync-dhcp-logs-every-5-minutes
```

### 步驟 4：訪問 Flower 監控界面

在瀏覽器打開：**http://localhost:5555**

您應該看到：
- ✅ **Dashboard**：顯示 Worker 狀態、任務統計
- ✅ **Tasks**：顯示所有任務列表
- ✅ **Workers**：顯示 Worker 狀態（應該有 1 個 Worker 運行中）
- ✅ **Broker**：Redis 連接狀態

### 步驟 5：測試手動執行任務

```bash
# 進入 Django Shell
docker exec -it nt-django python manage.py shell

# 手動觸發同步任務
from api.tasks import sync_dhcp_logs_task
result = sync_dhcp_logs_task.delay(server_id=1, limit=100)
print(f'Task ID: {result.task_id}')
print(f'Task State: {result.state}')

# 等待任務完成
result.wait(timeout=30)
print(f'Result: {result.result}')

# 退出
exit()
```

**預期結果**：
```python
Task ID: abcd-1234-...
Task State: PENDING
Result: {
    'server_id': 1,
    'server_name': 'Windows DHCP Server',
    'total': 100,
    'created': 5,
    'skipped': 95,
    'errors': 0
}
```

### 步驟 6：驗證定時任務運行

```bash
# 查看 Celery Beat 排程
docker exec nt-django python manage.py shell << 'EOF'
from django_celery_beat.models import PeriodicTask
tasks = PeriodicTask.objects.all()
for task in tasks:
    print(f'{task.name}: {task.enabled} - {task.crontab}')
EOF

# 等待 5 分鐘，查看是否自動同步
sleep 300
docker compose logs celery_worker --tail 100 | grep "sync_dhcp_logs_task"
```

**預期輸出**：
```
sync-dhcp-logs-every-5-minutes: True - */5 * * * * (每 5 分鐘)
cleanup-old-dhcp-logs-daily: True - 0 3 * * * (每天 3:00 AM)

[任務日誌]
Received task: api.tasks.sync_dhcp_logs_task
Task api.tasks.sync_dhcp_logs_task succeeded
```

### 步驟 7：查看資料庫中的任務結果

```bash
docker exec nt-django python manage.py shell << 'EOF'
from django_celery_results.models import TaskResult
results = TaskResult.objects.all().order_by('-date_done')[:10]
for r in results:
    print(f'{r.task_name} | {r.status} | {r.date_done}')
EOF
```

---

## 📊 Flower 監控功能說明

### Dashboard（首頁）
- **Workers**：查看 Worker 數量、狀態
- **Active Tasks**：正在執行的任務
- **Processed**：已處理任務數量
- **Failed**：失敗任務數量

### Tasks（任務列表）
- **All Tasks**：所有歷史任務
- **可搜尋**：按任務名稱、狀態搜尋
- **可點擊**：查看單個任務詳細資訊（參數、結果、執行時間）

### Workers（工作進程）
- **Status**：Worker 狀態（Online/Offline）
- **Concurrency**：並發數（當前設定為 2）
- **Processed Tasks**：已處理任務統計
- **Resource Usage**：CPU、記憶體使用情況

### Monitor（實時監控）
- **任務執行狀態**：即時更新
- **執行時間圖表**：任務耗時統計
- **成功率**：任務成功/失敗比例

---

## 🛠️ 常用管理命令

### 查看任務排程

```bash
# 方式 1：Django Admin
# 訪問 http://localhost/admin/
# 登入後進入 "Periodic tasks" 管理界面

# 方式 2：命令行
docker exec nt-django python manage.py shell
>>> from django_celery_beat.models import PeriodicTask, CrontabSchedule
>>> PeriodicTask.objects.all().values('name', 'enabled', 'crontab')
```

### 修改任務排程

```bash
docker exec nt-django python manage.py shell << 'EOF'
from django_celery_beat.models import PeriodicTask, CrontabSchedule

# 修改同步頻率（5分鐘 → 10分鐘）
task = PeriodicTask.objects.get(name='sync-dhcp-logs-every-5-minutes')
new_schedule = CrontabSchedule.objects.create(
    minute='*/10',  # 改為每 10 分鐘
    hour='*',
    day_of_week='*',
    day_of_month='*',
    month_of_year='*'
)
task.crontab = new_schedule
task.save()
print('✓ 任務排程已更新為每 10 分鐘')
EOF
```

### 暫停/啟用任務

```bash
# 暫停同步任務
docker exec nt-django python manage.py shell << 'EOF'
from django_celery_beat.models import PeriodicTask
task = PeriodicTask.objects.get(name='sync-dhcp-logs-every-5-minutes')
task.enabled = False
task.save()
print('✓ 同步任務已暫停')
EOF

# 啟用同步任務
docker exec nt-django python manage.py shell << 'EOF'
from django_celery_beat.models import PeriodicTask
task = PeriodicTask.objects.get(name='sync-dhcp-logs-every-5-minutes')
task.enabled = True
task.save()
print('✓ 同步任務已啟用')
EOF
```

### 手動觸發任務

```bash
# 透過 Django Shell
docker exec -it nt-django python manage.py shell
>>> from api.tasks import sync_dhcp_logs_task
>>> result = sync_dhcp_logs_task.delay(server_id=1, limit=500)
>>> result.get(timeout=60)  # 等待結果

# 透過 Flower Web UI
# 訪問 http://localhost:5555/tasks
# 點擊任務 → Execute
```

### 清理舊任務結果

```bash
# 清理 7 天前的任務結果
docker exec nt-django python manage.py shell << 'EOF'
from django_celery_results.models import TaskResult
from django.utils import timezone
from datetime import timedelta

cutoff = timezone.now() - timedelta(days=7)
deleted_count, _ = TaskResult.objects.filter(date_done__lt=cutoff).delete()
print(f'✓ 已刪除 {deleted_count} 筆舊任務結果')
EOF
```

---

## 🔍 故障排查

### 問題 1：Celery Worker 無法連接 Redis

**症狀**：
```
celery.exceptions.ImproperlyConfigured: CELERY_BROKER_URL is not set
```

**解決方法**：
```bash
# 檢查環境變數
docker exec nt-django env | grep REDIS

# 應該顯示：
# REDIS_HOST=redis
# REDIS_PORT=6379

# 測試 Redis 連接
docker exec nt-django python -c "
import redis
r = redis.Redis(host='redis', port=6379, db=1)
r.ping()
print('✓ Redis 連接成功')
"
```

### 問題 2：任務沒有自動執行

**檢查步驟**：
```bash
# 1. 確認 Celery Beat 正在運行
docker compose ps celery_beat

# 2. 查看 Beat 日誌
docker compose logs celery_beat --tail 100

# 3. 確認任務已啟用
docker exec nt-django python manage.py shell << 'EOF'
from django_celery_beat.models import PeriodicTask
tasks = PeriodicTask.objects.all()
for t in tasks:
    print(f'{t.name}: enabled={t.enabled}')
EOF

# 4. 重啟 Celery Beat
docker compose restart celery_beat
```

### 問題 3：Flower 無法訪問

**檢查步驟**：
```bash
# 確認 Flower 容器運行
docker ps | grep flower

# 查看 Flower 日誌
docker compose logs celery_flower

# 測試端口
curl http://localhost:5555

# 如果無法訪問，重啟 Flower
docker compose restart celery_flower
```

### 問題 4：任務執行失敗

**檢查步驟**：
```bash
# 查看 Worker 日誌
docker compose logs celery_worker --tail 200

# 查看失敗任務詳情（Flower）
# 訪問 http://localhost:5555/tasks
# 篩選 Status = FAILURE

# 或在 Django Shell 查詢
docker exec nt-django python manage.py shell << 'EOF'
from django_celery_results.models import TaskResult
failed = TaskResult.objects.filter(status='FAILURE').order_by('-date_done')[:10]
for t in failed:
    print(f'{t.task_name}: {t.result}')
EOF
```

---

## 📈 監控與維護

### 每日檢查

```bash
# 檢查容器狀態
docker compose ps

# 查看任務執行統計
docker exec nt-django python manage.py shell << 'EOF'
from django_celery_results.models import TaskResult
from datetime import datetime, timedelta

today = datetime.now().date()
stats = {
    'total': TaskResult.objects.filter(date_done__date=today).count(),
    'success': TaskResult.objects.filter(date_done__date=today, status='SUCCESS').count(),
    'failure': TaskResult.objects.filter(date_done__date=today, status='FAILURE').count(),
}
print(f"今日任務統計: 總計={stats['total']}, 成功={stats['success']}, 失敗={stats['failure']}")
EOF
```

### 週期性清理

```bash
# 每週清理任務結果（保留 30 天）
# 添加到 crontab 或創建新的 Celery 定時任務
0 4 * * 0 docker exec nt-django python manage.py shell << 'EOF'
from django_celery_results.models import TaskResult
from django.utils import timezone
from datetime import timedelta
cutoff = timezone.now() - timedelta(days=30)
deleted, _ = TaskResult.objects.filter(date_done__lt=cutoff).delete()
print(f'清理了 {deleted} 筆舊任務結果')
EOF
```

---

## 🎯 與方案 A（Cron）的對比

| 功能 | 方案 A（Cron） | 方案 B（Celery）✅ |
|------|---------------|-------------------|
| **Web 監控** | ❌ 無 | ✅ Flower (http://localhost:5555) |
| **任務歷史** | ❌ 只有日誌文件 | ✅ 資料庫存儲，可查詢 |
| **動態調整** | ❌ 需編輯 crontab | ✅ Django Admin 網頁修改 |
| **失敗重試** | ❌ 需手動 | ✅ 自動重試（max 3 次） |
| **資源消耗** | 0 MB | +250 MB (3 容器) |
| **容器數量** | 4 個 | 7 個 (+Redis, Beat, Worker) |
| **設置時間** | 5 分鐘 | 已完成（2 小時工作） |
| **適合場景** | 簡單需求 | ✅ 企業級、需監控 |

---

## ✅ 完成檢查清單

部署完成後，請確認以下項目：

- [ ] 所有 9 個容器正常運行（`docker compose ps`）
- [ ] Redis 可連接（`docker exec nt-redis redis-cli ping`）
- [ ] Celery Worker 已啟動（`docker compose logs celery_worker`）
- [ ] Celery Beat 已啟動（`docker compose logs celery_beat`）
- [ ] Flower 可訪問（http://localhost:5555）
- [ ] 資料庫遷移完成（django_celery_beat, django_celery_results）
- [ ] 手動任務執行成功
- [ ] 5 分鐘後自動任務執行
- [ ] 任務結果存入資料庫
- [ ] 前端應用正常訪問（http://localhost）

---

## 🚀 下一步

1. **監控任務執行**：
   - 每天查看 Flower 確認任務正常執行
   - 關注失敗任務並排查原因

2. **數據累積**：
   - 等待 7 天讓資料庫累積完整的 7 天日誌
   - 每天查看日誌增長情況

3. **效能優化**：
   - 根據實際日誌產生量調整 `--limit` 參數
   - 根據系統負載調整 Worker concurrency

4. **功能擴展**：
   - 添加告警通知（Slack/Email）
   - 添加更多定時任務（報告、分析）
   - 配置任務鏈（工作流）

---

**祝您部署順利！如有問題請參考故障排查章節。** 🎉
