# Jenkins 同步機制 - 系統保護與資源管理

## 📋 問題背景

之前發生過 **CPU 使用率飆升到 100%** 的問題，需要在改進同步機制時加入完整的保護機制。

### 可能導致 CPU 過載的原因

```
1. 同時處理大量 Jobs/Builds
   ├─ 過多的 API 請求
   ├─ 大量的資料庫查詢
   └─ 複雜的資料比對邏輯

2. 沒有速率限制
   ├─ 無限制地連續發送請求
   ├─ 並發執行多個同步任務
   └─ 沒有請求間隔控制

3. 記憶體洩漏
   ├─ 大量資料載入到記憶體
   ├─ 沒有及時釋放
   └─ 累積導致系統壓力

4. 死鎖或無限循環
   ├─ 錯誤處理不當
   ├─ 重試機制失控
   └─ 任務卡住不退出
```

---

## 🛡️ 多層保護機制設計

### 架構圖

```
┌─────────────────────────────────────────────────────────┐
│  層級 1: 任務調度保護（Celery 層）                       │
│  ├─ 任務互斥鎖（同時只能執行一個同步任務）                │
│  ├─ 任務優先級控制                                       │
│  ├─ 超時保護（硬限制 + 軟限制）                          │
│  └─ 並發控制（限制 Worker 數量）                         │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│  層級 2: API 請求保護（網路層）                          │
│  ├─ 速率限制（每秒最多 N 個請求）                        │
│  ├─ 請求超時控制                                         │
│  ├─ 連接池管理                                           │
│  └─ 指數退避重試                                         │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│  層級 3: 資料處理保護（應用層）                          │
│  ├─ 批次處理（分批載入資料）                             │
│  ├─ 資料量限制（單次最多處理 N 筆）                      │
│  ├─ 記憶體監控（超過閾值暫停）                           │
│  └─ 進度追蹤（可中斷恢復）                               │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│  層級 4: 系統資源保護（系統層）                          │
│  ├─ CPU 使用率監控                                       │
│  ├─ 記憶體使用率監控                                     │
│  ├─ 資料庫連接池管理                                     │
│  └─ 自動降級機制                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🔒 層級 1：任務調度保護

### 1.1 任務互斥鎖（防止重複執行）

**問題**：多個同步任務同時執行 → CPU 負載倍增

**解決方案**：使用分佈式鎖確保同時只執行一個同步任務

```python
# 文件：backend/library/utils/task_lock.py

import logging
from django.core.cache import cache
from functools import wraps
from datetime import timedelta

logger = logging.getLogger(__name__)


class TaskLock:
    """任務分佈式鎖"""
    
    @staticmethod
    def acquire(lock_name: str, timeout: int = 3600, wait: bool = False) -> bool:
        """
        獲取鎖
        
        Args:
            lock_name: 鎖名稱
            timeout: 鎖超時時間（秒）
            wait: 是否等待鎖釋放
            
        Returns:
            bool: 是否成功獲取鎖
        """
        lock_key = f'task_lock:{lock_name}'
        
        if wait:
            # 等待模式：最多等待 5 分鐘
            for _ in range(60):
                if cache.add(lock_key, True, timeout):
                    logger.info(f'✅ 獲取鎖成功: {lock_name}')
                    return True
                time.sleep(5)  # 每 5 秒檢查一次
            
            logger.warning(f'⏱️  等待鎖超時: {lock_name}')
            return False
        else:
            # 非等待模式：立即返回
            if cache.add(lock_key, True, timeout):
                logger.info(f'✅ 獲取鎖成功: {lock_name}')
                return True
            else:
                logger.warning(f'🔒 鎖已被佔用: {lock_name}')
                return False
    
    @staticmethod
    def release(lock_name: str):
        """釋放鎖"""
        lock_key = f'task_lock:{lock_name}'
        cache.delete(lock_key)
        logger.info(f'🔓 釋放鎖: {lock_name}')
    
    @staticmethod
    def is_locked(lock_name: str) -> bool:
        """檢查鎖是否存在"""
        lock_key = f'task_lock:{lock_name}'
        return cache.get(lock_key) is not None


