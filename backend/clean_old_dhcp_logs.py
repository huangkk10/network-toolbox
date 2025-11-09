#!/usr/bin/env python
"""
清理 DHCP 舊日誌並重新同步

此腳本會：
1. 刪除所有 DHCP 日誌
2. 觸發重新同步

執行方式：
docker exec nt-django python /app/clean_old_dhcp_logs.py
"""

import os
import sys
import django

# 設置 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.models import DHCPLog, DHCPServer
from django.db import transaction

def clean_and_resync():
    """清理舊日誌並重新同步"""
    
    print("=" * 60)
    print("DHCP 日誌清理與重新同步")
    print("=" * 60)
    print()
    
    # 1. 統計現有日誌
    total_logs = DHCPLog.objects.count()
    print(f"📊 現有日誌總數: {total_logs}")
    
    if total_logs == 0:
        print("✅ 沒有舊日誌，無需清理")
        return
    
    # 顯示各伺服器的日誌數量
    print("\n各伺服器日誌數量:")
    for server in DHCPServer.objects.all():
        count = DHCPLog.objects.filter(server=server).count()
        print(f"  - {server.name} ({server.ip_address}): {count} 筆")
    
    # 2. 詢問確認
    print()
    response = input("⚠️  是否刪除所有 DHCP 日誌？ (yes/no): ").strip().lower()
    
    if response != 'yes':
        print("❌ 已取消操作")
        return
    
    # 3. 刪除所有日誌
    print("\n🗑️  正在刪除舊日誌...")
    with transaction.atomic():
        deleted_count, _ = DHCPLog.objects.all().delete()
    
    print(f"✅ 已刪除 {deleted_count} 筆日誌")
    
    # 4. 提示重新同步
    print()
    print("=" * 60)
    print("✅ 清理完成！")
    print("=" * 60)
    print()
    print("下一步：")
    print("1. 進入 DHCP Server 分析 → 日誌查看")
    print("2. 選擇你的 DHCP Server")
    print("3. 點擊「同步日誌」按鈕")
    print()
    print("新同步的日誌將使用正確的時區設定 (Taipei, UTC+8)")
    print()

if __name__ == '__main__':
    try:
        clean_and_resync()
    except Exception as e:
        print(f"❌ 錯誤: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
