#!/usr/bin/env python3
"""
根據製造商自動識別和創建 Switch 記錄
"""
import os
import django
import sys

sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.models import DHCPServer, DHCPLease, NetworkSwitch, SwitchPort
from api.serializers import DHCPLeaseSerializer


# Switch 製造商關鍵字（不區分大小寫）
SWITCH_VENDOR_KEYWORDS = [
    'cisco', 'juniper', 'arista', 'extreme', 'huawei', 'h3c',
    'hewlett packard', 'hpe', 'dell', 'brocade', 'netgear',
    'd-link', 'tp-link', 'ubiquiti', 'mikrotik', 'zyxel',
    'switch', 'switching', 'ruijie', 'planet', 'edimax',
]


def is_switch_vendor(vendor):
    """判斷製造商是否為 Switch 廠商"""
    if not vendor:
        return False
    
    vendor_lower = vendor.lower()
    
    # 排除明確不是網路設備的製造商
    exclude_keywords = ['intel', 'realtek', 'broadcom', 'microsoft', 'apple', 
                       'samsung', 'lenovo', 'acer', 'gigabyte', 'msi']
    
    for exclude in exclude_keywords:
        if exclude in vendor_lower:
            return False
    
    # 檢查是否匹配 Switch 關鍵字
    for keyword in SWITCH_VENDOR_KEYWORDS:
        if keyword in vendor_lower:
            return True
    
    return False


def main():
    print("=" * 80)
    print("根據製造商自動識別 Switch")
    print("=" * 80)
    
    # 選擇 Server
    server_id = input("\n請輸入 DHCP Server ID (直接按 Enter 使用 ID=2): ").strip()
    server_id = int(server_id) if server_id else 2
    
    try:
        server = DHCPServer.objects.get(id=server_id)
        print(f"\n✅ 使用 DHCP Server: {server.name} (ID: {server.id})")
    except DHCPServer.DoesNotExist:
        print(f"❌ 錯誤：Server ID {server_id} 不存在")
        return
    
    # 獲取所有活動租約
    leases = DHCPLease.objects.filter(server=server, is_active=True)
    print(f"📊 找到 {leases.count()} 個活動租約")
    
    # 識別 Switch 設備
    print("\n正在識別 Switch 設備...")
    print("-" * 80)
    
    switch_devices = []
    
    for lease in leases:
        # 獲取 vendor
        serializer = DHCPLeaseSerializer(lease)
        vendor = serializer.data.get('vendor', '')
        
        if is_switch_vendor(vendor):
            switch_devices.append({
                'lease': lease,
                'vendor': vendor,
                'ip': lease.ip_address,
                'mac': lease.mac_address,
                'hostname': lease.hostname,
            })
            print(f"✅ Switch: {lease.ip_address:15} {lease.mac_address:17} [{vendor}]")
    
    if not switch_devices:
        print("\n⚠️  未找到任何 Switch 設備")
        print("提示：您可以修改 SWITCH_VENDOR_KEYWORDS 列表來添加更多製造商")
        return
    
    print(f"\n找到 {len(switch_devices)} 台 Switch 設備")
    
    # 自動創建（不需要確認）
    print(f"\n開始自動創建 Switch 記錄...")
    
    # 創建 Switch 記錄
    print("\n正在創建 Switch 記錄...")
    print("=" * 80)
    
    created_count = 0
    updated_count = 0
    
    for device in switch_devices:
        lease = device['lease']
        
        # 使用 MAC 地址作為 remote_id
        remote_id = lease.mac_address
        
        # 生成 Switch 名稱
        if lease.hostname:
            switch_name = lease.hostname
        else:
            switch_name = f"Switch-{lease.ip_address.replace('.', '-')}"
        
        # 創建或更新 Switch
        switch, created = NetworkSwitch.objects.update_or_create(
            remote_id=remote_id,
            defaults={
                'name': switch_name,
                'mac_address': lease.mac_address,
                'ip_address': lease.ip_address,
                'status': 'active',
                'dhcp_server': server,
            }
        )
        
        if created:
            created_count += 1
            print(f"✅ 創建: {switch.name} ({switch.ip_address})")
        else:
            updated_count += 1
            print(f"🔄 更新: {switch.name} ({switch.ip_address})")
        
        # 更新租約的 Option 82 資訊（使用 MAC 作為識別）
        lease.remote_id = remote_id
        lease.relay_agent_info = f"VendorBased,RemoteID={remote_id}"
        lease.save()
        
        # 更新統計
        switch.update_statistics()
    
    print("\n" + "=" * 80)
    print("✅ 完成！")
    print(f"   創建: {created_count} 個 Switch")
    print(f"   更新: {updated_count} 個 Switch")
    print(f"   總計: {len(switch_devices)} 個 Switch")
    print("\n💡 現在刷新網頁即可看到資料！")
    print("   http://localhost → DHCP Server 分析 → Switch 管理")
    print("=" * 80)


if __name__ == '__main__':
    main()
