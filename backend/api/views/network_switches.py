"""
Network Switch Views - 網路交換器管理 API
"""
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from api.models import NetworkSwitch, SwitchPort, DHCPLease, DHCPServer
from api.serializers import (
    NetworkSwitchSerializer, 
    NetworkSwitchDetailSerializer,
    SwitchPortSerializer,
)

logger = logging.getLogger(__name__)


class NetworkSwitchViewSet(viewsets.ModelViewSet):
    """
    網路交換器 ViewSet
    
    提供 Switch 的 CRUD 操作和統計功能
    """
    queryset = NetworkSwitch.objects.all()
    serializer_class = NetworkSwitchSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    
    def get_serializer_class(self):
        """根據 action 選擇不同的 serializer"""
        if self.action == 'retrieve':
            return NetworkSwitchDetailSerializer
        return NetworkSwitchSerializer
    
    def get_queryset(self):
        """支援按 DHCP Server 過濾"""
        queryset = NetworkSwitch.objects.all()
        
        # 過濾條件
        server_id = self.request.query_params.get('server_id', None)
        status_filter = self.request.query_params.get('status', None)
        
        if server_id and server_id != 'all':
            queryset = queryset.filter(dhcp_server_id=server_id)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-last_seen')
    
    @action(detail=True, methods=['get'])
    def devices(self, request, pk=None):
        """
        獲取 Switch 下的所有設備
        
        GET /api/switches/{id}/devices/
        """
        switch = self.get_object()
        
        # 時間範圍
        hours = int(request.query_params.get('hours', 24))
        recent_time = timezone.now() - timedelta(hours=hours)
        
        # 查詢設備
        devices = DHCPLease.objects.filter(
            remote_id=switch.remote_id,
            is_active=True,
            updated_at__gte=recent_time
        ).select_related('server').order_by('-updated_at')
        
        # 按端口分組
        devices_by_port = {}
        for device in devices:
            circuit_id = device.circuit_id or 'unknown'
            if circuit_id not in devices_by_port:
                devices_by_port[circuit_id] = []
            devices_by_port[circuit_id].append({
                'id': device.id,
                'ip_address': device.ip_address,
                'mac_address': device.mac_address,
                'hostname': device.hostname,
                'lease_start': device.lease_start,
                'lease_end': device.lease_end,
                'server_name': device.server.name,
            })
        
        return Response({
            'switch_id': switch.id,
            'switch_name': switch.name,
            'remote_id': switch.remote_id,
            'total_devices': devices.count(),
            'devices_by_port': devices_by_port,
        })
    
    @action(detail=True, methods=['get'])
    def ports(self, request, pk=None):
        """
        獲取 Switch 的所有端口資訊
        
        GET /api/switches/{id}/ports/
        """
        switch = self.get_object()
        ports = switch.ports.all().order_by('port_number')
        
        serializer = SwitchPortSerializer(ports, many=True)
        return Response({
            'switch_id': switch.id,
            'switch_name': switch.name,
            'total_ports': ports.count(),
            'ports': serializer.data,
        })
    
    @action(detail=True, methods=['post'])
    def update_stats(self, request, pk=None):
        """
        更新 Switch 統計資訊
        
        POST /api/switches/{id}/update_stats/
        """
        switch = self.get_object()
        
        try:
            switch.update_statistics()
            
            # 同時更新端口統計
            for port in switch.ports.all():
                port.update_statistics()
            
            logger.info(f'已更新 Switch {switch.name} 的統計資訊')
            
            return Response({
                'success': True,
                'message': '統計資訊已更新',
                'switch': NetworkSwitchSerializer(switch).data,
            })
        except Exception as e:
            logger.error(f'更新 Switch 統計失敗: {e}', exc_info=True)
            return Response({
                'success': False,
                'error': str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        獲取所有 Switch 的統計資訊
        
        GET /api/switches/statistics/
        
        Query Parameters:
        - server_id: DHCP Server ID (可選)
        """
        server_id = request.query_params.get('server_id', None)
        
        # 基礎查詢
        queryset = NetworkSwitch.objects.all()
        if server_id and server_id != 'all':
            queryset = queryset.filter(dhcp_server_id=server_id)
        
        # 統計資訊
        total_switches = queryset.count()
        active_switches = queryset.filter(status='active').count()
        inactive_switches = queryset.filter(status='inactive').count()
        unknown_switches = queryset.filter(status='unknown').count()
        
        # 連接設備統計
        total_devices = sum(sw.connected_devices for sw in queryset)
        total_ports = sum(sw.total_ports for sw in queryset)
        active_ports = sum(sw.active_ports for sw in queryset)
        
        # 按 DHCP Server 統計
        switches_by_server = queryset.values(
            'dhcp_server__name', 
            'dhcp_server__id'
        ).annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Top 10 最多設備的 Switch
        top_switches = queryset.order_by('-connected_devices')[:10]
        top_switches_data = [{
            'id': sw.id,
            'name': sw.name or sw.remote_id,
            'remote_id': sw.remote_id,
            'connected_devices': sw.connected_devices,
            'active_ports': sw.active_ports,
            'status': sw.status,
        } for sw in top_switches]
        
        return Response({
            'total_switches': total_switches,
            'active_switches': active_switches,
            'inactive_switches': inactive_switches,
            'unknown_switches': unknown_switches,
            'total_devices': total_devices,
            'total_ports': total_ports,
            'active_ports': active_ports,
            'switches_by_server': list(switches_by_server),
            'top_switches': top_switches_data,
        })
    
    @action(detail=False, methods=['post'])
    def sync_from_leases(self, request):
        """
        從 DHCP Lease 記錄中同步 Switch 資訊
        
        POST /api/switches/sync_from_leases/
        
        Body:
        {
            "server_id": 1,  // 可選，指定 DHCP Server
            "hours": 24      // 可選，同步最近幾小時的記錄
        }
        """
        server_id = request.data.get('server_id', None)
        hours = int(request.data.get('hours', 24))
        recent_time = timezone.now() - timedelta(hours=hours)
        
        try:
            # 查詢有 Option 82 資訊的租約
            leases_query = DHCPLease.objects.exclude(
                Q(remote_id='') | Q(remote_id__isnull=True)
            ).filter(updated_at__gte=recent_time)
            
            if server_id:
                leases_query = leases_query.filter(server_id=server_id)
            
            # 按 remote_id 分組
            remote_ids = leases_query.values_list('remote_id', flat=True).distinct()
            
            created_count = 0
            updated_count = 0
            
            for remote_id in remote_ids:
                # 檢查 Switch 是否存在
                switch, created = NetworkSwitch.objects.get_or_create(
                    remote_id=remote_id,
                    defaults={
                        'status': 'unknown',
                    }
                )
                
                if created:
                    created_count += 1
                    logger.info(f'創建新 Switch: {remote_id}')
                else:
                    updated_count += 1
                
                # 更新統計資訊
                switch.update_statistics()
                
                # 同步端口資訊
                circuit_ids = leases_query.filter(
                    remote_id=remote_id
                ).exclude(
                    Q(circuit_id='') | Q(circuit_id__isnull=True)
                ).values_list('circuit_id', flat=True).distinct()
                
                for circuit_id in circuit_ids:
                    port, port_created = SwitchPort.objects.get_or_create(
                        switch=switch,
                        circuit_id=circuit_id,
                        defaults={
                            'status': 'unknown',
                        }
                    )
                    
                    # 更新端口統計
                    port.update_statistics()
            
            logger.info(f'Switch 同步完成: 創建 {created_count}, 更新 {updated_count}')
            
            return Response({
                'success': True,
                'message': f'同步完成',
                'created': created_count,
                'updated': updated_count,
                'total': created_count + updated_count,
            })
        
        except Exception as e:
            logger.error(f'Switch 同步失敗: {e}', exc_info=True)
            return Response({
                'success': False,
                'error': str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def topology(self, request):
        """
        獲取網路拓撲資訊（用於視覺化）
        
        GET /api/switches/topology/
        
        返回格式適用於 D3.js 或其他圖表庫
        """
        server_id = request.query_params.get('server_id', None)
        
        queryset = NetworkSwitch.objects.all()
        if server_id and server_id != 'all':
            queryset = queryset.filter(dhcp_server_id=server_id)
        
        # 構建拓撲結構
        nodes = []
        links = []
        
        # 添加 DHCP Server 節點
        servers = DHCPServer.objects.all()
        if server_id and server_id != 'all':
            servers = servers.filter(id=server_id)
        
        for server in servers:
            nodes.append({
                'id': f'server_{server.id}',
                'name': server.name,
                'type': 'dhcp_server',
                'ip': server.ip_address,
                'status': server.status,
            })
        
        # 添加 Switch 節點和連結
        for switch in queryset:
            switch_node_id = f'switch_{switch.id}'
            nodes.append({
                'id': switch_node_id,
                'name': switch.name or switch.remote_id,
                'type': 'switch',
                'remote_id': switch.remote_id,
                'status': switch.status,
                'connected_devices': switch.connected_devices,
                'active_ports': switch.active_ports,
            })
            
            # 連接到 DHCP Server
            if switch.dhcp_server:
                links.append({
                    'source': f'server_{switch.dhcp_server.id}',
                    'target': switch_node_id,
                    'type': 'dhcp_relay',
                })
            
            # 添加連接設備（簡化版本，只顯示統計）
            if switch.connected_devices > 0:
                device_node_id = f'devices_{switch.id}'
                nodes.append({
                    'id': device_node_id,
                    'name': f'{switch.connected_devices} 台設備',
                    'type': 'device_group',
                    'count': switch.connected_devices,
                })
                
                links.append({
                    'source': switch_node_id,
                    'target': device_node_id,
                    'type': 'connection',
                    'count': switch.connected_devices,
                })
        
        return Response({
            'nodes': nodes,
            'links': links,
        })


class SwitchPortViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Switch 端口 ViewSet（只讀）
    """
    queryset = SwitchPort.objects.all()
    serializer_class = SwitchPortSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    
    def get_queryset(self):
        """支援按 Switch 過濾"""
        queryset = SwitchPort.objects.all()
        
        switch_id = self.request.query_params.get('switch_id', None)
        if switch_id:
            queryset = queryset.filter(switch_id=switch_id)
        
        return queryset.order_by('switch', 'port_number')
