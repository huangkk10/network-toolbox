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
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = config('TZ', default='Asia/Taipei')
USE_I18N = True
USE_TZ = False  # 關閉 UTC 時區轉換，直接使用本地時區

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ==================== Celery 配置 ====================
# Redis 連接設置
REDIS_HOST = config('REDIS_HOST', default='redis')
REDIS_PORT = config('REDIS_PORT', default='6379')

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
}

# CORS settings
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost",
]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False  # 安全性考量
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
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost",
]

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
        # Root logger
        '': {
            'handlers': ['console', 'daily_file', 'daily_error_file'],
            'level': 'INFO',
        },
    },
}
