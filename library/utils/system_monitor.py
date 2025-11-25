"""
系統資源監控工具

提供 CPU、記憶體、I/O 使用率的即時監控功能，
用於智能調節任務執行策略，避免系統過載。

作者：Network Toolbox Team
創建時間：2025-11-25
"""

import psutil
import time
import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """系統指標數據類別"""
    cpu_percent: float              # CPU 使用率 (%)
    memory_percent: float           # 記憶體使用率 (%)
    disk_io_read_mb: float         # 磁盤讀取速率 (MB/s)
    disk_io_write_mb: float        # 磁盤寫入速率 (MB/s)
    timestamp: datetime            # 採集時間
    
    def __str__(self):
        return (
            f"CPU: {self.cpu_percent:.1f}%, "
            f"Memory: {self.memory_percent:.1f}%, "
            f"Disk R/W: {self.disk_io_read_mb:.1f}/{self.disk_io_write_mb:.1f} MB/s"
        )
    
    def is_high_load(self, cpu_threshold: float = 85.0) -> bool:
        """判斷系統是否處於高負載狀態"""
        return self.cpu_percent > cpu_threshold
    
    def is_low_load(self, cpu_threshold: float = 60.0) -> bool:
        """判斷系統是否處於低負載狀態"""
        return self.cpu_percent < cpu_threshold


class SystemMonitor:
    """系統資源監控器"""
    
    def __init__(self, sample_interval: float = 1.0):
        """
        初始化系統監控器
        
        Args:
            sample_interval: 採樣間隔（秒）
        """
        self.sample_interval = sample_interval
        self._last_disk_io = None
        self._last_disk_io_time = None
        
    def get_current_metrics(self) -> SystemMetrics:
        """
        獲取當前系統指標
        
        Returns:
            SystemMetrics: 系統指標數據
        """
        # CPU 使用率（取樣間隔 1 秒）
        cpu_percent = psutil.cpu_percent(interval=self.sample_interval)
        
        # 記憶體使用率
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # 磁盤 I/O 速率
        disk_io_read_mb, disk_io_write_mb = self._get_disk_io_rate()
        
        metrics = SystemMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            disk_io_read_mb=disk_io_read_mb,
            disk_io_write_mb=disk_io_write_mb,
            timestamp=datetime.now()
        )
        
        logger.debug(f'系統指標: {metrics}')
        return metrics
    
    def _get_disk_io_rate(self) -> Tuple[float, float]:
        """
        計算磁盤 I/O 速率（MB/s）
        
        Returns:
            (read_mb_per_sec, write_mb_per_sec)
        """
        current_io = psutil.disk_io_counters()
        current_time = time.time()
        
        if self._last_disk_io is None:
            self._last_disk_io = current_io
            self._last_disk_io_time = current_time
            return 0.0, 0.0
        
        # 計算速率
        time_delta = current_time - self._last_disk_io_time
        if time_delta == 0:
            return 0.0, 0.0
        
        read_bytes = current_io.read_bytes - self._last_disk_io.read_bytes
        write_bytes = current_io.write_bytes - self._last_disk_io.write_bytes
        
        read_mb_per_sec = (read_bytes / time_delta) / (1024 * 1024)
        write_mb_per_sec = (write_bytes / time_delta) / (1024 * 1024)
        
        # 更新記錄
        self._last_disk_io = current_io
        self._last_disk_io_time = current_time
        
        return read_mb_per_sec, write_mb_per_sec
    
    def monitor_until_low_load(
        self,
        cpu_threshold: float = 85.0,
        max_wait_seconds: int = 300,
        check_interval: int = 5
    ) -> bool:
        """
        監控系統負載直到降至閾值以下
        
        Args:
            cpu_threshold: CPU 閾值 (%)
            max_wait_seconds: 最大等待時間（秒）
            check_interval: 檢查間隔（秒）
            
        Returns:
            bool: True 表示負載已降低，False 表示超時
        """
        start_time = time.time()
        
        logger.info(f'開始監控系統負載，目標 CPU < {cpu_threshold}%，最大等待 {max_wait_seconds} 秒')
        
        while True:
            metrics = self.get_current_metrics()
            
            if metrics.cpu_percent < cpu_threshold:
                logger.info(f'系統負載已降低: {metrics}')
                return True
            
            # 檢查是否超時
            elapsed = time.time() - start_time
            if elapsed > max_wait_seconds:
                logger.warning(f'等待系統負載降低超時（{max_wait_seconds} 秒），當前 CPU: {metrics.cpu_percent:.1f}%')
                return False
            
            logger.debug(f'系統負載仍高: {metrics}，等待 {check_interval} 秒後重試...')
            time.sleep(check_interval)


