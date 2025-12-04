# 🛠️ Network Toolbox CPU 優化完整規劃書

> **文件版本**：v1.0  
> **建立日期**：2025-12-04  
> **狀態**：待執行  
> **優先級**：緊急

---

## 一、問題概述

### 1.1 現象描述

根據 CPU 監控圖表分析，系統在 **06:55-07:03** 和 **07:11-07:38** 期間出現明顯的 CPU 飆升現象，使用率從低點快速上升至高峰值。

### 1.2 影響範圍

- 系統響應速度下降
- 定時任務可能延遲或超時
- 整體服務穩定性受影響

### 1.3 根本原因

經過程式碼分析，發現以下主要問題：

1. **Celery Worker/Beat 重複運行**（最嚴重）
2. Celery Worker 並行度過高
3. 高頻定時任務
4. 整點任務時間衝突
5. React Dev Server Polling 機制

---

## 二、當前架構分析

### 2.1 容器架構

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Compose 服務                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ nt-django (Supervisor 管理)                          │   │
│  │ ├── [program:django] runserver                       │   │
│  │ ├── [program:celery-worker] ⚠️ 重複！               │   │
│  │ └── [program:celery-beat]   ⚠️ 重複！               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ nt-celery-worker (獨立容器)                          │   │
│  │ └── celery worker --concurrency=8                    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ nt-celery-beat (獨立容器)                            │   │
│  │ └── celery beat --scheduler DatabaseScheduler       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐    │
│  │ nt-react      │ │ nt-nginx      │ │ nt-postgres   │    │
│  │ (Polling 模式)│ │               │ │               │    │
│  └───────────────┘ └───────────────┘ └───────────────┘    │
│                                                             │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐    │
│  │ nt-redis      │ │ nt-adminer    │ │ nt-celery-    │    │
│  │               │ │               │ │ flower        │    │
│  └───────────────┘ └───────────────┘ └───────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 問題架構說明

**🔴 嚴重問題**：Celery 服務重複運行

| 來源 | Celery Worker | Celery Beat |
|------|---------------|-------------|
| nt-django (Supervisor) | ✅ 運行中 | ✅ 運行中 |
| nt-celery-worker | ✅ 運行中 | - |
| nt-celery-beat | - | ✅ 運行中 |
| **總計** | **2 套** | **2 套** |

**⚠️ 重要說明**：

**Q：兩套 Celery Worker 會不會分工執行不同任務？**

**A：不會！它們會競爭同一個隊列**

```
Redis 任務隊列 (celery)
       │
       ├── Worker #1 (nt-django) ──→ 搶到任務 A、C
       │
       └── Worker #2 (nt-celery-worker) ──→ 搶到任務 B、D
       
結果：任務被「瓜分」執行，看似正常
```

**但 Celery Beat 會造成任務重複觸發**：

```
Celery Beat #1 (nt-django)      → 00:00 觸發 sync_jenkins_jobs
Celery Beat #2 (nt-celery-beat) → 00:00 觸發 sync_jenkins_jobs

結果：同一任務被觸發 2 次，放入隊列 2 次！
```

**後果**：
- 每個定時任務被觸發 **2 次**（Beat 重複）
- CPU 負載 **翻倍**
- 資料庫寫入可能產生衝突

**📌 目前實際狀態**（2025-12-04 檢查）：
- `nt-django` 容器已停止（Exited）
- 只有獨立的 `nt-celery-worker` 和 `nt-celery-beat` 在運行
- **目前沒有重複問題**，但當 Django 容器重啟後會出現

---

## 三、問題清單與優先級

### 3.1 原始方案（架構調整）

| 優先級 | 問題 | 影響程度 | 修復複雜度 | 狀態 |
|--------|------|----------|------------|------|
| 🔴 P0 | Supervisor 與獨立容器的 Celery 重複運行 | 極高 | 低 | 待修復 |
| 🟠 P1 | Celery Worker 並行度過高 (concurrency=8) | 高 | 低 | 待修復 |
| 🟠 P2 | 高頻任務 `sync_active_jenkins_builds` 每 1 分鐘 | 高 | 低 | 待修復 |
| 🟡 P3 | 整點任務時間衝突 | 中 | 中 | 待修復 |
| 🟡 P4 | React Dev Server Polling 機制 | 中 | 低 | 待修復 |
| 🟢 P5 | Console Log 分析 CPU 消耗 | 低 | - | 已有保護機制 |

### 3.2 替代方案（CPU 保護增強）⭐ 推薦

| 優先級 | 問題 | 解決方案 | 修復複雜度 | 狀態 |
|--------|------|----------|------------|------|
| 🔴 P0-ALT | 大多數高頻任務沒有 CPU 保護 | 為所有高頻任務加入 CPU 檢查 | 中 | 待修復 |
| 🟠 P1-ALT | 缺乏統一的 CPU 保護裝飾器 | 創建可重用的 `@cpu_guard` 裝飾器 | 中 | 待修復 |
| 🟡 P2-ALT | CPU 保護邏輯分散各處 | 集中管理 CPU 閾值配置 | 低 | 待修復 |

