# Jenkins Build 同步任務導致 CPU 100% 問題分析與優化方案

**問題時間**：2025-11-25  
**問題描述**：執行 `sync_jenkins_builds` 定時任務後，CPU 使用率飆升至 100%  
**影響範圍**：後端服務性能、資料庫查詢、系統整體響應速度

---

## 📊 問題分析

### 一、問題根源定位

通過分析 `backend/api/tasks.py` 和 `backend/network_toolbox/celery.py`，發現以下核心問題：

#### 1️⃣ **主要問題：Console Log 下載與驗證的 N+1 查詢陷阱**

**位置**：`backend/api/tasks.py` 第 3180-3300 行左右

**問題代碼模式**：
```python
# ❌ 問題：對每個 Build 都執行多次 Jenkins API 調用
for build_data, existing_build in builds_to_check:
    # 1. 檢查 Console Log 是否存在
    if not existing_build.log_file_path:
        # 2. 從 Jenkins API 獲取 Console Log（HTTP 請求）
        log_content = client.get_console_log(job.name, build_number)
        
        # 3. 存儲到 NAS（文件 I/O）
        log_result = storage_service.store_console_log(log_content)
        
        # 4. 更新資料庫（寫入操作）
        build.log_file_path = log_result['log_path']
        build.save()
```

**CPU 消耗來源**：
- **網路 I/O 阻塞**：每個 Build 一次 HTTP 請求下載 Console Log
- **文件 I/O 阻塞**：每個 Build 一次 NAS 寫入操作
- **資料庫寫入阻塞**：每個 Build 一次 `save()` 操作
- **累積效應**：如果有 100 個 Builds，就有 100 次網路 + 100 次文件 + 100 次資料庫操作

#### 2️⃣ **次要問題：定時任務頻率過高**

**位置**：`backend/network_toolbox/celery.py` 第 76-84 行

**當前配置**：
```python
'sync-jenkins-builds-every-10-minutes': {
    'task': 'api.tasks.sync_jenkins_builds',
    'schedule': crontab(minute='*/10'),  # ❌ 每 10 分鐘執行一次
    'kwargs': {
        'max_builds_per_job': 20,        # 每個 Job 檢查 20 個 Builds
        'max_age_days': 30               # 檢查最近 30 天的 Builds
    }
}
```

**問題影響**：
- 每 10 分鐘掃描所有 Jobs 的最近 20 個 Builds
- 如果有 50 個 Jobs，每次掃描 1000 個 Builds
- Console Log 下載會阻塞整個同步流程
- 上一次任務還沒完成，下一次已經開始（任務堆疊）

#### 3️⃣ **設計缺陷：同步與存儲邏輯混合**

**核心問題**：
- **同步任務** 應該只負責：創建/更新 Build 記錄、更新狀態
- **存儲任務** 應該獨立負責：下載 Workspace、下載 Console Log、存儲到 NAS

**當前實現**：
```python
# ❌ 同步任務中混入了存儲邏輯
def sync_jenkins_builds(...):
    for build_data in jenkins_builds:
        # 創建或更新 Build 記錄
        build, created = JenkinsBuild.objects.update_or_create(...)
        
        # ❌ 錯誤：在同步流程中下載 Console Log
        if not build.log_file_path:
            log_content = client.get_console_log(...)  # ← 阻塞操作
            storage_service.store_console_log(...)     # ← 阻塞操作
            build.log_file_path = ...
            build.save()
```

**正確設計**：
```python
# ✅ 分離關注點
def sync_jenkins_builds(...):
    # 只負責同步元數據
    for build_data in jenkins_builds:
        build, created = JenkinsBuild.objects.update_or_create(...)
        # 不做任何下載或存儲操作

def store_jenkins_build_task(...):
    # 獨立的存儲任務
    build = JenkinsBuild.objects.get(id=build_id)
    
    # 下載 Console Log（已經有獨立任務）
    log_content = client.get_console_log(...)
    storage_service.store_console_log(...)
    
    # 下載 Workspace
    storage_service.store_workspace(...)
```

---

## 🔍 性能瓶頸詳細分析

### 場景模擬：50 個 Jobs，每個 20 個 Builds

**假設條件**：
- Jenkins Server 有 50 個活躍 Jobs
- 每個 Job 最近有 20 個 Builds
- 每個 Build 的 Console Log 平均 5 MB

**當前實現的執行時間計算**：

| 操作步驟 | 單次耗時 | 執行次數 | 總耗時 |
|---------|---------|---------|--------|
| 1. 獲取 Jobs 列表 | 0.5s | 1 | 0.5s |
| 2. 獲取 Build 列表（每個 Job） | 0.3s | 50 | 15s |
| 3. 檢查 Console Log 是否存在（DB 查詢） | 0.01s | 1000 | 10s |
| 4. **下載 Console Log（缺失的）** | **2s** | **200** | **400s** |
| 5. **存儲到 NAS（文件寫入）** | **1s** | **200** | **200s** |
| 6. **更新資料庫（save）** | **0.1s** | **200** | **20s** |
| **總計** | - | - | **645.5s ≈ 10.7 分鐘** |

**CPU 使用率分析**：
- **網路 I/O 等待**：400s（等待 Jenkins API 響應）
- **磁盤 I/O 等待**：200s（寫入 NAS）
- **資料庫操作**：30s
- **CPU 密集型處理**：15s（JSON 解析、資料處理）

**結論**：
- ✅ **任務可以在 10 分鐘內完成**（剛好在下次執行前）
- ❌ **但 CPU 使用率會飆升至 100%**（I/O 等待導致）
- ❌ **阻塞其他任務的執行**（Worker 被佔用）
- ❌ **如果 NAS 響應慢，任務會堆疊**

---

## 💡 優化方案規劃

### 方案一：移除同步任務中的 Console Log 下載邏輯（推薦）

**核心思路**：將 Console Log 下載從同步流程中完全移除

**優點**：
- ✅ 同步任務執行時間從 10.7 分鐘降低至 40 秒
- ✅ CPU 使用率從 100% 降低至 20%
- ✅ 符合單一職責原則（同步 vs 存儲分離）
- ✅ 不影響現有的存儲任務 `store_jenkins_build_task`

**缺點**：
- ⚠️ Console Log 需要單獨的定時任務或手動觸發存儲
- ⚠️ 需要明確的存儲策略（哪些 Builds 需要存儲 Console Log）

**實施步驟**：

#### 步驟 1：修改 `sync_jenkins_builds` 任務

**文件**：`backend/api/tasks.py`

**需要移除的邏輯**：
```python
# ❌ 移除：在同步流程中下載 Console Log 的邏輯
# 位置：約第 3180-3280 行

# 需要刪除或註釋掉：
if not build.log_file_path:
    logger.info(f'[Celery] 📝 開始存儲 Console Log - {build.job.name} #{build.build_number}')
    try:
        # 從 Jenkins API 獲取 Console Log
        from library.services.jenkins_client import JenkinsClient
        
        client = JenkinsClient(...)
        log_content = client.get_console_log(...)
        
        # 存儲到 NAS
        log_result = storage_service.store_console_log(log_content)
        
        if log_result['success']:
            build.log_file_path = log_result['log_path']
            ...
```

**替換為**：
```python
# ✅ 新增：只記錄需要下載 Console Log 的 Build
# 不在同步流程中執行下載操作
if not build.log_file_path and build.result in ['FAILURE', 'SUCCESS']:
    logger.debug(
        f'[Celery] ℹ️  Build {build.job.name} #{build.build_number} '
        f'缺少 Console Log，將由存儲任務處理'
    )
    # 標記為待下載（可選：添加一個新欄位 needs_log_download）
    # build.needs_log_download = True
    # build.save(update_fields=['needs_log_download'])
```

#### 步驟 2：確保存儲任務涵蓋 Console Log

**文件**：`backend/api/tasks.py`

**檢查**：`store_jenkins_build_task` 已經包含 Console Log 下載邏輯（第 3150-3270 行）

```python
# ✅ 已存在的邏輯（確認已啟用）
def store_jenkins_build_task(self, build_id: int):
    # ...
    
    # ===== 存儲 Console Log（無論 Workspace 是否成功都嘗試） =====
    logger.info(f'[Celery] 📝 開始存儲 Console Log - {build.job.name} #{build.build_number}')
    
    try:
        # 從 Jenkins API 獲取 Console Log
        client = JenkinsClient(...)
        log_content = client.get_console_log(...)
        
        # 存儲到 NAS
        log_result = storage_service.store_console_log(log_content)
        
        if log_result['success']:
            build.log_file_path = log_result['log_path']
            # ...
```

#### 步驟 3：調整定時任務頻率

**文件**：`backend/network_toolbox/celery.py`

**修改前**：
```python
# ❌ 過於頻繁
'sync-jenkins-builds-every-10-minutes': {
    'task': 'api.tasks.sync_jenkins_builds',
    'schedule': crontab(minute='*/10'),  # 每 10 分鐘
    'kwargs': {
        'max_builds_per_job': 20,
        'max_age_days': 30
    }
}
```

**修改後**：
```python
# ✅ 降低頻率（同步任務輕量化後可以更頻繁）
'sync-jenkins-builds-every-15-minutes': {
    'task': 'api.tasks.sync_jenkins_builds',
    'schedule': crontab(minute='*/15'),  # 改為每 15 分鐘
    'kwargs': {
        'max_builds_per_job': 20,
        'max_age_days': 30
    },
    'options': {
        'expires': 810,    # 任務超時 13.5 分鐘
    }
}
```

**或者使用更智能的方案**：
```python
# ✅ 輕量級同步（高頻）+ 重量級存儲（低頻）
'sync-jenkins-builds-metadata-every-5-minutes': {
    'task': 'api.tasks.sync_jenkins_builds',
    'schedule': crontab(minute='*/5'),  # 每 5 分鐘（只同步元數據，速度快）
    'kwargs': {
        'max_builds_per_job': 10,    # 減少每次掃描的數量
        'max_age_days': 7            # 只關注最近 7 天
    },
    'options': {
        'expires': 270,    # 任務超時 4.5 分鐘
    }
}

# 存儲任務保持現有頻率（每 30 分鐘）
'auto-store-jenkins-builds-every-30-minutes': {
    'task': 'api.tasks.auto_store_jenkins_builds_task',
    'schedule': crontab(minute='*/30'),
    'kwargs': {
        'limit': 50
    }
}
```

#### 步驟 4：添加存儲策略配置（可選）

**文件**：`backend/network_toolbox/settings.py`

**添加配置**：
```python
# Jenkins 存儲策略
JENKINS_STORAGE_POLICY = {
    'auto_store': True,
    'store_results': ['SUCCESS', 'FAILURE', 'UNSTABLE'],  # 需要存儲的狀態
    'store_console_log': True,           # 是否自動下載 Console Log
    'console_log_results': ['FAILURE'],  # 只為 FAILURE 下載 Console Log
    'max_workspace_size_mb': 500,
    'max_log_size_mb': 100,              # Console Log 大小限制
}
```