class AdaptiveBatchController:
    """自適應批次控制器"""
    
    def __init__(
        self,
        min_batch_size: int = 1,
        max_batch_size: int = 10,
        target_cpu: float = 70.0,
        low_cpu_threshold: float = 60.0,
        high_cpu_threshold: float = 85.0
    ):
        """
        初始化自適應批次控制器
        
        Args:
            min_batch_size: 最小批次大小
            max_batch_size: 最大批次大小
            target_cpu: 目標 CPU 使用率 (%)
            low_cpu_threshold: 低負載 CPU 閾值 (%)
            high_cpu_threshold: 高負載 CPU 閾值 (%)
        """
        self.min_batch_size = min_batch_size
        self.max_batch_size = max_batch_size
        self.target_cpu = target_cpu
        self.low_cpu_threshold = low_cpu_threshold
        self.high_cpu_threshold = high_cpu_threshold
        
        self.current_batch_size = min_batch_size
        self.monitor = SystemMonitor()
        
    def adjust_batch_size(self) -> int:
        """
        根據當前系統負載動態調整批次大小
        
        Returns:
            int: 調整後的批次大小
        """
        metrics = self.monitor.get_current_metrics()
        cpu = metrics.cpu_percent
        
        # 高負載：減少批次大小
        if cpu > self.high_cpu_threshold:
            self.current_batch_size = max(
                self.min_batch_size,
                self.current_batch_size - 1
            )
            logger.info(
                f'⚠️  系統高負載 (CPU: {cpu:.1f}%)，'
                f'減少批次大小: {self.current_batch_size + 1} → {self.current_batch_size}'
            )
        
        # 低負載：增加批次大小
        elif cpu < self.low_cpu_threshold:
            self.current_batch_size = min(
                self.max_batch_size,
                self.current_batch_size + 1
            )
            logger.info(
                f'✅ 系統低負載 (CPU: {cpu:.1f}%)，'
                f'增加批次大小: {self.current_batch_size - 1} → {self.current_batch_size}'
            )
        
        # 中等負載：維持批次大小
        else:
            logger.debug(
                f'系統負載適中 (CPU: {cpu:.1f}%)，'
                f'維持批次大小: {self.current_batch_size}'
            )
        
        return self.current_batch_size
    
    def should_pause(self) -> bool:
        """
        判斷是否應該暫停處理（系統過載）
        
        Returns:
            bool: True 表示應該暫停
        """
        metrics = self.monitor.get_current_metrics()
        
        if metrics.cpu_percent > self.high_cpu_threshold:
            logger.warning(
                f'🛑 系統過載 (CPU: {metrics.cpu_percent:.1f}% > {self.high_cpu_threshold}%)，'
                f'建議暫停處理'
            )
            return True
        
        return False
    
    def get_wait_time(self) -> int:
        """
        根據系統負載計算等待時間（秒）
        
        Returns:
            int: 等待時間（秒）
        """
        metrics = self.monitor.get_current_metrics()
        cpu = metrics.cpu_percent
        
        # CPU 使用率越高，等待時間越長
        if cpu > 90:
            return 10
        elif cpu > 85:
            return 5
        elif cpu > 80:
            return 3
        elif cpu > 75:
            return 2
        else:
            return 1


# 示例使用
if __name__ == '__main__':
    # 配置日誌
    logging.basicConfig(
        level=logging.INFO,
        format='[%(levelname)s] %(asctime)s - %(message)s'
    )
    
    print('=' * 70)
    print('系統監控工具測試')
    print('=' * 70)
    print()
    
    # 測試系統監控
    monitor = SystemMonitor()
    print('1. 獲取當前系統指標：')
    metrics = monitor.get_current_metrics()
    print(f'   {metrics}')
    print()
    
    # 測試批次控制器
    controller = AdaptiveBatchController(
        min_batch_size=1,
        max_batch_size=10,
        target_cpu=70.0
    )
    print('2. 自適應批次控制：')
    for i in range(3):
        batch_size = controller.adjust_batch_size()
        print(f'   批次 {i+1}: 大小 = {batch_size}')
        time.sleep(1)
    print()
    
    # 測試暫停判斷
    print('3. 暫停判斷：')
    should_pause = controller.should_pause()
    print(f'   應該暫停: {should_pause}')
    print()
    
    # 測試等待時間計算
    print('4. 等待時間計算：')
    wait_time = controller.get_wait_time()
    print(f'   建議等待: {wait_time} 秒')
    print()
    
    print('=' * 70)
    print('測試完成！')
    print('=' * 70)
