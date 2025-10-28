"""
收集 IPXE 伺服器日誌到資料庫
"""
from django.core.management.base import BaseCommand
from api.models import IPXEServer
from api.ipxe_service import IPXEService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '從 IPXE Server 收集日誌到資料庫'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--server',
            type=int,
            help='指定 IPXE Server ID（不指定則同步所有伺服器）',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=1000,
            help='每個容器收集的日誌數量（預設: 1000）',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='顯示詳細輸出',
        )
    
    def handle(self, *args, **options):
        server_id = options.get('server')
        limit = options.get('limit', 1000)
        verbose = options.get('verbose', False)
        
        # 取得要同步的伺服器
        if server_id:
            servers = IPXEServer.objects.filter(id=server_id)
            if not servers.exists():
                self.stdout.write(self.style.ERROR(f'找不到 IPXE Server ID: {server_id}'))
                return
        else:
            servers = IPXEServer.objects.filter(status='online')
        
        if not servers.exists():
            self.stdout.write(self.style.WARNING('沒有可用的 IPXE 伺服器'))
            return
        
        total_stats = {
            'mac_logs': 0,
            'boot_logs': 0,
            'total': 0,
            'errors': 0,
        }
        
        for server in servers:
            self.stdout.write(f'\n收集日誌: {server.name} ({server.ip_address})')
            
            try:
                service = IPXEService(server)
                result = service.sync_logs_to_db(limit=limit)
                
                if 'error' in result:
                    self.stdout.write(self.style.ERROR(f'  ✗ 收集失敗: {result["error"]}'))
                    total_stats['errors'] += 1
                else:
                    # 累計統計
                    total_stats['mac_logs'] += result.get('mac_logs', 0)
                    total_stats['boot_logs'] += result.get('boot_logs', 0)
                    total_stats['total'] += result.get('total', 0)
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  ✓ MAC 日誌: {result["mac_logs"]} 條 | '
                            f'BOOT 日誌: {result["boot_logs"]} 條 | '
                            f'總計: {result["total"]} 條'
                        )
                    )
                    
                    if verbose:
                        self.stdout.write(f'    - 最後同步: {server.last_sync_at}')
            
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ 收集失敗: {str(e)}'))
                logger.error(f'收集日誌失敗 ({server.name}): {str(e)}', exc_info=True)
                total_stats['errors'] += 1
        
        # 輸出總結
        if total_stats['errors'] > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'\n⚠ 收集完成（部分失敗）！'
                    f'總計: {total_stats["total"]} 條 | '
                    f'MAC: {total_stats["mac_logs"]} 條 | '
                    f'BOOT: {total_stats["boot_logs"]} 條 | '
                    f'失敗: {total_stats["errors"]} 台伺服器'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✓ 收集完成！'
                    f'總計: {total_stats["total"]} 條 | '
                    f'MAC: {total_stats["mac_logs"]} 條 | '
                    f'BOOT: {total_stats["boot_logs"]} 條'
                )
            )
