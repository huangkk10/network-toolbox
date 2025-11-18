#!/usr/bin/env python3
"""
測試 Ansible Inventory 語法驗證

這個腳本測試各種正確和錯誤的語法，確認驗證功能是否正常工作
"""

import sys
import os
import tempfile
import subprocess
import json

# 添加專案路徑到 sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from library.services.ansible_inventory_service import AnsibleInventoryService


def test_case(name, content, expected_valid):
    """
    測試單個案例
    
    Args:
        name: 測試案例名稱
        content: 要測試的內容
        expected_valid: 預期是否應該通過驗證
    """
    print(f"\n{'='*80}")
    print(f"測試案例: {name}")
    print(f"預期結果: {'✅ 應該通過' if expected_valid else '❌ 應該失敗'}")
    print(f"{'='*80}")
    print("測試內容:")
    print("-" * 80)
    print(content)
    print("-" * 80)
    
    service = AnsibleInventoryService()
    syntax_valid, error_message, parsed_stats = service.validate_content_syntax(content)
    
    # 判斷結果
    if syntax_valid == expected_valid:
        result = "✅ PASS"
    else:
        result = "❌ FAIL"
    
    print(f"\n實際結果: {'✅ 通過驗證' if syntax_valid else '❌ 驗證失敗'}")
    
    if error_message:
        print(f"錯誤訊息: {error_message}")
    
    if parsed_stats:
        print(f"解析統計: {parsed_stats['total_hosts']} hosts, {parsed_stats['total_groups']} groups")
    
    print(f"\n測試結果: {result}")
    
    return syntax_valid == expected_valid


def main():
    """執行所有測試案例"""
    
    print("=" * 80)
    print("Ansible Inventory 語法驗證測試")
    print("=" * 80)
    
    test_results = []
    
    # ========== 正確語法測試 ==========
    
    # 測試 1: 基本正確語法
    test_results.append(test_case(
        "測試 1: 基本正確語法",
        """[test_group]
host1 ansible_host=192.168.1.1
host2 ansible_host=192.168.1.2
""",
        expected_valid=True
    ))
    
    # 測試 2: 正確的變數值包含空格和引號
    test_results.append(test_case(
        "測試 2: 變數值包含空格（使用引號 - 合法）",
        """[test_group]
host1 ansible_host=192.168.1.1 uart_host="UART-HUB02 P P P"
""",
        expected_valid=True
    ))
    
    # 測試 2b: 錯誤的變數值 - 空格未使用引號（錯誤）
    test_results.append(test_case(
        "測試 2b: 變數值包含空格但未使用引號（錯誤）",
        """[test_group]
host1 ansible_host=192.168.1.1 uart_host=UART-HUB02 P P P
""",
        expected_valid=False
    ))
    
    # 測試 3: 複雜的正確語法
    test_results.append(test_case(
        "測試 3: 複雜的正確語法",
        """[web_servers]
web1 ansible_host=10.0.0.1 ansible_user=admin
web2 ansible_host=10.0.0.2 ansible_user=admin

[db_servers]
db1 ansible_host=10.0.1.1

[all:vars]
ansible_port=22
""",
        expected_valid=True
    ))
    
    # ========== 錯誤語法測試 ==========
    
    # 測試 4: 缺少 Group 名稱（錯誤）
    test_results.append(test_case(
        "測試 4: 缺少 Group 名稱（錯誤）",
        """[]
host1 ansible_host=192.168.1.1
""",
        expected_valid=False
    ))
    
    # 測試 5: 不匹配的括號（錯誤）
    test_results.append(test_case(
        "測試 5: 不匹配的括號（錯誤）",
        """[test_group
host1 ansible_host=192.168.1.1
""",
        expected_valid=False
    ))
    
    # 測試 6: 變數格式錯誤 - 缺少等號（錯誤）
    test_results.append(test_case(
        "測試 6: 變數格式錯誤 - 缺少等號（錯誤）",
        """[test_group]
host1 ansible_host 192.168.1.1
""",
        expected_valid=False
    ))
    
    # 測試 7: 無效的 Group 繼承語法（錯誤）
    test_results.append(test_case(
        "測試 7: 無效的 Group 繼承語法（錯誤）",
        """[parent_group:children
child_group
""",
        expected_valid=False
    ))
    
    # 測試 8: YAML 語法混入 INI（錯誤）
    test_results.append(test_case(
        "測試 8: YAML 語法混入 INI（錯誤）",
        """all:
  hosts:
    host1:
      ansible_host: 192.168.1.1
""",
        expected_valid=False
    ))
    
    # 測試 9: 完全亂碼（錯誤）
    test_results.append(test_case(
        "測試 9: 完全亂碼（錯誤）",
        """asdfghjkl;'
qwertyuiop[]
zxcvbnm,./
""",
        expected_valid=False
    ))
    
    # 測試 10: 空文件（應該通過）
    test_results.append(test_case(
        "測試 10: 空文件（應該通過）",
        "",
        expected_valid=True
    ))
    
    # ========== 邊界測試 ==========
    
    # 測試 11: 只有註釋（應該通過）
    test_results.append(test_case(
        "測試 11: 只有註釋（應該通過）",
        """# This is a comment
# Another comment
""",
        expected_valid=True
    ))
    
    # 測試 12: 特殊字元在變數值中（應該通過）
    test_results.append(test_case(
        "測試 12: 特殊字元在變數值中（應該通過）",
        """[test]
host1 ansible_host=192.168.1.1 path=C:\\Windows\\System32
""",
        expected_valid=True
    ))
    
    # ========== 總結 ==========
    
    print("\n" + "=" * 80)
    print("測試總結")
    print("=" * 80)
    
    passed = sum(test_results)
    total = len(test_results)
    
    print(f"總測試數: {total}")
    print(f"通過: {passed} ✅")
    print(f"失敗: {total - passed} ❌")
    print(f"通過率: {passed/total*100:.1f}%")
    
    if passed == total:
        print("\n🎉 所有測試通過！")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 個測試失敗")
        return 1


if __name__ == '__main__':
    sys.exit(main())
