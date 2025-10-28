"""
清理舊的 IPXE 日誌（預設保留 7 天）
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count
from datetime import timedelta
from api.models import IPXELog, IPXEServer
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '清理超過指定天數的 IPXE 日誌'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='保留天數（預設: 7）',
        )
        parser.add_argument(
            '--server',
            type=int,
            help='指定 IPXE Server ID（不指定則清理所有伺服器）',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='測試模式（不實際刪除）',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='顯示詳細輸出',
        )
    
    def handle(self, *args, **options):
        days = options.get('days', 7)
        server_id = options.get('server')
        dry_run = options.get('dry_run', False)
        verbose = options.get('verbose', False)
        
        # 計算截止日期
        cutoff_date = timezone.now() - timedelta(days=days)
        
        self.stdout.write(f'\n清理 {days} 天前的 IPXE 日誌')
        self.stdout.write(f'截止日期: {cutoff_date.strftime("%Y-%m-%d %H:%M:%S")}')
        
        # 查詢要刪除的日誌
        old_logs = IPXELog.objects.filter(created_at__lt=cutoff_date)
        
        if server_id:
            old_logs = old_logs.filter(server_id=server_id)
            server = IPXEServer.objects.get(id=server_id)
            self.stdout.write(f'伺服器: {server.name}')
        
        count = old_logs.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('\n✓ 沒有需要清理的日誌'))
            return
        
        # 統計資訊
        mac_count = old_logs.filter(log_type='MAC').count()
        boot_count = old_logs.filter(log_type='BOOT').count()
        
        self.stdout.write(f'\n找到 {count} 筆舊日誌')
        self.stdout.write(f'  - MAC 日誌: {mac_count} 筆')
        self.stdout.write(f'  - BOOT 日誌: {boot_count} 筆')
        
        # 顯示時間範圍
        if verbose and count > 0:
            oldest = old_logs.order_by('timestamp').first()
            newest = old_logs.order_by('-timestamp').first()
            
            self.stdout.write(f'\n時間範圍:')
            self.stdout.write(f'  最舊: {oldest.timestamp.strftime("%Y-%m-%d %H:%M:%S")}')
            self.stdout.write(f'  最新: {newest.timestamp.strftime("%Y-%m-%d %H:%M:%S")}')
        
        # 依伺服器統計
        if verbose and not server_id:
            self.stdout.write(f'\n依伺服器統計:')
            server_stats = old_logs.values('server__name').annotate(
                count=Count('id')
            ).order_by('-count')
            
            for stat in server_stats:
                self.stdout.write(f'  - {stat["server__name"]}: {stat["count"]} 筆')
        
        # 執行刪除
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'\n[測試模式] 將會刪除 {count} 筆日誌（未實際執行）'
                )
            )
        else:
            deleted_count, details = old_logs.delete()
            self.stdout.write(
                self.style.SUCCESS(f'\n✓ 成功刪除 {deleted_count} 筆舊日誌')
            )
            logger.info(f'清理 IPXE 舊日誌: 刪除 {deleted_count} 筆 ({days} 天前)')
            
            if verbose:
                self.stdout.write(f'\n刪除詳情:')
                for model, count in details.items():
                    if count > 0:
                        self.stdout.write(f'  - {model}: {count} 筆')
        
        # 顯示剩餘日誌統計
        remaining = IPXELog.objects.count()
        remaining_mac = IPXELog.objects.filter(log_type='MAC').count()
        remaining_boot = IPXELog.objects.filter(log_type='BOOT').count()
        
        self.stdout.write(f'\n剩餘日誌: {remaining} 筆')
        self.stdout.write(f'  - MAC 日誌: {remaining_mac} 筆')
        self.stdout.write(f'  - BOOT 日誌: {remaining_boot} 筆')
