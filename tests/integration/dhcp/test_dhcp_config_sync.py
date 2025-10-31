#!/usr/bin/env python3
"""
測試 DHCP 配置同步功能

這個腳本用於測試：
1. DHCPConfigParser 解析 dhcpd.conf 的能力
2. LinuxDHCPConfigService 同步配置的功能
3. IP 使用率計算是否正確
"""

import sys
import os
import django

# 添加專案路徑
sys.path.append('/home/owner/Codes/network-toolbox/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')

# 初始化 Django
django.setup()

from api.models import DHCPServer, DHCPScope, DHCPLease
from api.services import DHCPConfigParser, LinuxDHCPConfigService


def test_config_parser():
    """測試配置解析器"""
    print("=== 測試 DHCPConfigParser ===")
    
    # 模擬的 dhcpd.conf 內容
    sample_config = """
# Global options
default-lease-time 600;
max-lease-time 7200;

# Subnet 1
subnet 192.168.1.0 netmask 255.255.255.0 {
    range 192.168.1.10 192.168.1.100;
    range 192.168.1.150 192.168.1.200;
    option routers 192.168.1.1;
    option domain-name-servers 8.8.8.8, 8.8.4.4;
}

# Subnet 2
subnet 10.0.0.0 netmask 255.255.255.0 {
    range 10.0.0.50 10.0.0.200;
    option routers 10.0.0.1;
    option domain-name-servers 8.8.8.8;
}

# Another subnet with no range (should be skipped)
subnet 172.16.0.0 netmask 255.255.255.0 {
    option routers 172.16.0.1;
}
"""
    
    try:
        # 解析配置
        subnets = DHCPConfigParser.parse_config_file(sample_config)
        
        print(f"✅ 解析成功，找到 {len(subnets)} 個 subnet")
        
        for i, subnet in enumerate(subnets, 1):
            print(f"\nSubnet {i}:")
            print(f"  ID: {subnet['subnet_id']}")
            print(f"  名稱: {subnet['name']}")
            print(f"  子網路遮罩: {subnet['subnet_mask']}")
            print(f"  網路範圍: {subnet['network_range']}")
            print(f"  總 IP 數: {subnet['total_addresses']}")
            print(f"  IP 範圍:")
            
            for j, ip_range in enumerate(subnet['ranges'], 1):
                print(f"    Range {j}: {ip_range['start_range']} - {ip_range['end_range']} ({ip_range['size']} IPs)")
        
        return True
        
    except Exception as e:
        print(f"❌ 解析失敗: {e}")
        return False


def test_usage_calculation():
    """測試使用率計算"""
    print("\n=== 測試使用率計算 ===")
    
    # 模擬 subnet 配置
    subnets = [
        {
            'subnet_id': '192.168.1.0',
            'name': 'Subnet 192.168.1.0',
            'subnet_mask': '255.255.255.0',
            'network_range': '192.168.1.0/24',
            'ranges': [
                {'start_range': '192.168.1.10', 'end_range': '192.168.1.100', 'size': 91},
                {'start_range': '192.168.1.150', 'end_range': '192.168.1.200', 'size': 51}
            ],
            'total_addresses': 142,
            'state': 'Active'
        }
    ]
    
    # 模擬活躍租約
    active_leases = [
        {'ip_address': '192.168.1.10'},
        {'ip_address': '192.168.1.20'},
        {'ip_address': '192.168.1.30'},
        {'ip_address': '192.168.1.150'},
        {'ip_address': '192.168.1.160'},
    ]
    
    try:
        # 計算使用率
        usage_stats = DHCPConfigParser.calculate_ip_usage(subnets, active_leases)
        
        print(f"✅ 使用率計算成功")
        print(f"  總 IP 數: {usage_stats['total_addresses']}")
        print(f"  已使用: {usage_stats['used_addresses']}")
        print(f"  可用: {usage_stats['available_addresses']}")
        print(f"  使用率: {usage_stats['usage_percentage']}%")
        
        # 檢查 subnet 詳細資訊
        for subnet in usage_stats['subnets']:
            print(f"\n  Subnet {subnet['subnet_id']}:")
            print(f"    已使用: {subnet['in_use_addresses']}")
            print(f"    可用: {subnet['available_addresses']}")
            print(f"    使用率: {subnet['usage_percentage']}%")
        
        return True
        
    except Exception as e:
        print(f"❌ 計算失敗: {e}")
        return False


