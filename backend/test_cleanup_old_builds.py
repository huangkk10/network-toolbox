#!/usr/bin/env python
"""
測試 Priority 2: cleanup_old_jenkins_builds_task
測試分為兩階段：
1. Dry-Run 測試：驗證邏輯、計算空間，不實際刪除
2. 實際刪除測試：小範圍測試（建議使用 days=365 或指定 server_id）
"""
import os
import sys
import django

# 設置 Django 環境
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.tasks import cleanup_old_jenkins_builds_task
from api.models import JenkinsServer, JenkinsBuild
from django.utils import timezone
from datetime import timedelta


def print_section(title):
    """打印分隔線"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_current_statistics():
    """打印當前資料統計"""
    print_section("📊 當前資料統計")
    
    # 所有 Server 統計
    servers = JenkinsServer.objects.filter(is_active=True)
    print(f"\n在線 Jenkins Server 數量: {servers.count()} 個\n")
    
    # 計算不同時間範圍的 Builds 數量
    now = timezone.now()
    cutoff_30 = now - timedelta(days=30)
    cutoff_90 = now - timedelta(days=90)
    cutoff_180 = now - timedelta(days=180)
    cutoff_365 = now - timedelta(days=365)
    
    total_builds = JenkinsBuild.objects.count()
    stored_builds = JenkinsBuild.objects.filter(is_workspace_stored=True).count()
    
    older_than_30 = JenkinsBuild.objects.filter(build_timestamp__lt=cutoff_30).count()
    older_than_90 = JenkinsBuild.objects.filter(build_timestamp__lt=cutoff_90).count()
    older_than_180 = JenkinsBuild.objects.filter(build_timestamp__lt=cutoff_180).count()
    older_than_365 = JenkinsBuild.objects.filter(build_timestamp__lt=cutoff_365).count()
    
    stored_older_than_30 = JenkinsBuild.objects.filter(
        is_workspace_stored=True, build_timestamp__lt=cutoff_30
    ).count()
    stored_older_than_90 = JenkinsBuild.objects.filter(
        is_workspace_stored=True, build_timestamp__lt=cutoff_90
    ).count()
    stored_older_than_180 = JenkinsBuild.objects.filter(
        is_workspace_stored=True, build_timestamp__lt=cutoff_180
    ).count()
    stored_older_than_365 = JenkinsBuild.objects.filter(
        is_workspace_stored=True, build_timestamp__lt=cutoff_365
    ).count()
    
    print(f"總 Builds 數量: {total_builds:,}")
    print(f"已存儲到 NAS 的 Builds: {stored_builds:,}")
    print("\n📅 不同時間範圍的舊 Builds 數量：")
    print(f"  > 30  天: {older_than_30:,} 個 (已存儲: {stored_older_than_30:,})")
    print(f"  > 90  天: {older_than_90:,} 個 (已存儲: {stored_older_than_90:,})")
    print(f"  > 180 天: {older_than_180:,} 個 (已存儲: {stored_older_than_180:,})")
    print(f"  > 365 天: {older_than_365:,} 個 (已存儲: {stored_older_than_365:,})")
    
    # 每個 Server 的統計
    print("\n📍 各 Server 統計：")
    for server in servers:
        server_builds = JenkinsBuild.objects.filter(job__server=server).count()
        server_stored = JenkinsBuild.objects.filter(
            job__server=server, is_workspace_stored=True
        ).count()
        server_old_90 = JenkinsBuild.objects.filter(
            job__server=server, build_timestamp__lt=cutoff_90
        ).count()
        server_old_stored_90 = JenkinsBuild.objects.filter(
            job__server=server, is_workspace_stored=True, build_timestamp__lt=cutoff_90
        ).count()
        
        print(f"\n  Server #{server.id}: {server.name} ({server.url})")
        print(f"    - 總 Builds: {server_builds:,}")
        print(f"    - 已存儲: {server_stored:,}")
        print(f"    - > 90 天: {server_old_90:,} (已存儲: {server_old_stored_90:,})")


def test_dry_run(days=90, only_stored=True, server_id=None):
    """
    測試 1: Dry-Run 模式
    
    Args:
        days: 保留天數（預設 90）
        only_stored: 只處理已存儲的 Builds（預設 True）
        server_id: 指定 Server ID（預設 None 表示所有）
    """
    print_section(f"🧪 測試 1: Dry-Run 模式 (days={days}, only_stored={only_stored}, server_id={server_id})")
    
    print("\n⚙️  執行參數:")
    print(f"  - days: {days}")
    print(f"  - only_stored: {only_stored}")
    print(f"  - exclude_patterns: []")
    print(f"  - dry_run: True (測試模式，不實際刪除)")
    print(f"  - server_id: {server_id or 'None (所有 Server)'}")
    
    print("\n🚀 開始執行...")
    
    # 執行任務
    result = cleanup_old_jenkins_builds_task.apply(
        kwargs={
            'days': days,
            'only_stored': only_stored,
            'exclude_patterns': [],
            'dry_run': True,
            'server_id': server_id,
        }
    )
    
    # 等待結果
    stats = result.get(timeout=300)  # 等待最多 5 分鐘
    
    # 打印結果
    print("\n📊 測試結果:")
    print(f"  - 成功: {stats.get('success', False)}")
    print(f"  - 檢查伺服器: {stats.get('servers_checked', 0)} 個")
    print(f"  - 檢查 Builds: {stats.get('total_checked', 0):,} 個")
    print(f"  - 找到舊 Builds: {stats.get('total_old_builds', 0):,} 個")
    print(f"  - 將刪除 Builds: {stats.get('deleted_builds', 0):,} 個")
    print(f"  - 將刪除 NAS 資料夾: {stats.get('nas_folders_deleted', 0):,} 個")
    
    # 計算空間
    freed_gb = stats.get('nas_space_freed', 0) / 1024 / 1024 / 1024
    print(f"  - 預計釋放 NAS 空間: {freed_gb:.3f} GB")
    
    print(f"  - 跳過 Builds: {stats.get('skipped', 0):,} 個")
    print(f"  - 錯誤: {stats.get('errors', 0):,} 個")
    print(f"  - 執行時間: {stats.get('duration', 0):.2f} 秒")
    
    # 詳細每個 Server 的結果
    if stats.get('servers_details'):
        print("\n📍 各 Server 詳細結果:")
        for server_stat in stats['servers_details']:
            print(f"\n  Server #{server_stat['server_id']}: {server_stat['server_name']}")
            print(f"    - 檢查: {server_stat['checked']:,} 個")
            print(f"    - 舊 Builds: {server_stat['old_builds']:,} 個")
            print(f"    - 將刪除: {server_stat['deleted']:,} 個")
            
            server_freed_gb = server_stat['nas_freed'] / 1024 / 1024 / 1024
            print(f"    - 預計釋放: {server_freed_gb:.3f} GB")
            print(f"    - 跳過: {server_stat['skipped']:,} 個")
            print(f"    - 錯誤: {server_stat['errors']:,} 個")
            print(f"    - 執行時間: {server_stat['duration']:.2f} 秒")
    
    return stats


def test_actual_cleanup(days=365, only_stored=True, server_id=None):
    """
    測試 2: 實際清理模式（小範圍測試）
    
    Args:
        days: 保留天數（建議 365，只清理非常舊的資料）
        only_stored: 只處理已存儲的 Builds（預設 True）
        server_id: 指定 Server ID（建議指定單一 Server 進行測試）
    """
    print_section(f"🧪 測試 2: 實際清理模式 (days={days}, only_stored={only_stored}, server_id={server_id})")
    
    print("\n⚠️  警告: 此模式將實際刪除資料！")
    print(f"⚙️  執行參數:")
    print(f"  - days: {days}")
    print(f"  - only_stored: {only_stored}")
    print(f"  - exclude_patterns: []")
    print(f"  - dry_run: False (實際刪除)")
    print(f"  - server_id: {server_id or 'None (所有 Server)'}")
    
    # 確認
    confirmation = input("\n⚠️  確定要執行實際清理嗎？輸入 'YES' 繼續: ")
    if confirmation != 'YES':
        print("❌ 取消執行")
        return None
    
    print("\n🚀 開始執行...")
    
    # 執行任務
    result = cleanup_old_jenkins_builds_task.apply(
        kwargs={
            'days': days,
            'only_stored': only_stored,
            'exclude_patterns': [],
            'dry_run': False,
            'server_id': server_id,
        }
    )
    
    # 等待結果
    stats = result.get(timeout=600)  # 等待最多 10 分鐘
    
    # 打印結果
    print("\n📊 執行結果:")
    print(f"  - 成功: {stats.get('success', False)}")
    print(f"  - 檢查伺服器: {stats.get('servers_checked', 0)} 個")
    print(f"  - 檢查 Builds: {stats.get('total_checked', 0):,} 個")
    print(f"  - 找到舊 Builds: {stats.get('total_old_builds', 0):,} 個")
    print(f"  - 已刪除 Builds: {stats.get('deleted_builds', 0):,} 個")
    print(f"  - 已刪除 NAS 資料夾: {stats.get('nas_folders_deleted', 0):,} 個")
    
    # 計算空間
    freed_gb = stats.get('nas_space_freed', 0) / 1024 / 1024 / 1024
    print(f"  - 實際釋放 NAS 空間: {freed_gb:.3f} GB")
    
    print(f"  - 跳過 Builds: {stats.get('skipped', 0):,} 個")
    print(f"  - 錯誤: {stats.get('errors', 0):,} 個")
    print(f"  - 執行時間: {stats.get('duration', 0):.2f} 秒")
    
    # 詳細每個 Server 的結果
    if stats.get('servers_details'):
        print("\n📍 各 Server 詳細結果:")
        for server_stat in stats['servers_details']:
            print(f"\n  Server #{server_stat['server_id']}: {server_stat['server_name']}")
            print(f"    - 檢查: {server_stat['checked']:,} 個")
            print(f"    - 舊 Builds: {server_stat['old_builds']:,} 個")
            print(f"    - 已刪除: {server_stat['deleted']:,} 個")
            
            server_freed_gb = server_stat['nas_freed'] / 1024 / 1024 / 1024
            print(f"    - 釋放空間: {server_freed_gb:.3f} GB")
            print(f"    - 跳過: {server_stat['skipped']:,} 個")
            print(f"    - 錯誤: {server_stat['errors']:,} 個")
            print(f"    - 執行時間: {server_stat['duration']:.2f} 秒")
    
    return stats


def main():
    """主測試流程"""
    import sys
    
    # 檢查是否為非互動模式
    is_interactive = sys.stdin.isatty()
    
    print_section("🎯 Priority 2 測試: cleanup_old_jenkins_builds_task")
    
    print("\n測試說明：")
    print("  1. 打印當前資料統計")
    print("  2. 執行 Dry-Run 測試（不實際刪除，只計算）")
    
    # Step 1: 打印當前統計
    print_current_statistics()
    
    # Step 2: Dry-Run 測試
    print("\n" + "=" * 80)
    print("  開始執行 Dry-Run 測試 (days=30)")
    print("=" * 80)
    
    try:
        # 測試 1: days=30 (應該找到 39 個)
        print("\n【測試 1】days=30, only_stored=True")
        dry_run_stats_30 = test_dry_run(days=30, only_stored=True, server_id=None)
        
        # 測試 2: days=90 (應該找到 0 個)
        print("\n【測試 2】days=90, only_stored=True")
        dry_run_stats_90 = test_dry_run(days=90, only_stored=True, server_id=None)
        
        # 測試 3: days=7 (應該找到更多)
        print("\n【測試 3】days=7, only_stored=True")
        dry_run_stats_7 = test_dry_run(days=7, only_stored=True, server_id=None)
        
        print_section("✅ 所有 Dry-Run 測試完成")
        
        # 總結
        print("\n📊 測試總結：")
        print(f"  - days=7:  找到 {dry_run_stats_7.get('total_old_builds', 0):,} 個舊 Builds")
        print(f"  - days=30: 找到 {dry_run_stats_30.get('total_old_builds', 0):,} 個舊 Builds")
        print(f"  - days=90: 找到 {dry_run_stats_90.get('total_old_builds', 0):,} 個舊 Builds")
        
        freed_7 = dry_run_stats_7.get('nas_space_freed', 0) / 1024 / 1024 / 1024
        freed_30 = dry_run_stats_30.get('nas_space_freed', 0) / 1024 / 1024 / 1024
        freed_90 = dry_run_stats_90.get('nas_space_freed', 0) / 1024 / 1024 / 1024
        
        print(f"\n💾 預計釋放空間：")
        print(f"  - days=7:  {freed_7:.3f} GB")
        print(f"  - days=30: {freed_30:.3f} GB")
        print(f"  - days=90: {freed_90:.3f} GB")
        
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print_section("🎉 所有測試完成")
    
    print("\n💡 後續步驟：")
    print("  1. 如果 Dry-Run 測試結果正確，可以進行小範圍實際清理測試")
    print("  2. 建議使用 days=365 或指定 server_id 進行小範圍測試")
    print("  3. 手動執行實際清理測試：")
    print("     docker exec nt-django python /app/test_cleanup_old_builds.py --actual --days=365")
    
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
