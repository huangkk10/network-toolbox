# 定時任務保護機制規劃

> **文件狀態**：規劃中（尚未實施）  
> **創建日期**：2025-12-07  
> **作者**：Network Toolbox Team

---

## 📋 目錄

1. [背景與目標](#背景與目標)
2. [現有機制](#現有機制)
3. [新增保護機制](#新增保護機制)
4. [系統資源監控](#系統資源監控)
5. [任務優先級設計](#任務優先級設計)
6. [實施計畫](#實施計畫)
7. [檔案清單](#檔案清單)

---

## 🎯 背景與目標

### 背景

目前系統已有 **CPU 使用率 80% 以下才執行任務** 的保護機制。為了進一步提升系統穩定性，需要加入更完善的保護機制，確保定時任務不會影響系統正常運作。

### 目標

1. **防止系統過載**：在高負載時自動延遲或跳過非關鍵任務
2. **保護關鍵服務**：確保 Web 服務和 API 響應不受影響
3. **智能調度**：根據系統狀態動態調整任務執行
4. **可觀測性**：完整記錄任務執行狀態和跳過原因

---

## 📊 現有機制

### 當前 CPU 保護機制

```python
# 現有實現（位於各 Celery Task 中）
import psutil

def check_cpu_before_task():
    cpu_percent = psutil.cpu_percent(interval=1)
    if cpu_percent > 80:
        logger.warning(f"CPU usage {cpu_percent}% > 80%, skipping task")
        return False
    return True
```

### 現有任務列表

| 任務名稱 | 執行頻率 | 說明 |
|---------|---------|------|
| `sync_dhcp_leases` | 每 5 分鐘 | 同步 DHCP 租約 |
| `sync_jenkins_builds` | 每 10 分鐘 | 同步 Jenkins Build |
| `analyze_fatal_errors` | 每 15 分鐘 | 分析 Fatal Errors |
| `cleanup_old_logs` | 每天凌晨 | 清理舊日誌 |
| `sync_ntp_time` | 每小時 | NTP 時間同步 |

---

## 🛡️ 新增保護機制

### 1. 多維度資源檢查

```python
# backend/library/services/task_protection_service.py

class TaskProtectionService:
    """任務保護服務"""
    
    # 資源閾值配置
    THRESHOLDS = {
        'cpu_percent': 80,           # CPU 使用率上限
        'memory_percent': 85,        # 記憶體使用率上限
        'disk_percent': 90,          # 磁碟使用率上限
        'load_average_1m': 4.0,      # 1 分鐘平均負載上限
        'io_wait_percent': 30,       # IO 等待時間上限
    }
    
    # 任務執行間隔保護（秒）
    MIN_TASK_INTERVAL = {
        'sync_dhcp_leases': 60,      # 最少間隔 60 秒
        'sync_jenkins_builds': 120,   # 最少間隔 120 秒
        'analyze_fatal_errors': 180,  # 最少間隔 180 秒
    }
    
    def can_execute_task(self, task_name: str, priority: str = 'normal') -> Tuple[bool, str]:
        """
        檢查是否可以執行任務
        
        Args:
            task_name: 任務名稱
            priority: 優先級 ('critical', 'high', 'normal', 'low')
            
        Returns:
            Tuple[bool, str]: (是否可執行, 原因)
        """
        pass
    
    def get_system_status(self) -> Dict:
        """獲取系統狀態"""
        pass
    
    def should_defer_task(self, task_name: str) -> Tuple[bool, int]:
        """
        是否應該延遲任務
        
        Returns:
            Tuple[bool, int]: (是否延遲, 建議延遲秒數)
        """
        pass
```

### 2. 資源檢查項目

| 檢查項目 | 閾值 | 說明 |
|---------|------|------|
| CPU 使用率 | 80% | 超過則延遲任務 |
| 記憶體使用率 | 85% | 超過則延遲任務 |
| 磁碟使用率 | 90% | 超過則跳過非關鍵任務 |
| 1 分鐘平均負載 | 4.0 | 超過則延遲任務 |
| IO 等待時間 | 30% | 超過則延遲 IO 密集任務 |
| 同類任務並發數 | 1 | 防止同類任務並發執行 |

### 3. 任務鎖機制

```python
# 防止同類任務並發執行
class TaskLockService:
    """任務鎖服務（使用 Redis 或檔案鎖）"""
    
    def acquire_lock(self, task_name: str, timeout: int = 300) -> bool:
        """獲取任務鎖"""
        pass
    
    def release_lock(self, task_name: str) -> bool:
        """釋放任務鎖"""
        pass
    
    def is_locked(self, task_name: str) -> bool:
        """檢查任務是否被鎖定"""
        pass
```

### 4. 任務執行頻率限制

```python
# 防止任務過於頻繁執行
class TaskRateLimiter:
    """任務頻率限制器"""
    
    def __init__(self):
        self.last_execution = {}  # {task_name: timestamp}
    
    def can_execute(self, task_name: str) -> Tuple[bool, int]:
        """
        檢查任務是否可以執行
        
        Returns:
            Tuple[bool, int]: (是否可執行, 距離下次可執行的秒數)
        """
        pass
    
    def record_execution(self, task_name: str):
        """記錄任務執行時間"""
        pass
```

---

## 📈 系統資源監控

### 監控指標

```python
# backend/library/services/system_monitor_service.py

class SystemMonitorService:
    """系統監控服務"""
    
    def get_cpu_usage(self) -> float:
        """獲取 CPU 使用率"""
        return psutil.cpu_percent(interval=1)
    
    def get_memory_usage(self) -> Dict:
        """獲取記憶體使用情況"""
        mem = psutil.virtual_memory()
        return {
            'total_gb': mem.total / (1024**3),
            'used_gb': mem.used / (1024**3),
            'percent': mem.percent,
            'available_gb': mem.available / (1024**3)
        }
    
    def get_disk_usage(self, path: str = '/') -> Dict:
        """獲取磁碟使用情況"""
        disk = psutil.disk_usage(path)
        return {
            'total_gb': disk.total / (1024**3),
            'used_gb': disk.used / (1024**3),
            'percent': disk.percent,
            'free_gb': disk.free / (1024**3)
        }
    
    def get_load_average(self) -> Dict:
        """獲取系統負載"""
        load1, load5, load15 = os.getloadavg()
        return {
            'load_1m': load1,
            'load_5m': load5,
            'load_15m': load15
        }
    
    def get_io_stats(self) -> Dict:
        """獲取 IO 統計"""
        io_counters = psutil.disk_io_counters()
        return {
            'read_bytes': io_counters.read_bytes,
            'write_bytes': io_counters.write_bytes,
            'read_count': io_counters.read_count,
            'write_count': io_counters.write_count
        }
    
    def get_network_stats(self) -> Dict:
        """獲取網路統計"""
        net = psutil.net_io_counters()
        return {
            'bytes_sent': net.bytes_sent,
            'bytes_recv': net.bytes_recv,
            'packets_sent': net.packets_sent,
            'packets_recv': net.packets_recv
        }
    
    def get_full_status(self) -> Dict:
        """獲取完整系統狀態"""
        return {
            'cpu': self.get_cpu_usage(),
            'memory': self.get_memory_usage(),
            'disk': self.get_disk_usage(),
            'load': self.get_load_average(),
            'io': self.get_io_stats(),
            'network': self.get_network_stats(),
            'timestamp': datetime.now().isoformat()
        }
```

---

## 🎚️ 任務優先級設計

### 優先級定義

| 優先級 | 說明 | CPU 閾值 | 記憶體閾值 | 範例任務 |
|--------|------|---------|-----------|---------|
| `critical` | 關鍵任務，幾乎不跳過 | 95% | 95% | 告警通知、安全任務 |
| `high` | 高優先級，較少跳過 | 85% | 90% | DHCP 租約同步 |
| `normal` | 普通任務，正常限制 | 80% | 85% | Jenkins Build 同步 |
| `low` | 低優先級，易被跳過 | 70% | 80% | 日誌清理、統計分析 |

### 任務優先級配置

```python
# backend/api/tasks_config.py

TASK_PRIORITIES = {
    # 關鍵任務
    'send_alert_notification': 'critical',
    'security_scan': 'critical',
    
    # 高優先級
    'sync_dhcp_leases': 'high',
    'sync_active_builds': 'high',
    
    # 普通任務
    'sync_jenkins_builds': 'normal',
    'analyze_fatal_errors': 'normal',
    'sync_ntp_time': 'normal',
    
    # 低優先級
    'cleanup_old_logs': 'low',
    'generate_statistics': 'low',
    'cleanup_cache': 'low',
}

# 各優先級的資源閾值
PRIORITY_THRESHOLDS = {
    'critical': {
        'cpu_percent': 95,
        'memory_percent': 95,
        'skip_on_high_load': False,
    },
    'high': {
        'cpu_percent': 85,
        'memory_percent': 90,
        'skip_on_high_load': False,
    },
    'normal': {
        'cpu_percent': 80,
        'memory_percent': 85,
        'skip_on_high_load': True,
    },
    'low': {
        'cpu_percent': 70,
        'memory_percent': 80,
        'skip_on_high_load': True,
    },
}
```

---

## 🔧 Celery Task 裝飾器

### 保護機制裝飾器

```python
# backend/library/decorators/task_protection.py

from functools import wraps
from library.services.task_protection_service import TaskProtectionService

def protected_task(priority: str = 'normal', allow_skip: bool = True):
    """
    任務保護裝飾器
    
    Args:
        priority: 任務優先級
        allow_skip: 是否允許在高負載時跳過
    
    Usage:
        @shared_task
        @protected_task(priority='high', allow_skip=False)
        def my_important_task():
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            task_name = func.__name__
            protection = TaskProtectionService()
            
            # 1. 檢查是否可以執行
            can_execute, reason = protection.can_execute_task(task_name, priority)
            
            if not can_execute:
                if allow_skip:
                    logger.warning(f"Task {task_name} skipped: {reason}")
                    return {
                        'status': 'skipped',
                        'reason': reason,
                        'task_name': task_name
                    }
                else:
                    # 不允許跳過，延遲執行
                    should_defer, defer_seconds = protection.should_defer_task(task_name)
                    if should_defer:
                        logger.info(f"Task {task_name} deferred by {defer_seconds}s: {reason}")
                        # 重新排程任務
                        func.apply_async(args=args, kwargs=kwargs, countdown=defer_seconds)
                        return {
                            'status': 'deferred',
                            'defer_seconds': defer_seconds,
                            'reason': reason
                        }
            
            # 2. 獲取任務鎖
            lock_service = TaskLockService()
            if not lock_service.acquire_lock(task_name):
                logger.warning(f"Task {task_name} skipped: another instance is running")
                return {
                    'status': 'skipped',
                    'reason': 'Another instance is running'
                }
            
            try:
                # 3. 執行任務
                logger.info(f"Task {task_name} started (priority: {priority})")
                start_time = time.time()
                
                result = func(*args, **kwargs)
                
                elapsed = time.time() - start_time
                logger.info(f"Task {task_name} completed in {elapsed:.2f}s")
                
                return result
                
            finally:
                # 4. 釋放任務鎖
                lock_service.release_lock(task_name)
        
        return wrapper
    return decorator
```

### 使用範例

```python
# backend/api/tasks.py

from celery import shared_task
from library.decorators.task_protection import protected_task

@shared_task
@protected_task(priority='high', allow_skip=False)
def sync_dhcp_leases():
    """同步 DHCP 租約（高優先級，不允許跳過）"""
    # ... 任務邏輯
    pass

@shared_task
@protected_task(priority='normal', allow_skip=True)
def sync_jenkins_builds():
    """同步 Jenkins Builds（普通優先級，允許跳過）"""
    # ... 任務邏輯
    pass

@shared_task
@protected_task(priority='low', allow_skip=True)
def cleanup_old_logs():
    """清理舊日誌（低優先級，允許跳過）"""
    # ... 任務邏輯
    pass
```

---

## 📊 監控與告警

### 任務執行統計

```python
# backend/library/services/task_stats_service.py

class TaskStatsService:
    """任務統計服務"""
    
    def record_task_execution(self, task_name: str, status: str, 
                              duration: float, reason: str = None):
        """記錄任務執行"""
        pass
    
    def get_task_stats(self, task_name: str, hours: int = 24) -> Dict:
        """獲取任務統計"""
        return {
            'task_name': task_name,
            'total_executions': 100,
            'successful': 95,
            'skipped': 3,
            'failed': 2,
            'average_duration': 5.2,
            'skip_reasons': {
                'high_cpu': 2,
                'high_memory': 1
            }
        }
    
    def get_all_tasks_stats(self, hours: int = 24) -> List[Dict]:
        """獲取所有任務統計"""
        pass
```

### 資源使用告警

```python
# 當系統資源持續超過閾值時發送告警

ALERT_CONFIG = {
    'cpu_sustained_high': {
        'threshold': 90,
        'duration_minutes': 5,
        'message': 'CPU 使用率持續高於 90% 超過 5 分鐘'
    },
    'memory_sustained_high': {
        'threshold': 90,
        'duration_minutes': 5,
        'message': '記憶體使用率持續高於 90% 超過 5 分鐘'
    },
    'tasks_frequently_skipped': {
        'skip_rate': 0.3,  # 30% 以上被跳過
        'period_hours': 1,
        'message': '過去 1 小時有超過 30% 的任務被跳過'
    }
}
```

---

## 🗂️ 資料模型

### 任務執行記錄

```python
# backend/api/models.py

class TaskExecutionLog(models.Model):
    """任務執行記錄"""
    
    STATUS_CHOICES = [
        ('success', '成功'),
        ('failed', '失敗'),
        ('skipped', '跳過'),
        ('deferred', '延遲'),
    ]
    
    task_name = models.CharField(max_length=100, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    priority = models.CharField(max_length=20, default='normal')
    
    # 執行時間
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True)
    duration_seconds = models.FloatField(null=True)
    
    # 系統狀態（執行時）
    cpu_percent = models.FloatField(null=True)
    memory_percent = models.FloatField(null=True)
    load_average = models.FloatField(null=True)
    
    # 跳過/失敗原因
    skip_reason = models.CharField(max_length=200, blank=True)
    error_message = models.TextField(blank=True)
    
    # 結果數據
    result_data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['task_name', 'started_at']),
            models.Index(fields=['status', 'started_at']),
        ]
        ordering = ['-started_at']
```

---

## 📅 實施計畫

### 階段一：基礎保護機制（2 天）

| 任務 | 說明 | 預估時間 |
|-----|------|---------|
| 系統監控服務 | 實現 `SystemMonitorService` | 0.5 天 |
| 任務保護服務 | 實現 `TaskProtectionService` | 0.5 天 |
| 任務鎖服務 | 實現 `TaskLockService` | 0.5 天 |
| 保護裝飾器 | 實現 `@protected_task` | 0.5 天 |

### 階段二：任務改造（1.5 天）

| 任務 | 說明 | 預估時間 |
|-----|------|---------|
| 現有任務改造 | 為現有 Celery Tasks 添加保護裝飾器 | 0.5 天 |
| 優先級配置 | 配置各任務的優先級 | 0.25 天 |
| 閾值調優 | 根據實際情況調整資源閾值 | 0.25 天 |
| 測試驗證 | 測試各種場景下的保護機制 | 0.5 天 |

### 階段三：監控與統計（1.5 天）

| 任務 | 說明 | 預估時間 |
|-----|------|---------|
| 資料模型 | 創建 `TaskExecutionLog` 模型 | 0.25 天 |
| 統計服務 | 實現 `TaskStatsService` | 0.5 天 |
| API 端點 | 創建任務統計 API | 0.25 天 |
| 前端展示 | 任務執行狀態儀表板（可選） | 0.5 天 |

### 總計：5 天

---

## 📁 檔案清單

### 後端新增檔案

```
backend/
├── library/
│   ├── services/
│   │   ├── task_protection_service.py    # 任務保護服務
│   │   ├── task_lock_service.py          # 任務鎖服務
│   │   ├── task_stats_service.py         # 任務統計服務
│   │   └── system_monitor_service.py     # 系統監控服務
│   └── decorators/
│       └── task_protection.py            # 保護裝飾器
├── api/
│   ├── models.py                         # 新增 TaskExecutionLog
│   ├── tasks_config.py                   # 任務優先級配置
│   └── tasks.py                          # 修改：添加保護裝飾器
└── migrations/
    └── XXXX_add_task_execution_log.py    # 資料庫遷移
```

### 前端新增檔案（可選）

```
frontend/src/
├── pages/
│   └── SystemMonitor/
│       └── TaskExecutionDashboard.js     # 任務執行儀表板
└── services/
    └── taskStatsApi.js                   # 任務統計 API
```

---

## ✅ 驗收標準

1. **資源保護**
   - [ ] CPU > 80% 時普通任務被跳過
   - [ ] 記憶體 > 85% 時普通任務被跳過
   - [ ] 關鍵任務在極端情況下仍能執行

2. **任務鎖**
   - [ ] 同類任務不會並發執行
   - [ ] 任務異常結束後鎖能正確釋放

3. **統計記錄**
   - [ ] 所有任務執行都有記錄
   - [ ] 跳過原因被正確記錄
   - [ ] 可查詢歷史執行統計

4. **日誌**
   - [ ] 任務跳過時有 WARNING 日誌
   - [ ] 任務延遲時有 INFO 日誌
   - [ ] 資源異常時有詳細日誌

---

## 📝 備註

- 此文件為規劃文件，尚未實施
- 實際閾值可能需要根據生產環境調整
- 建議先在測試環境驗證後再部署到生產環境

---

**最後更新**：2025-12-07  
**版本**：v1.0（規劃版）
