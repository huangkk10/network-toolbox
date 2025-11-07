"""
Django Signals - 自動化任務觸發器

在模型事件（創建、更新、刪除）時自動執行相應的操作
"""

import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import DHCPServer, DHCPLease, IPXEServer

logger = logging.getLogger(__name__)


@receiver(post_save, sender=DHCPServer)
def dhcp_server_post_save(sender, instance, created, **kwargs):
    """
    DHCP Server 創建或更新後的自動化處理
    
    功能：
    1. 新建伺服器時：自動執行初始 Scope 同步
    2. 更新伺服器時：如果狀態變為 online，檢查並同步 Scope
    
    Args:
        sender: DHCPServer 模型類別
        instance: DHCPServer 實例
        created: 是否為新建（True）或更新（False）
        **kwargs: 額外參數
    """
    try:
        if created:
            # 新建伺服器 - 執行初始同步
            logger.info(f'[Signal] 偵測到新建 DHCP Server: {instance.name} ({instance.ip_address})')
            
            # 檢查是否有 SSH 配置
            if not instance.ssh_password and not instance.ssh_key_file:
                logger.warning(f'[Signal] Server {instance.name} 缺少 SSH 憑證，跳過自動同步')
                return
            
            # 延遲 10 秒後執行（給用戶時間配置完整資訊）
            from .tasks import sync_dhcp_scopes_task
            
            logger.info(f'[Signal] 排程 Scope 初始同步任務 - Server ID: {instance.id}')
            sync_dhcp_scopes_task.apply_async(
                args=[instance.id],
                countdown=10,  # 10 秒後執行
                retry=True,
                retry_policy={
                    'max_retries': 3,
                    'interval_start': 60,  # 首次重試等待 60 秒
                    'interval_step': 60,   # 每次增加 60 秒
                }
            )
            
            logger.info(f'[Signal] Scope 同步任務已排程 - Server: {instance.name}')
            
            # 🆕 新功能：排程 Switch 自動識別任務
            # 延遲 60 秒後執行（等待租約同步完成）
            from .tasks import auto_identify_switches_task
            
            logger.info(f'[Signal] 排程 Switch 自動識別任務 - Server ID: {instance.id}')
            auto_identify_switches_task.apply_async(
                kwargs={'server_id': instance.id},
                countdown=60,  # 60 秒後執行（給足時間讓租約同步）
                retry=True,
                retry_policy={
                    'max_retries': 2,
                    'interval_start': 120,  # 首次重試等待 2 分鐘
                }
            )
            
            logger.info(f'[Signal] Switch 識別任務已排程 - Server: {instance.name}')
        
        else:
            # 更新伺服器 - 檢查狀態變化
            # 使用 instance._state.fields_cache 或查詢舊值
            # 如果從 offline 變為 online，執行同步
            
            # 簡化版本：不檢查舊值，僅當狀態為 online 且沒有 Scope 時同步
            if instance.status == 'online':
                from .models import DHCPScope
                
                scope_count = DHCPScope.objects.filter(server=instance).count()
                
                if scope_count == 0:
                    logger.info(
                        f'[Signal] Server {instance.name} 已上線但無 Scope 數據，'
                        f'排程自動同步'
                    )
                    
                    from .tasks import sync_dhcp_scopes_task
                    
                    sync_dhcp_scopes_task.apply_async(
                        args=[instance.id],
                        countdown=5,  # 5 秒後執行
                    )
    
    except Exception as e:
        logger.error(f'[Signal] DHCP Server post_save 處理失敗: {str(e)}', exc_info=True)


@receiver(post_delete, sender=DHCPServer)
def dhcp_server_post_delete(sender, instance, **kwargs):
    """
    DHCP Server 刪除後的清理工作
    
    注意：相關的 DHCPLease, DHCPScope, DHCPLog 會因為 CASCADE 自動刪除
    這裡只記錄日誌
    
    Args:
        sender: DHCPServer 模型類別
        instance: 已刪除的 DHCPServer 實例
        **kwargs: 額外參數
    """
    try:
        logger.info(f'[Signal] DHCP Server 已刪除: {instance.name} ({instance.ip_address})')
        
        # 可以在這裡添加額外的清理邏輯
        # 例如：通知管理員、備份數據等
        
    except Exception as e:
        logger.error(f'[Signal] DHCP Server post_delete 處理失敗: {str(e)}', exc_info=True)


