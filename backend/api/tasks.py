"""
Celery 定時任務

將 Django 管理命令包裝為 Celery 任務
"""

import logging
from celery import shared_task
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta

from .models import DHCPServer, DHCPLog, DHCPLease, DHCPScope
from .services import DHCPLogService

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name='api.tasks.sync_dhcp_logs_task',
    max_retries=3,
    default_retry_delay=60,  # 失敗後 60 秒重試
    time_limit=240,  # 硬限制 4 分鐘
    soft_time_limit=210  # 軟限制 3.5 分鐘
)
def sync_dhcp_logs_task(self, server_id, limit=500):
    """
    同步 DHCP 日誌到資料庫
    
    Args:
        server_id: DHCP Server ID
        limit: 每次同步的最大日誌數量
        
    Returns:
        dict: {
            'server_id': int,
            'server_name': str,
            'total': int,      # 讀取的總日誌數
            'created': int,    # 新增的日誌數
            'skipped': int,    # 跳過的日誌數
            'errors': int      # 錯誤數
        }
    """
    try:
        logger.info(f'[Celery] 開始同步 DHCP 日誌 - Server ID: {server_id}, Limit: {limit}')
        
        # 獲取伺服器
        try:
            server = DHCPServer.objects.get(id=server_id)
        except DHCPServer.DoesNotExist:
            error_msg = f'DHCP Server ID {server_id} 不存在'
            logger.error(f'[Celery] {error_msg}')
            return {
                'server_id': server_id,
                'server_name': None,
                'total': 0,
                'created': 0,
                'skipped': 0,
                'errors': 1,
                'error_message': error_msg
            }
        
        # 創建服務實例並執行同步
        service = DHCPLogService(dhcp_server=server)
        result = service.sync_logs_to_db(limit=limit)
        
        # 添加伺服器資訊
        result['server_id'] = server_id
        result['server_name'] = server.name
        
        # 記錄結果
        logger.info(
            f'[Celery] DHCP 日誌同步完成 - Server: {server.name} | '
            f'讀取: {result["total"]} 筆 | '
            f'新增: {result["created"]} 筆 | '
            f'跳過: {result["skipped"]} 筆 | '
            f'錯誤: {result["errors"]} 筆'
        )
        
        return result
        
    except Exception as exc:
        logger.error(f'[Celery] 同步 DHCP 日誌失敗 - Server ID: {server_id}', exc_info=True)
        
        # 自動重試（最多 3 次）
        try:
            raise self.retry(exc=exc, countdown=60)
        except self.MaxRetriesExceededError:
            logger.error(f'[Celery] 同步重試次數已達上限 - Server ID: {server_id}')
            return {
                'server_id': server_id,
                'server_name': None,
                'total': 0,
                'created': 0,
                'skipped': 0,
                'errors': 1,
                'error_message': str(exc)
            }


@shared_task(
    bind=True,
    name='api.tasks.cleanup_old_logs_task',
    time_limit=3600,  # 硬限制 1 小時
    soft_time_limit=3300  # 軟限制 55 分鐘
)
def cleanup_old_logs_task(self, days=7):
    """
    清理舊的 DHCP 日誌
    
    Args:
        days: 保留最近 N 天的日誌，刪除更早的日誌
        
    Returns:
        dict: {
            'deleted_count': int,  # 刪除的日誌數量
            'cutoff_date': str,    # 刪除日期界線
            'days': int            # 保留天數
        }
    """
    try:
        logger.info(f'[Celery] 開始清理 DHCP 舊日誌 - 保留最近 {days} 天')
        
        # 計算刪除日期界線
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # 查詢要刪除的日誌數量（用於統計）
        old_logs_count = DHCPLog.objects.filter(timestamp__lt=cutoff_date).count()
        
        # 執行刪除
        deleted_count, _ = DHCPLog.objects.filter(timestamp__lt=cutoff_date).delete()
        
        logger.info(
            f'[Celery] DHCP 舊日誌清理完成 - '
            f'刪除: {deleted_count} 筆 | '
            f'界線日期: {cutoff_date.strftime("%Y-%m-%d %H:%M:%S")}'
        )
        
        return {
            'deleted_count': deleted_count,
            'cutoff_date': cutoff_date.strftime('%Y-%m-%d %H:%M:%S'),
            'days': days
        }
        
    except Exception as exc:
        logger.error('[Celery] 清理 DHCP 舊日誌失敗', exc_info=True)
        return {
            'deleted_count': 0,
            'cutoff_date': None,
            'days': days,
            'error_message': str(exc)
        }


