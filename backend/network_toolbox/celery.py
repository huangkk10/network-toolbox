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

# 明確載入 api.tasks
# 這確保所有任務都被註冊到 Celery
app.conf.imports = ('api.tasks',)

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
    
    # 任務 6：DHCP Scope 自動同步（每天凌晨 4 點 30 分）
    'sync-all-dhcp-scopes-daily': {
        'task': 'api.tasks.sync_all_dhcp_scopes_task',
        'schedule': crontab(hour=4, minute=30),  # ✅ 改為每天 04:30 執行（錯開 30 分鐘）
        'options': {
            'expires': 1500,   # 任務超時 25 分鐘
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
    
    # 任務 10：Jenkins Builds 同步（每 10 分鐘執行一次）
    'sync-jenkins-builds-every-10-minutes': {
        'task': 'api.tasks.sync_jenkins_builds',
        'schedule': crontab(minute='*/10'),  # 每 10 分鐘執行一次
        'kwargs': {
            'server_id': None,           # None 表示處理所有 Server
            'max_builds_per_job': 20,    # 每個 Job 最多同步 20 個 Builds
            'max_age_days': 30           # 只同步最近 30 天內的 Builds（從 7 改為 30）
        },
        'options': {
            'expires': 540,    # 任務超時 9 分鐘
            # 'queue': 'default',  # 已移除：使用默認隊列 'celery'
        }
    },
    
    # 任務 10-1：【即時監控】活躍 Jenkins Builds 高頻同步（每 1 分鐘執行一次）
    'sync-active-jenkins-builds-every-1-minute': {
        'task': 'api.tasks.sync_active_jenkins_builds',
        'schedule': crontab(minute='*/1'),  # 每 1 分鐘執行一次
        'kwargs': {
            'server_id': None,  # None 表示處理所有 Server
        },
        'options': {
            'expires': 55,    # 任務超時 55 秒（避免與下次重疊）
        }
    },
    
    # 任務 11：Jenkins Workspace 自動存儲（每小時 15 分）
    'auto-store-jenkins-workspaces-hourly': {
        'task': 'api.tasks.auto_store_workspaces',
        'schedule': crontab(minute=15),  # ✅ 改為每小時 XX:15 執行（錯開 NAS I/O）
        'options': {
            'expires': 2700,   # 任務超時 45 分鐘（避免與下次重疊）
            # 'queue': 'default',  # 已移除：使用默認隊列 'celery'
        }
    },
    
    # 任務 12：Jenkins Builds 自動存儲到 NAS（每小時 45 分）
    'auto-store-jenkins-builds-every-hour': {
        'task': 'api.tasks.auto_store_jenkins_builds_task',
        'schedule': crontab(minute=45),  # ✅ 改為每小時 XX:45 執行（降低頻率，錯開 NAS I/O）
        'kwargs': {
            'limit': 100        # ✅ 每次處理 100 個 Builds（因頻率降低而增加批次）
        },
        'options': {
            'expires': 900,   # 任務超時 15 分鐘（避免與下次重疊）
            # 'queue': 'default',  # 已移除：使用默認隊列 'celery'
        }
    },
    
    # 任務 13：清理過期的 Ansible Inventory 快取（每天凌晨 5 點）
    'clean-expired-ansible-caches-daily': {
        'task': '清理過期的 Ansible Inventory 快取',
        'schedule': crontab(hour=5, minute=0),  # ✅ 改為每天 05:00 執行（延後到清晨）
        'options': {
            'expires': 1800,   # 任務超時 30 分鐘
            # 'queue': 'default',  # 已移除：使用默認隊列 'celery'
        }
    },
    
    # 任務 14：Jenkins Jobs 自動同步（每小時整點）
    'sync-jenkins-jobs-hourly': {
        'task': 'api.tasks.sync_all_jenkins_jobs_task',
        'schedule': crontab(minute=0),  # 每小時整點執行（00:00, 01:00, 02:00...）
        'kwargs': {
            'server_id': None  # None 表示處理所有在線 Server
        },
        'options': {
            'expires': 3300,   # 任務超時 55 分鐘（避免與下次重疊）
            # 'queue': 'default',  # 已移除：使用默認隊列 'celery'
        }
    },
    
    # 任務 15：Jenkins 資料一致性驗證（每天凌晨 2 點，僅檢測不清理）
    'validate-jenkins-data-daily': {
        'task': 'api.tasks.validate_jenkins_data',
        'schedule': crontab(hour=2, minute=0),  # ✅ 改為每天 02:00 執行（避免與其他任務衝突）
        'kwargs': {
            'server_id': None,         # None 表示處理所有在線 Server
            'auto_cleanup': False,     # 僅驗證，不自動清理（安全模式）
            'cleanup_nas': True,       # NAS 清理功能（當 auto_cleanup=True 時生效）
            'keep_recent_days': None,  # 使用 settings 配置（預設 7 天）
            'max_orphaned_threshold': None,  # 使用 settings 配置（預設 100）
            'dry_run': False,          # 實際執行模式
        },
        'options': {
            'expires': 1800,   # 任務超時 30 分鐘
        }
    },
    
    # 任務 16：Jenkins 孤立資料自動清理（每週日凌晨 1 點）
    'cleanup-orphaned-jenkins-data-weekly': {
        'task': 'api.tasks.validate_jenkins_data',
        'schedule': crontab(hour=1, minute=0, day_of_week=0),  # ✅ 改為每週日 01:00 執行（提前 3 小時）
        'kwargs': {
            'server_id': None,         # None 表示處理所有在線 Server
            'auto_cleanup': True,      # 自動清理孤立資料
            'cleanup_nas': True,       # ⭐ 同時清理 NAS Workspace 資料夾
            'keep_recent_days': None,  # 使用 settings 配置（預設 7 天）
            'max_orphaned_threshold': None,  # 使用 settings 配置（預設 100）
            'dry_run': False,          # 實際執行模式
        },
        'options': {
            'expires': 3600,   # 任務超時 1 小時
        }
    },
    
    # 任務 17：清理舊 Jenkins Builds（每月 1 號凌晨 5 點）
    'cleanup-old-jenkins-builds-monthly': {
        'task': 'api.tasks.cleanup_old_jenkins_builds_task',
        'schedule': crontab(hour=5, minute=0, day_of_month=1),  # 每月 1 號 05:00 執行
        'kwargs': {
            'days': 90,                # 只保留最近 90 天的 Builds
            'only_stored': True,       # 只清理已存儲到 NAS 的 Builds
            'exclude_patterns': [],    # 排除模式（空列表表示不排除）
            'dry_run': False,          # 實際執行模式
            'server_id': None,         # None 表示處理所有在線 Server
        },
        'options': {
            'expires': 7200,   # 任務超時 2 小時
        }
    },
    
    # 任務 18：補充缺失的 Fatal Error 分析（每小時 15 分）
    'auto-analyze-missing-fatal-errors-hourly': {
        'task': 'api.tasks.auto_analyze_missing_fatal_errors_task',
        'schedule': crontab(minute=15),  # 每小時 XX:15 執行
        'kwargs': {
            'limit': 50,       # 每次處理最多 50 個 Builds
            'days': 7          # 檢查最近 7 天的 Builds
        },
        'options': {
            'expires': 2700,   # 任務超時 45 分鐘（避免與下次重疊）
        }
    },
    
    # 任務 19：補充缺失的 Fatal Error 分析（每日批量處理，凌晨 2:30）
    'auto-analyze-missing-fatal-errors-daily': {
        'task': 'api.tasks.auto_analyze_missing_fatal_errors_task',
        'schedule': crontab(hour=2, minute=30),  # 每天 02:30 執行
        'kwargs': {
            'limit': 200,      # 每次處理最多 200 個 Builds
            'days': 30         # 檢查最近 30 天的 Builds
        },
        'options': {
            'expires': 5400,   # 任務超時 90 分鐘
        }
    },
    
    # 任務 20：NAS Jenkins Storage 清理（每週日凌晨 3 點）
    'cleanup-old-nas-jenkins-storage-weekly': {
        'task': 'api.tasks.cleanup_old_nas_jenkins_storage_task',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),  # 週日 03:00 執行
        'kwargs': {
            'max_age_days': 30,           # 清理超過 30 天的資料
            'dry_run': False,             # 正式執行模式
            'cpu_high_threshold': 80.0,   # CPU 上限 80%
            'cpu_low_threshold': 60.0,    # CPU 恢復閾值 60%
            'batch_size': 10,             # 每批 10 個資料夾
            'batch_delay': 2.0            # 批次間隔 2 秒
        },
        'options': {
            'expires': 14400,   # 任務超時 4 小時
        }
    },
    
    # 任務 21：Build 配置自動檢查（每 5 分鐘）
    'auto-validate-completed-builds-every-5-minutes': {
        'task': 'api.tasks.auto_validate_completed_builds',
        'schedule': crontab(minute='*/5'),  # 每 5 分鐘執行一次
        'kwargs': {
            'limit': 50,              # 每次最多檢查 50 個 Builds
            'days': 7,                # 只檢查最近 7 天的 Builds
            'priority_failed': True,  # 優先檢查失敗的 Build
        },
        'options': {
            'expires': 240,           # 任務超時 4 分鐘（避免與下次重疊）
        }
    },
    
    # ============================================================================
    # 🧠 智能自適應同步任務（可選啟用）
    # ============================================================================
    # 如果要啟用智能同步，請取消下面的註釋並停用標準的 sync-jenkins-builds-every-10-minutes
    # 智能版本會根據 CPU 負載自動調整執行策略，避免系統過載
    
    # 'sync-jenkins-builds-adaptive-every-10-minutes': {
    #     'task': 'api.tasks.sync_jenkins_builds_adaptive',
    #     'schedule': crontab(minute='*/10'),
    #     'kwargs': {
    #         'server_id': None,
    #         'max_builds_per_job': 20,
    #         'max_age_days': 30,
    #         'enable_cpu_monitoring': True,      # 啟用 CPU 監控
    #         'cpu_high_threshold': 85.0,         # CPU 高負載閾值
    #         'cpu_low_threshold': 60.0,          # CPU 低負載閾值
    #         'max_wait_seconds': 300,            # 最大等待時間（5 分鐘）
    #     },
    #     'options': {
    #         'expires': 540,  # 任務超時 9 分鐘
    #     }
    # },
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
