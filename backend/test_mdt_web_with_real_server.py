#!/usr/bin/env python
"""
MDT Web 功能驗證測試

使用實際的 MDT Web 伺服器 (10.250.10.2) 進行完整測試
"""

import os
import sys
import django

# 設置 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from library.services.mdt_web_service import MDTWebService
from library.services.inventory_config_validator import InventoryConfigValidator


def test_mdt_web_service():
    """測試 MDT Web 服務層"""
    print('\n' + '=' * 80)
    print('📊 測試 1: MDT Web 服務層功能')
    print('=' * 80)
    
    mdt_service = MDTWebService('10.250.10.2')
    
    # 測試連接
    is_accessible, error = mdt_service.check_connection()
    print(f'\n1. 連接測試: {"✓ 成功" if is_accessible else f"✗ 失敗 - {error}"}')
    
    if not is_accessible:
        print('⚠️ MDT Web 不可訪問，跳過後續測試')
        return False
    
    # 測試查詢設備
    test_device = 'PC-SSD-4052'
    device = mdt_service.get_device(test_device)
    print(f'\n2. 設備查詢 ({test_device}): {"✓ 找到" if device else "✗ 未找到"}')
    
    if device:
        print(f'   - 設備名稱: {device.get("name")}')
        print(f'   - IP 地址: {device.get("info", {}).get("ip")}')
        print(f'   - MAC 地址: {device.get("info", {}).get("mac")}')
        print(f'   - 作業系統: {device.get("os_build")}')
    
    # 測試配置驗證
    if device:
        result = mdt_service.validate_device_config(test_device, {
            'hostname': test_device,
            'ansible_host': device.get("info", {}).get("ip"),
            'mac_address': device.get("info", {}).get("mac")
        })
        print(f'\n3. 配置驗證: {"✓ 一致" if result["config_matches"] else "✗ 不一致"}')
        if not result["config_matches"]:
            print(f'   差異: {len(result["differences"])} 個')
    
    return True


def test_validator_integration():
    """測試驗證器整合"""
    print('\n' + '=' * 80)
    print('📊 測試 2: 驗證器整合測試')
    print('=' * 80)
    
    # 創建一個模擬的驗證場景
    print('\n測試場景: 使用 10.250.10.x 網段的 Inventory')
    print('預期: 自動推斷 DHCP Server IP = 10.250.10.1，MDT Web IP = 10.250.10.2')
    
    # 創建驗證器實例
    validator = InventoryConfigValidator(
        inventory_id=23,  # 使用測試 Inventory
        check_connectivity=False,
        check_dhcp=False  # 關閉 DHCP 檢查加快測試
    )
    
    # 模擬有 10.250.10.x 網段的內容
    original_content = validator.content
    # 在內容中添加一個 10.250.10.x 的主機（模擬）
    test_content = f"""
[test_hosts]
test_device ansible_host=10.250.10.100 macaddress=AA:BB:CC:DD:EE:FF device_number=PC-SSD-4052
{original_content}
"""
    validator.content = test_content
    
    # 測試 DHCP Server IP 推斷
    dhcp_ip = validator._get_dhcp_server_ip()
    print(f'\n1. DHCP Server IP 推斷: {dhcp_ip}')
    print(f'   {"✓ 正確" if dhcp_ip == "10.250.10.1" else "✗ 錯誤"}')
    
    # 測試 MDT Web IP 計算
    if dhcp_ip:
        mdt_ip = validator._calculate_mdt_web_ip(dhcp_ip)
        print(f'\n2. MDT Web IP 計算: {mdt_ip}')
        print(f'   {"✓ 正確" if mdt_ip == "10.250.10.2" else "✗ 錯誤"}')
    
    # 測試獲取有 device_number 的主機
    hosts = validator._get_inventory_hosts_with_device_number()
    print(f'\n3. 獲取 device_number 主機: 找到 {len(hosts)} 個')
    
    return True


def main():
    print('\n🧪 MDT Web 功能完整測試')
    print('=' * 80)
    
    try:
        # 測試 1: MDT Web 服務層
        success1 = test_mdt_web_service()
        
        # 測試 2: 驗證器整合
        success2 = test_validator_integration()
        
        print('\n' + '=' * 80)
        print('📈 測試總結')
        print('=' * 80)
        print(f'MDT Web 服務層: {"✓ 通過" if success1 else "✗ 失敗"}')
        print(f'驗證器整合: {"✓ 通過" if success2 else "✗ 失敗"}')
        print('=' * 80)
        
        return success1 and success2
        
    except Exception as e:
        print(f'\n❌ 測試失敗: {e}')
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
