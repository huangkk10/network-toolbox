#!/usr/bin/env python3
"""
測試 MAC 廠商識別功能 - 使用完整 IEEE OUI 資料庫

此腳本測試:
1. OUI 資料庫載入
2. MAC 地址解析（多種格式）
3. 廠商識別準確性
4. 性能測試
"""

import sys
import os
import time

# 添加專案路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# 設置 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')

import django
django.setup()

from api.utils.mac_vendor import (
    get_vendor_from_mac, 
    get_vendor_stats, 
    reload_oui_database,
    get_all_vendors
)


def test_database_loading():
    """測試資料庫載入"""
    print('=' * 70)
    print('測試 1: OUI 資料庫載入')
    print('=' * 70)
    
    stats = get_vendor_stats()
    
    print(f"資料庫檔案: {stats['database_file']}")
    print(f"檔案存在: {'✓' if stats['file_exists'] else '✗'}")
    print(f"資料庫已載入: {'✓' if stats['database_loaded'] else '✗'}")
    
    if stats['file_exists']:
        print(f"總 OUI 記錄: {stats['total_oui_entries']:,}")
        print(f"唯一製造商: {stats['unique_vendors']:,}")
        print('✓ 測試通過')
    else:
        print('✗ 測試失敗：資料庫檔案不存在')
        return False
    
    print()
    return True


def test_mac_parsing():
    """測試 MAC 地址解析（多種格式）"""
    print('=' * 70)
    print('測試 2: MAC 地址格式解析')
    print('=' * 70)
    
    test_cases = [
        # (MAC 地址, 預期包含的關鍵字)
        ('00:50:BA:11:22:33', 'D-Link'),  # D-Link
        ('00-50-BA-11-22-33', 'D-Link'),  # D-Link (連字符格式)
        ('0050BA112233', 'D-Link'),       # D-Link (無分隔符)
        ('CC:46:D6:AA:BB:CC', 'Cisco'),   # Cisco
        ('48:AD:08:11:22:33', 'HUAWEI'),  # Huawei
        ('3C:D9:2B:44:55:66', 'Hewlett'), # HP
        ('00:1A:A0:11:22:33', 'Dell'),    # Dell（可能存在）
        ('FF:FF:FF:AA:BB:CC', 'Unknown'), # 不存在的 OUI
    ]
    
    passed = 0
    failed = 0
    
    for mac, expected_keyword in test_cases:
        vendor = get_vendor_from_mac(mac)
        contains = expected_keyword.lower() in vendor.lower()
        
        status = '✓' if contains else '✗'
        print(f"{status} MAC: {mac:20} => {vendor:30} (期望包含: {expected_keyword})")
        
        if contains:
            passed += 1
        else:
            failed += 1
    
    print(f"\n通過: {passed}/{len(test_cases)}")
    print()
    return failed == 0


def test_vendor_lookup():
    """測試實際 DHCP 租約中的 MAC 地址"""
    print('=' * 70)
    print('測試 3: 實際設備 MAC 地址識別')
    print('=' * 70)
    
    # 這些是從 DHCP 租約中發現的實際 MAC 地址前綴
    real_mac_prefixes = [
        '58:11:22',  # Realtek
        '60:cf:84',  # Realtek
        'e8:9c:25',  # Realtek
        '80:09:02',  # Intel
        '48:21:0b',  # Intel
        '84:a9:38',  # Intel
        'f0:2f:74',  # Intel
        '1c:69:7a',  # Intel
        '10:4f:58',  # Intel
        '60:6d:3c',  # TP-Link
        'f8:75:a4',  # D-Link
        '9c:69:d3',  # Realtek
    ]
    
    for mac_prefix in real_mac_prefixes:
        # 補全 MAC 地址
        full_mac = f"{mac_prefix}:11:22:33"
        vendor = get_vendor_from_mac(full_mac)
        print(f"MAC: {full_mac:20} => {vendor}")
    
    print('✓ 測試完成')
    print()
    return True


def test_performance():
    """測試查詢性能"""
    print('=' * 70)
    print('測試 4: 查詢性能測試')
    print('=' * 70)
    
    # 生成 1000 個隨機 MAC 地址
    import random
    test_macs = []
    
    for _ in range(1000):
        mac = ':'.join([f"{random.randint(0, 255):02X}" for _ in range(6)])
        test_macs.append(mac)
    
    # 測試查詢速度
    start_time = time.time()
    
    for mac in test_macs:
        vendor = get_vendor_from_mac(mac)
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"查詢 {len(test_macs)} 個 MAC 地址")
    print(f"總耗時: {duration:.4f} 秒")
    print(f"平均每個查詢: {(duration/len(test_macs)*1000):.4f} 毫秒")
    print(f"每秒查詢數: {len(test_macs)/duration:.0f} 次")
    
    if duration < 1.0:  # 1000 次查詢應該在 1 秒內完成
        print('✓ 性能測試通過')
    else:
        print('✗ 性能測試未達標')
    
    print()
    return duration < 1.0


def test_vendor_list():
    """測試製造商列表"""
    print('=' * 70)
    print('測試 5: 製造商列表')
    print('=' * 70)
    
    vendors = get_all_vendors()
    
    print(f"總製造商數: {len(vendors):,}")
    print(f"\n前 20 個製造商:")
    for i, vendor in enumerate(vendors[:20], 1):
        print(f"{i:2}. {vendor}")
    
    print('✓ 測試完成')
    print()
    return True


def main():
    print('\n' + '=' * 70)
    print('IEEE OUI 資料庫 - MAC 廠商識別測試')
    print('=' * 70 + '\n')
    
    tests = [
        ('資料庫載入', test_database_loading),
        ('MAC 格式解析', test_mac_parsing),
        ('實際設備識別', test_vendor_lookup),
        ('查詢性能', test_performance),
        ('製造商列表', test_vendor_list),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f'✗ 測試 "{test_name}" 發生錯誤: {str(e)}')
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # 總結
    print('=' * 70)
    print('測試總結')
    print('=' * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = '✓ 通過' if result else '✗ 失敗'
        print(f"{status:8} - {test_name}")
    
    print(f"\n總計: {passed}/{total} 通過")
    
    if passed == total:
        print('\n🎉 所有測試通過！')
        return 0
    else:
        print('\n⚠️  部分測試失敗')
        return 1


if __name__ == '__main__':
    sys.exit(main())
