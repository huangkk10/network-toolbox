"""
Celery 定時任務

將 Django 管理命令包裝為 Celery 任務
"""

import logging
import time
from pathlib import Path
from typing import Dict, Any
from celery import shared_task
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from .models import DHCPServer, DHCPLog, DHCPLease, DHCPScope, JenkinsBuild, JenkinsServer
from .services import DHCPLogService
from library.services.jenkins_storage_service import JenkinsStorageService

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
    name='api.tasks.update_switch_statistics_task',
    max_retries=1,
    time_limit=60,
    soft_time_limit=50
)
def update_switch_statistics_task(self, switch_id):
    """
    更新單個 Switch 的統計資訊
    
    用於在租約變化時異步更新 Switch 統計，避免阻塞主流程
    
    Args:
        switch_id: NetworkSwitch ID
        
    Returns:
        dict: 更新結果
    """
    try:
        from api.models import NetworkSwitch
        
        switch = NetworkSwitch.objects.get(id=switch_id)
        switch.update_statistics()
        
        logger.debug(f'[Celery] Switch 統計更新完成: {switch.name}')
        
        return {
            'success': True,
            'switch_id': switch_id,
            'switch_name': switch.name,
            'connected_devices': switch.connected_devices,
            'active_ports': switch.active_ports,
            'timestamp': timezone.now().isoformat()
        }
        
    except NetworkSwitch.DoesNotExist:
        logger.error(f'[Celery] Switch 不存在 (ID: {switch_id})')
        return {'success': False, 'error': 'Switch not found'}
        
    except Exception as exc:
        logger.error(f'[Celery] Switch 統計更新失敗: {exc}', exc_info=True)
        return {'success': False, 'error': str(exc)}


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
    同步 Jenkins Builds 到資料庫（只處理新 Builds）
    
    從 Jenkins API 獲取所有 Jobs 的最新 Builds，並創建資料庫記錄。
    已存在的 Builds 會被跳過，不占用處理配額。
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
            'builds_updated': int,      # 更新的 Builds 數量（狀態變化）
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
                'builds_skipped': 0,
                'errors': 0,
                'duration': 0,
                'error_message': 'No online servers found'
            }
        
        total_servers = servers.count()
        total_jobs_processed = 0
        total_builds_found = 0
        builds_created = 0
        builds_updated = 0  # 🆕 新增：追蹤更新的 Builds 數量
        builds_skipped = 0
        errors = 0
        
        # ✅ V2 優化統計：添加詳細計數器
        total_builds_checked = 0      # 從 API 獲取的總 Build 數
        total_builds_filtered = 0     # 智能過濾掉的 Build 數
        total_api_calls = 0           # Jenkins API 調用次數
        total_jobs_skipped = 0        # 跳過的穩定 Jobs 數
        
        # ✅ V2 優化：收集需要批量更新的 Jobs
        jobs_to_update = []
        
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
                        # ✅ V2 優化：追蹤 Job 是否需要更新
                        job_needs_update = False
                        
                        # ✅ 優化：只查詢最近的 Builds + 只加載需要的字段
                        existing_builds = {
                            b.build_number: b
                            for b in JenkinsBuild.objects.filter(job=job)
                                .only(
                                    'id', 'build_number', 'result', 'is_building', 
                                    'duration', 'failed_stage', 'pipeline_stages', 'updated_at'
                                )
                                .order_by('-build_number')[:max_builds_per_job]
                        }
                        
                        # 從 Jenkins API 獲取 Builds
                        jenkins_builds = client.get_job_builds(
                            job.name, 
                            limit=max_builds_per_job
                        )
                        
                        # ✅ V2 統計：記錄 API 調用
                        total_api_calls += 1
                        
                        if not jenkins_builds:
                            continue
                        
                        total_builds_found += len(jenkins_builds)
                        total_builds_checked += len(jenkins_builds)  # ✅ V2 統計：記錄檢查數
                        
                        # ✅ V2 優化：縮短智能過濾時間窗口（1小時 → 15分鐘）
                        # Jenkins Build 通常在幾分鐘內完成，1 小時窗口過大
                        recent_time = dj_timezone.now() - timedelta(minutes=15)
                        
                        new_builds = []
                        builds_to_check = []
                        
                        for b in jenkins_builds:
                            build_num = b.get('number')
                            if build_num in existing_builds:
                                db_build = existing_builds[build_num]
                                
                                # 只檢查活躍的 Builds：
                                # 1. 正在構建的（is_building=True）
                                # 2. 最近 15 分鐘內更新的（縮短窗口）
                                # 3. 狀態未確定的（UNKNOWN/None）
                                if (db_build.is_building or 
                                    db_build.updated_at >= recent_time or 
                                    db_build.result in ['UNKNOWN', None]):
                                    builds_to_check.append((b, db_build))
                                else:
                                    # ✅ V2 統計：記錄被過濾掉的 Build
                                    total_builds_filtered += 1
                            else:
                                new_builds.append(b)
                        
                        logger.info(
                            f'[Celery]     📊 Job {job.name}: '
                            f'{len(new_builds)} 個新 Builds, '
                            f'{len(builds_to_check)} 個需檢查, '
                            f'{total_builds_filtered} 個已過濾'
                        )

                        
                        # 處理每個 Build（新建或更新）
                        # 處理新 Builds（創建）
                        for build_data in new_builds:
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
                                
                                # 🆕 創建 Build 記錄
                                build = JenkinsBuild.objects.create(
                                    job=job,
                                    build_number=build_number,
                                    display_name=f'#{build_number}',
                                    url=url,
                                    result=result or 'UNKNOWN',
                                    is_building=building,
                                    duration=duration,
                                    build_timestamp=build_timestamp,
                                )
                                builds_created += 1
                                logger.debug(f'[Celery]     ✅ 創建 Build: {job.name} #{build_number} ({result})')
                                
                                # ✅ V2 優化：標記 Job 需要更新（不立即 save）
                                if not job.last_build_time or build_timestamp > job.last_build_time:
                                    job.last_build_time = build_timestamp
                                    job.last_build_number = build_number
                                    job.last_build_status = result or 'UNKNOWN'
                                    job_needs_update = True
                                    logger.debug(f'[Celery]     🔄 標記 Job 需要更新 last_build_time: {build_timestamp}')
                                
                                # ✅ 優化：同步 Pipeline Stages（如果是 FAILURE 狀態，使用緩存）
                                if result == 'FAILURE':
                                    from django.core.cache import cache
                                    
                                    cache_key = f'failed_stages:{job.id}:{build_number}'
                                    failed_stages = cache.get(cache_key)
                                    
                                    if not failed_stages:
                                        try:
                                            # 獲取 Pipeline Stages
                                            failed_stages = client.get_failed_stages(job.name, build_number)
                                            if failed_stages:
                                                # 緩存 24 小時
                                                cache.set(cache_key, failed_stages, timeout=86400)
                                        except Exception as e:
                                            logger.error(f'[Celery]     ❌ 無法獲取 Pipeline Stages: {e}', exc_info=True)
                                    
                                    if failed_stages:
                                        # 儲存 failed stages（Django JSONField 會自動處理）
                                        build.pipeline_stages = failed_stages
                                        
                                        # 提取第一個失敗 Stage 的名稱
                                        first_failed = failed_stages[0]
                                        build.failed_stage = (
                                            first_failed.get('stage_name') or 
                                            first_failed.get('displayName') or 
                                            first_failed.get('name')
                                        )
                                        
                                        logger.info(f'[Celery]     🎯 發現失敗 Stage: {build.failed_stage}')
                                        build.save(update_fields=['pipeline_stages', 'failed_stage'])
                                        logger.info(f'[Celery]     ✅ 已儲存 Failed Stage: {build.failed_stage}')

                                
                            except Exception as e:
                                errors += 1
                                logger.error(f'[Celery]     ❌ 處理新 Build 失敗: {job.name} #{build_data.get("number")} - {e}')
                        
                        # ✅ 優化：批量更新現有 Builds
                        builds_to_update = []  # 收集需要更新的 Builds
                        job_builds_updated = 0
                        
                        for build_data, existing_build in builds_to_check:
                            try:
                                build_number = build_data.get('number')
                                result = build_data.get('result')
                                building = build_data.get('building', False)
                                duration = build_data.get('duration', 0)
                                
                                # 轉換時間戳（用於更新 Job）
                                timestamp = build_data.get('timestamp', 0) / 1000
                                build_timestamp = datetime.fromtimestamp(timestamp, tz=pytz.UTC)
                                
                                # 檢查是否需要更新
                                needs_update = False
                                
                                # 1. 檢查 result 是否變化（RUNNING → SUCCESS/FAILURE）
                                if result and result != existing_build.result:
                                    existing_build.result = result
                                    needs_update = True
                                    logger.debug(f'[Celery]     🔄 Build {job.name} #{build_number} 狀態變化: {existing_build.result} → {result}')
                                
                                # 2. 檢查 is_building 狀態（正在構建 → 已完成）
                                if existing_build.is_building and not building:
                                    existing_build.is_building = False
                                    needs_update = True
                                    logger.debug(f'[Celery]     ⏹️  Build {job.name} #{build_number} 構建完成')
                                
                                # 3. 檢查 duration（從 0 變為實際值）
                                if duration > 0 and existing_build.duration != duration:
                                    existing_build.duration = duration
                                    needs_update = True
                                
                                # 4. ✅ 優化：如果狀態變為 FAILURE，同步 failed_stage（使用緩存）
                                if result == 'FAILURE' and not existing_build.failed_stage:
                                    from django.core.cache import cache
                                    
                                    cache_key = f'failed_stages:{job.id}:{build_number}'
                                    failed_stages = cache.get(cache_key)
                                    
                                    if not failed_stages:
                                        try:
                                            failed_stages = client.get_failed_stages(job.name, build_number)
                                            if failed_stages:
                                                # 緩存 24 小時
                                                cache.set(cache_key, failed_stages, timeout=86400)
                                        except Exception as e:
                                            logger.error(f'[Celery]     ❌ 無法獲取 Pipeline Stages: {e}')
                                    
                                    if failed_stages:
                                        existing_build.pipeline_stages = failed_stages
                                        first_failed = failed_stages[0]
                                        existing_build.failed_stage = (
                                            first_failed.get('stage_name') or 
                                            first_failed.get('displayName') or 
                                            first_failed.get('name')
                                        )
                                        needs_update = True
                                        logger.debug(f'[Celery]     🎯 更新失敗 Stage: {existing_build.failed_stage}')

                                
                                # 收集需要更新的 Build
                                if needs_update:
                                    builds_to_update.append(existing_build)
                                    job_builds_updated += 1
                                    
                                    # ✅ V2 優化：標記 Job 需要更新（完整更新所有欄位）
                                    if not job.last_build_time or build_timestamp >= job.last_build_time:
                                        job.last_build_time = build_timestamp
                                        job.last_build_number = build_number
                                        job.last_build_status = result or 'UNKNOWN'
                                        job_needs_update = True
                                        logger.debug(f'[Celery]     🔄 更新 Job last_build_time: {build_timestamp}, #{build_number}')
                                
                            except Exception as e:
                                errors += 1
                                logger.error(f'[Celery]     ❌ 處理 Build 更新失敗: {job.name} #{build_number} - {e}')
                        
                        # ✅ 批量更新 Builds
                        if builds_to_update:
                            try:
                                JenkinsBuild.objects.bulk_update(
                                    builds_to_update,
                                    ['result', 'is_building', 'duration', 'failed_stage', 'pipeline_stages'],
                                    batch_size=100
                                )
                                builds_updated += len(builds_to_update)
                                logger.info(f'[Celery]     ✅ 批量更新 {len(builds_to_update)} 個 Builds')
                            except Exception as e:
                                errors += 1
                                logger.error(f'[Celery]     ❌ 批量更新 Builds 失敗: {job.name} - {e}')

                        
                        # ✅ V2 優化：收集需要更新的 Job
                        if job_needs_update:
                            jobs_to_update.append(job)
                        
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
        
        # ✅ V2 優化：批量更新所有 Jobs
        if jobs_to_update:
            try:
                JenkinsJob.objects.bulk_update(
                    jobs_to_update,
                    ['last_build_time', 'last_build_number', 'last_build_status'],
                    batch_size=100
                )
                logger.info(f'[Celery] 📊 批量更新 {len(jobs_to_update)} 個 Jobs')
            except Exception as e:
                errors += 1
                logger.error(f'[Celery] ❌ 批量更新 Jobs 失敗: {e}')
        
        duration = time.time() - start_time
        
        # ✅ V2 優化：計算過濾效率
        filter_rate = (total_builds_filtered / total_builds_checked * 100) if total_builds_checked > 0 else 0
        
        # 記錄結果
        logger.info('[Celery] ✅ Jenkins Builds 同步完成')
        logger.info(f'[Celery]   - 處理 Servers: {total_servers} 個')
        logger.info(f'[Celery]   - 處理 Jobs: {total_jobs_processed} 個')
        logger.info(f'[Celery]   - 跳過穩定 Jobs: {total_jobs_skipped} 個')
        logger.info(f'[Celery]   - 找到 Builds: {total_builds_found} 個')
        logger.info(f'[Celery]   - 創建 Builds: {builds_created} 個')
        logger.info(f'[Celery]   - 更新 Builds: {builds_updated} 個')
        logger.info(f'[Celery]   - 跳過 Builds: {builds_skipped} 個（超過 {max_age_days} 天）')
        logger.info(f'[Celery]   📈 V2 統計:')
        logger.info(f'[Celery]      - 總檢查數: {total_builds_checked} 個 Builds')
        logger.info(f'[Celery]      - 智能過濾: {total_builds_filtered} 個 ({filter_rate:.1f}%)')
        logger.info(f'[Celery]      - API 調用: {total_api_calls} 次')
        logger.info(f'[Celery]      - 批量更新: {len(jobs_to_update)} 個 Jobs')
        logger.info(f'[Celery]   - 錯誤: {errors} 個')
        logger.info(f'[Celery]   - 執行時間: {duration:.1f} 秒')
        
        return {
            'success': True,
            'total_servers': total_servers,
            'total_jobs': total_jobs_processed,
            'total_jobs_skipped': total_jobs_skipped,          # ✅ V2 新增
            'total_builds_found': total_builds_found,
            'builds_created': builds_created,
            'builds_updated': builds_updated,
            'builds_skipped': builds_skipped,
            'total_builds_checked': total_builds_checked,      # ✅ V2 新增
            'total_builds_filtered': total_builds_filtered,    # ✅ V2 新增
            'total_api_calls': total_api_calls,                # ✅ V2 新增
            'jobs_batch_updated': len(jobs_to_update),         # ✅ V2 新增
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


# ============================================================================
# 即時監控：高頻同步活躍 Jenkins Builds (1 分鐘)
# ============================================================================

@shared_task(
    bind=True,
    name='api.tasks.sync_active_jenkins_builds',
    max_retries=2,
    time_limit=60  # 1 分鐘超時
)
def sync_active_jenkins_builds(self, server_id=None):
    """
    高頻同步活躍的 Jenkins Builds（1 分鐘執行一次）
    
    【策略】
    - 只同步 is_building=True 的 Builds（正在構建中的）
    - 更新 Pipeline Stages、result、duration、failed_stage
    - 不發現新 Builds（由 sync_jenkins_builds 負責）
    - 輕量級、快速執行（預計 5-15 秒）
    
    【參數】
    - server_id: 可選，指定特定伺服器（預設：所有活躍伺服器）
    
    【返回】
    - success: 是否成功
    - servers_checked: 檢查的伺服器數量
    - active_builds_found: 找到的活躍 Builds 數量
    - builds_updated: 更新的 Builds 數量
    - builds_completed: 完成的 Builds 數量（is_building: True → False）
    - api_calls: API 調用次數
    - duration: 執行時間（秒）
    """
    start_time = time.time()
    logger.info('[Celery] 🚀 開始高頻同步活躍 Jenkins Builds')
    
    servers_checked = 0
    active_builds_found = 0
    builds_updated = 0
    builds_completed = 0
    api_calls = 0
    errors = 0
    
    try:
        # 1️⃣ 獲取活躍伺服器
        if server_id:
            servers = JenkinsServer.objects.filter(id=server_id, is_active=True)
        else:
            servers = JenkinsServer.objects.filter(is_active=True)
        
        if not servers.exists():
            logger.warning('[Celery] ⚠️ 沒有活躍的 Jenkins 伺服器')
            return {
                'success': True,
                'servers_checked': 0,
                'active_builds_found': 0,
                'builds_updated': 0,
                'builds_completed': 0,
                'api_calls': 0,
                'duration': time.time() - start_time,
            }
        
        # 2️⃣ 查詢所有活躍的 Builds（is_building=True）
        # 使用 select_related 優化查詢，避免 N+1 問題
        active_builds = JenkinsBuild.objects.filter(
            is_building=True,
            job__server__is_active=True
        ).select_related('job', 'job__server').order_by('-build_timestamp')
        
        active_builds_found = active_builds.count()
        
        if active_builds_found == 0:
            logger.info('[Celery] ✅ 沒有活躍的 Builds，跳過同步')
            return {
                'success': True,
                'servers_checked': servers.count(),
                'active_builds_found': 0,
                'builds_updated': 0,
                'builds_completed': 0,
                'api_calls': 0,
                'duration': time.time() - start_time,
            }
        
        logger.info(f'[Celery] 📊 找到 {active_builds_found} 個活躍 Builds')
        
        # 3️⃣ 按伺服器分組處理
        builds_by_server = {}
        for build in active_builds:
            server_id = build.job.server.id
            if server_id not in builds_by_server:
                builds_by_server[server_id] = []
            builds_by_server[server_id].append(build)
        
        # 4️⃣ 對每個伺服器進行同步
        builds_to_update = []
        
        for server in servers:
            if server.id not in builds_by_server:
                continue
            
            servers_checked += 1
            server_builds = builds_by_server[server.id]
            
            logger.info(f'[Celery] 🔄 同步伺服器: {server.name} ({len(server_builds)} 個活躍 Builds)')
            
            # 建立 Jenkins 客戶端連接
            client = None
            try:
                from library.services.jenkins_client import JenkinsClient
                client = JenkinsClient(server.url, server.username, server.api_token)
                
                # 5️⃣ 對每個活躍 Build 進行更新
                for build in server_builds:
                    try:
                        # 從 Jenkins API 獲取最新狀態
                        # get_job_builds 返回 Build 列表，我們只取第一個（最新的）
                        build_list = client.get_job_builds(build.job.name, limit=1)
                        api_calls += 1
                        
                        if not build_list:
                            logger.warning(f'[Celery]   ⚠️ 無法獲取 Build 資訊: {build.job.name} #{build.build_number}')
                            continue
                        
                        # 找到對應的 Build（可能返回的是最新 Build，不一定是我們要的）
                        # 所以我們需要檢查 build_number 是否匹配
                        build_info = None
                        for b in client.get_job_builds(build.job.name, limit=5):
                            if b.get('number') == build.build_number:
                                build_info = b
                                break
                        
                        if not build_info:
                            logger.warning(f'[Celery]   ⚠️ 找不到對應的 Build: {build.job.name} #{build.build_number}')
                            continue
                        
                        # 檢查是否有變化
                        needs_update = False
                        
                        # 6️⃣ 更新基本資訊
                        new_result = build_info.get('result')
                        new_building = build_info.get('building', False)
                        new_duration = build_info.get('duration', 0)
                        
                        # Result 變化
                        if new_result and new_result != build.result:
                            build.result = new_result
                            needs_update = True
                            logger.info(f'[Celery]   🔄 {build.job.name} #{build.build_number}: {build.result} → {new_result}')
                        
                        # Building 狀態變化（完成構建）
                        if build.is_building and not new_building:
                            build.is_building = False
                            builds_completed += 1
                            needs_update = True
                            logger.info(f'[Celery]   ✅ {build.job.name} #{build.build_number} 構建完成')
                        
                        # Duration 更新
                        if new_duration > 0 and build.duration != new_duration:
                            build.duration = new_duration
                            needs_update = True
                        
                        # 7️⃣ 同步 Pipeline Stages（所有活躍 Builds，不只 FAILURE）
                        try:
                            pipeline_nodes = client.get_blue_ocean_pipeline_nodes(build.job.name, build.build_number)
                            
                            if pipeline_nodes:
                                build.pipeline_stages = pipeline_nodes
                                needs_update = True
                                
                                # 如果有失敗的 Stage，提取第一個
                                failed_stages = [
                                    node for node in pipeline_nodes 
                                    if node.get('result') in ['FAILURE', 'ABORTED', 'UNSTABLE']
                                ]
                                
                                if failed_stages and not build.failed_stage:
                                    first_failed = failed_stages[0]
                                    build.failed_stage = (
                                        first_failed.get('displayName') or 
                                        first_failed.get('name')
                                    )
                                    logger.info(f'[Celery]   🎯 發現失敗 Stage: {build.failed_stage}')
                        
                        except Exception as e:
                            # Pipeline Stages 同步失敗不影響其他更新
                            logger.warning(f'[Celery]   ⚠️ 無法同步 Pipeline Stages: {e}')
                        
                        # 8️⃣ 收集需要更新的 Build
                        if needs_update:
                            builds_to_update.append(build)
                    
                    except Exception as e:
                        errors += 1
                        logger.error(f'[Celery]   ❌ 更新 Build 失敗: {build.job.name} #{build.build_number} - {e}')
            
            except Exception as e:
                errors += 1
                logger.error(f'[Celery] ❌ 連接伺服器失敗: {server.name} - {e}', exc_info=True)
            
            finally:
                if client:
                    client.close()
        
        # 9️⃣ 批量更新所有變化的 Builds
        if builds_to_update:
            try:
                JenkinsBuild.objects.bulk_update(
                    builds_to_update,
                    ['result', 'is_building', 'duration', 'pipeline_stages', 'failed_stage'],
                    batch_size=50
                )
                builds_updated = len(builds_to_update)
                logger.info(f'[Celery] ✅ 批量更新 {builds_updated} 個活躍 Builds')
            except Exception as e:
                errors += 1
                logger.error(f'[Celery] ❌ 批量更新失敗: {e}', exc_info=True)
        
        # 🔟 記錄結果
        duration = time.time() - start_time
        logger.info('[Celery] ✅ 高頻同步完成')
        logger.info(f'[Celery]   - 檢查伺服器: {servers_checked} 個')
        logger.info(f'[Celery]   - 活躍 Builds: {active_builds_found} 個')
        logger.info(f'[Celery]   - 更新 Builds: {builds_updated} 個')
        logger.info(f'[Celery]   - 完成 Builds: {builds_completed} 個')
        logger.info(f'[Celery]   - API 調用: {api_calls} 次')
        logger.info(f'[Celery]   - 錯誤: {errors} 個')
        logger.info(f'[Celery]   - 執行時間: {duration:.2f} 秒')
        
        return {
            'success': True,
            'servers_checked': servers_checked,
            'active_builds_found': active_builds_found,
            'builds_updated': builds_updated,
            'builds_completed': builds_completed,
            'api_calls': api_calls,
            'errors': errors,
            'duration': duration,
        }
    
    except Exception as exc:
        duration = time.time() - start_time
        logger.error(f'[Celery] ❌ 高頻同步失敗（執行 {duration:.2f} 秒）', exc_info=True)
        
        # 自動重試（最多 2 次，30 秒後重試）
        try:
            raise self.retry(exc=exc, countdown=30)
        except self.MaxRetriesExceededError:
            logger.error('[Celery] 高頻同步重試次數已達上限')
            return {
                'success': False,
                'servers_checked': 0,
                'active_builds_found': 0,
                'builds_updated': 0,
                'builds_completed': 0,
                'api_calls': 0,
                'errors': 0,
                'duration': duration,
                'error_message': str(exc),
            }


# ============================================================================
# iPXE 日誌同步任務
# ============================================================================

@shared_task(
    bind=True,
    name='api.tasks.verify_ipxe_ssh_connection_task',
    max_retries=1,
    time_limit=30  # SSH 連接驗證最多 30 秒
)
def verify_ipxe_ssh_connection_task(self, server_id):
    """
    驗證 iPXE Server 的 SSH 連接
    
    此任務在 iPXE Server 創建後立即執行（通常在 2 秒後）
    用於快速檢測 SSH 連接問題，並更新伺服器狀態
    
    成功：更新 status = 'online', last_error = None
    失敗：更新 status = 'error', last_error = 錯誤訊息
    
    Args:
        server_id: IPXEServer ID
        
    Returns:
        dict: {
            'server_id': int,
            'server_ip': str,
            'success': bool,
            'error_message': str or None
        }
    """
    from api.models import IPXEServer
    
    try:
        logger.info(f'[Celery] 開始驗證 iPXE Server SSH 連接 - Server ID: {server_id}')
        
        # 獲取伺服器
        try:
            server = IPXEServer.objects.get(id=server_id)
        except IPXEServer.DoesNotExist:
            error_msg = f'iPXE Server ID {server_id} 不存在'
            logger.error(f'[Celery] {error_msg}')
            return {
                'server_id': server_id,
                'server_ip': None,
                'success': False,
                'error_message': error_msg
            }
        
        # 檢查是否有 SSH 密碼
        if not server.ssh_password:
            error_msg = '缺少 SSH 密碼'
            logger.warning(f'[Celery] iPXE Server {server.ip_address} - {error_msg}')
            
            # 更新伺服器狀態
            server.status = 'error'
            server.last_error = error_msg
            server.save(update_fields=['status', 'last_error'])
            
            return {
                'server_id': server_id,
                'server_ip': server.ip_address,
                'success': False,
                'error_message': error_msg
            }
        
        # 嘗試 SSH 連接
        from library.services.ssh_service import SSHService
        
        ssh = SSHService(
            host=server.ip_address,
            username=server.ssh_username or 'root',
            password=server.ssh_password,
            port=server.ssh_port or 22
        )
        
        if ssh.connect():
            # 連接成功
            ssh.close()
            
            # 更新伺服器狀態
            server.status = 'online'
            server.last_error = None
            server.save(update_fields=['status', 'last_error'])
            
            logger.info(f'[Celery] ✅ iPXE Server {server.ip_address} SSH 連接驗證成功')
            
            return {
                'server_id': server_id,
                'server_ip': server.ip_address,
                'success': True,
                'error_message': None
            }
        else:
            # 連接失敗
            error_msg = 'SSH 連接失敗（無法建立連接）'
            
            # 更新伺服器狀態
            server.status = 'error'
            server.last_error = error_msg
            server.save(update_fields=['status', 'last_error'])
            
            logger.error(f'[Celery] ❌ iPXE Server {server.ip_address} SSH 連接失敗')
            
            return {
                'server_id': server_id,
                'server_ip': server.ip_address,
                'success': False,
                'error_message': error_msg
            }
        
    except Exception as exc:
        error_msg = f'SSH 驗證異常: {str(exc)}'
        logger.error(f'[Celery] iPXE Server {server_id} SSH 驗證失敗', exc_info=True)
        
        # 更新伺服器狀態
        try:
            server = IPXEServer.objects.get(id=server_id)
            server.status = 'error'
            server.last_error = error_msg
            server.save(update_fields=['status', 'last_error'])
        except:
            pass
        
        return {
            'server_id': server_id,
            'server_ip': None,
            'success': False,
            'error_message': error_msg
        }


@shared_task(
    bind=True,
    name='api.tasks.verify_ipxe_server_ssh_task',
    max_retries=2,
    default_retry_delay=30,
    time_limit=60,
    soft_time_limit=50
)
def verify_ipxe_server_ssh_task(self, server_id):
    """
    驗證 iPXE Server 的 SSH 連接
    
    在創建新的 iPXE Server 後自動執行，確保：
    1. SSH 連接可用
    2. Docker 容器正在運行
    3. 日誌文件可訪問
    
    Args:
        server_id: IPXEServer ID
        
    Returns:
        dict: {
            'server_id': int,
            'server_ip': str,
            'connection_status': str,  # 'success' 或 'failed'
            'containers_found': int,
            'error_message': str or None
        }
    """
    from api.models import IPXEServer
    from api.ipxe_service import IPXEService
    
    try:
        logger.info(f'[Celery] 開始驗證 iPXE Server SSH 連接 - Server ID: {server_id}')
        
        # 獲取伺服器
        try:
            server = IPXEServer.objects.get(id=server_id)
        except IPXEServer.DoesNotExist:
            error_msg = f'iPXE Server ID {server_id} 不存在'
            logger.error(f'[Celery] {error_msg}')
            return {
                'server_id': server_id,
                'server_ip': None,
                'connection_status': 'failed',
                'containers_found': 0,
                'error_message': error_msg
            }
        
        # 更新狀態為驗證中
        server.connection_status = 'verifying'
        server.save(update_fields=['connection_status'])
        
        # 創建服務實例並測試連接
        service = IPXEService(server)
        
        # 1. 測試 SSH 連接
        if not service.test_connection():
            error_msg = f'SSH 連接失敗: {server.ip_address}'
            logger.error(f'[Celery] {error_msg}')
            
            server.connection_status = 'failed'
            server.status = 'error'
            server.last_error = error_msg
            server.save(update_fields=['connection_status', 'status', 'last_error'])
            
            return {
                'server_id': server_id,
                'server_ip': server.ip_address,
                'connection_status': 'failed',
                'containers_found': 0,
                'error_message': error_msg
            }
        
        # 2. 檢查 Docker 容器
        containers = service.get_container_names()
        if not containers:
            error_msg = f'未找到 iPXE Docker 容器'
            logger.warning(f'[Celery] {error_msg} - Server: {server.name}')
            
            server.connection_status = 'no_containers'
            server.status = 'warning'
            server.last_error = error_msg
            server.save(update_fields=['connection_status', 'status', 'last_error'])
            
            return {
                'server_id': server_id,
                'server_ip': server.ip_address,
                'connection_status': 'no_containers',
                'containers_found': 0,
                'error_message': error_msg
            }
        
        # 3. 驗證成功
        server.connection_status = 'connected'
        server.status = 'active'
        server.last_error = None
        server.save(update_fields=['connection_status', 'status', 'last_error'])
        
        logger.info(
            f'[Celery] iPXE Server SSH 驗證成功 - Server: {server.name} ({server.ip_address}) | '
            f'找到 {len(containers)} 個容器'
        )
        
        return {
            'server_id': server_id,
            'server_ip': server.ip_address,
            'connection_status': 'connected',
            'containers_found': len(containers),
            'error_message': None
        }
        
    except Exception as exc:
        logger.error(f'[Celery] 驗證 iPXE Server SSH 連接失敗 - Server ID: {server_id}', exc_info=True)
        
        # 更新伺服器狀態
        try:
            server = IPXEServer.objects.get(id=server_id)
            server.connection_status = 'error'
            server.status = 'error'
            server.last_error = str(exc)
            server.save(update_fields=['connection_status', 'status', 'last_error'])
        except:
            pass
        
        # 自動重試（最多 2 次）
        try:
            raise self.retry(exc=exc, countdown=30)
        except self.MaxRetriesExceededError:
            logger.error(f'[Celery] iPXE Server SSH 驗證達到最大重試次數 - Server ID: {server_id}')
            return {
                'server_id': server_id,
                'server_ip': None,
                'connection_status': 'error',
                'containers_found': 0,
                'error_message': f'驗證失敗，已達最大重試次數: {str(exc)}'
            }


@shared_task(
    bind=True,
    name='api.tasks.sync_ipxe_logs_task',
    max_retries=3,
    default_retry_delay=60,  # 失敗後 60 秒重試
    time_limit=240,  # 硬限制 4 分鐘
    soft_time_limit=210  # 軟限制 3.5 分鐘
)
def sync_ipxe_logs_task(self, server_id, limit=1000):
    """
    同步 iPXE 日誌到資料庫
    
    Args:
        server_id: IPXEServer ID
        limit: 每個容器收集的日誌數量（預設: 1000）
        
    Returns:
        dict: {
            'server_id': int,
            'server_name': str,
            'mac_logs': int,    # MAC 管理日誌數
            'boot_logs': int,   # 開機日誌數
            'total': int,       # 總日誌數
            'errors': int       # 錯誤數
        }
    """
    from api.models import IPXEServer
    from api.ipxe_service import IPXEService
    
    try:
        logger.info(f'[Celery] 開始同步 iPXE 日誌 - Server ID: {server_id}, Limit: {limit}')
        
        # 獲取伺服器
        try:
            server = IPXEServer.objects.get(id=server_id)
        except IPXEServer.DoesNotExist:
            error_msg = f'iPXE Server ID {server_id} 不存在'
            logger.error(f'[Celery] {error_msg}')
            return {
                'server_id': server_id,
                'server_name': None,
                'mac_logs': 0,
                'boot_logs': 0,
                'total': 0,
                'errors': 1,
                'error_message': error_msg
            }
        
        # 檢查連接狀態（僅在已連接時執行同步）
        if hasattr(server, 'connection_status') and server.connection_status not in ['connected', None]:
            if server.connection_status == 'verifying':
                logger.info(f'[Celery] Server {server.name} SSH 驗證中，稍後重試')
                # 60 秒後重試
                raise self.retry(countdown=60)
            elif server.connection_status in ['failed', 'error', 'no_containers']:
                error_msg = f'Server {server.name} 連接狀態異常: {server.connection_status}'
                logger.warning(f'[Celery] {error_msg}，跳過日誌同步')
                return {
                    'server_id': server_id,
                    'server_name': server.name,
                    'mac_logs': 0,
                    'boot_logs': 0,
                    'total': 0,
                    'errors': 0,
                    'skipped': True,
                    'error_message': error_msg
                }
        
        # 創建服務實例並執行同步
        service = IPXEService(server)
        result = service.sync_logs_to_db(limit=limit)
        
        # 檢查是否有錯誤
        if 'error' in result:
            logger.error(f'[Celery] iPXE 日誌同步失敗 - Server: {server.name} | 錯誤: {result["error"]}')
            return {
                'server_id': server_id,
                'server_name': server.name,
                'mac_logs': 0,
                'boot_logs': 0,
                'total': 0,
                'errors': 1,
                'error_message': result['error']
            }
        
        # 添加伺服器資訊
        result['server_id'] = server_id
        result['server_name'] = server.name
        result['errors'] = 0
        
        # 記錄結果
        logger.info(
            f'[Celery] iPXE 日誌同步完成 - Server: {server.name} | '
            f'MAC 日誌: {result["mac_logs"]} 條 | '
            f'BOOT 日誌: {result["boot_logs"]} 條 | '
            f'總計: {result["total"]} 條'
        )
        
        return result
        
    except Exception as exc:
        logger.error(f'[Celery] 同步 iPXE 日誌失敗 - Server ID: {server_id}', exc_info=True)
        
        # 自動重試（最多 3 次）
        try:
            raise self.retry(exc=exc, countdown=60)
        except self.MaxRetriesExceededError:
            logger.error(f'[Celery] 同步重試次數已達上限 - Server ID: {server_id}')
            return {
                'server_id': server_id,
                'server_name': None,
                'mac_logs': 0,
                'boot_logs': 0,
                'total': 0,
                'errors': 1,
                'error_message': str(exc)
            }


@shared_task(
    bind=True,
    name='api.tasks.sync_all_ipxe_logs_task',
    max_retries=2,
    default_retry_delay=300,  # 失敗後 5 分鐘重試
    time_limit=1800,  # 硬限制 30 分鐘
    soft_time_limit=1650  # 軟限制 27.5 分鐘
)
def sync_all_ipxe_logs_task(self, limit=1000):
    """
    批次同步所有 iPXE Server 的日誌（定時任務）
    
    適用場景：
    - 定時自動同步所有伺服器的日誌
    - 確保所有伺服器都有最新的日誌數據
    
    Args:
        limit: 每個伺服器每個容器最多同步的日誌數量
        
    Returns:
        dict: {
            'total_servers': int,    # 處理的伺服器總數
            'success_count': int,    # 成功的伺服器數
            'failed_count': int,     # 失敗的伺服器數
            'total_logs_created': int,  # 總共新增的日誌數
            'results': [...]         # 每個伺服器的詳細結果
        }
    """
    from api.models import IPXEServer
    from api.ipxe_service import IPXEService
    
    try:
        logger.info(f'[Celery] 開始批次同步所有 iPXE Server 的日誌 (limit={limit})')
        
        # 獲取所有在線的 iPXE 伺服器
        servers = IPXEServer.objects.filter(status='online')
        total_servers = servers.count()
        
        logger.info(f'[Celery] 找到 {total_servers} 個在線的 iPXE Server')
        
        results = []
        success_count = 0
        failed_count = 0
        total_logs_created = 0
        
        for server in servers:
            try:
                logger.info(f'[Celery] 正在同步 Server 日誌: {server.name} ({server.ip_address})')
                
                # 創建日誌服務並同步
                service = IPXEService(server)
                result = service.sync_logs_to_db(limit=limit)
                
                # 檢查是否有錯誤
                if 'error' in result:
                    logger.error(f'[Celery] Server {server.name} 日誌同步失敗 - {result["error"]}')
                    result['server_id'] = server.id
                    result['server_name'] = server.name
                    result['server_ip'] = server.ip_address
                    results.append(result)
                    failed_count += 1
                    continue
                
                # 添加伺服器資訊
                result['server_id'] = server.id
                result['server_name'] = server.name
                result['server_ip'] = server.ip_address
                
                results.append(result)
                success_count += 1
                total_logs_created += result.get('total', 0)
                
                logger.info(
                    f'[Celery] Server {server.name} 日誌同步成功 - '
                    f'MAC: {result.get("mac_logs", 0)} 條 | '
                    f'BOOT: {result.get("boot_logs", 0)} 條 | '
                    f'總計: {result.get("total", 0)} 條'
                )
                
            except Exception as e:
                logger.error(f'[Celery] 同步 Server {server.name} 時發生錯誤: {e}', exc_info=True)
                results.append({
                    'server_id': server.id,
                    'server_name': server.name,
                    'server_ip': server.ip_address,
                    'error': str(e)
                })
                failed_count += 1
        
        # 彙總結果
        summary = {
            'total_servers': total_servers,
            'success_count': success_count,
            'failed_count': failed_count,
            'total_logs_created': total_logs_created,
            'results': results
        }
        
        logger.info(
            f'[Celery] 批次同步完成 - '
            f'總計: {total_servers} 個 | '
            f'成功: {success_count} 個 | '
            f'失敗: {failed_count} 個 | '
            f'新增日誌: {total_logs_created} 條'
        )
        
        return summary
        
    except Exception as exc:
        logger.error('[Celery] 批次同步 iPXE 日誌失敗', exc_info=True)
        
        # 自動重試（最多 2 次）
        try:
            raise self.retry(exc=exc, countdown=300)
        except self.MaxRetriesExceededError:
            logger.error('[Celery] 批次同步重試次數已達上限')
            return {
                'total_servers': 0,
                'success_count': 0,
                'failed_count': 0,
                'total_logs_created': 0,
                'results': [],
                'error_message': str(exc)
            }


@shared_task(
    bind=True,
    name='api.tasks.health_check_ipxe_servers_task',
    max_retries=1,
    default_retry_delay=300,
    time_limit=600,  # 10 分鐘
    soft_time_limit=540
)
def health_check_ipxe_servers_task(self):
    """
    健康檢查所有 iPXE Server 的連接狀態（定時任務）
    
    功能：
    1. 檢查所有 iPXE Server 的 SSH 連接
    2. 更新 connection_status 狀態
    3. 發現異常時記錄錯誤訊息
    
    建議排程：每小時執行一次
    
    Returns:
        dict: {
            'total_servers': int,       # 檢查的伺服器總數
            'healthy_count': int,       # 健康的伺服器數
            'unhealthy_count': int,     # 異常的伺服器數
            'results': [...]            # 每個伺服器的檢查結果
        }
    """
    from api.models import IPXEServer
    from api.ipxe_service import IPXEService
    
    try:
        logger.info('[Celery] 開始執行 iPXE Server 健康檢查')
        
        # 獲取所有 iPXE Server（包括離線的）
        servers = IPXEServer.objects.all()
        total_servers = servers.count()
        
        logger.info(f'[Celery] 找到 {total_servers} 個 iPXE Server 需要檢查')
        
        results = []
        healthy_count = 0
        unhealthy_count = 0
        
        for server in servers:
            try:
                logger.info(f'[Celery] 檢查 Server: {server.name} ({server.ip_address})')
                
                # 創建服務實例並測試連接
                service = IPXEService(server)
                
                # 測試 SSH 連接
                if not service.test_connection():
                    # 連接失敗
                    server.connection_status = 'failed'
                    server.status = 'offline'
                    server.last_error = 'SSH 連接失敗（健康檢查）'
                    server.save(update_fields=['connection_status', 'status', 'last_error'])
                    
                    unhealthy_count += 1
                    results.append({
                        'server_id': server.id,
                        'server_name': server.name,
                        'server_ip': server.ip_address,
                        'status': 'unhealthy',
                        'connection_status': 'failed',
                        'error': 'SSH 連接失敗'
                    })
                    
                    logger.warning(f'[Celery] Server {server.name} SSH 連接失敗')
                    continue
                
                # 檢查 Docker 容器
                containers = service.get_container_names()
                
                if not containers:
                    # 無容器
                    server.connection_status = 'no_containers'
                    server.status = 'warning'
                    server.last_error = '未找到 iPXE Docker 容器（健康檢查）'
                    server.save(update_fields=['connection_status', 'status', 'last_error'])
                    
                    unhealthy_count += 1
                    results.append({
                        'server_id': server.id,
                        'server_name': server.name,
                        'server_ip': server.ip_address,
                        'status': 'unhealthy',
                        'connection_status': 'no_containers',
                        'error': '未找到容器'
                    })
                    
                    logger.warning(f'[Celery] Server {server.name} 未找到 iPXE 容器')
                    continue
                
                # 連接正常
                server.connection_status = 'connected'
                server.status = 'online'
                server.last_error = None
                server.save(update_fields=['connection_status', 'status', 'last_error'])
                
                healthy_count += 1
                results.append({
                    'server_id': server.id,
                    'server_name': server.name,
                    'server_ip': server.ip_address,
                    'status': 'healthy',
                    'connection_status': 'connected',
                    'containers_found': len(containers)
                })
                
                logger.info(f'[Celery] Server {server.name} 健康狀態正常（找到 {len(containers)} 個容器）')
                
            except Exception as e:
                logger.error(f'[Celery] 檢查 Server {server.name} 時發生錯誤: {e}', exc_info=True)
                
                # 更新為錯誤狀態
                try:
                    server.connection_status = 'error'
                    server.status = 'error'
                    server.last_error = f'健康檢查錯誤: {str(e)}'
                    server.save(update_fields=['connection_status', 'status', 'last_error'])
                except:
                    pass
                
                unhealthy_count += 1
                results.append({
                    'server_id': server.id,
                    'server_name': server.name,
                    'server_ip': server.ip_address,
                    'status': 'error',
                    'connection_status': 'error',
                    'error': str(e)
                })
        
        # 彙總結果
        summary = {
            'total_servers': total_servers,
            'healthy_count': healthy_count,
            'unhealthy_count': unhealthy_count,
            'results': results
        }
        
        logger.info(
            f'[Celery] 健康檢查完成 - '
            f'總計: {total_servers} 個 | '
            f'健康: {healthy_count} 個 | '
            f'異常: {unhealthy_count} 個'
        )
        
        return summary
        
    except Exception as exc:
        logger.error('[Celery] iPXE Server 健康檢查失敗', exc_info=True)
        
        # 自動重試（最多 1 次）
        try:
            raise self.retry(exc=exc, countdown=300)
        except self.MaxRetriesExceededError:
            logger.error('[Celery] 健康檢查重試次數已達上限')
            return {
                'total_servers': 0,
                'healthy_count': 0,
                'unhealthy_count': 0,
                'results': [],
                'error_message': str(exc)
            }


# ==================== Jenkins Storage Tasks ====================

@shared_task(
    bind=True,
    name='api.tasks.store_jenkins_build_task',
    max_retries=3,
    default_retry_delay=120,  # 失敗後 2 分鐘重試
    time_limit=600,  # 硬限制 10 分鐘
    soft_time_limit=540  # 軟限制 9 分鐘
)
def store_jenkins_build_task(self, build_id: int) -> Dict[str, Any]:
    """
    存儲單個 Jenkins Build 到 NAS
    
    Args:
        build_id: JenkinsBuild ID
        
    Returns:
        dict: {
            'success': bool,
            'build_id': int,
            'job_name': str,
            'build_number': int,
            'workspace_path': str,
            'workspace_size': int,
            'stored_items': list,  # ['workspace', 'config', 'log']
            'error': str (如果失敗)
        }
    """
    try:
        logger.info(f'[Celery] 開始存儲 Jenkins Build - Build ID: {build_id}')
        
        # 獲取 Build 記錄
        try:
            build = JenkinsBuild.objects.select_related('job', 'job__server').get(id=build_id)
        except JenkinsBuild.DoesNotExist:
            error_msg = f'Build 不存在: {build_id}'
            logger.error(f'[Celery] {error_msg}')
            return {
                'success': False,
                'build_id': build_id,
                'error': error_msg
            }
        
        # 檢查是否已存儲（Workspace + Console Log 都存在才算完整存儲）
        if build.is_workspace_stored and build.log_file_path:
            logger.info(f'[Celery] Build 已完整存儲（Workspace + Console Log），跳過 - {build.job.name} #{build.build_number}')
            return {
                'success': True,
                'build_id': build_id,
                'job_name': build.job.name,
                'build_number': build.build_number,
                'already_stored': True,
                'workspace_path': build.workspace_path,
                'log_file_path': build.log_file_path
            }
        
        # 如果只有 Workspace 但沒有 Console Log，記錄並繼續處理
        if build.is_workspace_stored and not build.log_file_path:
            logger.info(f'[Celery] Build 只有 Workspace，缺少 Console Log，補充下載 - {build.job.name} #{build.build_number}')
        
        # 檢查 Build 狀態（只存儲已完成的 Builds）
        if build.is_building:
            logger.info(f'[Celery] Build 正在構建中，稍後再試 - {build.job.name} #{build.build_number}')
            return {
                'success': False,
                'build_id': build_id,
                'job_name': build.job.name,
                'build_number': build.build_number,
                'error': 'Build 仍在構建中'
            }
        
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
            error_msg = f'NAS 路徑不可訪問或不可寫: {path_check.get("error")}'
            logger.error(f'[Celery] {error_msg}')
            
            # 如果是權限問題，不重試
            return {
                'success': False,
                'build_id': build_id,
                'job_name': build.job.name,
                'build_number': build.build_number,
                'error': error_msg
            }
        
        # 構建 Workspace URL
        workspace_url = f"{build.url}ws/"
        
        stored_items = []
        total_size = 0
        
        # 存儲 Workspace（如果尚未存儲）
        if build.is_workspace_stored and build.workspace_path:
            logger.info(f'[Celery] Workspace 已存在，跳過下載 - {build.job.name} #{build.build_number}')
            stored_items.append('workspace')
            # 從已存儲的 Workspace 計算大小
            workspace_path = Path(build.workspace_path)
            if workspace_path.exists():
                workspace_size = sum(
                    f.stat().st_size 
                    for f in workspace_path.rglob('*') 
                    if f.is_file()
                )
                total_size += workspace_size
        else:
            logger.info(f'[Celery] 開始存儲 Workspace - {build.job.name} #{build.build_number}')
            workspace_result = storage_service.store_workspace(
                workspace_url=workspace_url,
                username=server.username,
                api_token=server.api_token
            )
            
            if workspace_result['success']:
                logger.info(f'[Celery] Workspace 存儲成功 - 大小: {workspace_result["workspace_size"]} bytes')
                stored_items.append('workspace')
                total_size += workspace_result['workspace_size']
            else:
                logger.warning(
                    f'[Celery] ⚠️  Workspace 存儲失敗: '
                    f'{workspace_result.get("error")}'
                )
        
        # ===== 存儲 Console Log（無論 Workspace 是否成功都嘗試） =====
        logger.info(f'[Celery] 📝 開始存儲 Console Log - {build.job.name} #{build.build_number}')
        
        try:
            # 從 Jenkins API 獲取 Console Log
            from library.services.jenkins_client import JenkinsClient
            
            client = JenkinsClient(
                base_url=server.url,
                username=server.username,
                api_token=server.api_token
            )
            
            try:
                log_content = client.get_console_log(
                    build.job.name,
                    build.build_number
                )
                
                # 存儲到 NAS
                log_result = storage_service.store_console_log(log_content)
                
                if log_result['success']:
                    stored_items.append('console_log')
                    total_size += log_result['log_size']
                    
                    # 更新資料庫
                    build.log_file_path = log_result['log_path']
                    
                    logger.info(
                        f'[Celery] ✅ Console Log 存儲成功 - '
                        f'{log_result["log_size"] / (1024**2):.2f} MB'
                    )
                else:
                    logger.warning(
                        f'[Celery] ⚠️  Console Log 存儲失敗: '
                        f'{log_result.get("error")}'
                    )
                    
            except requests.HTTPError as e:
                # 404 錯誤：Console Log 不存在（可能已被清理）
                if e.response and e.response.status_code == 404:
                    logger.info(
                        f'[Celery] Console Log 不存在（可能已被清理）- '
                        f'{build.job.name} #{build.build_number}'
                    )
                else:
                    logger.warning(
                        f'[Celery] ⚠️  獲取 Console Log 失敗: {e}',
                        exc_info=True
                    )
                    
            finally:
                client.close()
                    
        except Exception as e:
            # Console Log 存儲失敗不影響整體流程
            logger.warning(
                f'[Celery] ⚠️  Console Log 處理失敗: {e}',
                exc_info=True
            )
        
        # 更新 Build 記錄
        if 'workspace' in stored_items:
            # 只有成功存儲 Workspace 才更新這些欄位
            if not build.is_workspace_stored:
                build.workspace_path = workspace_result['workspace_path']
                build.workspace_size = workspace_result['workspace_size']
                build.workspace_stored_at = timezone.now()
                build.is_workspace_stored = True
        
        # 無論 Workspace 是否成功，都保存 log_file_path
        build.save(update_fields=[
            'workspace_path', 'workspace_size', 
            'workspace_stored_at', 'is_workspace_stored',
            'log_file_path',
        ])
        
        logger.info(f'[Celery] Build 存儲完成 - {build.job.name} #{build.build_number}')
        
        return {
            'success': True,
            'build_id': build_id,
            'job_name': build.job.name,
            'build_number': build.build_number,
            'server_ip': server_ip,
            'workspace_path': build.workspace_path,
            'workspace_size': build.workspace_size if build.workspace_size else 0,
            'stored_items': stored_items,
            'total_size': total_size
        }
    
    except Exception as exc:
        logger.error(f'[Celery] 存儲 Jenkins Build 失敗 - Build ID: {build_id}', exc_info=True)
        
        # 自動重試
        try:
            raise self.retry(exc=exc, countdown=120)
        except self.MaxRetriesExceededError:
            logger.error(f'[Celery] 存儲重試次數已達上限 - Build ID: {build_id}')
            return {
                'success': False,
                'build_id': build_id,
                'error': str(exc),
                'max_retries_exceeded': True
            }


@shared_task(
    bind=True,
    name='api.tasks.auto_store_jenkins_builds_task',
    max_retries=1,
    default_retry_delay=300,
    time_limit=600,
    soft_time_limit=540
)
def auto_store_jenkins_builds_task(self, limit: int = 20) -> Dict[str, Any]:
    """
    自動掃描並存儲未存儲的 Jenkins Builds
    
    這是一個定時任務，會定期掃描資料庫中未存儲的 Builds，
    並自動觸發存儲任務。
    
    Args:
        limit: 每次掃描處理的最大 Builds 數量（默認 20）
        
    Returns:
        dict: {
            'total_pending': int,     # 待存儲的總數
            'processed': int,         # 本次處理的數量
            'tasks_created': int,     # 創建的任務數
            'skipped': int,           # 跳過的數量
            'results': list
        }
    """
    from django.conf import settings
    
    try:
        logger.info(f'[Celery] 開始自動存儲任務掃描 - Limit: {limit}')
        
        # 獲取存儲策略配置
        storage_policy = getattr(settings, 'JENKINS_STORAGE_POLICY', {})
        auto_store_enabled = storage_policy.get('auto_store', True)
        store_results = storage_policy.get('store_results', ['SUCCESS', 'FAILURE', 'UNSTABLE'])
        max_workspace_size_mb = storage_policy.get('max_workspace_size_mb', 500)
        
        if not auto_store_enabled:
            logger.info('[Celery] 自動存儲功能已禁用')
            return {
                'total_pending': 0,
                'processed': 0,
                'tasks_created': 0,
                'skipped': 0,
                'disabled': True
            }
        
        # 查詢未存儲的 Builds
        # 條件：
        # 1. is_workspace_stored = False
        # 2. is_building = False（已完成）
        # 3. result 在配置的結果列表中
        # 4. 有 URL（可訪問）
        query = JenkinsBuild.objects.filter(
            is_workspace_stored=False,
            is_building=False,
            url__isnull=False
        )
        
        # 如果配置了只存儲特定結果
        if store_results:
            query = query.filter(result__in=store_results)
        
        # 排序：優先處理最新的 Builds
        query = query.select_related('job', 'job__server').order_by('-build_timestamp')
        
        total_pending = query.count()
        logger.info(f'[Celery] 找到 {total_pending} 個待存儲的 Builds')
        
        # 限制處理數量
        builds_to_process = query[:limit]
        
        processed = 0
        tasks_created = 0
        skipped = 0
        results = []
        
        for build in builds_to_process:
            processed += 1
            
            try:
                # 檢查 Workspace 大小限制（如果有記錄的話）
                # 注意：這裡的 workspace_size 可能是 0（未獲取）
                
                # 創建異步存儲任務
                task = store_jenkins_build_task.delay(build.id)
                tasks_created += 1
                
                logger.info(
                    f'[Celery] 創建存儲任務 - '
                    f'Build: {build.job.name} #{build.build_number} | '
                    f'Task ID: {task.id}'
                )
                
                results.append({
                    'build_id': build.id,
                    'job_name': build.job.name,
                    'build_number': build.build_number,
                    'result': build.result,
                    'task_id': task.id,
                    'status': 'task_created'
                })
                
            except Exception as e:
                logger.error(
                    f'[Celery] 創建存儲任務失敗 - '
                    f'Build: {build.job.name} #{build.build_number} | '
                    f'Error: {e}',
                    exc_info=True
                )
                skipped += 1
                results.append({
                    'build_id': build.id,
                    'job_name': build.job.name,
                    'build_number': build.build_number,
                    'status': 'error',
                    'error': str(e)
                })
        
        summary = {
            'total_pending': total_pending,
            'processed': processed,
            'tasks_created': tasks_created,
            'skipped': skipped,
            'results': results
        }
        
        logger.info(
            f'[Celery] 自動存儲掃描完成 - '
            f'待存儲: {total_pending} | '
            f'已處理: {processed} | '
            f'任務創建: {tasks_created} | '
            f'跳過: {skipped}'
        )
        
        return summary
        
    except Exception as exc:
        logger.error('[Celery] 自動存儲掃描失敗', exc_info=True)
        
        # 自動重試
        try:
            raise self.retry(exc=exc, countdown=300)
        except self.MaxRetriesExceededError:
            logger.error('[Celery] 自動存儲掃描重試次數已達上限')
            return {
                'total_pending': 0,
                'processed': 0,
                'tasks_created': 0,
                'skipped': 0,
                'error_message': str(exc)
            }



# ==================== Jenkins Artifacts 自動存儲任務 ====================

@shared_task(
    bind=True,
    name='api.tasks.store_jenkins_artifacts_task',
    max_retries=3,
    default_retry_delay=300,  # 失敗後 5 分鐘重試
    time_limit=1800,  # 硬限制 30 分鐘
    soft_time_limit=1650  # 軟限制 27.5 分鐘
)
def store_jenkins_artifacts_task(self, build_id):
    """
    存儲單個 Jenkins Build 的 Artifacts 到 NAS
    
    這是一個可重試的任務，用於：
    - 手動觸發存儲特定 Build 的 Artifacts
    - 從批量自動存儲任務中調用
    - 失敗後自動重試（最多 3 次）
    
    Args:
        build_id: JenkinsBuild ID
        
    Returns:
        dict: {
            'success': bool,
            'build_id': int,
            'job_name': str,
            'build_number': int,
            'artifacts_path': str,
            'artifacts_size': int,
            'artifacts_count': int,
            'stored_items': list,
            'error_message': str (如果失敗)
        }
    """
    import re
    from .models import JenkinsBuild
    from library.services.jenkins_client import JenkinsClient
    from library.services.jenkins_storage_service import JenkinsStorageService
    
    try:
        logger.info(f'[Celery] 🚀 開始存儲 Jenkins Artifacts - Build ID: {build_id}')
        
        # 獲取 Build 記錄
        try:
            build = JenkinsBuild.objects.select_related('job', 'job__server').get(id=build_id)
        except JenkinsBuild.DoesNotExist:
            error_msg = f'Build ID {build_id} 不存在'
            logger.error(f'[Celery] ❌ {error_msg}')
            return {
                'success': False,
                'build_id': build_id,
                'error_message': error_msg
            }
        
        logger.info(
            f'[Celery] 📦 處理 Build: {build.job.name} #{build.build_number} | '
            f'Result: {build.result} | '
            f'Server: {build.job.server.name}'
        )
        
        # 檢查是否已經存儲
        if build.is_artifacts_stored:
            logger.info(f'[Celery] ⚠️  Artifacts 已經存儲過，跳過')
            return {
                'success': True,
                'build_id': build_id,
                'job_name': build.job.name,
                'build_number': build.build_number,
                'already_stored': True,
                'artifacts_path': build.artifacts_path,
                'artifacts_size': build.artifacts_size,
                'artifacts_count': build.artifacts_count,
            }
        
        # 1. 從 Jenkins 獲取 Artifacts 列表
        client = None
        try:
            client = JenkinsClient(
                base_url=build.job.server.url,
                username=build.job.server.username,
                api_token=build.job.server.api_token
            )
            
            artifacts_list = client.get_build_artifacts(
                build.job.name,
                build.build_number
            )
            
            logger.info(f'[Celery] 📋 從 Jenkins API 獲取到 {len(artifacts_list)} 個 Artifacts')
            
        finally:
            if client:
                client.close()
        
        # 如果沒有 Artifacts
        if not artifacts_list:
            logger.info(f'[Celery] ℹ️  該 Build 沒有 Artifacts')
            
            # 標記為已存儲（避免重複檢查）
            build.is_artifacts_stored = True
            build.artifacts_count = 0
            build.artifacts_stored_at = timezone.now()
            build.save()
            
            return {
                'success': True,
                'build_id': build_id,
                'job_name': build.job.name,
                'build_number': build.build_number,
                'artifacts_count': 0,
                'message': '該 Build 沒有 Artifacts'
            }
        
        # 2. 解析 Jenkins Server IP
        jenkins_url = build.job.server.url
        match = re.search(r'https?://([^:/]+)', jenkins_url)
        if not match:
            error_msg = '無法解析 Jenkins Server IP'
            logger.error(f'[Celery] ❌ {error_msg}: {jenkins_url}')
            return {
                'success': False,
                'build_id': build_id,
                'job_name': build.job.name,
                'build_number': build.build_number,
                'error_message': error_msg
            }
        
        jenkins_ip = match.group(1)
        logger.info(f'[Celery] 🖥️  Jenkins IP: {jenkins_ip}')
        
        # 3. 創建存儲服務並執行存儲
        storage = JenkinsStorageService(
            jenkins_server_ip=jenkins_ip,
            job_name=build.job.name,
            build_number=build.build_number
        )
        
        # 檢查 NAS 路徑
        path_check = storage.check_storage_path_accessible()
        if not path_check['accessible'] or not path_check['writable']:
            error_msg = 'NAS 路徑不可訪問或不可寫'
            logger.error(f'[Celery] ❌ {error_msg}')
            
            # 這類錯誤值得重試（可能是網路問題）
            raise Exception(error_msg)
        
        # 存儲 Artifacts（包含自動解壓和刪除原始壓縮檔）
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
            build.artifacts_list = result['stored_items']  # JSON 格式
            build.is_artifacts_stored = True
            build.artifacts_stored_at = timezone.now()
            build.save()
            
            logger.info(
                f'[Celery] ✅ 成功存儲 Artifacts | '
                f'檔案數: {result["artifacts_count"]} | '
                f'總大小: {result["artifacts_size"] / (1024**2):.2f} MB | '
                f'路徑: {result["artifacts_path"]}'
            )
            
            return {
                'success': True,
                'build_id': build_id,
                'job_name': build.job.name,
                'build_number': build.build_number,
                'artifacts_path': result['artifacts_path'],
                'artifacts_size': result['artifacts_size'],
                'artifacts_count': result['artifacts_count'],
                'stored_items': result['stored_items'],
            }
        else:
            error_msg = result.get('error', 'Unknown error')
            logger.error(f'[Celery] ❌ 存儲 Artifacts 失敗: {error_msg}')
            
            # 拋出異常以觸發重試機制
            raise Exception(error_msg)
        
    except Exception as exc:
        logger.error(
            f'[Celery] ❌ 存儲 Artifacts 失敗 - '
            f'Build ID: {build_id} | '
            f'Error: {exc}',
            exc_info=True
        )
        
        # 自動重試（最多 3 次）
        try:
            raise self.retry(exc=exc, countdown=300)
        except self.MaxRetriesExceededError:
            logger.error(f'[Celery] ❌ Artifacts 存儲重試次數已達上限 - Build ID: {build_id}')
            return {
                'success': False,
                'build_id': build_id,
                'error_message': str(exc),
                'retries_exhausted': True
            }


@shared_task(
    bind=True,
    name='api.tasks.auto_store_jenkins_artifacts_task',
    max_retries=2,
    default_retry_delay=600,  # 失敗後 10 分鐘重試
    time_limit=7200,  # 硬限制 2 小時
    soft_time_limit=6900  # 軟限制 1 小時 55 分鐘
)
def auto_store_jenkins_artifacts_task(self, max_builds=50, max_age_hours=168):
    """
    自動批量存儲 Jenkins Artifacts 到 NAS（定時任務）
    
    根據配置的規則，自動掃描符合條件的 Build 並存儲其 Artifacts。
    類似 auto_store_workspaces 的實現邏輯。
    
    規則：
    - 處理所有狀態的 Build（SUCCESS、FAILURE、UNSTABLE 等）
    - 只存儲有 Artifacts 的 Build
    - 只存儲最近 N 小時內的 Build（預設 168 小時 = 7 天）
    - 至少 30 分鐘前完成的 Build（避免正在執行）
    - 跳過已存儲的 Build
    - 每次最多存儲 N 個 Build（預設 50）
    
    Args:
        max_builds: 每次執行最多存儲的 Build 數量（預設 50）
        max_age_hours: 只存儲最近 N 小時內的 Build（預設 168 = 7 天）
        
    Returns:
        dict: {
            'success': bool,
            'total_found': int,        # 找到符合條件的 Build 數量
            'processed': int,          # 實際處理的數量
            'stored': int,             # 成功存儲的數量
            'no_artifacts': int,       # 沒有 Artifacts 的數量
            'failed': int,             # 失敗的數量
            'total_size': int,         # 總存儲大小（bytes）
            'total_artifacts': int,    # 總 Artifacts 數
            'duration': float,         # 執行時間（秒）
            'details': list            # 詳細結果
        }
    """
    from .models import JenkinsBuild
    import time
    
    start_time = time.time()
    
    try:
        logger.info('=' * 80)
        logger.info('[Celery] 🚀 開始自動存儲 Jenkins Artifacts（批量任務）')
        logger.info('=' * 80)
        logger.info(f'[Celery] 參數配置：')
        logger.info(f'[Celery]   - 每次最多存儲: {max_builds} 個 Build')
        logger.info(f'[Celery]   - 時間範圍: 最近 {max_age_hours} 小時 ({max_age_hours / 24:.1f} 天)')
        logger.info(f'[Celery]   - 存儲狀態: 所有狀態（SUCCESS、FAILURE、UNSTABLE 等）')
        logger.info(f'[Celery]   - 跳過已存儲: True')
        
        # 計算時間範圍
        now = timezone.now()
        max_age = now - timedelta(hours=max_age_hours)
        min_age = now - timedelta(minutes=30)  # 至少 30 分鐘前完成
        
        # 查詢符合條件的 Build（不限定 result 狀態）
        queryset = JenkinsBuild.objects.select_related('job', 'job__server').filter(
            build_timestamp__gte=max_age,        # 最近 N 小時內
            build_timestamp__lte=min_age,        # 至少 30 分鐘前完成
            is_building=False,                   # 確保 Build 已完成
            is_artifacts_stored=False,           # 跳過已存儲的
        ).exclude(
            result__in=['ABORTED', 'NOT_BUILT']  # 排除被中止和未建置的
        ).order_by('-build_timestamp')[:max_builds]  # 優先處理最新的
        
        total_found = queryset.count()
        logger.info(f'[Celery] 📊 找到 {total_found} 個符合條件的 Build')
        
        if total_found == 0:
            logger.info('[Celery] ℹ️  沒有需要處理的 Build')
            return {
                'success': True,
                'total_found': 0,
                'processed': 0,
                'stored': 0,
                'no_artifacts': 0,
                'failed': 0,
                'total_size': 0,
                'total_artifacts': 0,
                'duration': time.time() - start_time,
                'details': []
            }
        
        # 處理每個 Build
        results = {
            'processed': 0,
            'stored': 0,
            'no_artifacts': 0,
            'failed': 0,
            'total_size': 0,
            'total_artifacts': 0,
            'details': []
        }
        
        for i, build in enumerate(queryset, 1):
            logger.info(
                f'[Celery] [{i}/{total_found}] 處理 Build: '
                f'{build.job.name} #{build.build_number} | '
                f'Server: {build.job.server.name}'
            )
            
            try:
                results['processed'] += 1
                
                # 調用單個 Build 存儲任務
                result = store_jenkins_artifacts_task(build.id)
                
                if result['success']:
                    if result.get('already_stored'):
                        logger.info(f'[Celery]   ⚠️  已存儲，跳過')
                        results['details'].append({
                            'build_id': build.id,
                            'job_name': build.job.name,
                            'build_number': build.build_number,
                            'status': 'already_stored'
                        })
                    elif result.get('artifacts_count', 0) == 0:
                        results['no_artifacts'] += 1
                        logger.info(f'[Celery]   ℹ️  沒有 Artifacts')
                        results['details'].append({
                            'build_id': build.id,
                            'job_name': build.job.name,
                            'build_number': build.build_number,
                            'status': 'no_artifacts'
                        })
                    else:
                        results['stored'] += 1
                        results['total_size'] += result.get('artifacts_size', 0)
                        results['total_artifacts'] += result.get('artifacts_count', 0)
                        
                        logger.info(
                            f'[Celery]   ✅ 成功 | '
                            f'{result["artifacts_count"]} 個檔案, '
                            f'{result["artifacts_size"] / (1024**2):.2f} MB'
                        )
                        
                        results['details'].append({
                            'build_id': build.id,
                            'job_name': build.job.name,
                            'build_number': build.build_number,
                            'status': 'success',
                            'artifacts_count': result['artifacts_count'],
                            'artifacts_size': result['artifacts_size'],
                            'artifacts_path': result['artifacts_path']
                        })
                else:
                    results['failed'] += 1
                    error_msg = result.get('error_message', 'Unknown error')
                    logger.error(f'[Celery]   ❌ 失敗: {error_msg}')
                    
                    results['details'].append({
                        'build_id': build.id,
                        'job_name': build.job.name,
                        'build_number': build.build_number,
                        'status': 'failed',
                        'error': error_msg
                    })
                
            except Exception as e:
                results['failed'] += 1
                logger.error(
                    f'[Celery]   ❌ 處理失敗: {e}',
                    exc_info=True
                )
                
                results['details'].append({
                    'build_id': build.id,
                    'job_name': build.job.name,
                    'build_number': build.build_number,
                    'status': 'error',
                    'error': str(e)
                })
        
        # 計算執行時間
        duration = time.time() - start_time
        
        # 記錄最終結果
        logger.info('=' * 80)
        logger.info('[Celery] 📊 執行報告')
        logger.info('=' * 80)
        logger.info(f'[Celery] 總處理數: {results["processed"]} 個 Build')
        logger.info(f'[Celery] 成功存儲: {results["stored"]} ✅')
        logger.info(f'[Celery] 無 Artifacts: {results["no_artifacts"]} ℹ️')
        logger.info(f'[Celery] 失敗: {results["failed"]} ❌')
        logger.info(f'[Celery] 總存儲大小: {results["total_size"] / (1024**2):.2f} MB')
        logger.info(f'[Celery] 總 Artifacts 數: {results["total_artifacts"]} 個')
        logger.info(f'[Celery] 總耗時: {duration:.1f} 秒')
        logger.info('=' * 80)
        logger.info('[Celery] ✅ 自動存儲 Artifacts 完成')
        logger.info('=' * 80)
        
        return {
            'success': True,
            'total_found': total_found,
            'processed': results['processed'],
            'stored': results['stored'],
            'no_artifacts': results['no_artifacts'],
            'failed': results['failed'],
            'total_size': results['total_size'],
            'total_artifacts': results['total_artifacts'],
            'duration': duration,
            'details': results['details']
        }
        
    except Exception as exc:
        duration = time.time() - start_time
        logger.error(
            f'[Celery] ❌ 自動存儲 Artifacts 失敗（執行 {duration:.1f} 秒）',
            exc_info=True
        )
        
        # 自動重試（最多 2 次）
        try:
            raise self.retry(exc=exc, countdown=600)
        except self.MaxRetriesExceededError:
            logger.error('[Celery] ❌ 自動存儲 Artifacts 重試次數已達上限')
            return {
                'success': False,
                'total_found': 0,
                'processed': 0,
                'stored': 0,
                'no_artifacts': 0,
                'failed': 0,
                'total_size': 0,
                'total_artifacts': 0,
                'duration': duration,
                'error_message': str(exc)
            }


# ==================== Ansible Inventory 快取清理任務 ====================

@shared_task(name='清理過期的 Ansible Inventory 快取')
def clean_expired_ansible_caches():
    """
    清理過期的 Ansible Inventory 快取
    
    每天執行一次，清理 7 天前的快取。
    
    清理邏輯：
    1. 遍歷所有 {server_ip}/{job_name}/{build_number}/cache/ 目錄
    2. 讀取 cache_metadata.json
    3. 檢查 cache_expires_at 是否過期
    4. 刪除過期的快取目錄
    5. 記錄統計信息
    
    Returns:
        dict: {
            "success": bool,
            "cleaned_count": int,
            "total_size_mb": float,
            "errors": list
        }
    """
    from django.conf import settings
    from pathlib import Path
    from datetime import datetime
    import json
    import shutil
    
    logger.info('[Celery] 🔍 開始清理過期的 Ansible Inventory 快取')
    start_time = datetime.now()
    
    base_path = Path(settings.JENKINS_STORAGE_BASE_PATH)
    now = datetime.now()
    cleaned_count = 0
    total_size_mb = 0
    errors = []
    
    try:
        # 遍歷所有 cache 目錄
        cache_dirs = list(base_path.rglob('cache'))
        logger.info(f'[Celery] 找到 {len(cache_dirs)} 個 cache 目錄')
        
        for cache_dir in cache_dirs:
            if not cache_dir.is_dir():
                continue
            
            # 讀取快取元數據
            metadata_file = cache_dir / 'cache_metadata.json'
            if not metadata_file.exists():
                logger.debug(f'[Celery] 跳過（無元數據）: {cache_dir}')
                continue
            
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                # 檢查是否過期
                expires_at_str = metadata.get('cache_expires_at')
                if not expires_at_str:
                    logger.warning(f'[Celery] 元數據缺少 cache_expires_at: {cache_dir}')
                    continue
                
                expires_at = datetime.fromisoformat(expires_at_str)
                
                if now > expires_at:
                    # 計算快取大小
                    cache_size = sum(
                        f.stat().st_size for f in cache_dir.iterdir() if f.is_file()
                    )
                    cache_size_mb = cache_size / 1024 / 1024
                    
                    # 記錄快取信息（用於日誌）
                    build_path = cache_dir.parent
                    relative_path = build_path.relative_to(base_path)
                    
                    # 刪除快取目錄
                    shutil.rmtree(cache_dir)
                    cleaned_count += 1
                    total_size_mb += cache_size_mb
                    
                    logger.info(
                        f'[Celery] ✅ 已清理過期快取: {relative_path} '
                        f'({cache_size_mb:.2f} MB)'
                    )
                else:
                    # 未過期，跳過
                    logger.debug(f'[Celery] 快取有效: {cache_dir}')
                    
            except json.JSONDecodeError as e:
                error_msg = f'JSON 解析失敗 {cache_dir}: {e}'
                logger.warning(f'[Celery] {error_msg}')
                errors.append(error_msg)
                continue
            except Exception as e:
                error_msg = f'處理快取目錄失敗 {cache_dir}: {e}'
                logger.warning(f'[Celery] {error_msg}')
                errors.append(error_msg)
                continue
        
        # 計算執行時間
        duration = (datetime.now() - start_time).total_seconds()
        
        logger.info(
            f'[Celery] ✅ 快取清理完成：'
            f'清理 {cleaned_count} 個目錄，'
            f'釋放 {total_size_mb:.2f} MB，'
            f'耗時 {duration:.2f} 秒'
        )
        
        return {
            'success': True,
            'cleaned_count': cleaned_count,
            'total_size_mb': round(total_size_mb, 2),
            'duration': round(duration, 2),
            'errors': errors
        }
        
    except Exception as e:
        logger.error(f'[Celery] 清理快取失敗: {e}', exc_info=True)
        return {
            'success': False,
            'cleaned_count': cleaned_count,
            'total_size_mb': round(total_size_mb, 2),
            'error': str(e),
            'errors': errors
        }


@shared_task(
    bind=True,
    name='api.tasks.check_ntp_sync_task',
    max_retries=2,
    default_retry_delay=60,  # 失敗後 1 分鐘重試
    time_limit=60,  # 硬限制 1 分鐘
    soft_time_limit=45  # 軟限制 45 秒
)
def check_ntp_sync_task(self):
    """
    NTP 時間同步檢測定時任務（每5分鐘執行一次）
    
    Returns:
        dict: {
            'success': bool,
            'status': str,           # 'success' or 'failed'
            'ntp_server': str,
            'response_time': float,  # 響應時間（ms）
            'offset': float,         # 時間偏移（ms）
            'stratum': int,          # Stratum 層級
            'jitter': float,         # 時間抖動（ms）
            'timestamp': str
        }
    """
    try:
        logger.info('[Celery] 開始執行 NTP 時間同步檢測')
        
        # 使用 NTP 服務執行檢測
        from .ntp_service import check_ntp_sync
        from .models import NTPSyncLog
        
        ntp_server = '10.10.10.51'
        result = check_ntp_sync(ntp_server)
        
        # 記錄到資料庫
        log_entry = NTPSyncLog.objects.create(
            timestamp=timezone.now(),
            status=result['status'],
            ntp_server=result['ntp_server'],
            response_time=result.get('response_time'),
            offset=result.get('offset'),
            stratum=result.get('stratum'),
            jitter=result.get('jitter'),
            error_message=result.get('error_message', '')
        )
        
        result_log = {
            'success': result['status'] == 'success',
            'status': result['status'],
            'ntp_server': result['ntp_server'],
            'response_time': result.get('response_time'),
            'offset': result.get('offset'),
            'stratum': result.get('stratum'),
            'jitter': result.get('jitter'),
            'timestamp': log_entry.timestamp.isoformat(),
        }
        
        if result['status'] == 'success':
            logger.info(
                f'[Celery] NTP 時間同步檢測完成 - '
                f'Server: {ntp_server} | '
                f'響應時間: {result["response_time"]:.2f} ms | '
                f'時間偏移: {result["offset"]:.3f} ms | '
                f'Stratum: {result["stratum"]}'
            )
        else:
            logger.warning(
                f'[Celery] NTP 時間同步失敗 - '
                f'Server: {ntp_server} | '
                f'錯誤: {result.get("error_message", "未知錯誤")}'
            )
        
        return result_log
        
    except Exception as exc:
        logger.error('[Celery] NTP 時間同步檢測異常', exc_info=True)
        
        # 自動重試（最多 2 次）
        try:
            raise self.retry(exc=exc, countdown=60)
        except self.MaxRetriesExceededError:
            logger.error('[Celery] NTP 時間同步檢測重試次數已達上限')
            return {
                'success': False,
                'error_message': str(exc),
                'timestamp': timezone.now().isoformat()
            }


@shared_task(
    bind=True,
    name='api.tasks.sync_ntp_time_task',
    max_retries=2,
    default_retry_delay=300,  # 失敗後 5 分鐘重試
    time_limit=120,  # 硬限制 2 分鐘
    soft_time_limit=90  # 軟限制 1.5 分鐘
)
def sync_ntp_time_task(self):
    """
    NTP 時間自動同步定時任務（每天執行一次）
    
    功能：
    1. 檢查是否需要同步（時間偏移 > 200ms）
    2. 檢查是否允許同步（距離上次同步 >= 30 分鐘）
    3. 執行系統時間同步（使用 ntpdate）
    4. 記錄同步操作到資料庫
    
    Returns:
        dict: {
            'success': bool,
            'sync_executed': bool,      # 是否執行了同步
            'offset_before': float,     # 同步前偏移（ms）
            'offset_after': float,      # 同步後偏移（ms）
            'improvement': float,       # 改善量（ms）
            'duration': float,          # 執行時間（秒）
            'reason': str,              # 決策原因
            'timestamp': str
        }
    """
    try:
        logger.info('[Celery] 開始執行 NTP 時間自動同步檢查')
        
        from .ntp_service import NTPSyncService
        from .models import NTPSyncOperation
        
        # 創建 NTP 同步服務
        ntp_server = '10.10.10.51'
        sync_service = NTPSyncService(ntp_server=ntp_server)
        
        result = {
            'success': False,
            'sync_executed': False,
            'offset_before': None,
            'offset_after': None,
            'improvement': None,
            'duration': None,
            'reason': '',
            'timestamp': timezone.now().isoformat()
        }
        
        # Step 1: 檢查是否允許同步（避免頻繁同步）
        can_sync, can_sync_reason = sync_service.can_sync_now()
        
        if not can_sync:
            result['reason'] = can_sync_reason
            result['success'] = True  # 檢查成功，但不執行同步
            logger.info(f'[Celery] NTP 同步檢查完成 - {can_sync_reason}')
            return result
        
        # Step 2: 檢查是否需要同步（時間偏移是否過大）
        should_sync, should_sync_reason, avg_offset = sync_service.should_sync(threshold_ms=200.0)
        
        if not should_sync:
            result['reason'] = should_sync_reason
            result['success'] = True  # 檢查成功，但不需要同步
            result['offset_before'] = avg_offset
            logger.info(f'[Celery] NTP 同步檢查完成 - {should_sync_reason}')
            return result
        
        # Step 3: 創建同步操作記錄（pending 狀態）
        logger.info(f'[Celery] 開始執行時間同步 - {should_sync_reason}')
        
        operation = NTPSyncOperation.objects.create(
            timestamp=timezone.now(),
            ntp_server=ntp_server,
            sync_method='ntpdate',
            triggered_by='auto',
            status='pending',
            offset_before=avg_offset,
            reason=should_sync_reason
        )
        
        # Step 4: 執行實際的時間同步
        sync_result = sync_service.sync_system_time(
            method='ntpdate',
            triggered_by='auto'
        )
        
        # Step 5: 更新操作記錄
        if sync_result['success']:
            operation.status = 'success'
            operation.offset_before = sync_result.get('offset_before')
            operation.offset_after = sync_result.get('offset_after')
            operation.improvement = sync_result.get('improvement')
            operation.duration = sync_result.get('duration')
            operation.command_output = sync_result.get('command_output', '')
            operation.save()
            
            result.update({
                'success': True,
                'sync_executed': True,
                'offset_before': sync_result.get('offset_before'),
                'offset_after': sync_result.get('offset_after'),
                'improvement': sync_result.get('improvement'),
                'duration': sync_result.get('duration'),
                'reason': f'同步成功 - {should_sync_reason}'
            })
            
            logger.info(
                f'[Celery] ✅ NTP 時間同步成功 - '
                f'改善量: {sync_result.get("improvement", 0):.3f}ms, '
                f'耗時: {sync_result.get("duration", 0):.2f}秒'
            )
        else:
            operation.status = 'failed'
            operation.error_message = sync_result.get('error_message', '')
            operation.duration = sync_result.get('duration')
            operation.command_output = sync_result.get('command_output', '')
            operation.save()
            
            result.update({
                'success': False,
                'sync_executed': True,
                'reason': f'同步失敗 - {sync_result.get("error_message", "未知錯誤")}'
            })
            
            logger.error(f'[Celery] ❌ NTP 時間同步失敗 - {sync_result.get("error_message")}')
        
        return result
        
    except Exception as exc:
        logger.error('[Celery] NTP 時間自動同步異常', exc_info=True)
        
        # 自動重試（最多 2 次）
        try:
            raise self.retry(exc=exc, countdown=300)
        except self.MaxRetriesExceededError:
            logger.error('[Celery] NTP 時間自動同步重試次數已達上限')
            return {
                'success': False,
                'sync_executed': False,
                'error_message': str(exc),
                'timestamp': timezone.now().isoformat()
            }


# ==================== Jenkins Jobs 自動同步任務 ====================

@shared_task(
    bind=True,
    name='api.tasks.sync_all_jenkins_jobs_task',
    max_retries=2,
    default_retry_delay=300,  # 失敗後 5 分鐘重試
    time_limit=1800,  # 硬限制 30 分鐘
    soft_time_limit=1650  # 軟限制 27.5 分鐘
)
def sync_all_jenkins_jobs_task(self, server_id=None):
    """
    自動同步所有在線 Jenkins Server 的 Jobs
    
    定期執行此任務可以：
    1. 自動發現新建立的 Jenkins Jobs
    2. 更新現有 Jobs 的狀態（is_buildable, is_disabled）
    3. 更新 View 分類資訊
    4. 更新最後同步時間
    
    Args:
        server_id: Jenkins Server ID（可選，None 表示所有在線 Server）
        
    Returns:
        dict: {
            'success': bool,
            'total_servers': int,        # 處理的伺服器數量
            'total_jobs_created': int,   # 新增的 Jobs 總數
            'total_jobs_updated': int,   # 更新的 Jobs 總數
            'total_jobs_found': int,     # 從 Jenkins 找到的 Jobs 總數
            'servers_details': List[dict],  # 每個伺服器的詳細結果
            'errors': int,               # 錯誤數量
            'duration': float,           # 執行時間（秒）
        }
    """
    from .models import JenkinsServer, JenkinsJob
    from library.services.jenkins_client import JenkinsClient
    
    start_time = time.time()
    
    try:
        logger.info('[Celery] 🔄 開始自動同步 Jenkins Jobs')
        logger.info(f'[Celery]   - Server ID: {server_id if server_id else "All Online"}')
        
        # 獲取要處理的 Server（只處理在線的）
        if server_id:
            servers = JenkinsServer.objects.filter(id=server_id, status='online')
        else:
            servers = JenkinsServer.objects.filter(status='online')
        
        if not servers.exists():
            logger.warning('[Celery] ⚠️  沒有找到在線的 Jenkins Server')
            return {
                'success': False,
                'total_servers': 0,
                'total_jobs_created': 0,
                'total_jobs_updated': 0,
                'total_jobs_found': 0,
                'servers_details': [],
                'errors': 0,
                'duration': 0,
                'error_message': 'No online servers found'
            }
        
        total_servers = servers.count()
        total_jobs_created = 0
        total_jobs_updated = 0
        total_jobs_found = 0
        servers_details = []
        total_errors = 0
        
        logger.info(f'[Celery] 📡 找到 {total_servers} 個在線的 Jenkins Server')
        
        # 遍歷每個 Server
        for server in servers:
            server_start = time.time()
            logger.info(f'[Celery] 🖥️  處理 Server: {server.name} ({server.url})')
            
            client = None
            try:
                # 創建 Jenkins 客戶端
                client = JenkinsClient(
                    base_url=server.url,
                    username=server.username,
                    api_token=server.api_token
                )
                
                # 1. 獲取所有 Views
                views = client.list_views()
                logger.info(f'[Celery]   - 找到 {len(views)} 個 Views')
                
                # 2. 建立 Job 到 View 的映射
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
                            # 如果 Job 還沒有被分配到 View，則記錄
                            if job_name not in job_view_map:
                                job_view_map[job_name] = view_name
                    except Exception as e:
                        logger.warning(f'[Celery]   - 無法獲取 View "{view_name}" 的 Jobs: {e}')
                
                # 3. 獲取所有 Job 列表
                jobs = client.list_jobs()
                logger.info(f'[Celery]   - 找到 {len(jobs)} 個 Jobs')
                
                created_count = 0
                updated_count = 0
                
                # 4. 遍歷每個 Job 並創建/更新
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
                
                # 5. 更新伺服器同步時間
                server.last_sync_at = timezone.now()
                server.save()
                
                server_duration = time.time() - server_start
                
                logger.info(
                    f'[Celery] ✅ Server "{server.name}" 同步完成: '
                    f'新增 {created_count}, 更新 {updated_count}, '
                    f'共 {len(jobs)} 個 Jobs, 耗時 {server_duration:.2f} 秒'
                )
                
                # 記錄每個 Server 的結果
                servers_details.append({
                    'server_id': server.id,
                    'server_name': server.name,
                    'server_url': server.url,
                    'jobs_found': len(jobs),
                    'jobs_created': created_count,
                    'jobs_updated': updated_count,
                    'views_count': len(views) - 1,  # 扣除 "all" view
                    'duration': server_duration,
                    'success': True
                })
                
                total_jobs_found += len(jobs)
                total_jobs_created += created_count
                total_jobs_updated += updated_count
                
            except Exception as e:
                logger.error(
                    f'[Celery] ❌ Server "{server.name}" 同步失敗: {e}',
                    exc_info=True
                )
                
                total_errors += 1
                
                servers_details.append({
                    'server_id': server.id,
                    'server_name': server.name,
                    'server_url': server.url,
                    'jobs_found': 0,
                    'jobs_created': 0,
                    'jobs_updated': 0,
                    'views_count': 0,
                    'duration': time.time() - server_start,
                    'success': False,
                    'error_message': str(e)
                })
                
            finally:
                if client:
                    client.close()
        
        # 計算總執行時間
        duration = time.time() - start_time
        
        logger.info('[Celery] 🎉 Jenkins Jobs 自動同步完成')
        logger.info(f'[Celery]   - 處理伺服器: {total_servers} 個')
        logger.info(f'[Celery]   - 找到 Jobs: {total_jobs_found} 個')
        logger.info(f'[Celery]   - 新增 Jobs: {total_jobs_created} 個')
        logger.info(f'[Celery]   - 更新 Jobs: {total_jobs_updated} 個')
        logger.info(f'[Celery]   - 錯誤數量: {total_errors} 個')
        logger.info(f'[Celery]   - 總耗時: {duration:.2f} 秒')
        
        return {
            'success': total_errors == 0,
            'total_servers': total_servers,
            'total_jobs_created': total_jobs_created,
            'total_jobs_updated': total_jobs_updated,
            'total_jobs_found': total_jobs_found,
            'servers_details': servers_details,
            'errors': total_errors,
            'duration': duration,
        }
        
    except Exception as exc:
        logger.error('[Celery] 💥 Jenkins Jobs 自動同步異常', exc_info=True)
        
        # 自動重試（最多 2 次）
        try:
            raise self.retry(exc=exc, countdown=300)
        except self.MaxRetriesExceededError:
            logger.error('[Celery] Jenkins Jobs 自動同步重試次數已達上限')
            duration = time.time() - start_time
            return {
                'success': False,
                'total_servers': 0,
                'total_jobs_created': 0,
                'total_jobs_updated': 0,
                'total_jobs_found': 0,
                'servers_details': [],
                'errors': 1,
                'duration': duration,
                'error_message': str(exc)
            }


# ============================================================
# Phase 2: Jenkins 資料驗證與清理任務
# ============================================================

def get_folder_size(folder_path):
    """
    計算資料夾大小（遞迴）
    
    Args:
        folder_path (str): 資料夾路徑
        
    Returns:
        int: 資料夾大小（bytes）
    """
    import os
    
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(folder_path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    try:
                        total_size += os.path.getsize(filepath)
                    except OSError:
                        # 跳過無法訪問的檔案
                        pass
    except Exception as e:
        logger.error(f"計算資料夾大小失敗 {folder_path}: {e}")
    
    return total_size


def cleanup_nas_workspace(build, dry_run=False):
    """
    清理 Build 對應的 NAS Workspace 資料夾
    
    Args:
        build: JenkinsBuild 實例
        dry_run (bool): 試運行模式（只檢查不刪除）
        
    Returns:
        dict: {
            'success': bool,
            'folder_path': str,
            'size_freed': int,  # Bytes
            'message': str,
            'error': str (if failed)
        }
    """
    import os
    import shutil
    
    # 檢查是否有存儲的 Workspace
    if not build.is_workspace_stored or not build.workspace_path:
        return {
            'success': True,
            'size_freed': 0,
            'message': 'No workspace stored'
        }
    
    folder_path = build.workspace_path
    
    try:
        # 檢查路徑是否存在
        if not os.path.exists(folder_path):
            logger.warning(f"[NAS Cleanup] Workspace path not found: {folder_path}")
            return {
                'success': True,
                'folder_path': folder_path,
                'size_freed': 0,
                'message': 'Path not found (already deleted or never existed)'
            }
        
        # 計算資料夾大小
        size_freed = get_folder_size(folder_path)
        
        # 試運行模式
        if dry_run:
            logger.info(
                f"[NAS Cleanup] [DRY-RUN] Would delete: {folder_path} "
                f"({size_freed / 1024 / 1024:.2f} MB)"
            )
            return {
                'success': True,
                'folder_path': folder_path,
                'size_freed': size_freed,
                'message': 'Dry-run: would be deleted'
            }
        
        # 實際刪除資料夾
        shutil.rmtree(folder_path)
        
        logger.info(
            f"[NAS Cleanup] ✅ Deleted workspace: {folder_path} "
            f"({size_freed / 1024 / 1024:.2f} MB freed)"
        )
        
        return {
            'success': True,
            'folder_path': folder_path,
            'size_freed': size_freed,
            'message': 'Successfully deleted'
        }
        
    except PermissionError as e:
        error_msg = f"Permission denied: {e}"
        logger.error(f"[NAS Cleanup] ❌ {error_msg} - {folder_path}")
        return {
            'success': False,
            'folder_path': folder_path,
            'size_freed': 0,
            'error': error_msg
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[NAS Cleanup] ❌ Failed to delete {folder_path}: {e}", exc_info=True)
        return {
            'success': False,
            'folder_path': folder_path,
            'size_freed': 0,
            'error': error_msg
        }


@shared_task(
    bind=True,
    name='api.tasks.validate_jenkins_data',
    max_retries=2,
    default_retry_delay=300,  # 5 分鐘後重試
    time_limit=1800,  # 硬限制 30 分鐘
    soft_time_limit=1650  # 軟限制 27.5 分鐘
)
def validate_jenkins_data(self, server_id=None, auto_cleanup=False, cleanup_nas=True, keep_recent_days=None, max_orphaned_threshold=None, dry_run=False):
    """
    驗證 Jenkins 資料一致性並可選擇自動清理孤立資料
    
    定期執行此任務可以：
    1. 檢查資料庫中的 Jobs 是否仍存在於 Jenkins
    2. 檢查資料庫中的 Builds 是否仍存在於 Jenkins
    3. 記錄異常情況到日誌
    4. 可選：自動清理孤立資料（需謹慎使用）
    5. 可選：清理 NAS 上對應的 Workspace 資料夾
    
    Args:
        server_id (int, optional): Jenkins Server ID，不指定則檢查所有活躍伺服器
        auto_cleanup (bool): 是否自動清理孤立資料（預設 False，只檢測不刪除）
        cleanup_nas (bool): 是否清理 NAS Workspace 資料夾（預設 True，當 auto_cleanup=True 時生效）
        keep_recent_days (int, optional): 保留最近 N 天的資料（None 則使用 settings 配置，預設 7 天）
        max_orphaned_threshold (int, optional): 自動清理的閾值（None 則使用 settings 配置，預設 100）
        dry_run (bool): 試運行模式（只檢查不刪除，預設 False）
    
    Returns:
        dict: 驗證結果統計
    """
    from .models import JenkinsServer, JenkinsJob, JenkinsBuild
    from library.services.jenkins_client import JenkinsClient
    from django.db import transaction
    from django.utils import timezone
    from django.conf import settings
    import re
    
    # 從 settings 讀取配置（如果未提供參數）
    cleanup_config = getattr(settings, 'JENKINS_CLEANUP_CONFIG', {})
    if keep_recent_days is None:
        keep_recent_days = cleanup_config.get('keep_recent_days', 7)
    if max_orphaned_threshold is None:
        max_orphaned_threshold = cleanup_config.get('auto_cleanup_threshold', 100)
    
    exclude_patterns = cleanup_config.get('exclude_patterns', [])
    batch_delete_size = cleanup_config.get('batch_delete_size', 100)
    validation_job_limit = cleanup_config.get('validation_job_limit', 50)
    validation_build_limit = cleanup_config.get('validation_build_limit', 100)
    
    start_time = time.time()
    logger.info('[Celery] 🔍 開始驗證 Jenkins 資料一致性')
    logger.info(f'[Celery] 📝 配置：keep_recent_days={keep_recent_days}, threshold={max_orphaned_threshold}')
    
    if auto_cleanup:
        logger.warning('[Celery] ⚠️  自動清理模式已啟用')
        if cleanup_nas:
            logger.info('[Celery] 🗑️  NAS Workspace 清理已啟用')
        else:
            logger.info('[Celery] ℹ️  NAS Workspace 清理已停用（只刪除資料庫記錄）')
    
    if dry_run:
        logger.info('[Celery] 🔍 試運行模式：只檢查不刪除')
    
    stats = {
        'success': True,
        'total_jobs_checked': 0,
        'total_builds_checked': 0,
        'orphaned_jobs_found': 0,
        'orphaned_builds_found': 0,
        'cleaned_jobs': 0,
        'cleaned_builds': 0,
        'nas_folders_deleted': 0,      # 新增：NAS 資料夾刪除數量
        'nas_space_freed': 0,          # 新增：NAS 釋放空間（bytes）
        'nas_errors': 0,               # 新增：NAS 清理錯誤數量
        'servers_checked': 0,
        'skipped_recent': 0,
        'errors': 0,
        'servers_details': []
    }
    
    # 計算保留時間閾值
    cutoff_time = timezone.now() - timedelta(days=keep_recent_days)
    
    try:
        # 獲取要檢查的伺服器
        if server_id:
            servers = JenkinsServer.objects.filter(id=server_id, is_active=True)
        else:
            servers = JenkinsServer.objects.filter(is_active=True, status='online')
        
        total_servers = servers.count()
        logger.info(f'[Celery] 📡 將檢查 {total_servers} 個 Jenkins Server')
        
        if total_servers == 0:
            logger.warning('[Celery] ⚠️  沒有活躍的 Jenkins Server')
            return stats
        
        for server in servers:
            server_start = time.time()
            logger.info(f'[Celery] 🖥️  檢查 Server: {server.name} ({server.url})')
            
            server_stats = {
                'server_id': server.id,
                'server_name': server.name,
                'server_url': server.url,
                'jobs_checked': 0,
                'builds_checked': 0,
                'orphaned_jobs': 0,
                'orphaned_builds': 0,
                'cleaned_jobs': 0,
                'cleaned_builds': 0,
                'nas_folders_deleted': 0,  # 新增
                'nas_space_freed': 0,      # 新增
                'nas_errors': 0,           # 新增
                'success': True,
                'duration': 0
            }
            
            client = None
            
            try:
                # 連接 Jenkins
                client = JenkinsClient(
                    base_url=server.url,
                    username=server.username,
                    api_token=server.api_token
                )
                
                # ===== 檢查 Jobs =====
                logger.info(f'[Celery]   📋 檢查 Jobs...')
                
                # 獲取 Jenkins 上所有 Job 名稱
                jenkins_jobs = client.list_jobs()
                jenkins_job_names = {job['name'] for job in jenkins_jobs}
                logger.info(f'[Celery]     Jenkins 上有 {len(jenkins_job_names)} 個 Jobs')
                
                # 獲取資料庫中此 Server 的所有 Jobs
                db_jobs = JenkinsJob.objects.filter(server=server)
                server_stats['jobs_checked'] = db_jobs.count()
                stats['total_jobs_checked'] += db_jobs.count()
                logger.info(f'[Celery]     資料庫中有 {db_jobs.count()} 個 Jobs')
                
                # 比對找出孤立的 Jobs
                orphaned_jobs = []
                for job in db_jobs:
                    if job.name not in jenkins_job_names:
                        # 檢查是否為最近的資料（保護機制）
                        if job.last_sync_at and job.last_sync_at > cutoff_time:
                            stats['skipped_recent'] += 1
                            logger.debug(f'[Celery]     ℹ️  跳過最近同步的 Job: {job.name}')
                            continue
                        
                        # 檢查是否符合排除模式（保護機制）
                        is_excluded = False
                        for pattern in exclude_patterns:
                            if re.match(pattern, job.name):
                                is_excluded = True
                                stats['skipped_recent'] += 1
                                logger.debug(f'[Celery]     🛡️  跳過受保護的 Job: {job.name} (符合模式: {pattern})')
                                break
                        
                        if is_excluded:
                            continue
                        
                        orphaned_jobs.append(job)
                        build_count = job.builds.count()
                        server_stats['orphaned_jobs'] += 1
                        stats['orphaned_jobs_found'] += 1
                        
                        logger.warning(
                            f'[Celery]     ❌ 孤立 Job: {job.name} '
                            f'(含 {build_count} 個 Builds, 最後同步: {job.last_sync_at})'
                        )
                
                # 自動清理 Jobs（如果啟用且符合條件）
                if auto_cleanup and orphaned_jobs:
                    orphaned_count = len(orphaned_jobs)
                    
                    # 安全檢查：孤立資料過多時不自動清理
                    if orphaned_count > max_orphaned_threshold:
                        logger.error(
                            f'[Celery]     ⚠️  孤立 Jobs 數量 ({orphaned_count}) 超過閾值 ({max_orphaned_threshold})，'
                            f'跳過自動清理以確保安全'
                        )
                    else:
                        logger.info(f'[Celery]     🗑️  準備清理 {orphaned_count} 個孤立 Jobs...')
                        
                        with transaction.atomic():
                            for job in orphaned_jobs:
                                build_count = job.builds.count()
                                job_name = job.name
                                job.delete()  # 級聯刪除相關 Builds
                                
                                server_stats['cleaned_jobs'] += 1
                                server_stats['cleaned_builds'] += build_count
                                stats['cleaned_jobs'] += 1
                                stats['cleaned_builds'] += build_count
                                
                                logger.info(f'[Celery]       ✅ 已刪除孤立 Job: {job_name} (含 {build_count} builds)')
                        
                        logger.info(f'[Celery]     ✅ 清理完成: {orphaned_count} 個 Jobs')
                
                # ===== 檢查 Builds =====
                logger.info(f'[Celery]   🔨 檢查 Builds（這可能需要較長時間）...')
                
                # 獲取非孤立的 Jobs
                valid_jobs = db_jobs.exclude(id__in=[j.id for j in orphaned_jobs])
                
                builds_checked_count = 0
                orphaned_builds = []
                
                # 使用配置的 validation_job_limit 限制檢查的 Job 數量
                for job in valid_jobs[:validation_job_limit]:
                    try:
                        # 從 Jenkins 獲取 Builds，使用配置的 validation_build_limit
                        builds_list = client.get_job_builds(job.name, limit=validation_build_limit)
                        jenkins_build_numbers = {build['number'] for build in builds_list}
                        
                        # 獲取資料庫中的 Builds
                        db_builds = JenkinsBuild.objects.filter(job=job)
                        builds_checked_count += db_builds.count()
                        
                        # 比對找出孤立的 Builds
                        for build in db_builds:
                            if build.build_number not in jenkins_build_numbers:
                                # 檢查是否為最近的資料（保護機制）
                                if build.build_timestamp and build.build_timestamp > cutoff_time:
                                    stats['skipped_recent'] += 1
                                    continue
                                
                                orphaned_builds.append(build)
                                server_stats['orphaned_builds'] += 1
                                stats['orphaned_builds_found'] += 1
                    
                    except Exception as e:
                        logger.error(f'[Celery]     ❌ 檢查 Job "{job.name}" 的 Builds 失敗: {e}')
                
                server_stats['builds_checked'] = builds_checked_count
                stats['total_builds_checked'] += builds_checked_count
                
                if orphaned_builds:
                    logger.warning(f'[Celery]     ⚠️  找到 {len(orphaned_builds)} 個孤立 Builds')
                    
                    # 自動清理 Builds（如果啟用且符合條件）
                    if auto_cleanup or dry_run:
                        orphaned_count = len(orphaned_builds)
                        
                        if orphaned_count > max_orphaned_threshold and not dry_run:
                            logger.error(
                                f'[Celery]     ⚠️  孤立 Builds 數量 ({orphaned_count}) 超過閾值 ({max_orphaned_threshold})，'
                                f'跳過自動清理'
                            )
                        else:
                            action_text = '檢查' if dry_run else '清理'
                            logger.info(f'[Celery]     🗑️  準備{action_text} {orphaned_count} 個孤立 Builds...')
                            
                            # 先清理 NAS Workspace（如果啟用）
                            if cleanup_nas:
                                logger.info(f'[Celery]     📁 清理 NAS Workspace 資料夾...')
                                
                                for build in orphaned_builds:
                                    # 清理 NAS
                                    nas_result = cleanup_nas_workspace(build, dry_run=dry_run)
                                    
                                    if nas_result['success']:
                                        if nas_result.get('size_freed', 0) > 0:
                                            server_stats['nas_folders_deleted'] += 1
                                            server_stats['nas_space_freed'] += nas_result['size_freed']
                                            stats['nas_folders_deleted'] += 1
                                            stats['nas_space_freed'] += nas_result['size_freed']
                                    else:
                                        server_stats['nas_errors'] += 1
                                        stats['nas_errors'] += 1
                                        logger.error(
                                            f'[Celery]       ❌ NAS 清理失敗: {build.job.name} #{build.build_number}: '
                                            f'{nas_result.get("error", "Unknown error")}'
                                        )
                                
                                if not dry_run:
                                    freed_gb = server_stats['nas_space_freed'] / 1024 / 1024 / 1024
                                    logger.info(
                                        f'[Celery]     ✅ NAS 清理完成: {server_stats["nas_folders_deleted"]} 資料夾, '
                                        f'{freed_gb:.3f} GB 釋放'
                                    )
                            
                            # 再刪除資料庫記錄（使用配置的批次大小分批刪除）
                            if not dry_run:
                                for i in range(0, orphaned_count, batch_delete_size):
                                    batch = orphaned_builds[i:i+batch_delete_size]
                                    with transaction.atomic():
                                        build_ids = [b.id for b in batch]
                                        deleted_count = JenkinsBuild.objects.filter(id__in=build_ids).delete()[0]
                                        server_stats['cleaned_builds'] += deleted_count
                                
                                logger.info(f'[Celery]     ✅ 資料庫清理完成: {orphaned_count} 個 Builds')
                            else:
                                logger.info(f'[Celery]     🔍 [DRY-RUN] 將刪除 {orphaned_count} 個 Builds')
                else:
                    logger.info(f'[Celery]     ✅ 無孤立 Builds')
                
            except Exception as e:
                logger.error(f'[Celery]   ❌ 檢查 Server "{server.name}" 失敗: {e}', exc_info=True)
                server_stats['success'] = False
                server_stats['error_message'] = str(e)
                stats['errors'] += 1
                stats['success'] = False
            
            finally:
                if client:
                    client.close()
                
                server_stats['duration'] = time.time() - server_start
                stats['servers_details'].append(server_stats)
                stats['servers_checked'] += 1
                
                logger.info(
                    f'[Celery]   Server "{server.name}" 檢查完成 '
                    f'(耗時: {server_stats["duration"]:.2f}s)'
                )
        
        # 計算總執行時間
        duration = time.time() - start_time
        stats['duration'] = duration
        
        # 輸出總結
        logger.info('[Celery] 🎉 Jenkins 資料驗證完成')
        logger.info(f'[Celery]   - 檢查伺服器: {stats["servers_checked"]} 個')
        logger.info(f'[Celery]   - 檢查 Jobs: {stats["total_jobs_checked"]} 個')
        logger.info(f'[Celery]   - 檢查 Builds: {stats["total_builds_checked"]} 個')
        logger.info(f'[Celery]   - 孤立 Jobs: {stats["orphaned_jobs_found"]} 個')
        logger.info(f'[Celery]   - 孤立 Builds: {stats["orphaned_builds_found"]} 個')
        
        if auto_cleanup and not dry_run:
            logger.info(f'[Celery]   - 已清理 Jobs: {stats["cleaned_jobs"]} 個')
            logger.info(f'[Celery]   - 已清理 Builds: {stats["cleaned_builds"]} 個')
            
            if cleanup_nas:
                freed_gb = stats['nas_space_freed'] / 1024 / 1024 / 1024
                logger.info(f'[Celery]   - NAS 資料夾已刪除: {stats["nas_folders_deleted"]} 個')
                logger.info(f'[Celery]   - NAS 空間釋放: {freed_gb:.3f} GB')
                
                if stats['nas_errors'] > 0:
                    logger.warning(f'[Celery]   - NAS 清理錯誤: {stats["nas_errors"]} 個')
        
        if dry_run:
            logger.info('[Celery]   - 模式: 試運行（未執行實際刪除）')
        
        if stats['skipped_recent'] > 0:
            logger.info(f'[Celery]   - 跳過最近資料: {stats["skipped_recent"]} 筆')
        
        logger.info(f'[Celery]   - 錯誤數量: {stats["errors"]} 個')
        logger.info(f'[Celery]   - 總耗時: {duration:.2f} 秒')
        
        return stats
        
    except Exception as exc:
        logger.error('[Celery] 💥 Jenkins 資料驗證異常', exc_info=True)
        
        # 自動重試（最多 2 次）
        try:
            raise self.retry(exc=exc, countdown=300)
        except self.MaxRetriesExceededError:
            logger.error('[Celery] Jenkins 資料驗證重試次數已達上限')
            duration = time.time() - start_time
            stats['success'] = False
            stats['duration'] = duration
            stats['error_message'] = str(exc)
            return stats


# ============================================================================
# 任務：按日期清理舊 Jenkins Builds
# ============================================================================

@shared_task(
    bind=True,
    name='api.tasks.cleanup_old_jenkins_builds_task',
    max_retries=2,
    default_retry_delay=1800,
    time_limit=7200,
    soft_time_limit=6600
)
def cleanup_old_jenkins_builds_task(
    self,
    days=90,
    only_stored=True,
    exclude_patterns=None,
    dry_run=False,
    server_id=None
):
    """
    清理過舊的 Jenkins Builds（按日期）
    
    此任務主動清理超過指定天數的 Builds，而不是等待 Jenkins 刪除後才清理。
    可用於長期維護 NAS 空間和資料庫效能。
    
    Args:
        days (int): 只保留最近 N 天的 Builds（預設 90 天）
        only_stored (bool): 只清理已存儲到 NAS 的 Builds（預設 True）
        exclude_patterns (list): 排除的 Job 名稱 regex 模式列表
        dry_run (bool): 試運行模式，只檢查不實際刪除（預設 False）
        server_id (int): 只處理特定 Jenkins Server（None 表示處理所有）
    
    Returns:
        dict: 執行結果統計
            {
                'success': bool,
                'total_checked': int,
                'total_old_builds': int,
                'deleted_builds': int,
                'nas_folders_deleted': int,
                'nas_space_freed': int,  # bytes
                'skipped': int,
                'errors': int,
                'duration': float
            }
    
    Examples:
        # Dry-run 模式測試
        cleanup_old_jenkins_builds_task(days=90, dry_run=True)
        
        # 清理 90 天前的 Builds
        cleanup_old_jenkins_builds_task(days=90, only_stored=True)
        
        # 清理特定伺服器，排除特定 Job
        cleanup_old_jenkins_builds_task(
            server_id=1,
            days=90,
            exclude_patterns=[r'^seed.*', r'.*_test$']
        )
    """
    from .models import JenkinsServer, JenkinsBuild
    from django.utils import timezone
    from django.db import transaction
    import re
    import time
    
    start_time = time.time()
    
    logger.info('[Celery] 🧹 開始清理舊 Jenkins Builds')
    logger.info(f'[Celery] 📝 配置：保留最近 {days} 天，only_stored={only_stored}')
    
    if dry_run:
        logger.warning('[Celery] 🔍 試運行模式：只檢查不刪除')
    
    exclude_patterns = exclude_patterns or []
    cutoff_date = timezone.now() - timedelta(days=days)
    
    logger.info(f'[Celery] ⏰ 截止日期：{cutoff_date.strftime("%Y-%m-%d %H:%M:%S")}')
    
    stats = {
        'success': True,
        'total_checked': 0,
        'total_old_builds': 0,
        'deleted_builds': 0,
        'nas_folders_deleted': 0,
        'nas_space_freed': 0,
        'skipped': 0,
        'errors': 0,
        'servers_checked': 0,
        'servers_details': [],
        'duration': 0
    }
    
    try:
        # 決定要處理的 Servers
        if server_id:
            servers = JenkinsServer.objects.filter(id=server_id, is_active=True)
            logger.info(f'[Celery] 📡 將檢查指定 Server (ID: {server_id})')
        else:
            servers = JenkinsServer.objects.filter(is_active=True)
            logger.info(f'[Celery] 📡 將檢查 {servers.count()} 個 Jenkins Servers')
        
        stats['servers_checked'] = servers.count()
        
        # 處理每個 Server
        for server in servers:
            server_start_time = time.time()
            server_name = server.name or server.ip_address or server.url
            
            logger.info(f'[Celery] 🖥️  檢查 Server: {server_name} ({server.url})')
            
            server_stats = {
                'server_id': server.id,
                'server_name': server_name,
                'server_url': server.url,
                'checked': 0,
                'old_builds': 0,
                'deleted': 0,
                'nas_deleted': 0,
                'nas_freed': 0,
                'skipped': 0,
                'errors': 0,
                'success': True,
                'duration': 0
            }
            
            try:
                # 查詢舊 Builds
                query = JenkinsBuild.objects.filter(
                    job__server=server,
                    build_timestamp__lt=cutoff_date
                ).select_related('job')
                
                if only_stored:
                    query = query.filter(is_workspace_stored=True)
                
                old_builds = list(query)
                server_stats['old_builds'] = len(old_builds)
                stats['total_old_builds'] += len(old_builds)
                
                logger.info(f'[Celery]   📊 找到 {len(old_builds)} 個舊 Builds（早於 {days} 天）')
                
                if len(old_builds) == 0:
                    logger.info('[Celery]   ✅ 無需清理的舊 Builds')
                    server_stats['duration'] = time.time() - server_start_time
                    stats['servers_details'].append(server_stats)
                    continue
                
                # 處理每個舊 Build
                for build in old_builds:
                    server_stats['checked'] += 1
                    stats['total_checked'] += 1
                    
                    # 檢查排除模式
                    is_excluded = False
                    for pattern in exclude_patterns:
                        try:
                            if re.match(pattern, build.job.name):
                                is_excluded = True
                                server_stats['skipped'] += 1
                                stats['skipped'] += 1
                                logger.debug(
                                    f'[Celery]     🛡️  跳過（符合排除模式）: {build.job.name} #{build.build_number}'
                                )
                                break
                        except re.error as e:
                            logger.warning(f'[Celery]     ⚠️  無效的 regex 模式 "{pattern}": {e}')
                    
                    if is_excluded:
                        continue
                    
                    # 試運行模式
                    if dry_run:
                        age_days = (timezone.now() - build.build_timestamp).days
                        logger.info(
                            f'[Celery]     🔍 [DRY-RUN] 將刪除: {build.job.name} #{build.build_number} '
                            f'({age_days} 天前)'
                        )
                        server_stats['deleted'] += 1
                        stats['deleted_builds'] += 1
                        
                        # 計算可能釋放的空間
                        if build.is_workspace_stored and build.workspace_path:
                            nas_result = cleanup_nas_workspace(build, dry_run=True)
                            if nas_result['success'] and nas_result.get('size_freed', 0) > 0:
                                server_stats['nas_deleted'] += 1
                                server_stats['nas_freed'] += nas_result['size_freed']
                                stats['nas_folders_deleted'] += 1
                                stats['nas_space_freed'] += nas_result['size_freed']
                        
                        continue
                    
                    # 實際清理
                    try:
                        build_info = f"{build.job.name} #{build.build_number}"
                        age_days = (timezone.now() - build.build_timestamp).days
                        
                        # 1. 清理 NAS Workspace
                        if build.is_workspace_stored and build.workspace_path:
                            nas_result = cleanup_nas_workspace(build, dry_run=False)
                            
                            if nas_result['success']:
                                if nas_result.get('size_freed', 0) > 0:
                                    server_stats['nas_deleted'] += 1
                                    server_stats['nas_freed'] += nas_result['size_freed']
                                    stats['nas_folders_deleted'] += 1
                                    stats['nas_space_freed'] += nas_result['size_freed']
                                    
                                    size_mb = nas_result['size_freed'] / 1024 / 1024
                                    logger.info(
                                        f'[Celery]     ✅ NAS 已清理: {build_info} ({age_days} 天前, {size_mb:.2f} MB)'
                                    )
                            else:
                                server_stats['errors'] += 1
                                stats['errors'] += 1
                                logger.error(
                                    f'[Celery]     ❌ NAS 清理失敗: {build_info}: '
                                    f'{nas_result.get("error", "Unknown error")}'
                                )
                        
                        # 2. 刪除資料庫記錄
                        with transaction.atomic():
                            build.delete()
                            server_stats['deleted'] += 1
                            stats['deleted_builds'] += 1
                            logger.debug(f'[Celery]     ✅ DB 已刪除: {build_info}')
                        
                    except Exception as e:
                        server_stats['errors'] += 1
                        stats['errors'] += 1
                        logger.error(
                            f'[Celery]     ❌ 清理失敗: {build.job.name} #{build.build_number}: {e}',
                            exc_info=True
                        )
                
                # Server 完成統計
                server_duration = time.time() - server_start_time
                server_stats['duration'] = server_duration
                
                logger.info(f'[Celery]   ✅ Server "{server_name}" 處理完成 (耗時: {server_duration:.2f}s)')
                logger.info(f'[Celery]     - 檢查: {server_stats["checked"]} 個')
                logger.info(f'[Celery]     - 刪除: {server_stats["deleted"]} 個')
                
                if server_stats['nas_deleted'] > 0:
                    freed_gb = server_stats['nas_freed'] / 1024 / 1024 / 1024
                    logger.info(f'[Celery]     - NAS 釋放: {freed_gb:.3f} GB')
                
                if server_stats['skipped'] > 0:
                    logger.info(f'[Celery]     - 跳過: {server_stats["skipped"]} 個')
                
                if server_stats['errors'] > 0:
                    logger.warning(f'[Celery]     - 錯誤: {server_stats["errors"]} 個')
                
            except Exception as e:
                server_stats['success'] = False
                server_stats['duration'] = time.time() - server_start_time
                logger.error(f'[Celery]   ❌ Server "{server_name}" 處理失敗: {e}', exc_info=True)
            
            stats['servers_details'].append(server_stats)
        
        # 最終統計
        duration = time.time() - start_time
        stats['duration'] = duration
        
        logger.info('[Celery] 🎉 舊 Builds 清理完成')
        logger.info(f'[Celery]   - 檢查伺服器: {stats["servers_checked"]} 個')
        logger.info(f'[Celery]   - 檢查 Builds: {stats["total_checked"]} 個')
        logger.info(f'[Celery]   - 找到舊 Builds: {stats["total_old_builds"]} 個')
        logger.info(f'[Celery]   - 已刪除 Builds: {stats["deleted_builds"]} 個')
        
        if stats['nas_folders_deleted'] > 0:
            freed_gb = stats['nas_space_freed'] / 1024 / 1024 / 1024
            logger.info(f'[Celery]   - NAS 資料夾已刪除: {stats["nas_folders_deleted"]} 個')
            logger.info(f'[Celery]   - NAS 空間釋放: {freed_gb:.3f} GB')
        
        if dry_run:
            logger.info('[Celery]   - 模式: 試運行（未執行實際刪除）')
        
        if stats['skipped'] > 0:
            logger.info(f'[Celery]   - 跳過（排除模式）: {stats["skipped"]} 個')
        
        if stats['errors'] > 0:
            logger.warning(f'[Celery]   - 錯誤數量: {stats["errors"]} 個')
        
        logger.info(f'[Celery]   - 總耗時: {duration:.2f} 秒')
        
        return stats
        
    except Exception as exc:
        logger.error('[Celery] 💥 舊 Builds 清理任務異常', exc_info=True)
        
        # 自動重試（最多 2 次）
        try:
            raise self.retry(exc=exc, countdown=1800)
        except self.MaxRetriesExceededError:
            logger.error('[Celery] 舊 Builds 清理任務重試次數已達上限')
            duration = time.time() - start_time
            stats['success'] = False
            stats['duration'] = duration
            stats['error_message'] = str(exc)
            return stats


# ============================================================================
# 智能自適應 Jenkins Builds 同步任務
# ============================================================================

@shared_task(
    bind=True,
    name='api.tasks.sync_jenkins_builds_adaptive',
    max_retries=2,
    default_retry_delay=300,
    time_limit=3600,
    soft_time_limit=3300
)
def sync_jenkins_builds_adaptive(
    self,
    server_id=None,
    max_builds_per_job=20,
    max_age_days=3,
    enable_cpu_monitoring=True,
    cpu_high_threshold=85.0,
    cpu_low_threshold=60.0,
    max_wait_seconds=300
):
    """
    智能自適應 Jenkins Builds 同步任務（CPU 感知版本）
    
    相比標準的 sync_jenkins_builds，此版本會：
    1. 實時監控系統 CPU 使用率
    2. 當 CPU > 85% 時自動暫停處理
    3. 當 CPU < 60% 時恢復處理
    4. 動態調整批次大小以優化性能
    
    Args:
        server_id: Jenkins Server ID（None = 所有）
        max_builds_per_job: 每個 Job 最多同步幾個 Builds
        max_age_days: 只同步最近 N 天內的 Builds
        enable_cpu_monitoring: 是否啟用 CPU 監控（預設 True）
        cpu_high_threshold: CPU 高負載閾值 (%)
        cpu_low_threshold: CPU 低負載閾值 (%)
        max_wait_seconds: CPU 過載時最大等待時間（秒）
        
    Returns:
        dict: 執行結果統計（包含 CPU 監控數據）
    """
    from .models import JenkinsServer, JenkinsJob, JenkinsBuild
    from library.services.jenkins_client import JenkinsClient
    from library.utils.system_monitor import SystemMonitor, AdaptiveBatchController
    from datetime import datetime, timedelta
    from django.utils import timezone as dj_timezone
    import pytz
    
    start_time = time.time()
    
    # 初始化系統監控（如果啟用）
    monitor = None
    batch_controller = None
    
    if enable_cpu_monitoring:
        monitor = SystemMonitor()
        batch_controller = AdaptiveBatchController(
            min_batch_size=1,
            max_batch_size=10,
            target_cpu=70.0,
            low_cpu_threshold=cpu_low_threshold,
            high_cpu_threshold=cpu_high_threshold
        )
        logger.info('[Celery] 🧠 智能自適應模式已啟用（CPU 監控）')
    
    try:
        logger.info('[Celery] 🔄 開始智能同步 Jenkins Builds')
        logger.info(f'[Celery]   - Server ID: {server_id if server_id else "All"}')
        logger.info(f'[Celery]   - CPU 監控: {"啟用" if enable_cpu_monitoring else "禁用"}')
        if enable_cpu_monitoring:
            logger.info(f'[Celery]   - CPU 閾值: 高={cpu_high_threshold}%, 低={cpu_low_threshold}%')
        
        # 計算時間範圍
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
                'error_message': 'No online servers found'
            }
        
        # 統計變數
        total_servers = servers.count()
        total_jobs_processed = 0
        builds_created = 0
        builds_updated = 0
        builds_skipped = 0
        errors = 0
        
        # CPU 監控統計
        cpu_pauses = 0          # CPU 過載導致的暫停次數
        cpu_wait_time = 0       # CPU 過載等待總時間（秒）
        cpu_samples = []        # CPU 採樣數據
        
        logger.info(f'[Celery] 📡 找到 {total_servers} 個在線的 Jenkins Server')
        
        for server in servers:
            logger.info(f'[Celery] 🖥️  處理 Server: {server.name}')
            
            jobs = JenkinsJob.objects.filter(server=server)
            jobs_count = jobs.count()
            
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
                        # ✅ CPU 監控：檢查是否需要暫停
                        if enable_cpu_monitoring and batch_controller.should_pause():
                            logger.warning(
                                f'[Celery] 🛑 CPU 過載，暫停處理 Job: {job.name}'
                            )
                            
                            # 等待系統負載降低
                            pause_start = time.time()
                            if monitor.monitor_until_low_load(
                                cpu_threshold=cpu_low_threshold,
                                max_wait_seconds=max_wait_seconds
                            ):
                                pause_duration = time.time() - pause_start
                                cpu_wait_time += pause_duration
                                cpu_pauses += 1
                                logger.info(
                                    f'[Celery] ✅ 系統負載已降低，'
                                    f'恢復處理（等待了 {pause_duration:.1f} 秒）'
                                )
                            else:
                                # 超時仍未恢復，記錄並繼續（可能需要跳過部分處理）
                                pause_duration = time.time() - pause_start
                                cpu_wait_time += pause_duration
                                cpu_pauses += 1
                                logger.warning(
                                    f'[Celery] ⏰ 等待超時（{max_wait_seconds} 秒），'
                                    f'強制恢復處理'
                                )
                        
                        # ✅ CPU 監控：記錄當前 CPU 狀態
                        if enable_cpu_monitoring:
                            current_metrics = monitor.get_current_metrics()
                            cpu_samples.append(current_metrics.cpu_percent)
                            
                            # 動態調整批次大小
                            batch_size = batch_controller.adjust_batch_size()
                            logger.debug(
                                f'[Celery]   當前 CPU: {current_metrics.cpu_percent:.1f}%, '
                                f'批次大小: {batch_size}'
                            )
                        
                        # 獲取現有 Builds
                        existing_builds = {
                            b.build_number: b
                            for b in JenkinsBuild.objects.filter(job=job)
                                .only('id', 'build_number', 'result', 'is_building', 'updated_at')
                                .order_by('-build_number')[:max_builds_per_job]
                        }
                        
                        # 從 Jenkins API 獲取 Builds
                        jenkins_builds = client.get_job_builds(job.name, limit=max_builds_per_job)
                        
                        if not jenkins_builds:
                            continue
                        
                        # 智能過濾
                        recent_time = dj_timezone.now() - timedelta(minutes=15)
                        new_builds = []
                        builds_to_check = []
                        
                        for b in jenkins_builds:
                            build_num = b.get('number')
                            if build_num in existing_builds:
                                db_build = existing_builds[build_num]
                                if (db_build.is_building or 
                                    db_build.updated_at >= recent_time or 
                                    db_build.result in ['UNKNOWN', None]):
                                    builds_to_check.append((b, db_build))
                            else:
                                new_builds.append(b)
                        
                        # 處理新 Builds
                        for build_data in new_builds:
                            try:
                                build_number = build_data.get('number')
                                result = build_data.get('result')
                                building = build_data.get('building', False)
                                duration = build_data.get('duration', 0)
                                url = build_data.get('url', '')
                                
                                timestamp = build_data.get('timestamp', 0) / 1000
                                build_timestamp = datetime.fromtimestamp(timestamp, tz=pytz.UTC)
                                
                                if build_timestamp < cutoff_time:
                                    builds_skipped += 1
                                    continue
                                
                                # 創建 Build
                                JenkinsBuild.objects.create(
                                    job=job,
                                    build_number=build_number,
                                    display_name=f'#{build_number}',
                                    url=url,
                                    result=result or 'UNKNOWN',
                                    is_building=building,
                                    duration=duration,
                                    build_timestamp=build_timestamp,
                                )
                                builds_created += 1
                                
                            except Exception as e:
                                logger.error(
                                    f'[Celery]     ❌ 創建 Build 失敗: {job.name} #{build_number}: {e}'
                                )
                                errors += 1
                        
                        # 處理需要檢查的 Builds
                        for build_data, db_build in builds_to_check:
                            try:
                                result = build_data.get('result')
                                building = build_data.get('building', False)
                                
                                # 檢查是否需要更新
                                needs_update = False
                                if db_build.result != result:
                                    db_build.result = result or 'UNKNOWN'
                                    needs_update = True
                                
                                if db_build.is_building != building:
                                    db_build.is_building = building
                                    needs_update = True
                                
                                if needs_update:
                                    db_build.save(update_fields=['result', 'is_building', 'updated_at'])
                                    builds_updated += 1
                                    
                            except Exception as e:
                                logger.error(
                                    f'[Celery]     ❌ 更新 Build 失敗: {job.name} #{db_build.build_number}: {e}'
                                )
                                errors += 1
                        
                        total_jobs_processed += 1
                        
                    except Exception as e:
                        logger.error(f'[Celery]   ❌ 處理 Job "{job.name}" 失敗: {e}', exc_info=True)
                        errors += 1
                        
            except Exception as e:
                logger.error(f'[Celery] ❌ 處理 Server "{server.name}" 失敗: {e}', exc_info=True)
                errors += 1
                
            finally:
                if client:
                    client.close()
        
        # 計算執行時間
        duration = time.time() - start_time
        
        # CPU 統計
        avg_cpu = sum(cpu_samples) / len(cpu_samples) if cpu_samples else 0
        max_cpu = max(cpu_samples) if cpu_samples else 0
        
        result = {
            'success': True,
            'total_servers': total_servers,
            'total_jobs': total_jobs_processed,
            'builds_created': builds_created,
            'builds_updated': builds_updated,
            'builds_skipped': builds_skipped,
            'errors': errors,
            'duration': duration,
            # CPU 監控數據
            'cpu_monitoring_enabled': enable_cpu_monitoring,
            'cpu_pauses': cpu_pauses,
            'cpu_wait_time': cpu_wait_time,
            'avg_cpu': avg_cpu,
            'max_cpu': max_cpu,
        }
        
        logger.info('[Celery] 🎉 智能同步完成')
        logger.info(f'[Celery]   - Jobs 處理: {total_jobs_processed} 個')
        logger.info(f'[Celery]   - Builds 創建: {builds_created} 個')
        logger.info(f'[Celery]   - Builds 更新: {builds_updated} 個')
        logger.info(f'[Celery]   - Builds 跳過: {builds_skipped} 個')
        
        if enable_cpu_monitoring:
            logger.info(f'[Celery]   - 平均 CPU: {avg_cpu:.1f}%')
            logger.info(f'[Celery]   - 峰值 CPU: {max_cpu:.1f}%')
            logger.info(f'[Celery]   - CPU 暫停次數: {cpu_pauses}')
            logger.info(f'[Celery]   - CPU 等待時間: {cpu_wait_time:.1f} 秒')
        
        if errors > 0:
            logger.warning(f'[Celery]   - 錯誤數量: {errors} 個')
        
        logger.info(f'[Celery]   - 總耗時: {duration:.2f} 秒')
        
        return result
        
    except Exception as exc:
        logger.error('[Celery] 💥 智能同步任務異常', exc_info=True)
        
        try:
            raise self.retry(exc=exc, countdown=300)
        except self.MaxRetriesExceededError:
            logger.error('[Celery] 智能同步任務重試次數已達上限')
            return {
                'success': False,
                'duration': time.time() - start_time,
                'error_message': str(exc)
            }
