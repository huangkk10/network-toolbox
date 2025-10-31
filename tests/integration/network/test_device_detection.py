#!/usr/bin/env python
"""測試設備類型識別功能"""

import os
import sys
import django

# 設置 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
sys.path.insert(0, '/app')
django.setup()

from api.models import DHCPLease
from api.utils.device_type_detector import detect_device_type, is_switch, is_network_device

print('=== 設備類型識別測試 ===\n')

# 獲取所有活躍的租約（最多 20 筆）
leases = DHCPLease.objects.filter(is_active=True)[:20]

if not leases:
    print('❌ 沒有找到活躍的租約資料')
    print('\n嘗試獲取所有租約...')
    leases = DHCPLease.objects.all()[:20]
    if not leases:
        print('❌ 資料庫中完全沒有租約資料')
        sys.exit(1)

print(f'📊 找到 {leases.count()} 筆租約\n')

# 統計各類設備數量
device_stats = {}
network_devices = []
switches = []

for lease in leases:
    result = detect_device_type(lease.mac_address, lease.hostname or '')
    device_type = result['type']
    
    # 統計
    device_stats[device_type] = device_stats.get(device_type, 0) + 1
    
    # 記錄網路設備
    if is_network_device(lease.mac_address, lease.hostname or ''):
        network_devices.append(lease)
    
    # 記錄 Switch
    if is_switch(lease.mac_address, lease.hostname or ''):
        switches.append(lease)
    
    # 顯示識別結果
    print(f'{result["icon"]} {lease.ip_address:15s} | {lease.mac_address:17s} | {lease.hostname or "(無主機名)":30s}')
    print(f'   └─ {device_type} ({result["vendor"]}) - 信心度: {result["confidence"]}')
    print()

# 顯示統計
print('\n' + '='*80)
print('📈 設備類型統計：')
for dtype, count in sorted(device_stats.items(), key=lambda x: -x[1]):
    print(f'   {dtype}: {count} 台')

print(f'\n🔀 Switch 數量: {len(switches)} 台')
print(f'🌐 網路設備總數: {len(network_devices)} 台')

# 顯示所有 Switch 詳情
if switches:
    print('\n' + '='*80)
    print('🔀 識別出的 Switch 設備：')
    for lease in switches:
        result = detect_device_type(lease.mac_address, lease.hostname or '')
        print(f'   • {lease.ip_address} - {lease.hostname or lease.mac_address}')
        print(f'     廠商: {result["vendor"]} | 信心度: {result["confidence"]}')
else:
    print('\n⚠️ 沒有識別出 Switch 設備')
    print('   可能原因：')
    print('   1. MAC 地址不在已知網路設備 OUI 列表中')
    print('   2. 主機名稱沒有包含 Switch 相關關鍵字')
    print('\n   建議：檢查實際租約資料中的 MAC 地址和主機名稱')

# 顯示前 5 筆 MAC 地址供分析
print('\n' + '='*80)
print('📋 前 5 筆租約的 MAC 地址（用於手動檢查）：')
for i, lease in enumerate(leases[:5], 1):
    print(f'   {i}. {lease.mac_address} - {lease.hostname or "(無主機名)"}')
