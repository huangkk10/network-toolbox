# Jenkins 同步機制改進 - 完整實施路線圖

## 📋 專案目標

整合 **資料清理** 和 **系統保護機制**，從根本上解決 Jenkins 資料同步問題，並避免系統資源過載。

### 核心問題

1. ❌ **資料不一致**：資料庫中的 Jobs/Builds 與 Jenkins Server 不同步
2. ❌ **孤立資料累積**：刪除或重命名的 Jobs/Builds 在資料庫中保留
3. ❌ **系統資源風險**：曾發生 CPU 使用率 100% 的問題

### 解決方案

- ✅ **立即清理**：手動腳本清理現有孤立資料
- ✅ **定期驗證**：自動任務定期檢查和清理
- ✅ **改進同步**：從根本上改進同步機制
- ✅ **系統保護**：多層保護機制防止資源過載

---

## 🎯 分階段執行計畫

### 📊 執行時間線

```
階段 1 (第 1 週)          階段 2 (第 2 週)          階段 3 (第 3-4 週)
立即清理 + 準備           保護機制實施             同步機制改進
├─ 手動清理腳本           ├─ 工具模組開發           ├─ 改進 Jobs 同步
├─ 測試和執行清理         ├─ JenkinsClient 改進     ├─ 改進 Builds 同步
└─ 驗證結果               ├─ 定期驗證任務           ├─ 完整測試
                          └─ Celery 配置調整        └─ 部署上線
```

---

## 📅 階段 1：立即清理與準備（第 1 週，預計 3-5 天）

### 目標
- 清理現有的孤立資料
- 驗證問題範圍
- 為後續開發準備基礎

### 📝 任務清單

#### 1.1 創建手動清理腳本（第 1 天）

**文件**：`backend/cleanup_orphaned_jenkins_data.py`

**任務**：
- [ ] 創建 `JenkinsDataCleaner` 類別
- [ ] 實作 `find_orphaned_jobs()` 方法
- [ ] 實作 `find_orphaned_builds()` 方法
- [ ] 實作 `backup_data()` 方法
- [ ] 實作 `cleanup_orphaned_data()` 方法
- [ ] 添加命令列參數解析（argparse）
- [ ] 添加詳細的日誌輸出

**驗收標準**：
- ✅ 腳本可正常執行（不報錯）
- ✅ `--help` 顯示完整的使用說明
- ✅ 支援 `--dry-run`, `--backup`, `--server-id`, `--yes` 參數

**預期輸出**：
```bash
# 測試執行
docker exec nt-django python cleanup_orphaned_jenkins_data.py --help
# 應該顯示完整的幫助訊息
```

---

#### 1.2 乾運行測試（第 2 天上午）

**任務**：
- [ ] 執行乾運行模式檢查所有 Servers
- [ ] 記錄孤立的 Jobs 和 Builds 數量
- [ ] 分析孤立資料的特徵
- [ ] 確認沒有重要資料將被誤刪

**執行步驟**：
```bash
# 1. 檢查所有 Servers
docker exec nt-django python cleanup_orphaned_jenkins_data.py --dry-run --backup

# 2. 針對特定 Server 測試
docker exec nt-django python cleanup_orphaned_jenkins_data.py --server-id 1 --dry-run

# 3. 檢查備份檔案
docker exec nt-django ls -lh /app/logs/jenkins_cleanup_backup_*.json
```

**驗收標準**：
- ✅ 腳本正常執行完成
- ✅ 日誌中顯示孤立資料統計
- ✅ 備份檔案已生成
- ✅ 沒有發現要保留的資料被標記為孤立

**預期結果文檔**：
```
📊 乾運行結果摘要
===================
總 Jobs: 150
總 Builds: 5000
孤立 Jobs: 12
孤立 Builds: 230

孤立 Jobs 清單：
- Server1: SAF3204_KVM05 (18 builds)
- Server1: OLD_PROJECT_TEST (12 builds)
...

決策：
[ ] 確認可以清理
[ ] 需要保留某些資料（列出原因）
```

---

#### 1.3 執行實際清理（第 2 天下午）

**前提條件**：
- ✅ 乾運行結果已審核通過
- ✅ 確認沒有重要資料將被刪除
- ✅ 已通知相關人員（如有必要）

**任務**：
- [ ] 執行實際清理（帶備份）
- [ ] 監控執行過程
- [ ] 記錄刪除結果
- [ ] 保存備份檔案

