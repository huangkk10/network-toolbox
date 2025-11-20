#!/usr/bin/env python
"""
測試 Ansible Inventory NAS 連線檢查功能

此腳本用於驗證新添加的 NAS 連線檢查功能是否正常工作
"""
import os
import sys
import django

# 設置 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.models import AnsibleInventoryImport
from library.services.inventory_config_validator import InventoryConfigValidator
import json


def test_nas_connection_check():
    """測試 NAS 連線檢查功能"""
    
    print("=" * 80)
    print("測試 Ansible Inventory NAS 連線檢查功能")
    print("=" * 80)
    
    # 1. 獲取一個有效的 Inventory 記錄
    inventory = AnsibleInventoryImport.objects.filter(status='success').first()
    
    if not inventory:
        print("\n❌ 找不到有效的 Inventory 記錄")
        print("   請先導入至少一個 Inventory 文件")
        return False
    
    print(f"\n✓ 找到 Inventory: ID={inventory.id}")
    print(f"  - NAS 路徑: {inventory.nas_path}")
    print(f"  - 檔案名稱: {inventory.file_name}")
    print(f"  - 狀態: {inventory.status}")
    print(f"  - Hosts 數量: {inventory.total_hosts}")
    print(f"  - Groups 數量: {inventory.total_groups}")
    
    # 2. 執行完整驗證（包含 NAS 連線檢查）
    print("\n" + "=" * 80)
    print("執行完整驗證流程...")
    print("=" * 80)
    
    validator = InventoryConfigValidator(
        inventory_id=inventory.id,
        check_connectivity=False,  # 不執行網路連線測試（節省時間）
        check_dhcp=False  # 不執行 DHCP 檢查（節省時間）
    )
    
    result = validator.validate()
    
    # 3. 顯示驗證結果
    print("\n" + "=" * 80)
    print("驗證結果摘要")
    print("=" * 80)
    
    print(f"\n總體狀態: {result['overall_status'].upper()}")
    
    summary = result.get('summary', {})
    print(f"\n統計資訊:")
    print(f"  - 總檢查項目: {summary.get('total_checks', 0)}")
    print(f"  - 通過: {summary.get('passed', 0)}")
    print(f"  - 警告: {summary.get('warnings', 0)}")
    print(f"  - 錯誤: {summary.get('errors', 0)}")
    
    # 4. 重點顯示 NAS 連線檢查結果
    print("\n" + "=" * 80)
    print("NAS 連線檢查詳細結果")
    print("=" * 80)
    
    checks = result.get('checks', {})
    nas_check = checks.get('nas_connection')
    
    if nas_check:
        print(f"\n狀態: {nas_check['status'].upper()}")
        print(f"訊息: {nas_check['message']}")
        print(f"數值: {nas_check['value']}")
        
        details = nas_check.get('details', {})
        if details:
            print(f"\n詳細資訊:")
            for key, value in details.items():
                if isinstance(value, (str, int, float, bool)):
                    print(f"  - {key}: {value}")
                elif value is None:
                    print(f"  - {key}: N/A")
        
        suggestions = nas_check.get('suggestions', [])
        if suggestions:
            print(f"\n建議:")
            for i, suggestion in enumerate(suggestions, 1):
                print(f"  {i}. {suggestion}")
    else:
        print("\n❌ 找不到 NAS 連線檢查結果")
        print("   可能檢查過程中發生錯誤")
    
    # 5. 顯示所有檢查項目狀態
    print("\n" + "=" * 80)
    print("所有檢查項目狀態")
    print("=" * 80)
    
    check_names = {
        'syntax': '語法驗證',
        'structure': '結構完整性',
        'host_config': '主機配置檢查',
        'ip_addresses': 'IP 地址驗證',
        'mac_addresses': 'MAC 地址驗證',
        'uart_ssh': 'UART SSH 連線檢查',
        'nas_connection': 'NAS 連線檢查',
        'network_connectivity': '網路連線測試',
    }
    
    for key, check_result in checks.items():
        name = check_names.get(key, key)
        status = check_result.get('status', 'unknown')
        message = check_result.get('message', 'N/A')
        
        status_icon = {
            'success': '✓',
            'warning': '⚠',
            'error': '✗',
            'unknown': '?'
        }.get(status, '?')
        
        print(f"\n{status_icon} {name}")
        print(f"  狀態: {status.upper()}")
        print(f"  訊息: {message}")
    
    # 6. 儲存完整結果到檔案（供查看）
    output_file = '/tmp/nas_check_result.json'
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n" + "=" * 80)
        print(f"✓ 完整驗證結果已儲存到: {output_file}")
        print(f"  可使用以下命令查看:")
        print(f"  cat {output_file} | jq")
    except Exception as e:
        print(f"\n⚠ 無法儲存結果到檔案: {e}")
    
    # 7. 判斷測試是否成功
    print("\n" + "=" * 80)
    print("測試結論")
    print("=" * 80)
    
    if nas_check and nas_check['status'] in ['success', 'warning']:
        print("\n✓ NAS 連線檢查功能正常運作！")
        print(f"  - 檢查狀態: {nas_check['status']}")
        print(f"  - 檢查結果: {nas_check['message']}")
        return True
    elif nas_check and nas_check['status'] == 'error':
        print("\n⚠ NAS 連線檢查功能運作正常，但 NAS 連線失敗")
        print(f"  - 這可能是正常的（如果 NAS 未啟動或網路不通）")
        print(f"  - 錯誤訊息: {nas_check['message']}")
        return True
    else:
        print("\n❌ NAS 連線檢查功能異常")
        print("  - 請檢查程式碼邏輯或日誌")
        return False


if __name__ == '__main__':
    try:
        success = test_nas_connection_check()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 測試過程發生異常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
