#!/usr/bin/env python
"""
同步 Celery Beat 定時任務到資料庫

這個腳本會將 celery.py 中定義的定時任務同步到資料庫中
使用 django_celery_beat 的 DatabaseScheduler
"""

import os
import sys
import django

# 設定 Django 環境
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from django_celery_beat.models import PeriodicTask, CrontabSchedule
import json


def create_or_update_crontab(minute='*', hour='*', day_of_week='*', day_of_month='*', month_of_year='*'):
    """創建或取得 Crontab Schedule"""
    schedule, created = CrontabSchedule.objects.get_or_create(
        minute=minute,
        hour=hour,
        day_of_week=day_of_week,
        day_of_month=day_of_month,
        month_of_year=month_of_year,
        timezone='Asia/Taipei'
    )
    return schedule


def setup_nas_connection_task():
    """設置 NAS 連線檢測定時任務（每 5 分鐘）"""
    
    print('正在設置 NAS 連線檢測任務...')
    
    # 創建 Crontab Schedule（每 5 分鐘）
    schedule = create_or_update_crontab(minute='*/5')
    
    # 創建或更新 Periodic Task
    task, created = PeriodicTask.objects.get_or_create(
        name='check-nas-connection-every-5-minutes',
        defaults={
            'task': 'api.tasks.check_nas_connection_task',
            'crontab': schedule,
            'enabled': True,
            'description': 'NAS 連線檢測任務 - 每 5 分鐘執行一次',
        }
    )
    
    if not created:
        # 更新現有任務
        task.task = 'api.tasks.check_nas_connection_task'
        task.crontab = schedule
        task.enabled = True
        task.description = 'NAS 連線檢測任務 - 每 5 分鐘執行一次'
        task.save()
        print(f'  ✅ 已更新任務: {task.name}')
    else:
        print(f'  ✅ 已創建任務: {task.name}')
    
    return task


def setup_dhcp_sync_task():
    """設置 DHCP 日誌同步任務（每 5 分鐘）"""
    
    print('正在設置 DHCP 日誌同步任務...')
    
    # 創建 Crontab Schedule（每 5 分鐘）
    schedule = create_or_update_crontab(minute='*/5')
    
    # 創建或更新 Periodic Task
    task, created = PeriodicTask.objects.get_or_create(
        name='sync-dhcp-logs-every-5-minutes',
        defaults={
            'task': 'api.tasks.sync_dhcp_logs_task',
            'crontab': schedule,
            'enabled': True,
            'kwargs': json.dumps({'server_id': 1, 'limit': 500}),
            'description': 'DHCP 日誌同步任務 - 每 5 分鐘執行一次',
        }
    )
    
    if not created:
        task.task = 'api.tasks.sync_dhcp_logs_task'
        task.crontab = schedule
        task.enabled = True
        task.kwargs = json.dumps({'server_id': 1, 'limit': 500})
        task.description = 'DHCP 日誌同步任務 - 每 5 分鐘執行一次'
        task.save()
        print(f'  ✅ 已更新任務: {task.name}')
    else:
        print(f'  ✅ 已創建任務: {task.name}')
    
    return task


def setup_cleanup_logs_task():
    """設置日誌清理任務（每天凌晨 3 點）"""
    
    print('正在設置日誌清理任務...')
    
    # 創建 Crontab Schedule（每天 03:00）
    schedule = create_or_update_crontab(minute='0', hour='3')
    
    # 創建或更新 Periodic Task
    task, created = PeriodicTask.objects.get_or_create(
        name='cleanup-old-dhcp-logs-daily',
        defaults={
            'task': 'api.tasks.cleanup_old_logs_task',
            'crontab': schedule,
            'enabled': True,
            'kwargs': json.dumps({'days': 7}),
            'description': 'DHCP 日誌清理任務 - 每天凌晨 3 點執行',
        }
    )
    
    if not created:
        task.task = 'api.tasks.cleanup_old_logs_task'
        task.crontab = schedule
        task.enabled = True
        task.kwargs = json.dumps({'days': 7})
        task.description = 'DHCP 日誌清理任務 - 每天凌晨 3 點執行'
        task.save()
        print(f'  ✅ 已更新任務: {task.name}')
    else:
        print(f'  ✅ 已創建任務: {task.name}')
    
    return task


def setup_oui_update_task():
    """設置 OUI 資料庫更新任務（每月 1 號凌晨 2 點）"""
    
    print('正在設置 OUI 資料庫更新任務...')
    
    # 創建 Crontab Schedule（每月 1 號 02:00）
    schedule = create_or_update_crontab(minute='0', hour='2', day_of_month='1')
    
    # 創建或更新 Periodic Task
    task, created = PeriodicTask.objects.get_or_create(
        name='update-oui-database-monthly',
        defaults={
            'task': 'api.tasks.update_oui_database_task',
            'crontab': schedule,
            'enabled': True,
            'kwargs': json.dumps({'source': 0, 'backup': True}),
            'description': 'OUI 資料庫更新任務 - 每月 1 號凌晨 2 點執行',
        }
    )
    
    if not created:
        task.task = 'api.tasks.update_oui_database_task'
        task.crontab = schedule
        task.enabled = True
        task.kwargs = json.dumps({'source': 0, 'backup': True})
        task.description = 'OUI 資料庫更新任務 - 每月 1 號凌晨 2 點執行'
        task.save()
        print(f'  ✅ 已更新任務: {task.name}')
    else:
        print(f'  ✅ 已創建任務: {task.name}')
    
    return task


def main():
    """主函數：設置所有定時任務"""
    
    print('=' * 60)
    print('開始同步 Celery Beat 定時任務到資料庫')
    print('=' * 60)
    print()
    
    try:
        # 設置所有任務
        setup_nas_connection_task()
        setup_dhcp_sync_task()
        setup_cleanup_logs_task()
        setup_oui_update_task()
        
        print()
        print('=' * 60)
        print('✅ 所有定時任務已成功設置！')
        print('=' * 60)
        print()
        
        # 顯示當前所有已啟用的任務
        print('當前已啟用的定時任務：')
        print('-' * 60)
        
        tasks = PeriodicTask.objects.filter(enabled=True).order_by('name')
        for task in tasks:
            schedule_info = ''
            if task.crontab:
                schedule_info = f'Crontab: {task.crontab}'
            elif task.interval:
                schedule_info = f'Interval: {task.interval}'
            
            print(f'  📋 {task.name}')
            print(f'     Task: {task.task}')
            print(f'     Schedule: {schedule_info}')
            print(f'     Description: {task.description or "N/A"}')
            print()
        
        print('=' * 60)
        print('提示：')
        print('  1. 重啟 Celery Beat 以載入新的任務配置')
        print('     docker compose restart celery_beat')
        print()
        print('  2. 重啟 Celery Worker 以確保任務能正常執行')
        print('     docker compose restart celery_worker')
        print('=' * 60)
        
    except Exception as e:
        print()
        print('=' * 60)
        print(f'❌ 錯誤：{str(e)}')
        print('=' * 60)
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