**執行步驟**：
```bash
# 1. 執行清理（會要求確認）
docker exec -it nt-django python cleanup_orphaned_jenkins_data.py --backup

# 2. 查看執行日誌
docker exec nt-django tail -f /app/logs/django.log

# 3. 驗證備份
docker exec nt-django ls -lh /app/logs/jenkins_cleanup_backup_*.json

# 4. 檢查資料庫記錄數量（清理前後對比）
docker exec nt-django python manage.py shell
>>> from api.models import JenkinsJob, JenkinsBuild
>>> JenkinsJob.objects.count()
>>> JenkinsBuild.objects.count()
```

**驗收標準**：
- ✅ 清理成功完成
- ✅ 刪除的 Jobs/Builds 數量與預期一致
- ✅ 備份檔案已保存
- ✅ 資料庫記錄數量正確

---

#### 1.4 驗證清理效果（第 3 天）

**任務**：
- [ ] 檢查前端 Web UI 顯示
- [ ] 驗證 API 返回資料
- [ ] 確認 Jenkins Server 功能正常
- [ ] 檢查資料庫完整性

**驗證步驟**：
```bash
# 1. 檢查資料庫
docker exec nt-django python manage.py shell
>>> from api.models import JenkinsJob, JenkinsBuild
>>> # 確認沒有孤立資料
>>> orphaned_jobs = JenkinsJob.objects.filter(server__is_online=False)
>>> orphaned_jobs.count()  # 應該很少或為 0

# 2. 測試 API
curl http://localhost/api/jenkins-servers/
curl http://localhost/api/jenkins-jobs/
curl http://localhost/api/jenkins-builds/

# 3. 前端測試
# 訪問 http://localhost → Jenkins 詳細頁面
# 確認顯示的 Jobs 和 Builds 都存在於 Jenkins Server
```

**驗收標準**：
- ✅ Web UI 不再顯示孤立的 Jobs/Builds
- ✅ API 返回資料正確
- ✅ Jenkins Server 可正常訪問
- ✅ 沒有因清理導致的錯誤

---

#### 1.5 階段 1 總結報告（第 3 天）

**生成報告**：`docs/reports/PHASE1_CLEANUP_REPORT.md`

**報告內容**：
```markdown
# 階段 1 清理報告

## 執行摘要
- 執行時間：2025-11-21 10:00 - 11:30
- 處理 Servers：3 個
- 清理前：150 Jobs, 5000 Builds
- 清理後：138 Jobs, 4770 Builds

## 刪除資料
- 孤立 Jobs：12 個
- 孤立 Builds：230 個
- 釋放空間：約 500 MB

## 問題發現
- 主要原因：Job 重命名、Build 手動刪除
- 最嚴重 Server：Server1（8 個孤立 Jobs）

## 後續建議
- 實施定期驗證任務
- 改進同步機制
- 添加系統保護
```

**驗收標準**：
- ✅ 報告已生成並審核
- ✅ 記錄了所有關鍵數據
- ✅ 確定了問題根源
- ✅ 為階段 2 提供了基礎

---

## 📅 階段 2：系統保護機制實施（第 2 週，預計 5-7 天）

### 目標
- 實施多層保護機制
- 防止 CPU 和記憶體過載
- 建立定期驗證任務

### 📝 任務清單

#### 2.1 創建工具模組（第 4-5 天）

##### 2.1.1 任務鎖模組

**文件**：`backend/library/utils/task_lock.py`

**任務**：
- [ ] 創建 `TaskLock` 類別
- [ ] 實作 `acquire()` 方法（獲取鎖）
- [ ] 實作 `release()` 方法（釋放鎖）
- [ ] 實作 `is_locked()` 方法（檢查鎖狀態）
- [ ] 創建 `@with_task_lock` 裝飾器
- [ ] 編寫單元測試

**驗收標準**：
- ✅ 模組可正常導入
- ✅ 鎖機制正常工作（同一任務不會重複執行）
- ✅ 單元測試通過
- ✅ 文檔完整（docstring）

**測試代碼**：
```python
# tests/unit/backend/test_task_lock.py
from library.utils.task_lock import TaskLock, with_task_lock

def test_task_lock_acquire():
    assert TaskLock.acquire('test_lock')
    assert not TaskLock.acquire('test_lock')  # 第二次應該失敗
    TaskLock.release('test_lock')
    assert TaskLock.acquire('test_lock')  # 釋放後可再次獲取

def test_with_task_lock_decorator():
    @with_task_lock('test_task')
    def my_task():
        return 'success'
    
    result1 = my_task()
    assert result1 == 'success'
    
    # 同時執行應該被拒絕
    result2 = my_task()
    assert result2['skipped'] == True
```

---

##### 2.1.2 速率限制模組

**文件**：`backend/library/utils/rate_limiter.py`

**任務**：
- [ ] 創建 `RateLimiter` 類別
- [ ] 實作 `wait_if_needed()` 方法
- [ ] 支援上下文管理器（`with` 語句）
- [ ] 編寫單元測試

