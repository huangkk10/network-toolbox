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