def with_task_lock(lock_name: str, timeout: int = 3600, wait: bool = False):
    """
    任務鎖裝飾器
    
    使用範例：
        @with_task_lock('sync_jenkins_builds', timeout=3600)
        def my_task():
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 獲取鎖
            if not TaskLock.acquire(lock_name, timeout, wait):
                logger.warning(f'⚠️  任務已在執行中，跳過: {func.__name__}')
                return {
                    'success': False,
                    'message': '任務已在執行中',
                    'skipped': True
                }
            
            try:
                # 執行任務
                result = func(*args, **kwargs)
                return result
            finally:
                # 釋放鎖
                TaskLock.release(lock_name)
        
        return wrapper
    return decorator
```

### 1.2 改進後的任務定義

```python
# 文件：backend/api/tasks.py

from library.utils.task_lock import with_task_lock
from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name='api.tasks.sync_jenkins_builds',
    max_retries=2,
    default_retry_delay=300,
    time_limit=3600,        # 🔒 硬限制：1 小時
    soft_time_limit=3300,   # 🔒 軟限制：55 分鐘
    acks_late=True,         # 🔒 任務完成後才確認（防止任務丟失）
    reject_on_worker_lost=True  # 🔒 Worker 失聯時拒絕任務
)
@with_task_lock('sync_jenkins_builds', timeout=3600)  # 🔒 互斥鎖
def sync_jenkins_builds(self, server_id=None, **kwargs):
    """
    同步 Jenkins Builds（帶保護機制）
    """
    try:
        # ... 執行同步邏輯 ...
        pass
    except SoftTimeLimitExceeded:
        logger.error('⏱️  任務執行超時（軟限制）')
        # 清理資源
        self.request.chain = None
        raise
    except Exception as e:
        logger.error(f'❌ 任務執行失敗: {e}', exc_info=True)
        raise
```

### 1.3 Celery 並發控制

```python
# 文件：backend/network_toolbox/celery.py

from celery import Celery

app = Celery('network_toolbox')

# 🔒 Celery Worker 配置
app.conf.update(
    # 並發控制
    worker_concurrency=2,              # 🔒 最多 2 個並發任務（降低 CPU 負載）
    worker_prefetch_multiplier=1,      # 🔒 每次只預取 1 個任務
    worker_max_tasks_per_child=50,     # 🔒 每個 Worker 執行 50 個任務後重啟（防止記憶體洩漏）
    
    # 任務確認
    task_acks_late=True,               # 🔒 任務執行完才確認
    task_reject_on_worker_lost=True,   # 🔒 Worker 失聯時拒絕任務
    
    # 結果過期
    result_expires=3600,               # 🔒 結果 1 小時後過期
    
    # 任務優先級
    task_default_priority=5,           # 🔒 預設優先級（0-9，數字越小優先級越高）
)

# 🔒 不同任務的優先級
app.conf.task_routes = {
    'api.tasks.sync_jenkins_builds': {
        'queue': 'default',
        'priority': 5,  # 中等優先級
    },
    'api.tasks.sync_all_jenkins_jobs_task': {
        'queue': 'default',
        'priority': 3,  # 高優先級（更重要）
    },
}
```

---

## 🌐 層級 2：API 請求保護

### 2.1 速率限制器

```python
# 文件：backend/library/utils/rate_limiter.py

import time
import logging
from collections import deque
from threading import Lock

logger = logging.getLogger(__name__)


class RateLimiter:
    """API 請求速率限制器"""
    
    def __init__(self, max_requests: int = 10, time_window: int = 1):
        """
        初始化速率限制器
        
        Args:
            max_requests: 時間窗口內最多請求數
            time_window: 時間窗口（秒）
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self.lock = Lock()
    
    def wait_if_needed(self):
        """如果需要，等待直到可以發送請求"""
        with self.lock:
            now = time.time()
            
            # 移除過期的請求記錄
            while self.requests and self.requests[0] < now - self.time_window:
                self.requests.popleft()
            
            # 如果達到速率限制，等待
            if len(self.requests) >= self.max_requests:
                sleep_time = self.requests[0] + self.time_window - now
                if sleep_time > 0:
                    logger.debug(f'⏸️  速率限制：等待 {sleep_time:.2f} 秒')
                    time.sleep(sleep_time)
                    # 遞歸檢查（等待後可能仍需等待）
                    return self.wait_if_needed()
            
            # 記錄請求
            self.requests.append(now)
    
    def __enter__(self):
        """上下文管理器入口"""
        self.wait_if_needed()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        pass
```

### 2.2 改進的 JenkinsClient

```python
# 文件：backend/library/services/jenkins_client.py

