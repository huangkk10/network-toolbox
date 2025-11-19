# Jenkins Jobs 自動同步失敗問題修復報告

## 問題描述

**現象**：
- Jenkins Server `10.252.170.171` (ID: 12) 的 Job `Test-KVM05_tt` 未出現在系統中
- 手動同步可以成功添加，但自動同步未執行
- 定時任務 `sync-jenkins-jobs-hourly` 配置正確，Beat 每小時都有發送，但 Worker 從未收到

**影響**：
- 新增的 Jenkins Jobs 無法自動同步到系統
- 需要手動觸發才能更新 Jobs 列表
- 系統數據與實際 Jenkins Server 狀態不一致

## 根本原因

**隊列配置不匹配**

### 配置對比：

| 組件 | 配置位置 | 隊列名稱 | 狀態 |
|------|---------|---------|------|
| Beat Scheduler | celery.py + PeriodicTask | `default` | ❌ 錯誤 |
| Worker | Docker compose | `celery` | ✅ 正常 |

### 問題分析：

1. **celery.py 中的配置**：
   ```python
   'sync-jenkins-jobs-hourly': {
       'task': 'api.tasks.sync_all_jenkins_jobs_task',
       'schedule': crontab(minute=0),
       'options': {
           'queue': 'default',  # ❌ 問題所在
       }
   }
   ```

2. **資料庫 PeriodicTask 記錄**：
   - `queue = 'default'` ← Beat 從這裡讀取配置
   - 任務被發送到 Redis 的 `default` 隊列

3. **Worker 配置**：
   ```bash
   $ docker exec nt-celery-worker celery -A network_toolbox inspect active_queues
   -> celery@fc9e10c3f72c: OK
       * {'name': 'celery', ...}  # ✅ 只監聽 'celery' 隊列
   ```

4. **結果**：
   - Beat 發送任務到 `default` 隊列
   - Worker 監聽 `celery` 隊列
   - **任務永遠無法送達 Worker**

## 驗證證據

### 1. Beat 日誌證據（任務已發送）

```
[2025-11-19 03:00:00,020: INFO/MainProcess] Scheduler: Sending due task sync-jenkins-jobs-hourly (api.tasks.sync_all_jenkins_jobs_task)
[2025-11-19 07:00:00,025: INFO/MainProcess] Scheduler: Sending due task sync-jenkins-jobs-hourly (api.tasks.sync_all_jenkins_jobs_task)
[2025-11-19 08:00:00,025: INFO/MainProcess] Scheduler: Sending due task sync-jenkins-jobs-hourly (api.tasks.sync_all_jenkins_jobs_task)
... (每小時都有)
```

### 2. Worker 日誌證據（任務未收到）

```bash
$ docker logs nt-celery-worker --since '2025-11-19T03:00:00' --until '2025-11-19T03:00:10' | grep "sync_all_jenkins_jobs_task"
(無輸出 - exit code 1)
```

對比同時發送的其他任務：
```
[2025-11-19 03:00:00,148: INFO/MainProcess] Task api.tasks.auto_store_jenkins_artifacts_task[...] received  # ✅ 收到
[2025-11-19 03:00:00,116: INFO/MainProcess] Task api.tasks.auto_identify_switches_task[...] received        # ✅ 收到
```

### 3. 資料庫證據（隊列配置）

```bash
$ docker exec nt-django python manage.py shell -c "..."
Task: api.tasks.sync_all_jenkins_jobs_task
Queue: default  # ❌ 問題
```

成功執行的任務：
```
auto-store-jenkins-artifacts-hourly | Queue: (default)  # ✅ 使用默認隊列 'celery'
```

### 4. Worker 監聽隊列證據

```bash
$ docker exec nt-celery-worker celery -A network_toolbox inspect active_queues
-> celery@fc9e10c3f72c: OK
    * {'name': 'celery', ...}  # ✅ 只有 'celery' 隊列
```

### 5. 手動觸發成功證據

```
[2025-11-19 10:55:35,207: INFO] [Celery] 🔄 開始自動同步 Jenkins Jobs
Server ID: 12
...
🎉 Jenkins Jobs 自動同步完成！新增 1, 更新 16, 共 17 個 Jobs
```

**為什麼手動成功？**
- 手動觸發繞過了 Celery 隊列機制
- 任務直接在 Django 進程中執行
- 不受隊列配置影響

