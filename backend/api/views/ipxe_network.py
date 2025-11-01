"""
IPXE 網路品質監控 Views
處理 IPXE 網路品質相關的 API 請求
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone
from django.db.models import Avg, Count
from datetime import timedelta
import logging

from ..models import IPXENetworkQuality
from ..serializers import IPXENetworkQualitySerializer

logger = logging.getLogger(__name__)


class IPXENetworkQualityViewSet(viewsets.ModelViewSet):
    """
    IPXE 網路品質記錄 ViewSet
    支援 CRUD 操作
    """
    queryset = IPXENetworkQuality.objects.all()
    serializer_class = IPXENetworkQualitySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """
        自訂查詢集（支援按伺服器、時間範圍、狀態篩選）
        Query Parameters:
        - server_id: 伺服器 ID
        - days: 查詢最近幾天的資料（預設 7 天）
        - status: 狀態篩選 (online/offline/warning)
        """
        queryset = IPXENetworkQuality.objects.all()
        
        server_id = self.request.query_params.get('server_id', None)
        if server_id:
            queryset = queryset.filter(server_id=server_id)
        
        days = int(self.request.query_params.get('days', 7))
        if days > 0:
            cutoff_time = timezone.now() - timedelta(days=days)
            queryset = queryset.filter(timestamp__gte=cutoff_time)
        
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.select_related('server').order_by('-timestamp')

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        獲取網路品質統計分析資料
        GET /api/ipxe-network-quality/statistics/
        Query Parameters:
        - server_id: 伺服器 ID（可選）
        - days: 統計天數（預設 7 天）
        """
        try:
            # 獲取參數
            server_id = request.query_params.get('server_id', None)
            days = int(request.query_params.get('days', 7))
            
            cutoff_time = timezone.now() - timedelta(days=days)
            
            # 基礎查詢
            quality_query = IPXENetworkQuality.objects.filter(timestamp__gte=cutoff_time)
            
            if server_id and server_id != 'all':
                quality_query = quality_query.filter(server_id=server_id)
            
            # 1. 基本統計
            total_checks = quality_query.count()
            
            if total_checks == 0:
                return Response({
                    'summary': {
                        'total_checks': 0,
                        'online_count': 0,
                        'offline_count': 0,
                        'warning_count': 0,
                        'avg_ping_latency': 0,
                        'avg_http_response_time': 0,
                        'avg_ssh_response_time': 0,
                        'avg_download_speed': 0,
                        'avg_packet_loss': 0,
                    },
                    'daily_stats': [],
                    'hourly_stats': [],
                    'quality_trends': [],
                    'latest_status': []
                })
            
            online_count = quality_query.filter(status='online').count()
            offline_count = quality_query.filter(status='offline').count()
            warning_count = quality_query.filter(status='warning').count()
            
            # 平均值統計
            avg_stats = quality_query.aggregate(
                avg_ping=Avg('ping_latency'),
                avg_http=Avg('http_response_time'),
                avg_ssh=Avg('ssh_response_time'),
                avg_speed=Avg('download_speed'),
                avg_loss=Avg('ping_packet_loss')  # 正確的欄位名稱
            )
            
            # 2. 每日統計
            daily_stats = []
            for i in range(days):
                day_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=i)
                day_end = day_start + timedelta(days=1)
                
                day_quality = quality_query.filter(timestamp__gte=day_start, timestamp__lt=day_end)
                
                if day_quality.exists():
                    day_avg = day_quality.aggregate(
                        avg_ping=Avg('ping_latency'),
                        avg_http=Avg('http_response_time'),
                        avg_ssh=Avg('ssh_response_time'),
                        avg_speed=Avg('download_speed'),
                        avg_loss=Avg('ping_packet_loss')
                    )
                    
                    daily_stats.append({
                        'date': day_start.date().isoformat(),
                        'total_checks': day_quality.count(),
                        'online_count': day_quality.filter(status='online').count(),
                        'offline_count': day_quality.filter(status='offline').count(),
                        'warning_count': day_quality.filter(status='warning').count(),
                        'avg_ping_latency': round(day_avg['avg_ping'] or 0, 2),
                        'avg_http_response_time': round(day_avg['avg_http'] or 0, 2),
                        'avg_ssh_response_time': round(day_avg['avg_ssh'] or 0, 2),
                        'avg_download_speed': round(day_avg['avg_speed'] or 0, 2),
                        'avg_packet_loss': round(day_avg['avg_loss'] or 0, 2),
                    })
            
            daily_stats.reverse()
            
            # 3. 每小時統計（過去 24 小時）
            hourly_stats = []
            for i in range(24):
                hour_start = timezone.now().replace(minute=0, second=0, microsecond=0) - timedelta(hours=i)
                hour_end = hour_start + timedelta(hours=1)
                
                hour_quality = quality_query.filter(timestamp__gte=hour_start, timestamp__lt=hour_end)
                
                if hour_quality.exists():
                    hour_avg = hour_quality.aggregate(
                        avg_ping=Avg('ping_latency'),
                        avg_http=Avg('http_response_time'),
                        avg_ssh=Avg('ssh_response_time'),
                        avg_speed=Avg('download_speed'),
                        avg_loss=Avg('ping_packet_loss')
                    )
                    
                    hourly_stats.append({
                        'hour': hour_start.strftime('%Y-%m-%d %H:00'),
                        'total_checks': hour_quality.count(),
                        'avg_ping_latency': round(hour_avg['avg_ping'] or 0, 2),
                        'avg_http_response_time': round(hour_avg['avg_http'] or 0, 2),
                        'avg_ssh_response_time': round(hour_avg['avg_ssh'] or 0, 2),
                        'avg_download_speed': round(hour_avg['avg_speed'] or 0, 2),
                        'avg_packet_loss': round(hour_avg['avg_loss'] or 0, 2),
                    })
            
            hourly_stats.reverse()
            
            # 4. 品質趨勢（動態取樣）
            quality_trends = []
            total_minutes = days * 24 * 60
            
            # 根據時間範圍動態決定取樣間隔
            if days <= 1:
                interval_minutes = 5  # 1 天內：每 5 分鐘
                sample_count = min(288, total_minutes // interval_minutes)
            elif days <= 3:
                interval_minutes = 15  # 3 天內：每 15 分鐘
                sample_count = min(288, total_minutes // interval_minutes)
            elif days <= 7:
                interval_minutes = 60  # 7 天內：每 1 小時
                sample_count = min(168, total_minutes // interval_minutes)
            else:
                interval_minutes = 180  # 7 天以上：每 3 小時
                sample_count = min(168, total_minutes // interval_minutes)
            
            for i in range(sample_count):
                period_end = timezone.now() - timedelta(minutes=i * interval_minutes)
                period_start = period_end - timedelta(minutes=interval_minutes)
                
                period_quality = quality_query.filter(
                    timestamp__gte=period_start,
                    timestamp__lt=period_end
                )
                
                if period_quality.exists():
                    period_avg = period_quality.aggregate(
                        avg_ping=Avg('ping_latency'),
                        avg_http=Avg('http_response_time'),
                        avg_ssh=Avg('ssh_response_time'),
                        avg_speed=Avg('download_speed'),
                        avg_loss=Avg('ping_packet_loss')
                    )
                    
                    quality_trends.append({
                        'timestamp': period_start.isoformat(),
                        'avg_ping_latency': round(period_avg['avg_ping'] or 0, 2),
                        'avg_http_response_time': round(period_avg['avg_http'] or 0, 2),
                        'avg_ssh_response_time': round(period_avg['avg_ssh'] or 0, 2),
                        'avg_download_speed': round(period_avg['avg_speed'] or 0, 2),
                        'avg_packet_loss': round(period_avg['avg_loss'] or 0, 2),
                    })
            
            quality_trends.reverse()
            
            # 5. 最新狀態（每個伺服器的最新記錄）
            from ..models import IPXEServer
            latest_status = []
            
            if server_id and server_id != 'all':
                servers = IPXEServer.objects.filter(id=server_id)
            else:
                servers = IPXEServer.objects.all()
            
            for server in servers:
                latest_record = quality_query.filter(server=server).order_by('-timestamp').first()
                
                if latest_record:
                    latest_status.append({
                        'server_id': server.id,
                        'server_name': server.name,
                        'server_ip': server.ip_address,
                        'status': latest_record.status,
                        'ping_latency': latest_record.ping_latency,
                        'http_response_time': latest_record.http_response_time,
                        'ssh_response_time': latest_record.ssh_response_time,
                        'download_speed': latest_record.download_speed,
                        'packet_loss': latest_record.ping_packet_loss,
                        'timestamp': latest_record.timestamp.isoformat(),
                    })
            
            logger.info(f'成功獲取 IPXE 網路品質統計: days={days}, total_checks={total_checks}')
            
            # 計算成功率（online / total）
            success_rate = 0
            if total_checks > 0:
                success_rate = (online_count / total_checks) * 100
            
            return Response({
                'summary': {
                    'total_checks': total_checks,
                    'total_records': total_checks,  # 前端期望的欄位名稱
                    'online_count': online_count,
                    'offline_count': offline_count,
                    'warning_count': warning_count,
                    'success_rate': round(success_rate, 2),  # 前端期望的成功率
                    'avg_ping_latency': round(avg_stats['avg_ping'] or 0, 2),
                    'avg_http_response_time': round(avg_stats['avg_http'] or 0, 2),
                    'avg_ssh_response_time': round(avg_stats['avg_ssh'] or 0, 2),
                    'avg_download_speed': round(avg_stats['avg_speed'] or 0, 2),
                    'avg_packet_loss': round(avg_stats['avg_loss'] or 0, 2),
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
