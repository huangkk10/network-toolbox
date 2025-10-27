#!/usr/bin/env python
"""
快速測試 SSH + PowerShell 同步功能
直接執行：docker exec -i nt-django python test_ssh_sync.py
"""

import os
import sys
import django

# 設定 Django 環境
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.models import DHCPServer
from api.ssh_powershell_service import WindowsSSHPowerShellService

def main():
    print("=" * 60)
    print("  Windows DHCP Server SSH 同步測試")
    print("=" * 60)
    print()
    
    # 配置資訊
    DHCP_IP = '10.250.50.1'
    SSH_USER = 'administrator'
    SSH_PASSWORD = input(f"請輸入 {SSH_USER}@{DHCP_IP} 的密碼: ")
    
    print()
    print("[1/5] 檢查/創建 DHCP Server 記錄...")
    
    # 創建或更新 Server
    server, created = DHCPServer.objects.update_or_create(
        ip_address=DHCP_IP,
        defaults={
            'name': 'Windows DHCP Server',
            'description': 'SSH + PowerShell 自動同步',
            'status': 'online',
            'ssh_port': 22,
            'ssh_username': SSH_USER,
            'ssh_password': SSH_PASSWORD,
            'ssh_key_file': '',
        }
    )
    
    if created:
        print(f"✓ 創建新 Server: {server.name} (ID: {server.id})")
    else:
        print(f"✓ 更新現有 Server: {server.name} (ID: {server.id})")
    
    print()
    print("[2/5] 測試 SSH 連接...")
    
    try:
        with WindowsSSHPowerShellService(server) as service:
            print("✓ SSH 連接成功")
            
            print()
            print("[3/5] 獲取 DHCP Scope 列表...")
            scopes = service.get_dhcp_scopes()
            print(f"✓ 發現 {len(scopes)} 個 Scope:")
            
            for i, scope in enumerate(scopes[:5], 1):  # 只顯示前 5 個
                print(f"  {i}. {scope['ScopeId']} - {scope['Name']} ({scope['State']})")
            
            if len(scopes) > 5:
                print(f"  ... 還有 {len(scopes) - 5} 個 Scope")
            
            print()
            print("[4/5] 獲取租約資料...")
            leases = service.get_dhcp_leases()
            print(f"✓ 成功獲取 {len(leases)} 筆租約")
            
            # 顯示前 5 筆樣本
            print("\n租約樣本（前 5 筆）:")
            for i, lease in enumerate(leases[:5], 1):
                hostname = lease.get('HostName', '(無)')
                print(f"  {i}. IP: {lease['IPAddress']:<15} MAC: {lease['ClientId']:<20} Hostname: {hostname}")
            
            print()
            print("[5/5] 同步到資料庫...")
            result = service.sync_leases_to_db()
            
            print("✓ 同步完成！")
            print(f"\n統計資訊:")
            print(f"  - 總數: {result['total']}")
            print(f"  - 新增: {result['created']}")
            print(f"  - 更新: {result['updated']}")
            print(f"  - 跳過: {result['skipped']}")
            print(f"  - 錯誤: {result['errors']}")
            
            print()
            print("=" * 60)
            print("  測試成功！ ✓")
            print("=" * 60)
            print()
            print(f"Server 資訊:")
            print(f"  - 總租約數: {server.total_leases}")
            print(f"  - 活躍租約: {server.active_leases}")
            print(f"  - 上次同步: {server.last_sync_at}")
            
    except Exception as e:
        print(f"\n✗ 測試失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
