# CPU 過載問題分析與改善計畫

**日期**：2025-12-19  
**環境**：Network Toolbox - Docker Compose + Celery 定時任務系統  
**問題**：運行一段時間後，Ubuntu 系統 CPU 使用率達到 100%

---

## 📊 問題摘要

根據分析，您的專案有 **23 個週期性 Celery 任務**，其中多個任務同時執行會導致 CPU 過載。這不是單一原因，而是多個因素累積的結果。

---

## 🔍 已啟用的週期性任務清單

### 高頻率任務（每 1-5 分鐘）

| 任務名稱 | 頻率 | 預估 CPU 負載 | 風險等級 |
|---------|------|--------------|---------|
| `sync_active_jenkins_builds` | 每 **1 分鐘** | ⭐⭐⭐ | 🔴 高 |
| `check_nas_connection_task` | 每 **5 分鐘** | ⭐⭐ | 🟢 低 |
| `check_all_ipxe_network_quality_task` | 每 **5 分鐘** | ⭐⭐⭐ | 🟡 中 |
| `check_gitlab_connection_task` | 每 **5 分鐘** | ⭐⭐ | 🟢 低 |
| `auto_validate_completed_builds` | 每 **5 分鐘** | ⭐⭐⭐ | 🟡 中 |
| `collect_network_quality_task` | 每 **5 分鐘** | ⭐⭐⭐ | 🟡 中 |

### 中頻率任務（每 10-15 分鐘）

| 任務名稱 | 頻率 | 預估 CPU 負載 | 風險等級 |
|---------|------|--------------|---------|
| `sync_all_dhcp_logs_task` | 每 **10 分鐘** | ⭐⭐⭐ | 🟡 中 |
| `sync_jenkins_builds` | 每 **10 分鐘** | ⭐⭐⭐⭐ | 🔴 高 |
| `sync_all_dhcp_leases_task` | 每 **15 分鐘** | ⭐⭐⭐ | 🟡 中 |

### 低頻率任務（每小時）

| 任務名稱 | 頻率 | 預估 CPU 負載 | 風險等級 |
|---------|------|--------------|---------|
| `auto_identify_switches_task` | 每小時整點 | ⭐⭐⭐ | 🟡 中 |
| `sync_all_jenkins_jobs_task` | 每小時整點 | ⭐⭐⭐⭐⭐ | 🔴 極高 |
| `auto_store_workspaces` | 每小時 :15 | ⭐⭐⭐⭐⭐ | 🔴 極高 |
| `auto_store_jenkins_builds_task` | 每小時 :45 | ⭐⭐⭐⭐⭐ | 🔴 極高 |

### 每日任務

| 任務名稱 | 執行時間 | 預估 CPU 負載 | 風險等級 |
|---------|---------|--------------|---------|
| `validate_jenkins_data` | 02:00 | ⭐⭐⭐ | 🟡 中 |
| `auto_analyze_missing_fatal_errors_task` | 02:30 | ⭐⭐⭐⭐ | 🔴 高 |
| `cleanup_old_dhcp_logs_task` | 03:00 | ⭐⭐ | 🟢 低 |
| `cleanup_old_quality_records_task` | 03:30 | ⭐⭐ | 🟢 低 |
| `sync_all_dhcp_scopes_task` | 04:30 | ⭐⭐⭐ | 🟡 中 |
| `clean_expired_ansible_caches` | 05:00 | ⭐⭐ | 🟢 低 |

### 每週/每月任務

| 任務名稱 | 執行時間 | 預估 CPU 負載 | 風險等級 |
|---------|---------|--------------|---------|
| `cleanup_orphaned_jenkins_data` | 每週日 01:00 | ⭐⭐⭐⭐ | 🔴 高 |
| `cleanup_old_nas_jenkins_storage_task` | 每週日 03:00 | ⭐⭐⭐⭐⭐ | 🔴 極高 |
| `update_oui_database_task` | 每月 1 號 02:00 | ⭐⭐ | 🟢 低 |
| `cleanup_old_jenkins_builds_task` | 每月 1 號 05:00 | ⭐⭐⭐⭐ | 🔴 高 |

---

## 🚨 主要 CPU 過載原因分析

### 原因 1：任務時間衝突（同時執行）

**問題**：多個重度任務在同一時間點執行

**衝突時間點**：

| 時間 | 同時執行的任務 | 總 CPU 負載 |
|------|---------------|------------|
| **:00** | `sync_all_jenkins_jobs` + `auto_identify_switches` + `sync_jenkins_builds` | ⭐⭐⭐⭐⭐⭐⭐⭐ |
| **:10** | `sync_all_dhcp_logs` + `sync_jenkins_builds` | ⭐⭐⭐⭐⭐⭐ |
| **:15** | `auto_store_workspaces` + `sync_all_dhcp_leases` | ⭐⭐⭐⭐⭐⭐⭐⭐ |
| **:45** | `auto_store_jenkins_builds` + `sync_all_dhcp_leases` | ⭐⭐⭐⭐⭐⭐⭐⭐ |

### 原因 2：每 1 分鐘執行的高頻任務