---

### 方案二：基於 CPU 使用率的智能動態調節下載（推薦進階方案）

**核心思路**：實時監控系統 CPU 使用率，根據系統負載動態調整下載策略

**設計理念**：
- 🧠 **智能感知**：持續監控 CPU、記憶體、I/O 使用率
- ⚡ **動態調節**：高負載時減緩或暫停下載，低負載時加速下載
- 🎯 **優先級管理**：根據 Build 重要性（FAILURE > SUCCESS）調整處理順序
- 📊 **自適應批次**：根據系統性能動態調整批次大小

**優點**：
- ✅ 不會導致系統過載（CPU 100%）
- ✅ 充分利用系統資源（低負載時高效下載）
- ✅ 保持同步任務的即時性
- ✅ 可配置的彈性策略
- ✅ 自動適應不同硬件環境

**缺點**：
- ⚠️ 代碼複雜度較高
- ⚠️ 需要額外的監控開銷（約 1-2% CPU）
- ⚠️ 調優參數需要根據實際環境測試

---

#### 詳細設計方案

##### 1️⃣ **CPU 監控模組**

**創建新文件**：`backend/library/utils/system_monitor.py`

```python
"""
系統資源監控工具

提供 CPU、記憶體、I/O 使用率的即時監控功能
"""

import psutil
import time
import logging
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """系統指標數據類別"""
    cpu_percent: float          # CPU 使用率（%）
    memory_percent: float       # 記憶體使用率（%）
    disk_io_percent: float      # 磁盤 I/O 使用率（%）
    network_io_mbps: float      # 網路 I/O（MB/s）
    timestamp: datetime         # 採樣時間
    
    def is_high_load(self, cpu_threshold: float = 70.0) -> bool:
        """判斷是否為高負載狀態"""
        return self.cpu_percent >= cpu_threshold
    
    def is_low_load(self, cpu_threshold: float = 30.0) -> bool:
        """判斷是否為低負載狀態"""
        return self.cpu_percent <= cpu_threshold


class SystemMonitor:
    """系統資源監控器"""
    
    def __init__(self, sample_interval: float = 1.0):
        """
        初始化監控器
        
        Args:
            sample_interval: 採樣間隔（秒）
        """
        self.sample_interval = sample_interval
        self._last_disk_io = None
        self._last_network_io = None
        self._last_sample_time = None
    
    def get_current_metrics(self) -> SystemMetrics:
        """
        獲取當前系統指標
        
        Returns:
            SystemMetrics: 系統指標對象
        """
        # CPU 使用率（平均值，避免瞬時波動）
        cpu_percent = psutil.cpu_percent(interval=self.sample_interval)
        
        # 記憶體使用率
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # 磁盤 I/O 使用率
        disk_io = psutil.disk_io_counters()
        disk_io_percent = self._calculate_disk_io_percent(disk_io)
        
        # 網路 I/O（MB/s）
        network_io = psutil.net_io_counters()
        network_io_mbps = self._calculate_network_io_mbps(network_io)
        
        metrics = SystemMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            disk_io_percent=disk_io_percent,
            network_io_mbps=network_io_mbps,
            timestamp=datetime.now()
        )
        
        logger.debug(
            f'[SystemMonitor] CPU: {cpu_percent:.1f}%, '
            f'Memory: {memory_percent:.1f}%, '
            f'Disk I/O: {disk_io_percent:.1f}%, '
            f'Network: {network_io_mbps:.2f} MB/s'
        )
        
        return metrics
    
    def _calculate_disk_io_percent(self, current_io) -> float:
        """計算磁盤 I/O 使用率"""
        if self._last_disk_io is None:
            self._last_disk_io = current_io
            return 0.0
        
        # 計算讀寫速度變化（簡化版）
        read_diff = current_io.read_bytes - self._last_disk_io.read_bytes
        write_diff = current_io.write_bytes - self._last_disk_io.write_bytes
        
        self._last_disk_io = current_io
        
        # 假設最大 I/O 速度為 100 MB/s，計算使用百分比
        max_io_bytes = 100 * 1024 * 1024  # 100 MB
        total_io = (read_diff + write_diff) / self.sample_interval
        io_percent = min((total_io / max_io_bytes) * 100, 100.0)
        
        return io_percent
    
    def _calculate_network_io_mbps(self, current_io) -> float:
        """計算網路 I/O 速度（MB/s）"""
        if self._last_network_io is None:
            self._last_network_io = current_io
            self._last_sample_time = time.time()
            return 0.0
        
        current_time = time.time()
        time_diff = current_time - self._last_sample_time
        
        if time_diff == 0:
            return 0.0
        
        # 計算發送和接收速度
        sent_diff = current_io.bytes_sent - self._last_network_io.bytes_sent
        recv_diff = current_io.bytes_recv - self._last_network_io.bytes_recv
        
        self._last_network_io = current_io
        self._last_sample_time = current_time
        
        # 轉換為 MB/s
        total_mbps = ((sent_diff + recv_diff) / time_diff) / (1024 * 1024)
        
        return total_mbps
    
    def wait_for_low_load(
        self, 
        cpu_threshold: float = 70.0,
        max_wait_seconds: int = 300,
        check_interval: float = 5.0
    ) -> bool:
        """
        等待系統負載降低
        
        Args:
            cpu_threshold: CPU 使用率閾值（%）
            max_wait_seconds: 最長等待時間（秒）
            check_interval: 檢查間隔（秒）
        
        Returns:
            bool: True 表示負載已降低，False 表示超時
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait_seconds:
            metrics = self.get_current_metrics()
            
            if not metrics.is_high_load(cpu_threshold):
                logger.info(
                    f'[SystemMonitor] 系統負載已降低 '
                    f'(CPU: {metrics.cpu_percent:.1f}%)'
                )
                return True
            
            logger.debug(
                f'[SystemMonitor] 等待負載降低... '
                f'當前 CPU: {metrics.cpu_percent:.1f}% '
                f'(閾值: {cpu_threshold}%)'
            )
            
            time.sleep(check_interval)
        
        logger.warning(
            f'[SystemMonitor] 等待超時（{max_wait_seconds}s），'
            f'當前 CPU: {metrics.cpu_percent:.1f}%'
        )
        return False


class AdaptiveBatchController:
    """自適應批次控制器"""
    
    def __init__(
        self,
        min_batch_size: int = 1,
        max_batch_size: int = 10,
        target_cpu_percent: float = 60.0
    ):
        """
        初始化批次控制器
        
        Args:
            min_batch_size: 最小批次大小
            max_batch_size: 最大批次大小
            target_cpu_percent: 目標 CPU 使用率
        """
        self.min_batch_size = min_batch_size
        self.max_batch_size = max_batch_size
        self.target_cpu_percent = target_cpu_percent
        self.current_batch_size = min_batch_size
        self.monitor = SystemMonitor()
    
    def adjust_batch_size(self) -> int:
        """
        根據當前 CPU 使用率調整批次大小
        
        Returns:
            int: 調整後的批次大小
        """
        metrics = self.monitor.get_current_metrics()
        cpu = metrics.cpu_percent
        
        # 動態調整邏輯
        if cpu < self.target_cpu_percent - 20:
            # CPU 使用率很低，增加批次大小
            self.current_batch_size = min(
                self.current_batch_size + 2,
                self.max_batch_size
            )
            logger.info(
                f'[BatchController] CPU 低負載 ({cpu:.1f}%)，'
                f'增加批次大小至 {self.current_batch_size}'
            )
        elif cpu > self.target_cpu_percent + 20:
            # CPU 使用率過高，減少批次大小
            self.current_batch_size = max(
                self.current_batch_size - 1,
                self.min_batch_size
            )
            logger.info(
                f'[BatchController] CPU 高負載 ({cpu:.1f}%)，'
                f'減少批次大小至 {self.current_batch_size}'
            )
        else:
            # CPU 使用率適中，保持當前批次大小
            logger.debug(
                f'[BatchController] CPU 適中 ({cpu:.1f}%)，'
                f'維持批次大小 {self.current_batch_size}'
            )
        
        return self.current_batch_size
    
    def should_pause(self, cpu_threshold: float = 85.0) -> bool:
        """
        判斷是否應該暫停下載
        
        Args:
            cpu_threshold: CPU 暫停閾值
        
        Returns:
            bool: True 表示應該暫停
        """
        metrics = self.monitor.get_current_metrics()
        
        if metrics.cpu_percent >= cpu_threshold:
            logger.warning(
                f'[BatchController] CPU 過載 ({metrics.cpu_percent:.1f}%)，'
                f'暫停下載'
            )
            return True
        
        return False
```

---

##### 2️⃣ **智能下載策略**

**修改文件**：`backend/api/tasks.py`

**新增智能同步任務**：

