"""
NAS 連線記錄 Views
包含 NAS 連線日誌和統計資料
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Avg
from datetime import timedelta
from ..models import NASConnectionLog
from ..serializers import NASConnectionLogSerializer
import logging

logger = logging.getLogger(__name__)


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
                
                # ✅ 轉換為當前時區（Asia/Taipei）再格式化
                local_day_start = timezone.localtime(day_start)
                
                daily_stats.append({
                    'date': local_day_start.strftime('%Y-%m-%d'),
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
                
                # ✅ 轉換為當前時區（Asia/Taipei）再格式化
                local_hour_start = timezone.localtime(hour_start)
                
                hourly_stats.append({
                    'hour': local_hour_start.strftime('%Y-%m-%d %H:00'),
                    'total': hour_total,
                    'success': hour_success,
                    'failed': hour_total - hour_success,
                })
            
            # 速度趨勢（根據時間範圍動態調整）
            speed_trends = []
            
            # 根據天數決定採樣間隔
            if days <= 1:
                interval_minutes = 5
                num_points = int((days * 24 * 60) / interval_minutes)
            elif days <= 3:
                interval_minutes = 15
                num_points = int((days * 24 * 60) / interval_minutes)
            elif days <= 7:
                interval_minutes = 60
                num_points = int((days * 24 * 60) / interval_minutes)
            else:
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
                
                # ✅ 轉換為當前時區（Asia/Taipei）再格式化時間標籤
                local_period_end = timezone.localtime(period_end)
                
                # 格式化時間標籤
                if interval_minutes < 60:
                    time_label = local_period_end.strftime('%m-%d %H:%M')
                else:
                    time_label = local_period_end.strftime('%m-%d %H:00')
                
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