**替代方案優點**：
- ✅ 不需要修改容器架構（Supervisor/Docker Compose）
- ✅ 任務會根據系統負載自動調節
- ✅ 保留現有的 Celery 架構彈性
- ✅ 更智能的資源管理

---

## 四、詳細修復計畫

---

## 🌟 替代方案：為高頻任務加入 CPU 保護（推薦）

### ALT-1：創建 CPU 保護裝飾器

#### 問題說明

目前只有少數任務（如 `auto_store_jenkins_build_task`）有 CPU 保護機制，大多數高頻任務缺乏保護。

#### 解決方案

創建一個通用的 `@cpu_guard` 裝飾器，可以輕鬆套用到任何 Celery 任務。

#### 新增檔案

- **檔案路徑**：`library/decorators/cpu_guard.py`

```python
"""
CPU 保護裝飾器

為 Celery 任務提供 CPU 負載保護機制，
當系統負載過高時自動跳過或延遲執行任務。

作者：Network Toolbox Team
創建時間：2025-12-04
"""

import functools
import logging
import time
from typing import Callable, Optional, Any, Dict

from library.utils.system_monitor import SystemMonitor

logger = logging.getLogger(__name__)


def cpu_guard(
    cpu_threshold: float = 80.0,
    wait_seconds: int = 0,
    max_wait_seconds: int = 300,
    check_interval: int = 10,
    skip_on_high_load: bool = True,
    task_name: Optional[str] = None
):
    """
    CPU 保護裝飾器
    
    當 CPU 使用率超過閾值時，根據設定跳過或等待執行任務。
    
    Args:
        cpu_threshold: CPU 使用率閾值 (預設 80%)
        wait_seconds: 初始等待秒數 (預設 0，不等待)
        max_wait_seconds: 最大等待秒數 (預設 300 秒)
        check_interval: 等待時的檢查間隔 (預設 10 秒)
        skip_on_high_load: 當超過 max_wait_seconds 後是否跳過 (預設 True)
        task_name: 任務名稱（用於日誌，預設使用函數名）
    
    Returns:
        裝飾後的函數
    
    使用範例:
        @shared_task
        @cpu_guard(cpu_threshold=80.0, wait_seconds=30)
        def my_heavy_task():
            # 任務邏輯
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            name = task_name or func.__name__
            
            try:
                monitor = SystemMonitor(sample_interval=0.5)
                metrics = monitor.get_current_metrics()
                current_cpu = metrics.cpu_percent
                
                # CPU 負載正常，直接執行
                if current_cpu < cpu_threshold:
                    logger.debug(
                        f'[CPU Guard] ✅ {name} - CPU: {current_cpu:.1f}% < {cpu_threshold}%，正常執行'
                    )
                    return func(*args, **kwargs)
                
                # CPU 負載過高
                logger.warning(
                    f'[CPU Guard] ⚠️  {name} - CPU: {current_cpu:.1f}% >= {cpu_threshold}%'
                )
                
                # 如果設定了等待時間，進入等待模式
                if wait_seconds > 0 or max_wait_seconds > 0:
                    total_waited = 0
                    effective_max_wait = max(wait_seconds, max_wait_seconds)
                    
                    while total_waited < effective_max_wait:
                        logger.info(
                            f'[CPU Guard] ⏳ {name} - 等待 CPU 負載降低，'
                            f'已等待 {total_waited}s / {effective_max_wait}s'
                        )
                        
                        time.sleep(check_interval)
                        total_waited += check_interval
                        
                        # 重新檢查 CPU
                        metrics = monitor.get_current_metrics()
                        current_cpu = metrics.cpu_percent
                        
                        if current_cpu < cpu_threshold:
                            logger.info(
                                f'[CPU Guard] ✅ {name} - CPU 降至 {current_cpu:.1f}%，開始執行'
                            )
                            return func(*args, **kwargs)
                    
                    # 等待超時
                    logger.warning(
                        f'[CPU Guard] ⏰ {name} - 等待超時 ({effective_max_wait}s)，'
                        f'CPU 仍在 {current_cpu:.1f}%'
                    )
                
                # 根據設定決定是否跳過
                if skip_on_high_load:
                    logger.warning(
                        f'[CPU Guard] ⏭️  {name} - 跳過本次執行（CPU: {current_cpu:.1f}%）'
                    )
                    return {
                        'success': False,
                        'skipped': True,
                        'reason': f'CPU 負載過高 ({current_cpu:.1f}% >= {cpu_threshold}%)',
                        'task_name': name
                    }
                else:
                    # 強制執行（不建議）
                    logger.warning(
                        f'[CPU Guard] ⚠️  {name} - 強制執行（CPU: {current_cpu:.1f}%）'
                    )
                    return func(*args, **kwargs)
                    
            except Exception as e:
                # 監控失敗時，仍然執行任務（保守策略）
                logger.error(
                    f'[CPU Guard] ❌ {name} - 監控失敗: {e}，繼續執行任務'
                )
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


def check_cpu_before_task(
    cpu_threshold: float = 80.0,
    task_name: str = "Unknown"
) -> Dict[str, Any]:
    """
    檢查 CPU 負載（非裝飾器版本，用於任務內部）
    
    Args:
        cpu_threshold: CPU 閾值
        task_name: 任務名稱
    
    Returns:
        {
            'can_proceed': bool,
            'cpu_percent': float,
            'threshold': float,
            'message': str
        }
    """
    try:
        monitor = SystemMonitor(sample_interval=0.5)
        metrics = monitor.get_current_metrics()
        current_cpu = metrics.cpu_percent
        
        can_proceed = current_cpu < cpu_threshold
        
        return {
            'can_proceed': can_proceed,
            'cpu_percent': current_cpu,
            'threshold': cpu_threshold,
            'message': (
                f'CPU {current_cpu:.1f}% < {cpu_threshold}%，可以執行'
                if can_proceed else
                f'CPU {current_cpu:.1f}% >= {cpu_threshold}%，建議跳過'
            )
        }
    except Exception as e:
        logger.error(f'[CPU Check] 監控失敗: {e}')
        return {
            'can_proceed': True,  # 監控失敗時允許執行
            'cpu_percent': -1,
            'threshold': cpu_threshold,
            'message': f'監控失敗: {e}，預設允許執行'
        }
```

