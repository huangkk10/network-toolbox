#!/usr/bin/env python
"""
清除測試數據並添加真實 Jenkins/RVT 伺服器

使用方式：
    docker exec nt-django python setup_real_jenkins_server.py
"""

import os
import sys
import django

# 設置 Django 環境
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.models import JenkinsServer, JenkinsJob, JenkinsBuild

def clear_test_data():
    """清除所有測試數據"""
    print("=" * 60)
    print("🗑️  清除測試數據...")
    print("=" * 60)
    
    builds_count = JenkinsBuild.objects.count()
    jobs_count = JenkinsJob.objects.count()
    servers_count = JenkinsServer.objects.count()
    
    print(f"\n📊 當前數據：")
    print(f"  - Jenkins Servers: {servers_count}")
    print(f"  - Jenkins Jobs: {jobs_count}")
    print(f"  - Jenkins Builds: {builds_count}")
    
    if servers_count == 0:
        print("\n✅ 資料庫已經是空的，無需清除")
        return
    
    # 確認刪除
    print("\n⚠️  警告：這將刪除所有 Jenkins 相關數據！")
    print("按 Ctrl+C 取消，或按 Enter 繼續...")
    
    try:
        input()
    except KeyboardInterrupt:
        print("\n\n❌ 已取消")
        sys.exit(0)
    
    # 執行刪除
    JenkinsBuild.objects.all().delete()
    JenkinsJob.objects.all().delete()
    JenkinsServer.objects.all().delete()
    
    print("\n✅ 測試數據已清除")

def add_real_server():
    """添加真實的 Jenkins 伺服器（互動式）"""
    print("\n" + "=" * 60)
    print("➕ 添加真實的 Jenkins/RVT 伺服器")
    print("=" * 60)
    
    print("\n請輸入 Jenkins 伺服器資訊：")
    print("（直接按 Enter 跳過）\n")
    
    try:
        name = input("伺服器名稱 (例如: RVT Production): ").strip()
        if not name:
            print("\n⏭️  跳過添加伺服器")
            return
        
        url = input("伺服器 URL (例如: http://jenkins.example.com:8080): ").strip()
        if not url:
            print("❌ URL 不能為空")
            return
        
        username = input("Jenkins 用戶名: ").strip()
        api_token = input("Jenkins API Token: ").strip()
        
        description = input("描述 (可選): ").strip()
        
        # 創建伺服器
        server = JenkinsServer.objects.create(
            name=name,
            url=url,
            username=username or None,
            api_token=api_token or None,
            description=description or f'{name} Jenkins 伺服器',
            status='online',
            is_active=True,
        )
        
        print(f"\n✅ 成功創建伺服器: {server.name}")
        print(f"   URL: {server.url}")
        print(f"   ID: {server.id}")
        
        print("\n📝 下一步：")
        print("   1. 訪問 http://localhost/rvt-analytics")
        print("   2. 點擊「同步所有伺服器」按鈕")
        print("   3. 系統會自動從 Jenkins 獲取 Jobs 和 Builds")
        
    except KeyboardInterrupt:
        print("\n\n❌ 已取消")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 錯誤: {str(e)}")
        import traceback
        traceback.print_exc()

def show_menu():
    """顯示選單"""
    print("\n" + "=" * 60)
    print("Jenkins/RVT 伺服器管理")
    print("=" * 60)
    print("\n請選擇操作：")
    print("  1. 清除測試數據")
    print("  2. 清除測試數據並添加真實伺服器")
    print("  3. 只添加真實伺服器（保留現有數據）")
    print("  4. 退出")
    
    try:
        choice = input("\n請輸入選項 (1-4): ").strip()
        return choice
    except KeyboardInterrupt:
        print("\n\n❌ 已取消")
        sys.exit(0)

if __name__ == '__main__':
    try:
        choice = show_menu()
        
        if choice == '1':
            clear_test_data()
        elif choice == '2':
            clear_test_data()
            add_real_server()
        elif choice == '3':
            add_real_server()
        elif choice == '4':
            print("\n👋 再見！")
            sys.exit(0)
        else:
            print("\n❌ 無效的選項")
            sys.exit(1)
        
        print("\n" + "=" * 60)
        print("✅ 完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
