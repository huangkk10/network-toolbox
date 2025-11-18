#!/usr/bin/env python
"""測試 Jinja2 模板語法的驗證"""

import sys
import os

# 添加專案路徑
sys.path.insert(0, '/app')

from library.utils.enhanced_ini_validator import EnhancedINIValidator

def test_jinja2_template_syntax():
    """測試包含 Jinja2 模板的 Inventory 語法"""
    
    print("=" * 80)
    print("測試 Jinja2 模板語法驗證")
    print("=" * 80)
    
    # 測試案例 1: 簡單 Jinja2 變數
    test_cases = [
        {
            "name": "Test 1: 簡單 Jinja2 變數",
            "content": """[test]
host1 ansible_host={{ ip_address }}
""",
            "expected": True
        },
        {
            "name": "Test 2: 複雜 Jinja2 表達式（實際案例）",
            "content": """[uart:vars]
saf_comment_full={{{{ firmware_sku_keyword }}}} - {{{{ sample_size }}}} - {{{{ saf_comment }}}}
""",
            "expected": True
        },
        {
            "name": "Test 3: 多個 Jinja2 變數",
            "content": """[test]
host1 var1={{ value1 }} var2={{ value2 }}
""",
            "expected": True
        },
        {
            "name": "Test 4: Jinja2 過濾器",
            "content": """[test]
host1 ansible_host={{ ip_address | default('127.0.0.1') }}
""",
            "expected": True
        },
        {
            "name": "Test 5: 正常變數（不含 Jinja2）",
            "content": """[test]
host1 ansible_host=192.168.1.1 ansible_user=root
""",
            "expected": True
        },
        {
            "name": "Test 6: 錯誤語法（缺少等號，無 Jinja2）",
            "content": """[test]
host1 ansible_host 192.168.1.1
""",
            "expected": False
        },
        {
            "name": "Test 7: 混合 Jinja2 和普通變數",
            "content": """[test]
host1 ansible_host={{ ip }} ansible_user=root mac_address=AA:BB:CC:DD:EE:FF
""",
            "expected": True
        },
        {
            "name": "Test 8: 實際 132 行的內容",
            "content": """[uart:vars]
ansible_user=administrator
saf_mode=beta
saf_comment=Andrews
saf_comment_full={{{{ firmware_sku_keyword }}}} - {{{{ sample_size }}}} - {{{{ saf_comment }}}}
""",
            "expected": True
        }
    ]
    
    passed = 0
    failed = 0
    
    for test_case in test_cases:
        print(f"\n{test_case['name']}")
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
            failed += 1
        
        # 顯示內容預覽
        lines = test_case['content'].strip().split('\n')
        for i, line in enumerate(lines, 1):
            marker = " ❌" if result['error_line'] == i else ""
            print(f"   {i}: {line}{marker}")
    
    print("\n" + "=" * 80)
    print(f"測試完成: {passed} 通過, {failed} 失敗")
    print("=" * 80)
    
    return failed == 0

if __name__ == '__main__':
    success = test_jinja2_template_syntax()
    sys.exit(0 if success else 1)
