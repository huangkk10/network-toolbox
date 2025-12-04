"""
Jenkins ViewSets

提供 Jenkins 伺服器、Job、Build 的 REST API 端點。
支援完整的 CRUD 操作、搜尋過濾、以及自訂操作。
"""

import logging
from typing import Optional
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db.models import Q, Count, Avg
from django.utils import timezone
from datetime import timedelta

from api.models import JenkinsServer, JenkinsJob, JenkinsBuild
from api.serializers import (
    JenkinsServerSerializer,
    JenkinsJobSerializer,
    JenkinsBuildSerializer,
    JenkinsBuildDetailSerializer,
)
from library.services.jenkins_client import JenkinsClient
from library.services.jenkins_storage_service import JenkinsStorageService
from library.utils import cache_jenkins_api, get_cache_stats

logger = logging.getLogger(__name__)


class JenkinsServerViewSet(viewsets.ModelViewSet):
    """
    Jenkins 伺服器管理 ViewSet
    
    提供 Jenkins 伺服器的完整 CRUD 操作。
    
    list: 獲取所有 Jenkins 伺服器列表
    retrieve: 獲取單個 Jenkins 伺服器詳情
    create: 創建新的 Jenkins 伺服器
    update: 更新 Jenkins 伺服器資訊
    destroy: 刪除 Jenkins 伺服器
    
    自訂操作：
    - test_connection: 測試伺服器連接
    - sync_jobs: 同步伺服器的所有 Job
    - statistics: 獲取伺服器統計資訊
    """
    
    queryset = JenkinsServer.objects.all().order_by('-created_at')
    serializer_class = JenkinsServerSerializer
    permission_classes = [AllowAny]  # 開發環境，生產環境改為 IsAuthenticated
    pagination_class = None  # 禁用分頁
    
    def get_queryset(self):
        """支援過濾和搜尋"""
        queryset = super().get_queryset()
        
        # 按狀態過濾
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # 搜尋（名稱或 URL）
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(url__icontains=search)
            )
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """
        測試 Jenkins 伺服器連接
        
        POST /api/jenkins-servers/{id}/test_connection/
        """
        server = self.get_object()
        
        client = None
        try:
            client = JenkinsClient(
                base_url=server.url,
                username=server.username,
                api_token=server.api_token
            )
            
            if client.test_connection():
                # 獲取伺服器資訊
                server_info = client.get_server_info()
                
                # 更新伺服器狀態
                server.status = 'online'
                server.last_sync_at = timezone.now()
                server.save()
                
                logger.info(f"Jenkins 伺服器連接成功: {server.name}")
                
                return Response({
                    'success': True,
                    'message': '連接成功',
                    'server_info': {
                        'description': server_info.get('nodeDescription', 'N/A'),
                        'jobs_count': len(server_info.get('jobs', [])),
                    }
                })
            else:
                server.status = 'offline'
                server.save()
                
                return Response({
                    'success': False,
                    'message': '連接失敗'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"測試 Jenkins 連接失敗: {e}", exc_info=True)
            server.status = 'offline'
            server.save()
            
            return Response({
                'success': False,
                'message': f'連接錯誤: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            client.close()
    
    @action(detail=True, methods=['post'])
    def sync_jobs(self, request, pk=None):
        """
        同步 Jenkins 伺服器的所有 Job
        
        POST /api/jenkins-servers/{id}/sync_jobs/
        """
        server = self.get_object()
        
        client = None
        try:
            client = JenkinsClient(
                base_url=server.url,
                username=server.username,
                api_token=server.api_token
            )
            
            # 獲取所有 Views
            views = client.list_views()
            
            # 建立 Job 到 View 的映射
            job_view_map = {}
            for view in views:
                view_name = view.get('name')
                # 跳過 "all" 視圖（包含所有 Job）
                if view_name == 'all':
                    continue
                
                try:
                    view_jobs = client.get_view_jobs(view_name)
                    for job_data in view_jobs:
                        job_name = job_data.get('name')
                        # 如果 Job 還沒有被分配到 View，或者當前 View 不是 "all"，則記錄
                        if job_name not in job_view_map:
                            job_view_map[job_name] = view_name
                except Exception as e:
                    logger.warning(f"無法獲取 View '{view_name}' 的 Job: {e}")
            
            # 獲取所有 Job 列表
            jobs = client.list_jobs()
            
            created_count = 0
            updated_count = 0
            
            for job_data in jobs:
                job_name = job_data.get('name')
                job_url = job_data.get('url')
                color = job_data.get('color', 'notbuilt')
                
                # 根據 color 判斷狀態和是否可構建
                is_disabled = color == 'disabled'
                is_buildable = color != 'disabled' and color != 'notbuilt'
                
                # 獲取 Job 所屬的 View
                view_name = job_view_map.get(job_name, '')
                
                # 創建或更新 Job
                job, created = JenkinsJob.objects.update_or_create(
                    server=server,
                    name=job_name,
                    defaults={
                        'url': job_url,
                        'full_name': job_name,
                        'is_buildable': is_buildable,
                        'is_disabled': is_disabled,
                        'view_name': view_name,
                        'last_sync_at': timezone.now(),
                    }
                )
                
                if created:
                    created_count += 1
                else:
                    updated_count += 1
            
            # 更新伺服器同步時間
            server.last_sync_at = timezone.now()
            server.save()
            
            logger.info(f"同步 Jenkins Job 完成: {server.name}, 新增 {created_count}, 更新 {updated_count}")
            
            return Response({
                'success': True,
                'message': '同步完成',
                'created': created_count,
                'updated': updated_count,
                'total': len(jobs)
            })
            
        except Exception as e:
            logger.error(f"同步 Jenkins Job 失敗: {e}", exc_info=True)
            return Response({
                'success': False,
                'message': f'同步錯誤: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            client.close()
    
    @action(detail=False, methods=['get'], url_path='global-statistics')
    def global_statistics(self, request):
        """
        獲取全局 Jenkins 統計資訊（支援時間範圍篩選）
        
        GET /api/jenkins-servers/global-statistics/?time_range=today
        
        Query Parameters:
        - time_range: 'today' | 'week' | '2weeks' | 'month' | 'all' (預設: 'today')
        
        Response:
        {
            "total_servers": 6,
            "total_jobs": 728,
            "period_builds": 156,
            "period_success": 89,
            "period_failure": 67,
            "success_rate": 57.1,
            "period_label": "今日",
            "period_start": "2025-11-17T00:00:00",
            "period_end": "2025-11-17T15:50:00",
            "time_range": "today"
        }
        """
        time_range = request.query_params.get('time_range', 'today')
        
        # 計算時間範圍
        end_time = timezone.now()
        start_time = None
        period_label = '全部'
        
        if time_range == 'today':
            start_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
            period_label = '今日'
        elif time_range == 'week':
            start_time = end_time - timedelta(days=7)
            period_label = '最近 7 天'
        elif time_range == '2weeks':
            start_time = end_time - timedelta(days=14)
            period_label = '最近 14 天'
        elif time_range == 'month':
            start_time = end_time - timedelta(days=30)
            period_label = '最近 30 天'
        else:  # 'all'
            start_time = None
            period_label = '全部'
        
        # 統計伺服器和 Jobs（不受時間範圍影響）
        total_servers = JenkinsServer.objects.count()
        total_jobs = JenkinsJob.objects.count()
        
        # 統計期間內的 Builds
        builds_query = JenkinsBuild.objects.all()
        if start_time:
            builds_query = builds_query.filter(build_timestamp__gte=start_time)
        
        period_builds = builds_query.count()
        period_success = builds_query.filter(result='SUCCESS').count()
        period_failure = builds_query.exclude(result='SUCCESS').count()
        
        # 計算成功率
        success_rate = (period_success / period_builds * 100) if period_builds > 0 else 0
        
        logger.info(f"全局統計查詢: time_range={time_range}, period_builds={period_builds}")
        
        return Response({
            'total_servers': total_servers,
            'total_jobs': total_jobs,
            'period_builds': period_builds,
            'period_success': period_success,
            'period_failure': period_failure,
            'success_rate': round(success_rate, 1),
            'period_label': period_label,
            'period_start': start_time.isoformat() if start_time else None,
            'period_end': end_time.isoformat(),
            'time_range': time_range,
        })
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """
        獲取 Jenkins 伺服器統計資訊
        
        GET /api/jenkins-servers/{id}/statistics/
        """
        server = self.get_object()
        
        # 統計資料
        total_jobs = server.jobs.count()
        total_builds = JenkinsBuild.objects.filter(job__server=server).count()
        
        # 最近 24 小時的 Build
        recent_time = timezone.now() - timedelta(hours=24)
        recent_builds = JenkinsBuild.objects.filter(
            job__server=server,
            build_timestamp__gte=recent_time
        ).count()
        
        # Build 狀態統計
        build_stats = JenkinsBuild.objects.filter(job__server=server).values('result').annotate(
            count=Count('id')
        )
        
        # 平均執行時間
        avg_duration = JenkinsBuild.objects.filter(
            job__server=server,
            duration__isnull=False
        ).aggregate(Avg('duration'))
        
        return Response({
            'server_id': server.id,
            'server_name': server.name,
            'total_jobs': total_jobs,
            'total_builds': total_builds,
            'recent_builds_24h': recent_builds,
            'build_status_distribution': list(build_stats),
            'average_duration': avg_duration['duration__avg'],
            'last_sync_at': server.last_sync_at,
        })


class JenkinsJobViewSet(viewsets.ModelViewSet):
    """
    Jenkins Job 管理 ViewSet
    
    提供 Jenkins Job 的完整 CRUD 操作。
    
    list: 獲取所有 Job 列表
    retrieve: 獲取單個 Job 詳情
    create: 創建新的 Job
    update: 更新 Job 資訊
    destroy: 刪除 Job
    
    自訂操作：
    - builds: 獲取 Job 的所有 Build
    - trigger_build: 觸發新的 Build（如果支援）
    - latest_build: 獲取最新的 Build
    """
    
    queryset = JenkinsJob.objects.all().select_related('server').order_by('-last_build_time')
    serializer_class = JenkinsJobSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    
    def get_queryset(self):
        """支援過濾和搜尋"""
        queryset = super().get_queryset()
        
        # 按伺服器過濾
        server_id = self.request.query_params.get('server_id')
        if server_id:
            queryset = queryset.filter(server_id=server_id)
        
        # 按 View 名稱過濾
        view_name = self.request.query_params.get('view_name')
        if view_name:
            queryset = queryset.filter(view_name=view_name)
        
        # 按 Build 狀態過濾（使用 last_build_status 欄位）
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(last_build_status=status_filter)
        
        # 🆕 按 Failed Stage 過濾（只顯示有該 failed_stage 的 Jobs）
        failed_stage = self.request.query_params.get('failed_stage')
        if failed_stage:
            # 找出有指定 failed_stage 的 Builds 所屬的 Job IDs
            from django.db.models import Exists, OuterRef
            
            queryset = queryset.filter(
                Exists(
                    JenkinsBuild.objects.filter(
                        job=OuterRef('pk'),
                        result='FAILURE',
                        failed_stage=failed_stage
                    )
                )
            )
            logger.info(f"Failed Stage 篩選: {failed_stage}")
        
        # 搜尋 Job 名稱
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)
        
        # 按 Build 日期範圍過濾（只返回在該日期範圍內有 Build 的 Jobs）
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date and end_date:
            from datetime import datetime, timedelta
            from django.db.models import Count, Q
            
            try:
                # 解析日期
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)  # 包含結束日期整天
                
                # 只保留在日期範圍內有 Build 的 Jobs
                queryset = queryset.annotate(
                    filtered_builds_count=Count(
                        'builds',
                        filter=Q(builds__build_timestamp__gte=start, builds__build_timestamp__lt=end)
                    )
                ).filter(filtered_builds_count__gt=0)
                
                logger.info(f"日期範圍篩選: {start_date} ~ {end_date}")
            except ValueError as e:
                logger.warning(f"日期格式錯誤: {e}")
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def builds(self, request, pk=None):
        """
        獲取 Job 的所有 Build（從資料庫獲取，包含 failed_stage）
        
        GET /api/jenkins-jobs/{id}/builds/
        支援參數：
        - limit: 限制返回數量（預設 10）
        - status: 按狀態過濾
        """
        job = self.get_object()
        
        # 限制數量
        limit = request.query_params.get('limit', 10)
        try:
            limit = int(limit)
        except ValueError:
            limit = 10
        
        try:
            # 從資料庫獲取 Builds
            builds_query = job.builds.all().order_by('-build_number')
            
            # 狀態過濾
            status_filter = request.query_params.get('status')
            if status_filter:
                builds_query = builds_query.filter(result=status_filter)
            
            # 日期範圍過濾
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            
            if start_date and end_date:
                from datetime import datetime, timedelta
                try:
                    start = datetime.strptime(start_date, '%Y-%m-%d')
                    end = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)  # 包含結束日期整天
                    builds_query = builds_query.filter(
                        build_timestamp__gte=start,
                        build_timestamp__lt=end
                    )
                    logger.info(f"Builds 日期範圍篩選: {start_date} ~ {end_date}")
                except ValueError as e:
                    logger.warning(f"日期格式錯誤: {e}")
            
            # 限制數量
            builds = builds_query[:limit]
            
            # 轉換為前端需要的格式
            builds_data = []
            for build in builds:
                # 格式化持續時間
                duration = build.duration / 1000 if build.duration else 0  # 轉換為秒
                if duration > 3600:
                    duration_str = f"{int(duration / 3600)} 小時 {int((duration % 3600) / 60)} 分"
                elif duration > 60:
                    duration_str = f"{int(duration / 60)} 分 {int(duration % 60)} 秒"
                else:
                    duration_str = f"{int(duration)} 秒"
                
                builds_data.append({
                    'id': build.id,  # 資料庫 ID
                    'build_number': build.build_number,
                    'result': build.result,
                    'failed_stage': build.failed_stage or None,  # ← 新增：失敗的 Stage
                    'build_timestamp': build.build_timestamp.strftime('%Y-%m-%d %H:%M:%S') if build.build_timestamp else 'N/A',
                    'duration': duration,
                    'duration_formatted': duration_str,
                    'url': build.url,
                    'building': build.is_building,
                })
            
            logger.info(f"從資料庫獲取 Job '{job.name}' 的 Builds: {len(builds_data)} 個")
            
            return Response({
                'job_id': job.id,
                'job_name': job.name,
                'total_builds': job.builds.count(),
                'builds': builds_data
            })
            
        except Exception as e:
            logger.error(f"獲取 Builds 失敗: {e}", exc_info=True)
            return Response({
                'job_id': job.id,
                'job_name': job.name,
                'total_builds': 0,
                'builds': [],
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def latest_build(self, request, pk=None):
        """
        獲取最新的 Build
        
        GET /api/jenkins-jobs/{id}/latest_build/
        """
        job = self.get_object()
        
        latest_build = job.builds.order_by('-build_number').first()
        
        if latest_build:
            serializer = JenkinsBuildDetailSerializer(latest_build)
            return Response(serializer.data)
        else:
            return Response({
                'message': 'No builds found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """
        獲取 Job 統計資訊
        
        GET /api/jenkins-jobs/{id}/statistics/
        """
        job = self.get_object()
        
        total_builds = job.builds.count()
        
        # Build 狀態統計
        build_stats = job.builds.values('result').annotate(count=Count('id'))
        
        # 成功率
        success_count = job.builds.filter(result='SUCCESS').count()
        success_rate = (success_count / total_builds * 100) if total_builds > 0 else 0
        
        # 平均執行時間
        avg_duration = job.builds.filter(duration__isnull=False).aggregate(
            Avg('duration')
        )
        
        # 最近 7 天的 Build 趨勢
        seven_days_ago = timezone.now() - timedelta(days=7)
        recent_builds = job.builds.filter(build_timestamp__gte=seven_days_ago).count()
        
        return Response({
            'job_id': job.id,
            'job_name': job.name,
            'total_builds': total_builds,
            'success_rate': round(success_rate, 2),
            'average_duration': avg_duration['duration__avg'],
            'build_status_distribution': list(build_stats),
            'recent_builds_7d': recent_builds,
            'last_build_time': job.last_build_time,
        })
    
    # ==================== Ansible Inventory 相關 API ====================
    
    def _get_build_inventory_path(self, job: 'JenkinsJob', build_number: int = None) -> tuple:
        """
        獲取指定 Build 或最新 Build 的 inventory/hosts 文件路徑
        
        Args:
            job: JenkinsJob 實例
            build_number: 指定的 Build 號碼，如果為 None 則使用最新 Build
        
        Returns:
            tuple: (inventory_path, build) 元組，如果不存在返回 (None, None)
        """
        from django.conf import settings
        from pathlib import Path
        
        # 根據是否指定 build_number 來獲取 Build
        if build_number is not None:
            # 獲取指定的 Build
            build = job.builds.filter(
                build_number=build_number,
                is_artifacts_stored=True
            ).first()
            
            if not build:
                logger.warning(f"Job {job.name} Build #{build_number} 不存在或沒有 artifacts")
                return None, None
        else:
            # 獲取最新的 Build（有 artifacts 的）
            build = job.builds.filter(is_artifacts_stored=True).order_by('-build_number').first()
            
            if not build:
                logger.warning(f"Job {job.name} 沒有包含 artifacts 的 Build")
                return None, None
        
        # 檢查是否有 artifacts_path
        if not build.artifacts_path:
            logger.warning(f"Build {build.build_number} 沒有 artifacts_path")
            return None, None
        
        # 構建 inventory 文件路徑（使用 artifacts_path）
        artifacts_path = Path(build.artifacts_path)
        inventory_path = artifacts_path / 'inventory' / 'hosts'
        
        if not inventory_path.exists():
            logger.warning(f"Inventory 文件不存在: {inventory_path}")
            return None, None
        
        return str(inventory_path), build
    
    def _get_latest_build_inventory_path(self, job: 'JenkinsJob') -> Optional[str]:
        """
        獲取最新 Build 的 inventory/hosts 文件路徑（向後兼容）
        
        Args:
            job: JenkinsJob 實例
        
        Returns:
            str: inventory 文件路徑，如果不存在返回 None
        """
        inventory_path, _ = self._get_build_inventory_path(job)
        return inventory_path
    
    @action(detail=True, methods=['get'], url_path='ansible-inventory')
    def ansible_inventory(self, request, pk=None):
        """
        獲取完整 Ansible Inventory
        
        GET /api/jenkins-jobs/{id}/ansible-inventory/
        
        Query Parameters:
            - use_cache: 是否使用快取（默認 true）
            - force_refresh: 強制刷新（清除快取後重新解析）
            - build_number: 指定 Build 號碼（可選，默認使用最新 Build）
        
        Returns:
            完整的 inventory JSON 數據
        """
        from library.services.ansible_inventory_service import AnsibleInventoryService
        
        job = self.get_object()
        use_cache = request.query_params.get('use_cache', 'true').lower() == 'true'
        force_refresh = request.query_params.get('force_refresh', 'false').lower() == 'true'
        
        # 獲取指定的 build_number（可選）
        build_number_str = request.query_params.get('build_number')
        build_number = int(build_number_str) if build_number_str else None
        
        # 獲取 inventory 文件路徑（支援指定 build_number）
        inventory_path, build = self._get_build_inventory_path(job, build_number)
        if not inventory_path:
            error_msg = f'Build #{build_number} 沒有 inventory 文件' if build_number else '該 Job 沒有包含 inventory/hosts 的 Build'
            return Response({
                'success': False,
                'error': '找不到 inventory 文件',
                'message': error_msg
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            service = AnsibleInventoryService(inventory_path)
            
            # 強制刷新：先清除快取
            if force_refresh:
                service.clear_cache('all')
                use_cache = False
            
            # 獲取數據
            result = service.get_full_inventory(use_cache=use_cache)
            
            if result['success']:
                return Response({
                    'success': True,
                    'job_id': job.id,
                    'job_name': job.name,
                    'build_number': build.build_number,
                    'cached': result['cached'],
                    'inventory_path': inventory_path,
                    'data': result['data']
                })
            else:
                return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except FileNotFoundError as e:
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Inventory 文件不存在'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"獲取 Ansible Inventory 失敗: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e),
                'message': '獲取 inventory 失敗'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'], url_path='ansible-inventory/hosts')
    def ansible_inventory_hosts(self, request, pk=None):
        """
        獲取主機列表
        
        GET /api/jenkins-jobs/{id}/ansible-inventory/hosts/
        
        Query Parameters:
            - use_cache: 是否使用快取（默認 true）
            - build_number: 指定 Build 號碼（可選，默認使用最新 Build）
        
        Returns:
            主機列表摘要（hostname, IP, device_number, groups）
        """
        from library.services.ansible_inventory_service import AnsibleInventoryService
        
        job = self.get_object()
        use_cache = request.query_params.get('use_cache', 'true').lower() == 'true'
        
        # 獲取指定的 build_number（可選）
        build_number_str = request.query_params.get('build_number')
        build_number = int(build_number_str) if build_number_str else None
        
        inventory_path, build = self._get_build_inventory_path(job, build_number)
        if not inventory_path:
            return Response({
                'success': False,
                'error': '找不到 inventory 文件'
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            service = AnsibleInventoryService(inventory_path)
            result = service.list_all_hosts(use_cache=use_cache)
            
            if result['success']:
                return Response({
                    'success': True,
                    'job_id': job.id,
                    'job_name': job.name,
                    'build_number': build.build_number,
                    'cached': result['cached'],
                    'total_hosts': result['total_hosts'],
                    'hosts': result['hosts']
                })
            else:
                return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"獲取主機列表失敗: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'], url_path='ansible-inventory/hosts/(?P<hostname>[^/.]+)')
    def ansible_inventory_host_config(self, request, pk=None, hostname=None):
        """
        獲取特定主機配置
        
        GET /api/jenkins-jobs/{id}/ansible-inventory/hosts/{hostname}/
        
        Query Parameters:
            - use_cache: 是否使用快取（默認 true）
            - build_number: 指定 Build 號碼（可選，默認使用最新 Build）
        
        Returns:
            {
                'success': True,
                'hostname': '主機名稱',
                'config': {
                    # 主機的完整配置（包括從群組繼承的所有變量）
                    'ansible_host': 'IP 地址',
                    'ansible_user': '主機使用者',
                    'ansible_password': '主機密碼',
                    'uart_host': 'UART 主機名稱',
                    ...
                },
                'uart_config': {
                    # UART 主機的完整配置（如果 uart_host 是 hostname）
                    'hostname': 'UART 主機名稱',
                    'ansible_host': 'UART IP',
                    'ansible_user': 'UART 使用者',
                    'ansible_password': 'UART 密碼',
                    'ansible_port': UART SSH 端口,
                    'uart_logger_upload_dir': 'UART Logger 目錄'
                } or null  # 如果沒有 uart_host 或 uart_host 是 IP 則為 null
            }
        """
        from library.services.ansible_inventory_service import AnsibleInventoryService
        
        job = self.get_object()
        use_cache = request.query_params.get('use_cache', 'true').lower() == 'true'
        
        # 獲取指定的 build_number（可選）
        build_number_str = request.query_params.get('build_number')
        build_number = int(build_number_str) if build_number_str else None
        
        inventory_path, build = self._get_build_inventory_path(job, build_number)
        if not inventory_path:
            return Response({
                'success': False,
                'error': '找不到 inventory 文件'
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            service = AnsibleInventoryService(inventory_path)
            result = service.get_host_config(hostname, use_cache=use_cache)
            
            if result['success']:
                config = result['config']
                uart_config = None  # 預設值
                
                # 增強功能：自動解析 UART hostname 並獲取 UART 主機完整配置
                if 'uart_host' in config and config['uart_host']:
                    uart_host = config['uart_host']
                    
                    # 檢查是否為 hostname（非 IP 格式）
                    import re
                    ip_pattern = r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
                    is_ip = bool(re.match(ip_pattern, uart_host))
                    
                    if not is_ip:
                        # uart_host 是 hostname，獲取其完整配置
                        logger.info(f"Fetching UART host config for: {uart_host}")
                        uart_result = service.get_host_config(uart_host, use_cache=use_cache)
                        
                        if uart_result['success']:
                            uart_cfg = uart_result['config']
                            # 構建 UART 配置物件
                            uart_config = {
                                'hostname': uart_host,
                                'ansible_host': uart_cfg.get('ansible_host'),
                                'ansible_user': uart_cfg.get('ansible_user'),
                                'ansible_password': uart_cfg.get('ansible_password'),
                                'ansible_port': uart_cfg.get('ansible_port', 22),
                                # 可選：其他 UART 相關配置
                                'uart_logger_upload_dir': uart_cfg.get('uart_logger_upload_dir')
                            }
                            logger.info(f"✅ Retrieved UART config for {uart_host}: user={uart_config['ansible_user']}, host={uart_config['ansible_host']}")
                            
                            # 相容性處理：保留舊的 UART_IP 欄位
                            if uart_config['ansible_host']:
                                config['UART_IP'] = uart_config['ansible_host']
                                config['UART_HOSTNAME'] = uart_host
                        else:
                            logger.warning(f"⚠️ Failed to get UART config for {uart_host}: {uart_result.get('error')}")
                    else:
                        # uart_host 已經是 IP 格式，無法獲取更多資訊
                        logger.info(f"uart_host is IP format: {uart_host}, skipping config lookup")
                        config['UART_IP'] = uart_host
                
                return Response({
                    'success': True,
                    'job_id': job.id,
                    'job_name': job.name,
                    'build_number': build.build_number,
                    'cached': result['cached'],
                    'hostname': hostname,
                    'config': config,
                    'uart_config': uart_config  # 新增：UART 主機配置
                })
            else:
                return Response(result, status=status.HTTP_404_NOT_FOUND)
                
        except Exception as e:
            logger.error(f"獲取主機配置失敗: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['delete'], url_path='ansible-inventory/cache')
    def clear_ansible_cache(self, request, pk=None):
        """
        清除快取
        
        DELETE /api/jenkins-jobs/{id}/ansible-inventory/cache/
        
        Query Parameters:
            - cache_type: 'all' | 'full_inventory' | 'hosts_list' | 'host_config'（默認 'all'）
            - hostname: 當 cache_type='host_config' 時指定主機名
        
        Returns:
            清除結果
        """
        from library.services.ansible_inventory_service import AnsibleInventoryService
        
        job = self.get_object()
        cache_type = request.query_params.get('cache_type', 'all')
        hostname = request.query_params.get('hostname')
        
        inventory_path = self._get_latest_build_inventory_path(job)
        if not inventory_path:
            return Response({
                'success': False,
                'error': '找不到 inventory 文件'
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            service = AnsibleInventoryService(inventory_path)
            result = service.clear_cache(cache_type, hostname)
            
            return Response({
                **result,
                'job_id': job.id,
                'job_name': job.name
            })
            
        except Exception as e:
            logger.error(f"清除快取失敗: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'], url_path='ansible-inventory/cache/statistics')
    def ansible_cache_statistics(self, request, pk=None):
        """
        獲取快取統計信息
        
        GET /api/jenkins-jobs/{id}/ansible-inventory/cache/statistics/
        
        Returns:
            快取統計（是否存在、是否有效、大小、過期時間等）
        """
        from library.services.ansible_inventory_service import AnsibleInventoryService
        
        job = self.get_object()
        
        inventory_path = self._get_latest_build_inventory_path(job)
        if not inventory_path:
            return Response({
                'success': False,
                'error': '找不到 inventory 文件'
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            service = AnsibleInventoryService(inventory_path)
            stats = service.get_cache_statistics()
            
            latest_build = job.builds.filter(is_artifacts_stored=True).order_by('-build_number').first()
            
            return Response({
                'success': True,
                'job_id': job.id,
                'job_name': job.name,
                'build_number': latest_build.build_number if latest_build else None,
                **stats
            })
            
        except Exception as e:
            logger.error(f"獲取快取統計失敗: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class JenkinsBuildViewSet(viewsets.ModelViewSet):
    """
    Jenkins Build 管理 ViewSet
    
    提供 Jenkins Build 的完整 CRUD 操作。
    
    list: 獲取所有 Build 列表
    retrieve: 獲取單個 Build 詳情
    create: 創建新的 Build 記錄
    update: 更新 Build 資訊
    destroy: 刪除 Build
    
    自訂操作：
    - console_log: 獲取 Build 的控制台日誌
    - config_file: 獲取 Build 的配置文件
    - artifacts: 獲取 Build 的產物列表
    - aggregate_data: 聚合資料庫和文件系統的數據
    """
    
    queryset = JenkinsBuild.objects.all().select_related('job', 'job__server').order_by('-build_timestamp')
    serializer_class = JenkinsBuildSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    
    def get_serializer_class(self):
        """根據操作選擇序列化器"""
        if self.action == 'retrieve':
            return JenkinsBuildDetailSerializer
        return JenkinsBuildSerializer
    
    def get_queryset(self):
        """支援過濾和搜尋"""
        queryset = super().get_queryset()
        
        # 按 Job 過濾
        job_id = self.request.query_params.get('job_id')
        if job_id:
            queryset = queryset.filter(job_id=job_id)
        
        # 按伺服器過濾
        server_id = self.request.query_params.get('server_id')
        if server_id:
            queryset = queryset.filter(job__server_id=server_id)
        
        # 按狀態過濾
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(result=status_filter)
        
        # 按日期範圍過濾
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(build_timestamp__gte=start_date)
        if end_date:
            queryset = queryset.filter(build_timestamp__lte=end_date)
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def console_log(self, request, pk=None):
        """
        獲取 Build 的控制台日誌（增強版）
        
        GET /api/jenkins-builds/{id}/console_log/
        
        支援參數：
        - from_nas: 是否從 NAS 讀取（默認 false）
        - tail: 返回最後 N 行（可選）
        - prefer_nas: 優先從 NAS 讀取，失敗則回退到 Jenkins API（默認 false）
        """
        build = self.get_object()
        from_nas = request.query_params.get('from_nas', 'false').lower() == 'true'
        prefer_nas = request.query_params.get('prefer_nas', 'false').lower() == 'true'
        tail_lines = request.query_params.get('tail')
        
        log_content = None
        source = None
        
        try:
            # ===== 🆕 修改：支援從 NAS 讀取 =====
            if from_nas or prefer_nas:
                # 檢查是否有 NAS 路徑
                if build.log_file_path:
                    logger.info(f'嘗試從 NAS 讀取 Console Log: {build.log_file_path}')
                    
                    # 使用 JenkinsStorageService 讀取
                    from library.services.jenkins_storage_service import JenkinsStorageService
                    
                    server = build.job.server
                    server_ip = server.ip_address if server.ip_address else server.url.split('//')[1].split(':')[0]
                    
                    storage_service = JenkinsStorageService(
                        jenkins_server_ip=server_ip,
                        job_name=build.job.name,
                        build_number=build.build_number
                    )
                    
                    # 轉換 tail_lines
                    tail = int(tail_lines) if tail_lines else None
                    
                    log_result = storage_service.read_console_log(tail_lines=tail)
                    
                    if log_result['success']:
                        log_content = log_result['log_content']
                        source = 'nas'
                        logger.info(f'從 NAS 讀取成功: {log_result["log_size"]} bytes')
                    else:
                        logger.warning(f'從 NAS 讀取失敗: {log_result.get("error")}')
                        
                        # 如果是 from_nas=true，直接返回錯誤
                        if from_nas:
                            return Response({
                                'success': False,
                                'message': f'從 NAS 讀取失敗: {log_result.get("error")}'
                            }, status=status.HTTP_404_NOT_FOUND)
                else:
                    # NAS 路徑不存在
                    if from_nas:
                        return Response({
                            'success': False,
                            'message': 'Console Log 尚未存儲到 NAS'
                        }, status=status.HTTP_404_NOT_FOUND)
            
            # ===== 如果 NAS 讀取失敗或未啟用，從 Jenkins API 獲取 =====
            if log_content is None:
                logger.info(f'從 Jenkins API 獲取 Console Log')
                
                client = JenkinsClient(
                    base_url=build.job.server.url,
                    username=build.job.server.username,
                    api_token=build.job.server.api_token
                )
                
                try:
                    log_content = client.get_console_log(
                        build.job.name,
                        build.build_number
                    )
                    source = 'jenkins_api'
                    
                    # 如果指定了 tail，處理
                    if tail_lines:
                        try:
                            tail = int(tail_lines)
                            lines = log_content.split('\n')
                            log_content = '\n'.join(lines[-tail:])
                        except ValueError:
                            pass
                            
                finally:
                    client.close()
            
            return Response({
                'success': True,
                'build_id': build.id,
                'job_name': build.job.name,
                'build_number': build.build_number,
                'log_content': log_content,
                'source': source,  # 'nas' 或 'jenkins_api'
                'nas_available': bool(build.log_file_path)  # 是否有 NAS 備份
            })
            
        except Exception as e:
            logger.error(f"獲取 Build 日誌失敗: {e}", exc_info=True)
            return Response({
                'success': False,
                'message': f'獲取日誌失敗: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def store_workspace(self, request, pk=None):
        """
        存儲 Build Workspace 到 NAS
        
        POST /api/jenkins-builds/{id}/store_workspace/
        
        將 Jenkins Build 的 Workspace 下載並存儲到 NAS 上。
        存儲路徑：{NAS_BASE}/jenkins_test_storage/{jenkins_ip}/{job_name}/{build_number}/workspace/
        
        Returns:
            {
                'success': bool,
                'message': str,
                'workspace_path': str,
                'workspace_size': int (bytes),
                'files_count': int,
                'stored_at': str (ISO 時間),
                'error': str (如果失敗)
            }
        """
        build = self.get_object()
        
        # 檢查是否已經存儲
        if build.is_workspace_stored:
            return Response({
                'success': True,
                'message': 'Workspace 已經存儲過了',
                'workspace_path': build.workspace_path,
                'workspace_size': build.workspace_size,
                'stored_at': build.workspace_stored_at.isoformat() if build.workspace_stored_at else None,
                'already_stored': True
            })
        
        try:
            # 解析 Jenkins Server IP
            jenkins_url = build.job.server.url
            import re
            match = re.search(r'https?://([^:/]+)', jenkins_url)
            if not match:
                return Response({
                    'success': False,
                    'error': '無法解析 Jenkins Server IP'
                }, status=status.HTTP_400_BAD_REQUEST)
            jenkins_ip = match.group(1)
            
            # 構建 Workspace URL
            # 例如：http://10.252.170.187:8080/job/SAF3201_KVM02/4/ws/
            workspace_url = f"{build.url}ws/"
            
            logger.info(f"開始存儲 Build #{build.build_number} Workspace")
            logger.info(f"  - Jenkins IP: {jenkins_ip}")
            logger.info(f"  - Job: {build.job.name}")
            logger.info(f"  - Workspace URL: {workspace_url}")
            
            # 創建存儲服務
            storage = JenkinsStorageService(
                jenkins_server_ip=jenkins_ip,
                job_name=build.job.name,
                build_number=build.build_number
            )
            
            # 檢查 NAS 路徑是否可訪問
            path_check = storage.check_storage_path_accessible()
            if not path_check['accessible']:
                return Response({
                    'success': False,
                    'error': f"NAS 路徑不可訪問: {path_check.get('error', 'Unknown error')}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            if not path_check['writable']:
                return Response({
                    'success': False,
                    'error': 'NAS 路徑不可寫'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # 存儲 Workspace
            result = storage.store_workspace(
                workspace_url=workspace_url,
                username=build.job.server.username,
                api_token=build.job.server.api_token
            )
            
            if result['success']:
                # 更新 Build 記錄
                build.workspace_path = result['workspace_path']
                build.workspace_size = result['workspace_size']
                build.workspace_stored_at = timezone.now()
                build.is_workspace_stored = True
                build.save()
                
                logger.info(f"Build #{build.build_number} Workspace 存儲成功")
                logger.info(f"  - 路徑: {result['workspace_path']}")
                logger.info(f"  - 大小: {result['workspace_size'] / (1024**2):.2f} MB")
                logger.info(f"  - 文件數: {result['files_count']}")
                
                return Response({
                    'success': True,
                    'message': 'Workspace 存儲成功',
                    'workspace_path': result['workspace_path'],
                    'workspace_size': result['workspace_size'],
                    'files_count': result['files_count'],
                    'stored_at': result['stored_at'],
                })
            else:
                logger.error(f"Build #{build.build_number} Workspace 存儲失敗: {result.get('error')}")
                return Response({
                    'success': False,
                    'error': result.get('error', 'Unknown error')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"存儲 Workspace 失敗: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': f'存儲失敗: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def artifacts(self, request, pk=None):
        """
        獲取 Build 的 Artifacts 列表
        
        GET /api/jenkins-builds/{id}/artifacts/
        
        支援參數：
        - from_nas: 是否從 NAS 讀取（預設 false，從 Jenkins API 獲取）
        
        Returns:
            {
                'success': bool,
                'build_id': int,
                'build_number': int,
                'artifacts_count': int,
                'total_size': int,
                'artifacts': [
                    {
                        'fileName': str,
                        'relativePath': str,
                        'size': int,
                        'displayPath': str,
                        'download_url': str
                    }
                ],
                'source': 'nas' | 'jenkins_api'
            }
        """
        build = self.get_object()
        from_nas = request.query_params.get('from_nas', 'false').lower() == 'true'
        
        try:
            if from_nas:
                # 從 NAS 讀取
                if not build.is_artifacts_stored:
                    return Response({
                        'success': False,
                        'message': 'Artifacts 尚未存儲到 NAS'
                    }, status=status.HTTP_404_NOT_FOUND)
                
                # 返回存儲時的 artifacts_list
                return Response({
                    'success': True,
                    'build_id': build.id,
                    'build_number': build.build_number,
                    'artifacts_count': build.artifacts_count,
                    'total_size': build.artifacts_size,
                    'artifacts': build.artifacts_list,
                    'artifacts_path': build.artifacts_path,
                    'stored_at': build.artifacts_stored_at.isoformat() if build.artifacts_stored_at else None,
                    'source': 'nas'
                })
            else:
                # 從 Jenkins API 獲取
                client = JenkinsClient(
                    base_url=build.job.server.url,
                    username=build.job.server.username,
                    api_token=build.job.server.api_token
                )
                
                try:
                    artifacts_list = client.get_build_artifacts(
                        build.job.name,
                        build.build_number
                    )
                    
                    # 獲取每個 Artifact 的大小
                    total_size = 0
                    for artifact in artifacts_list:
                        size = client.get_artifact_size(
                            build.job.name,
                            build.build_number,
                            artifact['relativePath']
                        )
                        artifact['size'] = size
                        total_size += size
                        
                        # 添加下載 URL
                        artifact['download_url'] = (
                            f"{build.job.server.url}/job/{build.job.name}/"
                            f"{build.build_number}/artifact/{artifact['relativePath']}"
                        )
                    
                finally:
                    client.close()
                
                return Response({
                    'success': True,
                    'build_id': build.id,
                    'build_number': build.build_number,
                    'artifacts_count': len(artifacts_list),
                    'total_size': total_size,
                    'artifacts': artifacts_list,
                    'source': 'jenkins_api'
                })
                
        except Exception as e:
            logger.error(f"獲取 Artifacts 失敗: {e}", exc_info=True)
            return Response({
                'success': False,
                'message': f'獲取 Artifacts 失敗: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def store_artifacts(self, request, pk=None):
        """
        存儲 Build Artifacts 到 NAS
        
        POST /api/jenkins-builds/{id}/store_artifacts/
        
        將 Jenkins Build 的 Artifacts 下載並存儲到 NAS 上。
        存儲路徑：{NAS_BASE}/jenkins_test_storage/{jenkins_ip}/{job_name}/{build_number}/artifacts/
        
        Returns:
            {
                'success': bool,
                'message': str,
                'artifacts_path': str,
                'artifacts_size': int (bytes),
                'artifacts_count': int,
                'stored_items': List[Dict],
                'failed_items': List[Dict],
                'error': str (如果失敗)
            }
        """
        build = self.get_object()
        
        # 檢查是否已經存儲
        if build.is_artifacts_stored:
            return Response({
                'success': True,
                'message': 'Artifacts 已經存儲過了',
                'artifacts_path': build.artifacts_path,
                'artifacts_size': build.artifacts_size,
                'artifacts_count': build.artifacts_count,
                'stored_at': build.artifacts_stored_at.isoformat() if build.artifacts_stored_at else None,
                'already_stored': True
            })
        
        try:
            # 1. 從 Jenkins 獲取 Artifacts 列表
            client = JenkinsClient(
                base_url=build.job.server.url,
                username=build.job.server.username,
                api_token=build.job.server.api_token
            )
            
            try:
                artifacts_list = client.get_build_artifacts(
                    build.job.name,
                    build.build_number
                )
            finally:
                client.close()
            
            # 如果沒有 Artifacts
            if not artifacts_list:
                # 標記為已存儲（避免重複檢查）
                build.is_artifacts_stored = True
                build.artifacts_count = 0
                build.artifacts_stored_at = timezone.now()
                build.save()
                
                return Response({
                    'success': True,
                    'message': '該 Build 沒有 Artifacts',
                    'artifacts_count': 0
                })
            
            # 2. 解析 Jenkins Server IP
            jenkins_url = build.job.server.url
            import re
            match = re.search(r'https?://([^:/]+)', jenkins_url)
            if not match:
                return Response({
                    'success': False,
                    'error': '無法解析 Jenkins Server IP'
                }, status=status.HTTP_400_BAD_REQUEST)
            jenkins_ip = match.group(1)
            
            logger.info(f"開始存儲 Build #{build.build_number} Artifacts")
            logger.info(f"  - Jenkins IP: {jenkins_ip}")
            logger.info(f"  - Job: {build.job.name}")
            logger.info(f"  - Artifacts 數量: {len(artifacts_list)}")
            
            # 3. 創建存儲服務並存儲
            storage = JenkinsStorageService(
                jenkins_server_ip=jenkins_ip,
                job_name=build.job.name,
                build_number=build.build_number
            )
            
            # 檢查 NAS 路徑是否可訪問
            path_check = storage.check_storage_path_accessible()
            if not path_check['accessible']:
                return Response({
                    'success': False,
                    'error': f"NAS 路徑不可訪問: {path_check.get('error', 'Unknown error')}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            if not path_check['writable']:
                return Response({
                    'success': False,
                    'error': 'NAS 路徑不可寫'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            result = storage.store_artifacts(
                artifacts_list=artifacts_list,
                job_name=build.job.name,
                build_number=build.build_number,
                username=build.job.server.username,
                api_token=build.job.server.api_token
            )
            
            if result['success']:
                # 更新 Build 記錄
                build.artifacts_path = result['artifacts_path']
                build.artifacts_size = result['artifacts_size']
                build.artifacts_count = result['artifacts_count']
                build.artifacts_list = result['stored_items']
                build.artifacts_stored_at = timezone.now()
                build.is_artifacts_stored = True
                build.save()
                
                logger.info(f"Build #{build.build_number} Artifacts 存儲成功")
                logger.info(f"  - 路徑: {result['artifacts_path']}")
                logger.info(f"  - 總大小: {result['artifacts_size'] / (1024**2):.2f} MB")
                logger.info(f"  - 檔案數: {result['artifacts_count']}")
                
                return Response({
                    'success': True,
                    'message': 'Artifacts 存儲成功',
                    'artifacts_path': result['artifacts_path'],
                    'artifacts_size': result['artifacts_size'],
                    'artifacts_count': result['artifacts_count'],
                    'stored_items': result['stored_items'],
                    'stored_at': result['stored_at'],
                })
            else:
                logger.error(f"Build #{build.build_number} Artifacts 存儲失敗: {result.get('error')}")
                return Response({
                    'success': False,
                    'error': result.get('error', 'Unknown error'),
                    'failed_items': result.get('failed_items', [])
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"存儲 Artifacts 失敗: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': f'存儲失敗: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def config_file(self, request, pk=None):
        """
        獲取 Build 的配置文件（Phase 4 功能，尚未實現）
        
        GET /api/jenkins-builds/{id}/config_file/
        """
        return Response({
            'success': False,
            'message': 'NAS 存儲服務功能尚未實現（Phase 4）'
        }, status=status.HTTP_501_NOT_IMPLEMENTED)
    
    @action(detail=True, methods=['get'])
    def aggregate_data(self, request, pk=None):
        """
        聚合 Build 的所有數據（資料庫 + 文件系統）（Phase 4 功能，尚未實現）
        
        GET /api/jenkins-builds/{id}/aggregate_data/
        """
        return Response({
            'success': False,
            'message': 'NAS 存儲服務功能尚未實現（Phase 4）'
        }, status=status.HTTP_501_NOT_IMPLEMENTED)
    
    @action(detail=False, methods=['get'])
    def cache_stats(self, request):
        """
        獲取緩存統計資訊
        
        GET /api/jenkins-builds/cache_stats/
        """
        try:
            stats = get_cache_stats()
            return Response(stats)
        except Exception as e:
            logger.error(f"獲取緩存統計失敗: {e}", exc_info=True)
            return Response({
                'success': False,
                'message': f'獲取統計失敗: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get', 'post'])
    def pipeline_stages(self, request, pk=None):
        """
        獲取或同步 Build 的 Pipeline Stage 資訊（Blue Ocean）
        
        GET /api/jenkins-builds/{id}/pipeline_stages/
        返回已存儲的 Pipeline Stage 資訊
        
        POST /api/jenkins-builds/{id}/pipeline_stages/
        從 Jenkins Blue Ocean API 同步最新的 Pipeline Stage 資訊
        
        Returns:
            {
                'success': bool,
                'build_id': int,
                'build_number': int,
                'result': str,
                'failed_stage': str,
                'pipeline_summary': {
                    'total_stages': int,
                    'successful_stages': int,
                    'failed_stages': int,
                    'unstable_stages': int,
                    'aborted_stages': int
                },
                'stages': [
                    {
                        'name': str,
                        'result': str,
                        'duration_ms': int,
                        'duration_formatted': str,
                        'error_message': str (可選)
                    }
                ],
                'failed_stages': [...]  # 只包含失敗的 Stage
            }
        """
        build = self.get_object()
        client = None
        
        try:
            # POST 請求：從 Jenkins 同步資料
            if request.method == 'POST':
                server = build.job.server
                
                # 創建 Jenkins 客戶端
                client = JenkinsClient(
                    base_url=server.url,
                    username=server.username,
                    api_token=server.api_token
                )
                
                # 獲取 Pipeline Nodes
                nodes = client.get_blue_ocean_pipeline_nodes(build.job.name, build.build_number)
                
                if not nodes:
                    return Response({
                        'success': False,
                        'message': '無法獲取 Pipeline Stage 資訊（可能不是 Pipeline Job 或 Blue Ocean 未安裝）'
                    }, status=status.HTTP_404_NOT_FOUND)
                
                # 提取 Stage 資訊
                stages = [
                    {
                        'id': node.get('id'),
                        'name': node.get('displayName'),
                        'result': node.get('result'),
                        'state': node.get('state'),
                        'duration_ms': node.get('durationInMillis', 0),
                        'start_time': node.get('startTime'),
                        'type': node.get('type'),
                        'error': node.get('error')
                    }
                    for node in nodes if node.get('type') == 'STAGE'
                ]
                
                # 找出失敗的 Stage
                failed_stages_list = client.get_failed_stages(build.job.name, build.build_number)
                failed_stage_name = failed_stages_list[0]['stage_name'] if failed_stages_list else ''
                
                # 更新資料庫
                build.pipeline_stages = stages
                build.failed_stage = failed_stage_name
                build.save(update_fields=['pipeline_stages', 'failed_stage'])
                
                logger.info(f"同步 Build #{build.build_number} 的 Pipeline Stage 資訊: {len(stages)} 個 Stage, 失敗: {failed_stage_name}")
            
            # GET 或 POST 後都返回相同格式的資料
            stages_data = build.pipeline_stages if isinstance(build.pipeline_stages, list) else []
            
            # 統計資訊
            pipeline_summary = {
                'total_stages': len(stages_data),
                'successful_stages': sum(1 for s in stages_data if s.get('result') == 'SUCCESS'),
                'failed_stages': sum(1 for s in stages_data if s.get('result') == 'FAILURE'),
                'unstable_stages': sum(1 for s in stages_data if s.get('result') == 'UNSTABLE'),
                'aborted_stages': sum(1 for s in stages_data if s.get('result') == 'ABORTED'),
            }
            
            # 格式化 Stage 資訊
            formatted_stages = []
            failed_stages = []
            
            for stage in stages_data:
                duration_ms = stage.get('duration_ms', 0)
                duration_sec = duration_ms / 1000 if duration_ms else 0
                
                if duration_sec >= 60:
                    duration_formatted = f"{int(duration_sec / 60)} 分 {int(duration_sec % 60)} 秒"
                else:
                    duration_formatted = f"{duration_sec:.1f} 秒"
                
                stage_info = {
                    'name': stage.get('name'),
                    'result': stage.get('result'),
                    'duration_ms': duration_ms,
                    'duration_formatted': duration_formatted,
                }
                
                # 添加錯誤訊息（如果有）
                if stage.get('error'):
                    stage_info['error_message'] = stage['error'].get('message', 'Unknown error')
                
                formatted_stages.append(stage_info)
                
                # 收集失敗的 Stage
                if stage.get('result') in ['FAILURE', 'UNSTABLE', 'ABORTED']:
                    failed_stages.append(stage_info)
            
            return Response({
                'success': True,
                'build_id': build.id,
                'build_number': build.build_number,
                'job_name': build.job.name,
                'result': build.result,
                'failed_stage': build.failed_stage,
                'pipeline_summary': pipeline_summary,
                'stages': formatted_stages,
                'failed_stages': failed_stages,
            })
            
        except Exception as e:
            logger.error(f"處理 Pipeline Stage 資訊失敗: {e}", exc_info=True)
            return Response({
                'success': False,
                'message': f'處理失敗: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            if client:
                client.close()
    
    @action(detail=False, methods=['get'])
    def check_nas_status(self, request):
        """
        檢查 NAS 存儲狀態
        
        GET /api/jenkins-builds/check_nas_status/
        """
        try:
            import os
            from django.conf import settings
            
            # 檢查存儲服務
            service = JenkinsStorageService('test', 'test', 1)
            result = service.check_storage_path_accessible()
            
            # 額外檢查：列出掛載點內容
            mount_point = settings.JENKINS_STORAGE_BASE_PATH
            mount_status = {
                'mount_point': mount_point,
                'exists': os.path.exists(mount_point),
                'is_dir': os.path.isdir(mount_point) if os.path.exists(mount_point) else False,
                'writable': result.get('writable', False),
            }
            
            # 嘗試列出目錄內容
            if mount_status['exists'] and mount_status['is_dir']:
                try:
                    mount_status['contents'] = os.listdir(mount_point)[:10]  # 最多列出 10 項
                except Exception as e:
                    mount_status['list_error'] = str(e)
            
            return Response({
                'success': result.get('accessible', False) and result.get('writable', False),
                'nas_check': result,
                'mount_status': mount_status,
            })
        except Exception as e:
            logger.error(f"檢查 NAS 狀態失敗: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def validate_config(self, request, pk=None):
        """
        檢查 Build 配置是否有問題
        
        POST /api/jenkins-builds/{id}/validate_config/
        
        Request Body (可選):
            {
                'dhcp_server_id': int  # 可選，指定要查詢的 DHCP Server ID
            }
        
        Returns:
            {
                'build_id': int,
                'job_name': str,
                'build_number': int,
                'overall_status': 'passed' | 'warning' | 'failed',
                'check_results': [
                    {
                        'item': 'host_ip' | 'host_mac' | 'uart_ip',
                        'status': 'passed' | 'warning' | 'failed',
                        'value': str,
                        'message': str,
                        'details': {}
                    }
                ],
                'checked_at': str (ISO 時間)
            }
        """
        from library.services.build_config_validator import BuildConfigValidator
        
        build = self.get_object()
        
        # 獲取可選的 dhcp_server_id（將單個 ID 轉換為列表）
        dhcp_server_id = request.data.get('dhcp_server_id')
        dhcp_server_ids = [dhcp_server_id] if dhcp_server_id else None
        
        try:
            # 創建檢查器並執行檢查
            validator = BuildConfigValidator(build.id, dhcp_server_ids=dhcp_server_ids)
            result = validator.validate()
            
            # 新增：存儲結果到 NAS
            self._save_config_validation_result(build, result, auto_triggered=False)
            
            logger.info(f"Build #{build.build_number} 配置檢查完成: {result['overall_status']}")
            
            return Response(result)
            
        except Exception as e:
            logger.error(f"配置檢查失敗: {e}", exc_info=True)
            return Response({
                'success': False,
                'message': f'檢查失敗: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # ========== Config Validation 輔助方法 ==========
    
    def _get_server_ip(self, server):
        """從 JenkinsServer 獲取 IP 地址
        
        優先使用 ip_address 欄位，若為空則從 url 或 name 推導
        """
        from urllib.parse import urlparse
        
        if not server:
            return None
        
        # 優先使用 ip_address 欄位
        if server.ip_address:
            return server.ip_address
        
        # 嘗試從 URL 解析
        if server.url:
            try:
                parsed = urlparse(server.url)
                host = parsed.hostname
                if host:
                    return host
            except Exception:
                pass
        
        # 使用 name 作為備選
        if server.name:
            return server.name
        
        return None
    
    def _get_config_validation_path(self, build):
        """獲取 config_validation.json 的路徑"""
        from django.conf import settings
        from pathlib import Path
        
        if not build.job or not build.job.server:
            return None
        
        server_ip = self._get_server_ip(build.job.server)
        job_name = build.job.name
        build_number = build.build_number
        
        # 檢查必要欄位
        if not server_ip or not job_name or build_number is None:
            logger.warning(f'Build #{build.id} 缺少必要欄位: server_ip={server_ip}, job_name={job_name}, build_number={build_number}')
            return None
        
        base_path = Path(settings.JENKINS_STORAGE_BASE_PATH)
        validation_path = base_path / server_ip / job_name / str(build_number) / 'config_validation.json'
        
        return validation_path

    def _save_config_validation_result(self, build, result, auto_triggered=False):
        """存儲配置檢查結果到 NAS"""
        from django.utils import timezone
        import json
        
        validation_path = self._get_config_validation_path(build)
        
        if not validation_path:
            logger.warning(f'無法獲取 Build #{build.id} 的存儲路徑')
            return False
        
        # 確保目錄存在
        validation_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 添加 build_info
        result['build_info'] = {
            'build_id': build.id,
            'job_name': build.job.name if build.job else 'Unknown',
            'build_number': build.build_number,
            'build_result': build.result,
            'validated_at': timezone.now().isoformat(),
            'auto_triggered': auto_triggered
        }
        
        try:
            with open(validation_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            logger.info(f'✅ 配置檢查結果已存儲: {validation_path}')
            return True
        except Exception as e:
            logger.error(f'❌ 存儲配置檢查結果失敗: {e}', exc_info=True)
            return False

    # ========== Config Validation API ==========
    
    @action(detail=True, methods=['get'], url_path='has_config_validation')
    def has_config_validation(self, request, pk=None):
        """
        檢查 Build 是否有配置檢查結果
        
        GET /api/jenkins-builds/{id}/has_config_validation/
        
        Returns:
            {
                'has_validation': bool,
                'overall_status': str | null,
                'validated_at': str | null,
                'file_path': str | null
            }
        """
        import json
        
        build = self.get_object()
        
        # 檢查 JSON 文件是否存在
        validation_path = self._get_config_validation_path(build)
        
        if validation_path and validation_path.exists():
            try:
                with open(validation_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                logger.info(f'[API] Config Validation 已存在: Build #{build.id}')
                
                return Response({
                    'has_validation': True,
                    'overall_status': data.get('overall_status'),
                    'validated_at': data.get('build_info', {}).get('validated_at'),
                    'file_path': str(validation_path)
                })
            except Exception as e:
                logger.error(f'[API] 讀取 config_validation.json 失敗: {e}', exc_info=True)
        
        return Response({
            'has_validation': False,
            'overall_status': None,
            'validated_at': None,
            'file_path': None
        })
    
    @action(detail=True, methods=['get'], url_path='config_validation')
    def config_validation(self, request, pk=None):
        """
        獲取 Build 的配置檢查完整內容
        
        GET /api/jenkins-builds/{id}/config_validation/
        
        Returns:
            完整的 config_validation.json 內容
        """
        import json
        
        build = self.get_object()
        
        validation_path = self._get_config_validation_path(build)
        
        if not validation_path or not validation_path.exists():
            return Response({
                'error': 'Config validation file not found',
                'hint': 'Validation may not have been performed yet'
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            with open(validation_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f'[API] 返回 Config Validation: Build #{build.id}')
            return Response(data)
        except Exception as e:
            logger.error(f'[API] 讀取 config_validation.json 失敗: {e}', exc_info=True)
            return Response({
                'error': f'Failed to read validation file: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'], url_path='failed-stages')
    def failed_stages(self, request):
        """
        獲取所有唯一的 Failed Stage 列表
        
        GET /api/jenkins-builds/failed-stages/
        
        Query Parameters:
        - server_id: 可選，按伺服器過濾
        - start_date: 可選，開始日期
        - end_date: 可選，結束日期
        
        Returns:
            {
                'failed_stages': ['Stage1', 'Stage2', ...],
                'count': int
            }
        """
        try:
            # 基礎查詢：只查詢 FAILURE 且有 failed_stage 的 Build
            queryset = JenkinsBuild.objects.filter(
                result='FAILURE',
                failed_stage__isnull=False
            ).exclude(failed_stage='')
            
            # 按伺服器過濾
            server_id = request.query_params.get('server_id')
            if server_id:
                queryset = queryset.filter(job__server_id=server_id)
            
            # 按日期範圍過濾
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            if start_date:
                queryset = queryset.filter(build_timestamp__gte=start_date)
            if end_date:
                queryset = queryset.filter(build_timestamp__lte=end_date)
            
            # 獲取唯一的 failed_stage 值並排序
            failed_stages = list(
                queryset.values_list('failed_stage', flat=True)
                .distinct()
                .order_by('failed_stage')
            )
            
            logger.info(f"獲取 Failed Stages 列表: {len(failed_stages)} 個")
            
            return Response({
                'failed_stages': failed_stages,
                'count': len(failed_stages)
            })
            
        except Exception as e:
            logger.error(f'獲取 Failed Stages 列表失敗: {e}', exc_info=True)
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'], url_path='has_fatal_analysis')
    def has_fatal_analysis(self, request, pk=None):
        """
        檢查 Build 是否有 Fatal Error 分析結果
        
        GET /api/jenkins-builds/{id}/has_fatal_analysis/
        
        Returns:
            {
                'has_analysis': bool,
                'fatal_count': int | null,
                'analyzed_at': str | null,
                'file_path': str | null
            }
        """
        build = self.get_object()
        
        # 只有 FAILURE Build 才可能有分析
        if build.result != 'FAILURE':
            return Response({
                'has_analysis': False,
                'reason': 'Not a FAILURE build'
            })
        
        # 檢查 JSON 文件是否存在
        if build.log_file_path:
            from pathlib import Path
            import json
            
            try:
                # fatal_analysis.json 與 console.log 在同一目錄
                log_path = Path(build.log_file_path)
                analysis_path = log_path.parent / 'fatal_analysis.json'
                
                if analysis_path.exists():
                    # 讀取 JSON 文件獲取摘要資訊
                    with open(analysis_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    logger.info(f'[API] Fatal Analysis 已存在: Build #{build.id}')
                    
                    return Response({
                        'has_analysis': True,
                        'fatal_count': data['summary'].get('total_fatal_count', 0),
                        'analyzed_at': data['build_info'].get('analyzed_at'),
                        'file_path': str(analysis_path)
                    })
                else:
                    logger.debug(f'[API] Fatal Analysis 檔案不存在: {analysis_path}')
                    
            except Exception as e:
                logger.error(f'[API] 檢查 Fatal Analysis 失敗: {e}', exc_info=True)
                return Response({
                    'has_analysis': False,
                    'reason': f'Error reading analysis file: {str(e)}'
                })
        
        return Response({
            'has_analysis': False,
            'reason': 'Console log not found'
        })
    
    @action(detail=True, methods=['get'], url_path='fatal_analysis')
    def fatal_analysis(self, request, pk=None):
        """
        獲取 Build 的 Fatal Error 分析完整內容
        
        GET /api/jenkins-builds/{id}/fatal_analysis/
        
        Returns:
            {
                'build_info': {...},
                'summary': {...},
                'fatal_tasks': [...]
            }
        """
        build = self.get_object()
        
        # 只有 FAILURE Build 才可能有分析
        if build.result != 'FAILURE':
            return Response({
                'error': 'Not a FAILURE build'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 檢查 Console Log 是否存在
        if not build.log_file_path:
            return Response({
                'error': 'Console log not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        from pathlib import Path
        import json
        
        try:
            # fatal_analysis.json 與 console.log 在同一目錄
            log_path = Path(build.log_file_path)
            analysis_path = log_path.parent / 'fatal_analysis.json'
            
            if not analysis_path.exists():
                return Response({
                    'error': 'Fatal analysis file not found',
                    'hint': 'Analysis may not have been performed yet'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # 讀取分析結果
            with open(analysis_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            # 轉換 fatal_tasks 為前端期望的格式
            # 每個 fatal_occurrence 作為一個獨立的 Task
            raw_tasks = raw_data.get('fatal_tasks', [])
            transformed_tasks = []
            task_index = 1
            
            for task in raw_tasks:
                occurrences = task.get('fatal_occurrences', [])
                
                # 將每個 occurrence 轉換為一個獨立的 Task
                for occ in occurrences:
                    # 從 context_lines 提取 Task 名稱
                    context_lines = occ.get('context_lines', [])
                    task_name = 'Unknown Task'
                    
                    # 嘗試從 context_lines 中找到 TASK [...] 或 - name: 行
                    for line in context_lines:
                        # Ansible TASK 格式: TASK [role : task name]
                        if 'TASK [' in line and ']' in line:
                            start = line.find('TASK [') + 6
                            end = line.find(']', start)
                            if end > start:
                                task_name = line[start:end].strip()
                                break
                        # Ansible playbook 格式: - name: task name
                        elif '- name:' in line:
                            start = line.find('- name:') + 7
                            task_name = line[start:].strip()
                            # 移除時間戳和其他前綴
                            if ']' in task_name:
                                task_name = task_name.split(']', 1)[1].strip()
                            break
                    
                    # 使用 context_lines 作為 task_content
                    task_content = '\n'.join(context_lines)
                    task_total_lines = len(context_lines)
                    
                    # 從 line_content 提取 Fatal 時間戳
                    line_content = occ.get('line_content', '')
                    task_start_time = 'N/A'
                    if line_content.startswith('[') and ']' in line_content:
                        end_bracket = line_content.find(']')
                        if end_bracket > 0:
                            timestamp = line_content[1:end_bracket]
                            # 提取時間部分 (HH:MM:SS)
                            if 'T' in timestamp:
                                time_part = timestamp.split('T')[1].split('.')[0] if '.' in timestamp else timestamp.split('T')[1].split('Z')[0]
                                task_start_time = time_part
                    
                    transformed_task = {
                        'task_index': task_index,
                        'task_name': task_name,
                        'task_start_time': task_start_time,
                        'fatal_count': 1,  # 每個 Task 只有一個 Fatal
                        'task_start_line': occ.get('line_number', 0),
                        'task_end_line': occ.get('line_number', 0),
                        'task_total_lines': task_total_lines,
                        'task_content': task_content,
                        'fatal_line_numbers': [occ.get('line_number', 0)],
                        'fatal_snippets': [line_content]
                    }
                    transformed_tasks.append(transformed_task)
                    task_index += 1
            
            # 轉換為前端期望的扁平化格式
            response_data = {
                # 扁平化 build_info
                'analyzed_at': raw_data['build_info'].get('analyzed_at'),
                'total_lines': raw_data['build_info'].get('total_lines', 0),
                
                # 扁平化 summary (並修正欄位名稱)
                'fatal_count': raw_data['summary'].get('total_fatal_count', 0),
                
                # 轉換後的 fatal_tasks
                'fatal_tasks': transformed_tasks
            }
            
            logger.info(
                f'[API] 返回 Fatal Analysis: Build #{build.id} | '
                f'Fatal Count: {response_data["fatal_count"]}'
            )
            
            return Response(response_data)
            
        except json.JSONDecodeError as e:
            logger.error(f'[API] Fatal Analysis JSON 格式錯誤: {e}', exc_info=True)
            return Response({
                'error': 'Invalid JSON format in analysis file'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except Exception as e:
            logger.error(f'[API] 讀取 Fatal Analysis 失敗: {e}', exc_info=True)
            return Response({
                'error': f'Failed to read analysis file: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ========== Standalone API Functions ==========

from rest_framework.decorators import api_view, permission_classes


@api_view(['GET'])
@permission_classes([AllowAny])
def jenkins_build_trend(request):
    """
    Jenkins Build 趨勢分析 API
    
    提供基於時間範圍的構建趨勢數據，支援按小時或按日聚合。
    
    Query Parameters:
    - time_range: 'today' | 'week' | '2weeks' | 'month' | 'all' (預設: 'today')
    - granularity: 'hourly' | 'daily' (預設: 根據 time_range 自動選擇)
    - server_id: int | 'all' (預設: 'all')
    
    Returns:
    [
        {
            'time': '2025-11-17 14:00',  # 或 '11/17' (daily)
            'total_builds': 45,
            'success_count': 32,
            'failure_count': 13,
            'success_rate': 71.1
        },
        ...
    ]
    """
    time_range = request.query_params.get('time_range', 'today')
    granularity = request.query_params.get('granularity', None)
    server_id = request.query_params.get('server_id', 'all')
    
    try:
        # 計算時間範圍
        end_time = timezone.now()
        start_time = None
        
        # 自動選擇粒度（如果未指定）
        if not granularity:
            if time_range in ['today']:
                granularity = 'hourly'
            else:
                granularity = 'daily'
        
        if time_range == 'today':
            start_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_range == 'week':
            start_time = end_time - timedelta(days=7)
        elif time_range == '2weeks':
            start_time = end_time - timedelta(days=14)
        elif time_range == 'month':
            start_time = end_time - timedelta(days=30)
        else:  # 'all'
            # 對於 'all'，取最早的 Build 時間
            earliest_build = JenkinsBuild.objects.order_by('build_timestamp').first()
            if earliest_build:
                start_time = earliest_build.build_timestamp
            else:
                start_time = end_time - timedelta(days=30)  # 預設 30 天
        
        # 構建查詢
        builds_query = JenkinsBuild.objects.filter(build_timestamp__gte=start_time)
        
        # 按 server_id 過濾
        if server_id != 'all':
            try:
                server_id_int = int(server_id)
                builds_query = builds_query.filter(job__server_id=server_id_int)
            except (ValueError, TypeError):
                pass  # 忽略無效的 server_id
        
        # 生成趨勢數據
        trend_data = []
        
        if granularity == 'hourly':
            # 按小時聚合
            current_time = start_time
            while current_time <= end_time:
                next_time = current_time + timedelta(hours=1)
                
                hour_builds = builds_query.filter(
                    build_timestamp__gte=current_time,
                    build_timestamp__lt=next_time
                )
                
                total_builds = hour_builds.count()
                success_count = hour_builds.filter(result='SUCCESS').count()
                failure_count = total_builds - success_count
                success_rate = (success_count / total_builds * 100) if total_builds > 0 else 0
                
                trend_data.append({
                    'time': current_time.strftime('%m/%d %H:%M'),
                    'total_builds': total_builds,
                    'success_count': success_count,
                    'failure_count': failure_count,
                    'success_rate': round(success_rate, 1)
                })
                
                current_time = next_time
        
        else:  # daily
            # 按天聚合
            current_date = start_time.date()
            end_date = end_time.date()
            
            while current_date <= end_date:
                date_start = timezone.make_aware(
                    timezone.datetime.combine(current_date, timezone.datetime.min.time())
                )
                date_end = timezone.make_aware(
                    timezone.datetime.combine(current_date, timezone.datetime.max.time())
                )
                
                day_builds = builds_query.filter(
                    build_timestamp__gte=date_start,
                    build_timestamp__lte=date_end
                )
                
                total_builds = day_builds.count()
                success_count = day_builds.filter(result='SUCCESS').count()
                failure_count = total_builds - success_count
                success_rate = (success_count / total_builds * 100) if total_builds > 0 else 0
                
                trend_data.append({
                    'time': current_date.strftime('%m/%d'),
                    'total_builds': total_builds,
                    'success_count': success_count,
                    'failure_count': failure_count,
                    'success_rate': round(success_rate, 1)
                })
                
                current_date += timedelta(days=1)
        
        logger.info(f"Jenkins 趨勢查詢: time_range={time_range}, granularity={granularity}, points={len(trend_data)}")
        
        return Response(trend_data)
    
    except Exception as e:
        logger.error(f'獲取 Jenkins 趨勢資料失敗: {str(e)}', exc_info=True)
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

