#!/usr/bin/env python
"""
NTP 時間同步測試腳本
用於測試 NTP 服務和創建初始測試數據
"""

import os
import django
import sys
from datetime import datetime, timedelta

# 設置 Django 環境
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.models import NTPSyncLog
from api.ntp_service import check_ntp_sync
from django.utils import timezone

def test_ntp_sync():
    """測試 NTP 同步功能"""
    print("=" * 60)
    print("NTP 時間同步測試")
    print("=" * 60)
    
    # 測試 NTP 同步
    print("\n1. 測試 NTP 同步（10.10.10.51）...")
    result = check_ntp_sync('10.10.10.51')
    
    print(f"\n同步結果：")
    print(f"  狀態: {result['status']}")
    print(f"  NTP Server: {result['ntp_server']}")
    
    if result['status'] == 'success':
        print(f"  響應時間: {result['response_time']} ms")
        print(f"  時間偏移: {result['offset']} ms")
        print(f"  Stratum: {result['stratum']}")
        if result['jitter']:
            print(f"  Jitter: {result['jitter']} ms")
    else:
        print(f"  錯誤訊息: {result['error_message']}")
    
    # 創建測試記錄
    print("\n2. 創建測試記錄到資料庫...")
    log = NTPSyncLog.objects.create(
        timestamp=timezone.now(),
        status=result['status'],
        ntp_server=result['ntp_server'],
        response_time=result['response_time'],
        offset=result['offset'],
        stratum=result['stratum'],
        jitter=result['jitter'],
        error_message=result['error_message']
    )
    print(f"  ✓ 記錄已創建 (ID: {log.id})")
    
    # 統計資訊
    print("\n3. 資料庫統計...")
    total_count = NTPSyncLog.objects.count()
    success_count = NTPSyncLog.objects.filter(status='success').count()
    failed_count = NTPSyncLog.objects.filter(status='failed').count()
    
    print(f"  總記錄數: {total_count}")
    print(f"  成功: {success_count}")
    print(f"  失敗: {failed_count}")
    
    if success_count > 0:
        success_rate = (success_count / total_count) * 100
        print(f"  成功率: {success_rate:.2f}%")
    
    print("\n" + "=" * 60)
    print("測試完成！")
    print("=" * 60)

def create_sample_data():
    """創建樣本數據（過去24小時，每5分鐘一筆）"""
    print("\n創建樣本數據（過去24小時）...")
    
    now = timezone.now()
    records_created = 0
    
    # 過去24小時，每5分鐘一筆記錄
    for i in range(288):  # 24小時 * 60分鐘 / 5分鐘 = 288筆
        timestamp = now - timedelta(minutes=i * 5)
        
        # 檢查是否已存在
        if NTPSyncLog.objects.filter(timestamp=timestamp).exists():
            continue
        
        # 執行 NTP 同步（可能會很慢，所以只創建模擬數據）
        import random
        
        # 90% 成功率
        if random.random() < 0.9:
            status = 'success'
            response_time = round(random.uniform(10, 50), 2)
            offset = round(random.uniform(-10, 10), 3)
            stratum = random.choice([1, 2, 3])
            jitter = round(random.uniform(0, 5), 3)
            error_message = ''
        else:
            status = 'failed'
            response_time = None
            offset = None
            stratum = None
            jitter = None
            error_message = 'Timeout'
        
        NTPSyncLog.objects.create(
            timestamp=timestamp,
            status=status,
            ntp_server='10.10.10.51',
            response_time=response_time,
            offset=offset,
            stratum=stratum,
            jitter=jitter,
            error_message=error_message
        )
        records_created += 1
    
    print(f"✓ 創建了 {records_created} 筆樣本數據")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='NTP 時間同步測試工具')
    parser.add_argument('--sample', action='store_true', help='創建樣本數據')
    args = parser.parse_args()
    
    if args.sample:
        create_sample_data()
    else:
        test_ntp_sync()
