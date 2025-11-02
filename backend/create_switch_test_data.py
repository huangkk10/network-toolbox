#!/usr/bin/env python3
"""
創建 Switch 測試資料
模擬從 DHCP Option 82 識別的 Switch 和端口
"""
import os
import django
import sys
from datetime import datetime, timedelta
import random

# Django 設定
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.models import DHCPServer, DHCPLease, NetworkSwitch, SwitchPort


def create_test_switches():
    """創建測試 Switch 資料"""
    
    print("=" * 60)
    print("創建 Switch 測試資料")
    print("=" * 60)
    
    # 獲取 DHCP Server
    try:
        dhcp_server = DHCPServer.objects.first()
        if not dhcp_server:
            print("❌ 錯誤：未找到 DHCP Server")
            return
        print(f"✅ 使用 DHCP Server: {dhcp_server.name}")
    except Exception as e:
        print(f"❌ 獲取 DHCP Server 失敗: {e}")
        return
    
    # 測試 Switch 資料（模擬真實的網路設備）
    test_switches = [
        {
            'remote_id': '00:1a:a1:12:34:56',
            'name': 'Core-Switch-01',
            'mac_address': '00:1a:a1:12:34:56',
            'ip_address': '10.250.1.1',
            'location': 'Server Room',
            'building': 'Building A',
            'floor': '1F',
            'ports': [
                {'circuit_id': 'gi0/0/1', 'port_number': '1', 'port_name': 'GigabitEthernet0/0/1'},
                {'circuit_id': 'gi0/0/2', 'port_number': '2', 'port_name': 'GigabitEthernet0/0/2'},
                {'circuit_id': 'gi0/0/3', 'port_number': '3', 'port_name': 'GigabitEthernet0/0/3'},
                {'circuit_id': 'gi0/0/5', 'port_number': '5', 'port_name': 'GigabitEthernet0/0/5'},
            ]
        },
        {
            'remote_id': '00:1b:b2:23:45:67',
            'name': 'Access-Switch-02',
            'mac_address': '00:1b:b2:23:45:67',
            'ip_address': '10.250.1.2',
            'location': 'Office Area',
            'building': 'Building A',
            'floor': '2F',
            'ports': [
                {'circuit_id': 'fa0/1', 'port_number': '1', 'port_name': 'FastEthernet0/1'},
                {'circuit_id': 'fa0/2', 'port_number': '2', 'port_name': 'FastEthernet0/2'},
                {'circuit_id': 'fa0/5', 'port_number': '5', 'port_name': 'FastEthernet0/5'},
                {'circuit_id': 'fa0/10', 'port_number': '10', 'port_name': 'FastEthernet0/10'},
                {'circuit_id': 'fa0/15', 'port_number': '15', 'port_name': 'FastEthernet0/15'},
            ]
        },
        {
            'remote_id': '00:1c:c3:34:56:78',
            'name': 'Distribution-Switch-03',
            'mac_address': '00:1c:c3:34:56:78',
            'ip_address': '10.250.1.3',
            'location': 'MDF Room',
            'building': 'Building B',
            'floor': '1F',
            'ports': [
                {'circuit_id': 'te0/1/1', 'port_number': '1', 'port_name': 'TenGigabitEthernet0/1/1'},
                {'circuit_id': 'te0/1/2', 'port_number': '2', 'port_name': 'TenGigabitEthernet0/1/2'},
                {'circuit_id': 'gi0/0/10', 'port_number': '10', 'port_name': 'GigabitEthernet0/0/10'},
            ]
        },
    ]
    
    created_switches = 0
    created_ports = 0
    created_leases = 0
    
    # 獲取現有的租約（將為其添加 Option 82 資料）
    existing_leases = list(DHCPLease.objects.filter(is_active=True)[:50])
    lease_index = 0
    
    for switch_data in test_switches:
        try:
            # 創建 Switch
            switch, created = NetworkSwitch.objects.update_or_create(
                remote_id=switch_data['remote_id'],
                defaults={
                    'name': switch_data['name'],
                    'mac_address': switch_data['mac_address'],
                    'ip_address': switch_data['ip_address'],
                    'location': switch_data['location'],
                    'building': switch_data['building'],
                    'floor': switch_data['floor'],
                    'status': 'active',
                    'dhcp_server': dhcp_server,
                }
            )
            
            if created:
                created_switches += 1
                print(f"\n✅ 創建 Switch: {switch.name}")
            else:
                print(f"\n✅ 更新 Switch: {switch.name}")
            
            # 創建端口
            for port_data in switch_data['ports']:
                port, port_created = SwitchPort.objects.update_or_create(
                    switch=switch,
                    circuit_id=port_data['circuit_id'],
                    defaults={
                        'port_number': port_data['port_number'],
                        'port_name': port_data['port_name'],
                        'status': 'up',
                    }
                )
                
                if port_created:
                    created_ports += 1
                    print(f"  ├─ 端口: {port.port_name}")
                
                # 為一些租約添加 Option 82 資料（模擬設備連接到此端口）
                devices_on_port = random.randint(1, 3)  # 每個端口 1-3 個設備
                
                for _ in range(devices_on_port):
                    if lease_index < len(existing_leases):
                        lease = existing_leases[lease_index]
                        lease.relay_agent_info = f"CircuitID={port_data['circuit_id']},RemoteID={switch_data['remote_id']}"
                        lease.circuit_id = port_data['circuit_id']
                        lease.remote_id = switch_data['remote_id']
                        lease.save()
                        
                        created_leases += 1
                        print(f"  │  └─ 設備: {lease.ip_address} ({lease.mac_address})")
                        
                        lease_index += 1
            
            # 更新 Switch 統計
            switch.update_statistics()
            print(f"  └─ 統計: {switch.connected_devices} 個設備, {switch.active_ports} 個活動端口")
            
        except Exception as e:
            print(f"❌ 創建 Switch {switch_data['name']} 失敗: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("測試資料創建完成")
    print("=" * 60)
    print(f"✅ 創建 Switch: {created_switches} 個")
    print(f"✅ 創建端口: {created_ports} 個")
    print(f"✅ 更新租約: {created_leases} 個（添加 Option 82 資料）")
    print("\n💡 現在可以在網頁上查看 Switch 管理功能了！")
    print("   http://localhost → DHCP Server 分析 → Switch 管理 Tab")
    print("=" * 60)


if __name__ == '__main__':
    create_test_switches()
