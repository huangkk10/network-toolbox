"""
IPXE 分析統計 Views
處理 IPXE 日誌的分析和統計功能
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone
from django.db.models import Count, Q
from datetime import timedelta, datetime
import logging

from ..models import DHCPLog, DHCPServer, IPXELog, IPXEServer

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def ipxe_analytics_overview(request):
    """
    獲取 IPXE 分析總覽資料
    GET /api/ipxe-analytics/overview/
    Query Parameters (可選):
    - days: 統計天數（預設 7）
    - server_id: 指定伺服器 ID（預設全部）
    
    註：此 API 從 IPXELog 表讀取日誌記錄
    """
    try:
        # 獲取參數
        days = int(request.query_params.get('days', 7))
        server_id = request.query_params.get('server_id', None)
        
        cutoff_time = timezone.now() - timedelta(days=days)
        
        # 基礎查詢：從 IPXELog 表讀取日誌
        logs_query = IPXELog.objects.filter(
            timestamp__gte=cutoff_time
        )
        
        if server_id:
            logs_query = logs_query.filter(server_id=server_id)
        
        # 1. 總體統計
        total_logs = logs_query.count()
        # MAC 管理請求：log_type='MAC'
        mac_logs_count = logs_query.filter(log_type='MAC').count()
        # BOOT 請求：log_type='BOOT'
        boot_logs_count = logs_query.filter(log_type='BOOT').count()
        
        # 2. MAC 操作統計
        mac_set_count = logs_query.filter(log_type='MAC', action='set_mac').count()
        mac_get_count = logs_query.filter(log_type='MAC', action='get_mac').count()
        
        # 3. BOOT 啟動檔案統計
        boot_files_data = logs_query.filter(log_type='BOOT').values('action').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # 轉換為前端期望的格式
        boot_logs = [
            {'file_requested': item['action'], 'count': item['count']} 
            for item in boot_files_data
        ]
        
        # 4. 每日統計（過去 N 天）
        daily_stats = []
        for i in range(days):
            day_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=i)
            day_end = day_start + timedelta(days=1)
            
            day_logs = logs_query.filter(timestamp__gte=day_start, timestamp__lt=day_end)
            # MAC 相關日誌
            mac_count = day_logs.filter(log_type='MAC').count()
            # BOOT 相關日誌
            boot_count = day_logs.filter(log_type='BOOT').count()
            
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
                'mac_logs': hour_logs.filter(log_type='MAC').count(),
                'boot_logs': hour_logs.filter(log_type='BOOT').count(),
            })
        
        hourly_stats.reverse()  # 從早到晚排序
        
        # 6. 伺服器統計（使用 IPXEServer）
        server_stats = []
        # 獲取唯一的伺服器 ID
        unique_server_ids = set(logs_query.values_list('server__id', flat=True))
        
        for sid in unique_server_ids:
            if sid is None:
                continue
                
            server_logs = logs_query.filter(server_id=sid)
            
            # 獲取伺服器資訊
            try:
                server = IPXEServer.objects.get(id=sid)
                server_name = server.name
                server_ip = server.ip_address
                last_sync = server.last_sync_at.isoformat() if server.last_sync_at else None
            except IPXEServer.DoesNotExist:
                server_name = f'Server {sid}'
                server_ip = 'N/A'
                last_sync = None
            
            server_stats.append({
                'server_id': sid,
                'server_name': server_name,
                'server_ip': server_ip,
                'total_logs': server_logs.count(),
                'mac_logs': server_logs.filter(log_type='MAC').count(),
                'boot_logs': server_logs.filter(log_type='BOOT').count(),
                'last_sync': last_sync,
            })
        
        # 7. Top 10 活躍 MAC 地址（從 mac_address 欄位讀取）
        top_mac_data = logs_query.filter(mac_address__isnull=False).exclude(mac_address='').values('mac_address').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        top_mac_addresses = [
            {'mac': item['mac_address'], 'count': item['count']}
            for item in top_mac_data
        ]
        
        logger.info(f'成功獲取 iPXE 分析資料: days={days}, total_logs={total_logs}, MAC={mac_logs_count}, BOOT={boot_logs_count}')
        
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