**驗收標準**：
- ✅ 速率限制正常工作
- ✅ 可正確計算等待時間
- ✅ 單元測試通過

**測試代碼**：
```python
# tests/unit/backend/test_rate_limiter.py
from library.utils.rate_limiter import RateLimiter
import time

def test_rate_limiter():
    limiter = RateLimiter(max_requests=5, time_window=1)
    
    start = time.time()
    for i in range(10):
        with limiter:
            pass
    duration = time.time() - start
    
    # 10 個請求，每秒 5 個，應該至少需要 2 秒
    assert duration >= 2.0
```

---

##### 2.1.3 資源監控模組

**文件**：`backend/library/utils/resource_monitor.py`

**任務**：
- [ ] 創建 `ResourceMonitor` 類別
- [ ] 實作 `get_memory_usage_mb()` 方法
- [ ] 實作 `get_cpu_percent()` 方法
- [ ] 實作 `check_memory_threshold()` 方法
- [ ] 實作 `log_resource_usage()` 方法
- [ ] 編寫單元測試

**依賴安裝**：
```bash
# 更新 requirements.txt
echo "psutil>=5.9.0" >> backend/requirements.txt

# 容器內安裝
docker exec nt-django pip install psutil
```

**驗收標準**：
- ✅ 可正確獲取 CPU 和記憶體使用率
- ✅ 閾值檢查正常工作
- ✅ 單元測試通過

---

##### 2.1.4 監控指標模組

**文件**：`backend/library/utils/metrics.py`

**任務**：
- [ ] 創建 `SyncMetrics` 類別
- [ ] 實作 `record_sync_start()` 方法
- [ ] 實作 `record_sync_end()` 方法
- [ ] 實作 `check_anomaly()` 方法
- [ ] 編寫單元測試

**驗收標準**：
- ✅ 可記錄任務執行指標
- ✅ 可檢測異常指標
- ✅ 資料可持久化（快取）

---

#### 2.2 改進 JenkinsClient（第 6 天）

**文件**：`backend/library/services/jenkins_client.py`

**任務**：
- [ ] 添加 `rate_limit` 參數
- [ ] 整合 `RateLimiter`
- [ ] 配置連接池（`HTTPAdapter`）
- [ ] 配置重試策略（指數退避）
- [ ] 添加請求超時控制
- [ ] 更新現有方法使用 `_request()`
- [ ] 編寫整合測試

**改進重點**：
```python
class JenkinsClient:
    def __init__(self, base_url, username, api_token, 
                 rate_limit=10, timeout=30, max_retries=3):
        # 速率限制器
        self.rate_limiter = RateLimiter(max_requests=rate_limit)
        
        # 連接池
        self.session = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=5,
            pool_maxsize=10,
            max_retries=self._get_retry_strategy(max_retries)
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
```

**驗收標準**：
- ✅ 速率限制生效（不會超過設定的請求頻率）
- ✅ 連接池正常工作
- ✅ 重試機制正常（模擬失敗情況）
- ✅ 整合測試通過

**測試代碼**：
```python
# tests/integration/services/test_jenkins_client.py
def test_rate_limit():
    client = JenkinsClient(
        base_url='http://jenkins.example.com',
        username='admin',
        api_token='token',
        rate_limit=5  # 每秒 5 個請求
    )
    
    start = time.time()
    for i in range(10):
        client.get_all_jobs()
    duration = time.time() - start
    
    # 應該至少需要 2 秒
    assert duration >= 2.0
```

---

#### 2.3 創建定期驗證任務（第 7 天）

**文件**：`backend/api/tasks.py`

**任務**：
- [ ] 創建 `validate_jenkins_data()` 任務
- [ ] 整合 `JenkinsClient`（帶速率限制）
- [ ] 實作孤立 Jobs 檢測
- [ ] 實作自動清理邏輯（可選）
- [ ] 添加詳細日誌
- [ ] 編寫任務測試

**核心邏輯**：
```python
@shared_task(
    bind=True,
    name='api.tasks.validate_jenkins_data',
    max_retries=2,
    time_limit=1800,
    soft_time_limit=1650
)
def validate_jenkins_data(self, server_id=None, auto_cleanup=False):
    """驗證 Jenkins 資料一致性"""
    # 1. 獲取 Servers
    # 2. 對每個 Server 檢查 Jobs
    # 3. 找出孤立的 Jobs
    # 4. 可選：自動清理
    # 5. 記錄統計資訊
```

**驗收標準**：
- ✅ 任務可正常執行
- ✅ 可正確檢測孤立 Jobs
- ✅ 自動清理功能正常（如果啟用）
- ✅ 日誌詳細且易讀

---

#### 2.4 配置 Celery Beat（第 7 天）

