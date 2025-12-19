# CPU 保護機制使用指南

## 概述

本專案提供 `cpu_protected_task` 裝飾器，用於保護 Celery 任務免受 CPU 過載影響。該機制可以：

1. **CPU 檢測**：在任務執行前檢測系統 CPU 使用率
2. **智能等待**：當 CPU 過高時，等待至 CPU 降低後再執行
3. **超時跳過**：如果等待時間過長，可以選擇跳過該任務（避免任務堆積）
4. **統計追蹤**：記錄任務執行、跳過、等待的統計數據

---

## 快速開始

### 基本使用

```python
from library.utils.cpu_protection import cpu_protected_task

@cpu_protected_task(
    high_threshold=70.0,    # CPU > 70% 時等待
    low_threshold=50.0,     # 等到 CPU < 50% 才執行
    max_wait=180,           # 最多等待 3 分鐘
    skip_on_timeout=True    # 等太久則跳過任務
)
def my_heavy_task():
    # 任務邏輯
    pass
```

### 與 Celery @shared_task 結合使用

**重要**：`@cpu_protected_task` 必須放在 `@shared_task` **之後**（更靠近函數定義）

```python
from celery import shared_task
from library.utils.cpu_protection import cpu_protected_task

@shared_task(bind=True, name='api.tasks.my_task')
@cpu_protected_task(high_threshold=70.0, skip_on_timeout=True)
def my_celery_task(self):
    # 任務邏輯
    pass
```

---

## 應用到現有的 Jenkins 同步任務

### 1. sync_jenkins_builds（每 10 分鐘執行，重量級任務）

**修改前：**
```python
@shared_task(
    bind=True,
    name='api.tasks.sync_jenkins_builds',
    max_retries=2,
    default_retry_delay=300,
    time_limit=3600,
    soft_time_limit=3300
)
def sync_jenkins_builds(self, server_id=None, max_builds_per_job=20, max_age_days=3):
    # ...
```

**修改後：**
```python
from library.utils.cpu_protection import cpu_protected_task

@shared_task(
    bind=True,
    name='api.tasks.sync_jenkins_builds',
    max_retries=2,
    default_retry_delay=300,
    time_limit=3600,
    soft_time_limit=3300
)
@cpu_protected_task(
    high_threshold=70.0,    # CPU > 70% 時等待
    low_threshold=50.0,     # 等到 CPU < 50% 才執行
    max_wait=300,           # 最多等待 5 分鐘
    skip_on_timeout=True    # 等太久則跳過（10 分鐘後下一個週期會再執行）
)
def sync_jenkins_builds(self, server_id=None, max_builds_per_job=20, max_age_days=3):
    # ...
```

### 2. sync_active_jenkins_builds（每 1 分鐘執行，輕量級但高頻）

**修改後：**
```python
@shared_task(
    bind=True,
    name='api.tasks.sync_active_jenkins_builds',
    max_retries=2,
    time_limit=60
)
@cpu_protected_task(
    high_threshold=80.0,    # CPU > 80% 時才等待（輕量任務可提高閾值）
    low_threshold=60.0,     # 等到 CPU < 60% 才執行
    max_wait=30,            # 最多等待 30 秒（因為是 1 分鐘執行一次）
    skip_on_timeout=True    # 等太久則跳過
)
def sync_active_jenkins_builds(self, server_id=None):
    # ...
```

### 3. sync_all_jenkins_jobs_task（每 30 分鐘執行）

**修改後：**
```python
@shared_task(
    bind=True,
    name='api.tasks.sync_all_jenkins_jobs_task',
    max_retries=2,
    default_retry_delay=300,
    time_limit=1800,
    soft_time_limit=1650
)
@cpu_protected_task(
    high_threshold=70.0,
    low_threshold=50.0,
    max_wait=300,           # 最多等待 5 分鐘
    skip_on_timeout=True
)
def sync_all_jenkins_jobs_task(self, server_id=None):
    # ...
```

---

## 配置參數說明

| 參數 | 預設值 | 說明 |
|------|--------|------|
| `high_threshold` | 70.0 | CPU 使用率超過此值時開始等待 |
| `low_threshold` | 50.0 | CPU 使用率低於此值時才執行任務 |
| `max_wait` | 180 | 最長等待時間（秒） |
| `check_interval` | 5 | 等待時檢查 CPU 的間隔（秒） |
| `skip_on_timeout` | True | 等待超時時是否跳過任務 |

### 不同類型任務的建議配置

