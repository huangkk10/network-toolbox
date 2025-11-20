"""
系統狀態和儀表板統計 Views
處理系統監控和儀表板數據
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone
from django.db.models import Avg
from datetime import timedelta
import psutil
import shutil
import logging

from ..models import DHCPServer, DHCPLease, SystemMonitorHistory

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def dashboard_stats(request):
    """
    儀表板統計資料
    GET /api/dashboard/stats/
    
    返回 DHCP 伺服器和租約的總體統計資訊
    """
    try:
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
        
        logger.info(f'儀表板統計查詢成功: servers={total_servers}, leases={total_leases}')
        
        return Response({
            'total_servers': total_servers,
            'online_servers': online_servers,
            'warning_servers': warning_servers,
            'offline_servers': total_servers - online_servers - warning_servers,
            'total_leases': total_leases,
            'active_leases': active_leases,
            'avg_pool_usage': round(avg_pool_usage, 2),
        })
        
    except Exception as e:
        logger.error(f'獲取儀表板統計失敗: {str(e)}', exc_info=True)
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def system_status(request):
    """
    獲取系統狀態（磁碟空間、CPU、RAM 使用率）
    GET /api/system/status/
    
    返回伺服器的系統資源使用情況
    """
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
        
        # 4. 保存歷史數據（每次查詢都保存）
        try:
            SystemMonitorHistory.objects.create(
                timestamp=timezone.now(),  # 手動設置當前時間
                cpu_percent=cpu_percent,
                cpu_count=cpu_count,
                ram_percent=ram_percent,
                ram_total_gb=ram_total,
                ram_used_gb=ram_used,
                ram_available_gb=ram_available,
                disk_percent=disk_percent,
                disk_total_gb=disk_total,
                disk_used_gb=disk_used,
                disk_free_gb=disk_free,
            )
        except Exception as save_error:
            logger.warning(f'保存系統監控歷史失敗: {str(save_error)}')
        
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


@api_view(['GET'])
@permission_classes([AllowAny])
def system_history(request):
    """
    獲取系統監控歷史數據
    GET /api/system/history/?range=1day|3days|1week
    
    根據時間範圍返回系統資源使用歷史數據
    """
    try:
        # 獲取時間範圍參數（預設 1 天）
        time_range = request.GET.get('range', '1day')
        
        # 計算時間範圍
        now = timezone.now()
        if time_range == '1day':
            start_time = now - timedelta(days=1)
            # 每 5 分鐘取一筆（1天 = 288筆）
            interval_minutes = 5
        elif time_range == '3days':
            start_time = now - timedelta(days=3)
            # 每 15 分鐘取一筆（3天 = 288筆）
            interval_minutes = 15
        elif time_range == '1week':
            start_time = now - timedelta(days=7)
            # 每 30 分鐘取一筆（7天 = 336筆）
            interval_minutes = 30
        else:
            start_time = now - timedelta(days=1)
            interval_minutes = 5
        
        # 查詢歷史數據
        history_records = SystemMonitorHistory.objects.filter(
            timestamp__gte=start_time
        ).order_by('timestamp')
        
        # 如果記錄數量少於 10 筆，直接返回所有數據（方便開發測試）
        if history_records.count() < 10:
            sampled_data = [{
                'time': record.timestamp.strftime('%m-%d %H:%M'),
                'cpu': round(record.cpu_percent, 1),
                'ram': round(record.ram_percent, 1),
                'disk': round(record.disk_percent, 1),
            } for record in history_records]
        else:
            # 採樣數據（避免返回過多數據點）
            sampled_data = []
            interval_seconds = interval_minutes * 60
            last_timestamp = None
            
            for record in history_records:
                # 如果是第一筆記錄，直接添加
                if last_timestamp is None:
                    sampled_data.append({
                        'time': record.timestamp.strftime('%m-%d %H:%M'),
                        'cpu': round(record.cpu_percent, 1),
                        'ram': round(record.ram_percent, 1),
                        'disk': round(record.disk_percent, 1),
                    })
                    last_timestamp = record.timestamp
                # 如果距離上次採樣已超過間隔時間，添加這筆記錄
                elif (record.timestamp - last_timestamp).total_seconds() >= interval_seconds:
                    sampled_data.append({
                        'time': record.timestamp.strftime('%m-%d %H:%M'),
                        'cpu': round(record.cpu_percent, 1),
                        'ram': round(record.ram_percent, 1),
                        'disk': round(record.disk_percent, 1),
                    })
                    last_timestamp = record.timestamp
        
        logger.info(f'系統歷史數據查詢成功: range={time_range}, records={len(sampled_data)}')
        
        return Response(sampled_data)
        
    except Exception as e:
        logger.error(f'獲取系統歷史數據失敗: {str(e)}', exc_info=True)
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
