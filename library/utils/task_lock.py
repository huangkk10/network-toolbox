"""
任務鎖工具 - 防止任務重複執行

使用 Django cache 實現分散式鎖機制
"""
import logging
from django.core.cache import cache
from functools import wraps
from typing import Optional, Callable, Any, Dict

logger = logging.getLogger(__name__)


class TaskLock:
    """任務鎖類別 - 防止任務重複執行"""
    
    @staticmethod
    def acquire(lock_name: str, timeout: int = 3600, wait: bool = False) -> bool:
        """
        獲取任務鎖
        
        Args:
            lock_name: 鎖名稱
            timeout: 鎖超時時間（秒），預設 1 小時
            wait: 是否等待鎖釋放（暫不實作）
            
        Returns:
            bool: 是否成功獲取鎖
        """
        cache_key = f'task_lock:{lock_name}'
        
        # 嘗試設置鎖（nx=True 表示只在不存在時設置）
        success = cache.add(cache_key, True, timeout)
        
        if success:
            logger.info(f'✅ 成功獲取任務鎖: {lock_name}')
        else:
            logger.warning(f'⚠️  任務鎖已存在，跳過執行: {lock_name}')
            
        return success
    
    @staticmethod
    def release(lock_name: str) -> bool:
        """
        釋放任務鎖
        
        Args:
            lock_name: 鎖名稱
            
        Returns:
            bool: 是否成功釋放
        """
        cache_key = f'task_lock:{lock_name}'
        cache.delete(cache_key)
        logger.info(f'🔓 釋放任務鎖: {lock_name}')
        return True
    
    @staticmethod
    def is_locked(lock_name: str) -> bool:
        """
        檢查任務鎖是否存在
        
        Args:
            lock_name: 鎖名稱
            
        Returns:
            bool: 鎖是否存在
        """
        cache_key = f'task_lock:{lock_name}'
        return cache.get(cache_key) is not None


def with_task_lock(lock_name: str, timeout: int = 3600) -> Callable:
    """
    任務鎖裝飾器 - 自動獲取和釋放鎖
    
    Args:
        lock_name: 鎖名稱
        timeout: 鎖超時時間（秒）
        
    Returns:
        裝飾器函數
        
    Example:
        @with_task_lock('sync_jenkins_builds', timeout=3600)
        def sync_task():
            # 任務邏輯
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Dict[str, Any]:
            # 嘗試獲取鎖
            if not TaskLock.acquire(lock_name, timeout):
                return {
                    'success': False,
                    'skipped': True,
                    'message': f'任務已在執行中: {lock_name}'
                }
            
            try:
                # 執行任務
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                logger.error(f'任務執行失敗: {lock_name}', exc_info=True)
                raise
            finally:
                # 釋放鎖
                TaskLock.release(lock_name)
        
        return wrapper
    return decorator
