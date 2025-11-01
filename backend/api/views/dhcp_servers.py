"""
DHCP Server 管理 Views
包含 DHCP Server 的 CRUD 操作和自動同步功能
"""

from rest_framework import viewsets, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from ..models import DHCPServer
from ..serializers import DHCPServerSerializer
import logging

logger = logging.getLogger(__name__)


class DHCPServerViewSet(viewsets.ModelViewSet):
    """DHCP Server API ViewSet"""
    queryset = DHCPServer.objects.all()
    serializer_class = DHCPServerSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        """
        創建新的 DHCP Server 並自動執行初始同步
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # 保存 DHCP Server
        server = serializer.save()
        logger.info(f'成功創建 DHCP Server: {server.name} ({server.ip_address})')
        
        # 自動執行初始同步
        sync_result = self._auto_sync_new_server(server)
        
        # 返回創建結果和同步統計
        response_data = serializer.data
        response_data['auto_sync'] = sync_result
        
        return Response(response_data, status=status.HTTP_201_CREATED)
    
    def _auto_sync_new_server(self, server):
        """
        自動同步新創建的 DHCP Server
        
        Args:
            server: DHCPServer 實例
        
        Returns:
            同步結果字典
        """
        sync_result = {
            'enabled': True,
            'scopes': {'success': False, 'stats': {}},
            'leases': {'success': False, 'stats': {}},
            'logs': {'success': False, 'stats': {}},
            'errors': [],
        }
        
        try:
            from ..ssh_powershell_service import WindowsSSHPowerShellService
            from ..services import DHCPLogService
            
            logger.info(f'開始自動同步 DHCP Server: {server.name} ({server.ip_address})')
            
            # 1. 同步 Scopes 和 Leases（使用 SSH + PowerShell）
            try:
                with WindowsSSHPowerShellService(server) as service:
                    # 同步 Scopes
                    scope_stats = service.sync_scopes_to_db()
                    sync_result['scopes'] = {
                        'success': True,
                        'stats': scope_stats
                    }
                    logger.info(f'Scopes 同步完成: {scope_stats}')
                    
                    # 同步 Leases
                    lease_stats = service.sync_leases_to_db()
                    sync_result['leases'] = {
                        'success': True,
                        'stats': lease_stats
                    }
                    logger.info(f'Leases 同步完成: {lease_stats}')
            
            except Exception as e:
                error_msg = f'同步 Scopes/Leases 失敗: {str(e)}'
                logger.error(error_msg, exc_info=True)
                sync_result['errors'].append(error_msg)
            
            # 2. 同步 Logs（使用 DHCPLogService）
            try:
                log_service = DHCPLogService(server)
                log_stats = log_service.sync_logs_to_db(limit=1000)
                sync_result['logs'] = {
                    'success': True,
                    'stats': log_stats
                }
                logger.info(f'Logs 同步完成: {log_stats}')
            
            except Exception as e:
                error_msg = f'同步 Logs 失敗: {str(e)}'
                logger.error(error_msg, exc_info=True)
                sync_result['errors'].append(error_msg)
            
            logger.info(f'DHCP Server 自動同步完成: {server.name}')
            
        except Exception as e:
            error_msg = f'自動同步失敗: {str(e)}'
            logger.error(error_msg, exc_info=True)
            sync_result['errors'].append(error_msg)
        
        return sync_result
