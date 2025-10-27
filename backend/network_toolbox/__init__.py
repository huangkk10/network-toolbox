"""
Network Toolbox Django 專案初始化

確保 Celery 在 Django 啟動時自動載入
"""

# 導入 Celery 應用，確保在 Django 啟動時載入
from .celery import app as celery_app

__all__ = ('celery_app',)