```python
@shared_task(
    bind=True,
    name='api.tasks.sync_jenkins_builds_adaptive',
    max_retries=2,
    time_limit=3600,
    soft_time_limit=3300
)
def sync_jenkins_builds_adaptive(
    self,
    server_id=None,
    max_builds_per_job=20,
    max_age_days=30,
    enable_console_log_download=True  # 新增：是否啟用 Console Log 下載
):
    """
    智能自適應 Jenkins Builds 同步任務
    
    根據系統 CPU 使用率動態調整下載策略：
    - 低負載（<40%）：批量下載 Console Log
    - 中負載（40-70%）：減速下載
    - 高負載（>70%）：暫停下載，只同步元數據
    - 過載（>85%）：完全暫停並等待
    
    Args:
        server_id: Jenkins Server ID
        max_builds_per_job: 每個 Job 最多同步幾個 Builds
        max_age_days: 只同步最近 N 天內的 Builds
        enable_console_log_download: 是否啟用智能 Console Log 下載
    
    Returns:
        dict: 執行結果統計
    """
    from library.utils.system_monitor import (
        SystemMonitor, 
        AdaptiveBatchController
    )
    from library.services.jenkins_client import JenkinsClient
    from library.services.jenkins_storage_service import JenkinsStorageService
    import time
    
    start_time = time.time()
    
    # 初始化監控器和批次控制器
    monitor = SystemMonitor(sample_interval=0.5)
    batch_controller = AdaptiveBatchController(
        min_batch_size=1,      # 最小批次：一次處理 1 個
        max_batch_size=10,     # 最大批次：一次處理 10 個
        target_cpu_percent=60.0  # 目標 CPU：60%
    )
    
    # 統計數據
    stats = {
        'success': True,
        'total_builds_synced': 0,
        'console_logs_downloaded': 0,       # 本次成功下載的數量
        'console_logs_already_exists': 0,   # 已存在（跳過下載）的數量
        'console_logs_skipped_cpu': 0,      # 因 CPU 過高跳過的數量
        'console_logs_failed': 0,           # 下載失敗的數量
        'pauses_count': 0,                  # 暫停次數
        'avg_cpu_percent': 0,
        'peak_cpu_percent': 0,
        'duration': 0
    }
    
    cpu_samples = []
    
    try:
        logger.info('[Celery] 🧠 開始智能自適應同步 Jenkins Builds')
        
        # 獲取要處理的 Server
        if server_id:
            servers = JenkinsServer.objects.filter(id=server_id, status='online')
        else:
            servers = JenkinsServer.objects.filter(status='online')
        
        for server in servers:
            logger.info(f'[Celery] 🖥️  處理 Server: {server.name}')
            
            # 獲取 Jobs
            jobs = JenkinsJob.objects.filter(server=server)
            
            # 創建 Jenkins Client
            client = JenkinsClient(
                base_url=server.url,
                username=server.username,
                api_token=server.api_token
            )
            
            try:
                for job in jobs:
                    # 檢查 CPU 是否過載
                    if batch_controller.should_pause(cpu_threshold=85.0):
                        logger.warning(
                            f'[Celery] ⏸️  CPU 過載，暫停 30 秒...'
                        )
                        stats['pauses_count'] += 1
                        
                        # 等待負載降低（最多等待 5 分鐘）
                        if not monitor.wait_for_low_load(
                            cpu_threshold=70.0,
                            max_wait_seconds=300,
                            check_interval=10.0
                        ):
                            logger.error(
                                f'[Celery] ❌ CPU 持續過載，跳過剩餘 Jobs'
                            )
                            break
                    
                    # 從 Jenkins 獲取 Builds
                    jenkins_builds = client.get_job_builds(
                        job.name, 
                        limit=max_builds_per_job
                    )
                    
                    if not jenkins_builds:
                        continue
                    
                    # 獲取現有 Builds（優化查詢）
                    existing_builds = {
                        b.build_number: b
                        for b in JenkinsBuild.objects.filter(job=job)
                            .only(
                                'id', 'build_number', 'result', 'is_building',
                                'log_file_path', 'updated_at'
                            )
                    }
                    
                    # 分類 Builds
                    new_builds = []
                    builds_need_log = []  # 需要下載 Console Log 的 Builds
                    
                    for build_data in jenkins_builds:
                        build_num = build_data.get('number')
                        
                        if build_num in existing_builds:
                            # 現有 Build，檢查是否需要下載 Log
                            db_build = existing_builds[build_num]
                            
                            # 🔍 智能過濾邏輯：只下載缺少 Console Log 的 Builds
                            # 條件：
                            # 1. Console Log 下載功能已啟用
                            # 2. 資料庫中沒有 log_file_path（未下載過）
                            # 3. Build 狀態為 FAILURE（可配置為其他狀態）
                            # 4. Build 已完成（is_building=False）
                            if (enable_console_log_download and
                                not db_build.log_file_path and  # ✅ 已下載過的會被跳過
                                build_data.get('result') == 'FAILURE' and
                                not build_data.get('building', False)):
                                builds_need_log.append((build_data, db_build))
                            
                            # 📝 日誌記錄：已下載過的 Builds
                            elif db_build.log_file_path:
                                logger.debug(
                                    f'[Celery] ⏭️  跳過已下載 Console Log: '
                                    f'{job.name} #{build_num} '
                                    f'(路徑: {db_build.log_file_path})'
                                )
                        else:
                            # 新 Build
                            new_builds.append(build_data)
                    
                    # 創建新 Builds（批量操作）
                    for build_data in new_builds:
                        # ... 創建 Build 邏輯（與原版相同）...
                        stats['total_builds_synced'] += 1
                    
                    # 🧠 智能下載 Console Log（自適應批次）
                    if builds_need_log:
                        logger.info(
                            f'[Celery] 📝 Job {job.name}: '
                            f'{len(builds_need_log)} 個 Builds 需要下載 Console Log '
                            f'({len(existing_builds) - len(builds_need_log)} 個已下載，跳過)'
                        )
                        
                        # 統計已下載的數量
                        stats['console_logs_already_exists'] += (
                            len(existing_builds) - len(builds_need_log)
                        )
                        
                        # 根據 CPU 調整批次大小
                        batch_size = batch_controller.adjust_batch_size()
                        
                        # 分批處理
                        for i in range(0, len(builds_need_log), batch_size):
                            batch = builds_need_log[i:i+batch_size]
                            
                            # 再次檢查 CPU（動態調整）
                            current_metrics = monitor.get_current_metrics()
                            cpu_samples.append(current_metrics.cpu_percent)
                            
                            if current_metrics.cpu_percent > 80:
                                logger.warning(
                                    f'[Celery] ⚠️  CPU 高負載 '
                                    f'({current_metrics.cpu_percent:.1f}%)，'
                                    f'跳過剩餘 Console Log 下載'
                                )
                                stats['console_logs_skipped_cpu'] += len(builds_need_log) - i
                                break
                            
                            # 批次下載
                            for build_data, db_build in batch:
                                try:
                                    # 下載 Console Log
                                    log_content = client.get_console_log(
                                        job.name,
                                        db_build.build_number
                                    )
                                    
                                    # 存儲到 NAS
                                    storage_service = JenkinsStorageService(
                                        jenkins_server_ip=server.ip_address,
                                        job_name=job.name,
                                        build_number=db_build.build_number
                                    )
                                    
                                    log_result = storage_service.store_console_log(
                                        log_content
                                    )
                                    
                                    if log_result['success']:
                                        db_build.log_file_path = log_result['log_path']
                                        db_build.save(update_fields=['log_file_path'])
                                        stats['console_logs_downloaded'] += 1
                                        
                                        logger.debug(
                                            f'[Celery] ✅ Console Log 已下載: '
                                            f'{job.name} #{db_build.build_number}'
                                        )
                                
                                except Exception as e:
                                    stats['console_logs_failed'] += 1
                                    logger.error(
                                        f'[Celery] ❌ Console Log 下載失敗: '
                                        f'{job.name} #{db_build.build_number} - {e}'
                                    )
                            
                            # 批次間短暫休息（避免持續高負載）
                            time.sleep(0.5)
            
            finally:
                client.close()
        
        # 計算統計數據
        if cpu_samples:
            stats['avg_cpu_percent'] = sum(cpu_samples) / len(cpu_samples)
            stats['peak_cpu_percent'] = max(cpu_samples)
        
        stats['duration'] = time.time() - start_time
        
        logger.info(
            f'[Celery] ✅ 智能同步完成 - '
            f'同步: {stats["total_builds_synced"]} | '
            f'下載: {stats["console_logs_downloaded"]} | '
            f'已存在: {stats["console_logs_already_exists"]} | '
            f'CPU跳過: {stats["console_logs_skipped_cpu"]} | '
            f'失敗: {stats["console_logs_failed"]} | '
            f'暫停: {stats["pauses_count"]} 次 | '
            f'平均 CPU: {stats["avg_cpu_percent"]:.1f}% | '
            f'峰值 CPU: {stats["peak_cpu_percent"]:.1f}% | '
            f'耗時: {stats["duration"]:.1f}s'
        )
        
        return stats
    
    except Exception as exc:
        logger.error('[Celery] 智能同步失敗', exc_info=True)
        stats['success'] = False
        stats['duration'] = time.time() - start_time
        return stats
```

---

##### 2️⃣-補充：**已下載 Console Log 的處理邏輯**

**核心原則**：避免重複下載，節省網路和 CPU 資源

**處理流程**：

```python
# 🔍 檢查邏輯（在智能同步任務中）

for build_data in jenkins_builds:
    build_num = build_data.get('number')
    
    if build_num in existing_builds:
        db_build = existing_builds[build_num]
        
        # ✅ 情況 1：已下載過 Console Log（有 log_file_path）
        if db_build.log_file_path:
            # 🎯 動作：直接跳過，不加入下載隊列
            # 📝 記錄：Debug 日誌（不影響主流程）
            # 📊 統計：console_logs_already_exists + 1
            
            logger.debug(
                f'⏭️  跳過已下載: {job.name} #{build_num} '
                f'(路徑: {db_build.log_file_path})'
            )
            stats['console_logs_already_exists'] += 1
            continue  # ← 直接跳過
        
        # ❌ 情況 2：未下載 Console Log（log_file_path 為 None 或空）
        elif (build_data.get('result') == 'FAILURE' and 
              not build_data.get('building')):
            # 🎯 動作：加入下載隊列
            # 📝 記錄：Info 日誌（重要操作）
            # 📊 統計：待下載數量 + 1
            
            builds_need_log.append((build_data, db_build))
            logger.info(
                f'📝 待下載: {job.name} #{build_num}'
            )
```

**詳細處理策略**：

| 情況 | log_file_path 狀態 | NAS 文件狀態 | 處理動作 | 統計計數 |
|-----|------------------|------------|---------|---------|
| 1️⃣ **正常已下載** | ✅ 有路徑 | ✅ 文件存在 | ⏭️ 跳過 | `console_logs_already_exists` |
| 2️⃣ **路徑損壞** | ✅ 有路徑 | ❌ 文件不存在 | ⏭️ 跳過（暫不處理） | `console_logs_already_exists` |
| 3️⃣ **未下載** | ❌ 無路徑 | ❌ 無文件 | 📥 下載 | `console_logs_downloaded` |
| 4️⃣ **下載中** | ❌ 無路徑 | - | 🔄 等待下次執行 | - |

**為什麼不驗證 NAS 文件是否存在？**

在智能同步任務中，我們**不會**檢查 NAS 文件是否實際存在，原因如下：

1. ⚡ **性能考量**：
   - 檢查文件存在需要 NAS I/O 操作（每個 Build 一次）
   - 如果有 1000 個已下載的 Builds，就需要 1000 次 NAS 訪問
   - 這會大幅增加執行時間和 I/O 負載

2. 🎯 **職責分離**：
   - **智能同步任務**：負責同步元數據、智能下載
   - **驗證任務**：負責檢查數據一致性（獨立的定時任務）

3. 🛡️ **信任資料庫**：
   - 假設資料庫記錄是準確的（`log_file_path` 有值表示已下載）
   - 如果需要修復，由專門的驗證任務處理

**可選：添加文件驗證功能（進階）**

如果需要驗證 NAS 文件完整性，可以創建獨立的驗證任務：

