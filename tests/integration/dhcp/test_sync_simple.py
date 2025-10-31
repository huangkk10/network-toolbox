#!/usr/bin/env python
"""簡單的同步測試腳本"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.models import DHCPServer, DHCPLease
from api.ssh_powershell_service import WindowsSSHPowerShellService

def main():
    server = DHCPServer.objects.get(ip_address='10.250.50.1')
    
    print("🔄 開始同步 Windows DHCP 租約...")
    print(f"   Server: {server.name} ({server.ip_address})")
    print()
    
    with WindowsSSHPowerShellService(server) as service:
        result = service.sync_leases_to_db()
    
    print("\n" + "="*60)
    print("✅ 同步完成！")
    print("="*60)
    print(f"📊 統計結果:")
    print(f"   總數: {result['total']}")
    print(f"   新增: {result['created']}")
    print(f"   更新: {result['updated']}")
    print(f"   跳過: {result['skipped']}")
    print(f"   錯誤: {result['errors']}")
    
    server.refresh_from_db()
    print(f"\n📈 Server 最新狀態:")
    print(f"   總租約數: {server.total_leases}")
    print(f"   活躍租約: {server.active_leases}")
    print(f"   上次同步: {server.last_sync_at}")
    
    if result['created'] > 0 or result['updated'] > 0:
        leases = DHCPLease.objects.filter(server=server).order_by('-created_at')[:10]
        print(f"\n📝 最新租約 (前 10 筆):")
        print(f"{'IP 地址':<15} | {'MAC 地址':<17} | {'主機名稱':<30}")
        print("-" * 65)
        for lease in leases:
            hostname = lease.hostname[:28] if lease.hostname else '(無)'
            print(f"{lease.ip_address:<15} | {lease.mac_address:<17} | {hostname:<30}")

if __name__ == '__main__':
    main()
