#!/usr/bin/env python3
"""
根據 IP 子網為 Switch 分配連接的設備
假設：同一個 /24 子網的設備可能連接到同一台 Switch
"""
import os
import django
import sys
from collections import defaultdict
import ipaddress

sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.models import DHCPLease, NetworkSwitch
from api.serializers import DHCPLeaseSerializer


def get_subnet(ip_address, prefix_length=24):
    """獲取 IP 的子網"""
    try:
        network = ipaddress.ip_network(f"{ip_address}/{prefix_length}", strict=False)
        return str(network)
    except:
        return None


def assign_devices_by_subnet():
    """根據子網為 Switch 分配設備"""
    
    print("=" * 80)
    print("根據 IP 子網為 Switch 分配連接設備")
    print("=" * 80)
    
    # 獲取所有 Switch
    switches = NetworkSwitch.objects.all()
    
    if not switches:
        print("❌ 沒有找到任何 Switch")
        return
    
    print(f"\n找到 {switches.count()} 台 Switch")
    
    # 按子網組織 Switch
    subnet_switches = defaultdict(list)
    
    for switch in switches:
        if switch.ip_address:
            subnet = get_subnet(switch.ip_address)
            if subnet:
                subnet_switches[subnet].append(switch)
                print(f"  {switch.name:20} {switch.ip_address:15} → 子網: {subnet}")
    
    print(f"\n找到 {len(subnet_switches)} 個不同的子網")
    
    # 為每個子網的 Switch 分配設備
    total_assigned = 0
    
    for subnet, switches_in_subnet in subnet_switches.items():
        print(f"\n{'=' * 80}")
        print(f"處理子網: {subnet}")
        print(f"此子網有 {len(switches_in_subnet)} 台 Switch")
        print(f"{'=' * 80}")
        
        # 獲取此子網的所有設備（排除 Switch 本身）
        switch_macs = [s.mac_address for s in switches_in_subnet]
        
        # 獲取子網內的所有租約
        network = ipaddress.ip_network(subnet)
        all_leases = DHCPLease.objects.filter(is_active=True)
        
        subnet_devices = []
        for lease in all_leases:
            try:
                ip = ipaddress.ip_address(lease.ip_address)
                if ip in network and lease.mac_address not in switch_macs:
                    # 獲取 vendor 資訊
                    serializer = DHCPLeaseSerializer(lease)
                    vendor = serializer.data.get('vendor', '')
                    
                    subnet_devices.append({
                        'lease': lease,
                        'vendor': vendor,
                    })
            except:
                continue
        
        print(f"找到 {len(subnet_devices)} 個設備（排除 Switch 本身）")
        
        if not subnet_devices:
            continue
        
        # 如果只有一台 Switch，直接分配所有設備
        if len(switches_in_subnet) == 1:
            switch = switches_in_subnet[0]
            print(f"\n將所有設備分配給: {switch.name}")
            
            for device in subnet_devices:
                lease = device['lease']
                lease.remote_id = switch.remote_id
                lease.circuit_id = f"subnet-{subnet}"
                lease.relay_agent_info = f"SubnetBased,RemoteID={switch.remote_id}"
                lease.save()
                print(f"  ├─ {lease.ip_address:15} {lease.mac_address:17} [{device['vendor']}]")
                total_assigned += 1
            
            # 更新 Switch 統計
            switch.update_statistics()
            print(f"  └─ 統計: {switch.connected_devices} 個設備")
        
        else:
            # 多台 Switch 的情況：平均分配或根據 IP 範圍分配
            print(f"\n多台 Switch，根據 IP 範圍分配...")
            
            # 按 IP 排序設備
            subnet_devices.sort(key=lambda x: ipaddress.ip_address(x['lease'].ip_address))
            
            # 計算每台 Switch 應該分配多少設備
            devices_per_switch = len(subnet_devices) // len(switches_in_subnet)
            
            for idx, switch in enumerate(switches_in_subnet):
                start_idx = idx * devices_per_switch
                end_idx = start_idx + devices_per_switch if idx < len(switches_in_subnet) - 1 else len(subnet_devices)
                
                assigned_devices = subnet_devices[start_idx:end_idx]
                
                print(f"\n分配給 {switch.name} ({len(assigned_devices)} 個設備):")
                
                for device in assigned_devices:
                    lease = device['lease']
                    lease.remote_id = switch.remote_id
                    lease.circuit_id = f"subnet-{subnet}-sw{idx+1}"
                    lease.relay_agent_info = f"SubnetBased,RemoteID={switch.remote_id}"
                    lease.save()
                    print(f"  ├─ {lease.ip_address:15} {lease.mac_address:17} [{device['vendor']}]")
                    total_assigned += 1
                
                # 更新 Switch 統計
                switch.update_statistics()
                print(f"  └─ 統計: {switch.connected_devices} 個設備")
    
    print(f"\n{'=' * 80}")
    print(f"✅ 完成！")
    print(f"   總共為 {total_assigned} 個設備分配了 Switch")
    print(f"\n💡 現在刷新網頁查看 Switch 詳情，可以看到連接的設備！")
    print(f"{'=' * 80}")


if __name__ == '__main__':
    assign_devices_by_subnet()
