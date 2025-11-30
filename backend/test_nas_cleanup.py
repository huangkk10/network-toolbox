#!/usr/bin/env python
"""
測試 NAS Jenkins Storage 清理任務

用法：
    docker exec nt-django python test_nas_cleanup.py
    docker exec nt-django python test_nas_cleanup.py --dry-run
    docker exec nt-django python test_nas_cleanup.py --execute
"""
import os
import sys
import argparse

# 設置 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()

from api.tasks import cleanup_old_nas_jenkins_storage_task


def print_section(title):
    """打印區段標題"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_result(result):
    """格式化打印結果"""
    print("\n📊 執行結果統計:")
    print(f"   - 成功: {'✅ 是' if result.get('success') else '❌ 否'}")
    print(f"   - 目標路徑: {result.get('base_path', 'N/A')}")
    print(f"   - 清理天數: {result.get('max_age_days', 'N/A')} 天")
    print(f"   - 模式: {'Dry-Run（只掃描）' if result.get('dry_run') else '正式執行'}")
    print()
    print(f"   📁 掃描統計:")
    print(f"      - Servers: {result.get('servers_scanned', 0)}")
    print(f"      - Jobs: {result.get('jobs_scanned', 0)}")
    print(f"      - Builds: {result.get('builds_scanned', 0)}")
    print()
    print(f"   🗑️  清理統計:")
    print(f"      - 待清理 Builds: {result.get('builds_to_delete', 0)}")
    print(f"      - 已刪除 Builds: {result.get('builds_deleted', 0)}")
    
    space_freed = result.get('space_freed_bytes', 0)
    if space_freed >= 1024 * 1024 * 1024:
        space_str = f"{space_freed / 1024 / 1024 / 1024:.2f} GB"
    elif space_freed >= 1024 * 1024:
        space_str = f"{space_freed / 1024 / 1024:.2f} MB"
    else:
        space_str = f"{space_freed} Bytes"
    print(f"      - 釋放空間: {space_str}")
    
    if result.get('empty_jobs_deleted', 0) > 0:
        print(f"      - 清理空 Job 資料夾: {result.get('empty_jobs_deleted')}")
    
    print()
    print(f"   🖥️  CPU 監控:")
    print(f"      - CPU 暫停次數: {result.get('cpu_pauses', 0)}")
    print(f"      - CPU 超時跳過: {result.get('cpu_timeout_skips', 0)}")
    
    if result.get('errors', 0) > 0:
        print()
        print(f"   ⚠️  錯誤: {result.get('errors')}")
    
    print()
    print(f"   ⏱️  耗時: {result.get('duration', 0):.2f} 秒")
    
    if result.get('error_message'):
        print()
        print(f"   ❌ 錯誤訊息: {result.get('error_message')}")


def test_dry_run(max_age_days=30):
    """測試 Dry-Run 模式（只掃描不刪除）"""
    print_section("🧪 測試模式：Dry-Run（只掃描不刪除）")
    
    print(f"\n🔧 執行參數:")
    print(f"   - max_age_days: {max_age_days}")
    print(f"   - dry_run: True")
    print(f"   - cpu_high_threshold: 80.0%")
    print(f"   - cpu_low_threshold: 60.0%")
    
    print("\n⏳ 正在執行掃描...")
    
    result = cleanup_old_nas_jenkins_storage_task.apply(kwargs={
        'max_age_days': max_age_days,
        'dry_run': True,
        'cpu_high_threshold': 80.0,
        'cpu_low_threshold': 60.0
    }).get()
    
    print_result(result)
    
    return result


def test_execute(max_age_days=30):
    """測試正式執行（實際刪除）"""
    print_section("🚀 正式執行模式（實際刪除）")
    
    print(f"\n🔧 執行參數:")
    print(f"   - max_age_days: {max_age_days}")
    print(f"   - dry_run: False")
    print(f"   - cpu_high_threshold: 80.0%")
    print(f"   - cpu_low_threshold: 60.0%")
    
    # 安全確認
    print("\n⚠️  警告：此操作將實際刪除超過 {0} 天的 Build 資料夾！".format(max_age_days))
    confirm = input("確定要執行嗎？(輸入 'yes' 確認): ")
    
    if confirm.lower() != 'yes':
        print("❌ 已取消執行")
        return None
    
    print("\n⏳ 正在執行清理...")
    
    result = cleanup_old_nas_jenkins_storage_task.apply(kwargs={
        'max_age_days': max_age_days,
        'dry_run': False,
        'cpu_high_threshold': 80.0,
        'cpu_low_threshold': 60.0,
        'batch_size': 10,
        'batch_delay': 2.0
    }).get()
    
    print_result(result)
    
    return result


def test_cpu_monitoring():
    """測試 CPU 監控功能"""
    print_section("🖥️  測試 CPU 監控功能")
    
    import psutil
    
    print("\n📊 當前系統狀態:")
    
    # 取得 CPU 資訊
    cpu_usage = psutil.cpu_percent(interval=2)
    cpu_count = psutil.cpu_count()
    
    print(f"   - CPU 使用率: {cpu_usage:.1f}%")
    print(f"   - CPU 核心數: {cpu_count}")
    
    # 取得記憶體資訊
    memory = psutil.virtual_memory()
    print(f"   - 記憶體使用率: {memory.percent:.1f}%")
    print(f"   - 可用記憶體: {memory.available / 1024 / 1024 / 1024:.2f} GB")
    
    # 判斷是否適合執行清理
    print()
    if cpu_usage > 80:
        print("⚠️  CPU 使用率較高 (> 80%)，清理任務可能會暫停等待")
    elif cpu_usage > 60:
        print("⚡ CPU 使用率中等 (60-80%)，清理任務會正常執行")
    else:
        print("✅ CPU 使用率正常 (< 60%)，清理任務可正常執行")


def check_nas_path():
    """檢查 NAS 路徑是否可存取"""
    print_section("📂 檢查 NAS 路徑")
    
    from django.conf import settings
    
    base_path = getattr(
        settings, 
        'JENKINS_STORAGE_BASE_PATH', 
        '/mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage'
    )
    
    print(f"\n目標路徑: {base_path}")
    
    if os.path.exists(base_path):
        print("✅ 路徑存在")
        
        # 列出子目錄
        try:
            subdirs = [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]
            print(f"\n📁 找到 {len(subdirs)} 個 Jenkins Server 資料夾:")
            for d in subdirs[:10]:
                print(f"   - {d}")
            if len(subdirs) > 10:
                print(f"   ... 還有 {len(subdirs) - 10} 個")
        except PermissionError:
            print("❌ 無法存取目錄（權限錯誤）")
    else:
        print("❌ 路徑不存在")
        print("\n💡 提示：請確認 NAS 已正確掛載")


def main():
    parser = argparse.ArgumentParser(description='測試 NAS Jenkins Storage 清理任務')
    parser.add_argument('--dry-run', action='store_true', help='執行 Dry-Run 測試（預設）')
    parser.add_argument('--execute', action='store_true', help='執行正式清理（會實際刪除）')
    parser.add_argument('--days', type=int, default=30, help='清理超過指定天數的資料夾（預設 30）')
    parser.add_argument('--cpu', action='store_true', help='只測試 CPU 監控功能')
    parser.add_argument('--check-path', action='store_true', help='只檢查 NAS 路徑')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("  🧹 NAS Jenkins Storage 清理任務測試")
    print("=" * 70)
    
    # 檢查 NAS 路徑
    check_nas_path()
    
    if args.check_path:
        return
    
    # 測試 CPU 監控
    test_cpu_monitoring()
    
    if args.cpu:
        return
    
    # 執行清理測試
    if args.execute:
        test_execute(max_age_days=args.days)
    else:
        test_dry_run(max_age_days=args.days)
    
    print("\n" + "=" * 70)
    print("  ✅ 測試完成")
    print("=" * 70)


if __name__ == '__main__':
    main()
