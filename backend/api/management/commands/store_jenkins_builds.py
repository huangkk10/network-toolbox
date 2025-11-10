"""
Django 管理命令：批量存儲 Jenkins Builds 到 NAS

用法：
    # 存儲所有未存儲的 Builds
    python manage.py store_jenkins_builds
    
    # 限制處理數量
    python manage.py store_jenkins_builds --limit 50
    
    # 只存儲特定伺服器的 Builds
    python manage.py store_jenkins_builds --server-id 1
    
    # 只存儲特定 Job 的 Builds
    python manage.py store_jenkins_builds --job-name "SAF3202_KVM03"
    
    # 只存儲特定結果的 Builds
    python manage.py store_jenkins_builds --results SUCCESS FAILURE
    
    # 使用同步模式（不使用 Celery）
    python manage.py store_jenkins_builds --sync
    
    # 回填歷史 Builds（危險操作！）
    python manage.py store_jenkins_builds --backfill --days 7
"""

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.conf import settings
from api.models import JenkinsBuild, JenkinsServer, JenkinsJob
from api.tasks import store_jenkins_build_task
from library.services.jenkins_storage_service import JenkinsStorageService
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '批量存儲 Jenkins Builds 到 NAS'
    
    def add_arguments(self, parser):
        # 基本參數
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='限制處理的 Builds 數量（默認：無限制）'
        )
        
        parser.add_argument(
            '--server-id',
            type=int,
            default=None,
            help='只處理指定伺服器的 Builds'
        )
        
        parser.add_argument(
            '--job-name',
            type=str,
            default=None,
            help='只處理指定 Job 的 Builds'
        )
        
        parser.add_argument(
            '--results',
            nargs='+',
            default=None,
            choices=['SUCCESS', 'FAILURE', 'UNSTABLE', 'ABORTED', 'NOT_BUILT'],
            help='只處理指定結果的 Builds（可多選）'
        )
        
        # 執行模式
        parser.add_argument(
            '--sync',
            action='store_true',
            help='使用同步模式（不使用 Celery 任務）'
        )
        
        parser.add_argument(
            '--backfill',
            action='store_true',
            help='回填歷史 Builds（包含已存儲的，慎用！）'
        )
        
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='回填模式：只處理最近 N 天的 Builds（默認：7）'
        )
        
        # 顯示選項
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='演練模式：只顯示將要處理的 Builds，不實際執行'
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='顯示詳細日誌'
        )
    
    def handle(self, *args, **options):
        limit = options['limit']
        server_id = options['server_id']
        job_name = options['job_name']
        results = options['results']
        sync_mode = options['sync']
        backfill = options['backfill']
        days = options['days']
        dry_run = options['dry_run']
        verbose = options['verbose']
        
        # 設置日誌級別
        if verbose:
            logger.setLevel(logging.DEBUG)
        
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Jenkins Builds 批量存儲工具'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')
        
        # 構建查詢條件
        query = JenkinsBuild.objects.select_related('job', 'job__server')
        
        # 回填模式
        if backfill:
            self.stdout.write(self.style.WARNING(f'⚠️  回填模式：將處理最近 {days} 天的所有 Builds'))
            cutoff_date = timezone.now() - timedelta(days=days)
            query = query.filter(build_timestamp__gte=cutoff_date)
        else:
            # 正常模式：只處理未存儲的
            query = query.filter(
                is_workspace_stored=False,
                is_building=False,
                url__isnull=False
            )
        
        # 伺服器過濾
        if server_id:
            query = query.filter(job__server__id=server_id)
            try:
                server = JenkinsServer.objects.get(id=server_id)
                self.stdout.write(f'🔍 伺服器過濾：{server.name}')
            except JenkinsServer.DoesNotExist:
                raise CommandError(f'伺服器不存在：ID {server_id}')
        
        # Job 過濾
        if job_name:
            query = query.filter(job__name=job_name)
            self.stdout.write(f'🔍 Job 過濾：{job_name}')
        
        # 結果過濾
        if results:
            query = query.filter(result__in=results)
            self.stdout.write(f'🔍 結果過濾：{", ".join(results)}')
        elif not backfill:
            # 使用配置的默認過濾
            storage_policy = getattr(settings, 'JENKINS_STORAGE_POLICY', {})
            default_results = storage_policy.get('store_results', [])
            if default_results:
                query = query.filter(result__in=default_results)
                self.stdout.write(f'🔍 使用配置的結果過濾：{", ".join(default_results)}')
        
        # 排序：優先最新的
        query = query.order_by('-build_timestamp')
        
        # 限制數量
        if limit:
            query = query[:limit]
            self.stdout.write(f'🔢 限制數量：{limit}')
        
        self.stdout.write('')
        
        # 統計
        total_count = query.count()
        
        if total_count == 0:
            self.stdout.write(self.style.WARNING('❌ 沒有找到符合條件的 Builds'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'✅ 找到 {total_count} 個符合條件的 Builds'))
        self.stdout.write('')
        
        # 演練模式
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 演練模式：只顯示前 10 個 Builds'))
            self.stdout.write('')
            for i, build in enumerate(query[:10], 1):
                self.stdout.write(
                    f'{i}. [{build.job.server.name}] '
                    f'{build.job.name} #{build.build_number} - '
                    f'{build.result} | '
                    f'{build.build_timestamp.strftime("%Y-%m-%d %H:%M")}'
                )
            if total_count > 10:
                self.stdout.write(f'... 還有 {total_count - 10} 個')
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('💡 移除 --dry-run 參數以實際執行'))
            return
        
        # 確認執行
        if not backfill:
            self.stdout.write(self.style.WARNING(f'準備處理 {total_count} 個 Builds'))
        else:
            self.stdout.write(
                self.style.ERROR(
                    f'⚠️  警告：回填模式將重新處理 {total_count} 個 Builds，'
                    f'這可能會覆蓋現有資料並佔用大量 NAS 空間！'
                )
            )
        
        confirm = input('確定要繼續嗎？ (yes/no): ')
        if confirm.lower() not in ['yes', 'y']:
            self.stdout.write(self.style.ERROR('❌ 已取消'))
            return
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('🚀 開始處理...'))
        self.stdout.write('')
        
        # 統計
        processed = 0
        success_count = 0
        failed_count = 0
        skipped_count = 0
        
        # 處理每個 Build
        for build in query:
            processed += 1
            
            try:
                # 顯示進度
                progress = f'[{processed}/{total_count}]'
                build_info = f'{build.job.server.name} / {build.job.name} #{build.build_number}'
                
                if sync_mode:
                    # 同步模式：直接執行
                    self.stdout.write(f'{progress} 處理中... {build_info}')
                    
                    # 獲取伺服器 IP
                    server = build.job.server
                    server_ip = server.ip_address if server.ip_address else server.url.split('//')[1].split(':')[0]
                    
                    # 初始化存儲服務
                    storage_service = JenkinsStorageService(
                        jenkins_server_ip=server_ip,
                        job_name=build.job.name,
                        build_number=build.build_number
                    )
                    
                    # 檢查存儲路徑
                    path_check = storage_service.check_storage_path_accessible()
                    if not path_check.get('accessible') or not path_check.get('writable'):
                        self.stdout.write(
                            self.style.ERROR(
                                f'{progress} ❌ 失敗 - NAS 路徑不可訪問：'
                                f'{path_check.get("error")}'
                            )
                        )
                        failed_count += 1
                        continue
                    
                    # 構建 Workspace URL
                    workspace_url = f"{build.url}ws/"
                    
                    # 存儲 Workspace
                    result = storage_service.store_workspace(
                        workspace_url=workspace_url,
                        username=server.username,
                        api_token=server.api_token
                    )
                    
                    if result['success']:
                        # 更新 Build 記錄
                        build.workspace_path = result['workspace_path']
                        build.workspace_size = result['workspace_size']
                        build.workspace_stored_at = timezone.now()
                        build.is_workspace_stored = True
                        build.save(update_fields=[
                            'workspace_path', 'workspace_size',
                            'workspace_stored_at', 'is_workspace_stored'
                        ])
                        
                        size_mb = result['workspace_size'] / 1024 / 1024
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'{progress} ✅ 成功 - {size_mb:.2f} MB'
                            )
                        )
                        success_count += 1
                    else:
                        self.stdout.write(
                            self.style.ERROR(
                                f'{progress} ❌ 失敗 - {result.get("error", "Unknown")}'
                            )
                        )
                        failed_count += 1
                else:
                    # 異步模式：使用 Celery 任務
                    task = store_jenkins_build_task.delay(build.id)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'{progress} ✅ 任務已創建 - Task ID: {task.id}'
                        )
                    )
                    success_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'{progress} ❌ 異常 - {build_info}: {e}'
                    )
                )
                failed_count += 1
                
                if verbose:
                    logger.exception(f'處理 Build {build.id} 時發生異常')
        
        # 輸出總結
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('處理完成'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'總計處理：{processed}')
        self.stdout.write(self.style.SUCCESS(f'✅ 成功：{success_count}'))
        if failed_count > 0:
            self.stdout.write(self.style.ERROR(f'❌ 失敗：{failed_count}'))
        if skipped_count > 0:
            self.stdout.write(self.style.WARNING(f'⏭️  跳過：{skipped_count}'))
        
        if not sync_mode and success_count > 0:
            self.stdout.write('')
            self.stdout.write(
                self.style.WARNING(
                    f'💡 已創建 {success_count} 個 Celery 任務，'
                    '實際存儲進度可在 Celery Flower 中查看'
                )
            )
            self.stdout.write(self.style.WARNING('   http://localhost:5555'))
