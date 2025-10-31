#!/usr/bin/env python3
"""
DHCP SSH 連接和資料同步測試腳本
"""

import os
import sys
import django

# 設定 Django 環境
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.models import DHCPServer, DHCPLease
from api.services import DHCPServerSSH, DHCPLeaseParser, DHCPDataService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_ssh_connection(server):
    """測試 SSH 連接"""
    print(f"\n{'='*60}")
    print(f"測試 SSH 連接到: {server.ip_address}")
    print(f"{'='*60}")
    
    ssh = DHCPServerSSH(
        host=server.ip_address,
        port=server.ssh_port,
        username=server.ssh_username,
        password=server.ssh_password if server.ssh_password else None,
        key_file=server.ssh_key_file if server.ssh_key_file else None
    )
    
    if ssh.connect():
        print("✅ SSH 連接成功！")
        
        # 測試執行簡單指令
        output, error = ssh.execute_command('hostname')
        if output:
            print(f"✅ 遠端主機名稱: {output.strip()}")
        
        # 測試讀取租約檔案
        output, error = ssh.execute_command(f'cat {server.dhcp_leases_path}')
        if output:
            print(f"✅ 租約檔案讀取成功，大小: {len(output)} bytes")
            print(f"前 500 字元預覽:")
            print("-" * 60)
            print(output[:500])
            print("-" * 60)
            return output
        else:
            print(f"❌ 讀取租約檔案失敗: {error}")
            return None
        
        ssh.close()
    else:
        print("❌ SSH 連接失敗！")
        return None


def test_lease_parsing(content):
    """測試租約解析"""
    print(f"\n{'='*60}")
    print(f"測試租約解析")
    print(f"{'='*60}")
    
    if not content:
        print("⚠️  沒有內容可解析")
        return []
    
    leases = DHCPLeaseParser.parse_leases_file(content)
    
    print(f"✅ 解析到 {len(leases)} 筆租約")
    
    if leases:
        print(f"\n前 3 筆租約範例：")
        for i, lease in enumerate(leases[:3], 1):
            print(f"\n租約 {i}:")
            print(f"  IP: {lease.get('ip_address')}")
            print(f"  MAC: {lease.get('mac_address')}")
            print(f"  主機名稱: {lease.get('hostname', 'N/A')}")
            print(f"  開始時間: {lease.get('lease_start')}")
            print(f"  結束時間: {lease.get('lease_end')}")
            print(f"  是否活躍: {lease.get('is_active')}")
    
    return leases


def test_sync_to_database(server):
    """測試同步到資料庫"""
    print(f"\n{'='*60}")
    print(f"測試同步到資料庫")
    print(f"{'='*60}")
    
    service = DHCPDataService(server)
    result = service.sync_leases_to_db()
    
    print(f"✅ 同步完成！")
    print(f"  總計: {result['total']}")
    print(f"  新增: {result['created']}")
    print(f"  更新: {result['updated']}")
    print(f"  錯誤: {result['errors']}")
    
    return result


def verify_database_data():
    """驗證資料庫資料"""
    print(f"\n{'='*60}")
    print(f"驗證資料庫資料")
    print(f"{'='*60}")
    
    total_leases = DHCPLease.objects.count()
    active_leases = DHCPLease.objects.filter(is_active=True).count()
    
    print(f"✅ 資料庫中的租約統計：")
    print(f"  總租約數: {total_leases}")
    print(f"  活躍租約: {active_leases}")
    print(f"  已過期租約: {total_leases - active_leases}")
    
    if total_leases > 0:
        print(f"\n最近 5 筆租約：")
        recent = DHCPLease.objects.all()[:5]
        for lease in recent:
            status = "活躍" if lease.is_active else "過期"
            print(f"  {lease.ip_address} | {lease.mac_address} | {status}")


def main():
    """主測試流程"""
    print("\n" + "="*60)
    print("DHCP SSH 整合測試")
    print("="*60)
    
    # 1. 檢查是否有 DHCP Server
    servers = DHCPServer.objects.all()
    
    if not servers.exists():
        print("❌ 資料庫中沒有 DHCP Server，請先新增！")
        return
    
    server = servers.first()
    print(f"\n使用 Server: {server.name} ({server.ip_address})")
    
    # 檢查 SSH 認證資訊
    if not server.ssh_password and not server.ssh_key_file:
        print("\n⚠️  警告：未配置 SSH 密碼或金鑰！")
        print("請在 Django Admin 中設定 SSH 認證資訊：")
        print(f"  http://localhost/admin/api/dhcpserver/{server.id}/change/")
        
        print("\n是否使用測試模式（手動輸入密碼）？[y/N]: ", end='')
        choice = input().lower()
        
        if choice == 'y':
            password = input(f"請輸入 {server.ssh_username}@{server.ip_address} 的密碼: ")
            server.ssh_password = password
        else:
            print("測試取消")
            return
    
    # 2. 測試 SSH 連接
    content = test_ssh_connection(server)
    
    if not content:
        print("\n❌ 無法獲取租約資料，測試終止")
        return
    
    # 3. 測試租約解析
    leases = test_lease_parsing(content)
    
    # 4. 測試同步到資料庫
    if leases:
        result = test_sync_to_database(server)
        
        # 5. 驗證資料庫資料
        verify_database_data()
    
    print("\n" + "="*60)
    print("測試完成！")
    print("="*60)
    
    # 6. 顯示 API 測試指令
    print("\n您現在可以測試 API 端點：")
    print(f"  curl http://localhost/api/dhcp-analytics/overview/?server={server.id}")
    print(f"  curl http://localhost/api/dhcp-analytics/trend/?server={server.id}")
    print(f"  curl http://localhost/api/dhcp-analytics/recent-leases/?server={server.id}")


if __name__ == '__main__':
    main()