---

### ALT-2：為高頻任務套用 CPU 保護

#### 需要保護的任務清單

| 任務名稱 | 頻率 | 建議 CPU 閾值 | 等待策略 |
|----------|------|---------------|----------|
| `sync_active_jenkins_builds` | 每 1 分鐘 | 75% | 跳過 |
| `sync_jenkins_builds` | 每 10 分鐘 | 80% | 等待 60s |
| `sync_all_dhcp_logs_task` | 每 10 分鐘 | 80% | 等待 60s |
| `sync_all_dhcp_leases_task` | 每 15 分鐘 | 80% | 等待 60s |
| `check_all_ipxe_network_quality_task` | 每 5 分鐘 | 75% | 跳過 |
| `check_nas_connection_task` | 每 5 分鐘 | 85% | 跳過 |
| `check_gitlab_connection_task` | 每 5 分鐘 | 85% | 跳過 |
| `auto_identify_switches_task` | 每小時 | 80% | 等待 120s |
| `sync_all_jenkins_jobs_task` | 每小時 | 80% | 等待 120s |

#### 修改方式示例

**修改檔案**：`backend/api/tasks.py`

**修改前**（以 `sync_active_jenkins_builds` 為例）：

```python
@shared_task(
    bind=True,
    name='api.tasks.sync_active_jenkins_builds',
    max_retries=2,
    time_limit=60
)
def sync_active_jenkins_builds(self, server_id=None):
    """高頻同步活躍的 Jenkins Builds"""
    start_time = time.time()
    logger.info('[Celery] 🚀 開始高頻同步活躍 Jenkins Builds')
    # ... 任務邏輯
```

**修改後**：

```python
from library.decorators.cpu_guard import cpu_guard

@shared_task(
    bind=True,
    name='api.tasks.sync_active_jenkins_builds',
    max_retries=2,
    time_limit=60
)
@cpu_guard(
    cpu_threshold=75.0,      # 較低閾值，因為是高頻任務
    wait_seconds=0,          # 不等待，直接跳過
    skip_on_high_load=True,
    task_name='sync_active_jenkins_builds'
)
def sync_active_jenkins_builds(self, server_id=None):
    """高頻同步活躍的 Jenkins Builds（含 CPU 保護）"""
    start_time = time.time()
    logger.info('[Celery] 🚀 開始高頻同步活躍 Jenkins Builds')
    # ... 任務邏輯
```

---

### ALT-3：集中管理 CPU 閾值配置

#### 新增檔案

- **檔案路徑**：`backend/network_toolbox/cpu_settings.py`

