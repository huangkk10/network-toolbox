"""
DHCP Lease 管理 Views
包含 DHCP Lease 的查詢和過濾功能
"""

from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from ..models import DHCPLease
from ..serializers import DHCPLeaseSerializer


class DHCPLeaseViewSet(viewsets.ModelViewSet):
    """DHCP Lease API ViewSet"""
    queryset = DHCPLease.objects.all()
    serializer_class = DHCPLeaseSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = DHCPLease.objects.all()
        server_id = self.request.query_params.get('server', None)
        if server_id is not None:
            queryset = queryset.filter(server_id=server_id)
        return queryset
