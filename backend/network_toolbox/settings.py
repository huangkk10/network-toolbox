"""
Django settings for network_toolbox project.
"""

import os
from pathlib import Path
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'django_celery_beat',      # Celery Beat 定時任務管理
    'django_celery_results',   # Celery 任務結果儲存
    'api',  # Our API app
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # CORS must be before CommonMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'api.middleware.website_usage.WebsiteUsageMiddleware',  # 網站使用統計
]

ROOT_URLCONF = 'network_toolbox.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'network_toolbox.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        'NAME': config('DB_NAME', default='network_toolbox'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default='postgres123'),
    }
}

# Password validation
# 已移除 NumericPasswordValidator 以允許純數字密碼
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,  # 最少 8 位
        }
    },
    # 已註解：允許常見密碼（開發階段方便測試）
    # {
    #     'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    # },
    # 已移除：允許純數字密碼
    # {
    #     'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    # },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = config('TZ', default='Asia/Taipei')  # 顯示時區：台北
USE_I18N = True
USE_TZ = True  # 啟用時區轉換，資料庫儲存 UTC，顯示時轉換為 TIME_ZONE

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ==================== Redis 緩存配置 ====================
# Redis 連接設置
REDIS_HOST = config('REDIS_HOST', default='redis')
REDIS_PORT = config('REDIS_PORT', default='6379')
REDIS_DB = config('REDIS_DB', default='0')

# Django Cache 配置（使用 Redis）
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'IGNORE_EXCEPTIONS': True,  # 緩存失敗不影響主要功能
        },
        'KEY_PREFIX': 'nt',  # Network Toolbox 緩存鍵前綴
        'TIMEOUT': 3600,  # 默認 1 小時過期
    }
}

# Session 使用 Redis 儲存
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'


# ==================== Celery 配置 ====================
# Celery Broker（消息隊列）
CELERY_BROKER_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/1'

# Celery Result Backend（任務結果儲存）
# 使用 PostgreSQL 存儲任務結果，便於查詢和追蹤
CELERY_RESULT_BACKEND = 'django-db'
CELERY_CACHE_BACKEND = 'django-cache'

# Celery Beat 定時任務調度器
# 使用資料庫存儲排程，可透過 Django Admin 動態修改
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# 時區設置
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = False

# 任務序列化格式
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']

# 任務結果過期時間（1 天）
CELERY_RESULT_EXPIRES = 86400

# Worker 配置
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # 一次只取一個任務
CELERY_WORKER_MAX_TASKS_PER_CHILD = 50  # 每個 Worker 處理 50 個任務後重啟

# 任務追蹤
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_SEND_SENT_EVENT = True

# 任務結果儲存設置
CELERY_RESULT_EXTENDED = True  # 儲存完整的任務結果資訊


# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',  # 開發階段允許所有請求
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    # ✅ 時區設定：使用 Django 的 TIME_ZONE 設定
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',  # 輸出格式
    'DATETIME_INPUT_FORMATS': ['iso-8601'],   # 輸入格式
}

# CORS settings
# 開發環境：允許所有來源（生產環境應該限制特定域名）
CORS_ALLOW_ALL_ORIGINS = True  # 開發環境設為 True，方便從任何 IP 訪問
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# CSRF settings
# 開發環境：信任所有來源（生產環境應該限制特定域名）
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost",
    "http://10.252.170.171",  # 添加您的伺服器 IP
]