```python
"""
CPU 保護相關配置

集中管理所有任務的 CPU 閾值設定，
方便統一調整和維護。

作者：Network Toolbox Team
創建時間：2025-12-04
"""

# ============================================================================
# 全局 CPU 閾值設定
# ============================================================================

# 預設 CPU 閾值（適用於大多數任務）
DEFAULT_CPU_THRESHOLD = 80.0

# 高頻任務 CPU 閾值（較低，更敏感）
HIGH_FREQ_CPU_THRESHOLD = 75.0

# 關鍵任務 CPU 閾值（較高，確保執行）
CRITICAL_CPU_THRESHOLD = 90.0

# 輕量任務 CPU 閾值（更高，幾乎不跳過）
LIGHT_CPU_THRESHOLD = 85.0


# ============================================================================
# 任務專屬設定
# ============================================================================

TASK_CPU_SETTINGS = {
    # 高頻同步任務（每 1-5 分鐘）- 敏感，優先跳過
    'sync_active_jenkins_builds': {
        'cpu_threshold': 75.0,
        'wait_seconds': 0,
        'skip_on_high_load': True,
    },
    'check_all_ipxe_network_quality_task': {
        'cpu_threshold': 75.0,
        'wait_seconds': 0,
        'skip_on_high_load': True,
    },
    
    # 連接檢測任務（輕量）
    'check_nas_connection_task': {
        'cpu_threshold': 85.0,
        'wait_seconds': 0,
        'skip_on_high_load': True,
    },
    'check_gitlab_connection_task': {
        'cpu_threshold': 85.0,
        'wait_seconds': 0,
        'skip_on_high_load': True,
    },
    
    # 中頻同步任務（每 10-15 分鐘）- 可以等待
    'sync_jenkins_builds': {
        'cpu_threshold': 80.0,
        'wait_seconds': 60,
        'max_wait_seconds': 120,
        'skip_on_high_load': True,
    },
    'sync_all_dhcp_logs_task': {
        'cpu_threshold': 80.0,
        'wait_seconds': 60,
        'max_wait_seconds': 120,
        'skip_on_high_load': True,
    },
    'sync_all_dhcp_leases_task': {
        'cpu_threshold': 80.0,
        'wait_seconds': 60,
        'max_wait_seconds': 120,
        'skip_on_high_load': True,
    },
    
    # 低頻任務（每小時）- 較長等待時間
    'auto_identify_switches_task': {
        'cpu_threshold': 80.0,
        'wait_seconds': 120,
        'max_wait_seconds': 300,
        'skip_on_high_load': True,
    },
    'sync_all_jenkins_jobs_task': {
        'cpu_threshold': 80.0,
        'wait_seconds': 120,
        'max_wait_seconds': 300,
        'skip_on_high_load': True,
    },
}


def get_task_cpu_settings(task_name: str) -> dict:
    """
    獲取任務的 CPU 設定
    
    Args:
        task_name: 任務名稱
    
    Returns:
        CPU 設定字典
    """
    return TASK_CPU_SETTINGS.get(task_name, {
        'cpu_threshold': DEFAULT_CPU_THRESHOLD,
        'wait_seconds': 0,
        'skip_on_high_load': True,
    })
```

---

### ALT-4：完整任務修改清單

需要在 `backend/api/tasks.py` 中為以下任務加入 `@cpu_guard` 裝飾器：

| 任務函數名 | 行號（約） | CPU 閾值 | 策略 |
|------------|-----------|----------|------|
| `sync_active_jenkins_builds` | ~2191 | 75% | 跳過 |
| `sync_jenkins_builds` | ~1722 | 80% | 等待 60s |
| `sync_all_dhcp_logs_task` | ~467 | 80% | 等待 60s |
| `sync_all_dhcp_leases_task` | ~582 | 80% | 等待 60s |
| `check_all_ipxe_network_quality_task` | ~1009 | 75% | 跳過 |
| `check_nas_connection_task` | ~826 | 85% | 跳過 |
| `check_gitlab_connection_task` | ~902 | 85% | 跳過 |
| `auto_identify_switches_task` | ~1147 | 80% | 等待 120s |
| `sync_all_jenkins_jobs_task` | ~1417 | 80% | 等待 120s |

---

## 原始方案詳細說明（供參考）

---

### 4.1 🔴 P0：移除 Supervisor 中的 Celery（最高優先）

#### 問題說明

當前 `nt-django` 容器透過 Supervisor 啟動了 Celery Worker 和 Beat，但同時已有獨立的 `nt-celery-worker` 和 `nt-celery-beat` 容器在運行，導致服務重複。

#### 相關檔案

- **檔案路徑**：`backend/supervisord.conf`

#### 修改前

```properties
[supervisord]
nodaemon=true
logfile=/var/log/supervisor/supervisord.log
pidfile=/var/run/supervisord.pid
user=root

[unix_http_server]
file=/var/run/supervisor.sock
chmod=0700

[supervisorctl]
serverurl=unix:///var/run/supervisor.sock

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[program:celery-worker]
command=celery -A network_toolbox worker --loglevel=info
directory=/app
stdout_logfile=/app/logs/celery_worker.log
stderr_logfile=/app/logs/celery_worker_error.log
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=600
killasgroup=true
priority=998

[program:celery-beat]
command=celery -A network_toolbox beat --loglevel=info
directory=/app
stdout_logfile=/app/logs/celery_beat.log
stderr_logfile=/app/logs/celery_beat_error.log
autostart=true
autorestart=true
startsecs=10
priority=999

[program:django]
command=python manage.py runserver 0.0.0.0:8000
directory=/app
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
autostart=true
autorestart=true
startsecs=5
priority=1000
```

