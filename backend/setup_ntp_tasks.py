#!/usr/bin/env python
"""
設置 NTP 定時任務
每 5 分鐘檢查一次 NTP 時間同步狀態
"""

import os
import django
import sys

# 設置 Django 環境
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from django_celery_beat.models import PeriodicTask, IntervalSchedule
import json

def setup_ntp_tasks():
    """設置 NTP 定時任務"""
    
    # 1. 創建 5 分鐘間隔
    interval_5min, created = IntervalSchedule.objects.get_or_create(
        every=5,
        period=IntervalSchedule.MINUTES,
    )
    if created:
        print(f"✓ 創建 5 分鐘間隔調度")
    
    # 2. 創建或更新 NTP 檢測任務
    task_name = 'NTP 時間同步檢測'
    task, created = PeriodicTask.objects.update_or_create(
        name=task_name,
        defaults={
            'interval': interval_5min,
            'task': 'api.tasks.check_ntp_sync_task',
            'enabled': True,
            'description': '每 5 分鐘檢測一次 NTP 時間同步狀態（10.10.10.51）',
        }
    )
    
    if created:
        print(f"✓ 創建定時任務: {task_name}")
    else:
        print(f"✓ 更新定時任務: {task_name}")
    
    print(f"  - 任務: api.tasks.check_ntp_sync_task")
    print(f"  - 間隔: 每 5 分鐘")
    print(f"  - 狀態: {'啟用' if task.enabled else '停用'}")
    
    # 顯示所有 NTP 相關任務
    print("\n所有 NTP 相關任務:")
    ntp_tasks = PeriodicTask.objects.filter(name__icontains='NTP')
    for task in ntp_tasks:
        print(f"  - {task.name}: {'啟用' if task.enabled else '停用'}")

if __name__ == '__main__':
    print("=" * 60)
    print("設置 NTP 定時任務")
    print("=" * 60)
    setup_ntp_tasks()
    print("\n" + "=" * 60)
    print("設置完成！")
    print("=" * 60)
