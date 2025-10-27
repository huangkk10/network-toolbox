"""
清理舊的 DHCP 日誌（7天滾動視窗）
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from api.models import DHCPLog
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '清理 7 天前的 DHCP 日誌'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='保留天數（預設: 7）',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='測試模式（不實際刪除）',
        )
    
    def handle(self, *args, **options):
        days = options.get('days', 7)
        dry_run = options.get('dry_run', False)
        
        # 計算截止日期
        cutoff_date = timezone.now() - timedelta(days=days)
        
        self.stdout.write(f'\n清理 {days} 天前的日誌')
        self.stdout.write(f'截止日期: {cutoff_date.strftime("%Y-%m-%d %H:%M:%S")}')
        
        # 查詢要刪除的日誌
        old_logs = DHCPLog.objects.filter(timestamp__lt=cutoff_date)
        count = old_logs.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('\n✓ 沒有需要清理的日誌'))
            return
        
        self.stdout.write(f'\n找到 {count} 筆舊日誌')
        
        # 顯示統計資訊
        if count > 0:
            oldest = old_logs.order_by('timestamp').first()
            newest = old_logs.order_by('-timestamp').first()
            
            self.stdout.write(f'最舊: {oldest.timestamp.strftime("%Y-%m-%d %H:%M:%S")}')
            self.stdout.write(f'最新: {newest.timestamp.strftime("%Y-%m-%d %H:%M:%S")}')
        
        # 執行刪除
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'\n[測試模式] 將會刪除 {count} 筆日誌（未實際執行）')
            )
        else:
            deleted_count, _ = old_logs.delete()
            self.stdout.write(
                self.style.SUCCESS(f'\n✓ 成功刪除 {deleted_count} 筆舊日誌')
            )
            logger.info(f'清理舊日誌: 刪除 {deleted_count} 筆 ({days} 天前)')
        
        # 顯示剩餘日誌統計
        remaining = DHCPLog.objects.count()
        self.stdout.write(f'\n剩餘日誌: {remaining} 筆')
