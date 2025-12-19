"""
CPU 保護裝飾器

為 Celery 任務提供 CPU 使用率保護機制
當 CPU 過高時等待，等待過久時直接跳過任務

使用方式：
    from library.utils.cpu_protection import cpu_protected_task
    
    @shared_task(bind=True)
    @cpu_protected_task(high_threshold=70.0, max_wait=180, skip_on_timeout=True)
    def my_heavy_task(self):
        # 任務邏輯
        pass
"""
import psutil
import logging
import time
from functools import wraps
from typing import Callable, Any, Dict, Optional
from dataclasses import dataclass, field
from threading import Lock

logger = logging.getLogger(__name__)


# ============================================================================
# 全局配置類
# ============================================================================

@dataclass
class CPUProtectionConfig:
    """
    CPU 保護全局配置
    
    可以在應用程式啟動時修改這些默認值
    
    Example:
        from library.utils.cpu_protection import CPUProtectionConfig
        
        # 修改全局默認值
        CPUProtectionConfig.HIGH_THRESHOLD = 75.0
        CPUProtectionConfig.LOW_THRESHOLD = 55.0
    """
    HIGH_THRESHOLD: float = 70.0      # 高負載閾值
    LOW_THRESHOLD: float = 50.0       # 恢復閾值
    MAX_WAIT_TIME: int = 180          # 最長等待時間（秒）
    CHECK_INTERVAL: int = 10          # 檢查間隔（秒）
    SKIP_ON_TIMEOUT: bool = True      # 超時後是否跳過


# ============================================================================
# 統計追蹤
# ============================================================================

class _CPUProtectionStats:
    """CPU 保護統計追蹤器（單例）"""
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init_stats()
        return cls._instance
    
    def _init_stats(self):
        self.total_tasks = 0
        self.executed_immediately = 0
        self.executed_after_wait = 0
        self.skipped = 0
        self.total_wait_time = 0.0
        self._stats_lock = Lock()
    
    def record_immediate_execution(self):
        with self._stats_lock:
            self.total_tasks += 1
            self.executed_immediately += 1
    
    def record_execution_after_wait(self, wait_time: float):
        with self._stats_lock:
            self.total_tasks += 1
            self.executed_after_wait += 1
            self.total_wait_time += wait_time
    
    def record_skip(self, wait_time: float):
        with self._stats_lock:
            self.total_tasks += 1
            self.skipped += 1
            self.total_wait_time += wait_time
    
    def get_stats(self) -> Dict[str, Any]:
        with self._stats_lock:
            waited_count = self.executed_after_wait + self.skipped
            avg_wait = self.total_wait_time / waited_count if waited_count > 0 else 0
            
            return {
                'total_tasks': self.total_tasks,
                'executed_immediately': self.executed_immediately,
                'executed_after_wait': self.executed_after_wait,
                'skipped': self.skipped,
                'total_wait_time': round(self.total_wait_time, 1),
                'average_wait_time': round(avg_wait, 1),
                'skip_rate': round(self.skipped / self.total_tasks * 100, 1) if self.total_tasks > 0 else 0
            }
    
    def reset(self):
        with self._stats_lock:
            self._init_stats()


# 全局統計實例
_stats = _CPUProtectionStats()


def get_cpu_protection_stats() -> Dict[str, Any]:
    """
    獲取 CPU 保護統計數據
    
    Returns:
        dict: {
            'total_tasks': int,           # 總任務數
            'executed_immediately': int,  # 直接執行的任務數
            'executed_after_wait': int,   # 等待後執行的任務數
            'skipped': int,               # 跳過的任務數
            'total_wait_time': float,     # 總等待時間（秒）
            'average_wait_time': float,   # 平均等待時間（秒）
            'skip_rate': float            # 跳過率（%）
        }
    
    Example:
        stats = get_cpu_protection_stats()
        print(f"跳過率: {stats['skip_rate']}%")
    """
    return _stats.get_stats()


# ============================================================================
# 主要裝飾器
# ============================================================================