import requests
import logging
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from library.utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class JenkinsClient:
    """Jenkins API 客戶端（帶保護機制）"""
    
    def __init__(self, base_url, username, api_token, 
                 rate_limit=10, timeout=30, max_retries=3):
        """
        初始化客戶端
        
        Args:
            base_url: Jenkins URL
            username: 使用者名稱
            api_token: API Token
            rate_limit: 每秒最多請求數（預設 10）
            timeout: 請求超時時間（秒，預設 30）
            max_retries: 最大重試次數（預設 3）
        """
        self.base_url = base_url.rstrip('/')
        self.auth = (username, api_token)
        self.timeout = timeout
        
        # 🔒 速率限制器
        self.rate_limiter = RateLimiter(max_requests=rate_limit, time_window=1)
        
        # 🔒 配置 Session（連接池 + 重試）
        self.session = requests.Session()
        
        # 連接池配置
        adapter = HTTPAdapter(
            pool_connections=5,      # 🔒 連接池大小
            pool_maxsize=10,         # 🔒 最大連接數
            max_retries=self._get_retry_strategy(max_retries)
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
    
    def _get_retry_strategy(self, max_retries):
        """
        配置重試策略（指數退避）
        
        🔒 保護機制：
        - 最多重試 N 次
        - 指數退避（0.5s, 1s, 2s, 4s...）
        - 只對特定錯誤碼重試
        """
        return Retry(
            total=max_retries,
            backoff_factor=0.5,  # 🔒 退避因子（每次等待時間倍增）
            status_forcelist=[429, 500, 502, 503, 504],  # 🔒 需要重試的狀態碼
            allowed_methods=['GET', 'POST'],
        )
    
    def _request(self, method, url, **kwargs):
        """
        發送請求（帶速率限制）
        
        🔒 保護機制：
        - 速率限制
        - 請求超時
        - 自動重試
        """
        # 速率限制
        with self.rate_limiter:
            try:
                # 設定超時
                kwargs.setdefault('timeout', self.timeout)
                kwargs.setdefault('auth', self.auth)
                
                # 發送請求
                response = self.session.request(method, url, **kwargs)
                response.raise_for_status()
                
                return response
            
            except requests.exceptions.Timeout:
                logger.error(f'⏱️  請求超時: {url}')
                raise
            except requests.exceptions.RequestException as e:
                logger.error(f'❌ 請求失敗: {url} - {e}')
                raise
    
    def get_all_jobs(self):
        """獲取所有 Jobs"""
        url = f"{self.base_url}/api/json"
        params = {'tree': 'jobs[name,url,color]'}
        
        response = self._request('GET', url, params=params)
        data = response.json()
        return data.get('jobs', [])
    
    def close(self):
        """關閉連接"""
        if self.session:
            self.session.close()
            logger.debug('🔌 Jenkins Client 連接已關閉')
```

---

## 💾 層級 3：資料處理保護

### 3.1 批次處理（避免一次載入過多資料）

```python
# 文件：backend/api/tasks.py

from django.db import connection
import gc  # 垃圾回收

@shared_task
@with_task_lock('sync_jenkins_builds')
def sync_jenkins_builds(self, server_id=None, batch_size=50, **kwargs):
    """
    同步 Jenkins Builds（批次處理）
    
    🔒 保護機制：
    - 分批處理 Jobs（每批 50 個）
    - 每批之間休息
    - 定期釋放記憶體
    """
    try:
        # 獲取所有 Jobs
        all_jobs = JenkinsJob.objects.filter(server__is_online=True)
        
        if server_id:
            all_jobs = all_jobs.filter(server_id=server_id)
        
        total_jobs = all_jobs.count()
        logger.info(f'📊 總共 {total_jobs} 個 Jobs 需要同步')
        
        # 🔒 分批處理
        for batch_start in range(0, total_jobs, batch_size):
            batch_end = min(batch_start + batch_size, total_jobs)
            batch_jobs = all_jobs[batch_start:batch_end]
            
            logger.info(f'🔄 處理批次 {batch_start}-{batch_end} ({len(batch_jobs)} 個 Jobs)')
            
            # 處理這一批 Jobs
            for job in batch_jobs:
                try:
                    _sync_single_job_builds(job, **kwargs)
                except Exception as e:
                    logger.error(f'❌ 同步 Job 失敗: {job.name} - {e}')
            
            # 🔒 批次間休息（降低 CPU 負載）
            if batch_end < total_jobs:
                rest_time = 2  # 休息 2 秒
                logger.debug(f'⏸️  批次完成，休息 {rest_time} 秒...')
                time.sleep(rest_time)
            
            # 🔒 強制垃圾回收（釋放記憶體）
            gc.collect()
            
            # 🔒 關閉空閒的資料庫連接
            connection.close_if_unusable_or_obsolete()
        
        logger.info('✅ 所有批次處理完成')
    
    except Exception as e:
        logger.error(f'❌ 批次處理失敗: {e}', exc_info=True)
        raise


def _sync_single_job_builds(job, **kwargs):
    """同步單個 Job 的 Builds（內部函數）"""
    # ... 同步邏輯 ...
    pass
```

### 3.2 資料量限制

```python
# 文件：backend/network_toolbox/settings.py

# 🔒 Jenkins 同步保護配置
JENKINS_SYNC_PROTECTION = {
    # 批次處理配置
    'batch_size': 50,                    # 每批處理的 Jobs 數量
    'batch_rest_seconds': 2,             # 批次間休息時間（秒）
    
    # 資料量限制
    'max_jobs_per_sync': 500,            # 單次同步最多處理的 Jobs 數量
    'max_builds_per_job': 100,           # 每個 Job 最多同步的 Builds 數量
    'max_builds_per_sync': 5000,         # 單次同步最多處理的 Builds 數量
    
    # API 請求限制
    'api_rate_limit': 10,                # 每秒最多 API 請求數
    'api_timeout': 30,                   # API 請求超時（秒）
    'api_max_retries': 3,                # API 請求最大重試次數
    
    # 記憶體監控
    'memory_threshold_mb': 1024,         # 記憶體使用閾值（MB）
    'memory_check_interval': 100,        # 每處理 N 個 Jobs 檢查一次記憶體
}
```

### 3.3 記憶體監控

```python
# 文件：backend/library/utils/resource_monitor.py

import psutil
import logging
import os

logger = logging.getLogger(__name__)


class ResourceMonitor:
    """系統資源監控器"""
    
    @staticmethod
    def get_memory_usage_mb():
        """獲取當前進程的記憶體使用量（MB）"""
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        return memory_info.rss / 1024 / 1024  # 轉換為 MB
    
    @staticmethod
    def get_cpu_percent():
        """獲取當前進程的 CPU 使用率"""
        process = psutil.Process(os.getpid())
        return process.cpu_percent(interval=1.0)
    
    @staticmethod
    def check_memory_threshold(threshold_mb: int = 1024) -> bool:
        """
        檢查記憶體使用是否超過閾值
        
        Args:
            threshold_mb: 記憶體閾值（MB）
            
        Returns:
            bool: 是否超過閾值
        """
        current_mb = ResourceMonitor.get_memory_usage_mb()
        
        if current_mb > threshold_mb:
            logger.warning(f'⚠️  記憶體使用超過閾值: {current_mb:.2f}MB > {threshold_mb}MB')
            return True
        
        return False
    
    @staticmethod
    def log_resource_usage():
        """記錄當前資源使用情況"""
        memory_mb = ResourceMonitor.get_memory_usage_mb()
        cpu_percent = ResourceMonitor.get_cpu_percent()
        
        logger.info(f'📊 資源使用: CPU {cpu_percent:.1f}% | 記憶體 {memory_mb:.2f}MB')


# 使用範例
def sync_jenkins_builds_with_monitoring(self):
    """帶資源監控的同步任務"""
    from django.conf import settings
    
    config = settings.JENKINS_SYNC_PROTECTION
    memory_threshold = config['memory_threshold_mb']
    check_interval = config['memory_check_interval']
    
    processed_count = 0
    
    for job in jobs:
        # 處理 Job
        _sync_single_job_builds(job)
        processed_count += 1
        
        # 🔒 定期檢查記憶體
        if processed_count % check_interval == 0:
            if ResourceMonitor.check_memory_threshold(memory_threshold):
                logger.warning('⚠️  記憶體使用過高，暫停同步並清理...')
                
                # 強制垃圾回收
                import gc
                gc.collect()
                
                # 再次檢查
                if ResourceMonitor.check_memory_threshold(memory_threshold):
                    logger.error('❌ 記憶體使用仍然過高，終止同步')
                    raise MemoryError('記憶體使用超過安全閾值')
                
                logger.info('✅ 記憶體清理完成，繼續同步')
            
            # 記錄資源使用
            ResourceMonitor.log_resource_usage()
```

---

## 🖥️ 層級 4：系統資源保護

### 4.1 自動降級機制

```python
# 文件：backend/api/tasks.py

from library.utils.resource_monitor import ResourceMonitor
from django.conf import settings

class AdaptiveSyncStrategy:
    """自適應同步策略（根據系統負載調整）"""
    
    @staticmethod
    def get_batch_size():
        """
        根據系統負載動態調整批次大小
        
        🔒 保護邏輯：
        - CPU < 50%：正常批次（50）
        - CPU 50-70%：減少批次（30）
        - CPU 70-90%：最小批次（10）
        - CPU > 90%：暫停同步
        """
        cpu_percent = ResourceMonitor.get_cpu_percent()
        
        if cpu_percent > 90:
            logger.warning(f'🚨 CPU 使用率過高: {cpu_percent:.1f}%，暫停同步')
            return 0  # 停止同步
        elif cpu_percent > 70:
            logger.warning(f'⚠️  CPU 使用率高: {cpu_percent:.1f}%，降級為最小批次')
            return 10  # 最小批次
        elif cpu_percent > 50:
            logger.info(f'📊 CPU 使用率中等: {cpu_percent:.1f}%，減少批次')
            return 30  # 減少批次
        else:
            return 50  # 正常批次
    
    @staticmethod
    def get_rest_time():
        """根據系統負載動態調整休息時間"""
        cpu_percent = ResourceMonitor.get_cpu_percent()
        
        if cpu_percent > 70:
            return 5  # CPU 高時，休息更久
        elif cpu_percent > 50:
            return 3
        else:
            return 2  # CPU 正常時，正常休息


@shared_task
@with_task_lock('sync_jenkins_builds')
def sync_jenkins_builds_adaptive(self, server_id=None, **kwargs):
    """
    自適應同步 Jenkins Builds
    
    🔒 保護機制：根據系統負載動態調整同步策略
    """
    total_processed = 0
    all_jobs = JenkinsJob.objects.filter(server__is_online=True)
    
    if server_id:
        all_jobs = all_jobs.filter(server_id=server_id)
    
    total_jobs = all_jobs.count()
    current_index = 0
    
    while current_index < total_jobs:
        # 🔒 動態獲取批次大小
        batch_size = AdaptiveSyncStrategy.get_batch_size()
        
        if batch_size == 0:
            logger.warning('⏸️  系統負載過高，暫停 30 秒後重試...')
            time.sleep(30)
            continue
        
        # 處理這一批
        batch_jobs = all_jobs[current_index:current_index + batch_size]
        
        for job in batch_jobs:
            try:
                _sync_single_job_builds(job, **kwargs)
                total_processed += 1
            except Exception as e:
                logger.error(f'❌ 同步失敗: {job.name} - {e}')
        
        current_index += batch_size
        
        # 🔒 動態休息時間
        rest_time = AdaptiveSyncStrategy.get_rest_time()
        if current_index < total_jobs:
            logger.debug(f'⏸️  批次完成，休息 {rest_time} 秒...')
            time.sleep(rest_time)
        
        # 記錄進度和資源使用
        progress = (current_index / total_jobs) * 100
        logger.info(f'📊 進度: {progress:.1f}% ({current_index}/{total_jobs})')
        ResourceMonitor.log_resource_usage()
    
    logger.info(f'✅ 同步完成，共處理 {total_processed} 個 Jobs')
```

### 4.2 資料庫連接池配置

```python
# 文件：backend/network_toolbox/settings.py

# 🔒 資料庫連接池配置
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'network_toolbox'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'host.docker.internal'),
        'PORT': os.getenv('DB_PORT', '5432'),
        
        # 🔒 連接池配置
        'CONN_MAX_AGE': 600,           # 連接最大存活時間（秒）
        'OPTIONS': {
            'connect_timeout': 10,      # 連接超時
            'options': '-c statement_timeout=60000'  # SQL 查詢超時（60秒）
        },
        
        # 🔒 連接池大小（需要安裝 django-db-pool）
        'POOL_OPTIONS': {
            'POOL_SIZE': 5,             # 連接池大小
            'MAX_OVERFLOW': 10,         # 最大溢出連接數
            'TIMEOUT': 30,              # 獲取連接超時
            'RECYCLE': 3600,            # 連接回收時間（1小時）
        }
    }
}
```

---

## 📊 監控和告警

### 監控指標

```python
# 文件：backend/library/utils/metrics.py