## 修復方案

### 方案 A：修改任務配置使用默認隊列（已採用）

**優點**：
- 簡單直接
- 與其他任務配置一致
- 不需要修改 Worker 啟動參數

**步驟**：

1. **修改 celery.py**：
   ```python
   'sync-jenkins-jobs-hourly': {
       'task': 'api.tasks.sync_all_jenkins_jobs_task',
       'schedule': crontab(minute=0),
       'options': {
           'expires': 3300,
           # 'queue': 'default',  # 移除此行，使用默認隊列
       }
   }
   ```

2. **更新資料庫記錄**：
   ```python
   from django_celery_beat.models import PeriodicTask
   task = PeriodicTask.objects.get(name='sync-jenkins-jobs-hourly')
   task.queue = None  # 或 ''，表示使用默認隊列
   task.save()
   ```

3. **重啟 Beat 容器**：
   ```bash
   docker restart nt-celery-beat
   ```

### 方案 B：讓 Worker 同時監聽 default 隊列（未採用）

**缺點**：
- 需要修改 docker-compose.yml
- 需要重啟 Worker（影響正在執行的任務）
- 與其他任務配置不一致

**步驟（僅供參考）**：
```yaml
celery_worker:
  command: celery -A network_toolbox worker -Q celery,default -l info
```

## 執行記錄

### 修復時間
- 2025-11-19 11:57

### 修復操作

1. ✅ 修改 `/home/owner/Codes/network-toolbox/backend/network_toolbox/celery.py`
   - 移除 `'queue': 'default'` 行

2. ✅ 更新資料庫 PeriodicTask：
   ```bash
   $ docker exec nt-django python manage.py shell -c "..."
   Before: default
   After: None
   ✅ Updated
   ```

3. ✅ 重啟 Beat 容器：
   ```bash
   $ docker restart nt-celery-beat
   nt-celery-beat
   ```

### 驗證計劃

**時間**：2025-11-19 12:00（下一個整點）

**驗證步驟**：
1. 檢查 Beat 是否發送任務
2. 檢查 Worker 是否收到任務
3. 檢查應用程式日誌是否有同步記錄
4. 檢查資料庫是否有新 Jobs 數據更新

**監控腳本**：
```bash
/home/owner/Codes/network-toolbox/scripts/monitor_jenkins_sync_12pm.sh
```

## 其他潛在問題

### 需要檢查的其他任務

發現以下任務在 celery.py 中也配置了 `'queue': 'default'`：

1. `sync-jenkins-builds-every-10-minutes`
2. `auto-store-jenkins-workspaces-hourly`
3. `auto-store-jenkins-builds-every-30-minutes`
4. `clean-expired-ansible-caches-daily`

**建議**：
- 檢查這些任務的資料庫配置
- 如果也是 `queue='default'`，建議一併修復
- 統一使用默認隊列，避免混亂

### 長期建議

1. **統一隊列策略**：
   - 所有任務都使用默認隊列 `celery`
   - 或者明確區分不同優先級的任務，使用多個專用隊列

2. **配置一致性檢查**：
   - 創建檢查腳本，定期比對 celery.py 和資料庫配置
   - 發現不一致時自動告警

3. **監控改進**：
   - 添加任務執行監控
   - 如果預期任務長時間未執行，發送告警

4. **文檔完善**：
   - 記錄隊列使用規範
   - 新增任務時明確指定隊列策略

## 參考連結

- **相關文件**：
  - `/home/owner/Codes/network-toolbox/backend/network_toolbox/celery.py`
  - `/home/owner/Codes/network-toolbox/backend/api/tasks.py`
  - `/home/owner/Codes/network-toolbox/backend/test_jenkins_task_dispatch.py`

- **調查過程記錄**：
  - Beat 日誌：`docker logs nt-celery-beat`
  - Worker 日誌：`docker logs nt-celery-worker`
  - Django 應用日誌：`/app/logs/django.log`

- **診斷工具**：
  - `test_jenkins_task_dispatch.py` - 任務派發測試腳本
  - `monitor_jenkins_sync_12pm.sh` - 12:00 監控腳本

---

**報告人**：GitHub Copilot  
**報告時間**：2025-11-19 11:58  
**問題狀態**：修復完成，等待驗證
