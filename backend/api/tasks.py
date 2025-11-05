"""
Celery 定時任務

將 Django 管理命令包裝為 Celery 任務
"""

import logging
import time
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
def cleanup_old_logs_task(self, days=15):
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


@shared_task(
    bind=True,
    name='api.tasks.sync_all_dhcp_scopes_task',
    max_retries=2,
    default_retry_delay=300,  # 失敗後 5 分鐘重試
    time_limit=1800,  # 硬限制 30 分鐘
    soft_time_limit=1650  # 軟限制 27.5 分鐘
)
def sync_all_dhcp_scopes_task(self):
    """
    批次同步所有 DHCP Server 的 Scope 資訊（定時任務）
    
    適用場景：
    - 新增伺服器後自動初始化
    - 定時更新所有伺服器的使用率
    - 確保所有伺服器都有完整的 Scope 數據
    
    Returns:
        dict: {
            'total_servers': int,    # 處理的伺服器總數
            'success_count': int,    # 成功的伺服器數
            'failed_count': int,     # 失敗的伺服器數
            'results': [...]         # 每個伺服器的詳細結果
        }
    """
    try:
        logger.info('[Celery] 開始批次同步所有 DHCP Server 的 Scope')
        
        # 獲取所有在線的 DHCP 伺服器
        servers = DHCPServer.objects.filter(status='online')
        total_servers = servers.count()
        
        logger.info(f'[Celery] 找到 {total_servers} 個在線的 DHCP Server')
        
        results = []
        success_count = 0
        failed_count = 0
        
        for server in servers:
            try:
                logger.info(f'[Celery] 正在同步 Server: {server.name} ({server.ip_address})')
                
                # 判斷伺服器類型並使用對應的同步方式
                if server.ssh_username in ['administrator', 'Administrator']:
                    # Windows DHCP Server - 使用 PowerShell
                    from .ssh_powershell_service import WindowsSSHPowerShellService
                    
                    with WindowsSSHPowerShellService(server) as service:
                        result = service.sync_scopes_to_db()
                    
                    result['server_id'] = server.id
                    result['server_name'] = server.name
                    result['server_type'] = 'Windows DHCP'
                    result['sync_method'] = 'PowerShell'
                    
                else:
                    # Linux DHCP Server - 解析 dhcpd.conf
                    from .services import LinuxDHCPConfigService
                    
                    with LinuxDHCPConfigService(server) as service:
                        result = service.sync_config_to_db()
                    
                    result['server_id'] = server.id
                    result['server_name'] = server.name
                    result['server_type'] = 'Linux DHCP'
                    result['sync_method'] = 'Config File'
                
                # 重新載入 Server 以獲取更新後的 pool_usage
                server.refresh_from_db()
                result['pool_usage'] = server.pool_usage
                
                results.append(result)
                success_count += 1
                
                logger.info(
                    f'[Celery] Server {server.name} 同步成功 - '
                    f'Scopes: {result.get("scopes_created", 0) + result.get("scopes_updated", 0)} | '
                    f'使用率: {server.pool_usage:.2f}%'
                )
                
            except Exception as e:
                logger.error(f'[Celery] Server {server.name} 同步失敗: {str(e)}', exc_info=True)
                
                results.append({
                    'server_id': server.id,
                    'server_name': server.name,
                    'success': False,
                    'error': str(e)
                })
                failed_count += 1
        
        summary = {
            'total_servers': total_servers,
            'success_count': success_count,
            'failed_count': failed_count,
            'results': results,
            'timestamp': timezone.now().isoformat()
        }
        
        logger.info(
            f'[Celery] 批次同步完成 - '
            f'總計: {total_servers} | 成功: {success_count} | 失敗: {failed_count}'
        )
        
        return summary
        
    except Exception as exc:
        logger.error('[Celery] 批次同步 DHCP Scope 失敗', exc_info=True)
        
        # 自動重試
        try:
            raise self.retry(exc=exc, countdown=300)
        except self.MaxRetriesExceededError:
            logger.error('[Celery] Scope 批次同步重試次數已達上限')
            return {
                'total_servers': 0,
                'success_count': 0,
                'failed_count': 0,
                'error': str(exc)
            }


@shared_task(
    bind=True,
    name='api.tasks.sync_all_dhcp_logs_task',
    max_retries=2,
    default_retry_delay=300,  # 失敗後 5 分鐘重試
    time_limit=1800,  # 硬限制 30 分鐘
    soft_time_limit=1650  # 軟限制 27.5 分鐘
)
def sync_all_dhcp_logs_task(self, limit=500):
    """
    批次同步所有 DHCP Server 的日誌（定時任務）
    
    適用場景：
    - 定時自動同步所有伺服器的日誌
    - 確保所有伺服器都有最新的日誌數據
    
    Args:
        limit: 每個伺服器最多同步的日誌數量
        
    Returns:
        dict: {
            'total_servers': int,    # 處理的伺服器總數
            'success_count': int,    # 成功的伺服器數
            'failed_count': int,     # 失敗的伺服器數
            'total_logs_created': int,  # 總共新增的日誌數
            'results': [...]         # 每個伺服器的詳細結果
        }
    """
    try:
        logger.info(f'[Celery] 開始批次同步所有 DHCP Server 的日誌 (limit={limit})')
        
        # 獲取所有在線的 DHCP 伺服器
        servers = DHCPServer.objects.filter(status='online')
        total_servers = servers.count()
        
        logger.info(f'[Celery] 找到 {total_servers} 個在線的 DHCP Server')
        
        results = []
        success_count = 0
        failed_count = 0
        total_logs_created = 0
        
        for server in servers:
            try:
                logger.info(f'[Celery] 正在同步 Server 日誌: {server.name} ({server.ip_address})')
                
                # 創建日誌服務並同步
                service = DHCPLogService(dhcp_server=server)
                result = service.sync_logs_to_db(limit=limit)
                
                # 添加伺服器資訊
                result['server_id'] = server.id
                result['server_name'] = server.name
                result['server_ip'] = server.ip_address
                
                results.append(result)
                success_count += 1
                total_logs_created += result.get('created', 0)
                
                logger.info(
                    f'[Celery] Server {server.name} 日誌同步成功 - '
                    f'讀取: {result.get("total", 0)} 筆 | '
                    f'新增: {result.get("created", 0)} 筆 | '
                    f'跳過: {result.get("skipped", 0)} 筆'
                )
                
            except Exception as e:
                logger.error(f'[Celery] Server {server.name} 日誌同步失敗: {str(e)}', exc_info=True)
                
                results.append({
                    'server_id': server.id,
                    'server_name': server.name,
                    'server_ip': server.ip_address,
                    'total': 0,
                    'created': 0,
                    'skipped': 0,
                    'errors': 1,
                    'error_message': str(e)
                })
                failed_count += 1
        
        summary = {
            'total_servers': total_servers,
            'success_count': success_count,
            'failed_count': failed_count,
            'total_logs_created': total_logs_created,
            'results': results,
            'timestamp': timezone.now().isoformat()
        }
        
        logger.info(
            f'[Celery] 批次日誌同步完成 - '
            f'伺服器總計: {total_servers} | 成功: {success_count} | 失敗: {failed_count} | '
            f'總共新增日誌: {total_logs_created} 筆'
        )
        
        return summary
        
    except Exception as exc:
        logger.error('[Celery] 批次同步 DHCP 日誌失敗', exc_info=True)
        
        # 自動重試
        try:
            raise self.retry(exc=exc, countdown=300)
        except self.MaxRetriesExceededError:
            logger.error('[Celery] 日誌批次同步重試次數已達上限')
            return {
                'total_servers': 0,
                'success_count': 0,
                'failed_count': 0,
                'total_logs_created': 0,
                'error': str(exc)
            }