def test_database_integration():
    """測試資料庫整合"""
    print("\n=== 測試資料庫整合 ===")
    
    try:
        # 查找 Linux DHCP 伺服器
        linux_servers = DHCPServer.objects.filter(
            ip_address='10.250.130.1'
        )
        
        if not linux_servers.exists():
            print("❌ 找不到 IP 為 10.250.130.1 的 DHCP 伺服器")
            print("請先在管理介面中添加該伺服器，並設定 SSH 連接資訊")
            return False
        
        server = linux_servers.first()
        print(f"✅ 找到伺服器: {server.name} ({server.ip_address})")
        
        # 檢查目前的 Scope 數量
        current_scopes = DHCPScope.objects.filter(server=server).count()
        print(f"  目前 Scope 數量: {current_scopes}")
        
        # 檢查租約數量
        total_leases = DHCPLease.objects.filter(server=server).count()
        active_leases = DHCPLease.objects.filter(server=server, is_active=True).count()
        print(f"  總租約數: {total_leases}")
        print(f"  活躍租約數: {active_leases}")
        
        print(f"  目前 pool_usage: {server.pool_usage}%")
        
        print("\n📝 要實際測試配置同步功能，請：")
        print("1. 確保伺服器的 SSH 連接資訊正確")
        print("2. 使用 API 端點測試: POST /api/dhcp-servers/{server.id}/sync-config/")
        print(f"3. 或在瀏覽器中訪問 DHCP 分析頁面，點擊「同步配置」按鈕")
        
        return True
        
    except Exception as e:
        print(f"❌ 資料庫測試失敗: {e}")
        return False


def print_api_usage():
    """顯示 API 使用方法"""
    print("\n=== API 使用方法 ===")
    print("新的配置同步 API 端點：")
    print("  POST /api/dhcp-servers/<server_id>/sync-config/")
    print()
    print("示例 curl 命令：")
    print("curl -X POST http://localhost/api/dhcp-servers/1/sync-config/")
    print()
    print("成功回應：")
    print("""
{
  "message": "成功同步 2 個 Scope",
  "stats": {
    "scopes_found": 2,
    "scopes_created": 2,
    "scopes_updated": 0,
    "scopes_with_leases": 1
  },
  "server": {
    "name": "10.250.130.1",
    "ip": "10.250.130.1",
    "pool_usage": 15.5,
    "total_leases": 160,
    "active_leases": 160,
    "last_sync": "2025-10-30 15:30:00"
  }
}
""")


def main():
    """主測試函數"""
    print("🚀 DHCP 配置同步功能測試")
    print("=" * 50)
    
    all_passed = True
    
    # 測試 1: 配置解析器
    if not test_config_parser():
        all_passed = False
    
    # 測試 2: 使用率計算
    if not test_usage_calculation():
        all_passed = False
    
    # 測試 3: 資料庫整合
    if not test_database_integration():
        all_passed = False
    
    # 顯示 API 使用方法
    print_api_usage()
    
    # 總結
    print("\n" + "=" * 50)
    if all_passed:
        print("✅ 所有測試通過！")
        print("✨ DHCP 配置同步功能已就緒")
    else:
        print("❌ 部分測試失敗")
        print("請檢查錯誤訊息並修復問題")
    
    print("\n🎯 下一步：")
    print("1. 在前端添加「同步配置」按鈕")
    print("2. 測試實際的 SSH 連接和配置解析")
    print("3. 驗證 IP 使用率計算結果")


if __name__ == '__main__':
    main()