**文件**：`backend/network_toolbox/celery.py`

**任務**：
- [ ] 更新 Celery Worker 配置
- [ ] 添加定期驗證任務排程
- [ ] 配置任務優先級
- [ ] 測試排程是否生效

**配置內容**：
```python
# Celery Worker 配置
app.conf.update(
    worker_concurrency=2,              # 🔒 最多 2 個並發
    worker_prefetch_multiplier=1,      # 🔒 預取 1 個任務
    worker_max_tasks_per_child=50,     # 🔒 執行 50 次後重啟
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

# Beat 排程
app.conf.beat_schedule = {
    # 每天凌晨 3 點驗證（只檢查）
    'validate-jenkins-data-daily': {
        'task': 'api.tasks.validate_jenkins_data',
        'schedule': crontab(hour=3, minute=0),
        'kwargs': {'auto_cleanup': False},
    },
    
    # 每週日凌晨 4 點清理
    'cleanup-orphaned-jenkins-data-weekly': {
        'task': 'api.tasks.validate_jenkins_data',
        'schedule': crontab(hour=4, minute=0, day_of_week=0),
        'kwargs': {'auto_cleanup': True},
    },
}
```

**驗收標準**：
- ✅ Celery Worker 以新配置啟動
- ✅ Beat 排程已註冊
- ✅ 可手動觸發任務測試

**測試步驟**：
```bash
# 1. 重啟 Celery
docker compose restart django

# 2. 檢查 Worker 配置
docker exec nt-django celery -A network_toolbox inspect active_queues

# 3. 檢查 Beat 排程
docker exec nt-django celery -A network_toolbox beat -l info

# 4. 手動測試任務
docker exec nt-django python manage.py shell
>>> from api.tasks import validate_jenkins_data
>>> result = validate_jenkins_data.delay()
>>> result.get()
```

---

#### 2.5 創建系統配置（第 8 天）

**文件**：`backend/network_toolbox/settings.py`

**任務**：
- [ ] 添加 `JENKINS_SYNC_PROTECTION` 配置
- [ ] 配置資料庫連接池
- [ ] 更新 `requirements.txt`
- [ ] 編寫配置文檔

**配置內容**：
```python
# Jenkins 同步保護配置
JENKINS_SYNC_PROTECTION = {
    # 批次處理
    'batch_size': 50,
    'batch_rest_seconds': 2,
    
    # 資料量限制
    'max_jobs_per_sync': 500,
    'max_builds_per_job': 100,
    'max_builds_per_sync': 5000,
    
    # API 請求
    'api_rate_limit': 10,
    'api_timeout': 30,
    'api_max_retries': 3,
    
    # 資源監控
    'memory_threshold_mb': 1024,
    'memory_check_interval': 100,
}
```

**驗收標準**：
- ✅ 配置可正常讀取
- ✅ 所有配置項都有說明
- ✅ 文檔已更新

---

#### 2.6 階段 2 測試（第 8-9 天）

**任務**：
- [ ] 單元測試（所有工具模組）
- [ ] 整合測試（JenkinsClient）
- [ ] 任務測試（validate_jenkins_data）
- [ ] 端對端測試（完整流程）

**測試清單**：
```bash
# 1. 單元測試
docker exec nt-django python manage.py test tests/unit/

# 2. 整合測試
docker exec nt-django python manage.py test tests/integration/

# 3. 任務測試
docker exec nt-django python manage.py test tests/unit/backend/test_validate_jenkins_data.py

# 4. 手動測試定期任務
docker exec nt-django python manage.py shell
>>> from api.tasks import validate_jenkins_data
>>> validate_jenkins_data(server_id=1, auto_cleanup=False)
```

**驗收標準**：
- ✅ 所有測試通過
- ✅ 代碼覆蓋率 > 80%
- ✅ 沒有發現嚴重 Bug

---

#### 2.7 階段 2 總結報告（第 9 天）

**生成報告**：`docs/reports/PHASE2_PROTECTION_REPORT.md`

**報告內容**：
- 實施的保護機制清單
- 測試結果摘要
- 性能測試數據（CPU、記憶體使用）
- 發現的問題和解決方案
- 階段 3 準備情況

---

## 📅 階段 3：同步機制改進（第 3-4 週，預計 7-10 天）

### 目標
- 從根本上改進同步邏輯
- 整合所有保護機制
- 實現自動清理功能

### 📝 任務清單

#### 3.1 改進 sync_all_jenkins_jobs_task（第 10-11 天）

**文件**：`backend/api/tasks.py`

**任務**：
- [ ] 添加 `cleanup_orphaned` 參數
- [ ] 實作孤立 Jobs 檢測邏輯
- [ ] 整合任務鎖（`@with_task_lock`）
- [ ] 整合資源監控
- [ ] 整合監控指標
- [ ] 添加批次處理
- [ ] 編寫測試

