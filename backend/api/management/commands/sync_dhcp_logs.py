"""
同步 DHCP 日誌到資料庫
"""
from django.core.management.base import BaseCommand
from api.models import DHCPServer
from api.services import DHCPLogService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '從 Windows DHCP Server 同步日誌到資料庫'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--server',
            type=int,
            help='指定 DHCP Server ID（不指定則同步所有伺服器）',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=1000,
            help='每次同步的日誌數量（預設: 1000）',
        )
    
    def handle(self, *args, **options):
        server_id = options.get('server')
        limit = options.get('limit', 1000)
        
        # 取得要同步的伺服器
        if server_id:
            servers = DHCPServer.objects.filter(id=server_id)
            if not servers.exists():
                self.stdout.write(self.style.ERROR(f'找不到 Server ID: {server_id}'))
                return
        else:
            servers = DHCPServer.objects.filter(status='online')
        
        total_stats = {
            'total': 0,
            'created': 0,
            'skipped': 0,
            'errors': 0,
        }
        
        for server in servers:
            self.stdout.write(f'\n同步伺服器: {server.name} ({server.ip_address})')
            
            try:
                service = DHCPLogService(server)
                stats = service.sync_logs_to_db(limit=limit)
                
                # 累計統計
                for key in total_stats:
                    total_stats[key] += stats[key]
                
                self.stdout.write(
                    f'  - 讀取: {stats["total"]} 筆 | '
                    f'新增: {stats["created"]} 筆 | '
                    f'跳過: {stats["skipped"]} 筆 | '
                    f'錯誤: {stats["errors"]} 筆'
                )
            
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  - 同步失敗: {str(e)}'))
                logger.error(f'同步失敗 ({server.name}): {str(e)}', exc_info=True)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ 同步完成！總計: {total_stats["total"]} 筆 | '
                f'新增: {total_stats["created"]} 筆 | '
                f'跳過: {total_stats["skipped"]} 筆 | '
                f'錯誤: {total_stats["errors"]} 筆'
            )
        )