```python
@shared_task(
    name='api.tasks.verify_console_log_integrity',
    time_limit=3600
)
def verify_console_log_integrity(limit=100):
    """
    驗證 Console Log 文件完整性（每天執行一次）
    
    檢查資料庫中有 log_file_path 的 Builds，
    驗證對應的 NAS 文件是否存在。
    
    Args:
        limit: 每次驗證的最大數量
    
    Returns:
        dict: {
            'verified': int,      # 驗證成功的數量
            'missing_files': int, # 文件丟失的數量
            'repaired': int       # 重新下載的數量
        }
    """
    from pathlib import Path
    
    stats = {
        'verified': 0,
        'missing_files': 0,
        'repaired': 0,
        'missing_details': []
    }
    
    # 查詢有 log_file_path 的 Builds
    builds = JenkinsBuild.objects.filter(
        log_file_path__isnull=False
    ).exclude(
        log_file_path=''
    ).select_related('job', 'job__server')[:limit]
    
    for build in builds:
        log_path = Path(build.log_file_path)
        
        # 驗證文件是否存在
        if log_path.exists():
            stats['verified'] += 1
            logger.debug(
                f'✅ 文件存在: {build.job.name} #{build.build_number}'
            )
        else:
            stats['missing_files'] += 1
            logger.warning(
                f'❌ 文件丟失: {build.job.name} #{build.build_number} '
                f'(路徑: {build.log_file_path})'
            )
            
            stats['missing_details'].append({
                'job_name': build.job.name,
                'build_number': build.build_number,
                'log_file_path': build.log_file_path
            })
            
            # 可選：自動修復（清空 log_file_path，等待下次下載）
            # build.log_file_path = None
            # build.save(update_fields=['log_file_path'])
            # stats['repaired'] += 1
    
    logger.info(
        f'[Verify] 驗證完成 - '
        f'成功: {stats["verified"]} | '
        f'丟失: {stats["missing_files"]} | '
        f'修復: {stats["repaired"]}'
    )
    
    return stats
```

**驗證任務的定時配置**：

```python
# backend/network_toolbox/celery.py

# 任務：驗證 Console Log 文件完整性（每天凌晨 4 點）
'verify-console-log-integrity-daily': {
    'task': 'api.tasks.verify_console_log_integrity',
    'schedule': crontab(hour=4, minute=0),  # 每天 04:00 執行
    'kwargs': {
        'limit': 1000  # 每次驗證 1000 個 Builds
    },
    'options': {
        'expires': 3300,  # 任務超時 55 分鐘
    }
},
```

**修復策略選項**：

| 修復策略 | 優點 | 缺點 | 建議 |
|---------|-----|------|------|
| **自動修復** | ✅ 無需人工介入<br>✅ 下次自動重新下載 | ❌ 可能重複下載<br>❌ 增加網路負載 | 🟢 推薦（小量丟失） |
| **手動修復** | ✅ 可控性高<br>✅ 避免誤刪 | ❌ 需要人工處理<br>❌ 延遲修復 | 🟡 大量丟失時使用 |
| **僅記錄** | ✅ 不影響系統<br>✅ 可供分析 | ❌ 不會自動恢復 | 🟢 推薦（初期階段） |

---

##### 3️⃣ **配置文件**

**修改文件**：`backend/network_toolbox/settings.py`

```python
# Jenkins 智能同步配置
JENKINS_ADAPTIVE_SYNC = {
    'enabled': True,  # 是否啟用智能同步
    
    # CPU 閾值配置
    'cpu_thresholds': {
        'low_load': 40.0,      # 低負載閾值（%）
        'medium_load': 70.0,   # 中負載閾值（%）
        'high_load': 85.0,     # 高負載閾值（%）
        'target': 60.0,        # 目標 CPU 使用率（%）
    },
    
    # 批次大小配置
    'batch_sizes': {
        'min': 1,              # 最小批次大小
        'max': 10,             # 最大批次大小
        'initial': 3,          # 初始批次大小
    },
    
    # 下載策略
    'download_strategy': {
        'console_log_enabled': True,           # 是否啟用 Console Log 下載
        'console_log_results': ['FAILURE'],    # 需要下載的 Build 狀態
        'skip_already_downloaded': True,       # 🆕 跳過已下載的 Builds（推薦）
        're_download_if_missing': False,       # 🆕 如果 NAS 文件丟失是否重新下載（需驗證任務支援）
        'max_wait_seconds': 300,               # 最長等待時間（秒）
        'pause_check_interval': 10.0,          # 暫停檢查間隔（秒）
        'batch_sleep_seconds': 0.5,            # 批次間休息時間（秒）
    },
    
    # 🆕 文件完整性驗證（可選功能）
    'integrity_check': {
        'enabled': False,                      # 是否啟用完整性驗證（預設關閉）
        'verify_limit': 1000,                  # 每次驗證的最大數量
        'auto_repair': False,                  # 是否自動修復丟失的文件（慎用）
        'log_missing_files': True,             # 是否記錄丟失的文件列表
    },
    
    # 監控配置
    'monitoring': {
        'sample_interval': 0.5,    # 採樣間隔（秒）
        'enable_detailed_logs': True,  # 是否記錄詳細日誌
    }
}
```

---

##### 4️⃣ **定時任務配置**

**修改文件**：`backend/network_toolbox/celery.py`

```python
# 任務 10（替換原有的）：Jenkins Builds 智能自適應同步（每 10 分鐘）
'sync-jenkins-builds-adaptive-every-10-minutes': {
    'task': 'api.tasks.sync_jenkins_builds_adaptive',
    'schedule': crontab(minute='*/10'),  # 每 10 分鐘執行一次
    'kwargs': {
        'server_id': None,                  # 處理所有 Server
        'max_builds_per_job': 20,
        'max_age_days': 30,
        'enable_console_log_download': True  # 啟用智能下載
    },
    'options': {
        'expires': 540,    # 任務超時 9 分鐘
    }
},

# 可選：禁用原有的同步任務（避免衝突）
# 'sync-jenkins-builds-every-10-minutes': {
#     'task': 'api.tasks.sync_jenkins_builds',
#     ...
# },
```

---

#### 實施效果預測

**場景：50 個 Jobs，1000 個 Builds（其中 200 個需要下載，800 個已下載）**

| 指標 | 原版同步 | 智能同步（方案二） |
|-----|---------|------------------|
| **檢查的 Builds** | 1000 個 | 1000 個 |
| **實際下載** | 200 個 | 200 個 |
| **跳過已下載** | ❌ 每次都檢查 | ✅ 800 個直接跳過 |
| **執行時間** | 10.7 分鐘 | 4-6 分鐘（已下載的不處理） |
| **平均 CPU** | 95% | 50-60% |
| **峰值 CPU** | 100% | 75-85% |
| **下載成功率** | 100% | 90-95%（高負載時跳過部分） |
| **系統穩定性** | ❌ 阻塞其他任務 | ✅ 不影響其他任務 |
| **適應性** | ❌ 固定策略 | ✅ 動態調整 |
| **重複下載** | ❌ 可能重複 | ✅ 避免重複 |

**優勢**：
1. ✅ **防止系統過載**：CPU 超過 85% 自動暫停
2. ✅ **智能資源利用**：低負載時加速，高負載時減速
3. ✅ **保證核心功能**：優先同步元數據，Console Log 可延後
4. ✅ **自適應硬件**：不同性能的機器自動調整策略

**劣勢**：
1. ⚠️ **部分 Log 延遲**：高負載時跳過的 Log 需要下次執行處理
2. ⚠️ **代碼複雜度**：需要維護監控模組
3. ⚠️ **調優成本**：需要根據實際環境調整參數

---

#### 測試與調優步驟

##### 步驟 1：創建監控模組

```bash
# 創建文件
touch backend/library/utils/system_monitor.py

# 安裝依賴
docker exec nt-django pip install psutil
```

##### 步驟 2：測試監控功能

```python
# 在 Django Shell 中測試
docker exec -it nt-django python manage.py shell

from library.utils.system_monitor import SystemMonitor, AdaptiveBatchController

# 測試系統監控
monitor = SystemMonitor()
metrics = monitor.get_current_metrics()
print(f'CPU: {metrics.cpu_percent}%')
print(f'Memory: {metrics.memory_percent}%')

# 測試批次控制器
controller = AdaptiveBatchController()
batch_size = controller.adjust_batch_size()
print(f'建議批次大小: {batch_size}')
```

##### 步驟 3：測試智能同步（Dry-run）

```python
# 手動執行智能同步任務
from api.tasks import sync_jenkins_builds_adaptive

result = sync_jenkins_builds_adaptive.delay(
    server_id=1,  # 測試單個 Server
    enable_console_log_download=False  # 第一次測試：不下載 Log
)

# 查看結果
print(result.get())
```

##### 步驟 4：參數調優

根據實際運行情況調整參數：

```python
# 調整 CPU 閾值
JENKINS_ADAPTIVE_SYNC['cpu_thresholds']['target'] = 50.0  # 降低目標 CPU

# 調整批次大小
JENKINS_ADAPTIVE_SYNC['batch_sizes']['max'] = 5  # 減少最大批次

# 調整暫停策略
JENKINS_ADAPTIVE_SYNC['download_strategy']['max_wait_seconds'] = 600  # 增加等待時間
```

##### 步驟 5：監控與日誌分析

```bash
# 查看詳細日誌
docker compose logs django -f | grep -i "adaptive\|cpu\|batch"

# 分析 CPU 使用率（實時監控）
docker exec nt-django python -c "
import psutil
import time
for i in range(60):
    print(f'CPU: {psutil.cpu_percent(interval=1)}%')
    time.sleep(5)
"
```

---

#### 與方案一的對比

| 特性 | 方案一（移除下載） | 方案二（智能調節） |
|-----|------------------|------------------|
| **實施難度** | 🟢 低（1-2 小時） | 🟡 中（4-6 小時） |
| **代碼複雜度** | 🟢 低 | 🟡 中 |
| **CPU 使用率** | 🟢 20% | 🟢 55-65% |
| **執行時間** | 🟢 40 秒 | 🟡 8-12 分鐘 |
| **即時性** | ❌ Console Log 延遲 | ✅ 智能平衡 |
| **適應性** | ❌ 固定策略 | ✅ 動態調整 |
| **維護成本** | 🟢 低 | 🟡 中 |
| **推薦場景** | 小型專案 | 大型專案 |

---

#### 推薦策略

**短期方案**：
- 先實施**方案一**（快速解決 CPU 100% 問題）
- 驗證系統穩定性

**長期方案**：
- 如果需要更即時的 Console Log 下載
- 且願意投入開發和調優成本
- 可以升級到**方案二**（智能調節）

**混合方案**（最佳實踐）：
```python
# 定時任務配置（兩者並存）

# 1. 輕量級同步（高頻，不下載 Log）
'sync-jenkins-builds-metadata-every-5-minutes': {
    'task': 'api.tasks.sync_jenkins_builds',  # 方案一：只同步元數據
    'schedule': crontab(minute='*/5'),
}

# 2. 智能下載（低頻，有 CPU 保護）
'download-console-logs-adaptive-hourly': {
    'task': 'api.tasks.sync_jenkins_builds_adaptive',  # 方案二：智能下載
    'schedule': crontab(minute=0),  # 每小時一次
    'kwargs': {
        'enable_console_log_download': True  # 只下載 Console Log
    }
}

# 3. 批量存儲（原有任務，處理 Workspace）
'auto-store-jenkins-builds-every-30-minutes': {
    'task': 'api.tasks.auto_store_jenkins_builds_task',
    'schedule': crontab(minute='*/30'),
}
```

---