**改進重點**：
```python
@shared_task(
    bind=True,
    name='api.tasks.sync_all_jenkins_jobs_task',
    time_limit=3600,
    soft_time_limit=3300
)
@with_task_lock('sync_jenkins_jobs', timeout=3600)
def sync_all_jenkins_jobs_task(self, server_id=None, cleanup_orphaned=True):
    """
    同步所有 Jenkins Jobs（帶保護機制）
    
    改進：
    1. 任務互斥鎖
    2. 自動清理孤立 Jobs
    3. 資源監控
    4. 批次處理
    """
    SyncMetrics.record_sync_start('sync_jenkins_jobs')
    
    try:
        # 同步邏輯...
        
        if cleanup_orphaned:
            # 檢測並清理孤立 Jobs
            jenkins_job_names = {job['name'] for job in jenkins_jobs}
            orphaned_jobs = db_jobs.exclude(name__in=jenkins_job_names)
            
            if orphaned_jobs.exists():
                orphaned_jobs.delete()
        
        SyncMetrics.record_sync_end('sync_jenkins_jobs', success=True)
    
    except Exception as e:
        SyncMetrics.record_sync_end('sync_jenkins_jobs', success=False)
        raise
```

**驗收標準**：
- ✅ 可自動檢測和清理孤立 Jobs
- ✅ 任務不會重複執行
- ✅ 資源使用在安全範圍
- ✅ 測試通過

---

#### 3.2 改進 sync_jenkins_builds（第 12-14 天）

**文件**：`backend/api/tasks.py`

**任務**：
- [ ] 添加 `full_sync` 參數
- [ ] 添加 `cleanup_orphaned` 參數
- [ ] 實作孤立 Builds 檢測邏輯
- [ ] 整合所有保護機制
- [ ] 實作自適應批次處理
- [ ] 添加進度追蹤
- [ ] 編寫完整測試

**改進重點**：
```python
@shared_task(
    bind=True,
    name='api.tasks.sync_jenkins_builds',
    max_retries=2,
    time_limit=3600,
    soft_time_limit=3300
)
@with_task_lock('sync_jenkins_builds', timeout=3600)
def sync_jenkins_builds(
    self,
    server_id=None,
    full_sync=False,
    cleanup_orphaned=False,
    max_builds_per_job=20,
    max_age_days=3
):
    """
    同步 Jenkins Builds（完整保護版本）
    
    🔒 保護機制：
    1. 任務互斥鎖
    2. 超時保護
    3. 批次處理
    4. 速率限制
    5. 資源監控
    6. 自適應策略
    7. 異常檢測
    """
    config = settings.JENKINS_SYNC_PROTECTION
    SyncMetrics.record_sync_start('sync_jenkins_builds')
    
    try:
        # 批次處理
        for batch_start in range(0, total_jobs, batch_size):
            # 🔒 自適應批次大小
            current_batch_size = AdaptiveSyncStrategy.get_batch_size()
            if current_batch_size == 0:
                time.sleep(30)  # CPU 過高，暫停
                continue
            
            # 處理這一批
            batch_jobs = all_jobs[batch_start:batch_start + batch_size]
            
            for job in batch_jobs:
                # 創建 JenkinsClient（帶速率限制）
                client = JenkinsClient(
                    base_url=job.server.url,
                    username=job.server.username,
                    api_token=job.server.api_token,
                    rate_limit=config['api_rate_limit'],
                    timeout=config['api_timeout'],
                    max_retries=config['api_max_retries']
                )
                
                # 同步 Builds
                _sync_single_job_builds(job, client, full_sync, cleanup_orphaned)
                
                client.close()
            
            # 🔒 批次間休息
            time.sleep(AdaptiveSyncStrategy.get_rest_time())
            
            # 🔒 記憶體檢查
            if ResourceMonitor.check_memory_threshold(config['memory_threshold_mb']):
                gc.collect()
            
            # 🔒 資源監控
            ResourceMonitor.log_resource_usage()
        
        SyncMetrics.record_sync_end('sync_jenkins_builds', success=True)
    
    except Exception as e:
        SyncMetrics.record_sync_end('sync_jenkins_builds', success=False)
        raise
```

**驗收標準**：
- ✅ 支援完整同步模式（`full_sync=True`）
- ✅ 可自動清理孤立 Builds
- ✅ CPU 使用率不超過 70%（正常情況）
- ✅ 記憶體使用不超過 1GB
- ✅ 自適應策略生效（CPU > 90% 時暫停）
- ✅ 測試通過

---

#### 3.3 創建自適應策略（第 14 天）

