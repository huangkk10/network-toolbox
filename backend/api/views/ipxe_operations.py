"""
IPXE 操作相關 Views
處理 IPXE 日誌同步等操作
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone
import logging

from ..models import IPXEServer
from ..ipxe_service import IPXEService

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def ipxe_sync_logs(request, server_id):
    """
    同步指定 IPXE 伺服器的日誌
    POST /api/ipxe-servers/{server_id}/sync-logs/
    Request Body:
    - limit: 同步日誌數量限制（預設 1000）
    """
    try:
        # 檢查伺服器是否存在
        try:
            server = IPXEServer.objects.get(id=server_id)
        except IPXEServer.DoesNotExist:
            logger.warning(f'IPXE 伺服器不存在: server_id={server_id}')
            return Response(
                {'error': 'IPXE 伺服器不存在'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 獲取限制數量（預設 1000）
        limit = request.data.get('limit', 1000)
        
        logger.info(f'開始同步 IPXE 伺服器日誌: {server.name} ({server.ip_address}), limit={limit}')
        
        # 執行同步
        ipxe_service = IPXEService(server)
        result = ipxe_service.sync_logs_to_db(limit=limit)
        
        # 更新伺服器的 last_sync_at
        server.last_sync_at = timezone.now()
        server.save(update_fields=['last_sync_at'])
        
        logger.info(f'IPXE 日誌同步完成: {result}')
        
        return Response({
            'message': '日誌同步成功',
            'server': server.name,
            'mac_logs_collected': result['mac_logs'],
            'boot_logs_collected': result['boot_logs'],
            'total_logs': result['mac_logs'] + result['boot_logs'],
            'sync_time': server.last_sync_at
        })
        
    except Exception as e:
        logger.error(f'同步 IPXE 日誌失敗: {str(e)}', exc_info=True)
        return Response(
            {'error': f'同步失敗: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
