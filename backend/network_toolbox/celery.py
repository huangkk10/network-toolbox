"""
Celery 配置文件

Network Toolbox 定時任務配置
"""

import os
from celery import Celery
from celery.schedules import crontab

# 設置 Django 設置模組
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')

# 創建 Celery 應用實例
app = Celery('network_toolbox')

# 從 Django settings 讀取配置（使用 CELERY_ 前綴）
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自動發現所有已安裝應用中的 tasks.py
app.autodiscover_tasks()


# ==================== 定時任務排程配置 ====================
app.conf.beat_schedule = {
    # 任務 1：DHCP 日誌自動同步（每 5 分鐘）
    'sync-dhcp-logs-every-5-minutes': {
        'task': 'api.tasks.sync_dhcp_logs_task',
        'schedule': crontab(minute='*/5'),  # 每 5 分鐘執行一次
        'kwargs': {
            'server_id': 1,    # DHCP Server ID
            'limit': 500       # 每次最多同步 500 筆
        },
        'options': {
            'expires': 240,    # 任務超時 4 分鐘（避免與下次重疊）
        }
    },
    
    # 任務 2：DHCP 日誌自動清理（每天凌晨 3 點）
    'cleanup-old-dhcp-logs-daily': {
        'task': 'api.tasks.cleanup_old_logs_task',
        'schedule': crontab(hour=3, minute=0),  # 每天 03:00 執行
        'kwargs': {
            'days': 7          # 清理 7 天前的日誌
        },
        'options': {
            'expires': 3600,   # 任務超時 1 小時
        }
    },
}


# ==================== Celery 配置 ====================
app.conf.update(
    # 時區設置
    timezone='Asia/Taipei',
    enable_utc=False,
    
    # 任務結果過期時間（1 天）
    result_expires=86400,
    
    # 任務序列化格式
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    
    # Worker 配置
    worker_prefetch_multiplier=1,  # 一次只取一個任務（避免阻塞）
    worker_max_tasks_per_child=50,  # 每個 Worker 處理 50 個任務後重啟（防止記憶體洩漏）
    
    # 任務追蹤
    task_track_started=True,
    task_send_sent_event=True,
)


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """除錯用的測試任務"""
    print(f'Request: {self.request!r}')
