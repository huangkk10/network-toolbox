"""
DHCP 日誌查詢 API Views
包含日誌查看和 MAC 地址查詢
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db.models import Q, Count
from datetime import datetime, timedelta
from ..models import DHCPServer, DHCPLease, DHCPLog
import logging

logger = logging.getLogger(__name__)


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
    from ..services import DHCPLogService
    
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
