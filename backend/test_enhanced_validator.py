#!/usr/bin/env python
"""
測試增強版 INI 驗證器（支援行號定位）
"""
import sys
import os

sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')

import django
django.setup()

from library.utils.enhanced_ini_validator import validate_ini_with_line_numbers


def test_case(name: str, content: str, expected_line: int = None):
    """測試單個案例"""
    print("=" * 80)
    print(f"測試案例: {name}")
    print("=" * 80)
    print(f"\n內容:")
    print("-" * 40)
    for i, line in enumerate(content.split('\n'), start=1):
        marker = " ← 預期錯誤" if i == expected_line else ""
        print(f"{i:3}: {line}{marker}")
    print("-" * 40)
    
    # 執行驗證
    result = validate_ini_with_line_numbers(content)
    
    print(f"\n驗證結果:")
    print(f"  是否有效: {'✅ 是' if result['is_valid'] else '❌ 否'}")
    print(f"  錯誤訊息: {result.get('error_message')}")
    print(f"  錯誤行號: {result.get('error_line')}")
    print(f"  錯誤行內容: {result.get('error_line_content')}")
    print(f"  驗證方法: {result.get('validation_method')}")
    
    # 判斷測試結果
    if result['is_valid']:
        if expected_line is None:
            print(f"\n結果: ✅ PASS - 正確通過驗證")
            return True
        else:
            print(f"\n結果: ❌ FAIL - 應該檢測出錯誤但沒有")
            return False
    else:
        if expected_line is not None:
            if result['error_line'] == expected_line:
                print(f"\n結果: ✅ PASS - 正確定位到第 {expected_line} 行")
                return True
            else:
                print(f"\n結果: ⚠️  PARTIAL - 檢測出錯誤但行號不對 (預期: {expected_line}, 實際: {result['error_line']})")
                return False
        else:
            print(f"\n結果: ❌ FAIL - 不應該報錯但報錯了")
            return False


def main():
    """執行所有測試"""
    print("=" * 80)
    print("增強版 INI 驗證器測試（支援行號定位）")
    print("=" * 80)
    print()
    
    test_results = []
    
    # 測試 1: 正確的語法
    test_results.append(test_case(
        "測試 1: 正確的語法（應該通過）",
        """[test_group]
host1 ansible_host=192.168.1.1
host2 ansible_host=192.168.1.2""",
        expected_line=None  # 不應該有錯誤
    ))
    
    # 測試 2: 缺少等號
    test_results.append(test_case(
        "測試 2: 變數缺少等號",
        """[test_group]
host1 ansible_host=192.168.1.1
host2 ansible_host 192.168.1.2
host3 ansible_host=192.168.1.3""",
        expected_line=3  # 錯誤在第 3 行
    ))
    
    # 測試 3: 空組名
    test_results.append(test_case(
        "測試 3: 空組名",
        """[]
host1 ansible_host=192.168.1.1""",
        expected_line=1  # 錯誤在第 1 行
    ))
    
    # 測試 4: 未閉合括號
    test_results.append(test_case(
        "測試 4: 未閉合的括號",
        """[test_group
host1 ansible_host=192.168.1.1""",
        expected_line=1  # 錯誤在第 1 行
    ))
    
    # 測試 5: 錯誤的變數值
    test_results.append(test_case(
        "測試 5: 變數缺少等號 (FFF)",
        """[test_group]
host1 ansible_host=192.168.1.1 uart_host=UART-HUB02 FFF""",
        expected_line=2  # 錯誤在第 2 行
    ))
    
    # 測試 6: YAML 語法
    test_results.append(test_case(
        "測試 6: YAML 語法混入",
        """[test_group]
host1:
  ansible_host: 192.168.1.1""",
        expected_line=2  # 錯誤在第 2 行
    ))
    
    # 測試 7: 多行錯誤（未閉合括號）
    test_results.append(test_case(
        "測試 7: 複雜的多行內容（未閉合括號）",
        """[web_servers]
web1 ansible_host=10.0.0.1
web2 ansible_host=10.0.0.2

[db_servers]
db1 ansible_host=10.0.1.1

[parent_group:children
child_group""",
        expected_line=8  # 錯誤在第 8 行
    ))
    
    # 測試 8: 複雜的正確語法
    test_results.append(test_case(
        "測試 8: 複雜的正確語法（應該通過）",
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
        expected_line=None  # 不應該有錯誤
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
        print(f"\n🎉 所有測試通過！")
        return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