**文件**：`backend/api/tasks.py`（或 `backend/library/utils/adaptive_strategy.py`）

**任務**：
- [ ] 創建 `AdaptiveSyncStrategy` 類別
- [ ] 實作 `get_batch_size()` 方法
- [ ] 實作 `get_rest_time()` 方法
- [ ] 編寫測試

**邏輯**：
```python
class AdaptiveSyncStrategy:
    @staticmethod
    def get_batch_size():
        cpu = ResourceMonitor.get_cpu_percent()
        if cpu > 90: return 0   # 暫停
        if cpu > 70: return 10  # 最小批次
        if cpu > 50: return 30  # 減少批次
        return 50               # 正常批次
    
    @staticmethod
    def get_rest_time():
        cpu = ResourceMonitor.get_cpu_percent()
        if cpu > 70: return 5   # 休息更久
        if cpu > 50: return 3
        return 2                # 正常休息
```

**驗收標準**：
- ✅ 可根據 CPU 負載動態調整
- ✅ 測試通過

---

#### 3.4 添加 JenkinsClient.get_all_builds()（第 15 天）

**文件**：`backend/library/services/jenkins_client.py`

**任務**：
- [ ] 實作 `get_all_builds(job_name)` 方法
- [ ] 支援分頁獲取（如果 Builds 很多）
- [ ] 整合速率限制
- [ ] 編寫測試

**實現**：
```python
def get_all_builds(self, job_name, include_details=False):
    """
    獲取 Job 的所有 Builds
    
    Args:
        job_name: Job 名稱
        include_details: 是否包含詳細資訊
        
    Returns:
        list: Builds 清單
    """
    url = f"{self.base_url}/job/{job_name}/api/json"
    params = {
        'tree': 'builds[number,url,result,timestamp,duration]'
    }
    
    response = self._request('GET', url, params=params)
    data = response.json()
    return data.get('builds', [])
```

**驗收標準**：
- ✅ 可正確獲取所有 Builds
- ✅ 速率限制生效
- ✅ 測試通過

---

#### 3.5 更新 Celery Beat 排程（第 15 天）

**文件**：`backend/network_toolbox/celery.py`

**任務**：
- [ ] 更新 `sync_jenkins_builds` 排程配置
- [ ] 添加三層排程策略
- [ ] 更新 `sync_all_jenkins_jobs_task` 排程
- [ ] 測試排程

**三層排程策略**：
```python
app.conf.beat_schedule = {
    # 🔒 第 1 層：快速同步（每 10 分鐘）
    'sync-jenkins-builds-fast': {
        'task': 'api.tasks.sync_jenkins_builds',
        'schedule': crontab(minute='*/10'),  # 每 10 分鐘
        'kwargs': {
            'full_sync': False,           # 快速模式
            'cleanup_orphaned': False,    # 不清理
            'max_builds_per_job': 20,
        },
    },
    
    # 🔒 第 2 層：Jobs 同步 + 清理（每小時）
    'sync-jenkins-jobs-hourly': {
        'task': 'api.tasks.sync_all_jenkins_jobs_task',
        'schedule': crontab(minute=0),    # 每小時
        'kwargs': {
            'cleanup_orphaned': True,     # 清理孤立 Jobs
        },
    },
    
    # 🔒 第 3 層：完整同步 + 清理（每天凌晨 2 點）
    'sync-jenkins-builds-full': {
        'task': 'api.tasks.sync_jenkins_builds',
        'schedule': crontab(hour=2, minute=0),  # 每天 2:00
        'kwargs': {
            'full_sync': True,            # 完整模式
            'cleanup_orphaned': True,     # 清理孤立 Builds
            'max_builds_per_job': 100,
        },
    },
    
    # 驗證任務（每天凌晨 3 點）
    'validate-jenkins-data-daily': {
        'task': 'api.tasks.validate_jenkins_data',
        'schedule': crontab(hour=3, minute=0),
        'kwargs': {'auto_cleanup': False},
    },
}
```

**驗收標準**：
- ✅ 三層排程已註冊
- ✅ 可手動觸發測試
- ✅ 時間配置正確

---

#### 3.6 完整測試（第 16-17 天）

**任務**：
- [ ] 單元測試（所有新功能）
- [ ] 整合測試（完整同步流程）
- [ ] 性能測試（CPU、記憶體）
- [ ] 壓力測試（大量 Jobs/Builds）
- [ ] 異常測試（網路錯誤、超時等）

**測試清單**：

##### 3.6.1 單元測試
```bash
# 測試 sync_all_jenkins_jobs_task
docker exec nt-django python manage.py test tests/unit/backend/test_sync_jenkins_jobs.py

# 測試 sync_jenkins_builds
docker exec nt-django python manage.py test tests/unit/backend/test_sync_jenkins_builds.py

# 測試 AdaptiveSyncStrategy
docker exec nt-django python manage.py test tests/unit/backend/test_adaptive_strategy.py
```

