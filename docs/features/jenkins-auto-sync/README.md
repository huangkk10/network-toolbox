# Jenkins Jobs 自動同步功能

## 📋 功能概述

本功能實現了 **Jenkins Server Jobs 的自動同步**，無需手動點擊「同步」按鈕，系統會定時自動從所有在線的 Jenkins Server 抓取最新的 Job 列表並更新到資料庫。

## ✨ 功能特性

### 自動化特性
- ✅ **定時同步**：每小時整點自動執行（00:00, 01:00, 02:00...）
- ✅ **智能篩選**：只同步狀態為「online」的 Jenkins Server
- ✅ **批次處理**：一次同步所有在線伺服器的 Jobs
- ✅ **增量更新**：自動識別新增和現有的 Jobs，避免重複

### 同步內容
1. **Job 基本資訊**：名稱、URL、完整名稱
2. **Job 狀態**：
   - `is_buildable`: 是否可構建
   - `is_disabled`: 是否被禁用
3. **View 分類**：Job 所屬的 View 名稱
4. **同步時間**：記錄每個 Job 的最後同步時間

### 智能特性
- 🔍 **自動發現**：自動發現新建立的 Jenkins Jobs
- 🔄 **狀態更新**：更新現有 Jobs 的狀態變化
- 📊 **詳細日誌**：完整記錄同步過程和結果
- 🛡️ **錯誤處理**：自動重試機制（最多 2 次，間隔 5 分鐘）

## 📊 測試結果

**測試時間**：2025-11-14 04:23:24

**測試結果**：
```
✅ 任務執行成功！
============================================================
處理伺服器: 4 個
找到 Jobs: 639 個
新增 Jobs: 0 個
更新 Jobs: 639 個
錯誤數量: 0 個
總耗時: 1.24 秒

各伺服器詳情：
  - 10.252.170.182: Jobs=355, 新增=0, 更新=355
  - 10.252.170.171: Jobs=16, 新增=0, 更新=16
  - 10.252.170.187: Jobs=203, 新增=0, 更新=203
  - 10.252.170.188: Jobs=65, 新增=0, 更新=65
```

## 🔧 技術實現

### 1. Celery 定時任務

**任務名稱**：`api.tasks.sync_all_jenkins_jobs_task`

**執行週期**：每小時整點（使用 `crontab(minute=0)`）

**配置位置**：`backend/network_toolbox/celery.py`

```python
# 任務 14：Jenkins Jobs 自動同步（每小時整點）
'sync-jenkins-jobs-hourly': {
    'task': 'api.tasks.sync_all_jenkins_jobs_task',
    'schedule': crontab(minute=0),  # 每小時整點執行
    'kwargs': {
        'server_id': None  # None 表示處理所有在線 Server
    },
    'options': {
        'expires': 3300,   # 任務超時 55 分鐘
        'queue': 'default',
    }
},
```

### 2. 任務實現

**文件位置**：`backend/api/tasks.py`

**核心功能**：
1. 獲取所有在線的 Jenkins Server
2. 遍歷每個 Server：
   - 連接 Jenkins API
   - 獲取所有 Views 及其 Jobs
   - 建立 Job 到 View 的映射
   - 獲取完整 Job 列表
   - 創建或更新資料庫記錄
3. 記錄詳細日誌和統計資訊

### 3. 同步邏輯

```python
# 創建或更新 Job
job, created = JenkinsJob.objects.update_or_create(
    server=server,
    name=job_name,
    defaults={
        'url': job_url,
        'full_name': job_name,
        'is_buildable': is_buildable,
        'is_disabled': is_disabled,
        'view_name': view_name,
        'last_sync_at': timezone.now(),
    }
)
```

## 🎯 使用場景

### 場景 1：自動發現新 Job
當 Jenkins Server 上新建了 Job 後，無需手動同步，系統會在下一個整點自動發現並添加到資料庫。

### 場景 2：狀態變化追蹤
當 Job 被禁用或啟用時，系統會自動更新 `is_disabled` 狀態。

### 場景 3：View 分類維護
當 Job 被移動到不同的 View 時，系統會自動更新 `view_name` 欄位。

## 📈 性能指標

**平均同步時間**：
- 單個 Server（~300 Jobs）：約 0.5-0.7 秒
- 4 個 Servers（~640 Jobs）：約 1.2-1.5 秒

**資源消耗**：
- CPU：輕量級（主要是 HTTP 請求）
- 記憶體：< 100 MB
- 網路：取決於 Jenkins Server 響應速度

## 🚀 手動觸發同步

如果需要立即同步（不等到整點），可以使用以下方式：

### 方式 1：通過 Django Shell

```bash
docker compose exec django python manage.py shell -c "
from api.tasks import sync_all_jenkins_jobs_task
result = sync_all_jenkins_jobs_task.delay()
print(f'任務 ID: {result.id}')
"
```

### 方式 2：通過 API（前端頁面）