#### 修改後

```properties
[supervisord]
nodaemon=true
logfile=/var/log/supervisor/supervisord.log
pidfile=/var/run/supervisord.pid
user=root

[unix_http_server]
file=/var/run/supervisor.sock
chmod=0700

[supervisorctl]
serverurl=unix:///var/run/supervisor.sock

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

# ============================================================================
# ⚠️  重要說明：Celery 服務已移至獨立容器
# ============================================================================
# Celery Worker 和 Beat 現在由以下獨立容器運行：
#   - nt-celery-worker: Celery Worker 服務（處理異步任務）
#   - nt-celery-beat: Celery Beat 排程器（定時任務調度）
#
# 請勿在此處啟動 Celery，否則會導致：
#   1. 任務重複執行
#   2. CPU 負載翻倍
#   3. 資料庫寫入衝突
#
# 修改日期：2025-12-04
# 修改原因：解決 CPU 飆升問題
# ============================================================================

[program:django]
command=python manage.py runserver 0.0.0.0:8000
directory=/app
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
autostart=true
autorestart=true
startsecs=5
priority=1000
```

#### 預期效果

- ✅ CPU 負載降低約 **50%**
- ✅ 消除任務重複執行
- ✅ 系統資源利用更合理

---

### 4.2 🟠 P1：降低 Celery Worker 並行度

#### 問題說明

`concurrency=8` 表示同時可執行 8 個任務，當多個 CPU 密集型任務同時觸發時，會瞬間佔滿所有 CPU 核心。

#### 相關檔案

- **檔案路徑**：`docker-compose.yml`
- **位置**：`celery_worker` 服務的 `command` 配置

#### 修改前

```yaml
celery_worker:
  build:
    context: ./backend
    dockerfile: Dockerfile
  container_name: nt-celery-worker
  restart: unless-stopped
  privileged: true
  cap_add:
    - SYS_ADMIN
  devices:
    - /dev/fuse
  command: bash -c "bash /app/mount_nas.sh || true && celery -A network_toolbox worker --loglevel=info --concurrency=8"
```

#### 修改後

```yaml
celery_worker:
  build:
    context: ./backend
    dockerfile: Dockerfile
  container_name: nt-celery-worker
  restart: unless-stopped
  privileged: true
  cap_add:
    - SYS_ADMIN
  devices:
    - /dev/fuse
  # ⚠️ concurrency 從 8 降低為 4，避免 CPU 過載
  # 修改日期：2025-12-04
  command: bash -c "bash /app/mount_nas.sh || true && celery -A network_toolbox worker --loglevel=info --concurrency=4"
```

#### 預期效果

- ✅ 限制同時執行的任務數量為 4 個
- ✅ 避免 CPU 被瞬間佔滿
- ⚠️ 任務執行時間可能略增（可接受的權衡）

---

### 4.3 🟠 P2：調整高頻任務執行間隔

#### 問題說明

`sync_active_jenkins_builds` 每 1 分鐘執行一次，頻率過高，持續消耗 CPU 資源。

#### 相關檔案

- **檔案路徑**：`backend/network_toolbox/celery.py`
- **位置**：`app.conf.beat_schedule` 中的 `sync-active-jenkins-builds-every-1-minute`

#### 修改前

```python
# 任務 10-1：【即時監控】活躍 Jenkins Builds 高頻同步（每 1 分鐘執行一次）
'sync-active-jenkins-builds-every-1-minute': {
    'task': 'api.tasks.sync_active_jenkins_builds',
    'schedule': crontab(minute='*/1'),  # 每 1 分鐘執行一次
    'kwargs': {
        'server_id': None,  # None 表示處理所有 Server
    },
    'options': {
        'expires': 55,    # 任務超時 55 秒（避免與下次重疊）
    }
},
```

#### 修改後

```python
# 任務 10-1：【即時監控】活躍 Jenkins Builds 高頻同步（每 3 分鐘執行一次）
# ⚠️ 從 1 分鐘調整為 3 分鐘，降低 CPU 負載
# 修改日期：2025-12-04
'sync-active-jenkins-builds-every-3-minutes': {
    'task': 'api.tasks.sync_active_jenkins_builds',
    'schedule': crontab(minute='*/3'),  # 每 3 分鐘執行一次
    'kwargs': {
        'server_id': None,  # None 表示處理所有 Server
    },
    'options': {
        'expires': 170,    # 任務超時 2 分 50 秒（避免與下次重疊）
    }
},
```

#### 預期效果

- ✅ 任務觸發頻率降低 **66%**
- ✅ 即時監控功能仍然有效（3 分鐘延遲可接受）
- ✅ CPU 負載顯著降低

---

### 4.4 🟡 P3：錯開整點任務執行時間

#### 問題說明

多個任務在整點（XX:00）同時觸發，造成 CPU 尖峰。

#### 當前衝突任務

