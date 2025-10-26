from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from django.contrib.auth.models import User
from .models import DHCPServer, DHCPLease
from .serializers import DHCPServerSerializer, DHCPLeaseSerializer, UserSerializer


class UserViewSet(viewsets.ModelViewSet):
    """用戶管理 API ViewSet"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]  # 開發階段允許所有請求，生產環境應改為 IsAdminUser
    pagination_class = None  # 禁用分頁，直接返回所有用戶
    
    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        """重設用戶密碼"""
        user = self.get_object()
        new_password = request.data.get('password')
        if not new_password:
            return Response(
                {'error': '請提供新密碼'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        user.set_password(new_password)
        user.save()
        return Response({'message': '密碼重設成功'})


class DHCPServerViewSet(viewsets.ModelViewSet):
    """DHCP Server API ViewSet"""
    queryset = DHCPServer.objects.all()
    serializer_class = DHCPServerSerializer
    permission_classes = [AllowAny]


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


@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request):
    """API 根端點"""
    return Response({
        'message': 'Network Toolbox API',
        'version': '1.0.0',
        'endpoints': {
            'dhcp_servers': '/api/dhcp-servers/',
            'dhcp_leases': '/api/dhcp-leases/',
            'admin': '/admin/',
        }
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def dashboard_stats(request):
    """儀表板統計資料"""
    total_servers = DHCPServer.objects.count()
    online_servers = DHCPServer.objects.filter(status='online').count()
    warning_servers = DHCPServer.objects.filter(status='warning').count()
    total_leases = DHCPLease.objects.count()
    active_leases = DHCPLease.objects.filter(is_active=True).count()
    
    # 計算平均池使用率
    avg_pool_usage = 0
    if total_servers > 0:
        servers = DHCPServer.objects.all()
        total_usage = sum(server.pool_usage for server in servers)
        avg_pool_usage = total_usage / total_servers
    
    return Response({
        'total_servers': total_servers,
        'online_servers': online_servers,
        'warning_servers': warning_servers,
        'offline_servers': total_servers - online_servers - warning_servers,
        'total_leases': total_leases,
        'active_leases': active_leases,
        'avg_pool_usage': round(avg_pool_usage, 2),
    })
