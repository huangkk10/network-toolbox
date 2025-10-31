from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.db.models import Count, Q, Sum, Avg
from django.utils import timezone
from datetime import timedelta
from .models import DHCPServer, DHCPLease, DHCPLog, NASConnectionLog, IPXEServer, IPXELog, IPXEStatistics, IPXENetworkQuality
from .serializers import DHCPServerSerializer, DHCPLeaseSerializer, DHCPLogSerializer, UserSerializer, NASConnectionLogSerializer, IPXEServerSerializer, IPXELogSerializer, IPXEStatisticsSerializer, IPXENetworkQualitySerializer
from .ipxe_service import IPXEService
import logging

logger = logging.getLogger(__name__)


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
            from .ssh_powershell_service import WindowsSSHPowerShellService
            from .services import DHCPLogService
            
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


@api_view(['GET'])
@permission_classes([AllowAny])
def dhcp_analytics_overview(request):
    """
    DHCP 分析 - 總覽統計
    支援單一 Server 或全部 Server 的統計
    """
    server_id = request.query_params.get('server', 'all')
    
    try:
        # 根據 server_id 篩選租約
        if server_id == 'all':
            leases = DHCPLease.objects.all()
            servers = DHCPServer.objects.all()
        else:
            leases = DHCPLease.objects.filter(server_id=server_id)
            servers = DHCPServer.objects.filter(id=server_id)
        
        # 基本統計
        total_leases = leases.count()
        active_leases = leases.filter(is_active=True).count()
        
        # 計算已過期租約（lease_end < 現在時間）
        now = timezone.now()
        expired_leases = leases.filter(lease_end__lt=now, is_active=False).count()
        
        # 計算 IP 使用率
        ip_utilization = 0
        if servers.exists():
            total_pool_usage = sum(s.pool_usage for s in servers)
            ip_utilization = total_pool_usage / servers.count() if servers.count() > 0 else 0
        
        # 計算趨勢（與昨天相比的變化百分比）
        yesterday = now - timedelta(days=1)
        yesterday_active = leases.filter(
            is_active=True,
            lease_start__lte=yesterday
        ).count()
        
        trend = 0
        if yesterday_active > 0:
            trend = ((active_leases - yesterday_active) / yesterday_active) * 100
        elif active_leases > 0:
            trend = 100
        
        return Response({
            'total_leases': total_leases,
            'active_leases': active_leases,
            'expired_leases': expired_leases,
            'ip_utilization': round(ip_utilization, 1),
            'trend': round(trend, 1),
        })
    
    except Exception as e:
        logger.error(f'獲取總覽統計失敗: {str(e)}', exc_info=True)
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def dhcp_analytics_trend(request):
    """
    DHCP 分析 - 租約趨勢（最近 7 天）
    """
    server_id = request.query_params.get('server', 'all')
    days = int(request.query_params.get('days', 7))
    
    try:
        # 準備日期範圍
        now = timezone.now()
        trend_data = []
        
        for i in range(days - 1, -1, -1):
            date = now - timedelta(days=i)
            date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            date_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # 根據 server_id 篩選
            if server_id == 'all':
                leases_on_date = DHCPLease.objects.filter(
                    lease_start__lte=date_end,
                    lease_end__gte=date_start
                )
            else:
                leases_on_date = DHCPLease.objects.filter(
                    server_id=server_id,
                    lease_start__lte=date_end,
                    lease_end__gte=date_start
                )
            
            # 統計當天的活躍和過期租約
            active_count = leases_on_date.filter(lease_end__gte=date_end).count()
            expired_count = leases_on_date.filter(lease_end__lt=date_end).count()
            
            trend_data.append({
                'date': date.strftime('%m/%d'),
                'active': active_count,
                'expired': expired_count,
                'total': active_count + expired_count,
            })
        
        return Response(trend_data)
    
    except Exception as e:
        logger.error(f'獲取趨勢資料失敗: {str(e)}', exc_info=True)
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def dhcp_analytics_status_distribution(request):
    """
    DHCP 分析 - 租約狀態分佈
    """
    server_id = request.query_params.get('server', 'all')
    
    try:
        if server_id == 'all':
            leases = DHCPLease.objects.all()
        else:
            leases = DHCPLease.objects.filter(server_id=server_id)
        
        now = timezone.now()
        
        # 統計各種狀態
        active_count = leases.filter(is_active=True, lease_end__gte=now).count()
        expired_count = leases.filter(lease_end__lt=now).count()
        released_count = leases.filter(is_active=False, lease_end__gte=now).count()
        
        return Response([
            {'name': '活躍中', 'value': active_count, 'color': '#52c41a'},
            {'name': '已過期', 'value': expired_count, 'color': '#faad14'},
            {'name': '已釋放', 'value': released_count, 'color': '#d9d9d9'},
        ])
    
    except Exception as e:
        logger.error(f'獲取狀態分佈失敗: {str(e)}', exc_info=True)
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def dhcp_analytics_recent_leases(request):
    """
    DHCP 分析 - 最近租約列表
    """
    server_id = request.query_params.get('server', 'all')
    limit = int(request.query_params.get('limit', 10))
    
    try:
        if server_id == 'all':
            leases = DHCPLease.objects.all()
        else:
            leases = DHCPLease.objects.filter(server_id=server_id)
        
        # 獲取最近的租約（按建立時間排序）
        recent_leases = leases.order_by('-created_at')[:limit]
        
        # 序列化資料
        leases_data = []
        for lease in recent_leases:
            leases_data.append({
                'key': lease.id,
                'ip': lease.ip_address,
                'mac': lease.mac_address,
                'hostname': lease.hostname or '-',
                'status': 'active' if lease.is_active else 'expired',
                'end_time': lease.lease_end.strftime('%Y-%m-%d %H:%M:%S') if lease.lease_end else '-',
            })
        
        return Response(leases_data)
    
    except Exception as e:
        logger.error(f'獲取最近租約失敗: {str(e)}', exc_info=True)
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def dhcp_sync_leases(request, server_id):
    """
    同步指定 DHCP Server 的租約資料
    支援 SSH + PowerShell 方式（Windows Server）
    """
    try:
        from .ssh_powershell_service import WindowsSSHPowerShellService
        
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
        from .services import LinuxDHCPConfigService
        
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


