#!/usr/bin/env python3
"""
建立測試租約資料
用於測試 DHCP Analytics API 功能
"""

import os
import sys
import django
from datetime import datetime, timedelta

# 設定 Django 環境
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.models import DHCPServer, DHCPLease
from django.utils import timezone


def create_test_data():
    """建立測試資料"""
    
    print("="*60)
    print("建立 DHCP 測試資料")
    print("="*60)
    
    # 1. 確保有 DHCP Server
    server, created = DHCPServer.objects.get_or_create(
        ip_address='10.250.50.1',
        defaults={
            'name': '測試 DHCP Server',
            'description': '用於測試的 DHCP Server',
            'status': 'online',
            'pool_usage': 65.5,
            'ssh_port': 22,
            'ssh_username': 'root',
        }
    )
    
    if created:
        print(f"✅ 建立 DHCP Server: {server.name}")
    else:
        print(f"ℹ️  使用現有 DHCP Server: {server.name}")
    
    # 2. 清除舊的測試資料
    old_count = DHCPLease.objects.filter(server=server).count()
    if old_count > 0:
        DHCPLease.objects.filter(server=server).delete()
        print(f"🗑️  清除 {old_count} 筆舊資料")
    
    # 3. 建立測試租約資料
    now = timezone.now()
    test_leases = []
    
    # 活躍租約（320 筆）
    print("\n建立活躍租約...")
    for i in range(1, 321):
        lease = DHCPLease(
            server=server,
            ip_address=f'192.168.{(i // 256) + 1}.{i % 256}',
            mac_address=f'00:1a:2b:3c:{(i // 256):02x}:{(i % 256):02x}',
            hostname=f'host-{i:03d}',
            lease_start=now - timedelta(hours=i % 24),
            lease_end=now + timedelta(hours=24 - (i % 12)),
            is_active=True,
        )
        test_leases.append(lease)
    
    # 已過期租約（130 筆）
    print("建立已過期租約...")
    for i in range(321, 451):
        lease = DHCPLease(
            server=server,
            ip_address=f'192.168.{(i // 256) + 1}.{i % 256}',
            mac_address=f'00:1a:2b:3c:{(i // 256):02x}:{(i % 256):02x}',
            hostname=f'host-{i:03d}',
            lease_start=now - timedelta(days=i % 7 + 1),
            lease_end=now - timedelta(hours=i % 48),
            is_active=False,
        )
        test_leases.append(lease)
    
    # 批次建立
    DHCPLease.objects.bulk_create(test_leases)
    
    # 4. 更新 Server 統計
    server.total_leases = DHCPLease.objects.filter(server=server).count()
    server.active_leases = DHCPLease.objects.filter(server=server, is_active=True).count()
    server.last_sync_at = now
    server.save()
    
    print(f"\n✅ 成功建立 {len(test_leases)} 筆測試租約")
    print(f"   活躍租約: {server.active_leases}")
    print(f"   總租約數: {server.total_leases}")
    
    # 5. 驗證資料
    print("\n" + "="*60)
    print("資料驗證")
    print("="*60)
    
    stats = {
        'total': DHCPLease.objects.count(),
        'active': DHCPLease.objects.filter(is_active=True).count(),
        'expired': DHCPLease.objects.filter(is_active=False).count(),
    }
    
    print(f"總租約數: {stats['total']}")
    print(f"活躍租約: {stats['active']}")
    print(f"已過期租約: {stats['expired']}")
    
    # 6. 顯示最近的幾筆租約
    print("\n最近 5 筆租約：")
    recent = DHCPLease.objects.all()[:5]
    for lease in recent:
        status = "✅ 活躍" if lease.is_active else "⏰ 過期"
        print(f"  {lease.ip_address:15s} | {lease.mac_address:17s} | {lease.hostname:15s} | {status}")
    
    print("\n" + "="*60)
    print("測試資料建立完成！")
    print("="*60)
    
    print("\n現在您可以測試 API：")
    print(f"  curl http://localhost/api/dhcp-analytics/overview/?server=all")
    print(f"  curl http://localhost/api/dhcp-analytics/overview/?server={server.id}")
    print(f"  curl http://localhost/api/dhcp-analytics/trend/?server={server.id}")
    print(f"  curl http://localhost/api/dhcp-analytics/recent-leases/?server={server.id}")
    
    print("\n或訪問前端頁面：")
    print(f"  http://localhost/dhcp-analytics")


if __name__ == '__main__':
    create_test_data()
