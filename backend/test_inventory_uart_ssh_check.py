#!/usr/bin/env python
"""
測試 Ansible Inventory UART SSH 連線檢查功能

使用方式：
python test_inventory_uart_ssh_check.py <inventory_id>
"""

import sys
import os
import django

# Setup Django
sys.path.insert(0, '/home/owner/Codes/network-toolbox/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from library.services.inventory_config_validator import InventoryConfigValidator
import json

def test_uart_ssh_check(inventory_id):
    """測試 Inventory UART SSH 檢查功能"""
    print(f"🔍 測試 Inventory ID: {inventory_id} 的配置檢查...")
    print("=" * 80)
    
    validator = InventoryConfigValidator(
        inventory_id=inventory_id,
        check_connectivity=False,
        check_dhcp=True
    )
    result = validator.validate()
    
    print(f"\n📊 檢查結果：")
    print(f"   整體狀態: {result['overall_status']}")
    print(f"   總檢查項: {result['summary']['total_checks']}")
    print(f"   通過: {result['summary']['passed']}")
    print(f"   警告: {result['summary']['warnings']}")
    print(f"   錯誤: {result['summary']['errors']}")
    
    print(f"\n🔌 UART SSH 連線檢查結果：")
    print("=" * 80)
    
    uart_ssh = result['checks'].get('uart_ssh', {})
    
    print(f"   狀態: {uart_ssh.get('status', 'unknown')}")
    print(f"   訊息: {uart_ssh.get('message', 'N/A')}")
    print(f"   值: {uart_ssh.get('value', 'N/A')}")
    
    if uart_ssh.get('details'):
        print(f"\n   詳細資訊:")
        details = uart_ssh['details']
        print(f"     - 總 UART 主機: {details.get('total', 0)}")
        print(f"     - 成功連接: {details.get('successful', 0)}")
        print(f"     - 失敗連接: {details.get('failed', 0)}")
        print(f"     - 跳過檢查: {details.get('skipped', 0)}")
        
        connections = details.get('connections', [])
        if connections:
            print(f"\n   連接詳情（共 {len(connections)} 個）:")
            for i, conn in enumerate(connections[:10], 1):  # 只顯示前 10 個
                status_icon = {
                    'success': '✅',
                    'error': '❌',
                    'warning': '⚠️'
                }.get(conn['status'], '❓')
                
                print(f"\n     [{i}] {status_icon} {conn['hostname']}")
                print(f"         UART 主機: {conn['uart_host']}")
                print(f"         狀態: {conn['status']}")
                print(f"         訊息: {conn['message']}")
                
                if conn.get('details'):
                    conn_details = conn['details']
                    if conn_details.get('uart_ip'):
                        print(f"         IP: {conn_details['uart_ip']}")
                    if conn_details.get('uart_user'):
                        print(f"         User: {conn_details['uart_user']}")
                    if conn_details.get('uart_port'):
                        print(f"         Port: {conn_details['uart_port']}")
                    if conn_details.get('error'):
                        print(f"         Error: {conn_details['error']}")
            
            if len(connections) > 10:
                print(f"\n     ...還有 {len(connections) - 10} 個連接結果")
    
    if uart_ssh.get('suggestions'):
        print(f"\n   建議:")
        for suggestion in uart_ssh['suggestions']:
            print(f"     - {suggestion}")
    
    print("\n" + "=" * 80)
    print("\n💾 完整結果（JSON 格式）:")
    print(json.dumps(uart_ssh, ensure_ascii=False, indent=2))
    
    print("\n✅ 測試完成！")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ 請提供 Inventory ID")
        print(f"使用方式: python {sys.argv[0]} <inventory_id>")
        print("\n💡 提示：")
        print("   - 確保 Inventory 中有配置 uart_host 的主機")
        print("   - UART 主機需要配置 ansible_user 和 ansible_password")
        print("   - UART 主機需要在線上且 SSH 服務正常運行")
        sys.exit(1)
    
    try:
        inventory_id = int(sys.argv[1])
        test_uart_ssh_check(inventory_id)
    except ValueError:
        print(f"❌ 無效的 Inventory ID: {sys.argv[1]}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