import logging
from django.core.cache import cache
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SyncMetrics:
    """同步任務監控指標"""
    
    @staticmethod
    def record_sync_start(task_name: str):
        """記錄同步開始"""
        key = f'sync_metrics:{task_name}:start_time'
        cache.set(key, datetime.now(), timeout=7200)
        logger.info(f'📊 {task_name} 開始執行')
    
    @staticmethod
    def record_sync_end(task_name: str, success: bool, **stats):
        """記錄同步結束"""
        start_key = f'sync_metrics:{task_name}:start_time'
        start_time = cache.get(start_key)
        
        if start_time:
            duration = (datetime.now() - start_time).total_seconds()
        else:
            duration = 0
        
        # 保存統計資訊
        metrics = {
            'task_name': task_name,
            'timestamp': datetime.now().isoformat(),
            'success': success,
            'duration_seconds': duration,
            'cpu_usage': ResourceMonitor.get_cpu_percent(),
            'memory_usage_mb': ResourceMonitor.get_memory_usage_mb(),
            **stats
        }
        
        # 保存到快取（保留 24 小時）
        history_key = f'sync_metrics:{task_name}:history'
        history = cache.get(history_key, [])
        history.append(metrics)
        
        # 只保留最近 20 次記錄
        if len(history) > 20:
            history = history[-20:]
        
        cache.set(history_key, history, timeout=86400)
        
        # 記錄日誌
        status = '✅ 成功' if success else '❌ 失敗'
        logger.info(f'📊 {task_name} {status} | 耗時: {duration:.2f}s | CPU: {metrics["cpu_usage"]:.1f}% | 記憶體: {metrics["memory_usage_mb"]:.2f}MB')
    
    @staticmethod
    def check_anomaly(task_name: str) -> dict:
        """
        檢查異常指標
        
        Returns:
            dict: {
                'has_anomaly': bool,
                'warnings': list,
                'metrics': dict
            }
        """
        history_key = f'sync_metrics:{task_name}:history'
        history = cache.get(history_key, [])
        
        if not history:
            return {'has_anomaly': False, 'warnings': [], 'metrics': {}}
        
        latest = history[-1]
        warnings = []
        
        # 檢查 CPU 使用率
        if latest['cpu_usage'] > 80:
            warnings.append(f'⚠️  CPU 使用率過高: {latest["cpu_usage"]:.1f}%')
        
        # 檢查記憶體使用
        if latest['memory_usage_mb'] > 1024:
            warnings.append(f'⚠️  記憶體使用過高: {latest["memory_usage_mb"]:.2f}MB')
        
        # 檢查執行時間
        if latest['duration_seconds'] > 1800:  # 30 分鐘
            warnings.append(f'⚠️  執行時間過長: {latest["duration_seconds"]:.2f}s')
        
        # 檢查失敗率
        recent_5 = history[-5:]
        failed_count = sum(1 for m in recent_5 if not m['success'])
        if failed_count >= 3:
            warnings.append(f'⚠️  最近 5 次中有 {failed_count} 次失敗')
        
        return {
            'has_anomaly': len(warnings) > 0,
            'warnings': warnings,
            'metrics': latest
        }
