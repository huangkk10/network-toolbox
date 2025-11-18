#!/usr/bin/env python
"""測試重複變數名稱的驗證"""

import sys
import os

# 添加專案路徑
sys.path.insert(0, '/app')

from library.utils.enhanced_ini_validator import EnhancedINIValidator

def test_duplicate_variable_names():
    """測試 Ansible 允許的重複變數名稱"""
    
    print("=" * 80)
    print("測試重複變數名稱驗證")
    print("=" * 80)
    
    # 測試案例
    test_cases = [
        {
            "name": "Test 1: 不同 vars section 中的相同變數名（應該允許）",
            "content": """[group1:vars]
saf_enabled=true
ansible_user=root

[group2:vars]
saf_enabled=false
ansible_user=admin

[all:vars]
saf_enabled=false
""",
            "expected": True,
            "reason": "Ansible 允許不同 section 有相同變數名"
        },
        {
            "name": "Test 2: 實際案例 - SPVT_BAT_2:vars 和 all:vars",
            "content": """[SPVT_BAT_2]
host1 ansible_host=192.168.1.1

[SPVT_BAT_2:vars]
saf_enabled=true
ansible_user=administrator

[all:vars]
saf_enabled=false
ansible_shell_type=cmd
""",
            "expected": True,
            "reason": "與截圖中的實際情況類似"
        },
        {
            "name": "Test 3: 同一 section 中的重複變數（後者覆蓋前者）",
            "content": """[test:vars]
var1=value1
var2=value2
var1=value3
""",
            "expected": True,
            "reason": "Ansible 允許重複，後面的值會覆蓋前面的"
        },
        {
            "name": "Test 4: 多個 vars section 使用相同變數",
            "content": """[group1:vars]
ansible_user=root
platform_install_vnc=true

[group2:vars]
ansible_user=admin
platform_install_vnc=false

[group3:vars]
ansible_user=test
platform_install_vnc=true

[all:vars]
ansible_shell_type=cmd
""",
            "expected": True,
            "reason": "多個 group 可以定義相同的變數"
        },
        {
            "name": "Test 5: 真實錯誤 - 缺少等號（應該失敗）",
            "content": """[test:vars]
saf_enabled false
""",
            "expected": False,
            "reason": "真正的語法錯誤"
        },
    ]
    
    passed = 0
    failed = 0
    
    for test_case in test_cases:
        print(f"\n{test_case['name']}")
        print(f"預期: {'✅ 通過' if test_case['expected'] else '❌ 失敗'}")
        print(f"原因: {test_case['reason']}")
        print("-" * 80)
        
        result = EnhancedINIValidator.validate(test_case['content'])
        
        is_valid = result['is_valid']
        expected = test_case['expected']
        
        if is_valid == expected:
            print(f"✅ PASS - 驗證結果符合預期")
            passed += 1
        else:
            print(f"❌ FAIL - 預期: {expected}, 實際: {is_valid}")
            if result['error_message']:
                print(f"   錯誤訊息: {result['error_message']}")
                print(f"   錯誤行號: {result['error_line']}")
                print(f"   驗證方法: {result.get('validation_method', 'N/A')}")
            failed += 1
        
        # 顯示內容預覽（前 10 行）
        lines = test_case['content'].strip().split('\n')
        for i, line in enumerate(lines[:10], 1):
            marker = " ❌" if result.get('error_line') == i else ""
            print(f"   {i}: {line}{marker}")
        if len(lines) > 10:
            print(f"   ... (共 {len(lines)} 行)")
    
    print("\n" + "=" * 80)
    print(f"測試完成: {passed} 通過, {failed} 失敗")
    print("=" * 80)
    
    return failed == 0

if __name__ == '__main__':
    success = test_duplicate_variable_names()
    sys.exit(0 if success else 1)