**`sync_active_jenkins_builds`** 每 1 分鐘執行一次：

```python
# celery.py:115
'sync-active-jenkins-builds-every-1-minute': {
    'task': 'api.tasks.sync_active_jenkins_builds',
    'schedule': crontab(minute='*/1'),  # ❌ 過於頻繁
}
```

**問題**：
- 即使沒有活躍 Builds，也會每分鐘執行
- 會對每個活躍 Build 進行多次 Jenkins API 調用
- 可能與其他 10 分鐘任務重疊

### 原因 3：批次處理過大

**`auto_store_jenkins_builds_task`** 批次太大：

```python
# celery.py:163
'kwargs': {
    'limit': 20  # 雖然已從 100 降低到 20，但仍可能過大
}
```

**問題**：
- 每個存儲任務會下載 Workspace + Console Log
- 觸發 Fatal Error 分析（CPU 密集）
- 與其他任務同時執行時會導致過載

### 原因 4：Celery Worker 併發數過高

```yaml
# docker-compose.yml:108
command: bash -c "... celery -A network_toolbox worker --loglevel=info --concurrency=8"
```

**問題**：
- 8 個併發 Worker 同時執行
- 當多個重度任務同時觸發時，CPU 負載會倍增
- 建議：將 concurrency 降低到 4-6

### 原因 5：缺乏全局 CPU 保護機制

雖然部分任務已實現 CPU 保護：

```python
# tasks.py（部分任務有實現）
cpu_percent = psutil.cpu_percent(interval=1)
if cpu_percent > 60.0:
    raise self.retry(countdown=300)
```

**但以下高風險任務缺乏 CPU 保護**：
- ❌ `sync_jenkins_builds`
- ❌ `sync_all_jenkins_jobs_task`
- ❌ `sync_active_jenkins_builds`
- ❌ `auto_identify_switches_task`

---

## ✅ 改善計畫

### 階段 1：立即修復（降低 CPU 負載 50%）

#### 1.1 調整 Celery Worker 併發數

**修改 `docker-compose.yml`**：

```yaml
# 第 108 行
celery_worker:
    # ...
    command: bash -c "bash /app/mount_nas.sh || true && celery -A network_toolbox worker --loglevel=info --concurrency=4"  # ✅ 從 8 改為 4
```

#### 1.2 降低高頻任務頻率

**修改 `backend/network_toolbox/celery.py`**：

```python
# 任務 10-1：改為每 2 分鐘（從 1 分鐘改為 2 分鐘）
'sync-active-jenkins-builds-every-2-minutes': {
    'task': 'api.tasks.sync_active_jenkins_builds',
    'schedule': crontab(minute='*/2'),  # ✅ 每 2 分鐘
    'kwargs': {
        'server_id': None,
    },
    'options': {
        'expires': 110,  # 任務超時 110 秒
    }
},
```

#### 1.3 錯開任務執行時間

**修改 `backend/network_toolbox/celery.py`**：

```python
# 任務 11：Workspace 存儲（從 :15 改為 :20）
'auto-store-jenkins-workspaces-hourly': {
    'task': 'api.tasks.auto_store_workspaces',
    'schedule': crontab(minute=20),  # ✅ 改為 :20（避開 :15 的 leases 同步）
    # ...
},

# 任務 12：Builds 存儲（從 :45 改為 :50）
'auto-store-jenkins-builds-every-hour': {
    'task': 'api.tasks.auto_store_jenkins_builds_task',
    'schedule': crontab(minute=50),  # ✅ 改為 :50
    'kwargs': {
        'limit': 10  # ✅ 降低到 10 個（從 20 改為 10）
    },
    # ...
},

# 任務 14：Jobs 同步（從 :00 改為 :05）
'sync-jenkins-jobs-hourly': {
    'task': 'api.tasks.sync_all_jenkins_jobs_task',
    'schedule': crontab(minute=5),  # ✅ 改為 :05（避開整點）
    # ...
},
```

---

### 階段 2：添加全局 CPU 保護（1-2 天內完成）

#### 2.1 為高風險任務添加 CPU 保護

**創建新文件 `backend/library/utils/cpu_protection.py`**：

```python
"""
CPU 保護裝飾器

為 Celery 任務提供 CPU 使用率保護機制
"""
import psutil
import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)


def cpu_protected_task(
    high_threshold: float = 70.0,
    low_threshold: float = 50.0,
    max_wait: int = 300,
    check_interval: int = 10
):
    """
    CPU 保護裝飾器
    
    當 CPU 使用率超過閾值時，延遲執行任務
    
    Args:
        high_threshold: CPU 高負載閾值（%），超過此值會等待
        low_threshold: CPU 恢復閾值（%），降到此值以下才繼續
        max_wait: 最長等待時間（秒）
        check_interval: 檢查間隔（秒）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            while True:
                cpu = psutil.cpu_percent(interval=1)
                
                if cpu < high_threshold:
                    logger.info(f'[CPU] {func.__name__} CPU 正常 ({cpu:.1f}%)，開始執行')
                    break
                
                if time.time() - start_time > max_wait:
                    logger.warning(
                        f'[CPU] {func.__name__} 等待超時 ({max_wait}s)，'
                        f'強制執行 (CPU: {cpu:.1f}%)'
                    )
                    break
                
                logger.info(
                    f'[CPU] {func.__name__} CPU 過高 ({cpu:.1f}%)，'
                    f'等待降至 {low_threshold}% 以下...'
                )
                time.sleep(check_interval)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

#### 2.2 在高風險任務中使用保護

**修改 `backend/api/tasks.py`**：

```python
from library.utils.cpu_protection import cpu_protected_task