### 方案三：批量下載 + 資料庫批量寫入（進階優化）

**核心思路**：批量處理減少資料庫和網路開銷

**實施步驟**：

```python
# 批量收集需要下載的 Builds
builds_to_download = []
for build_data, existing_build in builds_to_check:
    if not existing_build.log_file_path:
        builds_to_download.append(existing_build)

# 批量下載（使用連接池）
if builds_to_download:
    with JenkinsClient(...) as client:
        for build in builds_to_download:
            # 使用異步 HTTP 請求（aiohttp）
            # 或者使用線程池並行下載
            pass

# 批量更新資料庫
JenkinsBuild.objects.bulk_update(
    builds_to_download, 
    ['log_file_path'], 
    batch_size=100
)
```

**不推薦原因**：
- 需要引入異步框架（aiohttp）
- 代碼複雜度大幅增加
- 可能導致記憶體問題（大量 Log 內容）

---

## 🎯 最終推薦方案

### **方案一：移除同步任務中的 Console Log 下載**

**實施優先級**：🔥🔥🔥 **高優先級**

**預期效果**：
- ✅ **CPU 使用率**：從 100% 降低至 20%
- ✅ **同步任務執行時間**：從 10.7 分鐘降低至 40 秒
- ✅ **系統穩定性**：大幅提升
- ✅ **代碼可維護性**：職責分離更清晰

**實施時間**：約 1-2 小時

**風險評估**：🟢 **低風險**
- 不影響現有功能
- Console Log 下載邏輯已存在於 `store_jenkins_build_task`
- 只是改變調用時機（從同步任務改為存儲任務）

---

## 📋 實施檢查清單

- [ ] **步驟 1**：備份當前代碼（`git commit`）
- [ ] **步驟 2**：修改 `backend/api/tasks.py`
  - [ ] 移除或註釋 `sync_jenkins_builds` 中的 Console Log 下載邏輯
  - [ ] 添加日誌記錄（標記需要下載的 Builds）
- [ ] **步驟 3**：確認 `store_jenkins_build_task` 包含 Console Log 邏輯
- [ ] **步驟 4**：調整定時任務頻率（`backend/network_toolbox/celery.py`）
  - [ ] 將同步任務改為每 15 分鐘（或保持 10 分鐘）
  - [ ] 確認存儲任務配置正確（每 30 分鐘）
- [ ] **步驟 5**：測試驗證
  - [ ] 手動執行同步任務：`docker exec nt-django python manage.py shell`
    ```python
    from api.tasks import sync_jenkins_builds
    result = sync_jenkins_builds.delay()
    # 觀察 CPU 使用率
    ```
  - [ ] 檢查日誌：`docker compose logs django -f`
  - [ ] 確認執行時間：應在 1-2 分鐘內完成
- [ ] **步驟 6**：監控生產環境
  - [ ] 觀察 CPU 使用率（`htop`）
  - [ ] 檢查任務執行日誌
  - [ ] 確認 Console Log 仍然會被下載（由存儲任務處理）

---

## 🔧 後續優化建議

### 短期優化（1-2 週內）

1. **添加任務執行時間監控**
   ```python
   # 在任務開始和結束時記錄時間
   import time
   start_time = time.time()
   # ... 任務邏輯 ...
   duration = time.time() - start_time
   logger.info(f'[Celery] 任務執行時間: {duration:.2f} 秒')
   ```

2. **添加 CPU 使用率監控**
   ```python
   import psutil
   cpu_percent = psutil.cpu_percent(interval=1)
   logger.info(f'[Celery] CPU 使用率: {cpu_percent}%')
   ```

3. **優化資料庫查詢**
   ```python
   # 使用 select_related 減少 N+1 查詢
   builds = JenkinsBuild.objects.select_related('job', 'job__server').filter(...)
   
   # 使用 only() 只加載需要的字段
   builds = JenkinsBuild.objects.only('id', 'build_number', 'result').filter(...)
   ```

### 長期優化（1-2 個月內）

1. **引入任務隊列分級**
   - 高優先級：活躍 Builds 同步（每 1 分鐘）
   - 中優先級：一般 Builds 同步（每 15 分鐘）
   - 低優先級：存儲任務（每 30 分鐘）

2. **添加任務限流機制**
   ```python
   from celery import group
   from celery.task.control import rate_limit
   
   # 限制同時執行的任務數量
   @shared_task(rate_limit='10/m')  # 每分鐘最多 10 個
   def download_console_log_task(...):
       pass
   ```

3. **引入緩存機制**
   ```python
   from django.core.cache import cache
   
   # 緩存 Jenkins API 響應（1 分鐘）
   cache_key = f'jenkins_builds:{job_name}'
   builds = cache.get(cache_key)
   if not builds:
       builds = client.get_job_builds(job_name)
       cache.set(cache_key, builds, timeout=60)
   ```

---

## 📚 相關文檔

- **定時任務配置**：`backend/network_toolbox/celery.py`
- **同步任務實現**：`backend/api/tasks.py` (sync_jenkins_builds)
- **存儲任務實現**：`backend/api/tasks.py` (store_jenkins_build_task)
- **Jenkins 存儲服務**：`backend/library/services/jenkins_storage_service.py`

---

---

## 🔄 定時任務協調與資源管理規劃

### 當前定時任務架構分析

**Network Toolbox 目前運行的定時任務（共 17 個）**：

| 任務 ID | 任務名稱 | 執行頻率 | 主要操作 | CPU/IO 負載 | 與 Jenkins 相關 |
|--------|---------|---------|---------|------------|---------------|
| **1** | DHCP 日誌同步 | 每 10 分鐘 | SSH + 資料庫寫入 | 🟡 中 | ❌ |
| **2** | DHCP 日誌清理 | 每天 03:00 | 資料庫刪除 | 🟢 低 | ❌ |
| **3** | OUI 資料庫更新 | 每月 1 號 02:00 | HTTP 下載 + 解析 | 🟡 中 | ❌ |
| **4** | NAS 連線檢測 | 每 5 分鐘 | NAS 訪問測試 | 🟢 低 | ❌ |
| **5** | IPXE 網路品質檢測 | 每 5 分鐘 | Ping + SSH | 🟡 中 | ❌ |
| **6** | DHCP Scope 同步 | 每天 04:00 | SSH + 資料庫寫入 | 🟡 中 | ❌ |
| **7** | DHCP 租約同步 | 每 15 分鐘 | SSH + 資料庫寫入 | 🟡 中 | ❌ |
| **8** | Switch 自動識別 | 每小時整點 | 資料庫查詢 + 寫入 | 🟢 低 | ❌ |
| **9** | GitLab 連線檢測 | 每 5 分鐘 | HTTP 請求 | 🟢 低 | ❌ |
| **10** | **Jenkins Builds 同步** | **每 10 分鐘** | **Jenkins API + 下載 Console Log** | **🔴 高（問題所在）** | **✅** |
| **10-1** | 活躍 Jenkins Builds 同步 | 每 1 分鐘 | Jenkins API（只查詢） | 🟢 低 | ✅ |
| **11** | Jenkins Workspace 存儲 | 每小時整點 | Jenkins API + NAS 寫入 | 🔴 高 | ✅ |
| **12** | **Jenkins Builds 存儲** | **每 30 分鐘** | **Jenkins API + NAS 寫入 + Console Log** | **🔴 高** | **✅** |
| **13** | Ansible Inventory 快取清理 | 每天 03:30 | 檔案刪除 | 🟢 低 | ❌ |
| **14** | Jenkins Jobs 同步 | 每小時整點 | Jenkins API | 🟡 中 | ✅ |
| **15** | Jenkins 資料驗證 | 每天 03:00 | 資料庫查詢 + NAS 訪問 | 🟡 中 | ✅ |
| **16** | Jenkins 孤立資料清理 | 每週日 04:00 | 資料庫刪除 + NAS 刪除 | 🟡 中 | ✅ |
| **17** | 清理舊 Jenkins Builds | 每月 1 號 05:00 | 資料庫刪除 | 🟢 低 | ✅ |

**負載等級說明**：
- 🟢 **低負載**：CPU < 20%，執行時間 < 1 分鐘
- 🟡 **中負載**：CPU 20-50%，執行時間 1-5 分鐘
- 🔴 **高負載**：CPU > 50%，執行時間 > 5 分鐘

---

### 任務衝突與資源競爭分析

#### 🔴 **高風險衝突組合**

**1. Console Log 下載重疊（任務 10 + 任務 12）**

```
時間軸：
00:00 ─────────────────────────────────────────
00:05                        [任務 10 開始]
00:10 ─────────── [任務 12 開始] ────────────── ← 衝突！
00:15            ↑ 同時下載 Console Log
00:20            ↑ CPU 100%，NAS I/O 飽和
```

**問題**：
- **任務 10**（`sync_jenkins_builds`）：每 10 分鐘執行，下載 Console Log
- **任務 12**（`auto_store_jenkins_builds_task`）：每 30 分鐘執行，也下載 Console Log
- **重疊概率**：50%（每 30 分鐘中有 2 次任務 10 執行）
- **資源競爭**：
  - 同時訪問 Jenkins API（可能導致速率限制）
  - 同時寫入 NAS（I/O 飽和）
  - 可能重複下載同一個 Build 的 Console Log

**2. NAS 寫入衝突（任務 10 + 任務 11 + 任務 12）**

```
時間軸（每小時整點）：
01:00 ─── [任務 11 開始：Workspace 存儲] ────
01:05 ─── [任務 10 開始：Console Log 下載] ─ ← 衝突！
01:10 ─── [任務 10 可能還在執行]
01:30 ─── [任務 12 開始：Builds 存儲] ──────
```

**問題**：
- 三個任務都需要大量 NAS 寫入操作
- Workspace 文件通常很大（幾百 MB）
- 同時寫入會導致 NAS 性能下降

**3. 資料庫查詢競爭（任務 10 + 任務 14）**

```
時間軸（每小時整點）：
02:00 ─── [任務 14：Jobs 同步] ────────────
02:00 ─── [任務 10：Builds 同步] ──────── ← 同時查詢 JenkinsJob 表
```

**問題**：
- 同時查詢和更新 `JenkinsJob` 表
- 可能導致資料庫鎖（Row-level Lock）
- 影響查詢性能

---

#### 🟡 **中風險衝突組合**

**4. 夜間維護任務堆疊（任務 15 + 任務 6 + 任務 2）**

```
時間軸（凌晨時段）：
03:00 ─── [任務 15：Jenkins 驗證（30 分鐘）] ────
03:00 ─── [任務 2：DHCP 日誌清理] ──────────────
03:30 ─── [任務 13：Ansible 快取清理] ──────────
04:00 ─── [任務 6：DHCP Scope 同步（30 分鐘）] ──
04:00 ─── [任務 16：Jenkins 清理（週日，1 小時）] ← 週日衝突！
```