| 任務名稱 | 當前時間 | 建議時間 | 說明 |
|----------|----------|----------|------|
| `sync-jenkins-jobs-hourly` | XX:00 | XX:00 | 維持不變（主要任務） |
| `auto-identify-switches-hourly` | XX:00 | XX:20 | 錯開 20 分鐘 |

#### 相關檔案

- **檔案路徑**：`backend/network_toolbox/celery.py`
- **位置**：`app.conf.beat_schedule` 中的 `auto-identify-switches-hourly`

#### 修改前

```python
# 任務 8：Switch 自動識別與更新（每小時，所有 DHCP Server）
'auto-identify-switches-hourly': {
    'task': 'api.tasks.auto_identify_switches_task',
    'schedule': crontab(minute=0),  # 每小時整點執行
    'kwargs': {
        'server_id': None  # None 表示處理所有 Server
    },
    'options': {
        'expires': 540,    # 任務超時 9 分鐘
    }
},
```

#### 修改後

```python
# 任務 8：Switch 自動識別與更新（每小時 XX:20，錯開整點任務）
# ⚠️ 從 XX:00 改為 XX:20，避免與其他整點任務衝突
# 修改日期：2025-12-04
'auto-identify-switches-hourly': {
    'task': 'api.tasks.auto_identify_switches_task',
    'schedule': crontab(minute=20),  # 每小時 XX:20 執行
    'kwargs': {
        'server_id': None  # None 表示處理所有 Server
    },
    'options': {
        'expires': 540,    # 任務超時 9 分鐘
    }
},
```

#### 預期效果

- ✅ 避免整點時多個任務同時執行
- ✅ CPU 負載分散到不同時間點
- ✅ 減少 CPU 尖峰

---

### 4.5 🟡 P4：優化 React Dev Server Polling

#### 問題說明

`CHOKIDAR_USEPOLLING=true` 會讓檔案監控使用輪詢機制，在 Docker Volume 掛載環境下會持續消耗 CPU。

#### 相關檔案

- **檔案路徑**：`docker-compose.yml`
- **位置**：`react` 服務的 `environment` 配置

#### 修改前

```yaml
react:
  build:
    context: ./frontend
    dockerfile: Dockerfile
  container_name: nt-react
  restart: unless-stopped
  environment:
    - CHOKIDAR_USEPOLLING=true
    - REACT_APP_API_URL=http://localhost:8000
```

#### 修改後（方案 A：移除 Polling）

```yaml
react:
  build:
    context: ./frontend
    dockerfile: Dockerfile
  container_name: nt-react
  restart: unless-stopped
  environment:
    # ⚠️ 移除 CHOKIDAR_USEPOLLING（Linux 環境通常不需要）
    # 如果熱重載失效，請參考方案 B
    # 修改日期：2025-12-04
    - REACT_APP_API_URL=http://localhost:8000
```

#### 修改後（方案 B：降低 Polling 頻率）

如果移除後熱重載失效，可使用此方案：

```yaml
react:
  build:
    context: ./frontend
    dockerfile: Dockerfile
  container_name: nt-react
  restart: unless-stopped
  environment:
    # ⚠️ 保留 Polling 但降低頻率（從預設 100ms 改為 3000ms）
    # 修改日期：2025-12-04
    - CHOKIDAR_USEPOLLING=true
    - CHOKIDAR_INTERVAL=3000
    - REACT_APP_API_URL=http://localhost:8000
```

#### 預期效果

- ✅ 減少持續性 CPU 消耗
- ⚠️ 方案 A：熱重載可能失效（需測試）
- ⚠️ 方案 B：熱重載延遲增加至 3 秒

---

## 五、執行計畫

### 方案選擇

| 方案 | 說明 | 適用場景 |
|------|------|----------|
| **替代方案（推薦）** | 為高頻任務加入 CPU 保護 | 希望保留現有架構，智能調節 |
| **原始方案** | 移除重複 Celery + 降低並行度 | 希望從根本解決重複問題 |
| **混合方案** | 兩者都做 | 追求最佳效果 |

---

### 5.0 替代方案執行計畫（推薦）⭐

> **目標**：為高頻任務加入 CPU 保護，無需修改容器架構  
> **預計時間**：20 分鐘  
> **影響**：只需重啟 celery_worker 和 django 容器

#### 階段一：創建 CPU 保護裝飾器

| 步驟 | 操作 | 檔案 |
|------|------|------|
| 1 | 創建 `cpu_guard.py` 裝飾器 | `library/decorators/cpu_guard.py` |
| 2 | 創建 `__init__.py` | `library/decorators/__init__.py` |
| 3 | 創建 CPU 設定檔 | `backend/network_toolbox/cpu_settings.py` |

#### 階段二：套用到高頻任務

