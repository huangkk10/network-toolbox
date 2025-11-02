"""
GitLab 連線品質監控 Views
提供 GitLab 伺服器連線品質記錄和統計資料
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Avg, Count, Max, Min, Q
from datetime import timedelta
from ..models import GitLabConnection
from ..serializers import GitLabConnectionSerializer
import logging

logger = logging.getLogger(__name__)


class GitLabConnectionViewSet(viewsets.ModelViewSet):
    """GitLab 連線品質記錄 API ViewSet"""
    queryset = GitLabConnection.objects.all()
    serializer_class = GitLabConnectionSerializer
    permission_classes = [AllowAny]
    pagination_class = None  # 禁用分頁
    
    def get_queryset(self):
        """過濾查詢，支援時間範圍和狀態過濾"""
        queryset = GitLabConnection.objects.all()
        
        # 時間範圍過濾
        days = self.request.query_params.get('days', None)
        if days:
            try:
                days_int = int(days)
                start_time = timezone.now() - timedelta(days=days_int)
                queryset = queryset.filter(checked_at__gte=start_time)
            except ValueError:
                pass
        else:
            # 預設返回最近 7 天
            start_time = timezone.now() - timedelta(days=7)
            queryset = queryset.filter(checked_at__gte=start_time)
        
        # 狀態過濾
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # GitLab URL 過濾
        gitlab_url = self.request.query_params.get('gitlab_url', None)
        if gitlab_url:
            queryset = queryset.filter(gitlab_url=gitlab_url)
        
        return queryset.order_by('-checked_at')
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """GitLab 連線品質統計資料"""
        try:
            # 時間範圍
            days = int(request.query_params.get('days', 7))
            start_time = timezone.now() - timedelta(days=days)
            
            gitlab_url = request.query_params.get('gitlab_url', None)
            
            # 查詢數據
            logs = GitLabConnection.objects.filter(checked_at__gte=start_time)
            if gitlab_url:
                logs = logs.filter(gitlab_url=gitlab_url)
            
            # 基本統計
            total_checks = logs.count()
            successful_checks = logs.filter(status='success').count()
            failed_checks = logs.filter(status='failed').count()
            timeout_checks = logs.filter(status='timeout').count()
            success_rate = (successful_checks / total_checks * 100) if total_checks > 0 else 0
            
            # 網路性能指標
            successful_logs = logs.filter(status='success')
            
            avg_ping_latency = successful_logs.filter(
                ping_latency__isnull=False
            ).aggregate(Avg('ping_latency'))['ping_latency__avg'] or 0
            
            avg_http_response = successful_logs.filter(
                http_response_time__isnull=False
            ).aggregate(Avg('http_response_time'))['http_response_time__avg'] or 0
            
            max_ping_latency = successful_logs.filter(
                ping_latency__isnull=False
            ).aggregate(Max('ping_latency'))['ping_latency__max'] or 0
            
            min_ping_latency = successful_logs.filter(
                ping_latency__isnull=False
            ).aggregate(Min('ping_latency'))['ping_latency__min'] or 0
            
            avg_packet_loss = logs.aggregate(Avg('packet_loss'))['packet_loss__avg'] or 0
            
            # 可用性百分比（Uptime）
            uptime_percentage = success_rate
            
            # 每日趨勢（最近指定天數）
            daily_trends = []
            for i in range(days - 1, -1, -1):
                day_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=i)
                day_end = day_start + timedelta(days=1)
                
                day_logs = logs.filter(checked_at__gte=day_start, checked_at__lt=day_end)
                day_total = day_logs.count()
                day_success = day_logs.filter(status='success').count()
                day_failed = day_logs.filter(status='failed').count()
                
                day_avg_latency = day_logs.filter(
                    status='success',
                    ping_latency__isnull=False
                ).aggregate(Avg('ping_latency'))['ping_latency__avg'] or 0
                
                day_avg_http = day_logs.filter(
                    status='success',
                    http_response_time__isnull=False
                ).aggregate(Avg('http_response_time'))['http_response_time__avg'] or 0
                
                daily_trends.append({
                    'date': day_start.strftime('%Y-%m-%d'),
                    'total_checks': day_total,
                    'success_count': day_success,
                    'failed_count': day_failed,
                    'success_rate': (day_success / day_total * 100) if day_total > 0 else 0,
                    'avg_latency': round(day_avg_latency, 2),
                    'avg_http_response': round(day_avg_http, 3),
                })
            
            # 每小時趨勢（最近24小時）
            hourly_trends = []
            for i in range(23, -1, -1):
                hour_start = timezone.now().replace(minute=0, second=0, microsecond=0) - timedelta(hours=i)
                hour_end = hour_start + timedelta(hours=1)
                
                hour_logs = logs.filter(checked_at__gte=hour_start, checked_at__lt=hour_end)
                hour_total = hour_logs.count()
                hour_success = hour_logs.filter(status='success').count()
                
                hour_avg_latency = hour_logs.filter(
                    status='success',
                    ping_latency__isnull=False
                ).aggregate(Avg('ping_latency'))['ping_latency__avg'] or 0
                
                hourly_trends.append({
                    'hour': hour_start.strftime('%Y-%m-%d %H:00'),
                    'total_checks': hour_total,
                    'success_count': hour_success,
                    'avg_latency': round(hour_avg_latency, 2),
                })
            
            # HTTP 狀態碼分佈
            http_status_distribution = logs.filter(
                http_status_code__isnull=False
            ).values('http_status_code').annotate(
                count=Count('id')
            ).order_by('-count')[:10]
            
            # 最近的檢查記錄
            latest_check = logs.order_by('-checked_at').first()
            latest_check_data = None
            if latest_check:
                latest_check_data = {
                    'checked_at': latest_check.checked_at.isoformat(),
                    'status': latest_check.status,
                    'ping_latency': latest_check.ping_latency,
                    'http_response_time': latest_check.http_response_time,
                    'http_status_code': latest_check.http_status_code,
                    'is_reachable': latest_check.is_reachable,
                }
            
            return Response({
                'total_checks': total_checks,
                'successful_checks': successful_checks,
                'failed_checks': failed_checks,
                'timeout_checks': timeout_checks,
                'success_rate': round(success_rate, 2),
                'uptime_percentage': round(uptime_percentage, 2),
                'avg_ping_latency': round(avg_ping_latency, 2),
                'avg_http_response': round(avg_http_response, 3),
                'max_ping_latency': round(max_ping_latency, 2),
                'min_ping_latency': round(min_ping_latency, 2),
                'avg_packet_loss': round(avg_packet_loss, 2),
                'daily_trends': daily_trends,
                'hourly_trends': hourly_trends,
                'http_status_distribution': list(http_status_distribution),
                'latest_check': latest_check_data,
                'time_range_days': days,
            })
        
        except Exception as e:
            logger.error(f'獲取 GitLab 統計資料失敗: {str(e)}', exc_info=True)
            return Response(
                {'error': '獲取統計資料失敗', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def current_status(self, request):
        """獲取 GitLab 當前連線狀態"""
        try:
            gitlab_url = request.query_params.get('gitlab_url', None)
            
            # 獲取最近的一筆記錄
            if gitlab_url:
                # 如果提供了 URL，進行精確或模糊匹配（去除結尾斜線）
                gitlab_url = gitlab_url.rstrip('/')
                latest = GitLabConnection.objects.filter(
                    gitlab_url__startswith=gitlab_url
                ).order_by('-checked_at').first()
            else:
                # 如果沒有提供 URL，返回最新的一筆記錄
                latest = GitLabConnection.objects.order_by('-checked_at').first()
            
            if not latest:
                return Response({
                    'status': 'unknown',
                    'message': '尚未有任何檢查記錄'
                })
            
            # 計算距離上次檢查的時間
            time_since_check = (timezone.now() - latest.checked_at).total_seconds() / 60  # 分鐘
            
            return Response({
                'gitlab_url': latest.gitlab_url,
                'gitlab_name': latest.gitlab_name,
                'status': latest.status,
                'is_reachable': latest.is_reachable,
                'ping_latency': latest.ping_latency,
                'http_response_time': latest.http_response_time,
                'http_status_code': latest.http_status_code,
                'last_checked': latest.checked_at.isoformat(),
                'minutes_since_check': round(time_since_check, 1),
                'error_message': latest.error_message if latest.error_message else None,
            })
        
        except Exception as e:
            logger.error(f'獲取 GitLab 當前狀態失敗: {str(e)}', exc_info=True)
            return Response(
                {'error': '獲取當前狀態失敗', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
