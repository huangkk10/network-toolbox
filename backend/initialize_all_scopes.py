#!/usr/bin/env python
"""
初始化所有 DHCP Server 的 Scope 數據

用途：
- 新部署系統後批次初始化所有伺服器
- 修復缺少 Scope 數據的伺服器
- 手動觸發全面同步

執行方式：
    python manage.py shell < initialize_all_scopes.py
    或
    docker exec nt-django python manage.py shell < initialize_all_scopes.py
"""

import sys
import django

# 設置 Django 環境
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.models import DHCPServer, DHCPScope
from api.tasks import sync_all_dhcp_scopes_task
import logging

logger = logging.getLogger(__name__)

def main():
    """主函數"""
    print("=" * 60)
    print("DHCP Server Scope 初始化腳本")
    print("=" * 60)
    print()
    
    # 1. 檢查所有 DHCP 伺服器
    all_servers = DHCPServer.objects.all()
    total_count = all_servers.count()
    
    print(f"📊 檢測到 {total_count} 個 DHCP Server:")
    print()
    
    servers_without_scopes = []
    
    for server in all_servers:
        scope_count = DHCPScope.objects.filter(server=server).count()
        status_icon = "✅" if scope_count > 0 else "❌"
        
        print(f"{status_icon} {server.name} ({server.ip_address})")
        print(f"   狀態: {server.status}")
        print(f"   SSH 用戶: {server.ssh_username}")
        print(f"   Scope 數量: {scope_count}")
        print(f"   Pool 使用率: {server.pool_usage}%")
        print()
        
        if scope_count == 0:
            servers_without_scopes.append(server)
    
    # 2. 處理缺少 Scope 的伺服器
    if not servers_without_scopes:
        print("🎉 所有伺服器都已有 Scope 數據，無需初始化！")
        return
    
    print(f"⚠️  發現 {len(servers_without_scopes)} 個伺服器缺少 Scope 數據")
    print()
    
    # 3. 詢問是否執行同步
    print("選項：")
    print("  1. 執行自動同步（推薦）- 使用 Celery 任務")
    print("  2. 手動同步（阻塞式）- 立即執行")
    print("  3. 取消")
    print()
    
    choice = input("請選擇 (1/2/3): ").strip()
    
    if choice == "1":
        # 使用 Celery 任務
        print()
        print("🚀 正在排程 Celery 任務...")
        
        result = sync_all_dhcp_scopes_task.delay()
        
        print(f"✅ 任務已排程，Task ID: {result.id}")
        print()
        print("📝 檢查任務狀態：")
        print(f"   docker exec nt-django celery -A network_toolbox inspect active")
        print()
        print("📝 檢查日誌：")
        print(f"   docker compose logs django -f | grep Celery")
        
    elif choice == "2":
        # 手動同步（阻塞式）
        print()
        print("⚙️  開始手動同步...")
        print()
        
        success_count = 0
        failed_count = 0
        
        for server in servers_without_scopes:
            try:
                print(f"正在同步: {server.name} ({server.ip_address})...")
                
                # 判斷伺服器類型
                if server.ssh_username in ['administrator', 'Administrator']:
                    # Windows DHCP
                    from api.ssh_powershell_service import WindowsSSHPowerShellService
                    
                    with WindowsSSHPowerShellService(server) as service:
                        result = service.sync_scopes_to_db()
                    
                    print(f"  ✅ 成功同步 {result.get('total', 0)} 個 Scope")
                else:
                    # Linux DHCP
                    from api.services import LinuxDHCPConfigService
                    
                    with LinuxDHCPConfigService(server) as service:
                        result = service.sync_config_to_db()
                    
                    if result.get('success'):
                        print(f"  ✅ 成功同步 {result.get('scopes_created', 0) + result.get('scopes_updated', 0)} 個 Scope")
                    else:
                        print(f"  ❌ 同步失敗: {result.get('error', 'Unknown error')}")
                
                # 重新載入並顯示結果
                server.refresh_from_db()
                print(f"  📊 Pool 使用率: {server.pool_usage}%")
                print()
                
                success_count += 1
                
            except Exception as e:
                print(f"  ❌ 錯誤: {str(e)}")
                print()
                failed_count += 1
        
        print("=" * 60)
        print(f"同步完成 - 成功: {success_count} | 失敗: {failed_count}")
        print("=" * 60)
        
    else:
        print("❌ 已取消")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  已中斷")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
