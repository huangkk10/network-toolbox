"""
Redis 緩存裝飾器

提供通用的緩存裝飾器，用於函數和方法的結果緩存。
支援自動生成緩存鍵、TTL 配置、緩存失效等功能。
"""

import functools
import hashlib
import logging
from typing import Any, Callable, Optional, Union
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


def _generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """
    生成緩存鍵
    
    Args:
        prefix: 緩存鍵前綴
        *args: 位置參數
        **kwargs: 關鍵字參數
        
    Returns:
        str: 緩存鍵
    """
    # 將參數轉換為可序列化的字串
    key_parts = [prefix]
    
    # 添加位置參數
    for arg in args:
        if hasattr(arg, 'id'):  # Django 模型實例
            key_parts.append(f"{arg.__class__.__name__}:{arg.id}")
        else:
            key_parts.append(str(arg))
    
    # 添加關鍵字參數（排序以確保一致性）
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}:{v}")
    
    # 生成緩存鍵
    key_string = ":".join(key_parts)
    
    # 如果太長，使用 MD5 雜湊
    if len(key_string) > 200:
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        return f"{prefix}:{key_hash}"
    
    return key_string


def cached(
    ttl: Optional[int] = None,
    prefix: Optional[str] = None,
    key_builder: Optional[Callable] = None
):
    """
    通用緩存裝飾器
    
    使用範例：
        @cached(ttl=3600, prefix='user')
        def get_user_data(user_id):
            return expensive_query(user_id)
    
    Args:
        ttl: 緩存過期時間（秒），None 表示永不過期
        prefix: 緩存鍵前綴（默認使用函數名）
        key_builder: 自訂緩存鍵生成函數
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 生成緩存鍵
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                key_prefix = prefix or f"{func.__module__}.{func.__name__}"
                cache_key = _generate_cache_key(key_prefix, *args, **kwargs)
            
            # 嘗試從緩存讀取
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"緩存命中: {cache_key}")
                return cached_result
            
            # 執行函數
            logger.debug(f"緩存未命中，執行函數: {cache_key}")
            result = func(*args, **kwargs)
            
            # 儲存到緩存
            cache.set(cache_key, result, ttl)
            logger.debug(f"結果已緩存: {cache_key}, TTL={ttl}s")
            
            return result
        
        # 添加清除緩存的方法
        def clear_cache(*args, **kwargs):
            """清除特定參數的緩存"""
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                key_prefix = prefix or f"{func.__module__}.{func.__name__}"
                cache_key = _generate_cache_key(key_prefix, *args, **kwargs)
            cache.delete(cache_key)
            logger.info(f"已清除緩存: {cache_key}")
        
        wrapper.clear_cache = clear_cache
        return wrapper
    
    return decorator


def cache_result(ttl: int = 3600, prefix: Optional[str] = None):
    """
    簡化版緩存裝飾器（常用配置）
    
    使用範例：
        @cache_result(ttl=1800)
        def get_expensive_data():
            return expensive_computation()
    
    Args:
        ttl: 緩存過期時間（秒），默認 1 小時
        prefix: 緩存鍵前綴
    """
    return cached(ttl=ttl, prefix=prefix)


def cache_model_method(ttl: int = 600):
    """
    Django 模型方法緩存裝飾器
    
    使用範例:
        class MyModel(models.Model):
            @cache_model_method(ttl=300)
            def get_related_data(self):
                return expensive_query()
    
    Args:
        ttl: 緩存過期時間（秒），默認 10 分鐘
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # 使用模型類名、實例 ID 和方法名作為緩存鍵
            cache_key = f"{self.__class__.__name__}:{self.pk}:{func.__name__}"
            
            if args or kwargs:
                param_str = _generate_cache_key("", *args, **kwargs)
                cache_key = f"{cache_key}:{param_str}"
            
            # 嘗試從緩存讀取
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"模型方法緩存命中: {cache_key}")
                return cached_result
            
            # 執行方法
            result = func(self, *args, **kwargs)
            
            # 儲存到緩存
            cache.set(cache_key, result, ttl)
            logger.debug(f"模型方法結果已緩存: {cache_key}, TTL={ttl}s")
            
            return result
        
        return wrapper
    
    return decorator