##### 3.6.2 整合測試
```bash
# 測試完整同步流程
docker exec nt-django python manage.py test tests/integration/test_jenkins_sync_flow.py
```

##### 3.6.3 性能測試
```python
# tests/performance/test_sync_performance.py
import psutil
import time

def test_sync_performance():
    """測試同步任務的性能"""
    process = psutil.Process()
    
    # 記錄初始狀態
    start_cpu = process.cpu_percent(interval=1.0)
    start_memory = process.memory_info().rss / 1024 / 1024
    
    # 執行同步
    from api.tasks import sync_jenkins_builds
    result = sync_jenkins_builds(server_id=1)
    
    # 記錄結束狀態
    end_cpu = process.cpu_percent(interval=1.0)
    end_memory = process.memory_info().rss / 1024 / 1024
    
    # 驗證
    assert end_cpu < 80, f'CPU 使用率過高: {end_cpu}%'
    assert end_memory < 1024, f'記憶體使用過高: {end_memory}MB'
    assert result['success'] == True
```

##### 3.6.4 壓力測試
```bash
# 模擬大量 Jobs 和 Builds
docker exec nt-django python create_jenkins_test_data.py --jobs 500 --builds 10000

# 執行同步測試
docker exec nt-django python manage.py test tests/performance/test_large_sync.py
```

**驗收標準**：
- ✅ 所有單元測試通過
- ✅ 整合測試通過
- ✅ CPU 使用率 < 80%（正常情況）
- ✅ 記憶體使用 < 1GB
- ✅ 可處理 500+ Jobs, 10000+ Builds
- ✅ 異常情況處理正確

---

#### 3.7 文檔更新（第 18 天）

**任務**：
- [ ] 更新 API 文檔
- [ ] 更新開發者文檔
- [ ] 創建使用指南
- [ ] 創建故障排除指南

**文檔清單**：
- `docs/api/JENKINS_SYNC_API.md` - API 參數說明
- `docs/development/JENKINS_SYNC_ARCHITECTURE.md` - 架構文檔
- `docs/quickstart/JENKINS_SYNC_USAGE.md` - 使用指南
- `docs/troubleshooting/JENKINS_SYNC_ISSUES.md` - 故障排除

---

#### 3.8 部署準備（第 19 天）

**任務**：
- [ ] 更新 `requirements.txt`
- [ ] 更新 `docker-compose.yml`（如需要）
- [ ] 創建資料庫遷移（如需要）
- [ ] 準備部署腳本
- [ ] 創建回滾計畫

**部署檢查清單**：
```bash
# 1. 更新依賴
docker exec nt-django pip install -r requirements.txt

# 2. 執行遷移
docker exec nt-django python manage.py makemigrations
docker exec nt-django python manage.py migrate

# 3. 收集靜態檔案
docker exec nt-django python manage.py collectstatic --noinput

# 4. 重啟服務
docker compose restart django

# 5. 驗證 Celery Beat
docker exec nt-django celery -A network_toolbox beat -l info
```

**回滾計畫**：
```bash
# 如果出現問題，快速回滾
git checkout <previous-commit>
docker compose down
docker compose up -d --build
```

---

#### 3.9 灰度發佈（第 20 天）

**策略**：
1. 先部署到測試環境
2. 觀察 24 小時
3. 逐步部署到生產環境

**測試環境部署**：
```bash
# 1. 部署到 test 環境
git checkout main
docker compose -f docker-compose.test.yml up -d --build

# 2. 手動觸發測試
docker exec nt-django-test python manage.py shell
>>> from api.tasks import sync_jenkins_builds
>>> sync_jenkins_builds.delay(server_id=1)

# 3. 監控 24 小時
# - CPU 使用率
# - 記憶體使用
# - 錯誤日誌
# - 資料一致性
```

**生產環境部署**（確認測試無誤後）：
```bash
# 1. 備份資料庫
docker exec nt-postgres pg_dump -U postgres network_toolbox > backup.sql

# 2. 部署
git checkout main
docker compose up -d --build

# 3. 驗證
curl http://localhost/api/jenkins-servers/
docker compose logs -f django

# 4. 監控
# 持續監控 CPU、記憶體、日誌
```

---

#### 3.10 階段 3 總結報告（第 20 天）

**生成報告**：`docs/reports/PHASE3_SYNC_IMPROVEMENT_REPORT.md`

**報告內容**：
- 實施的改進清單
- 測試結果摘要
- 性能對比（改進前後）
- 部署情況
- 監控數據
- 後續優化建議

---

## 📊 總體時間表

