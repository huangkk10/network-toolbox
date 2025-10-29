#!/usr/bin/env python3
"""檢查 NAS 連線記錄"""
import os
import sys
import django

# 設定 Django 環境
sys.path.insert(0, '/home/owner/Codes/network-toolbox/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.models import NASConnectionLog
from django.utils import timezone
from datetime import timedelta

print('=' * 60)
print('NAS 連線記錄檢查')
print('=' * 60)

total_count = NASConnectionLog.objects.count()
print(f'\n總記錄數: {total_count}')

if total_count == 0:
    print('\n❌ 資料庫中沒有任何 NAS 連線記錄！')
    print('   可能原因：')
    print('   1. Cron 定時任務未啟動')
    print('   2. Celery 定時任務未啟動')
    print('   3. NAS 連線檢測失敗')
else:
    print('\n✅ 找到記錄，顯示最近 20 筆：')
    print('-' * 60)
    
    logs = NASConnectionLog.objects.order_by('-timestamp')[:20]
    for log in logs:
        status_icon = '✅' if log.status == 'success' else '❌'
        print(f'{status_icon} {log.timestamp.strftime("%Y-%m-%d %H:%M:%S")} | {log.status:7s} | {log.nas_ip} | {log.response_time:.2f}ms' if log.response_time else 'N/A')
    
    # 檢查時間分佈
    print('\n' + '=' * 60)
    print('時間分佈分析：')
    print('=' * 60)
    
    for days in [1, 7, 14]:
        start_time = timezone.now() - timedelta(days=days)
        count = NASConnectionLog.objects.filter(timestamp__gte=start_time).count()
        print(f'最近 {days:2d} 天: {count:4d} 筆記錄')
    
    # 檢查最新記錄時間
    latest = NASConnectionLog.objects.order_by('-timestamp').first()
    if latest:
        time_diff = timezone.now() - latest.timestamp
        minutes_ago = time_diff.total_seconds() / 60
        print(f'\n最新記錄時間: {latest.timestamp.strftime("%Y-%m-%d %H:%M:%S")}')
        print(f'距離現在: {int(minutes_ago)} 分鐘前')
        
        if minutes_ago > 10:
            print(f'\n⚠️  警告：最新記錄已經是 {int(minutes_ago)} 分鐘前了！')
            print('   定時任務可能已停止運行。')
        else:
            print('\n✅ 定時任務運行正常（最近 10 分鐘內有新記錄）')
    
    # 檢查成功率
    print('\n' + '=' * 60)
    print('成功率統計：')
    print('=' * 60)
    
    for days in [1, 7, 14]:
        start_time = timezone.now() - timedelta(days=days)
        logs_period = NASConnectionLog.objects.filter(timestamp__gte=start_time)
        total = logs_period.count()
        success = logs_period.filter(status='success').count()
        failed = logs_period.filter(status='failed').count()
        rate = (success / total * 100) if total > 0 else 0
        
        print(f'最近 {days:2d} 天: 成功 {success:3d} | 失敗 {failed:3d} | 成功率 {rate:6.2f}%')

print('\n' + '=' * 60)
