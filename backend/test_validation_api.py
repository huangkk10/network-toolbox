#!/usr/bin/env python
"""
測試 Ansible Inventory 驗證 API（增強版 - 支援行號定位）
"""
import sys
import os
import json

sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')

import django
django.setup()

from rest_framework.test import APIClient


def test_validation_api(name: str, content: str, expected_valid: bool, expected_line: int = None):
    """測試驗證 API"""
    print("=" * 80)
    print(f"測試案例: {name}")
    print("=" * 80)
    
    # 顯示內容
    print(f"\n發送內容:")
    print("-" * 40)
    for i, line in enumerate(content.split('\n'), start=1):
        marker = " ← 預期錯誤" if i == expected_line else ""
        print(f"{i:3}: {line}{marker}")
    print("-" * 40)
    
    # 調用 API
    client = APIClient()
    response = client.post(
        '/api/ansible-inventory/validate-content/',
        data={'content': content},
        format='json'
    )
    
    print(f"\nAPI 響應:")
    print(f"  HTTP Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"  語法有效: {data.get('syntax_valid')}")
        print(f"  錯誤訊息: {data.get('error_message')}")
        
        if data.get('syntax_valid'):
            print(f"  解析主機數: {data.get('parsed_hosts')}")
            print(f"  解析組數: {data.get('parsed_groups')}")
        else:
            print(f"  錯誤行號: {data.get('error_line')}")
            print(f"  錯誤行內容: {data.get('error_line_content')}")
            print(f"  驗證方法: {data.get('validation_method')}")
        
        # 判斷測試結果
        if data.get('syntax_valid') == expected_valid:
            if expected_valid:
                print(f"\n結果: ✅ PASS - 正確識別為有效語法")
                return True
            else:
                # 預期失敗
                if expected_line is not None:
                    if data.get('error_line') == expected_line:
                        print(f"\n結果: ✅ PASS - 正確識別錯誤並定位到第 {expected_line} 行")
                        return True
                    else:
                        print(f"\n結果: ⚠️  PARTIAL - 識別錯誤但行號不準確 (預期: {expected_line}, 實際: {data.get('error_line')})")
                        return False
                else:
                    print(f"\n結果: ✅ PASS - 正確識別為無效語法")
                    return True
        else:
            print(f"\n結果: ❌ FAIL - 驗證結果不符合預期")
            return False
    else:
        print(f"  錯誤: {response.json()}")
        print(f"\n結果: ❌ FAIL - API 請求失敗")
        return False


def main():
    """執行所有測試"""
    print("=" * 80)
    print("Ansible Inventory 驗證 API 測試（增強版 - 支援行號定位）")
    print("=" * 80)
    print()
    
    test_results = []
    
    # 測試 1: 正確的語法
    test_results.append(test_validation_api(
        "測試 1: 正確的語法",
        """[test_group]
host1 ansible_host=192.168.1.1
host2 ansible_host=192.168.1.2""",
        expected_valid=True
    ))
    
    # 測試 2: 缺少等號（精確行號）
    test_results.append(test_validation_api(
        "測試 2: 變數缺少等號",
        """[test_group]
host1 ansible_host=192.168.1.1
host2 ansible_host 192.168.1.2
host3 ansible_host=192.168.1.3""",
        expected_valid=False,
        expected_line=3
    ))
    
    # 測試 3: 空組名
    test_results.append(test_validation_api(
        "測試 3: 空組名",
        """[]
host1 ansible_host=192.168.1.1""",
        expected_valid=False,
        expected_line=1
    ))
    
    # 測試 4: 未閉合括號
    test_results.append(test_validation_api(
        "測試 4: 未閉合的括號",
        """[test_group
host1 ansible_host=192.168.1.1""",
        expected_valid=False,
        expected_line=1
    ))
    
    # 測試 5: 你的案例（FFF 錯誤）
    test_results.append(test_validation_api(
        "測試 5: 用戶實際案例 (FFF)",
        """[test_group]
host1 ansible_host=192.168.1.1 uart_host=UART-HUB02 FFF""",
        expected_valid=False,
        expected_line=2
    ))
    
    # 測試 6: 複雜的正確語法
    test_results.append(test_validation_api(
        "測試 6: 複雜的正確語法",
        """[web_servers]
web1 ansible_host=10.0.0.1 ansible_user=admin
web2 ansible_host=10.0.0.2 ansible_user=admin

[db_servers]
db1 ansible_host=10.0.1.1

[all:vars]
ansible_port=22

[parent_group:children]
web_servers
db_servers""",
        expected_valid=True
    ))
    
    # 測試 7: 多行錯誤定位
    test_results.append(test_validation_api(
        "測試 7: 多行文件中的錯誤定位",
        """[web_servers]
web1 ansible_host=10.0.0.1
web2 ansible_host=10.0.0.2

[db_servers]
db1 ansible_host=10.0.1.1

[parent_group:children
child_group""",
        expected_valid=False,
        expected_line=8
    ))
    
    # 測試總結
    print("\n" + "=" * 80)
    print("測試總結")
    print("=" * 80)
    total = len(test_results)
    passed = sum(test_results)
    failed = total - passed
    
    print(f"總測試數: {total}")
    print(f"通過: {passed} ✅")
    print(f"失敗: {failed} ❌")
    print(f"成功率: {passed/total*100:.1f}%")
    
    if failed > 0:
        print(f"\n⚠️  有 {failed} 個測試失敗")
        return 1
    else:
        print(f"\n🎉 所有 API 測試通過！")
        return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
