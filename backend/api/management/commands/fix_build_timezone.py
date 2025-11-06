"""
修復資料庫中 JenkinsBuild 的時區問題
將所有 naive datetime 轉換為 aware datetime (UTC)
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
import pytz
from api.models import JenkinsBuild


class Command(BaseCommand):
    help = '修復 JenkinsBuild 資料表中的時區問題，將 naive datetime 轉換為 aware datetime'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只檢查不修改',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS('🔧 修復 JenkinsBuild 時區問題'))
        self.stdout.write("=" * 80)
        self.stdout.write("")
        
        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️  DRY RUN 模式（不會實際修改資料）'))
            self.stdout.write("")
        
        # 獲取所有 Build
        all_builds = JenkinsBuild.objects.all()
        total = all_builds.count()
        
        self.stdout.write(f"總共有 {total} 個 Build 記錄")
        self.stdout.write("")
        
        # 統計
        naive_count = 0
        aware_count = 0
        fixed_count = 0
        error_count = 0
        
        self.stdout.write("開始檢查和修復...")
        self.stdout.write("")
        
        for i, build in enumerate(all_builds, 1):
            try:
                # 檢查 build_timestamp
                if build.build_timestamp.tzinfo is None:
                    # Naive datetime - 需要修復
                    naive_count += 1
                    
                    if not dry_run:
                        # 轉換為 aware datetime (假設原本是 Asia/Taipei)
                        # 先假設是台北時區，然後轉換為 UTC 儲存
                        taipei_tz = pytz.timezone('Asia/Taipei')
                        aware_dt = taipei_tz.localize(build.build_timestamp)
                        build.build_timestamp = aware_dt
                        build.save(update_fields=['build_timestamp'])
                        fixed_count += 1
                    
                    if naive_count <= 10 or naive_count % 100 == 0:
                        status = "檢查到" if dry_run else "修復"
                        self.stdout.write(f"  {status}: {build.job.name} #{build.build_number}")
                else:
                    # 已經有時區資訊
                    aware_count += 1
                
                # 每 100 個顯示進度
                if i % 100 == 0:
                    percentage = i * 100 // total
                    self.stdout.write(f"  進度: {i}/{total} ({percentage}%)")
                    
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f"  ❌ 錯誤 ({build.job.name} #{build.build_number}): {e}")
                )
        
        self.stdout.write("")
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS('✅ 處理完成！'))
        self.stdout.write("=" * 80)
        self.stdout.write(f"總共: {total} 個")
        self.stdout.write(f"已有時區: {aware_count} 個")
        self.stdout.write(f"需要修復: {naive_count} 個")
        
        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f"成功修復: {fixed_count} 個"))
        else:
            self.stdout.write(self.style.WARNING(f"將會修復: {naive_count} 個 (dry-run 模式)"))
        
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f"錯誤: {error_count} 個"))
        
        self.stdout.write("=" * 80)
