#!/usr/bin/env python3
"""
為 Server ID 2 (10.250.130.1) 創建 Switch 測試資料
"""
import os
import django
import sys
import random

# Django 設定
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.models import DHCPServer, DHCPLease, NetworkSwitch, SwitchPort


def main():
    print("=" * 60)
    print("為 Server 2 創建 Switch 測試資料")
    print("=" * 60)
    
    # 獲取 Server ID 2
    try:
        server = DHCPServer.objects.get(id=2)
        print(f"✅ 使用 DHCP Server: {server.name} (ID: {server.id})")
    except DHCPServer.DoesNotExist:
        print("❌ 錯誤：Server ID 2 不存在")
        return
    
    # 創建 Switch
    switch, created = NetworkSwitch.objects.update_or_create(
        remote_id='00:2a:d4:45:67:89',
        defaults={
            'name': 'Office-Switch-01',
            'mac_address': '00:2a:d4:45:67:89',
            'ip_address': '10.250.130.10',
            'location': 'Main Office',
            'building': 'Building C',
            'floor': '3F',
            'status': 'active',
            'dhcp_server': server,
        }
    )
    
    action = "創建" if created else "更新"
    print(f"\n✅ {action} Switch: {switch.name}")
    
    # 創建端口
    ports = [
        {'circuit_id': 'gi0/0/1', 'port_number': '1', 'port_name': 'GigabitEthernet0/0/1'},
        {'circuit_id': 'gi0/0/2', 'port_number': '2', 'port_name': 'GigabitEthernet0/0/2'},
        {'circuit_id': 'gi0/0/5', 'port_number': '5', 'port_name': 'GigabitEthernet0/0/5'},
    ]
    
    # 獲取此 Server 的租約
    existing_leases = list(DHCPLease.objects.filter(server=server, is_active=True)[:15])
    if not existing_leases:
        print("⚠️  警告：此 Server 沒有活動租約")
        return
    
    print(f"📊 找到 {len(existing_leases)} 個活動租約")
    lease_index = 0
    device_count = 0
    
    for port_data in ports:
        port, port_created = SwitchPort.objects.update_or_create(
            switch=switch,
            circuit_id=port_data['circuit_id'],
            defaults={
                'port_number': port_data['port_number'],
                'port_name': port_data['port_name'],
                'status': 'up',
            }
        )
        print(f"  ├─ 端口: {port.port_name}")
        
        # 為每個端口分配 2-3 個設備
        devices_count = random.randint(2, 3)
        for _ in range(devices_count):
            if lease_index < len(existing_leases):
                lease = existing_leases[lease_index]
                lease.relay_agent_info = f"CircuitID={port_data['circuit_id']},RemoteID=00:2a:d4:45:67:89"
                lease.circuit_id = port_data['circuit_id']
                lease.remote_id = '00:2a:d4:45:67:89'
                lease.save()
                print(f"  │  └─ 設備: {lease.ip_address} ({lease.mac_address})")
                lease_index += 1
                device_count += 1
    
    # 更新統計
    switch.update_statistics()
    print(f"  └─ 統計: {switch.connected_devices} 個設備, {switch.active_ports} 個活動端口")
    
    print("\n" + "=" * 60)
    print("✅ 完成！")
    print(f"   已為 {server.name} 創建 1 個 Switch")
    print(f"   包含 {len(ports)} 個端口，{device_count} 個設備")
    print("\n💡 現在刷新網頁即可看到資料！")
    print("=" * 60)


if __name__ == '__main__':
    main()
