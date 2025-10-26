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
    path('', include(router.urls)),
]
