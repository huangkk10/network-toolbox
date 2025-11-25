"""
系統狀態和儀表板統計 Views
處理系統監控和儀表板數據
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone
from django.db.models import Avg, Sum, Count
from django.db import models
from datetime import timedelta
import psutil
import shutil
import logging
from celery import current_app

from ..models import DHCPServer, DHCPLease, SystemMonitorHistory, WebsiteUsageStats

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
        
        # ✨ 網站使用統計（今日）
        today = timezone.now().date()
        today_stats = WebsiteUsageStats.objects.filter(date=today).first()
        
        # 如果今天沒有統計記錄，創建一個空的
        if not today_stats:
            today_stats = WebsiteUsageStats.objects.create(date=today)
        
        # 過去7天的使用趨勢
        seven_days_ago = today - timedelta(days=7)
        recent_stats = WebsiteUsageStats.objects.filter(
            date__gte=seven_days_ago
        ).order_by('date')
        
        usage_trend = [
            {
                'date': str(stat.date),
                'page_views': stat.total_page_views,
                'api_requests': stat.total_api_requests,
                'unique_visitors': stat.unique_visitors,
            }
            for stat in recent_stats
        ]
        
        # 頁面訪問分佈
        page_distribution = {
            'dashboard': today_stats.dashboard_visits,
            'dhcp': today_stats.dhcp_page_visits,
            'ipxe': today_stats.ipxe_page_visits,
            'jenkins': today_stats.jenkins_page_visits,
            'ansible': today_stats.ansible_page_visits,
        } if today_stats else {}
        
        # 功能使用統計
        feature_usage = {
            'dhcp_sync': today_stats.dhcp_sync_count,
            'ipxe_operations': today_stats.ipxe_operations,
            'jenkins_builds': today_stats.jenkins_builds,
            'ansible_executions': today_stats.ansible_executions,
        } if today_stats else {}
        
        logger.info(f'儀表板統計查詢成功: servers={total_servers}, leases={total_leases}, page_views={today_stats.total_page_views if today_stats else 0}')
        
        return Response({
            # DHCP 統計
            'total_servers': total_servers,
            'online_servers': online_servers,
            'warning_servers': warning_servers,
            'offline_servers': total_servers - online_servers - warning_servers,
            'total_leases': total_leases,
            'active_leases': active_leases,
            'avg_pool_usage': round(avg_pool_usage, 2),
            
            # ✨ 網站使用統計
            'website_usage': {
                # 今日統計
                'today': {
                    'total_page_views': today_stats.total_page_views if today_stats else 0,
                    'unique_visitors': today_stats.unique_visitors if today_stats else 0,
                    'total_api_requests': today_stats.total_api_requests if today_stats else 0,
                    'error_count': today_stats.error_count if today_stats else 0,
                },
                # 過去7天趨勢
                'trend': usage_trend,
                # 頁面訪問分佈
                'page_distribution': page_distribution,
                # 功能使用統計
                'feature_usage': feature_usage,
                # 熱門頁面（前5名）
                'top_pages': dict(sorted(
                    (today_stats.top_pages if today_stats else {}).items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]) if today_stats else {},
                # 熱門 API 端點（前5名）
                'top_api_endpoints': dict(sorted(
                    (today_stats.top_api_endpoints if today_stats else {}).items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]) if today_stats else {},
            }
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
                'time': timezone.localtime(record.timestamp).strftime('%m-%d %H:%M'),
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
                        'time': timezone.localtime(record.timestamp).strftime('%m-%d %H:%M'),
                        'cpu': round(record.cpu_percent, 1),
                        'ram': round(record.ram_percent, 1),
                        'disk': round(record.disk_percent, 1),
                    })
                    last_timestamp = record.timestamp
                # 如果距離上次採樣已超過間隔時間，添加這筆記錄
                elif (record.timestamp - last_timestamp).total_seconds() >= interval_seconds:
                    sampled_data.append({
                        'time': timezone.localtime(record.timestamp).strftime('%m-%d %H:%M'),
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


@api_view(['GET'])
@permission_classes([AllowAny])
def task_stats(request):
    """
    獲取 Celery 任務統計數據
    GET /api/system/task-stats/
    
    返回：
    - 當前執行中的任務數量
    - 今日任務成功/失敗統計
    - Worker 狀態
    - 平均執行時間
    """
    try:
        # 1. 獲取 Celery Inspector
        inspector = current_app.control.inspect()
        
        # 2. 當前執行中的任務
        active_tasks = inspector.active()
        running_count = sum(len(tasks) for tasks in (active_tasks or {}).values()) if active_tasks else 0
        
        # 3. 定時任務數量
        scheduled_count = len(current_app.conf.beat_schedule)
        
        # 4. Worker 狀態
        stats = inspector.stats()
        worker_count = len(stats) if stats else 0
        
        # 5. 今日任務統計（從 Django Celery Results 查詢）
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        try:
            from django_celery_results.models import TaskResult
            
            today_tasks = TaskResult.objects.filter(
                date_created__gte=today_start
            )
            
            success_count = today_tasks.filter(status='SUCCESS').count()
            failure_count = today_tasks.filter(status='FAILURE').count()
            total_count = today_tasks.count()
            
            success_rate = (success_count / total_count * 100) if total_count > 0 else 0
            
            # 計算平均執行時間（秒）
            completed_tasks = today_tasks.filter(
                status__in=['SUCCESS', 'FAILURE'],
                date_done__isnull=False
            )
            
            avg_execution_time = 0
            if completed_tasks.exists():
                durations = []
                for task in completed_tasks:
                    if task.date_done and task.date_created:
                        duration = (task.date_done - task.date_created).total_seconds()
                        if duration > 0:
                            durations.append(duration)
                
                avg_execution_time = sum(durations) / len(durations) if durations else 0
            
        except ImportError:
            # 如果沒有安裝 django-celery-results，返回模擬數據
            logger.warning('django-celery-results 未安裝，返回模擬數據')
            success_count = 0
            failure_count = 0
            total_count = 0
            success_rate = 0
            avg_execution_time = 0
        
        logger.info(f'任務統計查詢成功: running={running_count}, workers={worker_count}, success_rate={success_rate:.1f}%')
        
        # 返回統計數據
        return Response({
            'success': True,
            'data': {
                'current_tasks': {
                    'running': running_count,
                    'pending': 0,  # 需要查詢 Redis 隊列長度（進階功能）
                    'scheduled': scheduled_count
                },
                'today_stats': {
                    'success': success_count,
                    'failure': failure_count,
                    'total': total_count,
                    'success_rate': round(success_rate, 2)
                },
                'workers': {
                    'total': worker_count,
                    'active': worker_count,  # 簡化：假設所有 Worker 都活躍
                    'offline': 0
                },
                'avg_execution_time': {
                    'all_tasks': round(avg_execution_time, 2),
                    'last_hour': 0  # 進階功能：需要計算最近 1 小時的平均時間
                }
            }
        })
        
    except Exception as e:
        logger.error(f'獲取任務統計失敗: {e}', exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def recent_tasks(request):
    """
    獲取最近任務列表
    GET /api/system/recent-tasks/?limit=10&status=all
    
    查詢參數：
    - limit: 返回數量（預設 10）
    - status: 過濾狀態（all/SUCCESS/FAILURE/RUNNING）
    """
    try:
        limit = int(request.GET.get('limit', 10))
        status_filter = request.GET.get('status', 'all')
        
        from django_celery_results.models import TaskResult
        
        # 查詢最近任務
        query = TaskResult.objects.all()
        
        if status_filter != 'all':
            query = query.filter(status=status_filter.upper())
        
        tasks = query.order_by('-date_created')[:limit]
        
        # 任務名稱映射（中文顯示）
        task_name_map = {
            'api.tasks.sync_all_dhcp_logs_task': 'DHCP 日誌同步',
            'api.tasks.sync_jenkins_builds': 'Jenkins Builds 同步',
            'api.tasks.sync_jenkins_builds_adaptive': 'Jenkins Builds 智能同步',
            'api.tasks.check_nas_connection_task': 'NAS 連線檢測',
            'api.tasks.check_ntp_server_status_task': 'NTP 伺服器檢測',
            'api.tasks.sync_dhcp_logs_by_server_task': 'DHCP 日誌分伺服器同步',
            'api.tasks.cleanup_old_dhcp_logs_task': '清理舊 DHCP 日誌',
            'api.tasks.validate_jenkins_task': 'Jenkins 資料驗證',
            'api.tasks.cleanup_orphaned_jenkins_data_task': '清理孤立 Jenkins 資料',
            'api.tasks.cleanup_old_build_artifacts_task': '清理舊 Build Artifacts',
            'api.tasks.cleanup_invalid_ipxe_logs_task': '清理無效 iPXE 日誌',
        }
        
        result = []
        for task in tasks:
            # 計算執行時間
            duration = None
            if task.date_done and task.date_created:
                duration = (task.date_done - task.date_created).total_seconds()
            
            result.append({
                'task_id': task.task_id,
                'task_name': task.task_name,
                'display_name': task_name_map.get(task.task_name, task.task_name.split('.')[-1]),
                'status': task.status,
                'started_at': task.date_created.isoformat() if task.date_created else None,
                'finished_at': task.date_done.isoformat() if task.date_done else None,
                'duration': round(duration, 2) if duration else None,
                'args': task.task_args or '[]',
                'result': str(task.result) if task.result else None,
                'error': task.traceback if task.status == 'FAILURE' else None
            })
        
        logger.info(f'最近任務查詢成功: limit={limit}, status={status_filter}, found={len(result)}')
        
        return Response({
            'success': True,
            'data': {
                'tasks': result,
                'total': TaskResult.objects.count()
            }
        })
        
    except Exception as e:
        logger.error(f'獲取任務列表失敗: {e}', exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def task_trend(request):
    """
    獲取任務執行趨勢數據
    GET /api/system/task-trend/?time_range=1hour&interval=5
    
    查詢參數：
    - time_range: 1hour/6hours/24hours（預設 1hour）
    - interval: 數據點間隔（分鐘，預設 5）
    - top_n: 返回前 N 個高頻任務（預設 5）
    """
    try:
        from django_celery_results.models import TaskResult
        from django.db.models import Count
        from collections import defaultdict
        
        # 獲取查詢參數
        time_range = request.GET.get('time_range', '1hour')
        interval_minutes = int(request.GET.get('interval', 5))
        top_n = int(request.GET.get('top_n', 5))
        
        # 計算時間範圍
        now = timezone.now()
        if time_range == '1hour':
            start_time = now - timedelta(hours=1)
            total_minutes = 60
        elif time_range == '6hours':
            start_time = now - timedelta(hours=6)
            total_minutes = 360
        elif time_range == '24hours':
            start_time = now - timedelta(hours=24)
            total_minutes = 1440
        else:
            start_time = now - timedelta(hours=1)
            total_minutes = 60
        
        # 查詢時間範圍內的所有任務
        all_tasks = TaskResult.objects.filter(
            date_created__gte=start_time
        ).order_by('date_created')
        
        # 1. 統計各任務總執行次數，找出 TOP N
        task_counts = defaultdict(int)
        for task in all_tasks:
            task_counts[task.task_name] += 1
        
        # 排序並取前 N 個
        top_tasks = sorted(task_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]
        top_task_names = [task_name for task_name, _ in top_tasks]
        
        # 任務名稱映射（中文顯示）
        task_name_map = {
            'api.tasks.sync_all_dhcp_logs_task': 'DHCP 日誌同步',
            'api.tasks.sync_jenkins_builds': 'Jenkins Builds 同步',
            'api.tasks.sync_jenkins_builds_adaptive': 'Jenkins Builds 智能同步',
            'api.tasks.sync_active_jenkins_builds': 'Jenkins Active Builds',
            'api.tasks.check_nas_connection_task': 'NAS 連線檢測',
            'api.tasks.check_ntp_sync_task': 'NTP 伺服器檢測',
            'api.tasks.sync_dhcp_logs_by_server_task': 'DHCP 分伺服器同步',
            'api.tasks.cleanup_old_dhcp_logs_task': '清理舊 DHCP 日誌',
            'api.tasks.validate_jenkins_task': 'Jenkins 資料驗證',
            'api.tasks.store_jenkins_build_task': '存儲 Jenkins Build',
            'api.tasks.check_all_ipxe_network_quality_task': 'iPXE 網路質量檢測',
        }
        
        # 2. 按時間區間統計每個任務的執行次數
        data_points = []
        current_time = start_time
        
        while current_time < now:
            interval_end = current_time + timedelta(minutes=interval_minutes)
            
            # 統計這個時間區間內的任務執行次數
            interval_tasks = all_tasks.filter(
                date_created__gte=current_time,
                date_created__lt=interval_end
            )
            
            # 為每個 TOP 任務統計次數
            tasks_data = {}
            for task_name in top_task_names:
                count = interval_tasks.filter(task_name=task_name).count()
                display_name = task_name_map.get(task_name, task_name.split('.')[-1])
                tasks_data[display_name] = count
            
            data_points.append({
                'time': timezone.localtime(current_time).strftime('%H:%M'),
                **tasks_data
            })
            
            current_time = interval_end
        
        # 3. 計算頻率統計
        frequency_summary = {}
        for task_name, total_count in top_tasks:
            display_name = task_name_map.get(task_name, task_name.split('.')[-1])
            
            # 計算平均頻率
            per_minute = total_count / total_minutes if total_minutes > 0 else 0
            per_hour = per_minute * 60
            
            # 判斷執行間隔
            if per_minute >= 1:
                frequency_text = f"{per_minute:.1f}次/分鐘"
            elif per_hour >= 1:
                frequency_text = f"{per_hour:.1f}次/小時"
            else:
                avg_interval = total_minutes / total_count if total_count > 0 else 0
                frequency_text = f"每{avg_interval:.0f}分鐘"
            
            frequency_summary[display_name] = {
                'total': total_count,
                'per_minute': round(per_minute, 2),
                'per_hour': round(per_hour, 1),
                'frequency_text': frequency_text,
                'task_name': task_name
            }
        
        logger.info(f'任務趨勢查詢成功: range={time_range}, interval={interval_minutes}min, points={len(data_points)}')
        
        return Response({
            'success': True,
            'data': {
                'time_range': time_range,
                'interval_minutes': interval_minutes,
                'total_tasks': all_tasks.count(),
                'data_points': data_points,
                'frequency_summary': frequency_summary,
                'top_tasks': [
                    {
                        'name': task_name_map.get(name, name.split('.')[-1]),
                        'count': count,
                        'task_name': name
                    }
                    for name, count in top_tasks
                ]
            }
        })
        
    except Exception as e:
        logger.error(f'獲取任務趨勢失敗: {e}', exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)