**問題**：
- 凌晨 3-5 點有多個維護任務集中執行
- 週日凌晨 4 點任務 16（清理）與任務 6 同時執行
- 雖然是低峰時段，但可能影響早晨工作時段

---

### 任務協調策略規劃

#### 策略一：職責分離 + 時間錯開（推薦）

**核心原則**：
1. **同步任務**（Metadata）：輕量、高頻
2. **存儲任務**（Files）：重量、低頻
3. **維護任務**（Cleanup）：夜間執行，時間錯開

**具體調整**：

##### 1️⃣ **分離 Console Log 下載邏輯**

```python
# 任務 10：輕量級同步（移除 Console Log 下載）
'sync-jenkins-builds-metadata-every-10-minutes': {
    'task': 'api.tasks.sync_jenkins_builds',  # 只同步元數據
    'schedule': crontab(minute='*/10'),
    'kwargs': {
        'download_console_log': False,  # 🆕 明確禁用下載
        'max_builds_per_job': 20,
        'max_age_days': 30
    },
    'options': {
        'expires': 540,  # 9 分鐘（應該會更快完成）
    }
}

# 任務 12：重量級存儲（保留 Console Log 下載）
'auto-store-jenkins-builds-every-30-minutes': {
    'task': 'api.tasks.auto_store_jenkins_builds_task',
    'schedule': crontab(minute='*/30'),  # 保持 30 分鐘
    'kwargs': {
        'limit': 50,
        'download_console_log': True,  # 🆕 明確啟用下載
        'priority_results': ['FAILURE', 'UNSTABLE']  # 優先處理失敗 Builds
    },
    'options': {
        'expires': 1500,  # 25 分鐘
    }
}
```

**效果**：
- ✅ 任務 10 執行時間：10.7 分鐘 → **40 秒**
- ✅ 任務 10 CPU 使用率：100% → **20%**
- ✅ Console Log 下載集中在任務 12，可控管理
- ✅ 消除任務 10 和 12 的重複下載

##### 2️⃣ **錯開 NAS 密集任務的執行時間**

```python
# 任務 11：Workspace 存儲（調整到每小時 15 分）
'auto-store-jenkins-workspaces-hourly': {
    'task': 'api.tasks.auto_store_workspaces',
    'schedule': crontab(minute=15),  # 改為每小時 XX:15 執行
    'options': {
        'expires': 2700,  # 45 分鐘
    }
}

# 任務 12：Builds 存儲（調整到每小時 45 分）
'auto-store-jenkins-builds-every-hour': {  # 降低頻率
    'task': 'api.tasks.auto_store_jenkins_builds_task',
    'schedule': crontab(minute=45),  # 改為每小時 XX:45 執行
    'kwargs': {
        'limit': 100,  # 每小時處理更多（因為頻率降低）
    },
    'options': {
        'expires': 900,  # 15 分鐘
    }
}
```

**時間分佈**：
```
每小時時間軸：
XX:00 ─── [任務 14：Jobs 同步（整點）]
XX:10 ─── [任務 10：輕量級 Builds 同步]
XX:15 ─── [任務 11：Workspace 存儲] ← 錯開 15 分鐘
XX:20 ─── [任務 10：輕量級 Builds 同步]
XX:30 ─── 
XX:40 ─── [任務 10：輕量級 Builds 同步]
XX:45 ─── [任務 12：Builds 存儲（含 Console Log）] ← 錯開 30 分鐘
XX:50 ─── [任務 10：輕量級 Builds 同步]
```

**效果**：
- ✅ NAS 寫入任務不重疊（最少間隔 30 分鐘）
- ✅ 每個任務都有足夠的執行時間窗口
- ✅ 降低 I/O 競爭

##### 3️⃣ **夜間維護任務時間調整**

```python
# 任務 2：DHCP 日誌清理（保持 03:00）
'cleanup-old-dhcp-logs-daily': {
    'schedule': crontab(hour=3, minute=0),  # 03:00
}

# 任務 15：Jenkins 驗證（調整到 02:00）
'validate-jenkins-data-daily': {
    'schedule': crontab(hour=2, minute=0),  # 改為 02:00（提前 1 小時）
}

# 任務 13：Ansible 快取清理（調整到 05:00）
'clean-expired-ansible-caches-daily': {
    'schedule': crontab(hour=5, minute=0),  # 改為 05:00（延後到清晨）
}

# 任務 6：DHCP Scope 同步（調整到 04:30）
'sync-all-dhcp-scopes-daily': {
    'schedule': crontab(hour=4, minute=30),  # 改為 04:30（錯開 30 分鐘）
}

# 任務 16：Jenkins 清理（調整到週日 01:00）
'cleanup-orphaned-jenkins-data-weekly': {
    'schedule': crontab(hour=1, minute=0, day_of_week=0),  # 改為週日 01:00（提前 3 小時）
}
```

**夜間時間軸（優化後）**：
```
週日凌晨：
01:00 ─── [任務 16：Jenkins 孤立資料清理（1 小時）]
02:00 ─── [任務 15：Jenkins 驗證（30 分鐘）]
       ─── [任務 3：OUI 更新（每月 1 號）]
03:00 ─── [任務 2：DHCP 日誌清理（10 分鐘）]
04:30 ─── [任務 6：DHCP Scope 同步（30 分鐘）]
05:00 ─── [任務 13：Ansible 快取清理（5 分鐘）]
       ─── [任務 17：清理舊 Builds（每月 1 號）]
```

**效果**：
- ✅ 避免多個任務同時執行
- ✅ 重量級任務（Jenkins 清理）提前執行，不影響早晨
- ✅ 每個任務都有獨立的時間窗口

---

#### 策略二：資源池管理（進階方案）

**核心思路**：使用 Celery 隊列和優先級管理不同類型的任務

##### 1️⃣ **創建專用任務隊列**

```python
# backend/network_toolbox/celery.py

# 定義多個隊列
from kombu import Queue

app.conf.task_queues = (
    Queue('default',      routing_key='task.default'),      # 預設隊列
    Queue('lightweight',  routing_key='task.lightweight'),  # 輕量級任務
    Queue('storage',      routing_key='task.storage'),      # 存儲任務（NAS 密集）
    Queue('maintenance',  routing_key='task.maintenance'),  # 維護任務（夜間）
)

# 設置任務路由
app.conf.task_routes = {
    # 輕量級任務（高優先級）
    'api.tasks.sync_jenkins_builds': {
        'queue': 'lightweight',
        'routing_key': 'task.lightweight',
    },
    'api.tasks.sync_active_jenkins_builds': {
        'queue': 'lightweight',
        'routing_key': 'task.lightweight',
    },
    'api.tasks.check_nas_connection_task': {
        'queue': 'lightweight',
        'routing_key': 'task.lightweight',
    },
    
    # 存儲任務（中優先級，資源密集）
    'api.tasks.auto_store_jenkins_builds_task': {
        'queue': 'storage',
        'routing_key': 'task.storage',
    },
    'api.tasks.auto_store_workspaces': {
        'queue': 'storage',
        'routing_key': 'task.storage',
    },
    'api.tasks.store_jenkins_build_task': {
        'queue': 'storage',
        'routing_key': 'task.storage',
    },
    
    # 維護任務（低優先級，夜間執行）
    'api.tasks.cleanup_old_logs_task': {
        'queue': 'maintenance',
        'routing_key': 'task.maintenance',
    },
    'api.tasks.validate_jenkins_data': {
        'queue': 'maintenance',
        'routing_key': 'task.maintenance',
    },
    'api.tasks.cleanup_old_jenkins_builds_task': {
        'queue': 'maintenance',
        'routing_key': 'task.maintenance',
    },
}
```

##### 2️⃣ **啟動多個 Worker（不同隊列）**

**修改文件**：`backend/supervisord.conf`

```ini
[program:celery-worker-lightweight]
command=celery -A network_toolbox worker -Q lightweight --concurrency=4 --loglevel=info
directory=/app
user=root
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/app/logs/celery_lightweight.log

[program:celery-worker-storage]
command=celery -A network_toolbox worker -Q storage --concurrency=2 --loglevel=info
directory=/app
user=root
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/app/logs/celery_storage.log

[program:celery-worker-maintenance]
command=celery -A network_toolbox worker -Q maintenance --concurrency=1 --loglevel=info
directory=/app
user=root
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/app/logs/celery_maintenance.log

[program:celery-beat]
command=celery -A network_toolbox beat --loglevel=info
directory=/app
user=root
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/app/logs/celery_beat.log
```

**Worker 配置說明**：
- **lightweight 隊列**：4 個並發（處理多個輕量級任務）
- **storage 隊列**：2 個並發（限制 NAS I/O 競爭）
- **maintenance 隊列**：1 個並發（串行執行維護任務）

**效果**：
- ✅ 輕量級任務不會被重量級任務阻塞
- ✅ 存儲任務並發限制（避免 NAS 過載）
- ✅ 維護任務獨立執行（不影響日常任務）

---

#### 策略三：智能限流與熔斷（防禦性方案）

**核心思路**：為資源密集型任務添加限流和熔斷機制

##### 1️⃣ **任務速率限制**

```python
# backend/api/tasks.py

@shared_task(
    bind=True,
    name='api.tasks.auto_store_jenkins_builds_task',
    rate_limit='10/m',  # 🆕 每分鐘最多 10 個任務實例
    max_retries=2,
    time_limit=1800
)
def auto_store_jenkins_builds_task(self, limit: int = 50):
    # ... 任務邏輯 ...
    pass
```

##### 2️⃣ **NAS I/O 熔斷器**

**創建新文件**：`backend/library/utils/circuit_breaker.py`

```python
"""
熔斷器模式實現

當 NAS I/O 失敗率過高時自動熔斷，避免雪崩效應
"""

import time
import logging
from enum import Enum
from typing import Callable, Any

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """熔斷器狀態"""
    CLOSED = 'closed'      # 正常狀態
    OPEN = 'open'          # 熔斷狀態（拒絕請求）
    HALF_OPEN = 'half_open'  # 半開狀態（嘗試恢復）


class CircuitBreaker:
    """熔斷器"""
    
    def __init__(
        self,
        failure_threshold: int = 5,      # 失敗次數閾值
        timeout: int = 60,               # 熔斷超時（秒）
        half_open_max_calls: int = 3     # 半開狀態最大嘗試次數
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.half_open_max_calls = half_open_max_calls
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.half_open_calls = 0
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        執行受保護的函數
        
        Args:
            func: 要執行的函數
            *args, **kwargs: 函數參數
        
        Returns:
            函數返回值
        
        Raises:
            Exception: 熔斷器開啟時拋出異常
        """
        # 檢查是否可以執行
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                logger.info('[CircuitBreaker] 進入半開狀態，嘗試恢復')
            else:
                logger.warning('[CircuitBreaker] 熔斷器開啟，拒絕請求')
                raise Exception('Circuit breaker is OPEN')
        
        try:
            # 執行函數
            result = func(*args, **kwargs)
            
            # 成功
            self._on_success()
            return result
        
        except Exception as e:
            # 失敗
            self._on_failure()
            raise e
    
    def _on_success(self):
        """處理成功"""
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_calls += 1
            
            if self.half_open_calls >= self.half_open_max_calls:
                # 恢復成功
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info('[CircuitBreaker] 恢復正常狀態')
        else:
            self.failure_count = 0
    
    def _on_failure(self):
        """處理失敗"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(
                f'[CircuitBreaker] 失敗次數達到閾值 ({self.failure_count})，'
                f'熔斷器開啟'
            )
        
        if self.state == CircuitState.HALF_OPEN:
            # 半開狀態失敗，重新開啟
            self.state = CircuitState.OPEN
            logger.warning('[CircuitBreaker] 半開狀態失敗，重新開啟熔斷器')
    
    def _should_attempt_reset(self) -> bool:
        """判斷是否應該嘗試恢復"""
        if self.last_failure_time is None:
            return False
        
        return (time.time() - self.last_failure_time) >= self.timeout


# 全局熔斷器實例
nas_circuit_breaker = CircuitBreaker(
    failure_threshold=5,  # 5 次失敗後熔斷
    timeout=300,          # 5 分鐘後嘗試恢復
    half_open_max_calls=3  # 半開狀態嘗試 3 次
)
```

