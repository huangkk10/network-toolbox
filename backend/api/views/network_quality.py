"""
網路品質監控 Views

提供 DHCP Server 到 Switch 的網路品質監控 API 端點
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from api.models import DHCPServer, NetworkSwitch, NetworkQualityRecord
from api.serializers import NetworkQualityRecordSerializer

logger = logging.getLogger(__name__)


class NetworkQualityViewSet(viewsets.ViewSet):
    """
    網路品質監控 API
    
    提供 DHCP Server 到 Switch 的網路品質查詢和手動刷新功能
    """
    
    permission_classes = [AllowAny]  # 開發環境使用，生產環境應改為 IsAuthenticated
    
    def _get_service(self):
        """獲取網路品質服務實例"""
        from library.services.network_quality_service import NetworkQualityService
        return NetworkQualityService()
    
    @action(detail=True, methods=['get'], url_path='network-quality')
    def current_quality(self, request, pk=None):
        """
        獲取當前網路品質
        
        GET /api/dhcp-servers/{id}/network-quality/
        
        返回該 DHCP Server 到所有關聯 Switch 的當前網路品質
        """
        try:
            service = self._get_service()
            result = service.get_current_quality(int(pk))
            
            if 'error' in result:
                return Response(
                    {'success': False, 'error': result['error']},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            return Response({
                'success': True,
                'data': result
            })
            
        except Exception as e:
            logger.error(f"Failed to get current quality for server {pk}: {e}", exc_info=True)
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'], url_path='network-quality/history')
    def quality_history(self, request, pk=None):
        """
        獲取歷史網路品質
        
        GET /api/dhcp-servers/{id}/network-quality/history/?time_range=24h&switch_ids=1,2,3
        
        Query Parameters:
            - time_range: 時間範圍（1h, 6h, 24h, 7d, 30d），預設 24h
            - switch_ids: Switch ID 列表，逗號分隔（可選）
        """
        try:
            time_range = request.query_params.get('time_range', '24h')
            switch_ids_str = request.query_params.get('switch_ids', '')
            
            # 解析 switch_ids
            switch_ids = None
            if switch_ids_str:
                try:
                    switch_ids = [int(x.strip()) for x in switch_ids_str.split(',') if x.strip()]
                except ValueError:
                    return Response(
                        {'success': False, 'error': 'Invalid switch_ids format'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # 驗證 time_range
            valid_ranges = ['1h', '6h', '24h', '7d', '30d']
            if time_range not in valid_ranges:
                return Response(
                    {'success': False, 'error': f'Invalid time_range. Valid values: {valid_ranges}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            service = self._get_service()
            result = service.get_history(int(pk), time_range, switch_ids)
            
            if 'error' in result:
                return Response(
                    {'success': False, 'error': result['error']},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            return Response({
                'success': True,
                'data': result
            })
            
        except Exception as e:
            logger.error(f"Failed to get quality history for server {pk}: {e}", exc_info=True)
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='network-quality/refresh')
    def refresh_quality(self, request, pk=None):
        """
        手動觸發品質檢測
        
        POST /api/dhcp-servers/{id}/network-quality/refresh/
        
        Request Body (Optional):
            {
                "switch_ids": [1, 2, 3]
            }
        
        注意：此操作會同步執行 Ping 測試，可能需要數秒時間
        """
        try:
            # 檢查 DHCP Server 是否存在
            try:
                server = DHCPServer.objects.get(id=pk)
            except DHCPServer.DoesNotExist:
                return Response(
                    {'success': False, 'error': 'DHCP Server not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            service = self._get_service()
            result = service.collect_server_quality(int(pk))
            
            return Response({
                'success': True,
                'message': f'網路品質檢測完成，共 {result.get("total_records", 0)} 筆記錄',
                'data': result
            })
            
        except Exception as e:
            logger.error(f"Failed to refresh quality for server {pk}: {e}", exc_info=True)
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'], url_path='network-quality/summary')
    def quality_summary(self, request, pk=None):
        """
        獲取品質統計摘要
        
        GET /api/dhcp-servers/{id}/network-quality/summary/
        
        返回指定時間範圍內的統計摘要
        """
        try:
            time_range = request.query_params.get('time_range', '24h')
            
            service = self._get_service()
            result = service.get_history(int(pk), time_range)
            
            if 'error' in result:
                return Response(
                    {'success': False, 'error': result['error']},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # 只返回統計部分
            return Response({
                'success': True,
                'data': {
                    'time_range': result.get('time_range'),
                    'start_time': result.get('start_time'),
                    'end_time': result.get('end_time'),
                    'statistics': result.get('statistics', {})
                }
            })
            
        except Exception as e:
            logger.error(f"Failed to get quality summary for server {pk}: {e}", exc_info=True)
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='network-quality/all')
    def all_servers_quality(self, request):
        """
        獲取所有 DHCP Server 的網路品質概覽
        
        GET /api/dhcp-servers/network-quality/all/
        """
        try:
            servers = DHCPServer.objects.filter(status='online')
            service = self._get_service()
            
            results = []
            for server in servers:
                quality = service.get_current_quality(server.id)
                results.append({
                    'server_id': server.id,
                    'server_name': server.name,
                    'server_ip': server.ip_address,
                    'summary': quality.get('summary', {}),
                    'recorded_at': quality.get('recorded_at')
                })
            
            return Response({
                'success': True,
                'data': {
                    'total_servers': len(results),
                    'servers': results
                }
            })
            
        except Exception as e:
            logger.error(f"Failed to get all servers quality: {e}", exc_info=True)
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
