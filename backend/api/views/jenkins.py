"""
Jenkins ViewSets

提供 Jenkins 伺服器、Job、Build 的 REST API 端點。
支援完整的 CRUD 操作、搜尋過濾、以及自訂操作。
"""

import logging
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
# from library.services.jenkins_storage_service import JenkinsStorageService  # Phase 4 功能，暫時註釋
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
        
        # 按狀態過濾
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # 搜尋 Job 名稱
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def builds(self, request, pk=None):
        """
        獲取 Job 的所有 Build（從 Jenkins 實時獲取）
        
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
        
        client = None
        try:
            # 從 Jenkins 實時獲取 Builds
            client = JenkinsClient(
                base_url=job.server.url,
                username=job.server.username,
                api_token=job.server.api_token
            )
            
            jenkins_builds = client.get_job_builds(job.name, limit=limit)
            
            # 轉換為前端需要的格式
            builds_data = []
            for build in jenkins_builds:
                # 格式化時間戳
                timestamp = build.get('timestamp', 0) / 1000  # Jenkins 返回毫秒
                from datetime import datetime
                build_time = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S') if timestamp else 'N/A'
                
                # 格式化持續時間
                duration = build.get('duration', 0) / 1000  # 轉換為秒
                if duration > 3600:
                    duration_str = f"{int(duration / 3600)} 小時 {int((duration % 3600) / 60)} 分"
                elif duration > 60:
                    duration_str = f"{int(duration / 60)} 分 {int(duration % 60)} 秒"
                else:
                    duration_str = f"{int(duration)} 秒"
                
                builds_data.append({
                    'id': f"jenkins-{job.id}-{build.get('number')}",  # 臨時 ID
                    'build_number': build.get('number'),
                    'result': build.get('result') or ('RUNNING' if build.get('building') else 'UNKNOWN'),
                    'build_timestamp': build_time,
                    'duration': duration,
                    'duration_formatted': duration_str,
                    'url': build.get('url'),
                    'building': build.get('building', False),
                })
            
            # 狀態過濾（在前端數據上過濾）
            status_filter = request.query_params.get('status')
            if status_filter:
                builds_data = [b for b in builds_data if b['result'] == status_filter]
            
            logger.info(f"從 Jenkins 獲取 Job '{job.name}' 的 Builds: {len(builds_data)} 個")
            
            return Response({
                'job_id': job.id,
                'job_name': job.name,
                'total_builds': len(jenkins_builds),
                'builds': builds_data
            })
            
        except Exception as e:
            logger.error(f"獲取 Jenkins Builds 失敗: {e}", exc_info=True)
            return Response({
                'job_id': job.id,
                'job_name': job.name,
                'total_builds': 0,
                'builds': [],
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            if client:
                client.close()
    
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
        獲取 Build 的控制台日誌
        
        GET /api/jenkins-builds/{id}/console_log/
        
        支援參數：
        - from_nas: 是否從 NAS 讀取（預設 false，從 Jenkins API 獲取）
        - tail: 返回最後 N 行（可選）
        """
        build = self.get_object()
        from_nas = request.query_params.get('from_nas', 'false').lower() == 'true'
        tail_lines = request.query_params.get('tail')
        
        try:
            if from_nas:
                # 從 NAS 讀取（Phase 4 功能，尚未實現）
                return Response({
                    'success': False,
                    'message': 'NAS 存儲服務功能尚未實現（Phase 4）'
                }, status=status.HTTP_501_NOT_IMPLEMENTED)
            else:
                # 從 Jenkins API 獲取
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
                finally:
                    client.close()
            
            # 如果指定了 tail，只返回最後 N 行
            if tail_lines:
                try:
                    tail_lines = int(tail_lines)
                    lines = log_content.split('\n')
                    log_content = '\n'.join(lines[-tail_lines:])
                except ValueError:
                    pass
            
            return Response({
                'build_id': build.id,
                'job_name': build.job.name,
                'build_number': build.build_number,
                'log_content': log_content,
                'source': 'nas' if from_nas else 'jenkins_api'
            })
            
        except Exception as e:
            logger.error(f"獲取 Build 日誌失敗: {e}", exc_info=True)
            return Response({
                'success': False,
                'message': f'獲取日誌失敗: {str(e)}'
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
