"""
Django Signals - 自動化任務觸發器

在模型事件（創建、更新、刪除）時自動執行相應的操作
"""

import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import DHCPServer

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
