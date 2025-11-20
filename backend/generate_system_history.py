#!/usr/bin/env python
"""
生成系統監控歷史測試數據
用於展示時間範圍選擇器功能
"""
import os
import django
import random
from datetime import timedelta

# 設置 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from django.utils import timezone
from api.models import SystemMonitorHistory

def generate_history_data(days=7):
    """
    生成過去 N 天的系統監控歷史數據
    每 5 分鐘生成一筆記錄
    """
    now = timezone.now()
    start_time = now - timedelta(days=days)
    
    # 清空現有數據
    deleted_count = SystemMonitorHistory.objects.all().delete()[0]
    print(f'已清空 {deleted_count} 筆舊數據')
    
    # 生成數據
    records = []
    current_time = start_time
    base_cpu = 10  # CPU 基準值
    base_ram = 40  # RAM 基準值
    base_disk = 36  # 磁碟基準值
    
    count = 0
    while current_time <= now:
        # 模擬數據波動（使用正弦波 + 隨機噪聲）
        hour = current_time.hour
        
        # CPU: 白天使用率較高，晚上較低
        cpu_variation = 15 * abs(((hour - 12) / 12))  # 中午12點最低，午夜最高
        cpu_percent = base_cpu + cpu_variation + random.uniform(-5, 5)
        cpu_percent = max(0.1, min(100, cpu_percent))
        
        # RAM: 緩慢增長趨勢 + 小波動
        ram_percent = base_ram + random.uniform(-3, 3)
        ram_percent = max(20, min(80, ram_percent))
        
        # 磁碟: 幾乎不變
        disk_percent = base_disk + random.uniform(-0.1, 0.1)
        
        # 計算實際容量（假設）
        cpu_count = 8
        ram_total = 16.0
        disk_total = 100.0
        
        ram_used = ram_total * (ram_percent / 100)
        ram_available = ram_total - ram_used
        
        disk_used = disk_total * (disk_percent / 100)
        disk_free = disk_total - disk_used
        
        record = SystemMonitorHistory(
            timestamp=current_time,
            cpu_percent=cpu_percent,
            cpu_count=cpu_count,
            ram_percent=ram_percent,
            ram_total_gb=ram_total,
            ram_used_gb=ram_used,
            ram_available_gb=ram_available,
            disk_percent=disk_percent,
            disk_total_gb=disk_total,
            disk_used_gb=disk_used,
            disk_free_gb=disk_free,
        )
        records.append(record)
        
        count += 1
        current_time += timedelta(minutes=5)
        
        # 批量插入（每 100 筆）
        if len(records) >= 100:
            SystemMonitorHistory.objects.bulk_create(records)
            print(f'已生成 {count} 筆記錄...')
            records = []
    
    # 插入剩餘記錄
    if records:
        SystemMonitorHistory.objects.bulk_create(records)
    
    print(f'✅ 完成！總共生成 {count} 筆歷史數據')
    print(f'時間範圍: {start_time.strftime("%Y-%m-%d %H:%M")} ~ {now.strftime("%Y-%m-%d %H:%M")}')
    print(f'資料庫記錄總數: {SystemMonitorHistory.objects.count()}')

if __name__ == '__main__':
    import sys
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    print(f'開始生成過去 {days} 天的系統監控歷史數據...')
    generate_history_data(days)
