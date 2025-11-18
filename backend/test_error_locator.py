#!/usr/bin/env python
"""
測試錯誤定位功能

測試 InventoryErrorLocator 能否正確定位各種錯誤
"""
import sys
import os

# 添加專案路徑
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')

import django
django.setup()

from library.utils.inventory_error_locator import InventoryErrorLocator, locate_error_in_content


def test_case(name: str, content: str, error_message: str):
    """測試單個案例"""
    print("=" * 80)
    print(f"測試案例: {name}")
    print("=" * 80)
    print(f"\n內容:")
    print("-" * 40)
    for i, line in enumerate(content.split('\n'), start=1):
        print(f"{i:3}: {line}")
    print("-" * 40)
    
    print(f"\n錯誤訊息:")
    print(error_message)
    
    # 執行錯誤定位
    result = locate_error_in_content(content, error_message)
    
    print(f"\n定位結果:")
    print(f"  錯誤關鍵字: {result.get('error_keyword')}")
    print(f"  錯誤行號: {result.get('line_number')}")
    print(f"  錯誤行內容: {result.get('line_content')}")
    
    if result.get('suggestions'):
        print(f"\n修正建議:")
        for i, suggestion in enumerate(result['suggestions'], start=1):
            print(f"  {i}. {suggestion}")
    
    # 判斷結果
    if result.get('line_number'):
        print(f"\n結果: ✅ 成功定位到第 {result['line_number']} 行")
        return True
    else:
        print(f"\n結果: ❌ 無法定位錯誤")
        return False


def main():
    """執行所有測試"""
    print("=" * 80)
    print("Ansible Inventory 錯誤定位測試")
    print("=" * 80)
    print()
    
    test_results = []
    
    # 測試 1: 缺少等號
    test_results.append(test_case(
        "測試 1: 變數缺少等號",
        """[test_group]
host1 ansible_host=192.168.1.1
host2 ansible_host 192.168.1.2
host3 ansible_host=192.168.1.3""",
        "[WARNING]: Failed to parse inventory with 'ini' plugin: Failed to parse inventory: Expected key=value host variable assignment, got: ansible_host"
    ))
    
    # 測試 2: 空組名
    test_results.append(test_case(
        "測試 2: 空組名",
        """[]
host1 ansible_host=192.168.1.1""",
        "[WARNING]: Failed to parse inventory with 'ini' plugin: Failed to parse inventory: Invalid section entry: '[]'. Please make sure that there are no spaces in the section entry"
    ))
    
    # 測試 3: 未閉合括號
    test_results.append(test_case(
        "測試 3: 未閉合的括號",
        """[test_group
host1 ansible_host=192.168.1.1""",
        "[WARNING]: Failed to parse inventory with 'ini' plugin: Failed to parse inventory: not enough values to unpack (expected 3, got 2)"
    ))
    
    # 測試 4: 錯誤的變數值
    test_results.append(test_case(
        "測試 4: 錯誤的變數值",
        """[test_group]
host1 ansible_host=192.168.1.1 uart_host=UART-HUB02 FFF""",
        "[WARNING]: Failed to parse inventory with 'ini' plugin: Failed to parse inventory: Expected key=value host variable assignment, got: FFF"
    ))
    
    # 測試 5: 多行錯誤
    test_results.append(test_case(
        "測試 5: 複雜的多行內容",
        """[web_servers]
web1 ansible_host=10.0.0.1
web2 ansible_host=10.0.0.2

[db_servers]
db1 ansible_host=10.0.1.1

[parent_group:children
child_group""",
        "[WARNING]: Failed to parse inventory with 'ini' plugin: Failed to parse inventory: not enough values to unpack (expected 3, got 2)"
    ))
    
    # 測試總結
    print("\n" + "=" * 80)
    print("測試總結")
    print("=" * 80)
    total = len(test_results)
    passed = sum(test_results)
    failed = total - passed
    
    print(f"總測試數: {total}")
    print(f"成功定位: {passed} ✅")
    print(f"定位失敗: {failed} ❌")
    print(f"成功率: {passed/total*100:.1f}%")
    
    if failed > 0:
        print(f"\n⚠️  有 {failed} 個測試未能成功定位錯誤")
        return 1
    else:
        print(f"\n🎉 所有測試都成功定位錯誤！")
        return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
