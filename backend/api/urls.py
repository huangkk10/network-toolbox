from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'dhcp-servers', views.DHCPServerViewSet)
router.register(r'dhcp-leases', views.DHCPLeaseViewSet)

urlpatterns = [
    path('', views.api_root, name='api_root'),
    path('dashboard/stats/', views.dashboard_stats, name='dashboard_stats'),
    
    # DHCP Analytics API
    path('dhcp-analytics/overview/', views.dhcp_analytics_overview, name='dhcp_analytics_overview'),
    path('dhcp-analytics/trend/', views.dhcp_analytics_trend, name='dhcp_analytics_trend'),
    path('dhcp-analytics/status-distribution/', views.dhcp_analytics_status_distribution, name='dhcp_analytics_status_distribution'),
    path('dhcp-analytics/recent-leases/', views.dhcp_analytics_recent_leases, name='dhcp_analytics_recent_leases'),
    path('dhcp-analytics/logs/', views.dhcp_analytics_logs, name='dhcp_analytics_logs'),
    path('dhcp-servers/<int:server_id>/sync-leases/', views.dhcp_sync_leases, name='dhcp_sync_leases'),
    
    path('', include(router.urls)),
]
