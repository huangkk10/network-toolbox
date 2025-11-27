"""
補充缺失的 Fatal Error 分析

用法:
    python manage.py analyze_missing_fatal_errors --limit 20 --days 7
    python manage.py analyze_missing_fatal_errors --sync  # 同步執行（不用 Celery）
"""

from django.core.management.base import BaseCommand
from api.models import JenkinsBuild
from pathlib import Path
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '補充缺失的 Fatal Error 分析'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=20,
            help='處理的最大 Build 數量（默認 20）'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='檢查最近幾天的 Builds（默認 7 天）'
        )
        parser.add_argument(
            '--sync',
            action='store_true',
            help='同步執行（不使用 Celery，直接執行分析）'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只檢查不執行'
        )

    def handle(self, *args, **options):
        limit = options['limit']
        days = options['days']
        sync = options['sync']
        dry_run = options['dry_run']

        self.stdout.write('=' * 70)
        self.stdout.write(self.style.SUCCESS('🔍 掃描缺失的 Fatal Error 分析'))
        self.stdout.write('=' * 70)
        self.stdout.write(f'參數: Limit={limit}, Days={days}, Sync={sync}, Dry-Run={dry_run}')
        self.stdout.write('')

        # 計算時間範圍
        time_threshold = timezone.now() - timedelta(days=days)

        # 查詢已存儲的 FAILURE Builds
        query = JenkinsBuild.objects.filter(
            result='FAILURE',
            is_workspace_stored=True,
            log_file_path__isnull=False,
            is_building=False,
            build_timestamp__gte=time_threshold
        ).select_related('job', 'job__server').order_by('-build_timestamp')

        total_failure_builds = query.count()
        self.stdout.write(f'📊 找到 {total_failure_builds} 個已存儲的 FAILURE Builds')

        # 檢查缺少分析的 Builds
        missing_builds = []
        for build in query:
            try:
                log_path = Path(build.log_file_path)
                analysis_file = log_path.parent / 'fatal_analysis.json'

                if not analysis_file.exists():
                    missing_builds.append(build)

                    if len(missing_builds) >= limit:
                        break
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠️  檢查失敗: {build.job.name} #{build.build_number} - {e}'
                    )
                )

        total_missing = len(missing_builds)
        self.stdout.write(
            self.style.WARNING(
                f'🔴 缺少 Fatal 分析: {total_missing} / {total_failure_builds}'
            )
        )
        self.stdout.write('')

        if total_missing == 0:
            self.stdout.write(self.style.SUCCESS('✅ 所有 FAILURE Builds 都已有 Fatal 分析！'))
            return

        # 顯示缺少分析的 Builds
        self.stdout.write('缺少分析的 Builds:')
        for i, build in enumerate(missing_builds, 1):
            self.stdout.write(
                f'  [{i:2d}] {build.job.name} #{build.build_number} '
                f'({build.build_timestamp.strftime("%Y-%m-%d %H:%M")})'
            )
        self.stdout.write('')

        if dry_run:
            self.stdout.write(self.style.WARNING('ℹ️  Dry-run 模式，不執行分析'))
            return

        # 執行分析
        if sync:
            # 同步執行
            self.stdout.write(self.style.WARNING('⚙️  同步執行模式（直接分析）'))
            self.stdout.write('')

            from api.tasks import store_jenkins_build_task

            success_count = 0
            error_count = 0

            for i, build in enumerate(missing_builds, 1):
                self.stdout.write(
                    f'[{i}/{total_missing}] 分析 {build.job.name} #{build.build_number}...',
                    ending=' '
                )

                try:
                    result = store_jenkins_build_task(build.id)

                    if result.get('success'):
                        fatal_count = result.get('fatal_count', 0)
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'✅ 完成 (Fatal: {fatal_count})'
                            )
                        )
                        success_count += 1
                    else:
                        error = result.get('error', 'Unknown')
                        self.stdout.write(
                            self.style.ERROR(f'❌ 失敗: {error}')
                        )
                        error_count += 1

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'❌ 異常: {e}')
                    )
                    error_count += 1

            self.stdout.write('')
            self.stdout.write('=' * 70)
            self.stdout.write(self.style.SUCCESS(f'✅ 成功: {success_count}'))
            self.stdout.write(self.style.ERROR(f'❌ 失敗: {error_count}'))
            self.stdout.write(f'📊 總計: {total_missing}')

        else:
            # 異步執行（使用 Celery）
            self.stdout.write(self.style.WARNING('🚀 異步執行模式（使用 Celery）'))
            self.stdout.write('')

            from api.tasks import auto_analyze_missing_fatal_errors_task

            # 觸發 Celery 任務
            task = auto_analyze_missing_fatal_errors_task.delay(
                limit=limit,
                days=days
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Celery 任務已創建: {task.id}'
                )
            )
            self.stdout.write('')
            self.stdout.write('使用以下命令查看任務狀態:')
            self.stdout.write(f'  celery -A network_toolbox inspect active')
            self.stdout.write('')
            self.stdout.write('或查看 Celery Worker 日誌:')
            self.stdout.write('  docker compose logs celery_worker -f')
