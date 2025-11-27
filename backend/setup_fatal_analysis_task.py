#!/usr/bin/env python
"""
設置 Fatal Error 補分析定時任務

此腳本會在 django_celery_beat 中創建/更新定時任務配置
"""

import os
import sys
import django

# 設置 Django 環境
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from django_celery_beat.models import PeriodicTask, CrontabSchedule
import json


def setup_fatal_analysis_task():
    """設置 Fatal Error 補分析定時任務"""
    
    print('=' * 70)
    print('🔧 設置 Fatal Error 補分析定時任務')
    print('=' * 70)
    print()
    
    # 創建 Crontab Schedule（每小時執行一次，在每小時的 15 分）
    schedule_hourly, created = CrontabSchedule.objects.get_or_create(
        minute='15',
        hour='*',
        day_of_week='*',
        day_of_month='*',
        month_of_year='*',
    )
    
    if created:
        print('✅ 創建 Crontab Schedule (每小時 15 分)')
    else:
        print('ℹ️  Crontab Schedule 已存在 (每小時 15 分)')
    
    # 創建或更新定時任務
    task_name = 'auto-analyze-missing-fatal-errors-hourly'
    
    task, created = PeriodicTask.objects.get_or_create(
        name=task_name,
        defaults={
            'task': 'api.tasks.auto_analyze_missing_fatal_errors_task',
            'crontab': schedule_hourly,
            'enabled': True,
            'kwargs': json.dumps({
                'limit': 20,  # 每次處理 20 個
                'days': 7     # 檢查最近 7 天
            }),
            'description': '自動補充缺失的 Fatal Error 分析（每小時執行）'
        }
    )
    
    if created:
        print(f'✅ 創建定時任務: {task_name}')
    else:
        # 更新現有任務
        task.task = 'api.tasks.auto_analyze_missing_fatal_errors_task'
        task.crontab = schedule_hourly
        task.enabled = True
        task.kwargs = json.dumps({
            'limit': 20,
            'days': 7
        })
        task.description = '自動補充缺失的 Fatal Error 分析（每小時執行）'
        task.save()
        print(f'🔄 更新定時任務: {task_name}')
    
    print()
    print('任務配置:')
    print(f'  Task: {task.task}')
    print(f'  Schedule: 每小時的 15 分')
    print(f'  Enabled: {task.enabled}')
    print(f'  參數: limit=20, days=7')
    print()
    
    # 也創建一個每天執行的版本（處理更多 Builds）
    schedule_daily, created = CrontabSchedule.objects.get_or_create(
        minute='30',
        hour='2',  # 凌晨 2:30
        day_of_week='*',
        day_of_month='*',
        month_of_year='*',
    )
    
    if created:
        print('✅ 創建 Crontab Schedule (每天凌晨 2:30)')
    else:
        print('ℹ️  Crontab Schedule 已存在 (每天凌晨 2:30)')
    
    task_name_daily = 'auto-analyze-missing-fatal-errors-daily'
    
    task_daily, created = PeriodicTask.objects.get_or_create(
        name=task_name_daily,
        defaults={
            'task': 'api.tasks.auto_analyze_missing_fatal_errors_task',
            'crontab': schedule_daily,
            'enabled': True,
            'kwargs': json.dumps({
                'limit': 100,  # 每天處理更多
                'days': 30     # 檢查最近 30 天
            }),
            'description': '自動補充缺失的 Fatal Error 分析（每日批量）'
        }
    )
    
    if created:
        print(f'✅ 創建定時任務: {task_name_daily}')
    else:
        task_daily.task = 'api.tasks.auto_analyze_missing_fatal_errors_task'
        task_daily.crontab = schedule_daily
        task_daily.enabled = True
        task_daily.kwargs = json.dumps({
            'limit': 100,
            'days': 30
        })
        task_daily.description = '自動補充缺失的 Fatal Error 分析（每日批量）'
        task_daily.save()
        print(f'🔄 更新定時任務: {task_name_daily}')
    
    print()
    print('任務配置:')
    print(f'  Task: {task_daily.task}')
    print(f'  Schedule: 每天凌晨 2:30')
    print(f'  Enabled: {task_daily.enabled}')
    print(f'  參數: limit=100, days=30')
    print()
    
    print('=' * 70)
    print('✅ Fatal Error 補分析定時任務設置完成！')
    print('=' * 70)
    print()
    print('已創建兩個定時任務：')
    print('  1. 每小時執行（處理 20 個，最近 7 天）')
    print('  2. 每天凌晨執行（處理 100 個，最近 30 天）')
    print()
    print('查看所有定時任務：')
    print('  docker exec nt-django python manage.py shell -c "')
    print('  from django_celery_beat.models import PeriodicTask')
    print('  tasks = PeriodicTask.objects.filter(name__icontains=\"fatal\")')
    print('  for t in tasks: print(f\"{t.name}: {t.enabled}\")')
    print('  "')
    print()


if __name__ == '__main__':
    setup_fatal_analysis_task()