##### 3️⃣ **在任務中使用熔斷器**

```python
# backend/api/tasks.py

from library.utils.circuit_breaker import nas_circuit_breaker

@shared_task(...)
def auto_store_jenkins_builds_task(self, limit: int = 50):
    # ... 前置邏輯 ...
    
    for build in builds_to_store:
        try:
            # 🛡️ 使用熔斷器保護 NAS 寫入操作
            nas_circuit_breaker.call(
                storage_service.store_console_log,
                log_content
            )
        except Exception as e:
            if 'Circuit breaker is OPEN' in str(e):
                logger.error('[Celery] NAS 熔斷器開啟，暫停存儲操作')
                break  # 停止本次任務
            else:
                logger.error(f'[Celery] 存儲失敗: {e}')
```

**效果**：
- ✅ 當 NAS 出現故障時自動熔斷（避免雪崩）
- ✅ 5 分鐘後自動嘗試恢復
- ✅ 保護系統不被故障拖垮

---

### 最終推薦協調方案

**階段一：立即實施（1-2 小時）**

1. ✅ **移除任務 10 的 Console Log 下載邏輯**（方案一-1）
2. ✅ **調整任務 11、12 的執行時間**（方案一-2）
3. ✅ **調整夜間維護任務時間**（方案一-3）

**階段二：中期優化（1-2 週）**

4. ✅ **引入任務隊列分級**（方案二-1）
5. ✅ **配置多個 Worker**（方案二-2）

**階段三：長期加固（1-2 個月）**

6. ✅ **添加熔斷器機制**（方案三）
7. ✅ **實施智能限流**（方案三）

---

### 協調方案對比表

| 方案 | 實施難度 | 效果 | 維護成本 | 推薦優先級 |
|-----|---------|------|---------|-----------|
| **方案一：職責分離 + 時間錯開** | 🟢 低 | 🟢 立即見效 | 🟢 低 | 🔥🔥🔥 **高** |
| **方案二：資源池管理** | 🟡 中 | 🟢 顯著提升 | 🟡 中 | 🔥🔥 **中** |
| **方案三：智能限流與熔斷** | 🟡 中 | 🟢 防禦性增強 | 🟡 中 | 🔥 **低** |

---

---

## 🚀 立即實施階段詳細規劃（1-2 小時）

### 總覽

**目標**：在 1-2 小時內完成三個關鍵調整，立即解決 CPU 100% 問題

**預期效果**：
- ✅ CPU 使用率：100% → 20-30%
- ✅ 任務執行時間：10.7 分鐘 → 40-60 秒
- ✅ 消除任務衝突（Console Log 下載重疊）
- ✅ 系統穩定性大幅提升

---

### 步驟一：移除任務 10 的 Console Log 下載邏輯（30 分鐘）

#### 📍 **定位問題代碼**

**文件**：`backend/api/tasks.py`  
**函數**：`sync_jenkins_builds` (第 1713-2200 行左右)  
**問題邏輯位置**：約第 2000-2100 行

**當前代碼結構**：
```python
@shared_task(
    bind=True,
    name='api.tasks.sync_jenkins_builds',
    max_retries=2,
    time_limit=3600,
    soft_time_limit=3300
)
def sync_jenkins_builds(self, server_id=None, max_builds_per_job=20, max_age_days=3):
    """同步 Jenkins Builds 到資料庫（只處理新 Builds）"""
    
    # ... 前面的邏輯（保持不變）...
    
    # 處理每個 Build
    for build_data in jenkins_builds:
        # 創建或更新 Build 記錄
        build, created = JenkinsBuild.objects.update_or_create(...)
        
        # ❌ 問題所在：這裡有下載 Console Log 的邏輯
        # 需要完全移除或註釋掉這段代碼
        if not build.log_file_path and build.result == 'FAILURE':
            # 從 Jenkins API 獲取 Console Log
            log_content = client.get_console_log(job.name, build_number)
            
            # 存儲到 NAS
            from library.services.jenkins_storage_service import JenkinsStorageService
            storage_service = JenkinsStorageService(...)
            log_result = storage_service.store_console_log(log_content)
            
            # 更新資料庫
            if log_result['success']:
                build.log_file_path = log_result['log_path']
                build.save()
```

#### 🛠️ **修改方案**

**方案 A：完全移除（推薦）**

```python
# ✅ 修改後：完全移除 Console Log 下載邏輯

for build_data in jenkins_builds:
    # 創建或更新 Build 記錄
    build, created = JenkinsBuild.objects.update_or_create(...)
    
    # ✅ 只記錄需要下載 Console Log 的 Build（可選）
    if not build.log_file_path and build.result in ['FAILURE', 'UNSTABLE']:
        logger.debug(
            f'[Celery] ℹ️  Build {build.job.name} #{build.build_number} '
            f'缺少 Console Log，將由存儲任務處理'
        )
    
    # 繼續處理其他邏輯...
```

**方案 B：條件性禁用（保守方案）**

如果擔心直接刪除代碼，可以添加一個配置開關：

```python
# backend/network_toolbox/settings.py

# Jenkins 同步任務配置
JENKINS_SYNC_CONFIG = {
    'enable_console_log_download': False,  # 🆕 禁用同步任務中的 Console Log 下載
    'download_in_storage_task_only': True, # 🆕 只在存儲任務中下載
}
```

```python
# backend/api/tasks.py

from django.conf import settings

def sync_jenkins_builds(...):
    # ...
    
    # ✅ 使用配置控制是否下載 Console Log
    sync_config = getattr(settings, 'JENKINS_SYNC_CONFIG', {})
    enable_console_log = sync_config.get('enable_console_log_download', False)
    
    if enable_console_log and not build.log_file_path:
        # 下載 Console Log（保留原邏輯）
        ...
    else:
        # 跳過下載，只記錄
        logger.debug(f'[Celery] ⏭️  跳過 Console Log 下載（由配置禁用）')
```

#### 📝 **實施步驟**

1. **備份代碼**
   ```bash
   cd /home/owner/Codes/network-toolbox
   git add .
   git commit -m "Backup before removing Console Log download from sync task"
   ```

2. **定位代碼**
   ```bash
   # 搜尋 Console Log 下載相關代碼
   grep -n "get_console_log\|store_console_log" backend/api/tasks.py
   
   # 預期會找到兩處：
   # 1. sync_jenkins_builds 函數（需要移除）
   # 2. store_jenkins_build_task 函數（保留）
   ```

3. **修改 `sync_jenkins_builds` 函數**
   - 找到 Console Log 下載的 `if` 區塊
   - 刪除或註釋掉整個區塊（約 20-30 行代碼）
   - 替換為簡單的 `logger.debug` 記錄

4. **驗證修改**
   ```bash
   # 檢查語法
   docker exec nt-django python manage.py check
   
   # 如果有語法錯誤，修正後再檢查
   ```

5. **重啟服務**
   ```bash
   docker compose restart django
   ```

#### ✅ **驗證效果**

**測試方法 1：手動執行任務**
```bash
docker exec -it nt-django python manage.py shell
```

```python
from api.tasks import sync_jenkins_builds
import time

start = time.time()
result = sync_jenkins_builds(server_id=1, max_builds_per_job=20)
duration = time.time() - start

print(f"執行時間: {duration:.1f} 秒")
print(f"結果: {result}")

# 預期：
# - 執行時間應該在 30-60 秒內（原本 10.7 分鐘）
# - 日誌中不應該出現 "下載 Console Log" 相關訊息
```

**測試方法 2：監控 CPU**
```bash
# 在任務執行期間監控 CPU
docker exec nt-django python -c "
import psutil
import time
for i in range(30):
    cpu = psutil.cpu_percent(interval=1)
    print(f'{i}s: CPU {cpu}%')
    time.sleep(2)
"
```

**預期結果**：
- ✅ CPU 使用率保持在 20-30% 以下
- ✅ 執行時間縮短至 1 分鐘內
- ✅ 日誌中只看到「同步元數據」，沒有「下載 Console Log」

---

### 步驟二：調整任務 11、12 的執行時間（20 分鐘）

#### 📍 **當前任務配置**

**文件**：`backend/network_toolbox/celery.py`

**當前時間表**：
```python
# 任務 11：Workspace 存儲（每小時整點）
'auto-store-jenkins-workspaces-hourly': {
    'task': 'api.tasks.auto_store_workspaces',
    'schedule': crontab(minute=0),  # XX:00
}

# 任務 12：Builds 存儲（每 30 分鐘）
'auto-store-jenkins-builds-every-30-minutes': {
    'task': 'api.tasks.auto_store_jenkins_builds_task',
    'schedule': crontab(minute='*/30'),  # XX:00, XX:30
}
```

**問題**：
- 任務 11 在 XX:00 執行（Workspace 存儲，大量 NAS 寫入）
- 任務 12 在 XX:00 和 XX:30 執行（Builds 存儲 + Console Log 下載）
- 兩者在 XX:00 和 XX:30 同時執行，導致 NAS I/O 競爭

#### 🛠️ **修改方案**

**目標**：錯開執行時間，確保 NAS 密集任務不重疊

**調整後的時間表**：
```python
# 任務 11：Workspace 存儲（調整到每小時 15 分）
'auto-store-jenkins-workspaces-hourly': {
    'task': 'api.tasks.auto_store_workspaces',
    'schedule': crontab(minute=15),  # ✅ 改為 XX:15 執行
    'options': {
        'expires': 2700,  # 45 分鐘超時（確保不會跨到下個週期）
    }
}

# 任務 12：Builds 存儲（調整到每小時 45 分）
'auto-store-jenkins-builds-every-hour': {  # ✅ 改為每小時（降低頻率）
    'task': 'api.tasks.auto_store_jenkins_builds_task',
    'schedule': crontab(minute=45),  # ✅ 改為 XX:45 執行
    'kwargs': {
        'limit': 100,  # ✅ 每小時處理更多（因為頻率降低）
    },
    'options': {
        'expires': 900,  # 15 分鐘超時
    }
}
```

