#!/usr/bin/env python
"""
清理特定 DHCP Server 的舊日誌

此腳本會：
1. 選擇特定的 DHCP Server
2. 刪除該 Server 的所有日誌
3. 提示重新同步

執行方式：
docker exec nt-django python /app/clean_dhcp_logs_by_server.py
"""

import os
import sys
import django

# 設置 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.models import DHCPLog, DHCPServer
from django.db import transaction

def clean_logs_by_server():
    """清理特定伺服器的日誌"""
    
    print("=" * 60)
    print("DHCP 日誌清理（按伺服器）")
    print("=" * 60)
    print()
    
    # 1. 列出所有伺服器
    servers = DHCPServer.objects.all()
    
    if not servers:
        print("❌ 沒有 DHCP Server")
        return
    
    print("可用的 DHCP Servers:")
    for i, server in enumerate(servers, 1):
        count = DHCPLog.objects.filter(server=server).count()
        print(f"  [{i}] {server.name} ({server.ip_address}) - {count:,} 筆日誌")
    
    # 2. 選擇伺服器
    print()
    try:
        choice = input("請選擇要清理的伺服器編號 (或輸入 'all' 清理全部): ").strip()
        
        if choice.lower() == 'all':
            selected_servers = list(servers)
        else:
            index = int(choice) - 1
            if index < 0 or index >= len(servers):
                print("❌ 無效的選擇")
                return
            selected_servers = [servers[index]]
    
    except (ValueError, IndexError):
        print("❌ 無效的輸入")
        return
    
    # 3. 顯示將要刪除的日誌
    total_to_delete = sum(DHCPLog.objects.filter(server=s).count() for s in selected_servers)
    
    print()
    print(f"將要刪除的日誌:")
    for server in selected_servers:
        count = DHCPLog.objects.filter(server=server).count()
        print(f"  - {server.name}: {count:,} 筆")
    print(f"總計: {total_to_delete:,} 筆")
    
    # 4. 確認
    print()
    response = input(f"⚠️  確定要刪除這些日誌嗎？ (yes/no): ").strip().lower()
    
    if response != 'yes':
        print("❌ 已取消操作")
        return
    
    # 5. 刪除日誌
    print("\n🗑️  正在刪除日誌...")
    total_deleted = 0
    
    with transaction.atomic():
        for server in selected_servers:
            deleted_count, _ = DHCPLog.objects.filter(server=server).delete()
            total_deleted += deleted_count
            print(f"  ✓ {server.name}: 已刪除 {deleted_count:,} 筆")
    
    print(f"\n✅ 共刪除 {total_deleted:,} 筆日誌")
    
    # 6. 提示重新同步
    print()
    print("=" * 60)
    print("✅ 清理完成！")
    print("=" * 60)
    print()
    print("下一步：")
    print("1. 進入 DHCP Server 分析 → 日誌查看")
    print("2. 選擇你清理過的 DHCP Server")
    print("3. 點擊「同步日誌」按鈕")
    print()
    print("新同步的日誌將使用正確的時區設定 (Taipei, UTC+8)")
    print("Web 顯示時間 = Raw Log 時間 ✅")
    print()

if __name__ == '__main__':
    try:
        clean_logs_by_server()
    except KeyboardInterrupt:
        print("\n\n❌ 操作已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 錯誤: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