@shared_task(
    bind=True,
    name='api.tasks.sync_dhcp_leases_task',
    max_retries=3,
    default_retry_delay=120,  # 失敗後 2 分鐘重試
    time_limit=300,  # 硬限制 5 分鐘
    soft_time_limit=270  # 軟限制 4.5 分鐘
)
def sync_dhcp_leases_task(self, server_id):
    """
    同步 DHCP 租約到資料庫
    
    Args:
        server_id: DHCP Server ID
        
    Returns:
        dict: {
            'server_id': int,
            'server_name': str,
            'total': int,      # 讀取的總租約數
            'created': int,    # 新增的租約數
            'updated': int,    # 更新的租約數
            'errors': int      # 錯誤數
        }
    """
    try:
        logger.info(f'[Celery] 開始同步 DHCP 租約 - Server ID: {server_id}')
        
        # 獲取伺服器
        try:
            server = DHCPServer.objects.get(id=server_id)
        except DHCPServer.DoesNotExist:
            error_msg = f'DHCP Server ID {server_id} 不存在'
            logger.error(f'[Celery] {error_msg}')
            return {
                'server_id': server_id,
                'server_name': None,
                'total': 0,
                'created': 0,
                'updated': 0,
                'errors': 1,
                'error_message': error_msg
            }
        
        # 使用 SSH + PowerShell 同步（適用於 Windows DHCP Server）
        from .ssh_powershell_service import WindowsSSHPowerShellService
        
        with WindowsSSHPowerShellService(server) as service:
            # 執行同步
            result = service.sync_leases_to_db()
        
        # 添加伺服器資訊
        result['server_id'] = server_id
        result['server_name'] = server.name
        
        # 更新 Server 的租約統計
        server.total_leases = DHCPLease.objects.filter(server=server).count()
        server.active_leases = DHCPLease.objects.filter(server=server, is_active=True).count()
        server.last_sync_at = timezone.now()
        server.save(update_fields=['total_leases', 'active_leases', 'last_sync_at'])
        
        # 記錄結果
        logger.info(
            f'[Celery] DHCP 租約同步完成 - Server: {server.name} | '
            f'總計: {result["total"]} 筆 | '
            f'新增: {result["created"]} 筆 | '
            f'更新: {result["updated"]} 筆 | '
            f'錯誤: {result["errors"]} 筆'
        )
        
        return result
        
    except Exception as exc:
        logger.error(f'[Celery] 同步 DHCP 租約失敗 - Server ID: {server_id}', exc_info=True)
        
        # 自動重試（最多 3 次）
        try:
            raise self.retry(exc=exc, countdown=120)
        except self.MaxRetriesExceededError:
            logger.error(f'[Celery] 租約同步重試次數已達上限 - Server ID: {server_id}')
            return {
                'server_id': server_id,
                'server_name': None,
                'total': 0,
                'created': 0,
                'updated': 0,
                'errors': 1,
                'error_message': str(exc)
            }


@shared_task(
    bind=True,
    name='api.tasks.sync_dhcp_scopes_task',
    max_retries=3,
    default_retry_delay=120,  # 失敗後 2 分鐘重試
    time_limit=300,  # 硬限制 5 分鐘
    soft_time_limit=270  # 軟限制 4.5 分鐘
)
def sync_dhcp_scopes_task(self, server_id):
    """
    同步 DHCP Scope 資訊到資料庫（包含使用率統計）
    
    Args:
        server_id: DHCP Server ID
        
    Returns:
        dict: {
            'server_id': int,
            'server_name': str,
            'total': int,      # 讀取的總 Scope 數
            'created': int,    # 新增的 Scope 數
            'updated': int,    # 更新的 Scope 數
            'errors': int,     # 錯誤數
            'pool_usage': float  # 更新後的平均使用率
        }
    """
    try:
        logger.info(f'[Celery] 開始同步 DHCP Scope - Server ID: {server_id}')
        
        # 獲取伺服器
        try:
            server = DHCPServer.objects.get(id=server_id)
        except DHCPServer.DoesNotExist:
            error_msg = f'DHCP Server ID {server_id} 不存在'
            logger.error(f'[Celery] {error_msg}')
            return {
                'server_id': server_id,
                'server_name': None,
                'total': 0,
                'created': 0,
                'updated': 0,
                'errors': 1,
                'pool_usage': 0.0,
                'error_message': error_msg
            }
        
        # 使用 SSH + PowerShell 同步（適用於 Windows DHCP Server）
        from .ssh_powershell_service import WindowsSSHPowerShellService
        
        with WindowsSSHPowerShellService(server) as service:
            # 執行同步
            result = service.sync_scopes_to_db()
        
        # 添加伺服器資訊
        result['server_id'] = server_id
        result['server_name'] = server.name
        
        # 重新載入 Server 以獲取更新後的 pool_usage
        server.refresh_from_db()
        result['pool_usage'] = server.pool_usage
        
        # 記錄結果
        logger.info(
            f'[Celery] DHCP Scope 同步完成 - Server: {server.name} | '
            f'總計: {result["total"]} 個 | '
            f'新增: {result["created"]} 個 | '
            f'更新: {result["updated"]} 個 | '
            f'錯誤: {result["errors"]} 個 | '
            f'平均使用率: {result["pool_usage"]:.2f}%'
        )
        
        return result
        
    except Exception as exc:
        logger.error(f'[Celery] 同步 DHCP Scope 失敗 - Server ID: {server_id}', exc_info=True)
        
        # 自動重試（最多 3 次）
        try:
            raise self.retry(exc=exc, countdown=120)
        except self.MaxRetriesExceededError:
            logger.error(f'[Celery] Scope 同步重試次數已達上限 - Server ID: {server_id}')
            return {
                'server_id': server_id,
                'server_name': None,
                'total': 0,
                'created': 0,
                'updated': 0,
                'errors': 1,
                'pool_usage': 0.0,
                'error_message': str(exc)
            }


@shared_task(name='api.tasks.get_logs_statistics_task')
def get_logs_statistics_task():
    """
    獲取日誌統計資訊（示範用任務）
    
    Returns:
        dict: 各伺服器的日誌統計
    """
    try:
        logger.info('[Celery] 開始統計 DHCP 日誌')
        
        # 按伺服器統計
        stats = DHCPLog.objects.values('server__name').annotate(
            total=Count('id')
        ).order_by('-total')
        
        result = {
            'total_logs': DHCPLog.objects.count(),
            'by_server': list(stats),
            'timestamp': timezone.now().isoformat()
        }
        
        logger.info(f'[Celery] 日誌統計完成 - 總計: {result["total_logs"]} 筆')
        
        return result
        
    except Exception as exc:
        logger.error('[Celery] 日誌統計失敗', exc_info=True)
        return {'error': str(exc)}