@shared_task(...)
@cpu_protected_task(high_threshold=70.0, low_threshold=50.0)
def sync_jenkins_builds(self, server_id=None, max_builds_per_job=20, max_age_days=3):
    # ... 原有邏輯
```

---

### 階段 3：優化任務調度策略（1 週內完成）

#### 3.1 新的任務時間表

| 時間 | 任務 | 變更說明 |
|------|------|---------|
| :00 | `auto_identify_switches` | 保持不變 |
| :02 | `sync_active_jenkins_builds` | 每 2 分鐘（降頻） |
| :05 | `sync_all_jenkins_jobs` | 從 :00 移動 |
| :10 | `sync_all_dhcp_logs`, `sync_jenkins_builds` | 保持不變 |
| :15 | `sync_all_dhcp_leases` | 保持不變 |
| :20 | `auto_store_workspaces` | 從 :15 移動 |
| :30 | `cleanup_old_quality_records` | 從 03:30 移動（減少凌晨負載） |
| :50 | `auto_store_jenkins_builds` | 從 :45 移動，批次降為 10 |

#### 3.2 考慮使用 Celery 速率限制

**修改 `backend/api/tasks.py`**：

```python
@shared_task(
    bind=True,
    name='api.tasks.store_jenkins_build_task',
    rate_limit='5/m',  # ✅ 每分鐘最多 5 個
    # ...
)
def store_jenkins_build_task(self, build_id: int):
    # ...
```

---

### 階段 4：長期監控和調優（持續進行）

#### 4.1 添加 Prometheus 監控（可選）

**安裝 celery-exporter**：

```yaml
# docker-compose.yml 添加
celery_exporter:
    image: danihodovic/celery-exporter:latest
    container_name: nt-celery-exporter
    environment:
      - CE_BROKER_URL=redis://redis:6379/0
    ports:
      - "9808:9808"
    depends_on:
      - redis
    networks:
      - nt_network
```

#### 4.2 使用 Flower 監控

已啟用的 Flower：http://localhost:5555

**監控指標**：
- 活躍任務數（建議 < 10）
- 任務成功率（建議 > 95%）
- 任務執行時間（建議 < 任務間隔的 80%）

---

## 📋 快速修復腳本

創建一個修復腳本以快速應用最重要的變更：

### 修改 `docker-compose.yml`

```yaml
# celery_worker 服務
# 第 108 行，將 concurrency=8 改為 concurrency=4
command: bash -c "bash /app/mount_nas.sh || true && celery -A network_toolbox worker --loglevel=info --concurrency=4"
```

### 修改 `backend/network_toolbox/celery.py`

需要修改的位置和內容：

1. **第 115-123 行**：將 `sync_active_jenkins_builds` 從每 1 分鐘改為每 2 分鐘
2. **第 134-143 行**：將 `auto_store_workspaces` 從 minute=15 改為 minute=20
3. **第 147-157 行**：將 `auto_store_jenkins_builds_task` 從 minute=45 改為 minute=50，limit 從 20 改為 10
4. **第 178-188 行**：將 `sync_all_jenkins_jobs_task` 從 minute=0 改為 minute=5

---

## 🎯 預期效果

| 指標 | 調整前 | 調整後 |
|------|--------|--------|
| CPU 使用率（高峰） | 80-100% | 40-60% |
| 併發 Worker 數 | 8 | 4 |
| 每分鐘任務觸發數 | ~10 | ~5 |
| 任務時間衝突 | 嚴重 | 輕微 |
| 系統穩定性 | 不穩定 | 穩定 |

---

## 📚 相關文檔

- [Jenkins Build 同步 CPU 100% 問題分析](./JENKINS_BUILD_SYNC_CPU_100_ANALYSIS.md)
- [CPU 100% 分析報告](./CPU_100_ANALYSIS_REPORT.md)
- [Celery 配置文件](../../backend/network_toolbox/celery.py)
- [Celery Tasks 實現](../../backend/api/tasks.py)

---

## ⚠️ 注意事項

1. **修改後需重啟服務**：
   ```bash
   docker compose restart celery_worker celery_beat
   ```

2. **監控效果**：
   ```bash
   # 監控 CPU 使用率
   docker stats nt-celery-worker
   
   # 檢查 Flower
   http://localhost:5555
   ```

3. **如果問題仍然存在**：
   - 進一步降低 concurrency 到 2
   - 考慮禁用部分非必要任務
   - 檢查是否有任務進入無限循環

---

**最後更新**：2025-12-19
