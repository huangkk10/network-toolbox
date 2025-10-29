"""
工具函數模組

提供各種可重用的工具函數，包括：
- MAC 地址解析和驗證
- 日期時間解析和格式化
"""

# MAC 地址工具
from .mac_utils import (
    parse_windows_client_id,
    normalize_mac_address,
    validate_mac_address,
)

# 日期時間工具
from .datetime_utils import (
    parse_windows_lease_expiry,
    parse_lease_expiry,  # 向後兼容別名
    format_datetime_for_display,
    is_expired,
    get_remaining_time,
    format_remaining_time,
)

__all__ = [
    # MAC 工具
    'parse_windows_client_id',
    'normalize_mac_address',
    'validate_mac_address',
    # 日期時間工具
    'parse_windows_lease_expiry',
    'parse_lease_expiry',
    'format_datetime_for_display',
    'is_expired',
    'get_remaining_time',
    'format_remaining_time',
]