**時間分佈（優化後）**：
```
每小時時間軸：
XX:00 ─── [任務 14：Jobs 同步（輕量）]
XX:10 ─── [任務 10：Builds 同步（已優化，輕量）]
XX:15 ─── [任務 11：Workspace 存儲] ← 30 分鐘間隔
XX:20 ─── [任務 10：Builds 同步]
XX:30 ─── 
XX:40 ─── [任務 10：Builds 同步]
XX:45 ─── [任務 12：Builds 存儲] ← 30 分鐘間隔
XX:50 ─── [任務 10：Builds 同步]
```

#### 📝 **實施步驟**

1. **編輯 Celery 配置**
   ```bash
   docker exec -it nt-django nano /app/network_toolbox/celery.py
   
   # 或在 VS Code 中直接編輯：
   # backend/network_toolbox/celery.py
   ```

2. **修改任務 11 配置**
   - 找到 `'auto-store-jenkins-workspaces-hourly'`
   - 修改 `crontab(minute=0)` → `crontab(minute=15)`
   - 添加 `'expires': 2700`

3. **修改任務 12 配置**
   - 找到 `'auto-store-jenkins-builds-every-30-minutes'`
   - 修改任務名稱為 `'auto-store-jenkins-builds-every-hour'`
   - 修改 `crontab(minute='*/30')` → `crontab(minute=45)`
   - 修改 `'limit': 50` → `'limit': 100`
   - 修改 `'expires': 1500` → `'expires': 900`

4. **重啟 Celery Beat**
   ```bash
   docker compose restart django
   
   # 或只重啟 Celery Beat（如果使用獨立容器）
   # docker exec nt-django supervisorctl restart celery-beat
   ```

#### ✅ **驗證效果**

**檢查任務排程**：
```bash
docker exec -it nt-django python manage.py shell
```

```python
from network_toolbox.celery import app

# 查看所有定時任務
for task_name, task_config in app.conf.beat_schedule.items():
    if 'jenkins' in task_name.lower():
        schedule = task_config['schedule']
        print(f"{task_name}: {schedule}")

# 預期輸出：
# auto-store-jenkins-workspaces-hourly: <crontab: minute=15>
# auto-store-jenkins-builds-every-hour: <crontab: minute=45>
```

**監控實際執行時間**：
```bash
# 查看 Celery Beat 日誌
docker compose logs django -f | grep -i "auto-store"

# 預期：
# - Workspace 存儲在 XX:15 執行
# - Builds 存儲在 XX:45 執行
# - 兩者相隔 30 分鐘
```

---

### 步驟三：調整夜間維護任務時間（20 分鐘）

#### 📍 **當前夜間任務配置**

**文件**：`backend/network_toolbox/celery.py`

**當前時間表（有衝突）**：
```
凌晨時段：
02:00 ─── [任務 3：OUI 更新（每月 1 號）]
03:00 ─── [任務 2：DHCP 日誌清理]
03:00 ─── [任務 15：Jenkins 驗證（30 分鐘）] ← 衝突！
03:30 ─── [任務 13：Ansible 快取清理]
04:00 ─── [任務 6：DHCP Scope 同步（30 分鐘）]
04:00 ─── [任務 16：Jenkins 清理（週日，1 小時）] ← 衝突！
05:00 ─── [任務 17：清理舊 Builds（每月 1 號）]
```

**問題**：
- 03:00：任務 2 和任務 15 同時執行
- 04:00：任務 6 和任務 16 同時執行（週日）
- 週日凌晨 4 點可能需要執行 2 小時（任務 16 + 任務 6）

#### 🛠️ **調整方案**

**目標**：錯開所有維護任務，確保每個任務有獨立時間窗口

**調整後的時間表**：
```
凌晨時段（優化後）：
01:00 ─── [任務 16：Jenkins 清理（週日，1 小時）] ← 提前 3 小時
02:00 ─── [任務 15：Jenkins 驗證（30 分鐘）] ← 提前 1 小時
       ─── [任務 3：OUI 更新（每月 1 號）] ← 保持不變
03:00 ─── [任務 2：DHCP 日誌清理（10 分鐘）] ← 保持不變
04:30 ─── [任務 6：DHCP Scope 同步（30 分鐘）] ← 延後 30 分鐘
05:00 ─── [任務 13：Ansible 快取清理（5 分鐘）] ← 保持不變
       ─── [任務 17：清理舊 Builds（每月 1 號）] ← 保持不變
```

#### 📝 **具體修改**

**修改 1：任務 15（Jenkins 驗證）**
```python
# 修改前
'validate-jenkins-data-daily': {
    'schedule': crontab(hour=3, minute=0),  # 03:00
}

# 修改後
'validate-jenkins-data-daily': {
    'schedule': crontab(hour=2, minute=0),  # ✅ 改為 02:00
    'options': {
        'expires': 3300,  # 55 分鐘超時
    }
}
```

**修改 2：任務 16（Jenkins 清理）**
```python
# 修改前
'cleanup-orphaned-jenkins-data-weekly': {
    'schedule': crontab(hour=4, minute=0, day_of_week=0),  # 週日 04:00
}

# 修改後
'cleanup-orphaned-jenkins-data-weekly': {
    'schedule': crontab(hour=1, minute=0, day_of_week=0),  # ✅ 改為週日 01:00
    'options': {
        'expires': 3600,  # 1 小時超時
    }
}
```

**修改 3：任務 6（DHCP Scope 同步）**
```python
# 修改前
'sync-all-dhcp-scopes-daily': {
    'schedule': crontab(hour=4, minute=0),  # 04:00
}

# 修改後
'sync-all-dhcp-scopes-daily': {
    'schedule': crontab(hour=4, minute=30),  # ✅ 改為 04:30
    'options': {
        'expires': 1500,  # 25 分鐘超時
    }
}
```

**修改 4：任務 13（Ansible 快取清理）**
```python
# 修改前
'clean-expired-ansible-caches-daily': {
    'schedule': crontab(hour=3, minute=30),  # 03:30
}

# 修改後（可選，避免與任務 2 過近）
'clean-expired-ansible-caches-daily': {
    'schedule': crontab(hour=5, minute=0),  # ✅ 改為 05:00
    'options': {
        'expires': 1800,  # 30 分鐘超時
    }
}
```

#### 📝 **實施步驟**

1. **編輯 Celery 配置**
   ```bash
   # 在 VS Code 中編輯
   # backend/network_toolbox/celery.py
   ```

2. **依序修改 4 個任務的 crontab 配置**
   - `validate-jenkins-data-daily`：hour=2
   - `cleanup-orphaned-jenkins-data-weekly`：hour=1
   - `sync-all-dhcp-scopes-daily`：hour=4, minute=30
   - `clean-expired-ansible-caches-daily`：hour=5

3. **重啟 Celery Beat**
   ```bash
   docker compose restart django
   ```

#### ✅ **驗證效果**

**檢查夜間任務排程**：
```bash
docker exec -it nt-django python manage.py shell
```

```python
from network_toolbox.celery import app

# 查看所有夜間維護任務
night_tasks = [
    'validate-jenkins-data-daily',
    'cleanup-orphaned-jenkins-data-weekly',
    'sync-all-dhcp-scopes-daily',
    'clean-expired-ansible-caches-daily',
    'cleanup-old-dhcp-logs-daily'
]

for task_name in night_tasks:
    if task_name in app.conf.beat_schedule:
        schedule = app.conf.beat_schedule[task_name]['schedule']
        print(f"{task_name}: {schedule}")

# 預期輸出：
# cleanup-orphaned-jenkins-data-weekly: <crontab: hour=1, day_of_week=0>
# validate-jenkins-data-daily: <crontab: hour=2>
# cleanup-old-dhcp-logs-daily: <crontab: hour=3>
# sync-all-dhcp-scopes-daily: <crontab: hour=4, minute=30>
# clean-expired-ansible-caches-daily: <crontab: hour=5>
```

**等待實際執行驗證**：
```bash
# 查看 Celery Beat 日誌（第二天凌晨）
docker compose logs django --since 1h | grep -i "validate-jenkins\|cleanup-orphaned\|sync-all-dhcp-scopes"

# 預期：
# - 01:00 執行 Jenkins 清理（週日）
# - 02:00 執行 Jenkins 驗證
# - 03:00 執行 DHCP 日誌清理
# - 04:30 執行 DHCP Scope 同步
# - 05:00 執行 Ansible 快取清理
```

---

### 總結：立即實施階段檢查清單

#### 完成檢查清單

- [ ] **步驟 1：移除 Console Log 下載（30 分鐘）**
  - [ ] 備份代碼（`git commit`）
  - [ ] 定位 `sync_jenkins_builds` 函數中的 Console Log 下載邏輯
  - [ ] 移除或註釋相關代碼（約 20-30 行）
  - [ ] 驗證語法（`python manage.py check`）
  - [ ] 重啟服務（`docker compose restart django`）
  - [ ] 測試執行時間（應該 < 1 分鐘）
  - [ ] 確認 CPU 使用率（應該 < 30%）

- [ ] **步驟 2：調整任務 11、12 時間（20 分鐘）**
  - [ ] 編輯 `backend/network_toolbox/celery.py`
  - [ ] 修改任務 11：`minute=15`
  - [ ] 修改任務 12：`minute=45`, `limit=100`
  - [ ] 重啟 Celery Beat
  - [ ] 驗證排程配置
  - [ ] 監控實際執行時間

- [ ] **步驟 3：調整夜間任務時間（20 分鐘）**
  - [ ] 編輯 `backend/network_toolbox/celery.py`
  - [ ] 修改任務 15：`hour=2`
  - [ ] 修改任務 16：`hour=1`
  - [ ] 修改任務 6：`hour=4, minute=30`
  - [ ] 修改任務 13：`hour=5`
  - [ ] 重啟 Celery Beat
  - [ ] 驗證排程配置

#### 預期成果

**立即見效**：
- ✅ CPU 使用率：100% → 20-30%
- ✅ 任務 10 執行時間：10.7 分鐘 → 40-60 秒
- ✅ 消除 NAS I/O 競爭（任務間隔 30 分鐘）

**次日驗證**：
- ✅ 夜間任務不重疊（查看日誌）
- ✅ 系統整體穩定性提升
- ✅ 日誌中無 CPU 過載警告

**長期效果**：
- ✅ 系統負載均衡
- ✅ 任務執行可預測
- ✅ 為後續優化奠定基礎

---

**最後更新**：2025-11-25  
**文檔狀態**：詳細實施規劃完成（未執行）  
**預計時間**：1-2 小時  
**下一步行動**：等待用戶確認後開始執行