| 步驟 | 任務 | 閾值 | 策略 |
|------|------|------|------|
| 4 | `sync_active_jenkins_builds` | 75% | 跳過 |
| 5 | `check_all_ipxe_network_quality_task` | 75% | 跳過 |
| 6 | `check_nas_connection_task` | 85% | 跳過 |
| 7 | `check_gitlab_connection_task` | 85% | 跳過 |
| 8 | `sync_jenkins_builds` | 80% | 等待 60s |
| 9 | `sync_all_dhcp_logs_task` | 80% | 等待 60s |
| 10 | `sync_all_dhcp_leases_task` | 80% | 等待 60s |
| 11 | `auto_identify_switches_task` | 80% | 等待 120s |
| 12 | `sync_all_jenkins_jobs_task` | 80% | 等待 120s |

#### 階段三：部署與驗證

```bash
# 1. 重啟容器以載入新代碼
docker compose restart django celery_worker celery_beat

# 2. 監控 CPU 和任務日誌
docker logs nt-celery-worker --tail 50 | grep "CPU Guard"

# 3. 觀察 CPU 使用率
watch -n 5 'docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}"'
```

#### 預期效果

- ✅ 當 CPU 超過閾值時，高頻任務自動跳過
- ✅ 重要任務會等待 CPU 降低後再執行
- ✅ 避免多個任務同時執行造成的 CPU 尖峰
- ✅ 保留現有架構的彈性

---

### 5.1 階段一：緊急修復（建議立即執行）

> **目標**：解決最嚴重的 CPU 問題  
> **預計時間**：10 分鐘  
> **影響**：需重啟 django 和 celery_worker 容器

| 步驟 | 操作 | 修改檔案 |
|------|------|----------|
| 1 | 移除 Supervisor 中的 Celery | `backend/supervisord.conf` |
| 2 | 降低 Celery Worker 並行度 | `docker-compose.yml` |

**執行命令**：

```bash
# 1. 編輯檔案（手動或由 AI 執行）

# 2. 重建並重啟受影響的容器
docker compose up -d --build django celery_worker

# 3. 驗證修復結果（見第六節）
```

### 5.2 階段二：優化調整（建議於低峰時段執行）

> **目標**：優化任務調度，減少 CPU 尖峰  
> **預計時間**：5 分鐘  
> **影響**：需重啟 celery_beat 和 react 容器

| 步驟 | 操作 | 修改檔案 |
|------|------|----------|
| 3 | 調整高頻任務間隔 | `backend/network_toolbox/celery.py` |
| 4 | 錯開整點任務時間 | `backend/network_toolbox/celery.py` |
| 5 | 優化 React Polling | `docker-compose.yml` |

**執行命令**：

```bash
# 1. 編輯檔案（手動或由 AI 執行）

# 2. 重啟受影響的容器
docker compose restart celery_beat react

# 3. 監控 CPU 使用率
docker stats --no-stream
```

---

## 六、驗證計畫

### 6.1 修復前基準測量

在執行修復前，請先記錄當前狀態：

```bash
# 1. 記錄當前 CPU 使用率
docker stats --no-stream > /tmp/cpu_before.txt
cat /tmp/cpu_before.txt

# 2. 確認當前 Celery Worker 數量（預期：應該有多個）
echo "=== Django 容器內的 Celery 進程 ==="
docker exec nt-django ps aux | grep celery

echo "=== Celery Worker 容器內的進程 ==="
docker exec nt-celery-worker ps aux | grep celery

# 3. 確認當前 Celery Beat 數量
echo "=== Celery Beat 容器內的進程 ==="
docker exec nt-celery-beat ps aux | grep celery
```

### 6.2 修復後驗證

#### 驗證 P0：Celery 不再重複

```bash
# 確認 django 容器內沒有 Celery 進程
docker exec nt-django ps aux | grep celery
# 預期結果：空（或只有 grep 本身）

# 確認 celery_worker 容器正常運行
docker exec nt-celery-worker celery -A network_toolbox inspect active_queues
# 預期結果：顯示活躍的隊列資訊
```

#### 驗證 P1：並行度已降低

```bash
# 確認 Worker 並行度
docker exec nt-celery-worker celery -A network_toolbox inspect stats 2>/dev/null | grep -A5 'pool'
# 預期結果：max-concurrency: 4
```

#### 驗證 P2/P3：任務調度已更新

```bash
# 查看 Celery Beat 日誌
docker logs nt-celery-beat --tail 20 | grep -E 'Scheduler|sync-active|auto-identify'
# 預期結果：看到新的調度間隔
```

#### 綜合驗證：CPU 使用率

```bash
# 監控 CPU 持續 5 分鐘
watch -n 5 'docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"'

# 或者記錄到檔案
for i in {1..60}; do
    echo "=== $(date) ===" >> /tmp/cpu_after.txt
    docker stats --no-stream >> /tmp/cpu_after.txt
    sleep 5
done
```

---

## 七、回滾計畫

如果修復後出現非預期問題，可按以下步驟回滾：

### 7.1 快速回滾

