#!/usr/bin/env python
"""尋找所有可能的 Switch 設備"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
sys.path.insert(0, '/app')
django.setup()

from api.models import DHCPLease
from api.utils.device_type_detector import detect_device_type, is_switch, SWITCH_HOSTNAME_KEYWORDS, NETWORK_DEVICE_VENDORS

print('=== 尋找 Switch 設備 ===\n')

# 獲取所有租約
all_leases = DHCPLease.objects.all()
print(f'📊 資料庫中共有 {all_leases.count()} 筆租約\n')

# 1. 檢查是否有 Switch 關鍵字的主機名
print('🔍 搜尋包含 Switch 關鍵字的主機名稱...')
print(f'   關鍵字: {", ".join(SWITCH_HOSTNAME_KEYWORDS)}\n')

switch_by_name = []
for lease in all_leases:
    if lease.hostname:
        hostname_lower = lease.hostname.lower()
        for keyword in SWITCH_HOSTNAME_KEYWORDS:
            if keyword in hostname_lower:
                switch_by_name.append(lease)
                result = detect_device_type(lease.mac_address, lease.hostname)
                print(f'   ✅ {lease.ip_address} - {lease.hostname}')
                print(f'      MAC: {lease.mac_address} | 廠商: {result["vendor"]} | 信心度: {result["confidence"]}')
                break

if not switch_by_name:
    print('   ❌ 沒有找到包含 Switch 關鍵字的主機名稱\n')
else:
    print(f'\n   找到 {len(switch_by_name)} 台（根據主機名稱）\n')

# 2. 檢查是否有網路設備 MAC OUI
print('='*80)
print('🔍 搜尋網路設備廠商的 MAC 地址...')
print(f'   已知網路設備廠商數: {len(NETWORK_DEVICE_VENDORS)}\n')

network_by_mac = []
for lease in all_leases:
    mac_prefix = lease.mac_address[:8].upper()
    if mac_prefix in NETWORK_DEVICE_VENDORS:
        vendor = NETWORK_DEVICE_VENDORS[mac_prefix]
        network_by_mac.append((lease, vendor))
        result = detect_device_type(lease.mac_address, lease.hostname or '')
        print(f'   ✅ {lease.ip_address} - {lease.hostname or "(無主機名)"}')
        print(f'      MAC: {lease.mac_address} | 廠商: {vendor} | 類型: {result["type"]}')

if not network_by_mac:
    print('   ❌ 沒有找到已知網路設備廠商的 MAC 地址\n')
else:
    print(f'\n   找到 {len(network_by_mac)} 台網路設備（根據 MAC OUI）\n')

# 3. 顯示所有可能的網路設備
print('='*80)
print('📊 總結：\n')

all_network_devices = list(set(switch_by_name + [lease for lease, _ in network_by_mac]))

if all_network_devices:
    print(f'🌐 可能的網路設備總數: {len(all_network_devices)} 台\n')
    
    for lease in all_network_devices:
        result = detect_device_type(lease.mac_address, lease.hostname or '')
        print(f'{result["icon"]} {lease.ip_address:15s} - {lease.hostname or lease.mac_address}')
        print(f'   廠商: {result["vendor"]} | 類型: {result["type"]} | 信心度: {result["confidence"]}')
        print()
else:
    print('❌ 沒有找到任何網路設備')
    print('\n可能的原因：')
    print('1. 網路中真的沒有 Switch（所有設備都是 PC/伺服器）')
    print('2. Switch 使用的是未知的 MAC OUI（不在我們的資料庫中）')
    print('3. Switch 沒有主機名稱或使用非標準命名')
    
    # 顯示一些建議
    print('\n💡 建議：')
    print('1. 檢查您的網路設備清單，確認是否有 Switch')
    print('2. 如果有 Switch，請提供其 MAC 地址前綴，我可以加入資料庫')
    print('3. 或者設定 Switch 的主機名稱包含 "switch", "sw-" 等關鍵字')

# 4. 顯示 MAC 地址分佈
print('\n' + '='*80)
print('📋 MAC 地址廠商分佈（前 10 名）：\n')

from collections import Counter
mac_prefixes = [lease.mac_address[:8].upper() for lease in all_leases]
mac_counter = Counter(mac_prefixes)

for prefix, count in mac_counter.most_common(10):
    # 嘗試從 mac_vendor.py 獲取廠商名稱
    try:
        from api.utils.mac_vendor import get_vendor
        vendor = get_vendor(prefix + ':00:00:00')
        print(f'   {prefix} - {vendor}: {count} 台')
    except:
        print(f'   {prefix} - (未知廠商): {count} 台')