def invalidate_cache(cache_keys: Union[str, list]):
    """
    緩存失效裝飾器（在函數執行後清除指定緩存）
    
    使用範例：
        @invalidate_cache(['user:*', 'profile:*'])
        def update_user_profile(user_id):
            # 更新資料庫
            pass
    
    Args:
        cache_keys: 要清除的緩存鍵或緩存鍵列表（支援萬用字元 *）
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 執行函數
            result = func(*args, **kwargs)
            
            # 清除緩存
            keys_to_delete = cache_keys if isinstance(cache_keys, list) else [cache_keys]
            for key_pattern in keys_to_delete:
                if '*' in key_pattern:
                    # 注意：Redis KEYS 命令在生產環境可能影響性能
                    logger.warning(f"使用萬用字元清除緩存: {key_pattern}（可能影響性能）")
                    try:
                        cache.delete_pattern(key_pattern)
                    except AttributeError:
                        logger.error("Cache backend 不支援 delete_pattern，請使用精確的緩存鍵")
                else:
                    cache.delete(key_pattern)
                    logger.debug(f"已清除緩存: {key_pattern}")
            
            return result
        
        return wrapper
    
    return decorator


class CachedProperty:
    """
    緩存屬性裝飾器（類似 @property 但帶緩存）
    
    使用範例：
        class MyClass:
            @CachedProperty(ttl=300)
            def expensive_property(self):
                return expensive_computation()
    """
    
    def __init__(self, ttl: int = 3600):
        self.ttl = ttl
        self.func = None
    
    def __call__(self, func):
        self.func = func
        return self
    
    def __get__(self, instance, owner):
        if instance is None:
            return self
        
        # 生成緩存鍵
        cache_key = f"{instance.__class__.__name__}:{id(instance)}:{self.func.__name__}"
        
        # 嘗試從緩存讀取
        cached_value = cache.get(cache_key)
        if cached_value is not None:
            return cached_value
        
        # 計算值
        value = self.func(instance)
        
        # 儲存到緩存
        cache.set(cache_key, value, self.ttl)
        
        return value


# ==================== Jenkins 專用緩存裝飾器 ====================

def cache_jenkins_api(ttl: int = 300):
    """
    Jenkins API 調用緩存裝飾器
    
    使用範例：
        @cache_jenkins_api(ttl=600)
        def get_jenkins_data(jenkins_url, job_name):
            return jenkins_api_call()
    
    Args:
        ttl: 緩存過期時間（秒），默認 5 分鐘
    """
    return cached(ttl=ttl, prefix='jenkins_api')


def cache_jenkins_config(ttl: Optional[int] = None):
    """
    Jenkins 配置文件緩存裝飾器
    
    使用範例：
        @cache_jenkins_config(ttl=1800)
        def read_jenkins_config(jenkins_ip, job_name, build_number):
            return read_file()
    
    Args:
        ttl: 緩存過期時間（秒），默認從 settings 讀取
    """
    cache_ttl = ttl or getattr(settings, 'JENKINS_CONFIG_CACHE_TTL', 1800)
    return cached(ttl=cache_ttl, prefix='jenkins_config')


def cache_jenkins_log(ttl: Optional[int] = None):
    """
    Jenkins 日誌文件緩存裝飾器
    
    使用範例：
        @cache_jenkins_log(ttl=3600)
        def read_jenkins_log(jenkins_ip, job_name, build_number):
            return read_log_file()
    
    Args:
        ttl: 緩存過期時間（秒），默認從 settings 讀取
    """
    cache_ttl = ttl or getattr(settings, 'JENKINS_LOG_CACHE_TTL', 3600)
    return cached(ttl=cache_ttl, prefix='jenkins_log')


# ==================== 工具函數 ====================

def get_cache_stats() -> dict:
    """
    獲取緩存統計資訊（需要 django-redis 支援）
    
    Returns:
        dict: 緩存統計資訊
    """
    try:
        from django_redis import get_redis_connection
        redis_conn = get_redis_connection("default")
        info = redis_conn.info()
        
        return {
            'used_memory': info.get('used_memory_human', 'N/A'),
            'total_keys': redis_conn.dbsize(),
            'hits': info.get('keyspace_hits', 0),
            'misses': info.get('keyspace_misses', 0),
            'hit_rate': info.get('keyspace_hits', 0) / max(info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0), 1) * 100,
        }
    except Exception as e:
        logger.error(f"獲取緩存統計失敗: {e}")
        return {}


def warm_cache(func: Callable, params_list: list):
    """
    預熱緩存（批量執行函數以填充緩存）
    
    使用範例：
        warm_cache(get_user_data, [
            {'user_id': 1},
            {'user_id': 2},
            {'user_id': 3},
        ])
    
    Args:
        func: 要預熱的函數
        params_list: 參數列表
    """
    logger.info(f"開始預熱緩存: {func.__name__}, 參數數量: {len(params_list)}")
    
    for params in params_list:
        try:
            func(**params)
        except Exception as e:
            logger.error(f"預熱緩存失敗: {params}, 錯誤: {e}")
    
    logger.info(f"緩存預熱完成: {func.__name__}")