def cpu_protected_task(
    high_threshold: float = 70.0,
    low_threshold: float = 50.0,
    max_wait: int = 180,
    check_interval: int = 10,
    skip_on_timeout: bool = True
):
    """
    CPU 保護裝飾器
    
    當 CPU 使用率超過閾值時，延遲執行任務。
    如果等待超時，根據 skip_on_timeout 決定是否跳過任務。
    
    這個機制可以有效防止：
    1. CPU 持續過載導致系統不穩定
    2. 任務堆積導致的惡性循環（超時的任務會被跳過）
    
    Args:
        high_threshold: CPU 高負載閾值（%），超過此值會等待
        low_threshold: CPU 恢復閾值（%），降到此值以下才繼續
        max_wait: 最長等待時間（秒），預設 3 分鐘
        check_interval: 檢查間隔（秒）
        skip_on_timeout: 超時後是否跳過任務（True=跳過，False=強制執行）
    
    Returns:
        裝飾後的函數
    
    Example:
        @shared_task(bind=True)
        @cpu_protected_task(high_threshold=70.0, max_wait=180, skip_on_timeout=True)
        def sync_jenkins_builds(self, ...):
            # 如果 CPU > 70%，最多等 3 分鐘
            # 超過 3 分鐘還是高，就跳過這次執行
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            task_name = func.__name__
            start_time = time.time()
            
            # 初始 CPU 檢查（快速檢查，只取 0.5 秒樣本）
            initial_cpu = psutil.cpu_percent(interval=0.5)
            
            if initial_cpu < high_threshold:
                # CPU 正常，直接執行
                logger.debug(
                    f'[CPU] ✅ {task_name} CPU 正常 ({initial_cpu:.1f}%)，直接執行'
                )
                _stats.record_immediate_execution()
                return func(*args, **kwargs)
            
            # CPU 過高，進入等待循環
            logger.warning(
                f'[CPU] ⚠️  {task_name} CPU 過高 ({initial_cpu:.1f}% > {high_threshold}%)，'
                f'開始等待... (最長 {max_wait}s，超時後{"跳過" if skip_on_timeout else "強制執行"})'
            )
            
            wait_count = 0
            while True:
                elapsed = time.time() - start_time
                
                # 檢查是否超時
                if elapsed >= max_wait:
                    final_cpu = psutil.cpu_percent(interval=0.1)
                    
                    if skip_on_timeout:
                        logger.warning(
                            f'[CPU] ⏭️  {task_name} 等待超時 ({elapsed:.0f}s)，'
                            f'跳過此次執行 (CPU: {final_cpu:.1f}%)'
                        )
                        _stats.record_skip(elapsed)
                        # 返回跳過狀態，讓調用者知道任務被跳過了
                        return {
                            'status': 'skipped',
                            'reason': 'cpu_protection_timeout',
                            'task_name': task_name,
                            'waited_seconds': round(elapsed, 1),
                            'cpu_percent': final_cpu,
                            'threshold': high_threshold
                        }
                    else:
                        logger.warning(
                            f'[CPU] ⚡ {task_name} 等待超時 ({elapsed:.0f}s)，'
                            f'強制執行 (CPU: {final_cpu:.1f}%)'
                        )
                        _stats.record_execution_after_wait(elapsed)
                        break
                
                # 等待一段時間
                time.sleep(check_interval)
                wait_count += 1
                
                # 重新檢查 CPU
                current_cpu = psutil.cpu_percent(interval=0.5)
                
                if current_cpu < low_threshold:
                    # CPU 已降低到安全閾值以下
                    logger.info(
                        f'[CPU] ✅ {task_name} CPU 已降低 ({current_cpu:.1f}% < {low_threshold}%)，'
                        f'等待 {elapsed:.0f}s 後開始執行'
                    )
                    _stats.record_execution_after_wait(elapsed)
                    break
                elif current_cpu < high_threshold:
                    # CPU 低於高閾值，可以執行
                    logger.info(
                        f'[CPU] ✅ {task_name} CPU 可接受 ({current_cpu:.1f}%)，'
                        f'等待 {elapsed:.0f}s 後開始執行'
                    )
                    _stats.record_execution_after_wait(elapsed)
                    break
                else:
                    # 繼續等待
                    remaining = max_wait - elapsed
                    if wait_count % 3 == 0:  # 每 3 次檢查輸出一次日誌
                        logger.info(
                            f'[CPU] ⏳ {task_name} 仍在等待... '
                            f'CPU: {current_cpu:.1f}%, 剩餘: {remaining:.0f}s'
                        )
            
            # 執行任務
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def check_cpu_before_task(
    threshold: float = 80.0,
    task_name: str = "unknown"
) -> Dict[str, Any]:
    """
    在任務開始前檢查 CPU（非裝飾器版本）
    
    適用於在任務內部進行 CPU 檢查，決定是否繼續執行
    
    Args:
        threshold: CPU 閾值（%）
        task_name: 任務名稱（用於日誌）
    
    Returns:
        dict: {
            'should_skip': bool,  # True 表示應該跳過
            'cpu_percent': float,
            'threshold': float
        }
    
    Example:
        def my_task():
            check = check_cpu_before_task(threshold=80.0, task_name="my_task")
            if check['should_skip']:
                return {'status': 'skipped', **check}
            # 繼續執行任務邏輯
    """
    cpu = psutil.cpu_percent(interval=0.5)
    should_skip = cpu >= threshold
    
    if should_skip:
        logger.warning(
            f'[CPU] ⚠️  {task_name} CPU 過高 ({cpu:.1f}% >= {threshold}%)，建議跳過'
        )
    else:
        logger.debug(
            f'[CPU] ✅ {task_name} CPU 正常 ({cpu:.1f}% < {threshold}%)'
        )
    
    return {
        'should_skip': should_skip,
        'cpu_percent': cpu,
        'threshold': threshold
    }


class TaskCPUGuard:
    """
    任務 CPU 守衛類別
    
    提供更細緻的 CPU 監控功能，適用於需要在任務執行過程中
    多次檢查 CPU 狀態的場景（例如批次處理）
    
    Example:
        guard = TaskCPUGuard(high_threshold=70.0, max_wait=60)
        
        for item in large_dataset:
            # 每次處理前檢查 CPU
            if guard.should_wait():
                if not guard.wait_for_cpu_drop():
                    # 超時，決定是否繼續
                    break
            
            process(item)
            
            # 每 10 個項目主動讓出 CPU
            if guard.items_processed % 10 == 0:
                guard.yield_cpu(seconds=0.5)
    """
    
    def __init__(
        self,
        high_threshold: float = 70.0,
        low_threshold: float = 50.0,
        max_wait: int = 60,
        check_interval: int = 5
    ):
        self.high_threshold = high_threshold
        self.low_threshold = low_threshold
        self.max_wait = max_wait
        self.check_interval = check_interval
        self._last_check_time = 0
        self._check_cooldown = 2  # 最小檢查間隔（秒）
        self.items_processed = 0
    
    def get_cpu_percent(self) -> float:
        """獲取當前 CPU 使用率"""
        return psutil.cpu_percent(interval=0.5)
    
    def should_wait(self) -> bool:
        """
        檢查是否應該等待
        
        包含冷卻時間，避免過於頻繁的檢查
        """
        current_time = time.time()
        
        # 冷卻時間內不重複檢查
        if current_time - self._last_check_time < self._check_cooldown:
            return False
        
        self._last_check_time = current_time
        cpu = self.get_cpu_percent()
        
        return cpu >= self.high_threshold
    
    def wait_for_cpu_drop(self, task_name: str = "task") -> bool:
        """
        等待 CPU 降低
        
        Args:
            task_name: 任務名稱（用於日誌）
        
        Returns:
            bool: True 表示 CPU 已降低，False 表示超時
        """
        start_time = time.time()
        
        logger.info(
            f'[CPU] ⏳ {task_name} 暫停執行，等待 CPU 降低 '
            f'(目標: < {self.low_threshold}%，最長: {self.max_wait}s)...'
        )
        
        while True:
            elapsed = time.time() - start_time
            
            if elapsed >= self.max_wait:
                logger.warning(
                    f'[CPU] ⏰ {task_name} 等待超時 ({elapsed:.0f}s)'
                )
                return False
            
            time.sleep(self.check_interval)
            cpu = self.get_cpu_percent()
            
            if cpu < self.low_threshold:
                logger.info(
                    f'[CPU] ✅ {task_name} CPU 已降低 ({cpu:.1f}%)，繼續執行'
                )
                return True
    
    def yield_cpu(self, seconds: float = 0.1):
        """
        主動讓出 CPU（短暫休眠）
        
        在批次處理中定期調用，避免長時間佔用 CPU
        """
        time.sleep(seconds)
        self.items_processed += 1