在 RVT 管理頁面點擊各伺服器的「同步」按鈕，仍然可以手動觸發單個伺服器的同步。

### 方式 3：直接調用（測試用）

```bash
docker compose exec django python manage.py shell -c "
from api.tasks import sync_all_jenkins_jobs_task
result = sync_all_jenkins_jobs_task()  # 直接執行，不通過 Celery
print(result)
"
```

## 📝 日誌查看

### 查看同步日誌

```bash
# 查看 Django 日誌
tail -f logs/django.log | grep "Jenkins Jobs"

# 查看最近的同步記錄
tail -100 logs/django.log | grep -A 20 "開始自動同步 Jenkins Jobs"
```

### 日誌內容示例

```
[INFO] [Celery] 🔄 開始自動同步 Jenkins Jobs
[INFO] [Celery]   - Server ID: All Online
[INFO] [Celery] 📡 找到 4 個在線的 Jenkins Server
[INFO] [Celery] 🖥️  處理 Server: 10.252.170.182
[INFO] [Celery]   - 找到 21 個 Views
[INFO] [Celery]   - 找到 355 個 Jobs
[INFO] [Celery] ✅ Server "10.252.170.182" 同步完成: 新增 0, 更新 355, 共 355 個 Jobs
[INFO] [Celery] 🎉 Jenkins Jobs 自動同步完成
[INFO] [Celery]   - 處理伺服器: 4 個
[INFO] [Celery]   - 找到 Jobs: 639 個
[INFO] [Celery]   - 新增 Jobs: 0 個
[INFO] [Celery]   - 更新 Jobs: 639 個
[INFO] [Celery]   - 錯誤數量: 0 個
[INFO] [Celery]   - 總耗時: 1.24 秒
```

## ⚙️ 配置選項

### 修改同步頻率

編輯 `backend/network_toolbox/celery.py`：

```python
# 每 30 分鐘同步一次
'schedule': crontab(minute='*/30')

# 每 2 小時同步一次
'schedule': crontab(minute=0, hour='*/2')

# 每天固定時間同步（例如：每天 8:00 和 20:00）
'schedule': crontab(minute=0, hour='8,20')
```

### 指定特定 Server

如果只想自動同步特定的 Server，可以修改 `kwargs`：

```python
'kwargs': {
    'server_id': 13  # 只同步 ID=13 的 Server
},
```

## 🔍 監控與告警

### 檢查任務狀態

```bash
# 查看已註冊的任務
docker compose exec django celery -A network_toolbox inspect registered | grep sync_all_jenkins

# 查看定時任務排程
docker compose exec django celery -A network_toolbox inspect scheduled
```

### 查看任務執行歷史

通過 Django Admin 或 API 查看 `JenkinsServer` 模型的 `last_sync_at` 欄位，確認最後同步時間。

## 🛠️ 故障排查

### 問題 1：任務未執行

**檢查步驟**：
1. 確認 Celery Worker 正在運行：
   ```bash
   docker compose exec django celery -A network_toolbox inspect active
   ```

2. 確認 Celery Beat 正在運行：
   ```bash
   docker compose logs django | grep "beat"
   ```

3. 查看錯誤日誌：
   ```bash
   tail -100 logs/django_error.log
   ```

### 問題 2：同步失敗

**檢查步驟**：
1. 驗證 Jenkins Server 連線：
   ```bash
   curl -I http://10.252.170.182:8080/
   ```

2. 檢查認證資訊：確認 `username` 和 `api_token` 是否正確

3. 查看詳細錯誤：
   ```bash
   docker compose exec django python manage.py shell -c "
   from api.tasks import sync_all_jenkins_jobs_task
   result = sync_all_jenkins_jobs_task()
   "
   ```

### 問題 3：同步速度慢

**優化建議**：
1. 減少同步頻率（改為每 2 小時）
2. 只同步特定的 Server
3. 檢查網路延遲：
   ```bash
   ping 10.252.170.182
   ```

## 📚 相關文檔

- [Jenkins API 文檔](../../../backend/library/services/jenkins_client.py)
- [Celery 定時任務配置](../../../backend/network_toolbox/celery.py)
- [Jenkins Models](../../../backend/api/models.py)
- [RVT 管理頁面](../../../frontend/src/pages/RVTManagementPage.js)

## 🔗 API 端點

相關的 API 端點（仍可手動調用）：

- `POST /api/jenkins-servers/{id}/sync_jobs/` - 手動同步單個 Server 的 Jobs
- `GET /api/jenkins-servers/` - 獲取所有 Jenkins Servers（包含最後同步時間）
- `GET /api/jenkins-jobs/` - 獲取所有 Jobs（支援過濾）

## 📅 版本歷史

- **v1.0.0** (2025-11-14) - 初始版本
  - 實現每小時自動同步功能
  - 支援批次處理多個 Server
  - 完整的日誌記錄和錯誤處理
  - 自動重試機制

## 👥 維護者

Network Toolbox Team

## 📄 授權

本功能為 Network Toolbox 專案的一部分。