| 任務類型 | high_threshold | low_threshold | max_wait | skip_on_timeout |
|----------|----------------|---------------|----------|-----------------|
| 高頻輕量任務（1分鐘） | 80.0 | 60.0 | 30 | True |
| 中頻中量任務（10分鐘） | 70.0 | 50.0 | 180 | True |
| 低頻重量任務（30分鐘+） | 70.0 | 50.0 | 300 | True |
| 重要不可跳過任務 | 85.0 | 70.0 | 600 | False |

---

## 進階使用

### 手動檢測 CPU（不使用裝飾器）

```python
from library.utils.cpu_protection import check_cpu_before_task, TaskCPUGuard

# 方式 1：使用函數
can_run, cpu_percent = check_cpu_before_task(
    threshold=70.0,
    max_wait=60,
    check_interval=5,
    skip_on_timeout=True
)
if can_run:
    # 執行任務邏輯
    pass
else:
    logger.info(f'任務因 CPU 過高 ({cpu_percent}%) 而跳過')

# 方式 2：使用上下文管理器
with TaskCPUGuard(threshold=70.0, max_wait=60) as guard:
    if guard.can_proceed:
        # 執行任務邏輯
        pass
```

### 查看 CPU 保護統計

```python
from library.utils.cpu_protection import get_cpu_protection_stats

stats = get_cpu_protection_stats()
print(f"總執行: {stats['total_tasks']}")
print(f"直接執行: {stats['executed_immediately']}")
print(f"等待後執行: {stats['executed_after_wait']}")
print(f"跳過: {stats['skipped']}")
print(f"平均等待: {stats['average_wait_time']:.1f}秒")
```

### 配置全局默認值

```python
from library.utils.cpu_protection import CPUProtectionConfig

# 修改全局默認配置
CPUProtectionConfig.HIGH_THRESHOLD = 75.0
CPUProtectionConfig.LOW_THRESHOLD = 55.0
CPUProtectionConfig.MAX_WAIT_TIME = 240
CPUProtectionConfig.SKIP_ON_TIMEOUT = True
```

---

## 日誌輸出範例

### 正常執行（CPU 不高）
```
[CPU保護] 任務 sync_jenkins_builds 開始 CPU 檢測
[CPU保護] 當前 CPU: 45.2%，閾值: 70.0%，可以執行
[CPU保護] 任務 sync_jenkins_builds 執行完成，耗時: 125.3 秒
```

### 等待後執行
```
[CPU保護] 任務 sync_jenkins_builds 開始 CPU 檢測
[CPU保護] 當前 CPU: 78.5%，超過閾值 70.0%，開始等待...
[CPU保護] 等待 5 秒後，CPU: 72.3%，繼續等待...
[CPU保護] 等待 10 秒後，CPU: 65.1%，繼續等待...
[CPU保護] 等待 15 秒後，CPU: 48.2%，低於 50.0%，開始執行
[CPU保護] 任務 sync_jenkins_builds 執行完成，耗時: 130.2 秒（等待: 15 秒）
```

### 跳過任務
```
[CPU保護] 任務 sync_jenkins_builds 開始 CPU 檢測
[CPU保護] 當前 CPU: 85.3%，超過閾值 70.0%，開始等待...
[CPU保護] 等待 180 秒後仍超過閾值（CPU: 75.2%），跳過任務
[CPU保護] 任務 sync_jenkins_builds 被跳過，原因: CPU 持續過高（等待 180 秒超時）
```

---

## 注意事項

### 1. 裝飾器順序
`@cpu_protected_task` 必須放在 `@shared_task` **之後**：

```python
# ✅ 正確
@shared_task(bind=True)
@cpu_protected_task(...)
def my_task(self):
    pass

# ❌ 錯誤
@cpu_protected_task(...)
@shared_task(bind=True)
def my_task(self):
    pass
```

### 2. bind=True 的任務
對於 `bind=True` 的 Celery 任務，`cpu_protected_task` 會正確處理 `self` 參數。

### 3. skip_on_timeout 的選擇
- **True**（推薦）：適合週期性任務，避免任務堆積
- **False**：適合重要的、不可跳過的任務（但可能導致任務排隊）

### 4. 與現有 CPU 監控的整合
本模組已與 `library/utils/system_monitor.py` 中的 `SystemMonitor` 類整合，提供一致的 CPU 監控數據。

---

## 相關文件

- [CPU 過載改善計畫](/docs/features/cpu-protection/CPU_OVERLOAD_IMPROVEMENT_PLAN.md)
- [系統監控工具](/library/utils/system_monitor.py)
- [CPU 保護模組](/library/utils/cpu_protection.py)

---

**最後更新**：2025-01-XX  
**作者**：Network Toolbox Team
