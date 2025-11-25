#!/usr/bin/env python
"""
設置 NTP 自動同步定時任務
每天凌晨 3 點執行一次時間同步
"""

import os
import django
import sys

# 設置 Django 環境
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from django_celery_beat.models import PeriodicTask, CrontabSchedule
import json

def setup_ntp_sync_task():
    """設置 NTP 自動同步定時任務"""
    
    # 1. 創建每天凌晨 3 點的排程
    schedule, created = CrontabSchedule.objects.get_or_create(
        minute='0',
        hour='3',
        day_of_week='*',
        day_of_month='*',
        month_of_year='*',
    )
    if created:
        print(f"✓ 創建排程: 每天凌晨 3:00")
    else:
        print(f"✓ 使用現有排程: 每天凌晨 3:00")
    
    # 2. 創建或更新 NTP 自動同步任務
    task_name = 'NTP 時間自動同步（每天凌晨）'
    task, created = PeriodicTask.objects.update_or_create(
        name=task_name,
        defaults={
            'crontab': schedule,
            'task': 'api.tasks.sync_ntp_time_task',
            'enabled': True,
            'description': '每天凌晨 3 點自動檢查並同步 NTP 時間（如果偏移 > 200ms）',
        }
    )
    
    if created:
        print(f"✓ 創建定時任務: {task_name}")
    else:
        print(f"✓ 更新定時任務: {task_name}")
    
    print(f"  - 任務: api.tasks.sync_ntp_time_task")
    print(f"  - 排程: 每天凌晨 3:00")
    print(f"  - 狀態: {'啟用' if task.enabled else '停用'}")
    print(f"  - 描述: {task.description}")
    
    # 顯示所有 NTP 相關任務
    print("\n所有 NTP 相關任務:")
    ntp_tasks = PeriodicTask.objects.filter(name__icontains='NTP')
    for task in ntp_tasks:
        status = '✅ 啟用' if task.enabled else '⭕ 停用'
        print(f"  - {task.name}: {status}")
        if hasattr(task, 'crontab') and task.crontab:
            print(f"    排程: {task.crontab}")
        elif hasattr(task, 'interval') and task.interval:
            print(f"    間隔: {task.interval}")

if __name__ == '__main__':
    print("=" * 60)
    print("設置 NTP 自動同步定時任務")
    print("=" * 60)
    setup_ntp_sync_task()
    print("\n" + "=" * 60)
    print("設置完成！")
    print("=" * 60)
    print("\n⚠️  注意事項：")
    print("  1. 任務會在每天凌晨 3 點執行")
    print("  2. 只有當時間偏移 > 200ms 時才會實際同步")
    print("  3. 距離上次同步至少需間隔 30 分鐘")
    print("  4. 執行同步需要 sudo 權限，請確保 Django 容器已配置")
    print("\n💡 手動測試執行：")
    print("  docker exec nt-django python -c \"")
    print("  from api.tasks import sync_ntp_time_task; ")
    print("  result = sync_ntp_time_task(); ")
    print("  print(result)\"")
    print("\n📊 查看執行記錄：")
    print("  訪問「系統監控」頁面 → 查看任務執行記錄")
    print("")
