"""
DHCP 分析 API Views
包含總覽、趨勢、狀態分佈、最近租約、統計分析
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from collections import Counter
from ..models import DHCPServer, DHCPLease
import logging

logger = logging.getLogger(__name__)


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
        from ..utils.mac_vendor import get_vendor_from_mac
        
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