```
┌────────────────────────────────────────────────────────┐
│  第 1 週                                                │
│  階段 1：立即清理與準備                                │
│  ├─ Day 1: 創建清理腳本                                │
│  ├─ Day 2: 測試和執行清理                              │
│  ├─ Day 3: 驗證效果 + 總結                             │
│  └─ 成果：孤立資料已清理                               │
└────────────────────────────────────────────────────────┘
                        ↓
┌────────────────────────────────────────────────────────┐
│  第 2 週                                                │
│  階段 2：系統保護機制實施                              │
│  ├─ Day 4-5: 工具模組開發                              │
│  ├─ Day 6: JenkinsClient 改進                          │
│  ├─ Day 7: 定期驗證任務 + Celery 配置                  │
│  ├─ Day 8: 系統配置 + 文檔                             │
│  ├─ Day 9: 測試 + 總結                                 │
│  └─ 成果：保護機制已就緒                               │
└────────────────────────────────────────────────────────┘
                        ↓
┌────────────────────────────────────────────────────────┐
│  第 3-4 週                                              │
│  階段 3：同步機制改進                                  │
│  ├─ Day 10-11: sync_all_jenkins_jobs_task 改進         │
│  ├─ Day 12-14: sync_jenkins_builds 改進                │
│  ├─ Day 15: get_all_builds + Beat 排程更新             │
│  ├─ Day 16-17: 完整測試                                │
│  ├─ Day 18: 文檔更新                                   │
│  ├─ Day 19: 部署準備                                   │
│  ├─ Day 20: 灰度發佈 + 總結                            │
│  └─ 成果：完整解決方案上線                             │
└────────────────────────────────────────────────────────┘
```

---

## 📋 最終檢查清單

### 功能完整性

- [ ] 手動清理腳本可用
- [ ] 定期驗證任務運行正常
- [ ] sync_all_jenkins_jobs_task 可自動清理孤立 Jobs
- [ ] sync_jenkins_builds 可自動清理孤立 Builds
- [ ] 支援快速同步和完整同步
- [ ] 三層排程策略已配置

### 保護機制

- [ ] 任務互斥鎖生效
- [ ] 速率限制生效
- [ ] 批次處理正常
- [ ] 資源監控正常
- [ ] 自適應策略生效
- [ ] 異常檢測正常

### 性能指標

- [ ] CPU 使用率 < 80%（正常情況）
- [ ] 記憶體使用 < 1GB
- [ ] 可處理 500+ Jobs
- [ ] 可處理 10000+ Builds
- [ ] API 請求速率符合限制

### 測試覆蓋

- [ ] 單元測試覆蓋率 > 80%
- [ ] 整合測試通過
- [ ] 性能測試通過
- [ ] 壓力測試通過
- [ ] 異常測試通過

### 文檔完整性

- [ ] API 文檔已更新
- [ ] 架構文檔已更新
- [ ] 使用指南已創建
- [ ] 故障排除指南已創建
- [ ] 三個階段總結報告已生成

### 監控告警

- [ ] Celery Beat 正常運行
- [ ] 定期任務正常執行
- [ ] 日誌記錄詳細
- [ ] 監控指標正常
- [ ] 異常告警機制生效

---

## 🎯 成功標準

### 資料一致性

- ✅ Web UI 顯示的 Jobs/Builds 與 Jenkins Server 一致
- ✅ 沒有孤立的 Jobs 或 Builds
- ✅ 定期驗證任務發現異常立即告警

### 系統穩定性

- ✅ CPU 使用率正常（< 80%）
- ✅ 記憶體使用正常（< 1GB）
- ✅ 沒有任務卡死或超時
- ✅ 可處理大規模資料

### 可維護性

- ✅ 代碼結構清晰
- ✅ 文檔完整
- ✅ 測試覆蓋充分
- ✅ 日誌詳細易讀
- ✅ 監控指標完善

---

## 📞 支援和協助

### 遇到問題時

1. **查看日誌**：
   ```bash
   # Django 日誌
   tail -f logs/django.log
   
   # Celery 日誌
   docker compose logs -f django | grep Celery
   ```

2. **檢查資源使用**：
   ```bash
   docker stats nt-django
   ```

3. **查看任務狀態**：
   ```bash
   docker exec nt-django celery -A network_toolbox inspect active
   ```

4. **回滾到上一版本**：
   ```bash
   git checkout <previous-commit>
   docker compose restart django
   ```

### 聯絡方式

- **開發團隊**：Network Toolbox Team
- **文檔位置**：`docs/` 目錄
- **問題追蹤**：GitHub Issues

---

**最後更新**：2025-11-21  
**維護者**：Network Toolbox Team  
**狀態**：待實施（詳細規劃完成）
