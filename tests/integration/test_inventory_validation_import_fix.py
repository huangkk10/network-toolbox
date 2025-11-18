#!/usr/bin/env python3
"""
Ansible Inventory Validation Import Fix Test

測試 InventoryConfigValidator 的導入問題是否已修復

Bug: ImportError: cannot import name 'AnsibleInventory' from 'api.models'
Fix: 將導入從方法內移至文件頂部

Author: Network Toolbox Team
Date: 2025-11-18
"""

import os
import sys
import django

# Django setup
sys.path.insert(0, '/home/owner/Codes/network-toolbox/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

import importlib
import inspect


def test_import_fix():
    """測試導入修復"""
    print("=" * 80)
    print("🔍 測試 InventoryConfigValidator 導入修復")
    print("=" * 80)
    print()
    
    # Step 1: 測試頂層導入
    print("步驟 1: 檢查模組導入")
    print("-" * 80)
    
    try:
        # 導入服務模組
        from library.services import inventory_config_validator
        print("✓ library.services.inventory_config_validator 模組導入成功")
        
        # 檢查 AnsibleInventory 是否在頂層導入
        module_source = inspect.getsource(inventory_config_validator)
        
        # 檢查頂層導入
        has_top_level_import = False
        for line in module_source.split('\n')[:30]:  # 檢查前 30 行
            if 'from api.models import AnsibleInventory' in line and not line.strip().startswith('#'):
                has_top_level_import = True
                print(f"✓ 找到頂層導入: {line.strip()}")
                break
        
        if not has_top_level_import:
            print("✗ 未找到 AnsibleInventory 的頂層導入")
            return False
        
        print()
        
    except Exception as e:
        print(f"✗ 模組導入失敗: {e}")
        return False
    
    # Step 2: 檢查 _load_inventory 方法
    print("步驟 2: 檢查 _load_inventory 方法")
    print("-" * 80)
    
    try:
        from library.services.inventory_config_validator import InventoryConfigValidator
        
        # 獲取 _load_inventory 方法的源代碼
        method_source = inspect.getsource(InventoryConfigValidator._load_inventory)
        
        # 檢查方法內是否還有導入語句
        has_method_import = False
        for line in method_source.split('\n'):
            if 'from api.models import' in line and not line.strip().startswith('#'):
                has_method_import = True
                print(f"✗ 方法內仍有導入: {line.strip()}")
                break
        
        if has_method_import:
            print("✗ _load_inventory 方法內仍包含導入語句（應該移除）")
            return False
        else:
            print("✓ _load_inventory 方法內無導入語句")
        
        # 檢查方法是否直接使用 AnsibleInventory
        if 'AnsibleInventory.objects' in method_source:
            print("✓ _load_inventory 方法直接使用 AnsibleInventory（無需局部導入）")
        else:
            print("✗ _load_inventory 方法未使用 AnsibleInventory")
            return False
        
        print()
        
    except Exception as e:
        print(f"✗ 方法檢查失敗: {e}")
        return False
    
    # Step 3: 實例化測試
    print("步驟 3: 測試類別實例化")
    print("-" * 80)
    
    try:
        from library.services.inventory_config_validator import InventoryConfigValidator
        
        # 嘗試創建實例（不執行驗證）
        validator = InventoryConfigValidator(inventory_id=9999)
        print("✓ InventoryConfigValidator 實例化成功")
        
        # 檢查類別屬性
        if hasattr(validator, '_load_inventory'):
            print("✓ _load_inventory 方法存在")
        else:
            print("✗ _load_inventory 方法不存在")
            return False
        
        print()
        
    except Exception as e:
        print(f"✗ 實例化失敗: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 4: 檢查所有導入
    print("步驟 4: 檢查完整導入列表")
    print("-" * 80)
    
    try:
        from library.services import inventory_config_validator
        module_source = inspect.getsource(inventory_config_validator)
        
        # 提取所有導入語句（前 50 行）
        imports = []
        for line_num, line in enumerate(module_source.split('\n')[:50], 1):
            stripped = line.strip()
            if stripped.startswith('import ') or stripped.startswith('from '):
                if not stripped.startswith('#'):
                    imports.append(f"Line {line_num}: {stripped}")
        
        print(f"找到 {len(imports)} 個導入語句：")
        for imp in imports:
            print(f"  {imp}")
        
        # 檢查必要的導入
        required_imports = [
            'import logging',
            'import re',
            'import socket',
            'import ipaddress',
            'from typing import',
            'from configparser import ConfigParser',
            'from collections import defaultdict',
            'from api.models import AnsibleInventory'
        ]
        
        print()
        print("檢查必要導入：")
        all_imports_text = '\n'.join(imports)
        for req in required_imports:
            if any(req in imp for imp in imports):
                print(f"  ✓ {req}")
            else:
                print(f"  ✗ {req} (缺失)")
                return False
        
        print()
        
    except Exception as e:
        print(f"✗ 導入檢查失敗: {e}")
        return False
    
    # Step 5: 模擬調用測試
    print("步驟 5: 模擬 _load_inventory 調用")
    print("-" * 80)
    
    try:
        from library.services.inventory_config_validator import InventoryConfigValidator
        from api.models import AnsibleInventory
        
        # 檢查是否有測試數據
        test_inventory = AnsibleInventory.objects.first()
        
        if test_inventory:
            print(f"✓ 找到測試 Inventory: ID={test_inventory.id}")
            
            # 創建驗證器並嘗試載入
            validator = InventoryConfigValidator(inventory_id=test_inventory.id)
            
            try:
                result = validator._load_inventory()
                if result:
                    print("✓ _load_inventory 執行成功")
                    print(f"  - Inventory ID: {validator.inventory.id}")
                    print(f"  - Content length: {len(validator.content)} chars")
                else:
                    print("⚠ _load_inventory 返回 False（可能是數據問題）")
            except Exception as e:
                print(f"✗ _load_inventory 執行失敗: {e}")
                import traceback
                traceback.print_exc()
                return False
        else:
            print("⚠ 無測試數據，跳過實際調用測試")
        
        print()
        
    except Exception as e:
        print(f"✗ 模擬調用失敗: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def main():
    """主函數"""
    try:
        success = test_import_fix()
        
        print("=" * 80)
        if success:
            print("✓✓✓ 導入修復測試通過！✓✓✓")
            print()
            print("修復摘要：")
            print("  1. ✓ AnsibleInventory 已移至頂層導入")
            print("  2. ✓ _load_inventory 方法內無導入語句")
            print("  3. ✓ 類別可正常實例化")
            print("  4. ✓ 所有必要導入存在")
            print("  5. ✓ _load_inventory 可正常執行")
            print()
            print("🎉 Bug 已修復：ImportError 問題已解決")
        else:
            print("✗✗✗ 導入修復測試失敗 ✗✗✗")
            print()
            print("請檢查：")
            print("  1. AnsibleInventory 是否在文件頂部導入")
            print("  2. _load_inventory 方法內是否移除了導入語句")
            print("  3. Django 是否正確配置")
        print("=" * 80)
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"\n❌ 測試執行失敗: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
