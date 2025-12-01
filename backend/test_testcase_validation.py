#!/usr/bin/env python3
"""
Testcase Validation Feature Test

測試 Ansible Inventory 的 testcase 檔案驗證功能
"""

import os
import sys
import django

# 設置 Django 環境
sys.path.insert(0, '/home/owner/Codes/network-toolbox/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from library.utils.yaml_validator import YAMLValidator, validate_yaml_with_line_numbers


def test_yaml_validator():
    """測試 YAML 驗證器"""
    print("=" * 60)
    print("測試 1: YAML 語法驗證")
    print("=" * 60)
    
    # 測試有效的 YAML
    valid_yaml = """
testcase_sets:
  UGSD_GSD_mix:
    - test_case_1
    - test_case_2
  POR:
    - test_case_3
  Junior:
    - test_case_4
    """
    
    result = YAMLValidator.validate_yaml_syntax(valid_yaml)
    print(f"有效 YAML 測試: is_valid={result['is_valid']}")
    assert result['is_valid'], "有效 YAML 應該通過驗證"
    print("✓ 通過")
    
    # 測試無效的 YAML
    invalid_yaml = """
testcase_sets:
  UGSD_GSD_mix:
    - test_case_1
  invalid_indent
    - test_case_2
    """
    
    result = YAMLValidator.validate_yaml_syntax(invalid_yaml)
    print(f"\n無效 YAML 測試: is_valid={result['is_valid']}, error_line={result.get('error_line')}")
    assert not result['is_valid'], "無效 YAML 應該失敗"
    print(f"錯誤訊息: {result.get('error_message', '')[:100]}")
    print("✓ 通過")


def test_jinja2_validation():
    """測試 Jinja2 驗證"""
    print("\n" + "=" * 60)
    print("測試 2: Jinja2 語法驗證")
    print("=" * 60)
    
    # 包含 Jinja2 的 YAML（正確格式）
    yaml_with_jinja2 = """
common_vars:
  base_path: "/mnt/data"
  config_path: "{{ base_path }}/config"
    """
    
    result = YAMLValidator.validate_jinja2_in_yaml(yaml_with_jinja2)
    print(f"Jinja2 檢查: is_valid={result['is_valid']}, total_vars={result['total_jinja2_vars']}")
    print(f"未加引號的變數: {len(result['unquoted_jinja2'])}")
    print("✓ 通過")


def test_testcase_set_extraction():
    """測試 testcase_set 提取"""
    print("\n" + "=" * 60)
    print("測試 3: Testcase Set 提取")
    print("=" * 60)
    
    # 模擬 testcases.yml 內容
    testcases_yaml = """
# 測試案例定義
UGSD_GSD_mix:
  - SSD_Performance_Test
  - GSD_Stress_Test

POR:
  - Power_On_Reset_Test
  - Boot_Time_Validation

Junior:
  - Basic_Function_Test

SPOR:
  - Sudden_Power_Off_Test
    """
    
    result = YAMLValidator.extract_testcase_sets(testcases_yaml)
    print(f"提取到的 testcase_set: {result}")
    print(f"數量: {len(result)}")
    
    expected = {'UGSD_GSD_mix', 'POR', 'Junior', 'SPOR'}
    assert expected <= result, f"應該包含 {expected}，實際 {result}"
    print("✓ 通過")


def test_integration_with_inventory():
    """測試與 Inventory 的整合"""
    print("\n" + "=" * 60)
    print("測試 4: Inventory 整合測試")
    print("=" * 60)
    
    from api.models import AnsibleInventoryImport
    
    # 獲取最新的 Inventory
    inventory = AnsibleInventoryImport.objects.first()
    
    if not inventory:
        print("⚠ 沒有找到 Inventory 記錄，跳過整合測試")
        return
    
    print(f"找到 Inventory: ID={inventory.id}, Path={inventory.nas_path}")
    
    # 使用驗證器
    from library.services.inventory_config_validator import InventoryConfigValidator
    
    validator = InventoryConfigValidator(inventory.id, check_dhcp=False)
    
    # 測試 testcase 檔案路徑查找
    testcases_path = validator._get_testcases_file_path()
    
    if testcases_path:
        print(f"✓ 找到 testcases 檔案: {testcases_path}")
        
        # 讀取並驗證
        content = validator._read_testcases_file(testcases_path)
        if content:
            print(f"✓ 成功讀取檔案: {len(content)} 字元")
            
            # 驗證 YAML
            yaml_result = YAMLValidator.validate_yaml_syntax(content)
            print(f"  YAML 語法: {'有效' if yaml_result['is_valid'] else '無效'}")
            
            # 提取 testcase_set
            defined_sets = YAMLValidator.extract_testcase_sets(content)
            print(f"  定義的 testcase_set: {len(defined_sets)} 個")
            if defined_sets:
                print(f"    {list(defined_sets)[:5]}...")
    else:
        print("⚠ 未找到 testcases 檔案")
    
    # 測試從 Inventory 收集引用的 testcase_set
    # 先載入 Inventory 內容
    validator._load_inventory()
    referenced_sets = validator._collect_referenced_testcase_sets()
    print(f"\nInventory 引用的 testcase_set: {len(referenced_sets)} 個")
    if referenced_sets:
        print(f"  {list(referenced_sets)[:5]}...")
    
    print("\n✓ 整合測試完成")


def test_full_validation():
    """測試完整驗證流程"""
    print("\n" + "=" * 60)
    print("測試 5: 完整驗證流程")
    print("=" * 60)
    
    from api.models import AnsibleInventoryImport
    from library.services.inventory_config_validator import InventoryConfigValidator
    
    inventory = AnsibleInventoryImport.objects.first()
    
    if not inventory:
        print("⚠ 沒有找到 Inventory 記錄，跳過完整驗證測試")
        return
    
    print(f"執行完整驗證: Inventory ID={inventory.id}")
    
    validator = InventoryConfigValidator(inventory.id, check_dhcp=False)
    result = validator.validate()
    
    print(f"\n整體狀態: {result['overall_status']}")
    print(f"總檢查項: {result['summary']['total_checks']}")
    print(f"通過: {result['summary']['passed']}")
    print(f"警告: {result['summary']['warnings']}")
    print(f"錯誤: {result['summary']['errors']}")
    
    # 檢查 testcases 結果
    if 'testcases' in result['checks']:
        tc = result['checks']['testcases']
        print(f"\n📋 Testcases 檢查結果:")
        print(f"  狀態: {tc['status']}")
        print(f"  訊息: {tc['message']}")
        print(f"  值: {tc['value']}")
        
        if tc.get('details'):
            d = tc['details']
            print(f"  檔案路徑: {d.get('file_path', 'N/A')}")
            print(f"  YAML 有效: {d.get('yaml_valid', 'N/A')}")
            print(f"  已定義: {d.get('total_defined', 0)} 個")
            print(f"  被引用: {d.get('total_referenced', 0)} 個")
            
            if d.get('missing_sets'):
                print(f"  缺失: {d['missing_sets']}")
    else:
        print("\n⚠ 沒有 testcases 檢查結果")
    
    print("\n✓ 完整驗證測試完成")


if __name__ == '__main__':
    print("=" * 60)
    print("Testcase Validation Feature Test")
    print("=" * 60)
    
    try:
        test_yaml_validator()
        test_jinja2_validation()
        test_testcase_set_extraction()
        test_integration_with_inventory()
        test_full_validation()
        
        print("\n" + "=" * 60)
        print("✅ 所有測試通過！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