# 開發環境：禁用 CSRF 驗證（僅用於開發，生產環境必須啟用）
# 注意：這僅在開發環境中使用，生產環境應該移除此設定
if DEBUG:
    # 對於開發環境，我們可以放寬 CSRF 限制
    # 但仍保留 CSRF middleware 以確保 CSRF token 可用
    pass

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} | {name} | {funcName} | Line {lineno} | {message}',
            'style': '{',
        },
        'simple': {
            'format': '[{levelname}] {asctime} {name}: {message}',
            'style': '{',
        },
        'detailed': {
            'format': '[{levelname}] {asctime} | PID:{process:d} | Thread:{thread:d} | {name} | {funcName} | Line {lineno} | {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        # 按日期分割的一般 log（每天午夜輪替，保留 30 天）
        'daily_file': {
            'level': 'INFO',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': '/app/logs/django.log',
            'when': 'midnight',
            'interval': 1,
            'backupCount': 30,  # 保留 30 天
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
        # 按日期分割的錯誤 log（保留 60 天）
        'daily_error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': '/app/logs/django_error.log',
            'when': 'midnight',
            'interval': 1,
            'backupCount': 60,  # 錯誤 log 保留更久
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
        # DHCP 操作專用 log
        'dhcp_operations_file': {
            'level': 'INFO',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': '/app/logs/dhcp_operations.log',
            'when': 'midnight',
            'interval': 1,
            'backupCount': 15,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
        # API 訪問記錄（輕量級）
        'api_access_file': {
            'level': 'INFO',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': '/app/logs/api_access.log',
            'when': 'midnight',
            'interval': 1,
            'backupCount': 7,  # API 訪問只保留 7 天
            'formatter': 'simple',
            'encoding': 'utf-8',
        },
        # Debug 詳細日誌（保留 3 天，用於調試）
        'debug_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': '/app/logs/debug.log',
            'when': 'midnight',
            'interval': 1,
            'backupCount': 3,  # Debug log 只保留 3 天
            'formatter': 'detailed',
            'encoding': 'utf-8',
        },
    },
    'loggers': {
        # API Views
        'api.views': {
            'handlers': ['console', 'daily_file', 'daily_error_file', 'api_access_file'],
            'level': 'INFO',
            'propagate': True,
        },
        # Django 核心
        'django': {
            'handlers': ['console', 'daily_file', 'daily_error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        # Django Request（API 訪問）
        'django.request': {
            'handlers': ['console', 'daily_file', 'api_access_file'],
            'level': 'WARNING',
            'propagate': False,
        },
        # DHCP 相關操作 - 只記錄到 django.log，不記錄到 dhcp_operations.log
        # dhcp_operations.log 專門用於存儲真實的 DHCP Server 日誌
        'api.services': {
            'handlers': ['console', 'daily_file', 'daily_error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        # Library 工具模組（包含 log_parser）- 啟用 DEBUG
        'library.utils': {
            'handlers': ['console', 'debug_file', 'daily_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        # Root logger
        '': {
            'handlers': ['console', 'daily_file', 'daily_error_file'],
            'level': 'INFO',
        },
    },
}


# ==================== Jenkins 整合配置 ====================
# NAS 掛載路徑配置
NAS_MOUNT_PATH = config('NAS_MOUNT_PATH', default='/mnt/mdt')

# Jenkins 存儲路徑結構：{NAS_MOUNT_PATH}/Team/PQ1-3/tool/jenkins_test_storage/{jenkins_ip}/{job_name}/{build_number}/
JENKINS_STORAGE_BASE_PATH = os.path.join(NAS_MOUNT_PATH, 'Team', 'PQ1-3', 'tool', 'jenkins_test_storage')

# Jenkins 配置緩存時間（秒）
JENKINS_CONFIG_CACHE_TTL = 1800  # 30 分鐘
JENKINS_LOG_CACHE_TTL = 3600  # 1 小時
JENKINS_DB_QUERY_CACHE_TTL = 300  # 5 分鐘

# Jenkins API 請求超時設置
JENKINS_API_TIMEOUT = 30  # 30 秒
JENKINS_API_RETRY_TIMES = 3  # 重試次數

# Jenkins 自動存儲策略配置
JENKINS_STORAGE_POLICY = {
    # 基本開關
    'auto_store': True,                      # 是否啟用自動存儲（默認：啟用）
    
    # 存儲內容選擇
    'store_workspace': True,                 # 存儲 Workspace（默認：是）
    'store_config': False,                   # 存儲 config.xml（默認：否，待實現）
    'store_logs': False,                     # 存儲日誌（默認：否，待實現）
    
    # 存儲條件過濾
    'store_results': ['SUCCESS', 'FAILURE', 'UNSTABLE', 'ABORTED'],  # 只存儲這些結果的 Builds
                                                           # 選項：SUCCESS, FAILURE, UNSTABLE, ABORTED, NOT_BUILT
                                                           # 設為 None 或空列表表示存儲所有結果
    
    # 容量限制
    'max_workspace_size_mb': 500,            # 單個 Workspace 最大大小（MB），超過則跳過
    'retention_days': 90,                    # 保留天數（超過則清理，0 表示永久保留）
    
    # 定時任務設置
    'scan_interval_minutes': 30,             # 掃描間隔（分鐘）- 由 Celery Beat 控制
    'batch_size': 50,                        # 每次掃描處理的最大 Builds 數量（已從 20 改為 50）
}