@receiver(post_save, sender=DHCPLease)
def dhcp_lease_post_save(sender, instance, created, **kwargs):
    """
    DHCP Lease 創建或更新後的處理
    
    當租約有 Option 82 資訊 (remote_id) 時，自動更新對應 Switch 的統計資訊
    這確保 Switch 資訊保持最新狀態
    
    Args:
        sender: DHCPLease 模型類別
        instance: DHCPLease 實例
        created: 是否為新建
        **kwargs: 額外參數
    """
    try:
        # 只處理有 remote_id 的租約（表示有 Option 82 資訊）
        if instance.remote_id and instance.remote_id.strip():
            from .models import NetworkSwitch
            
            # 查找對應的 Switch
            switch = NetworkSwitch.objects.filter(remote_id=instance.remote_id).first()
            
            if switch:
                # 更新 Switch 統計資訊（避免頻繁更新，使用 Celery 延遲）
                from .tasks import update_switch_statistics_task
                
                # 延遲 30 秒批次更新（避免大量租約同時更新造成性能問題）
                update_switch_statistics_task.apply_async(
                    kwargs={'switch_id': switch.id},
                    countdown=30,
                    # 使用任務去重，同一個 Switch 30 秒內只更新一次
                    task_id=f'update_switch_stats_{switch.id}'
                )
                
                logger.debug(f'[Signal] 已排程 Switch 統計更新: {switch.name} (remote_id: {instance.remote_id})')
            
            elif created:
                # 新租約有 remote_id 但找不到對應的 Switch
                # 可能是新的 Switch 設備，記錄以便後續識別
                logger.info(
                    f'[Signal] 發現新的 remote_id 但無對應 Switch: {instance.remote_id} '
                    f'(IP: {instance.ip_address}, Server: {instance.server.name})'
                )
    
    except Exception as e:
        logger.error(f'[Signal] DHCP Lease post_save 處理失敗: {str(e)}', exc_info=True)


def trigger_switch_identification_for_server(server_id, delay_seconds=5):
    """
    手動觸發特定 Server 的 Switch 識別任務
    
    可用於：
    1. 手動補充識別
    2. 在租約同步後立即識別 Switch
    3. 故障排查和測試
    
    Args:
        server_id: DHCP Server ID
        delay_seconds: 延遲執行秒數（預設 5 秒）
        
    Returns:
        str: Celery Task ID，如果失敗則返回 None
        
    Example:
        >>> from api.signals import trigger_switch_identification_for_server
        >>> task_id = trigger_switch_identification_for_server(server_id=6, delay_seconds=10)
        >>> print(f"Task ID: {task_id}")
    """
    try:
        from .tasks import auto_identify_switches_task
        
        result = auto_identify_switches_task.apply_async(
            kwargs={'server_id': server_id},
            countdown=delay_seconds
        )
        
        logger.info(
            f'[Manual] 已手動觸發 Switch 識別任務 '
            f'(Server ID: {server_id}, Task ID: {result.id}, Delay: {delay_seconds}s)'
        )
        return result.id
        
    except Exception as e:
        logger.error(f'[Manual] 手動觸發 Switch 識別失敗: {e}', exc_info=True)
        return None


# ============================================================================
# iPXE Server 自動化 Signals
# ============================================================================

