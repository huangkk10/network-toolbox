from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views.user_profile import UserProfileViewSet

router = DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'dhcp-servers', views.DHCPServerViewSet)
router.register(r'dhcp-leases', views.DHCPLeaseViewSet)
router.register(r'nas-logs', views.NASConnectionLogViewSet)
router.register(r'ntp-logs', views.NTPSyncLogViewSet)
router.register(r'gitlab-connection', views.GitLabConnectionViewSet)
router.register(r'ipxe-servers', views.IPXEServerViewSet)
router.register(r'ipxe-logs', views.IPXELogViewSet)
router.register(r'ipxe-network-quality', views.IPXENetworkQualityViewSet)
router.register(r'switches', views.NetworkSwitchViewSet)
router.register(r'switch-ports', views.SwitchPortViewSet)

# Jenkins API
router.register(r'jenkins-servers', views.JenkinsServerViewSet)
router.register(r'jenkins-jobs', views.JenkinsJobViewSet)
router.register(r'jenkins-builds', views.JenkinsBuildViewSet)

# Ansible Inventory API
router.register(r'ansible-inventory', views.AnsibleInventoryViewSet)

# User Profile API
router.register(r'user-profile', UserProfileViewSet, basename='user-profile')

urlpatterns = [
    path('', views.api_root, name='api_root'),
    path('dashboard/stats/', views.dashboard_stats, name='dashboard_stats'),
    
    # DHCP Analytics API
    path('dhcp-analytics/overview/', views.dhcp_analytics_overview, name='dhcp_analytics_overview'),
    path('dhcp-analytics/trend/', views.dhcp_analytics_trend, name='dhcp_analytics_trend'),
    path('dhcp-analytics/status-distribution/', views.dhcp_analytics_status_distribution, name='dhcp_analytics_status_distribution'),
    path('dhcp-analytics/recent-leases/', views.dhcp_analytics_recent_leases, name='dhcp_analytics_recent_leases'),
    path('dhcp-analytics/logs/', views.dhcp_analytics_logs, name='dhcp_analytics_logs'),
    path('dhcp-analytics/statistics/', views.dhcp_analytics_statistics, name='dhcp_analytics_statistics'),
    path('dhcp-servers/<int:server_id>/sync-leases/', views.dhcp_sync_leases, name='dhcp_sync_leases'),
    path('dhcp-servers/<int:server_id>/sync-logs/', views.dhcp_sync_logs, name='dhcp_sync_logs'),
    path('dhcp-servers/<int:server_id>/sync-config/', views.dhcp_sync_config, name='dhcp_sync_config'),
    
    # IPXE Analytics API
    path('ipxe-servers/<int:server_id>/sync-logs/', views.ipxe_sync_logs, name='ipxe_sync_logs'),
    path('ipxe-analytics/overview/', views.ipxe_analytics_overview, name='ipxe_analytics_overview'),
    path('ipxe-analytics/statistics/', views.ipxe_analytics_statistics, name='ipxe_analytics_statistics'),
    
    # Jenkins Analytics API
    path('jenkins-analytics/build-trend/', views.jenkins_build_trend, name='jenkins_build_trend'),
    
    # MAC 地址查詢 API
    path('dhcp-leases/lookup/', views.dhcp_lease_lookup, name='dhcp_lease_lookup'),
    
    # 系統監控 API
    path('system/status/', views.system_status, name='system_status'),
    
    path('', include(router.urls)),
]
