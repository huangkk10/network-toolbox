"""
日期時間工具模組

提供統一的日期時間解析、格式化和轉換功能。
主要用於處理 DHCP 租約到期時間、日誌時間戳等。
"""
import logging
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Optional, Union
from django.utils import timezone

logger = logging.getLogger(__name__)


def parse_windows_lease_expiry(
    expiry_str: Union[str, None],
    default_hours: int = 24
) -> datetime:
    """
    解析 Windows DHCP 租約到期時間
    
    支援多種時間格式：
    1. Windows JSON 格式: /Date(1761993082644)/
    2. ISO 格式: 2025-10-30T15:30:00
    3. 標準格式: 2025-10-30 15:30:00
    4. 美式格式: 10/30/2025 03:30:00 PM
    
    Args:
        expiry_str: 時間字串，可以是上述任一格式
        default_hours: 當解析失敗時，返回當前時間 + N 小時（預設 24 小時）
    
    Returns:
        datetime: Django aware datetime 對象（帶時區資訊）
    
    Examples:
        >>> parse_windows_lease_expiry('/Date(1698409200000)/')
        datetime.datetime(2023, 10, 27, 15, 0, 0, tzinfo=<UTC>)
        
        >>> parse_windows_lease_expiry('2025-10-30 15:30:00')
        datetime.datetime(2025, 10, 30, 15, 30, 0, tzinfo=<...>)
        
        >>> parse_windows_lease_expiry(None)
        datetime.datetime(...) # 當前時間 + 24 小時
    """
    # 空值處理：返回當前時間 + 預設小時數
    if not expiry_str:
        logger.debug(f'租約到期時間為空，使用預設值: +{default_hours}h')
        return timezone.now() + timedelta(hours=default_hours)
    
    try:
        # 格式 1: Windows JSON 格式 /Date(timestamp)/
        if isinstance(expiry_str, str) and expiry_str.startswith('/Date('):
            # 提取毫秒時間戳：/Date(1761993082644)/
            timestamp_str = expiry_str[6:-2]  # 移除 "/Date(" 和 ")/"
            timestamp_ms = int(timestamp_str)
            timestamp_sec = timestamp_ms / 1000.0
            
            # 從 UTC 時間戳創建 aware datetime
            dt = datetime.fromtimestamp(timestamp_sec, tz=dt_timezone.utc)
            logger.debug(f'成功解析 Windows JSON 時間: {expiry_str} -> {dt}')
            return dt
        
        # 格式 2-4: 嘗試多種標準格式
        formats = [
            '%Y-%m-%dT%H:%M:%S',      # ISO 格式
            '%Y-%m-%d %H:%M:%S',       # 標準格式
            '%m/%d/%Y %I:%M:%S %p',    # 美式格式
            '%Y/%m/%d %H:%M:%S',       # 另一種標準格式
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(str(expiry_str), fmt)
                # 使用 Django timezone 使其 aware
                aware_dt = timezone.make_aware(dt)
                logger.debug(f'成功解析時間 (格式: {fmt}): {expiry_str} -> {aware_dt}')
                return aware_dt
            except ValueError:
                continue
        
        # 所有格式都失敗
        logger.warning(
            f'無法解析租約到期時間 "{expiry_str}"，'
            f'使用預設值: +{default_hours}h'
        )
        return timezone.now() + timedelta(hours=default_hours)
    
    except Exception as e:
        logger.error(
            f'租約到期時間解析異常 ({expiry_str}): {str(e)}',
            exc_info=True
        )
        return timezone.now() + timedelta(hours=default_hours)


def format_datetime_for_display(
    dt: datetime,
    format_type: str = 'standard'
) -> str:
    """
    格式化 datetime 用於顯示
    
    Args:
        dt: datetime 對象
        format_type: 格式類型
            - 'standard': 2025-10-30 15:30:00
            - 'iso': 2025-10-30T15:30:00
            - 'us': 10/30/2025 03:30:00 PM
            - 'compact': 20251030153000
    
    Returns:
        格式化後的時間字串
    
    Examples:
        >>> now = timezone.now()
        >>> format_datetime_for_display(now, 'standard')
        '2025-10-30 15:30:00'
    """
    if not dt:
        return ''
    
    formats = {
        'standard': '%Y-%m-%d %H:%M:%S',
        'iso': '%Y-%m-%dT%H:%M:%S',
        'us': '%m/%d/%Y %I:%M:%S %p',
        'compact': '%Y%m%d%H%M%S',
    }
    
    fmt = formats.get(format_type, formats['standard'])
    return dt.strftime(fmt)


def is_expired(expiry_dt: datetime) -> bool:
    """
    判斷租約是否已過期
    
    Args:
        expiry_dt: 到期時間
    
    Returns:
        bool: True 表示已過期，False 表示未過期
    
    Examples:
        >>> past_time = timezone.now() - timedelta(hours=1)
        >>> is_expired(past_time)
        True
        
        >>> future_time = timezone.now() + timedelta(hours=1)
        >>> is_expired(future_time)
        False
    """
    if not expiry_dt:
        return False
    
    return expiry_dt < timezone.now()


def get_remaining_time(expiry_dt: datetime) -> timedelta:
    """
    取得剩餘時間
    
    Args:
        expiry_dt: 到期時間
    
    Returns:
        timedelta: 剩餘時間（如果已過期則為負值）
    
    Examples:
        >>> future_time = timezone.now() + timedelta(hours=2)
        >>> remaining = get_remaining_time(future_time)
        >>> remaining.total_seconds() > 7000  # 接近 2 小時
        True
    """
    if not expiry_dt:
        return timedelta(0)
    
    return expiry_dt - timezone.now()


def format_remaining_time(expiry_dt: datetime) -> str:
    """
    格式化剩餘時間為人類可讀格式
    
    Args:
        expiry_dt: 到期時間
    
    Returns:
        str: 剩餘時間描述（例如：「2天3小時」、「已過期」）
    
    Examples:
        >>> future_time = timezone.now() + timedelta(days=2, hours=3)
        >>> format_remaining_time(future_time)
        '2天3小時'
    """
    if not expiry_dt:
        return '未知'
    
    remaining = get_remaining_time(expiry_dt)
    
    if remaining.total_seconds() < 0:
        return '已過期'
    
    days = remaining.days
    hours = remaining.seconds // 3600
    minutes = (remaining.seconds % 3600) // 60
    
    parts = []
    if days > 0:
        parts.append(f'{days}天')
    if hours > 0:
        parts.append(f'{hours}小時')
    if minutes > 0 and days == 0:  # 只在不到一天時顯示分鐘
        parts.append(f'{minutes}分鐘')
    
    return ''.join(parts) if parts else '不到1分鐘'


# 向後兼容別名
parse_lease_expiry = parse_windows_lease_expiry