@shared_task(
    bind=True,
    name='api.tasks.sync_all_dhcp_leases_task',
    max_retries=2,
    default_retry_delay=300,  # 失敗後 5 分鐘重試
    time_limit=1800,  # 硬限制 30 分鐘
    soft_time_limit=1650  # 軟限制 27.5 分鐘
)
def sync_all_dhcp_leases_task(self):
    """
    批次同步所有 DHCP Server 的租約（定時任務）
    
    適用場景：
    - 定時自動同步所有伺服器的租約
    - 確保所有伺服器都有最新的租約數據
    
    Returns:
        dict: {
            'total_servers': int,    # 處理的伺服器總數
            'success_count': int,    # 成功的伺服器數
            'failed_count': int,     # 失敗的伺服器數
            'total_leases_created': int,  # 總共新增的租約數
            'total_leases_updated': int,  # 總共更新的租約數
            'results': [...]         # 每個伺服器的詳細結果
        }
    """
    try:
        logger.info('[Celery] 開始批次同步所有 DHCP Server 的租約')
        
        # 獲取所有在線的 DHCP 伺服器
        servers = DHCPServer.objects.filter(status='online')
        total_servers = servers.count()
        
        logger.info(f'[Celery] 找到 {total_servers} 個在線的 DHCP Server')
        
        results = []
        success_count = 0
        failed_count = 0
        total_leases_created = 0
        total_leases_updated = 0
        
        for server in servers:
            try:
                logger.info(f'[Celery] 正在同步 Server 租約: {server.name} ({server.ip_address})')
                
                # 使用 SSH + PowerShell 同步租約
                from .ssh_powershell_service import WindowsSSHPowerShellService
                
                with WindowsSSHPowerShellService(server) as service:
                    result = service.sync_leases_to_db()
                
                # 添加伺服器資訊
                result['server_id'] = server.id
                result['server_name'] = server.name
                result['server_ip'] = server.ip_address
                
                # 更新 Server 的租約統計
                server.total_leases = DHCPLease.objects.filter(server=server).count()
                server.active_leases = DHCPLease.objects.filter(server=server, is_active=True).count()
                server.last_sync_at = timezone.now()
                server.save(update_fields=['total_leases', 'active_leases', 'last_sync_at'])
                
                results.append(result)
                success_count += 1
                total_leases_created += result.get('created', 0)
                total_leases_updated += result.get('updated', 0)
                
                logger.info(
                    f'[Celery] Server {server.name} 租約同步成功 - '
                    f'總計: {result.get("total", 0)} 筆 | '
                    f'新增: {result.get("created", 0)} 筆 | '
                    f'更新: {result.get("updated", 0)} 筆 | '
                    f'活躍: {server.active_leases} 筆'
                )
                
            except Exception as e:
                logger.error(f'[Celery] Server {server.name} 租約同步失敗: {str(e)}', exc_info=True)
                
                results.append({
                    'server_id': server.id,
                    'server_name': server.name,
                    'server_ip': server.ip_address,
                    'success': False,
                    'error': str(e)
                })
                failed_count += 1
        
        summary = {
            'total_servers': total_servers,
            'success_count': success_count,
            'failed_count': failed_count,
            'total_leases_created': total_leases_created,
            'total_leases_updated': total_leases_updated,
            'results': results,
            'timestamp': timezone.now().isoformat()
        }
        
        logger.info(
            f'[Celery] 批次租約同步完成 - '
            f'伺服器總計: {total_servers} | 成功: {success_count} | 失敗: {failed_count} | '
            f'總共新增租約: {total_leases_created} 筆 | 總共更新租約: {total_leases_updated} 筆'
        )
        
        return summary
        
    except Exception as exc:
        logger.error('[Celery] 批次同步 DHCP 租約失敗', exc_info=True)
        
        # 自動重試
        try:
            raise self.retry(exc=exc, countdown=300)
        except self.MaxRetriesExceededError:
            logger.error('[Celery] 租約批次同步重試次數已達上限')
            return {
                'total_servers': 0,
                'success_count': 0,
                'failed_count': 0,
                'total_leases_created': 0,
                'total_leases_updated': 0,
                'error': str(exc)
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


@shared_task(
    bind=True,
    name='api.tasks.update_oui_database_task',
    max_retries=3,
    default_retry_delay=300,  # 失敗後 5 分鐘重試
    time_limit=600,  # 硬限制 10 分鐘
    soft_time_limit=540  # 軟限制 9 分鐘
)
def update_oui_database_task(self, source=0, backup=True):
    """
    更新 IEEE OUI 資料庫（定時任務）
    
    Args:
        source: 資料來源索引 (0: IEEE Official HTTPS, 1: IEEE Official HTTP, 2: Gist Mirror)
        backup: 是否備份現有資料庫
        
    Returns:
        dict: {
            'success': bool,
            'source': str,
            'total_oui_entries': int,
            'unique_vendors': int,
            'backup_created': bool,
            'timestamp': str
        }
    """
    try:
        logger.info(f'[Celery] 開始更新 OUI 資料庫 - 來源索引: {source}, 備份: {backup}')
        
        # 使用 Django 管理命令更新
        from django.core.management import call_command
        from io import StringIO
        import sys
        
        # 捕獲命令輸出
        out = StringIO()
        
        # 執行更新命令
        call_command(
            'update_oui',
            source=source,
            backup=backup,
            stdout=out,
            stderr=out
        )
        
        # 獲取輸出
        command_output = out.getvalue()
        
        # 獲取更新後的統計資訊
        from api.utils.mac_vendor import get_vendor_stats
        stats = get_vendor_stats()
        
        result = {
            'success': True,
            'source': source,
            'total_oui_entries': stats.get('total_oui_entries', 0),
            'unique_vendors': stats.get('unique_vendors', 0),
            'backup_created': backup,
            'timestamp': timezone.now().isoformat(),
            'command_output': command_output
        }
        
        logger.info(
            f'[Celery] OUI 資料庫更新完成 - '
            f'總 OUI: {result["total_oui_entries"]:,} | '
            f'製造商: {result["unique_vendors"]:,}'
        )
        
        return result
        
    except Exception as exc:
        logger.error('[Celery] OUI 資料庫更新失敗', exc_info=True)
        
        # 自動重試（最多 3 次）
        try:
            raise self.retry(exc=exc, countdown=300)
        except self.MaxRetriesExceededError:
            logger.error('[Celery] OUI 更新重試次數已達上限')
            return {
                'success': False,
                'source': source,
                'total_oui_entries': 0,
                'unique_vendors': 0,
                'backup_created': backup,
                'timestamp': timezone.now().isoformat(),
                'error_message': str(exc)
            }


@shared_task(
    bind=True,
    name='api.tasks.check_nas_connection_task',
    max_retries=2,
    default_retry_delay=60,  # 失敗後 1 分鐘重試
    time_limit=180,  # 硬限制 3 分鐘
    soft_time_limit=150  # 軟限制 2.5 分鐘
)
def check_nas_connection_task(self):
    """
    NAS 連線檢測定時任務（每5分鐘執行一次）
    
    Returns:
        dict: {
            'success': bool,
            'status': str,      # 'success' or 'failed'
            'nas_ip': str,
            'nas_share': str,
            'response_time': float,  # 響應時間（ms）
            'upload_speed': float,   # 上傳速度（MB/s）
            'download_speed': float, # 下載速度（MB/s）
            'timestamp': str
        }
    """
    try:
        logger.info('[Celery] 開始執行 NAS 連線檢測')
        
        # 使用 NAS 服務執行檢測並記錄
        from .nas_service import record_nas_connection
        
        success = record_nas_connection()
        
        # 獲取最新的記錄
        from .models import NASConnectionLog
        latest_log = NASConnectionLog.objects.order_by('-timestamp').first()
        
        if latest_log:
            result = {
                'success': success,
                'status': latest_log.status,
                'nas_ip': latest_log.nas_ip,
                'nas_share': latest_log.nas_share,
                'response_time': latest_log.response_time,
                'upload_speed': latest_log.upload_speed,
                'download_speed': latest_log.download_speed,
                'timestamp': latest_log.timestamp.isoformat(),
            }
            
            logger.info(
                f'[Celery] NAS 連線檢測完成 - '
                f'狀態: {result["status"]} | '
                f'響應時間: {result["response_time"]:.2f} ms' if result["response_time"] else 'N/A'
            )
        else:
            result = {
                'success': False,
                'error_message': '無法獲取最新記錄'
            }
        
        return result
        
    except Exception as exc:
        logger.error('[Celery] NAS 連線檢測失敗', exc_info=True)
        
        # 自動重試（最多 2 次）
        try:
            raise self.retry(exc=exc, countdown=60)
        except self.MaxRetriesExceededError:
            logger.error('[Celery] NAS 連線檢測重試次數已達上限')
            return {
                'success': False,
                'error_message': str(exc),
                'timestamp': timezone.now().isoformat()
            }


@shared_task(
    bind=True,
    name='api.tasks.check_ipxe_network_quality_task',
    max_retries=2,
    default_retry_delay=60,  # 失敗後 1 分鐘重試
    time_limit=180,  # 硬限制 3 分鐘
    soft_time_limit=150  # 軟限制 2.5 分鐘
)
def check_ipxe_network_quality_task(self, server_id):
    """
    IPXE 網路品質檢測定時任務（每5分鐘執行一次）
    
    Args:
        server_id: IPXE Server ID
    
    Returns:
        dict: {
            'success': bool,
            'status': str,              # 'success', 'partial', or 'failed'
            'server_id': int,
            'server_name': str,
            'ping_latency': float,      # Ping 延遲（ms）
            'ping_packet_loss': float,  # 丟包率（%）
            'http_response_time': float,  # HTTP 響應時間（ms）
            'ssh_response_time': float,   # SSH 響應時間（ms）
            'download_speed': float,    # 下載速度（MB/s）
            'timestamp': str
        }
    """
    try:
        logger.info(f'[Celery] 開始執行 IPXE 網路品質檢測 - Server ID: {server_id}')
        
        # 使用 IPXE 網路服務執行檢測並記錄
        from .ipxe_network_service import record_ipxe_network_quality
        from .models import IPXEServer, IPXENetworkQuality
        
        success = record_ipxe_network_quality(server_id)
        
        # 獲取伺服器資訊
        try:
            server = IPXEServer.objects.get(id=server_id)
            server_name = server.name
        except IPXEServer.DoesNotExist:
            logger.error(f'[Celery] IPXE Server ID {server_id} 不存在')
            return {
                'success': False,
                'error_message': f'IPXE Server ID {server_id} 不存在',
                'timestamp': timezone.now().isoformat()
            }
        
        # 獲取最新的記錄
        latest_log = IPXENetworkQuality.objects.filter(
            server_id=server_id
        ).order_by('-timestamp').first()
        
        if latest_log:
            result = {
                'success': success,
                'status': latest_log.status,
                'server_id': server_id,
                'server_name': server_name,
                'ping_latency': latest_log.ping_latency,
                'ping_packet_loss': latest_log.ping_packet_loss,
                'http_response_time': latest_log.http_response_time,
                'http_status_code': latest_log.http_status_code,
                'ssh_response_time': latest_log.ssh_response_time,
                'ssh_connected': latest_log.ssh_connected,
                'download_speed': latest_log.download_speed,
                'error_message': latest_log.error_message,
                'timestamp': latest_log.timestamp.isoformat(),
            }
            
            logger.info(
                f'[Celery] IPXE 網路品質檢測完成 - '
                f'Server: {server_name} | '
                f'狀態: {result["status"]} | '
                f'Ping: {result["ping_latency"]:.2f} ms | ' if result["ping_latency"] else 'Ping: N/A | '
                f'HTTP: {result["http_response_time"]:.2f} ms | ' if result["http_response_time"] else 'HTTP: N/A | '
                f'SSH: {result["ssh_response_time"]:.2f} ms' if result["ssh_response_time"] else 'SSH: N/A'
            )
        else:
            result = {
                'success': False,
                'server_id': server_id,
                'server_name': server_name,
                'error_message': '無法獲取最新記錄',
                'timestamp': timezone.now().isoformat()
            }
        
        return result
        
    except Exception as exc:
        logger.error(f'[Celery] IPXE 網路品質檢測失敗 - Server ID: {server_id}', exc_info=True)
        
        # 自動重試（最多 2 次）
        try:
            raise self.retry(exc=exc, countdown=60)
        except self.MaxRetriesExceededError:
            logger.error(f'[Celery] IPXE 網路品質檢測重試次數已達上限 - Server ID: {server_id}')
            return {
                'success': False,
                'server_id': server_id,
                'error_message': str(exc),
                'timestamp': timezone.now().isoformat()
            }


@shared_task(
    bind=True,
    name='api.tasks.check_all_ipxe_network_quality_task',
    max_retries=1,
    time_limit=600,  # 硬限制 10 分鐘（多個 Server）
    soft_time_limit=540  # 軟限制 9 分鐘
)
def check_all_ipxe_network_quality_task(self):
    """
    批次檢測所有線上 IPXE Server 的網路品質（每5分鐘執行一次）
    
    此任務會自動偵測所有狀態為 'online' 的 IPXE Server，
    並對每個 Server 執行網路品質檢測。
    
    Returns:
        dict: {
            'success': bool,
            'total_servers': int,        # 總共檢測的 Server 數量
            'success_count': int,         # 成功的數量
            'failed_count': int,          # 失敗的數量
            'results': list,              # 每個 Server 的詳細結果
            'timestamp': str
        }
    """
    try:
        logger.info('[Celery] 開始批次執行 IPXE 網路品質檢測')
        
        from .models import IPXEServer
        from .ipxe_network_service import record_ipxe_network_quality
        
        # 獲取所有線上的 IPXE Server
        online_servers = IPXEServer.objects.filter(status='online')
        total_servers = online_servers.count()
        
        if total_servers == 0:
            logger.warning('[Celery] 沒有線上的 IPXE Server 可供檢測')
            return {
                'success': True,
                'total_servers': 0,
                'success_count': 0,
                'failed_count': 0,
                'results': [],
                'timestamp': timezone.now().isoformat()
            }
        
        logger.info(f'[Celery] 找到 {total_servers} 個線上的 IPXE Server')
        
        results = []
        success_count = 0
        failed_count = 0
        
        # 逐一檢測每個 Server
        for server in online_servers:
            try:
                logger.info(f'[Celery] 正在檢測 Server: {server.name} (ID: {server.id}, IP: {server.ip_address})')
                
                # 執行網路品質檢測
                success = record_ipxe_network_quality(server.id)
                
                if success:
                    success_count += 1
                    logger.info(f'[Celery] Server {server.name} 檢測成功')
                else:
                    failed_count += 1
                    logger.warning(f'[Celery] Server {server.name} 檢測失敗')
                
                # 獲取最新記錄
                from .models import IPXENetworkQuality
                latest_log = IPXENetworkQuality.objects.filter(
                    server_id=server.id
                ).order_by('-timestamp').first()
                
                result_item = {
                    'server_id': server.id,
                    'server_name': server.name,
                    'server_ip': server.ip_address,
                    'success': success,
                }
                
                if latest_log:
                    result_item.update({
                        'status': latest_log.status,
                        'ping_latency': latest_log.ping_latency,
                        'http_response_time': latest_log.http_response_time,
                        'ssh_response_time': latest_log.ssh_response_time,
                        'download_speed': latest_log.download_speed,
                    })
                
                results.append(result_item)
                
            except Exception as e:
                failed_count += 1
                logger.error(f'[Celery] Server {server.name} 檢測異常: {e}', exc_info=True)
                results.append({
                    'server_id': server.id,
                    'server_name': server.name,
                    'server_ip': server.ip_address,
                    'success': False,
                    'error_message': str(e)
                })
        
        logger.info(
            f'[Celery] 批次網路品質檢測完成 - '
            f'總計: {total_servers} | '
            f'成功: {success_count} | '
            f'失敗: {failed_count}'
        )
        
        return {
            'success': True,
            'total_servers': total_servers,
            'success_count': success_count,
            'failed_count': failed_count,
            'results': results,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error('[Celery] 批次 IPXE 網路品質檢測失敗', exc_info=True)
        
        # 自動重試（最多 1 次）
        try:
            raise self.retry(exc=exc, countdown=120)
        except self.MaxRetriesExceededError:
            logger.error('[Celery] 批次 IPXE 網路品質檢測重試次數已達上限')
            return {
                'success': False,
                'total_servers': 0,
                'success_count': 0,
                'failed_count': 0,
                'results': [],
                'error_message': str(exc),
                'timestamp': timezone.now().isoformat()
            }


# ==================== Switch 管理相關任務 ====================

@shared_task(
    bind=True,
    name='api.tasks.auto_identify_switches_task',
    max_retries=2,
    default_retry_delay=120,  # 失敗後 2 分鐘重試
    time_limit=600,  # 硬限制 10 分鐘
    soft_time_limit=540  # 軟限制 9 分鐘
)
def auto_identify_switches_task(self, server_id=None):
    """
    自動識別 Switch 設備（根據製造商）
    
    Args:
        server_id: DHCP Server ID（可選，None 表示所有 Server）
        
    Returns:
        dict: 執行結果統計
    """
    try:
        from api.models import DHCPServer, DHCPLease, NetworkSwitch
        from api.serializers import DHCPLeaseSerializer
        
        logger.info(f'[Celery] 開始自動識別 Switch - Server ID: {server_id if server_id else "All"}')
        
        # Switch 製造商關鍵字
        SWITCH_VENDOR_KEYWORDS = [
            'cisco', 'juniper', 'arista', 'extreme', 'huawei', 'h3c',
            'hewlett packard', 'hpe', 'dell', 'brocade', 'netgear',
            'd-link', 'tp-link', 'ubiquiti', 'mikrotik', 'zyxel',
            'switch', 'switching', 'ruijie', 'planet', 'edimax',
        ]
        
        def is_switch_vendor(vendor):
            """判斷製造商是否為 Switch 廠商"""
            if not vendor:
                return False
            
            vendor_lower = vendor.lower()
            exclude_keywords = ['intel', 'realtek', 'broadcom', 'microsoft', 'apple', 
                               'samsung', 'lenovo', 'acer', 'gigabyte', 'msi']
            
            for exclude in exclude_keywords:
                if exclude in vendor_lower:
                    return False
            
            for keyword in SWITCH_VENDOR_KEYWORDS:
                if keyword in vendor_lower:
                    return True
            
            return False
        
        # 獲取要處理的 Server
        if server_id:
            servers = DHCPServer.objects.filter(id=server_id)
        else:
            servers = DHCPServer.objects.all()
        
        if not servers.exists():
            error_msg = f'找不到 DHCP Server (ID: {server_id})'
            logger.error(f'[Celery] {error_msg}')
            return {'success': False, 'error_message': error_msg}
        
        # 處理每個 Server
        results = []
        total_created = 0
        total_updated = 0
        
        for server in servers:
            try:
                leases = DHCPLease.objects.filter(server=server, is_active=True)
                switch_devices = []
                
                for lease in leases:
                    serializer = DHCPLeaseSerializer(lease)
                    vendor = serializer.data.get('vendor', '')
                    if is_switch_vendor(vendor):
                        switch_devices.append({'lease': lease, 'vendor': vendor})
                
                created_count = 0
                updated_count = 0
                
                for device in switch_devices:
                    lease = device['lease']
                    remote_id = lease.mac_address
                    switch_name = lease.hostname if lease.hostname else f"Switch-{lease.ip_address.replace('.', '-')}"
                    
                    switch, created = NetworkSwitch.objects.update_or_create(
                        remote_id=remote_id,
                        defaults={
                            'name': switch_name,
                            'mac_address': lease.mac_address,
                            'ip_address': lease.ip_address,
                            'status': 'active',
                            'dhcp_server': server,
                        }
                    )
                    
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
                    
                    lease.remote_id = remote_id
                    lease.relay_agent_info = f"VendorBased,RemoteID={remote_id}"
                    lease.save()
                    switch.update_statistics()
                
                total_created += created_count
                total_updated += updated_count
                
                results.append({
                    'server_id': server.id,
                    'server_name': server.name,
                    'switches_found': len(switch_devices),
                    'switches_created': created_count,
                    'switches_updated': updated_count,
                    'success': True
                })
                
                logger.info(f'[Celery] Server {server.name} 完成 - 創建: {created_count}, 更新: {updated_count}')
                
            except Exception as e:
                logger.error(f'[Celery] Server {server.name} 處理失敗: {e}', exc_info=True)
                results.append({'server_id': server.id, 'server_name': server.name, 'success': False, 'error_message': str(e)})
        
        logger.info(f'[Celery] Switch 自動識別完成 - 處理: {len(results)} | 創建: {total_created} | 更新: {total_updated}')
        
        return {
            'success': True,
            'servers_processed': len(results),
            'total_switches_created': total_created,
            'total_switches_updated': total_updated,
            'results': results,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error('[Celery] Switch 自動識別失敗', exc_info=True)
        try:
            raise self.retry(exc=exc, countdown=120)
        except self.MaxRetriesExceededError:
            logger.error('[Celery] Switch 自動識別重試次數已達上限')
            return {'success': False, 'error_message': str(exc), 'timestamp': timezone.now().isoformat()}


@shared_task(
    bind=True,
    name='api.tasks.check_gitlab_connection_task',
    max_retries=2,
    default_retry_delay=30,
    time_limit=30,  # 硬限制 30 秒
    soft_time_limit=25  # 軟限制 25 秒
)
def check_gitlab_connection_task(self):
    """
    定時檢查 GitLab 連線品質
    
    每 5 分鐘執行一次，測試 GitLab 伺服器的連線品質並記錄到資料庫
    
    Returns:
        dict: 測試結果
    """
    try:
        from .models import GitLabConnection
        import sys
        
        # 導入 library 中的服務（使用容器內的絕對路徑）
        if '/app/library' not in sys.path:
            sys.path.insert(0, '/app/library')
        from services.gitlab_service import test_gitlab_connection
        
        logger.info('[Celery] 開始 GitLab 連線品質檢查')
        
        # GitLab 伺服器配置
        GITLAB_URL = 'http://10.252.170.11/'
        GITLAB_NAME = 'CW1 GitLab Server'
        
        # 執行連線測試
        result = test_gitlab_connection(GITLAB_URL, GITLAB_NAME)
        
        # 儲存到資料庫
        connection_log = GitLabConnection.objects.create(
            gitlab_url=result['gitlab_url'],
            gitlab_name=result['gitlab_name'],
            ping_latency=result['ping_latency'],
            http_response_time=result['http_response_time'],
            http_status_code=result['http_status_code'],
            status=result['status'],
            is_reachable=result['is_reachable'],
            packet_loss=result['packet_loss'],
            error_message=result['error_message']
        )
        
        logger.info(
            f'[Celery] GitLab 連線檢查完成 - '
            f'Status: {result["status"]} | '
            f'Ping: {result["ping_latency"]}ms | '
            f'HTTP: {result["http_response_time"]}s'
        )
        
        return {
            'success': True,
            'status': result['status'],
            'is_reachable': result['is_reachable'],
            'ping_latency': result['ping_latency'],
            'http_response_time': result['http_response_time'],
            'record_id': connection_log.id,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error('[Celery] GitLab 連線檢查失敗', exc_info=True)
        
        # 自動重試（最多 2 次）
        try:
            raise self.retry(exc=exc, countdown=30)
        except self.MaxRetriesExceededError:
            logger.error('[Celery] GitLab 連線檢查重試次數已達上限')
            return {
                'success': False,
                'error_message': str(exc),
                'timestamp': timezone.now().isoformat()
            }


@shared_task(
    bind=True,
    name='api.tasks.auto_store_workspaces',
    max_retries=2,
    default_retry_delay=300,  # 失敗後 5 分鐘重試
    time_limit=3300,  # 硬限制 55 分鐘
    soft_time_limit=3000  # 軟限制 50 分鐘
)
def auto_store_workspaces(self, dry_run=False, max_builds=10):
    """
    自動存儲 Jenkins Workspace 到 NAS
    
    根據配置的規則，自動掃描符合條件的 Build 並存儲其 Workspace。
    
    規則（從 Django Settings 讀取）：
    - 只存儲 SUCCESS 的 Build
    - 只存儲最近 24 小時內的 Build
    - 至少 30 分鐘前完成的 Build（避免正在執行）
    - 跳過已存儲的 Build
    - 每次最多存儲 N 個 Build（預設 10）
    
    Args:
        dry_run: 試運行模式，不實際存儲（預設 False）
        max_builds: 每次執行最多存儲的 Build 數量（預設 10）
        
    Returns:
        dict: {
            'success': bool,
            'total_found': int,        # 找到符合條件的 Build 數量
            'processed': int,          # 實際處理的數量
            'stored': int,             # 成功存儲的數量
            'skipped': int,            # 跳過的數量
            'failed': int,             # 失敗的數量
            'details': list,           # 詳細結果
            'total_size': int,         # 總存儲大小（bytes）
            'total_files': int,        # 總文件數
            'duration': float,         # 執行時間（秒）
        }
    """
    from .models import JenkinsBuild
    from library.services.jenkins_storage_service import JenkinsStorageService
    import re
    import time
    
    start_time = time.time()
    
    try:
        logger.info('=' * 60)
        logger.info('[Celery] 開始自動存儲 Jenkins Workspace')
        logger.info('=' * 60)
        logger.info(f'[Celery] 模式: {"試運行" if dry_run else "正式執行"}')
        logger.info(f'[Celery] 每次最多存儲: {max_builds} 個 Build')
        
        # 定義存儲規則
        rules = {
            'store_success': True,      # 存儲 SUCCESS 的 Build
            'store_failure': False,     # 不存儲 FAILURE
            'store_unstable': False,    # 不存儲 UNSTABLE
            'store_aborted': False,     # 不存儲 ABORTED
            'max_age_hours': 72,        # 只存儲 72 小時（3 天）內的 Build
            'min_age_minutes': 30,      # 至少 30 分鐘前的 Build
            'skip_already_stored': True, # 跳過已存儲的 Build
        }
        
        logger.info('[Celery] 存儲規則：')
        logger.info(f'[Celery]   - 存儲狀態: SUCCESS')
        logger.info(f'[Celery]   - 時間範圍: 最近 {rules["max_age_hours"]} 小時')
        logger.info(f'[Celery]   - 最小完成時間: {rules["min_age_minutes"]} 分鐘前')
        logger.info(f'[Celery]   - 跳過已存儲: {rules["skip_already_stored"]}')
        
        # 計算時間範圍
        now = timezone.now()
        max_age = now - timedelta(hours=rules['max_age_hours'])
        min_age = now - timedelta(minutes=rules['min_age_minutes'])
        
        # 查詢符合條件的 Build
        queryset = JenkinsBuild.objects.select_related('job', 'job__server').filter(
            result__in=['SUCCESS', 'FAILURE'],   # 處理成功和失敗的 Build
            build_timestamp__gte=max_age,        # 最近 N 小時內
            build_timestamp__lte=min_age,        # 至少 N 分鐘前完成
            is_building=False,                   # 確保 Build 已完成
        )
        
        # 跳過已存儲的 Build
        if rules['skip_already_stored']:
            queryset = queryset.filter(is_workspace_stored=False)
        
        # 排序：優先處理最新的 Build
        queryset = queryset.order_by('-build_timestamp')[:max_builds]
        
        total_found = queryset.count()
        logger.info(f'[Celery] 找到 {total_found} 個符合條件的 Build')
        
        if total_found == 0:
            logger.info('[Celery] 沒有需要處理的 Build')
            return {
                'success': True,
                'total_found': 0,
                'processed': 0,
                'stored': 0,
                'skipped': 0,
                'failed': 0,
                'details': [],
                'total_size': 0,
                'total_files': 0,
                'duration': time.time() - start_time,
            }
        
        # 處理每個 Build
        results = {
            'processed': 0,
            'stored': 0,
            'skipped': 0,
            'failed': 0,
            'details': [],
            'total_size': 0,
            'total_files': 0,
        }
        
        for i, build in enumerate(queryset, 1):
            logger.info(f'[Celery] [{i}/{total_found}] 處理 Build: {build.job.name} #{build.build_number}')
            
            try:
                results['processed'] += 1
                
                # 試運行模式：不實際存儲
                if dry_run:
                    logger.info(f'[Celery] [試運行] 跳過存儲 Build #{build.build_number}')
                    results['skipped'] += 1
                    results['details'].append({
                        'build_id': build.id,
                        'job_name': build.job.name,
                        'build_number': build.build_number,
                        'status': 'skipped',
                        'reason': 'dry_run',
                    })
                    continue
                
                # 解析 Jenkins Server IP
                jenkins_url = build.job.server.url
                match = re.search(r'https?://([^:/]+)', jenkins_url)
                if not match:
                    logger.error(f'[Celery] 無法解析 Jenkins Server IP: {jenkins_url}')
                    results['failed'] += 1
                    results['details'].append({
                        'build_id': build.id,
                        'job_name': build.job.name,
                        'build_number': build.build_number,
                        'status': 'failed',
                        'error': '無法解析 Jenkins Server IP',
                    })
                    continue
                
                jenkins_ip = match.group(1)
                workspace_url = f"{build.url}ws/"
                
                # 創建存儲服務
                storage = JenkinsStorageService(
                    jenkins_server_ip=jenkins_ip,
                    job_name=build.job.name,
                    build_number=build.build_number
                )
                
                # 檢查 NAS 路徑
                path_check = storage.check_storage_path_accessible()
                if not path_check['accessible'] or not path_check['writable']:
                    logger.error(f'[Celery] NAS 路徑不可訪問或不可寫')
                    results['failed'] += 1
                    results['details'].append({
                        'build_id': build.id,
                        'job_name': build.job.name,
                        'build_number': build.build_number,
                        'status': 'failed',
                        'error': 'NAS 路徑不可訪問',
                    })
                    continue
                
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
                    
                    results['stored'] += 1
                    results['total_size'] += result['workspace_size']
                    results['total_files'] += result['files_count']
                    
                    logger.info(
                        f'[Celery] ✅ 成功存儲 Build #{build.build_number} | '
                        f'{result["files_count"]} files, '
                        f'{result["workspace_size"] / 1024:.1f} KB'
                    )
                    
                    results['details'].append({
                        'build_id': build.id,
                        'job_name': build.job.name,
                        'build_number': build.build_number,
                        'status': 'success',
                        'workspace_size': result['workspace_size'],
                        'files_count': result['files_count'],
                        'workspace_path': result['workspace_path'],
                    })
                else:
                    results['failed'] += 1
                    logger.warning(
                        f'[Celery] ❌ 存儲失敗 Build #{build.build_number}: '
                        f'{result.get("error", "Unknown error")}'
                    )
                    
                    results['details'].append({
                        'build_id': build.id,
                        'job_name': build.job.name,
                        'build_number': build.build_number,
                        'status': 'failed',
                        'error': result.get('error', 'Unknown error'),
                    })
                
            except Exception as e:
                results['failed'] += 1
                logger.error(
                    f'[Celery] ❌ 處理 Build #{build.build_number} 時發生錯誤: {e}',
                    exc_info=True
                )
                results['details'].append({
                    'build_id': build.id,
                    'job_name': build.job.name,
                    'build_number': build.build_number,
                    'status': 'error',
                    'error': str(e),
                })
        
        # 計算執行時間
        duration = time.time() - start_time
        
        # 記錄最終結果
        logger.info('=' * 60)
        logger.info('[Celery] 執行報告')
        logger.info('=' * 60)
        logger.info(f'[Celery] 總處理數: {results["processed"]}')
        logger.info(f'[Celery] 成功: {results["stored"]} ✅')
        logger.info(f'[Celery] 跳過: {results["skipped"]} ⚠️')
        logger.info(f'[Celery] 失敗: {results["failed"]} ❌')
        logger.info(f'[Celery] 總存儲大小: {results["total_size"] / 1024:.1f} KB')
        logger.info(f'[Celery] 總文件數: {results["total_files"]}')
        logger.info(f'[Celery] 總耗時: {duration:.1f} 秒')
        logger.info('=' * 60)
        logger.info('[Celery] ✅ 自動存儲完成')
        logger.info('=' * 60)
        
        return {
            'success': True,
            'total_found': total_found,
            'processed': results['processed'],
            'stored': results['stored'],
            'skipped': results['skipped'],
            'failed': results['failed'],
            'details': results['details'],
            'total_size': results['total_size'],
            'total_files': results['total_files'],
            'duration': duration,
        }
        
    except Exception as exc:
        duration = time.time() - start_time
        logger.error(f'[Celery] 自動存儲失敗（執行 {duration:.1f} 秒）', exc_info=True)
        
        # 自動重試（最多 2 次）
        try:
            raise self.retry(exc=exc, countdown=300)
        except self.MaxRetriesExceededError:
            logger.error('[Celery] 自動存儲重試次數已達上限')
            return {
                'success': False,
                'total_found': 0,
                'processed': 0,
                'stored': 0,
                'skipped': 0,
                'failed': 0,
                'details': [],
                'total_size': 0,
                'total_files': 0,
                'duration': duration,
                'error_message': str(exc),
            }


# ==================== Jenkins Builds 同步任務 ====================

@shared_task(
    bind=True,
    name='api.tasks.sync_jenkins_builds',
    max_retries=2,
    default_retry_delay=300,  # 失敗後 5 分鐘重試
    time_limit=3600,  # 硬限制 1 小時
    soft_time_limit=3300  # 軟限制 55 分鐘
)
def sync_jenkins_builds(self, server_id=None, max_builds_per_job=20, max_age_days=3):
    """
    同步 Jenkins Builds 到資料庫
    
    從 Jenkins API 獲取所有 Jobs 的最新 Builds，並創建/更新資料庫記錄。
    這個任務是自動存儲 Workspace 的前置步驟。
    
    Args:
        server_id: Jenkins Server ID（可選，None 表示所有 Server）
        max_builds_per_job: 每個 Job 最多同步幾個 Builds（預設 20）
        max_age_days: 只同步最近 N 天內的 Builds（預設 3 天）
        
    Returns:
        dict: {
            'success': bool,
            'total_servers': int,      # 處理的伺服器數量
            'total_jobs': int,          # 處理的 Jobs 數量
            'total_builds_found': int,  # 從 Jenkins 找到的 Builds 數量
            'builds_created': int,      # 新增的 Builds 數量
            'builds_updated': int,      # 更新的 Builds 數量
            'builds_skipped': int,      # 跳過的 Builds 數量（太舊）
            'errors': int,              # 錯誤數量
            'duration': float,          # 執行時間（秒）
        }
    """
    from .models import JenkinsServer, JenkinsJob, JenkinsBuild
    from library.services.jenkins_client import JenkinsClient
    from datetime import datetime, timedelta
    from django.utils import timezone as dj_timezone
    import pytz
    
    start_time = time.time()
    
    try:
        logger.info('[Celery] 🔄 開始同步 Jenkins Builds 到資料庫')
        logger.info(f'[Celery]   - Server ID: {server_id if server_id else "All"}')
        logger.info(f'[Celery]   - 每個 Job 最多: {max_builds_per_job} 個 Builds')
        logger.info(f'[Celery]   - 時間範圍: 最近 {max_age_days} 天')
        
        # 計算時間範圍（使用 UTC 時區）
        cutoff_time = datetime.now(pytz.UTC) - timedelta(days=max_age_days)
        
        # 獲取要處理的 Server
        if server_id:
            servers = JenkinsServer.objects.filter(id=server_id, status='online')
        else:
            servers = JenkinsServer.objects.filter(status='online')
        
        if not servers.exists():
            logger.warning('[Celery] ⚠️  沒有找到在線的 Jenkins Server')
            return {
                'success': False,
                'total_servers': 0,
                'total_jobs': 0,
                'total_builds_found': 0,
                'builds_created': 0,
                'builds_updated': 0,
                'builds_skipped': 0,
                'errors': 0,
                'duration': 0,
                'error_message': 'No online servers found'
            }
        
        total_servers = servers.count()
        total_jobs_processed = 0
        total_builds_found = 0
        builds_created = 0
        builds_updated = 0
        builds_skipped = 0
        errors = 0
        
        logger.info(f'[Celery] 📡 找到 {total_servers} 個在線的 Jenkins Server')
        
        for server in servers:
            logger.info(f'[Celery] 🖥️  處理 Server: {server.name} ({server.url})')
            
            # 獲取該 Server 的所有 Jobs
            jobs = JenkinsJob.objects.filter(server=server)
            jobs_count = jobs.count()
            logger.info(f'[Celery]   - 找到 {jobs_count} 個 Jobs')
            
            if jobs_count == 0:
                continue
            
            # 創建 Jenkins Client
            client = None
            try:
                client = JenkinsClient(
                    base_url=server.url,
                    username=server.username,
                    api_token=server.api_token
                )
                
                # 處理每個 Job
                for job in jobs:
                    try:
                        # 從 Jenkins API 獲取 Builds
                        jenkins_builds = client.get_job_builds(
                            job.name, 
                            limit=max_builds_per_job
                        )
                        
                        if not jenkins_builds:
                            continue
                        
                        total_builds_found += len(jenkins_builds)
                        
                        # 處理每個 Build
                        for build_data in jenkins_builds:
                            try:
                                build_number = build_data.get('number')
                                result = build_data.get('result')
                                building = build_data.get('building', False)
                                duration = build_data.get('duration', 0)
                                url = build_data.get('url', '')
                                
                                # 轉換時間戳
                                timestamp = build_data.get('timestamp', 0) / 1000
                                build_timestamp = datetime.fromtimestamp(timestamp, tz=pytz.UTC)
                                
                                # 檢查是否在時間範圍內
                                if build_timestamp < cutoff_time:
                                    builds_skipped += 1
                                    continue
                                
                                # 創建或更新 Build 記錄
                                build, created = JenkinsBuild.objects.update_or_create(
                                    job=job,
                                    build_number=build_number,
                                    defaults={
                                        'display_name': f'#{build_number}',
                                        'url': url,
                                        'result': result or 'UNKNOWN',
                                        'is_building': building,
                                        'duration': duration,
                                        'build_timestamp': build_timestamp,
                                    }
                                )
                                
                                if created:
                                    builds_created += 1
                                    logger.debug(f'[Celery]     ✅ 創建 Build: {job.name} #{build_number} ({result})')
                                else:
                                    builds_updated += 1
                                    logger.debug(f'[Celery]     🔄 更新 Build: {job.name} #{build_number} ({result})')
                                
                            except Exception as e:
                                errors += 1
                                logger.error(f'[Celery]     ❌ 處理 Build 失敗: {job.name} #{build_number} - {e}')
                        
                        total_jobs_processed += 1
                        
                    except Exception as e:
                        errors += 1
                        logger.error(f'[Celery]   ❌ 處理 Job 失敗: {job.name} - {e}')
                
            except Exception as e:
                errors += 1
                logger.error(f'[Celery] ❌ 連接 Server 失敗: {server.name} - {e}', exc_info=True)
            finally:
                if client:
                    client.close()
        
        duration = time.time() - start_time
        
        # 記錄結果
        logger.info('[Celery] ✅ Jenkins Builds 同步完成')
        logger.info(f'[Celery]   - 處理 Servers: {total_servers} 個')
        logger.info(f'[Celery]   - 處理 Jobs: {total_jobs_processed} 個')
        logger.info(f'[Celery]   - 找到 Builds: {total_builds_found} 個')
        logger.info(f'[Celery]   - 創建 Builds: {builds_created} 個')
        logger.info(f'[Celery]   - 更新 Builds: {builds_updated} 個')
        logger.info(f'[Celery]   - 跳過 Builds: {builds_skipped} 個（超過 {max_age_days} 天）')
        logger.info(f'[Celery]   - 錯誤: {errors} 個')
        logger.info(f'[Celery]   - 執行時間: {duration:.1f} 秒')
        
        return {
            'success': True,
            'total_servers': total_servers,
            'total_jobs': total_jobs_processed,
            'total_builds_found': total_builds_found,
            'builds_created': builds_created,
            'builds_updated': builds_updated,
            'builds_skipped': builds_skipped,
            'errors': errors,
            'duration': duration,
        }
        
    except Exception as exc:
        duration = time.time() - start_time
        logger.error(f'[Celery] ❌ 同步 Jenkins Builds 失敗（執行 {duration:.1f} 秒）', exc_info=True)
        
        # 自動重試（最多 2 次）
        try:
            raise self.retry(exc=exc, countdown=300)
        except self.MaxRetriesExceededError:
            logger.error('[Celery] 同步 Jenkins Builds 重試次數已達上限')
            return {
                'success': False,
                'total_servers': 0,
                'total_jobs': 0,
                'total_builds_found': 0,
                'builds_created': 0,
                'builds_updated': 0,
                'builds_skipped': 0,
                'errors': 0,
                'duration': duration,
                'error_message': str(exc),
            }