@api_view(['GET'])
@permission_classes([AllowAny])
def dhcp_analytics_logs(request):
    """
    DHCP 分析 - 日誌查看
    支援資料庫查詢（優先）和遠端 SSH 日誌（備用）
    
    參數:
        server: Server ID（必填，不支援 'all'）
        source: 'database'（預設）或 'remote'（SSH 即時查詢）
        page: 頁碼（從 1 開始）
        page_size: 每頁數量（預設 20）
        level: 日誌等級篩選（ALL, INFO, WARN, ERROR, DEBUG）
        keyword: 關鍵字篩選
        time_range: 快速時間範圍（1h, 6h, today, 1d, 3d, 7d）
        start_time: 自訂開始時間 (YYYY-MM-DD HH:mm:ss)
        end_time: 自訂結束時間 (YYYY-MM-DD HH:mm:ss)
    
    返回:
        {
            "logs": [...],
            "total": 總數,
            "page": 當前頁碼,
            "page_size": 每頁數量,
            "total_pages": 總頁數,
            "statistics": {
                "total": 總數,
                "info": INFO 數量,
                "warn": WARN 數量,
                "error": ERROR 數量
            }
        }
    """
    from .services import DHCPLogService
    from datetime import datetime, timedelta
    from django.utils import timezone
    
    server_id = request.query_params.get('server', None)
    source = request.query_params.get('source', 'database')  # database 或 remote
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 20))
    level = request.query_params.get('level', None)
    client_type = request.query_params.get('client_type', None)  # 新增：客戶端類型篩選
    keyword = request.query_params.get('keyword', None)
    time_range = request.query_params.get('time_range', None)
    start_time_str = request.query_params.get('start_time', None)
    end_time_str = request.query_params.get('end_time', None)
    
    # 驗證必要參數
    if not server_id or server_id == 'all':
        return Response(
            {'error': '請指定 DHCP Server ID'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        server = DHCPServer.objects.get(id=server_id)
        log_service = DHCPLogService(server)
        
        # 解析時間範圍
        start_time = None
        end_time = None
        
        if time_range:
            now = timezone.now()
            if time_range == '1h':
                start_time = now - timedelta(hours=1)
            elif time_range == '6h':
                start_time = now - timedelta(hours=6)
            elif time_range == 'today':
                start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif time_range == '1d':
                start_time = now - timedelta(days=1)
            elif time_range == '3d':
                start_time = now - timedelta(days=3)
            elif time_range == '7d':
                start_time = now - timedelta(days=7)
        
        # 自訂時間範圍（優先）
        if start_time_str:
            start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S')
        if end_time_str:
            end_time = datetime.strptime(end_time_str, '%Y-%m-%d %H:%M:%S')
        
        # 根據來源查詢日誌
        if source == 'database':
            # 從資料庫查詢（預設，速度快）
            result = log_service.get_db_logs(
                limit=page_size,
                page=page,
                level=level,
                client_type=client_type,  # 新增
                keyword=keyword,
                start_time=start_time,
                end_time=end_time
            )
            
            # 計算統計資訊
            from .models import DHCPLog
            from django.db.models import Q, Count
            
            queryset = DHCPLog.objects.filter(server=server)
            if level and level != 'ALL':
                queryset = queryset.filter(level=level)
            if client_type and client_type != 'ALL':  # 新增
                queryset = queryset.filter(client_type=client_type)
            if keyword:
                queryset = queryset.filter(
                    Q(message__icontains=keyword) | 
                    Q(event__icontains=keyword) |
                    Q(vendor_class__icontains=keyword) |  # 新增：搜尋 Vendor Class
                    Q(user_class__icontains=keyword)      # 新增：搜尋 User Class
                )
            if start_time:
                queryset = queryset.filter(timestamp__gte=start_time)
            if end_time:
                queryset = queryset.filter(timestamp__lte=end_time)
            
            stats = queryset.values('level').annotate(count=Count('id'))
            statistics = {
                'total': result['total'],
                'info': next((s['count'] for s in stats if s['level'] == 'INFO'), 0),
                'warn': next((s['count'] for s in stats if s['level'] == 'WARN'), 0),
                'error': next((s['count'] for s in stats if s['level'] == 'ERROR'), 0),
                'debug': next((s['count'] for s in stats if s['level'] == 'DEBUG'), 0),
            }
            
            result['statistics'] = statistics
            return Response(result)
        
        else:
            # 從遠端 SSH 查詢（備用，速度慢）
            logs = log_service.get_remote_logs(
                limit=page_size * page,  # SSH 模式下先讀取所有頁
                level=level,
                keyword=keyword,
                start_time=start_time_str,
                end_time=end_time_str
            )
            
            # 手動分頁
            total = len(logs)
            total_pages = (total + page_size - 1) // page_size
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            page_logs = logs[start_idx:end_idx]
            
            # 計算統計資訊
            statistics = {
                'total': total,
                'info': len([l for l in logs if l['level'] == 'INFO']),
                'warn': len([l for l in logs if l['level'] == 'WARN']),
                'error': len([l for l in logs if l['level'] == 'ERROR']),
                'debug': len([l for l in logs if l['level'] == 'DEBUG']),
            }
            
            return Response({
                'logs': page_logs,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages,
                'statistics': statistics,
            })
    
    except DHCPServer.DoesNotExist:
        return Response(
            {'error': 'DHCP Server 不存在'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f'獲取日誌失敗: {str(e)}', exc_info=True)
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def dhcp_lease_lookup(request):
    """
    根據 MAC 地址查詢租約資訊（用於日誌客戶端類型識別）
    
    參數:
        mac: MAC 地址 (格式: xx:xx:xx:xx:xx:xx 或 xx-xx-xx-xx-xx-xx)
    
    返回:
        {
            "mac": "b0:25:2b:0f:a9:45",
            "ip": "192.168.7.89",
            "hostname": "desktop-win11",
            "is_active": true
        }
    """
    mac = request.query_params.get('mac', None)
    
    if not mac:
        return Response(
            {'error': '請提供 MAC 地址'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # 標準化 MAC 地址格式（統一使用冒號分隔）
        mac = mac.strip().lower().replace('-', ':')
        
        # 查詢租約（優先查詢活躍租約）
        lease = DHCPLease.objects.filter(mac_address__iexact=mac).first()
        
        if not lease:
            return Response(
                {
                    'mac': mac,
                    'hostname': None,
                    'ip': None,
                    'is_active': False,
                    'found': False
                }
            )
        
        return Response({
            'mac': lease.mac_address,
            'ip': lease.ip_address,
            'hostname': lease.hostname,
            'is_active': lease.is_active,
            'lease_end': lease.lease_end.strftime('%Y-%m-%d %H:%M:%S') if lease.lease_end else None,
            'found': True
        })
    
    except Exception as e:
        logger.error(f'MAC 地址查詢失敗 ({mac}): {str(e)}', exc_info=True)
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def dhcp_sync_logs(request, server_id):
    """
    同步指定 DHCP Server 的日誌到資料庫
    """
    try:
        from .services import DHCPLogService
        
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


@api_view(['GET'])
@permission_classes([AllowAny])
def dhcp_analytics_statistics(request):
    """
    DHCP 分析 - 統計數據（StatisticsTab）
    提供租約增長趨勢、每日活躍數、Top 客戶端、製造商分佈、每日摘要
    
    參數:
        server: Server ID 或 'all'（預設）
        days: 統計天數（預設 7 天）
    """
    from collections import Counter
    from datetime import datetime, timedelta
    
    server_id = request.query_params.get('server', 'all')
    days = int(request.query_params.get('days', 7))
    
    try:
        # 篩選租約
        if server_id == 'all':
            leases = DHCPLease.objects.all()
        else:
            leases = DHCPLease.objects.filter(server_id=server_id)
        
        now = timezone.now()
        
        # 1. 租約增長趨勢（最近 N 天的租約總數）
        growth_data = []
        for i in range(days - 1, -1, -1):
            date = now - timedelta(days=i)
            date_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # 統計該日期之前建立的所有租約
            total_count = leases.filter(created_at__lte=date_end).count()
            
            growth_data.append({
                'date': date.strftime('%m/%d'),
                'count': total_count,
            })
        
        # 2. 每日活躍租約數（按星期幾分組）
        daily_active_data = []
        weekday_names = ['週一', '週二', '週三', '週四', '週五', '週六', '週日']
        
        # 統計最近 7 天，按星期幾分組
        weekday_counts = {i: [] for i in range(7)}  # 0=週一, 6=週日
        
        for i in range(6, -1, -1):  # 最近 7 天
            date = now - timedelta(days=i)
            date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            date_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
            weekday = date.weekday()  # 0=週一, 6=週日
            
            # 統計該天的活躍租約
            active_count = leases.filter(
                lease_start__lte=date_end,
                lease_end__gte=date_start
            ).count()
            
            weekday_counts[weekday].append(active_count)
        
        # 計算每個星期幾的平均值
        for weekday in range(7):
            counts = weekday_counts[weekday]
            avg_count = sum(counts) / len(counts) if counts else 0
            daily_active_data.append({
                'day': weekday_names[weekday],
                'count': int(avg_count),
            })
        
        # 3. Top 10 活躍客戶端（依據 hostname 出現次數）
        top_clients_data = []
        
        # 統計所有有主機名稱的租約
        hostnames = leases.exclude(hostname='').exclude(hostname__isnull=True).values_list('hostname', flat=True)
        hostname_counter = Counter(hostnames)
        
        # 取前 10 名
        for hostname, count in hostname_counter.most_common(10):
            top_clients_data.append({
                'hostname': hostname,
                'count': count,
            })
        
        # 4. 設備製造商分佈（根據 MAC 地址前綴）
        from .utils.mac_vendor import get_vendor_from_mac
        
        vendor_counter = Counter()
        mac_addresses = leases.exclude(mac_address='').exclude(mac_address__isnull=True).values_list('mac_address', flat=True)
        
        for mac in mac_addresses:
            vendor = get_vendor_from_mac(mac)
            if vendor and vendor != 'Unknown':
                vendor_counter[vendor] += 1
            else:
                vendor_counter['其他'] += 1
        
        # 取前 5 名，其餘歸為「其他」
        vendor_data = []
        colors = ['#2196f3', '#52c41a', '#faad14', '#ff4d4f', '#d9d9d9']
        
        top_vendors = vendor_counter.most_common(4)  # 只取前 4 名
        other_count = sum(count for vendor, count in vendor_counter.items() if vendor not in [v[0] for v in top_vendors])
        
        for i, (vendor, count) in enumerate(top_vendors):
            vendor_data.append({
                'name': vendor,
                'value': count,
                'color': colors[i] if i < len(colors) else '#d9d9d9',
            })
        
        if other_count > 0:
            vendor_data.append({
                'name': '其他',
                'value': other_count,
                'color': colors[4],
            })
        
        # 5. 每日統計摘要（最近 5 天）
        daily_summary = []
        
        for i in range(4, -1, -1):  # 最近 5 天
            date = now - timedelta(days=i)
            date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            date_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # 統計該天的租約狀態
            total = leases.filter(created_at__lte=date_end).count()
            active = leases.filter(
                lease_start__lte=date_end,
                lease_end__gte=date_start,
                is_active=True
            ).count()
            expired = leases.filter(
                lease_end__lt=date_end
            ).count()
            released = leases.filter(
                is_active=False,
                lease_end__gte=date_start,
                lease_end__lte=date_end
            ).count()
            
            # 計算 IP 使用率（如果有 server 資訊）
            utilization = 0
            if server_id != 'all':
                try:
                    server = DHCPServer.objects.get(id=server_id)
                    utilization = server.pool_usage
                except DHCPServer.DoesNotExist:
                    pass
            else:
                # 所有 server 的平均使用率
                servers = DHCPServer.objects.all()
                if servers.exists():
                    total_usage = sum(s.pool_usage for s in servers)
                    utilization = total_usage / servers.count()
            
            daily_summary.append({
                'key': str(5 - i),
                'date': date.strftime('%Y-%m-%d'),
                'total': total,
                'active': active,
                'expired': expired,
                'released': released,
                'utilization': f'{utilization:.1f}%',
            })
        
        return Response({
            'growth_data': growth_data,
            'daily_active_data': daily_active_data,
            'top_clients_data': top_clients_data,
            'vendor_data': vendor_data,
            'daily_summary': daily_summary,
        })
    
    except Exception as e:
        logger.error(f'獲取統計資料失敗: {str(e)}', exc_info=True)
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class NASConnectionLogViewSet(viewsets.ModelViewSet):
    """NAS 連線記錄 API ViewSet"""
    queryset = NASConnectionLog.objects.all()
    serializer_class = NASConnectionLogSerializer
    permission_classes = [AllowAny]
    pagination_class = None  # 禁用分頁
    
    def get_queryset(self):
        """過濾查詢，只返回最近2週的數據"""
        queryset = NASConnectionLog.objects.all()
        
        # 時間範圍過濾
        days = self.request.query_params.get('days', None)
        if days:
            try:
                days_int = int(days)
                start_time = timezone.now() - timedelta(days=days_int)
                queryset = queryset.filter(timestamp__gte=start_time)
            except ValueError:
                pass
        else:
            # 默認返回最近2週
            start_time = timezone.now() - timedelta(days=14)
            queryset = queryset.filter(timestamp__gte=start_time)
        
        # 狀態過濾
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-timestamp')
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """NAS 連線統計資料"""
        try:
            # 時間範圍
            days = int(request.query_params.get('days', 14))
            start_time = timezone.now() - timedelta(days=days)
            
            logs = NASConnectionLog.objects.filter(timestamp__gte=start_time)
            
            # 基本統計
            total_records = logs.count()
            success_count = logs.filter(status='success').count()
            failed_count = logs.filter(status='failed').count()
            success_rate = (success_count / total_records * 100) if total_records > 0 else 0
            
            # 平均效能
            avg_response_time = logs.filter(
                status='success', 
                response_time__isnull=False
            ).aggregate(Avg('response_time'))['response_time__avg'] or 0
            
            avg_upload_speed = logs.filter(
                status='success',
                upload_speed__isnull=False
            ).aggregate(Avg('upload_speed'))['upload_speed__avg'] or 0
            
            avg_download_speed = logs.filter(
                status='success',
                download_speed__isnull=False
            ).aggregate(Avg('download_speed'))['download_speed__avg'] or 0
            
            # 每日統計（最近7天）
            daily_stats = []
            for i in range(6, -1, -1):
                day_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=i)
                day_end = day_start + timedelta(days=1)
                
                day_logs = logs.filter(timestamp__gte=day_start, timestamp__lt=day_end)
                day_total = day_logs.count()
                day_success = day_logs.filter(status='success').count()
                day_failed = day_logs.filter(status='failed').count()
                
                daily_stats.append({
                    'date': day_start.strftime('%Y-%m-%d'),
                    'total': day_total,
                    'success': day_success,
                    'failed': day_failed,
                    'success_rate': (day_success / day_total * 100) if day_total > 0 else 0,
                })
            
            # 每小時統計（最近24小時）
            hourly_stats = []
            for i in range(23, -1, -1):
                hour_start = timezone.now().replace(minute=0, second=0, microsecond=0) - timedelta(hours=i)
                hour_end = hour_start + timedelta(hours=1)
                
                hour_logs = logs.filter(timestamp__gte=hour_start, timestamp__lt=hour_end)
                hour_total = hour_logs.count()
                hour_success = hour_logs.filter(status='success').count()
                
                hourly_stats.append({
                    'hour': hour_start.strftime('%Y-%m-%d %H:00'),
                    'total': hour_total,
                    'success': hour_success,
                    'failed': hour_total - hour_success,
                })
            
            # 速度趨勢（根據時間範圍動態調整）
            speed_trends = []
            
            # 根據天數決定採樣間隔
            if days <= 1:
                # 1 天內：每 5 分鐘一個數據點
                interval_minutes = 5
                num_points = int((days * 24 * 60) / interval_minutes)
            elif days <= 3:
                # 3 天內：每 15 分鐘一個數據點
                interval_minutes = 15
                num_points = int((days * 24 * 60) / interval_minutes)
            elif days <= 7:
                # 7 天內：每小時一個數據點
                interval_minutes = 60
                num_points = int((days * 24 * 60) / interval_minutes)
            else:
                # 7 天以上：每 3 小時一個數據點
                interval_minutes = 180
                num_points = int((days * 24 * 60) / interval_minutes)
            
            # 生成速度趨勢數據
            for i in range(num_points - 1, -1, -1):
                period_end = timezone.now() - timedelta(minutes=i * interval_minutes)
                period_start = period_end - timedelta(minutes=interval_minutes)
                
                period_logs = logs.filter(
                    timestamp__gte=period_start,
                    timestamp__lt=period_end,
                    status='success'
                )
                
                # 計算該時段的平均速度
                avg_upload = period_logs.filter(
                    upload_speed__isnull=False
                ).aggregate(Avg('upload_speed'))['upload_speed__avg']
                
                avg_download = period_logs.filter(
                    download_speed__isnull=False
                ).aggregate(Avg('download_speed'))['download_speed__avg']
                
                # 格式化時間標籤
                if interval_minutes < 60:
                    time_label = period_end.strftime('%m-%d %H:%M')
                else:
                    time_label = period_end.strftime('%m-%d %H:00')
                
                speed_trends.append({
                    'time': time_label,
                    'upload_speed': round(avg_upload, 2) if avg_upload else None,
                    'download_speed': round(avg_download, 2) if avg_download else None,
                })
            
            return Response({
                'total_records': total_records,
                'success_count': success_count,
                'failed_count': failed_count,
                'success_rate': round(success_rate, 2),
                'avg_response_time': round(avg_response_time, 2),
                'avg_upload_speed': round(avg_upload_speed, 2),
                'avg_download_speed': round(avg_download_speed, 2),
                'daily_stats': daily_stats,
                'hourly_stats': hourly_stats,
                'speed_trends': speed_trends,
            })
            
        except Exception as e:
            logger.error(f'獲取 NAS 統計資料失敗: {str(e)}', exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ========== IPXE Management ViewSets ==========

class IPXEServerViewSet(viewsets.ModelViewSet):
    """IPXE 伺服器管理 API ViewSet"""
    queryset = IPXEServer.objects.all()
    serializer_class = IPXEServerSerializer
    permission_classes = [AllowAny]  # 開發階段允許所有請求，生產環境應改為 IsAuthenticated
    pagination_class = None  # 禁用分頁

    def list(self, request, *args, **kwargs):
        """列出所有 IPXE 伺服器"""
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            logger.info(f'成功獲取 {len(serializer.data)} 個 IPXE 伺服器')
            return Response(serializer.data)
        except Exception as e:
            logger.error(f'獲取 IPXE 伺服器列表失敗: {str(e)}', exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def create(self, request, *args, **kwargs):
        """創建新的 IPXE 伺服器"""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            logger.info(f"成功創建 IPXE 伺服器: {serializer.data['name']}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f'創建 IPXE 伺服器失敗: {str(e)}', exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def update(self, request, *args, **kwargs):
        """更新 IPXE 伺服器資訊"""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            logger.info(f"成功更新 IPXE 伺服器: {serializer.data['name']}")
            return Response(serializer.data)
        except Exception as e:
            logger.error(f'更新 IPXE 伺服器失敗: {str(e)}', exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def destroy(self, request, *args, **kwargs):
        """刪除 IPXE 伺服器"""
        try:
            instance = self.get_object()
            server_name = instance.name
            self.perform_destroy(instance)
            logger.info(f'成功刪除 IPXE 伺服器: {server_name}')
            return Response(
                {'message': f'成功刪除 IPXE 伺服器: {server_name}'},
                status=status.HTTP_204_NO_CONTENT
            )
        except Exception as e:
            logger.error(f'刪除 IPXE 伺服器失敗: {str(e)}', exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class IPXELogViewSet(viewsets.ReadOnlyModelViewSet):
    """IPXE 日誌查詢 API ViewSet（只讀）- 從 DHCPLog 表讀取 iPXE 相關日誌"""
    queryset = DHCPLog.objects.filter(
        client_type__in=['PXE', 'iPXE', 'WinPE']
    ).order_by('-timestamp')
    serializer_class = DHCPLogSerializer  # 使用 DHCPLogSerializer
    permission_classes = [AllowAny]
    pagination_class = None  # 禁用分頁

    def get_queryset(self):
        """支援篩選參數"""
        # 基礎查詢：只查詢 iPXE 相關的日誌（PXE, iPXE, WinPE）
        queryset = DHCPLog.objects.filter(
            client_type__in=['PXE', 'iPXE', 'WinPE']
        ).select_related('server')
        
        # 依 server_id 篩選
        server_id = self.request.query_params.get('server_id', None)
        if server_id and server_id != 'all':
            queryset = queryset.filter(server_id=server_id)
        
        # 依 log_type 篩選（映射到 client_type）
        log_type = self.request.query_params.get('log_type', None)
        if log_type:
            # log_type='BOOT' -> client_type in ['PXE', 'iPXE', 'WinPE']
            # log_type='MAC' -> 暫時不篩選（DHCPLog 沒有 MAC 管理日誌）
            if log_type == 'BOOT':
                queryset = queryset.filter(client_type__in=['PXE', 'iPXE', 'WinPE'])
        
        # 搜尋功能（支援 message、raw）
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(message__icontains=search) |
                Q(raw__icontains=search)
            )
        
        # 依時間範圍篩選（預設 7 天）
        days = self.request.query_params.get('days', 7)
        try:
            days = int(days)
            cutoff_time = timezone.now() - timedelta(days=days)
            queryset = queryset.filter(timestamp__gte=cutoff_time)
        except ValueError:
            pass
        
        # 先排序再限制數量（重要：必須先 order_by 再切片）
        queryset = queryset.order_by('-timestamp')
        
        # 限制返回數量（防止一次返回過多資料）
        limit = self.request.query_params.get('limit', None)
        if limit:
            try:
                limit = int(limit)
                queryset = queryset[:limit]
            except ValueError:
                pass
        
        return queryset

    def list(self, request, *args, **kwargs):
        """列出 IPXE 日誌 - 從 DHCPLog 讀取並轉換格式"""
        try:
            queryset = self.get_queryset()
            
            # 轉換 DHCPLog 格式為前端需要的格式
            logs_data = []
            for log in queryset:
                # 提取 IP 和 MAC（從 message 或 raw 中）
                import re
                client_ip = ''
                mac_address = ''
                
                # 嘗試從 message 提取 IP
                ip_match = re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', log.message)
                if ip_match:
                    client_ip = ip_match.group(0)
                
                # 嘗試從 raw 提取 MAC 地址
                mac_match = re.search(r'\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b', log.raw)
                if mac_match:
                    mac_address = mac_match.group(0)
                
                logs_data.append({
                    'id': log.id,
                    'timestamp': log.timestamp,
                    'log_type': 'BOOT',  # iPXE 相關都歸類為 BOOT
                    'action': log.client_type.lower(),  # PXE, iPXE, WinPE
                    'client_ip': client_ip,
                    'mac_address': mac_address,
                    'status_code': 200 if log.level == 'INFO' else 500,  # 根據 level 決定狀態碼
                    'raw': log.raw,
                    'server_ip': log.server.ip_address,
                    'server_name': log.server.name,
                    'message': log.message,
                    'client_type': log.client_type,
                    'boot_stage': log.boot_stage,
                })
            
            logger.info(f'成功獲取 {len(logs_data)} 條 IPXE 日誌（從 DHCPLog）')
            return Response(logs_data)
        except Exception as e:
            logger.error(f'獲取 IPXE 日誌失敗: {str(e)}', exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class IPXENetworkQualityViewSet(viewsets.ModelViewSet):
    """IPXE 網路品質監控 API ViewSet"""
    queryset = IPXENetworkQuality.objects.all()
    serializer_class = IPXENetworkQualitySerializer
    permission_classes = [AllowAny]
    pagination_class = None  # 禁用分頁
    
    def get_queryset(self):
        """過濾查詢，支援時間範圍和伺服器過濾"""
        queryset = IPXENetworkQuality.objects.all()
        
        # 依 server_id 篩選
        server_id = self.request.query_params.get('server_id', None)
        if server_id:
            queryset = queryset.filter(server_id=server_id)
        
        # 依時間範圍篩選（預設 7 天）
        days = self.request.query_params.get('days', 7)
        try:
            days = int(days)
            cutoff_time = timezone.now() - timedelta(days=days)
            queryset = queryset.filter(timestamp__gte=cutoff_time)
        except ValueError:
            pass
        
        # 依狀態篩選
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-timestamp')
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """IPXE 網路品質統計資料"""
        try:
            # 時間範圍
            days = int(request.query_params.get('days', 7))
            start_time = timezone.now() - timedelta(days=days)
            
            # 伺服器過濾
            server_id = request.query_params.get('server_id', None)
            
            logs = IPXENetworkQuality.objects.filter(timestamp__gte=start_time)
            if server_id:
                logs = logs.filter(server_id=server_id)
            
            # 基本統計
            total_records = logs.count()
            success_count = logs.filter(status='success').count()
            failed_count = logs.filter(status='failed').count()
            partial_count = logs.filter(status='partial').count()
            success_rate = (success_count / total_records * 100) if total_records > 0 else 0
            
            # 平均網路指標（計算所有有資料的記錄，不只是 success）
            avg_ping_latency = logs.filter(
                ping_latency__isnull=False
            ).aggregate(Avg('ping_latency'))['ping_latency__avg'] or 0
            
            avg_http_response_time = logs.filter(
                http_response_time__isnull=False
            ).aggregate(Avg('http_response_time'))['http_response_time__avg'] or 0
            
            avg_ssh_response_time = logs.filter(
                ssh_response_time__isnull=False
            ).aggregate(Avg('ssh_response_time'))['ssh_response_time__avg'] or 0
            
            avg_download_speed = logs.filter(
                download_speed__isnull=False
            ).aggregate(Avg('download_speed'))['download_speed__avg'] or 0
            
            avg_packet_loss = logs.filter(
                ping_packet_loss__isnull=False
            ).aggregate(Avg('ping_packet_loss'))['ping_packet_loss__avg'] or 0
            
            # 每日統計
            daily_stats = []
            for i in range(6, -1, -1):
                day_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=i)
                day_end = day_start + timedelta(days=1)
                
                day_logs = logs.filter(timestamp__gte=day_start, timestamp__lt=day_end)
                day_total = day_logs.count()
                day_success = day_logs.filter(status='success').count()
                day_failed = day_logs.filter(status='failed').count()
                day_partial = day_logs.filter(status='partial').count()
                
                # 當日平均延遲
                day_avg_ping = day_logs.filter(
                    ping_latency__isnull=False
                ).aggregate(Avg('ping_latency'))['ping_latency__avg']
                
                daily_stats.append({
                    'date': day_start.strftime('%Y-%m-%d'),
                    'total': day_total,
                    'success': day_success,
                    'failed': day_failed,
                    'partial': day_partial,
                    'success_rate': (day_success / day_total * 100) if day_total > 0 else 0,
                    'avg_ping_latency': round(day_avg_ping, 2) if day_avg_ping else None,
                })
            
            # 每小時統計（最近24小時）
            hourly_stats = []
            for i in range(23, -1, -1):
                hour_start = timezone.now().replace(minute=0, second=0, microsecond=0) - timedelta(hours=i)
                hour_end = hour_start + timedelta(hours=1)
                
                hour_logs = logs.filter(timestamp__gte=hour_start, timestamp__lt=hour_end)
                hour_total = hour_logs.count()
                hour_success = hour_logs.filter(status='success').count()
                
                # 當小時平均延遲
                hour_avg_ping = hour_logs.filter(
                    ping_latency__isnull=False
                ).aggregate(Avg('ping_latency'))['ping_latency__avg']
                
                hourly_stats.append({
                    'hour': hour_start.strftime('%Y-%m-%d %H:00'),
                    'total': hour_total,
                    'success': hour_success,
                    'failed': hour_total - hour_success,
                    'avg_ping_latency': round(hour_avg_ping, 2) if hour_avg_ping else None,
                })
            
            # 網路品質趨勢（根據時間範圍動態調整）
            quality_trends = []
            
            # 根據天數決定採樣間隔
            if days <= 1:
                interval_minutes = 5  # 1 天內：每 5 分鐘
                num_points = int((days * 24 * 60) / interval_minutes)
            elif days <= 3:
                interval_minutes = 15  # 3 天內：每 15 分鐘
                num_points = int((days * 24 * 60) / interval_minutes)
            elif days <= 7:
                interval_minutes = 60  # 7 天內：每小時
                num_points = int((days * 24 * 60) / interval_minutes)
            else:
                interval_minutes = 180  # 7 天以上：每 3 小時
                num_points = int((days * 24 * 60) / interval_minutes)
            
            # 生成品質趨勢數據
            for i in range(num_points - 1, -1, -1):
                period_end = timezone.now() - timedelta(minutes=i * interval_minutes)
                period_start = period_end - timedelta(minutes=interval_minutes)
                
                period_logs = logs.filter(
                    timestamp__gte=period_start,
                    timestamp__lt=period_end
                )
                
                # 計算該時段的平均指標
                avg_ping = period_logs.filter(
                    ping_latency__isnull=False
                ).aggregate(Avg('ping_latency'))['ping_latency__avg']
                
                avg_http = period_logs.filter(
                    http_response_time__isnull=False
                ).aggregate(Avg('http_response_time'))['http_response_time__avg']
                
                avg_ssh = period_logs.filter(
                    ssh_response_time__isnull=False
                ).aggregate(Avg('ssh_response_time'))['ssh_response_time__avg']
                
                avg_dl_speed = period_logs.filter(
                    download_speed__isnull=False
                ).aggregate(Avg('download_speed'))['download_speed__avg']
                
                avg_loss = period_logs.filter(
                    ping_packet_loss__isnull=False
                ).aggregate(Avg('ping_packet_loss'))['ping_packet_loss__avg']
                
                # 格式化時間標籤
                if interval_minutes < 60:
                    time_label = period_end.strftime('%m-%d %H:%M')
                else:
                    time_label = period_end.strftime('%m-%d %H:00')
                
                quality_trends.append({
                    'time': time_label,
                    'ping_latency': round(avg_ping, 2) if avg_ping else None,
                    'http_response_time': round(avg_http, 2) if avg_http else None,
                    'ssh_response_time': round(avg_ssh, 2) if avg_ssh else None,
                    'download_speed': round(avg_dl_speed, 2) if avg_dl_speed else None,
                    'packet_loss': round(avg_loss, 2) if avg_loss else None,
                })
            
            # 最新狀態
            latest_log = logs.order_by('-timestamp').first()
            latest_status = None
            if latest_log:
                latest_status = {
                    'timestamp': latest_log.timestamp,
                    'status': latest_log.status,
                    'ping_latency': latest_log.ping_latency,
                    'ping_packet_loss': latest_log.ping_packet_loss,
                    'http_response_time': latest_log.http_response_time,
                    'http_status_code': latest_log.http_status_code,
                    'ssh_response_time': latest_log.ssh_response_time,
                    'ssh_connected': latest_log.ssh_connected,
                    'download_speed': latest_log.download_speed,
                    'error_message': latest_log.error_message,
                }
            
            return Response({
                'summary': {
                    'total_records': total_records,
                    'success_count': success_count,
                    'failed_count': failed_count,
                    'partial_count': partial_count,
                    'success_rate': round(success_rate, 2),
                    'avg_ping_latency': round(avg_ping_latency, 2),
                    'avg_http_response_time': round(avg_http_response_time, 2),
                    'avg_ssh_response_time': round(avg_ssh_response_time, 2),
                    'avg_download_speed': round(avg_download_speed, 2),
                    'avg_packet_loss': round(avg_packet_loss, 2),
                },
                'daily_stats': daily_stats,
                'hourly_stats': hourly_stats,
                'quality_trends': quality_trends,
                'latest_status': latest_status,
            })
            
        except Exception as e:
            logger.error(f'獲取 IPXE 網路品質統計失敗: {str(e)}', exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['POST'])
@permission_classes([AllowAny])
def ipxe_sync_logs(request, server_id):
    """
    手動同步指定 IPXE 伺服器的日誌
    POST /api/ipxe-servers/<server_id>/sync-logs/
    Body (可選): { "limit": 1000 }
    """
    try:
        # 獲取 IPXE 伺服器
        try:
            server = IPXEServer.objects.get(pk=server_id)
        except IPXEServer.DoesNotExist:
            logger.error(f'IPXE 伺服器不存在: ID={server_id}')
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


@api_view(['GET'])
@permission_classes([AllowAny])
def ipxe_analytics_overview(request):
    """
    獲取 IPXE 分析總覽資料
    GET /api/ipxe-analytics/overview/
    Query Parameters (可選):
    - days: 統計天數（預設 7）
    - server_id: 指定伺服器 ID（預設全部）
    
    註：此 API 從 DHCPLog 表讀取 client_type 為 iPXE/PXE/WinPE 的記錄
    """
    try:
        # 獲取參數
        days = int(request.query_params.get('days', 7))
        server_id = request.query_params.get('server_id', None)
        
        cutoff_time = timezone.now() - timedelta(days=days)
        
        # 基礎查詢：從 DHCPLog 表讀取 iPXE 相關的日誌
        # client_type 包含：'PXE', 'iPXE', 'WinPE'
        logs_query = DHCPLog.objects.filter(
            timestamp__gte=cutoff_time,
            client_type__in=['PXE', 'iPXE', 'WinPE']
        )
        
        if server_id:
            logs_query = logs_query.filter(server_id=server_id)
        
        # 1. 總體統計
        total_logs = logs_query.count()
        # MAC 管理請求：根據訊息內容判斷（包含 MAC 地址相關操作）
        mac_logs_count = logs_query.filter(message__icontains='MAC').count()
        # BOOT 請求：PXE、iPXE、WinPE 類型的日誌
        boot_logs_count = logs_query.count()  # 所有 iPXE 相關日誌都視為 BOOT 請求
        
        # 2. MAC 操作統計（從訊息中分析）
        mac_set_count = logs_query.filter(message__icontains='MAC').filter(
            Q(message__icontains='set') | Q(message__icontains='add') | Q(message__icontains='register')
        ).count()
        mac_get_count = logs_query.filter(message__icontains='MAC').filter(
            Q(message__icontains='get') | Q(message__icontains='query') | Q(message__icontains='request')
        ).count()
        
        # 3. IPXE 啟動檔案統計（從訊息中提取 BOOT 文件資訊）
        # 統計不同 client_type 的分佈
        boot_files_data = logs_query.values('client_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # 轉換為前端期望的格式
        boot_logs = [
            {'file_requested': item['client_type'], 'count': item['count']} 
            for item in boot_files_data
        ]
        
        # 4. 每日統計（過去 N 天）
        daily_stats = []
        for i in range(days):
            day_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=i)
            day_end = day_start + timedelta(days=1)
            
            day_logs = logs_query.filter(timestamp__gte=day_start, timestamp__lt=day_end)
            # MAC 相關日誌
            mac_count = day_logs.filter(message__icontains='MAC').count()
            # BOOT 相關日誌（所有 iPXE 相關日誌）
            boot_count = day_logs.count()
            
            daily_stats.append({
                'date': day_start.date().isoformat(),
                'total_logs': day_logs.count(),
                'mac_logs': mac_count,      # 舊欄位名稱（兼容）
                'boot_logs': boot_count,    # 舊欄位名稱（兼容）
                'mac_count': mac_count,     # 前端圖表期望的欄位
                'boot_count': boot_count,   # 前端圖表期望的欄位
            })
        
        daily_stats.reverse()  # 從早到晚排序
        
        # 5. 每小時統計（過去 24 小時）
        hourly_stats = []
        for i in range(24):
            hour_start = timezone.now().replace(minute=0, second=0, microsecond=0) - timedelta(hours=i)
            hour_end = hour_start + timedelta(hours=1)
            
            hour_logs = logs_query.filter(timestamp__gte=hour_start, timestamp__lt=hour_end)
            
            hourly_stats.append({
                'hour': hour_start.strftime('%Y-%m-%d %H:00'),
                'total_logs': hour_logs.count(),
                'mac_logs': hour_logs.filter(message__icontains='MAC').count(),
                'boot_logs': hour_logs.count(),
            })
        
        hourly_stats.reverse()  # 從早到晚排序
        
        # 6. 伺服器統計（使用 DHCP Server，因為資料在 DHCPLog 表）
        server_stats = []
        # 獲取唯一的伺服器 ID（使用 set 去重，因為 PostgreSQL 的 DISTINCT 在有 ORDER BY 時會失效）
        unique_server_ids = set(logs_query.values_list('server__id', flat=True))
        
        from .models import DHCPServer
        for sid in unique_server_ids:
            server_logs = logs_query.filter(server_id=sid)
            
            # 獲取伺服器資訊
            try:
                server = DHCPServer.objects.get(id=sid)
                server_name = server.name
                server_ip = server.ip_address
            except DHCPServer.DoesNotExist:
                server_name = f'Server {sid}'
                server_ip = 'N/A'
            
            server_stats.append({
                'server_id': sid,
                'server_name': server_name,
                'server_ip': server_ip,
                'total_logs': server_logs.count(),
                'mac_logs': server_logs.filter(message__icontains='MAC').count(),
                'boot_logs': server_logs.count(),
                'last_sync': None,  # DHCPLog 沒有 last_sync_at 欄位
            })
        
        # 7. Top 10 活躍 MAC 地址（從 message 中提取）
        # 由於 DHCPLog 的 MAC 地址在 message 中，暫時返回空陣列
        # 未來可以考慮添加專門的 MAC 欄位或使用正則表達式提取
        top_mac_addresses = []
        
        logger.info(f'成功獲取 IPXE 分析資料: days={days}, total_logs={total_logs}, iPXE={logs_query.filter(client_type="iPXE").count()}, PXE={logs_query.filter(client_type="PXE").count()}, WinPE={logs_query.filter(client_type="WinPE").count()}')
        
        return Response({
            'summary': {
                'total_servers': len(server_stats),  # 有 iPXE 日誌的伺服器數量
                'total_logs': total_logs,
                'mac_logs': mac_logs_count,
                'boot_logs': boot_logs_count,
                'mac_set_operations': mac_set_count,
                'mac_get_operations': mac_get_count,
                'time_range_days': days,
            },
            'daily_trends': daily_stats,              # 前端期望的欄位名稱
            'log_type_distribution': {                # 前端期望的對象格式
                'MAC': mac_logs_count,
                'BOOT': boot_logs_count,
            },
            'top_mac_addresses': top_mac_addresses,   # Top 10 MAC 地址
            'recent_boot_files': boot_logs,           # 前端期望的欄位名稱
            'boot_files': boot_logs,                  # 保留舊欄位名稱（兼容）
            'daily_stats': daily_stats,               # 保留舊欄位名稱（兼容）
            'hourly_stats': hourly_stats,
            'server_stats': server_stats,
        })
        
    except Exception as e:
        logger.error(f'獲取 IPXE 分析資料失敗: {str(e)}', exc_info=True)
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def ipxe_analytics_statistics(request):
    """
    獲取 IPXE 統計分析資料（用於統計分析頁面）
    GET /api/ipxe-analytics/statistics/
    Query Parameters:
    - start_date: 開始日期 (YYYY-MM-DD)
    - end_date: 結束日期 (YYYY-MM-DD)
    - granularity: 時間粒度 (hourly/daily)，預設 hourly
    - server_id: 指定伺服器 ID（可選）
    """
    try:
        # 獲取參數
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        granularity = request.query_params.get('granularity', 'hourly')
        server_id = request.query_params.get('server_id', None)
        
        # 解析日期
        if start_date_str and end_date_str:
            from datetime import datetime
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            # 設定為當天結束時間
            end_date = end_date.replace(hour=23, minute=59, second=59)
            # 轉換為 timezone-aware
            start_date = timezone.make_aware(start_date)
            end_date = timezone.make_aware(end_date)
        else:
            # 預設過去 7 天
            end_date = timezone.now()
            start_date = end_date - timedelta(days=7)
        
        # 基礎查詢
        logs_query = IPXELog.objects.filter(timestamp__gte=start_date, timestamp__lte=end_date)
        
        if server_id and server_id != 'all':
            logs_query = logs_query.filter(server_id=server_id)
        
        # 1. 總體統計
        total_logs = logs_query.count()
        mac_logs_count = logs_query.filter(log_type='MAC').count()
        boot_logs_count = logs_query.filter(log_type='BOOT').count()
        mac_set_count = logs_query.filter(log_type='MAC', action='set_mac').count()
        mac_get_count = logs_query.filter(log_type='MAC', action='get_mac').count()
        
        # 2. 時間序列統計
        time_series = []
        
        if granularity == 'hourly':
            # 每小時統計
            hours = int((end_date - start_date).total_seconds() / 3600)
            for i in range(hours + 1):
                hour_start = start_date + timedelta(hours=i)
                hour_end = hour_start + timedelta(hours=1)
                
                hour_logs = logs_query.filter(timestamp__gte=hour_start, timestamp__lt=hour_end)
                
                time_series.append({
                    'time': hour_start.strftime('%Y-%m-%d %H:00'),
                    'total': hour_logs.count(),
                    'mac': hour_logs.filter(log_type='MAC').count(),
                    'boot': hour_logs.filter(log_type='BOOT').count(),
                })
        else:
            # 每日統計
            days = (end_date.date() - start_date.date()).days + 1
            for i in range(days):
                day = start_date.date() + timedelta(days=i)
                day_start = timezone.make_aware(datetime.combine(day, datetime.min.time()))
                day_end = day_start + timedelta(days=1)
                
                day_logs = logs_query.filter(timestamp__gte=day_start, timestamp__lt=day_end)
                
                time_series.append({
                    'time': day.isoformat(),
                    'total': day_logs.count(),
                    'mac': day_logs.filter(log_type='MAC').count(),
                    'boot': day_logs.filter(log_type='BOOT').count(),
                })
        
        # 3. BOOT 檔案統計（Top 10）
        boot_files = logs_query.filter(log_type='BOOT').values('file_requested').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # 4. 伺服器統計
        server_stats = []
        for server in IPXEServer.objects.all():
            server_logs = logs_query.filter(server=server)
            server_stats.append({
                'server_id': server.id,
                'server_name': server.name,
                'server_ip': server.ip_address,
                'total': server_logs.count(),
                'mac': server_logs.filter(log_type='MAC').count(),
                'boot': server_logs.filter(log_type='BOOT').count(),
            })
        
        # 5. 活躍 Client IP 統計（Top 10）
        active_clients = logs_query.values('client_ip').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # 計算唯一客戶端數量
        unique_clients = logs_query.values('client_ip').distinct().count()
        
        logger.info(f'成功獲取 IPXE 統計資料: {start_date_str} ~ {end_date_str}, total={total_logs}')
        
        return Response({
            'summary': {
                'total_requests': total_logs,        # 前端期望的欄位名稱
                'mac_requests': mac_logs_count,      # 前端期望的欄位名稱
                'boot_requests': boot_logs_count,    # 前端期望的欄位名稱
                'unique_clients': unique_clients,     # 唯一客戶端數量
                'mac_set': mac_set_count,
                'mac_get': mac_get_count,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'granularity': granularity,
            },
            'time_series': time_series,
            'boot_files': list(boot_files),
            'top_files': list(boot_files),  # 前端期望的欄位名稱
            'server_stats': server_stats,
            'active_clients': list(active_clients),
            'top_clients': list(active_clients),  # 前端期望的欄位名稱
        })
        
    except Exception as e:
        logger.error(f'獲取 IPXE 統計資料失敗: {str(e)}', exc_info=True)
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def system_status(request):
    """獲取系統狀態（磁碟空間、CPU、RAM 使用率）"""
    import psutil
    import shutil
    
    try:
        # 1. 磁碟空間資訊
        disk_usage = shutil.disk_usage('/')
        disk_total = disk_usage.total / (1024 ** 3)  # GB
        disk_used = disk_usage.used / (1024 ** 3)    # GB
        disk_free = disk_usage.free / (1024 ** 3)    # GB
        disk_percent = (disk_usage.used / disk_usage.total) * 100
        
        # 2. CPU 使用率（過去 1 秒的平均值）
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # 3. RAM 使用率
        memory = psutil.virtual_memory()
        ram_total = memory.total / (1024 ** 3)      # GB
        ram_used = memory.used / (1024 ** 3)        # GB
        ram_available = memory.available / (1024 ** 3)  # GB
        ram_percent = memory.percent
        
        logger.info(f'系統狀態查詢成功: CPU={cpu_percent}%, RAM={ram_percent}%, Disk={disk_percent:.1f}%')
        
        return Response({
            'disk': {
                'total': round(disk_total, 2),
                'used': round(disk_used, 2),
                'free': round(disk_free, 2),
                'percent': round(disk_percent, 1),
            },
            'cpu': {
                'percent': round(cpu_percent, 1),
                'count': cpu_count,
            },
            'ram': {
                'total': round(ram_total, 2),
                'used': round(ram_used, 2),
                'available': round(ram_available, 2),
                'percent': round(ram_percent, 1),
            },
        })
        
    except Exception as e:
        logger.error(f'獲取系統狀態失敗: {str(e)}', exc_info=True)
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
