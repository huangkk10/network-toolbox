#!/usr/bin/env python3
"""
回填現有 DHCP 日誌的 client_type 資訊

這個腳本會重新解析資料庫中現有日誌的 raw 欄位，
並更新 client_type, boot_stage, vendor_class, user_class 欄位。
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')

import django
django.setup()

from api.models import DHCPLog
from api.services import WindowsDHCPLogParser
from django.db import transaction

print("=" * 80)
print("開始回填 DHCP 日誌的 client_type 資訊")
print("=" * 80)

# 統計資訊
total_logs = DHCPLog.objects.count()
updated_count = 0
ipxe_count = 0
pxe_count = 0
winpe_count = 0
os_count = 0
unknown_count = 0

print(f"\n總日誌數: {total_logs}")
print("\n開始處理...")

# 批次處理（每次 1000 筆）
batch_size = 1000
for offset in range(0, total_logs, batch_size):
    print(f"\n處理第 {offset + 1} - {min(offset + batch_size, total_logs)} 筆...")
    
    logs = DHCPLog.objects.all()[offset:offset + batch_size]
    
    with transaction.atomic():
        for log in logs:
            try:
                # 重新解析原始日誌
                parsed = WindowsDHCPLogParser.parse_log_lines([log.raw], limit=1)
                
                if parsed and len(parsed) > 0:
                    parsed_log = parsed[0]
                    
                    # 更新欄位
                    log.client_type = parsed_log.get('client_type', 'Unknown')
                    log.boot_stage = parsed_log.get('boot_stage', '')
                    log.vendor_class = parsed_log.get('vendor_class', '')
                    log.user_class = parsed_log.get('user_class', '')
                    log.save()
                    
                    updated_count += 1
                    
                    # 統計客戶端類型
                    if log.client_type == 'iPXE':
                        ipxe_count += 1
                    elif log.client_type == 'PXE':
                        pxe_count += 1
                    elif log.client_type == 'WinPE':
                        winpe_count += 1
                    elif log.client_type == 'OS':
                        os_count += 1
                    else:
                        unknown_count += 1
            
            except Exception as e:
                print(f"  警告: 解析日誌失敗 (ID: {log.id}): {str(e)}")
                continue
    
    print(f"  已更新: {updated_count} 筆")

print("\n" + "=" * 80)
print("回填完成！")
print("=" * 80)
print(f"\n更新統計:")
print(f"  總更新數: {updated_count}")
print(f"  iPXE:     {ipxe_count} 筆")
print(f"  PXE:      {pxe_count} 筆")
print(f"  WinPE:    {winpe_count} 筆")
print(f"  OS:       {os_count} 筆")
print(f"  Unknown:  {unknown_count} 筆")

# 驗證結果
print("\n" + "=" * 80)
print("驗證結果:")
print("=" * 80)

ipxe_in_db = DHCPLog.objects.filter(client_type='iPXE').count()
pxe_in_db = DHCPLog.objects.filter(client_type='PXE').count()
winpe_in_db = DHCPLog.objects.filter(client_type='WinPE').count()
os_in_db = DHCPLog.objects.filter(client_type='OS').count()

print(f"資料庫中的客戶端類型統計:")
print(f"  iPXE:  {ipxe_in_db} 筆")
print(f"  PXE:   {pxe_in_db} 筆")
print(f"  WinPE: {winpe_in_db} 筆")
print(f"  OS:    {os_in_db} 筆")

if ipxe_in_db > 0:
    print("\n✓ 成功！現在可以在前端篩選 iPXE 日誌了！")
    print("\n前端操作步驟:")
    print("  1. 訪問 DHCP Server 分析 → 日誌")
    print("  2. 客戶端類型選擇 'iPXE'")
    print(f"  3. 應該會看到 {ipxe_in_db} 筆 iPXE 日誌")
else:
    print("\n⚠ 注意: 資料庫中沒有 iPXE 日誌")
    print("  可能原因:")
    print("  1. DHCP Server 沒有記錄 iPXE 啟動事件")
    print("  2. 日誌時間範圍內沒有 iPXE 活動")
    print("  3. DHCP 日誌不包含 DHCP Options 資訊")

print("=" * 80)