```bash
# 回滾所有變更
cd /home/owner/Codes/network-toolbox

# 1. 恢復檔案
git checkout backend/supervisord.conf
git checkout docker-compose.yml
git checkout backend/network_toolbox/celery.py

# 2. 重建所有容器
docker compose down
docker compose up -d --build

# 3. 確認服務正常
docker compose ps
```

### 7.2 部分回滾

如果只需回滾特定修改：

```bash
# 只回滾 supervisord.conf
git checkout backend/supervisord.conf
docker compose up -d --build django

# 只回滾 docker-compose.yml
git checkout docker-compose.yml
docker compose up -d --build celery_worker react

# 只回滾 celery.py
git checkout backend/network_toolbox/celery.py
docker compose restart celery_beat
```

---

## 八、修改檔案清單總覽

| 檔案路徑 | 修改內容 | 優先級 | 影響容器 |
|----------|----------|--------|----------|
| `backend/supervisord.conf` | 移除 celery-worker 和 celery-beat 程序 | P0 | nt-django |
| `docker-compose.yml` | 降低 concurrency 為 4 | P1 | nt-celery-worker |
| `backend/network_toolbox/celery.py` | 調整 sync_active 任務頻率為 3 分鐘 | P2 | nt-celery-beat |
| `backend/network_toolbox/celery.py` | 錯開 auto_identify 任務至 XX:20 | P3 | nt-celery-beat |
| `docker-compose.yml` | 移除或優化 CHOKIDAR_USEPOLLING | P4 | nt-react |

---

## 九、預期成效

### 9.1 量化指標

| 指標 | 修復前 | 修復後（預估） | 改善幅度 |
|------|--------|----------------|----------|
| 平均 CPU 使用率 | 高峰 80-100% | 高峰 40-60% | ↓ 40-50% |
| Celery Worker 套數 | 2 套（重複） | 1 套 | ↓ 50% |
| 每分鐘任務觸發次數 | ~15 次 | ~8 次 | ↓ 47% |
| 整點 CPU 尖峰 | 明顯 | 平滑 | 顯著改善 |

### 9.2 定性改善

- ✅ 系統響應速度提升
- ✅ 定時任務執行穩定
- ✅ 資源利用更合理
- ✅ 服務穩定性增強

---

## 十、風險評估

| 風險項目 | 可能性 | 影響 | 緩解措施 |
|----------|--------|------|----------|
| 修改後服務無法啟動 | 低 | 高 | 完整測試 + 回滾計畫 |
| 任務執行延遲增加 | 中 | 低 | 監控任務執行時間 |
| React 熱重載失效 | 中 | 低 | 使用方案 B |
| 遺漏某些任務執行 | 低 | 中 | 檢查任務日誌 |

---

## 十一、後續監控建議

修復完成後，建議持續監控以下指標：

1. **CPU 使用率**：使用 `docker stats` 或 Prometheus/Grafana
2. **Celery 任務隊列**：訪問 Flower (http://localhost:5555)
3. **任務執行日誌**：`docker logs nt-celery-worker --tail 100`
4. **錯誤日誌**：`tail -f logs/django_error.log`

---

## 十二、附錄

### A. 任務時間表（修復後）

| 時間 | 任務 |
|------|------|
| XX:00 | sync-jenkins-jobs-hourly |
| XX:03, 06, 09... | sync-active-jenkins-builds (每 3 分鐘) |
| XX:05, 10, 15... | check-nas-connection, check-gitlab-connection (每 5 分鐘) |
| XX:10, 20, 30... | sync-all-dhcp-logs, sync-jenkins-builds (每 10 分鐘) |
| XX:15, 30, 45, 00 | sync-all-dhcp-leases (每 15 分鐘) |
| XX:20 | auto-identify-switches-hourly ⬅️ **已錯開** |

### B. 相關文件

- Docker Compose 配置：`docker-compose.yml`
- Celery 配置：`backend/network_toolbox/celery.py`
- Supervisor 配置：`backend/supervisord.conf`
- 任務定義：`backend/api/tasks.py`

---

## 十三、執行確認

**請確認以上規劃書內容後，選擇執行選項：**

### 替代方案（CPU 保護增強）⭐ 推薦

- [ ] `執行替代方案` - 創建 CPU 保護裝飾器並套用到所有高頻任務

### 原始方案（架構調整）

- [ ] `執行全部` - 執行所有修復（P0-P4）
- [ ] `只執行 P0` - 只移除重複的 Celery
- [ ] `只執行 P0+P1` - 移除重複 Celery + 降低並行度
- [ ] `只執行 P0+P1+P2` - 緊急修復 + 調整高頻任務

### 混合方案（最佳效果）

- [ ] `執行混合方案` - 替代方案 + P0（移除重複 Celery）

### 其他

- [ ] `需要調整` - 說明需要調整的部分

---

> **文件結束**  
> 如有任何問題，請在執行前提出討論。
