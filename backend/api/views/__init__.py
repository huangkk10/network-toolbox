"""
Views Package - 模組化 Views 導入
將所有 ViewSet 和 API 函數從子模組導入到此處
"""

# Base API
from .base import api_root

# Auth Views
from .auth import UserViewSet

# DHCP Views
from .dhcp_servers import DHCPServerViewSet
from .dhcp_leases import DHCPLeaseViewSet
from .dhcp_analytics import (
    dhcp_analytics_overview,
    dhcp_analytics_trend,
    dhcp_analytics_status_distribution,
    dhcp_analytics_recent_leases,
    dhcp_analytics_statistics,
)
from .dhcp_operations import (
    dhcp_sync_leases,
    dhcp_sync_config,
    dhcp_sync_logs,
)
from .dhcp_logs import (
    dhcp_analytics_logs,
    dhcp_lease_lookup,
)

# NAS Views
from .nas import NASConnectionLogViewSet

# IPXE Views
from .ipxe_servers import IPXEServerViewSet
from .ipxe_logs import IPXELogViewSet
from .ipxe_network import IPXENetworkQualityViewSet
from .ipxe_operations import ipxe_sync_logs
from .ipxe_analytics import (
    ipxe_analytics_overview,
    ipxe_analytics_statistics,
)

# Network Switch Views
from .network_switches import NetworkSwitchViewSet, SwitchPortViewSet

# System Views
from .system import (
    dashboard_stats,
    system_status,
)

# 明確導出所有公開的 API
__all__ = [
    # Base
    'api_root',
    
    # Auth
    'UserViewSet',
    
    # DHCP
    'DHCPServerViewSet',
    'DHCPLeaseViewSet',
    'dhcp_analytics_overview',
    'dhcp_analytics_trend',
    'dhcp_analytics_status_distribution',
    'dhcp_analytics_recent_leases',
    'dhcp_analytics_statistics',
    'dhcp_sync_leases',
    'dhcp_sync_config',
    'dhcp_sync_logs',
    'dhcp_analytics_logs',
    'dhcp_lease_lookup',
    
    # NAS
    'NASConnectionLogViewSet',
    
    # IPXE
    'IPXEServerViewSet',
    'IPXELogViewSet',
    'IPXENetworkQualityViewSet',
    'ipxe_sync_logs',
    'ipxe_analytics_overview',
    'ipxe_analytics_statistics',
    
    # Network Switches
    'NetworkSwitchViewSet',
    'SwitchPortViewSet',
    
    # System
    'dashboard_stats',
    'system_status',
]
