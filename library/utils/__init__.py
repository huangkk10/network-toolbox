"""
工具函數模組

提供各種可重用的工具函數，包括：
- MAC 地址解析和驗證
- 日期時間解析和格式化
- 日誌解析（DHCP, Windows DHCP, iPXE）
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

# 日誌解析工具
from .log_parser import (
    DHCPLogParser,
    WindowsDHCPLogParser,
    IPXELogParser,
    LogLevel,
    parse_dhcp_log,
    parse_windows_dhcp_log,
    parse_ipxe_log,
)

# 緩存裝飾器
from .cache_decorators import (
    cached,
    cache_result,
    cache_model_method,
    invalidate_cache,
    CachedProperty,
    cache_jenkins_api,
    cache_jenkins_config,
    cache_jenkins_log,
    get_cache_stats,
    warm_cache,
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
    # 日誌解析工具
    'DHCPLogParser',
    'WindowsDHCPLogParser',
    'IPXELogParser',
    'LogLevel',
    'parse_dhcp_log',
    'parse_windows_dhcp_log',
    'parse_ipxe_log',
    # 緩存裝飾器
    'cached',
    'cache_result',
    'cache_model_method',
    'invalidate_cache',
    'CachedProperty',
    'cache_jenkins_api',
    'cache_jenkins_config',
    'cache_jenkins_log',
    'get_cache_stats',
    'warm_cache',
]