@receiver(post_save, sender=IPXEServer)
def ipxe_server_post_save(sender, instance, created, **kwargs):
    """
    iPXE Server 創建或更新後的自動化處理
    
    功能：
    1. 新建伺服器時：
       - 步驟 1：驗證 SSH 連接（2 秒後）
       - 步驟 2：執行首次日誌收集（30 秒後，僅當 SSH 驗證成功）
    2. 確保新伺服器立即開始工作
    
    Args:
        sender: IPXEServer 模型類別
        instance: IPXEServer 實例
        created: 是否為新建（True）或更新（False）
        **kwargs: 額外參數
    """
    try:
        if created:
            # 新建伺服器 - 執行 SSH 驗證和首次日誌收集
            logger.info(f'[Signal] 偵測到新建 iPXE Server: {instance.name} ({instance.ip_address})')
            
            # 步驟 1：快速驗證 SSH 連接（2 秒後執行）
            from .tasks import verify_ipxe_server_ssh_task
            
            logger.info(f'[Signal] 排程 SSH 連接驗證任務 - Server ID: {instance.id}')
            verify_task = verify_ipxe_server_ssh_task.apply_async(
                args=[instance.id],
                countdown=2,  # 2 秒後快速驗證
            )
            
            logger.info(f'[Signal] SSH 驗證任務已排程 - Task ID: {verify_task.id}')
            
            # 步驟 2：延遲執行首次日誌收集（30 秒後）
            # 僅當 connection_status 為 'connected' 時才會實際收集
            from .tasks import sync_ipxe_logs_task
            
            logger.info(f'[Signal] 排程首次日誌收集任務 - Server ID: {instance.id}')
            sync_ipxe_logs_task.apply_async(
                args=[instance.id],
                kwargs={'limit': 1000},
                countdown=30,  # 30 秒後執行（給 SSH 驗證足夠時間）
                retry=True,
                retry_policy={
                    'max_retries': 3,
                    'interval_start': 60,  # 首次重試等待 60 秒
                    'interval_step': 60,   # 每次增加 60 秒
                }
            )
            
            logger.info(f'[Signal] SSH 驗證和日誌收集任務已排程 - Server: {instance.name}')
        
        else:
            # 更新伺服器 - 檢查狀態變化
            # 如果從 offline 變為 online，執行一次日誌收集
            if instance.status == 'online':
                from .models import IPXELog
                
                log_count = IPXELog.objects.filter(server=instance).count()
                
                if log_count == 0:
                    logger.info(
                        f'[Signal] Server {instance.name} 已上線但無日誌數據，'
                        f'排程自動收集'
                    )
                    
                    from .tasks import sync_ipxe_logs_task
                    
                    sync_ipxe_logs_task.apply_async(
                        args=[instance.id],
                        kwargs={'limit': 1000},
                        countdown=5,  # 5 秒後執行
                    )
    
    except Exception as e:
        logger.error(f'[Signal] iPXE Server post_save 處理失敗: {str(e)}', exc_info=True)


@receiver(post_delete, sender=IPXEServer)
def ipxe_server_post_delete(sender, instance, **kwargs):
    """
    iPXE Server 刪除後的清理工作
    
    注意：相關的 IPXELog 會因為 CASCADE 自動刪除
    這裡只記錄日誌
    
    Args:
        sender: IPXEServer 模型類別
        instance: 已刪除的 IPXEServer 實例
        **kwargs: 額外參數
    """
    try:
        logger.info(f'[Signal] iPXE Server 已刪除: {instance.name} ({instance.ip_address})')
        
        # 可以在這裡添加額外的清理邏輯
        # 例如：通知管理員、備份數據等
        
    except Exception as e:
        logger.error(f'[Signal] iPXE Server post_delete 處理失敗: {str(e)}', exc_info=True)


def trigger_ipxe_logs_sync_for_server(server_id, delay_seconds=5, limit=1000):
    """
    手動觸發特定 iPXE Server 的日誌收集任務
    
    可用於：
    1. 手動補充收集日誌
    2. 故障排查和測試
    3. 立即同步特定伺服器
    
    Args:
        server_id: iPXE Server ID
        delay_seconds: 延遲執行秒數（預設 5 秒）
        limit: 每個容器收集的日誌數量（預設 1000）
        
    Returns:
        str: Celery Task ID，如果失敗則返回 None
        
    Example:
        >>> from api.signals import trigger_ipxe_logs_sync_for_server
        >>> task_id = trigger_ipxe_logs_sync_for_server(server_id=4, delay_seconds=0, limit=2000)
        >>> print(f"Task ID: {task_id}")
    """
    try:
        from .tasks import sync_ipxe_logs_task
        
        result = sync_ipxe_logs_task.apply_async(
            args=[server_id],
            kwargs={'limit': limit},
            countdown=delay_seconds
        )
        
        logger.info(
            f'[Manual] 已手動觸發 iPXE 日誌收集任務 '
            f'(Server ID: {server_id}, Task ID: {result.id}, Delay: {delay_seconds}s, Limit: {limit})'
        )
        return result.id
        
    except Exception as e:
        logger.error(f'[Manual] 手動觸發 iPXE 日誌收集失敗: {e}', exc_info=True)
        return None
