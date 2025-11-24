#!/usr/bin/env python
"""
MDT Web 整合測試腳本

測試 MDT Web 檢查功能是否正確整合到 InventoryConfigValidator
"""

import os
import sys
import django

# 設置 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from library.services.inventory_config_validator import InventoryConfigValidator
from api.models import AnsibleInventoryImport


def test_mdt_web_integration():
    """測試 MDT Web 整合功能"""
    print('✓ MDT Web 整合測試')
    print('=' * 80)
    
    # 查找第一個可用的 Inventory
    inventory = AnsibleInventoryImport.objects.first()
    
    if not inventory:
        print('❌ 沒有可用的 Inventory 記錄')
        return False
    
    print(f'\n📋 測試 Inventory:')
    print(f'  ID: {inventory.id}')
    print(f'  檔案: {inventory.file_name}')
    print(f'  DHCP Server ID: {getattr(inventory, "dhcp_server_id", "N/A")}')
    
    # 創建驗證器（啟用 DHCP 檢查）
    validator = InventoryConfigValidator(
        inventory_id=inventory.id,
        check_connectivity=False,
        check_dhcp=True
    )
    
    # 執行驗證
    print('\n🔍 開始執行配置驗證...\n')
    results = validator.validate()
    
    # 顯示 MDT Web 檢查結果
    if 'mdt_web' in results.get('checks', {}):
        mdt_check = results['checks']['mdt_web']
        
        print('\n' + '=' * 80)
        print('📊 MDT Web 檢查結果')
        print('=' * 80)
        print(f'狀態: {mdt_check["status"].upper()}')
        print(f'訊息: {mdt_check["message"]}')
        print(f'數值: {mdt_check["value"]}')
        
        details = mdt_check.get('details', {})
        if details:
            print('\n詳細資訊:')
            for key, value in details.items():
                if key not in ['not_found_devices', 'mismatched_devices']:
                    print(f'  • {key}: {value}')
            
            # 顯示問題設備（如果有）
            if details.get('not_found_devices'):
                print('\n  未找到的設備:')
                for device in details['not_found_devices'][:5]:
                    print(f'    - {device["device_number"]} ({device["hostname"]})')
            
            if details.get('mismatched_devices'):
                print('\n  配置不一致的設備:')
                for device in details['mismatched_devices'][:5]:
                    print(f'    - {device["device_number"]} ({device["hostname"]})')
                    for diff in device['differences']:
                        print(f'      • {diff["field"]}: Inventory={diff["inventory_value"]} vs MDT Web={diff["mdt_web_value"]}')
        
        # 顯示建議
        suggestions = mdt_check.get('suggestions', [])
        if suggestions:
            print('\n💡 建議:')
            for suggestion in suggestions:
                print(f'  {suggestion}')
    else:
        print('\n⚠️ 驗證結果中沒有 MDT Web 檢查項目')
        print('\n所有檢查項目:')
        for check_name in results.get('checks', {}).keys():
            print(f'  - {check_name}')
    
    print('\n' + '=' * 80)
    print('📈 整體驗證結果')
    print('=' * 80)
    print(f'整體狀態: {results["overall_status"].upper()}')
    print(f'總檢查項目: {results["summary"]["total_checks"]}')
    print(f'通過: {results["summary"]["passed"]} | 警告: {results["summary"]["warnings"]} | 錯誤: {results["summary"]["errors"]}')
    
    # 列出所有檢查項目及其狀態
    print('\n檢查項目明細:')
    for check_name, check_result in results.get('checks', {}).items():
        status_icon = {
            'success': '✓',
            'warning': '⚠',
            'error': '✗',
            'unknown': '?'
        }.get(check_result['status'], '?')
        print(f'  {status_icon} {check_name}: {check_result["status"]} - {check_result["message"]}')
    
    print('=' * 80)
    
    return True


if __name__ == '__main__':
    try:
        success = test_mdt_web_integration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f'\n❌ 測試失敗: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)