```

### 使用監控

```python
@shared_task
@with_task_lock('sync_jenkins_builds')
def sync_jenkins_builds_with_monitoring(self, **kwargs):
    """帶完整監控的同步任務"""
    task_name = 'sync_jenkins_builds'
    
    # 記錄開始
    SyncMetrics.record_sync_start(task_name)
    
    try:
        # 執行同步
        result = _do_sync(**kwargs)
        
        # 記錄成功
        SyncMetrics.record_sync_end(task_name, success=True, **result)
        
        # 檢查異常
        anomaly = SyncMetrics.check_anomaly(task_name)
        if anomaly['has_anomaly']:
            logger.warning(f'⚠️  檢測到異常指標:')
            for warning in anomaly['warnings']:
                logger.warning(f'  {warning}')
        
        return result
    
    except Exception as e:
        # 記錄失敗
        SyncMetrics.record_sync_end(task_name, success=False, error=str(e))
        raise
```

---

## 🎯 完整實施範例

### 最終的 sync_jenkins_builds 實現

```python
# 文件：backend/api/tasks.py

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from library.utils.task_lock import with_task_lock
from library.utils.resource_monitor import ResourceMonitor
from library.utils.metrics import SyncMetrics
from django.conf import settings
import logging
import time
import gc

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name='api.tasks.sync_jenkins_builds',
    max_retries=2,
    default_retry_delay=300,
    time_limit=3600,        # 🔒 硬限制：1 小時
    soft_time_limit=3300,   # 🔒 軟限制：55 分鐘
    acks_late=True,
    reject_on_worker_lost=True
)
@with_task_lock('sync_jenkins_builds', timeout=3600)  # 🔒 互斥鎖
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
    1. 任務互斥鎖（防止重複執行）
    2. 超時保護（軟限制 + 硬限制）
    3. 批次處理（降低記憶體使用）
    4. 速率限制（保護 Jenkins API）
    5. 資源監控（CPU + 記憶體）
    6. 自適應策略（根據負載調整）
    7. 異常檢測（及時發現問題）
    """
    task_name = 'sync_jenkins_builds'
    config = settings.JENKINS_SYNC_PROTECTION
    
    # 記錄開始
    SyncMetrics.record_sync_start(task_name)
    start_time = timezone.now()
    
    stats = {
        'total_jobs': 0,
        'total_builds': 0,
        'builds_created': 0,
        'builds_updated': 0,
        'builds_deleted': 0,
        'errors': 0,
    }
    
    try:
        logger.info(f'[Celery] 🔄 開始同步 Jenkins Builds')
        logger.info(f'[Celery]   - 模式: {"完整" if full_sync else "快速"}')
        logger.info(f'[Celery]   - 清理孤立: {"是" if cleanup_orphaned else "否"}')
        
        # 獲取所有 Jobs
        all_jobs = JenkinsJob.objects.filter(server__is_online=True)
        if server_id:
            all_jobs = all_jobs.filter(server_id=server_id)
        
        total_jobs = all_jobs.count()
        stats['total_jobs'] = total_jobs
        
        # 🔒 檢查 Jobs 數量限制
        if total_jobs > config['max_jobs_per_sync']:
            logger.warning(f'⚠️  Jobs 數量過多: {total_jobs} > {config["max_jobs_per_sync"]}')
            logger.warning(f'⚠️  將只處理前 {config["max_jobs_per_sync"]} 個')
            all_jobs = all_jobs[:config['max_jobs_per_sync']]
            total_jobs = config['max_jobs_per_sync']
        
        logger.info(f'[Celery] 📊 準備處理 {total_jobs} 個 Jobs')
        
        # 🔒 分批處理
        batch_size = config['batch_size']
        batch_rest = config['batch_rest_seconds']
        memory_threshold = config['memory_threshold_mb']
        check_interval = config['memory_check_interval']
        
        processed_count = 0
        
        for batch_start in range(0, total_jobs, batch_size):
            try:
                # 🔒 檢查軟超時
                if self.request.called_directly:
                    pass  # 直接調用時不檢查
                else:
                    # Celery 任務中檢查剩餘時間
                    pass
                
                # 🔒 自適應批次大小
                current_batch_size = AdaptiveSyncStrategy.get_batch_size()
                if current_batch_size == 0:
                    logger.warning('⏸️  CPU 負載過高，暫停 30 秒...')
                    time.sleep(30)
                    continue
                
                batch_size = min(batch_size, current_batch_size)
                
                batch_end = min(batch_start + batch_size, total_jobs)
                batch_jobs = all_jobs[batch_start:batch_end]
                
                logger.info(f'[Celery] 🔄 批次 {batch_start}-{batch_end} ({len(batch_jobs)} Jobs)')
                
                # 處理這一批
                for job in batch_jobs:
                    try:
                        # 創建 Jenkins Client（帶速率限制）
                        client = JenkinsClient(
                            base_url=job.server.url,
                            username=job.server.username,
                            api_token=job.server.api_token,
                            rate_limit=config['api_rate_limit'],
                            timeout=config['api_timeout'],
                            max_retries=config['api_max_retries']
                        )
                        
                        # 同步這個 Job 的 Builds
                        job_stats = _sync_single_job_builds(
                            job, client, full_sync, cleanup_orphaned,
                            max_builds_per_job, max_age_days
                        )
                        
                        # 累計統計
                        stats['builds_created'] += job_stats.get('created', 0)
                        stats['builds_updated'] += job_stats.get('updated', 0)
                        stats['builds_deleted'] += job_stats.get('deleted', 0)
                        
                        client.close()
                        processed_count += 1
                    
                    except Exception as e:
                        stats['errors'] += 1
                        logger.error(f'[Celery] ❌ Job 同步失敗: {job.name} - {e}')
                
                # 🔒 批次間休息
                if batch_end < total_jobs:
                    rest_time = AdaptiveSyncStrategy.get_rest_time()
                    logger.debug(f'[Celery] ⏸️  休息 {rest_time} 秒...')
                    time.sleep(rest_time)
                
                # 🔒 定期檢查記憶體
                if processed_count % check_interval == 0:
                    if ResourceMonitor.check_memory_threshold(memory_threshold):
                        logger.warning('[Celery] ⚠️  記憶體使用過高，執行清理...')
                        gc.collect()
                        
                        if ResourceMonitor.check_memory_threshold(memory_threshold):
                            raise MemoryError('記憶體使用超過安全閾值')
                    
                    ResourceMonitor.log_resource_usage()
                
                # 🔒 強制垃圾回收
                gc.collect()
            
            except SoftTimeLimitExceeded:
                logger.error('[Celery] ⏱️  任務執行超時（軟限制）')
                stats['errors'] += 1
                break
        
        # 最終統計
        duration = (timezone.now() - start_time).total_seconds()
        stats['duration'] = duration
        
        logger.info('[Celery] ✅ 同步完成')
        logger.info(f'[Celery]   - 處理 Jobs: {processed_count}/{total_jobs}')
        logger.info(f'[Celery]   - 創建 Builds: {stats["builds_created"]}')
        logger.info(f'[Celery]   - 更新 Builds: {stats["builds_updated"]}')
        logger.info(f'[Celery]   - 刪除 Builds: {stats["builds_deleted"]}')
        logger.info(f'[Celery]   - 錯誤數: {stats["errors"]}')
        logger.info(f'[Celery]   - 耗時: {duration:.2f} 秒')
        
        # 記錄成功
        SyncMetrics.record_sync_end(task_name, success=True, **stats)
        
        # 檢查異常
        anomaly = SyncMetrics.check_anomaly(task_name)
        if anomaly['has_anomaly']:
            for warning in anomaly['warnings']:
                logger.warning(f'[Celery] {warning}')
        
        return {
            'success': True,
            **stats
        }
    
    except Exception as e:
        duration = (timezone.now() - start_time).total_seconds()
        stats['duration'] = duration
        
        logger.error(f'[Celery] ❌ 同步失敗: {e}', exc_info=True)
        
        # 記錄失敗
        SyncMetrics.record_sync_end(task_name, success=False, **stats, error=str(e))
        
        return {
            'success': False,
            'error': str(e),
            **stats
        }


def _sync_single_job_builds(job, client, full_sync, cleanup_orphaned, 
                            max_builds_per_job, max_age_days):
    """同步單個 Job 的 Builds（內部函數）"""
    # ... 實際同步邏輯 ...
    return {
        'created': 0,
        'updated': 0,
        'deleted': 0,
    }
```

---

## 📝 部署檢查清單

### 部署前

- [ ] 安裝依賴：`psutil`（系統資源監控）
- [ ] 配置 `JENKINS_SYNC_PROTECTION` 設定
- [ ] 配置 Celery Worker 並發數（建議 2-4）
- [ ] 測試任務鎖機制
- [ ] 測試速率限制器
- [ ] 測試資源監控

### 部署後

- [ ] 監控第一次執行的資源使用
- [ ] 檢查 CPU 使用率是否正常（< 70%）
- [ ] 檢查記憶體使用是否正常（< 1GB）
- [ ] 驗證任務不會重複執行
- [ ] 驗證異常檢測是否正常

### 持續監控

- [ ] 每天檢查 `sync_metrics` 快取
- [ ] 每週分析執行日誌
- [ ] 發現異常立即調整參數

---

## 🎯 總結

### 保護機制清單

| 層級 | 保護機制 | 作用 | 實施位置 |
|------|---------|------|---------|
| **任務調度** | 互斥鎖 | 防止重複執行 | `@with_task_lock` |
| | 超時保護 | 防止任務卡死 | `time_limit`, `soft_time_limit` |
| | 並發控制 | 限制同時執行 | `worker_concurrency=2` |
| **API 請求** | 速率限制 | 保護 Jenkins | `RateLimiter` |
| | 連接池 | 複用連接 | `HTTPAdapter` |
| | 指數退避 | 智能重試 | `Retry` |
| **資料處理** | 批次處理 | 分批載入 | `batch_size=50` |
| | 記憶體監控 | 防止溢出 | `ResourceMonitor` |
| | 垃圾回收 | 釋放記憶體 | `gc.collect()` |
| **系統資源** | 自適應策略 | 動態調整 | `AdaptiveSyncStrategy` |
| | 資源監控 | 即時追蹤 | `psutil` |
| | 異常檢測 | 及時發現 | `SyncMetrics` |

### 關鍵參數建議

```python
# 小型專案
SMALL_PROJECT = {
    'worker_concurrency': 2,
    'batch_size': 50,
    'api_rate_limit': 10,
    'memory_threshold_mb': 512,
}

# 中型專案（推薦）
MEDIUM_PROJECT = {
    'worker_concurrency': 2,
    'batch_size': 50,
    'api_rate_limit': 10,
    'memory_threshold_mb': 1024,
}

# 大型專案
LARGE_PROJECT = {
    'worker_concurrency': 1,  # 更保守
    'batch_size': 30,         # 更小批次
    'api_rate_limit': 5,      # 更慢速率
    'memory_threshold_mb': 1024,
}
```

---

**最後更新**：2025-11-21  
**維護者**：Network Toolbox Team  
**狀態**：詳細設計完成，待實施
