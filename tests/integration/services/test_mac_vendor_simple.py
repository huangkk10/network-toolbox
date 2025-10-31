#!/usr/bin/env python3
"""
簡單測試 MAC 廠商識別功能
直接在容器內運行
"""

import os
import sys

# 添加當前目錄到路徑
sys.path.insert(0, '/app')

# 設置 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')

import django
django.setup()

from api.utils.mac_vendor import get_vendor_from_mac, get_vendor_stats

# 測試資料庫狀態
print('=' * 60)
print('OUI 資料庫狀態')
print('=' * 60)

stats = get_vendor_stats()
for key, value in stats.items():
    print(f"{key}: {value}")

print('\n' + '=' * 60)
print('測試 MAC 地址識別')
print('=' * 60)

# 測試案例
test_macs = [
    '00:50:BA:11:22:33',  # D-Link
    'CC:46:D6:AA:BB:CC',  # Cisco
    '48:AD:08:11:22:33',  # Huawei
    '3C:D9:2B:44:55:66',  # HP
    '58:11:22:33:44:55',  # Realtek
    '80:09:02:11:22:33',  # Intel
    'FF:FF:FF:AA:BB:CC',  # Unknown
]

for mac in test_macs:
    vendor = get_vendor_from_mac(mac)
    print(f"MAC: {mac:20} => Vendor: {vendor}")

print('\n✓ 測試完成')
