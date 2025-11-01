"""
DHCP 操作 API Views
包含同步租約、配置、日誌的操作
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from ..models import DHCPServer
import logging

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def dhcp_sync_leases(request, server_id):
    """
    同步指定 DHCP Server 的租約資料
    支援 SSH + PowerShell 方式（Windows Server）
    """
    try:
        from ..ssh_powershell_service import WindowsSSHPowerShellService
        
        server = DHCPServer.objects.get(id=server_id)
        
        # 使用 SSH + PowerShell 同步（適用於 Windows DHCP Server）
        logger.info(f'開始透過 SSH + PowerShell 同步 Server {server.name} ({server.ip_address})')
        
        with WindowsSSHPowerShellService(server) as service:
            # 執行同步
            result = service.sync_leases_to_db()
        
        logger.info(f'成功同步 Server {server.name} 的租約資料: {result}')
        
        return Response({
            'message': '同步成功',
            'stats': result,
            'server': {
                'name': server.name,
                'ip': server.ip_address,
                'total_leases': server.total_leases,
                'active_leases': server.active_leases,
                'last_sync': server.last_sync_at.strftime('%Y-%m-%d %H:%M:%S') if server.last_sync_at else None,
            }
        })
    
    except DHCPServer.DoesNotExist:
        return Response(
            {'error': 'DHCP Server 不存在'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f'同步租約失敗: {str(e)}', exc_info=True)
        return Response(
            {'error': f'同步失敗: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def dhcp_sync_config(request, server_id):
    """
    同步指定 DHCP Server 的配置文件（dhcpd.conf）
    解析 subnet 和 range 資訊，創建 DHCPScope 記錄
    適用於 Linux DHCP Server (ISC DHCP)
    """
    try:
        from ..services import LinuxDHCPConfigService
        
        server = DHCPServer.objects.get(id=server_id)
        
        logger.info(f'開始同步 Linux DHCP 配置: {server.name} ({server.ip_address})')
        
        with LinuxDHCPConfigService(server) as service:
            # 執行配置同步
            result = service.sync_config_to_db()
        
        if result.get('success'):
            logger.info(f'成功同步 Server {server.name} 的配置: {result}')
            
            return Response({
                'message': result.get('message', '同步成功'),
                'stats': {
                    'scopes_found': result.get('scopes_found', 0),
                    'scopes_created': result.get('scopes_created', 0),
                    'scopes_updated': result.get('scopes_updated', 0),
                    'scopes_with_leases': result.get('scopes_with_leases', 0),
                },
                'server': {
                    'name': server.name,
                    'ip': server.ip_address,
                    'pool_usage': server.pool_usage,
                    'total_leases': server.total_leases,
                    'active_leases': server.active_leases,
                    'last_sync': server.last_sync_at.strftime('%Y-%m-%d %H:%M:%S') if server.last_sync_at else None,
                }
            })
        else:
            return Response(
                {'error': result.get('error', '同步失敗')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    except DHCPServer.DoesNotExist:
        return Response(
            {'error': 'DHCP Server 不存在'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f'同步配置失敗: {str(e)}', exc_info=True)
        return Response(
            {'error': f'同步失敗: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def dhcp_sync_logs(request, server_id):
    """
    同步指定 DHCP Server 的日誌到資料庫
    """
    try:
        from ..services import DHCPLogService
        
        server = DHCPServer.objects.get(id=server_id)
        log_service = DHCPLogService(server)
        
        # 執行同步
        limit = int(request.data.get('limit', 1000)) if request.data else 1000
        stats = log_service.sync_logs_to_db(limit=limit)
        
        logger.info(f'成功同步 Server {server.name} 的日誌: {stats}')
        
        return Response({
            'message': '日誌同步成功',
            'stats': stats,
            'server': {
                'name': server.name,
                'ip': server.ip_address,
            }
        })
    
    except DHCPServer.DoesNotExist:
        return Response(
            {'error': 'DHCP Server 不存在'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f'同步日誌失敗: {str(e)}', exc_info=True)
        return Response(
            {'error': f'同步失敗: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
