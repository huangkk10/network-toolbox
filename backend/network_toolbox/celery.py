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
    # 任務 1：DHCP 日誌自動同步（每 10 分鐘，同步所有在線伺服器）
    'sync-all-dhcp-logs-every-10-minutes': {
        'task': 'api.tasks.sync_all_dhcp_logs_task',
        'schedule': crontab(minute='*/10'),  # 每 10 分鐘執行一次
        'kwargs': {
            'limit': 500       # 每個伺服器最多同步 500 筆
        },
        'options': {
            'expires': 540,    # 任務超時 9 分鐘（避免與下次重疊）
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
    
    # 任務 3：OUI 資料庫自動更新（每月 1 號凌晨 2 點）
    'update-oui-database-monthly': {
        'task': 'api.tasks.update_oui_database_task',
        'schedule': crontab(day_of_month='1', hour=2, minute=0),  # 每月 1 號 02:00 執行
        'kwargs': {
            'source': 0,       # 使用 IEEE Official HTTPS 來源
            'backup': True     # 自動備份現有資料庫
        },
        'options': {
            'expires': 540,    # 任務超時 9 分鐘
        }
    },
    
    # 任務 4：NAS 連線檢測（每 5 分鐘）
    'check-nas-connection-every-5-minutes': {
        'task': 'api.tasks.check_nas_connection_task',
        'schedule': crontab(minute='*/5'),  # 每 5 分鐘執行一次
        'options': {
            'expires': 150,    # 任務超時 2.5 分鐘
        }
    },
    
    # 任務 5：IPXE 網路品質檢測 - 批次檢測所有線上 Server（每 5 分鐘）
    'check-all-ipxe-network-quality-every-5-minutes': {
        'task': 'api.tasks.check_all_ipxe_network_quality_task',
        'schedule': crontab(minute='*/5'),  # 每 5 分鐘執行一次
        'options': {
            'expires': 540,    # 任務超時 9 分鐘（批次執行需要更長時間）
        }
    },
    
    # 任務 6：DHCP Scope 自動同步（每天凌晨 4 點）
    'sync-all-dhcp-scopes-daily': {
        'task': 'api.tasks.sync_all_dhcp_scopes_task',
        'schedule': crontab(hour=4, minute=0),  # 每天 04:00 執行
        'options': {
            'expires': 1800,   # 任務超時 30 分鐘
        }
    },
    
    # 任務 7：DHCP 租約自動同步（每 15 分鐘，同步所有在線伺服器）
    'sync-all-dhcp-leases-every-15-minutes': {
        'task': 'api.tasks.sync_all_dhcp_leases_task',
        'schedule': crontab(minute='*/15'),  # 每 15 分鐘執行一次
        'options': {
            'expires': 810,    # 任務超時 13.5 分鐘（避免與下次重疊）
        }
    },
    
    # 任務 8：Switch 自動識別與更新（每小時，所有 DHCP Server）
    'auto-identify-switches-hourly': {
        'task': 'api.tasks.auto_identify_switches_task',
        'schedule': crontab(minute=0),  # 每小時整點執行
        'kwargs': {
            'server_id': None  # None 表示處理所有 Server
        },
        'options': {
            'expires': 540,    # 任務超時 9 分鐘
        }
    },
    
    # 任務 9：GitLab 連線品質檢測（每 5 分鐘）
    'check-gitlab-connection-every-5-minutes': {
        'task': 'api.tasks.check_gitlab_connection_task',
        'schedule': crontab(minute='*/5'),  # 每 5 分鐘執行一次
        'options': {
            'expires': 150,    # 任務超時 2.5 分鐘
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
