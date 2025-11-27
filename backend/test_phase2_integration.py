#!/usr/bin/env python
"""
Phase 2 整合測試腳本

測試 Fatal Error 分析整合到 store_jenkins_build_task 的功能
"""
import os
import sys
import django

# 設置 Django 環境
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.models import JenkinsBuild, JenkinsJob, JenkinsServer
from api.tasks import store_jenkins_build_task
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def test_phase2_integration():
    """測試 Phase 2 整合功能"""
    
    print("=" * 70)
    print("Phase 2 整合測試 - Fatal Error 分析")
    print("=" * 70)
    
    # 1. 查找 FAILURE 狀態的 Build
    print("\n[步驟 1] 查找 FAILURE 狀態的 Build...")
    
    failure_builds = JenkinsBuild.objects.filter(
        result='FAILURE',
        log_file_path__isnull=False
    ).order_by('-created_at')[:5]
    
    if not failure_builds.exists():
        print("⚠️  沒有找到 FAILURE 狀態且有 Console Log 的 Build")
        print("\n嘗試查找任何 FAILURE Build...")
        
        failure_builds = JenkinsBuild.objects.filter(
            result='FAILURE'
        ).order_by('-created_at')[:5]
        
        if not failure_builds.exists():
            print("❌ 沒有找到任何 FAILURE Build")
            return False
    
    print(f"✓ 找到 {failure_builds.count()} 個 FAILURE Build")
    
    # 2. 顯示 Build 列表
    print("\n[步驟 2] 可用的 FAILURE Builds:")
    for i, build in enumerate(failure_builds, 1):
        print(f"  {i}. {build.job.name} #{build.build_number}")
        print(f"     - Server: {build.job.server.name}")
        print(f"     - Result: {build.result}")
        print(f"     - Log Path: {build.log_file_path or 'N/A'}")
        print(f"     - Created: {build.created_at}")
    
    # 3. 選擇第一個有 log_file_path 的 Build
    print("\n[步驟 3] 選擇測試 Build...")
    
    test_build = None
    for build in failure_builds:
        if build.log_file_path:
            test_build = build
            break
    
    if not test_build:
        print("❌ 沒有找到有 Console Log 路徑的 Build")
        print("\n提示: 需要先執行一次 store_jenkins_build_task 來下載 Console Log")
        
        # 嘗試手動觸發第一個 Build
        test_build = failure_builds[0]
        print(f"\n嘗試為 {test_build.job.name} #{test_build.build_number} 下載 Console Log...")
    
    print(f"✓ 選擇測試 Build: {test_build.job.name} #{test_build.build_number}")
    
    # 4. 檢查 Console Log 文件是否存在
    print("\n[步驟 4] 檢查 Console Log 文件...")
    
    if test_build.log_file_path:
        log_path = Path(test_build.log_file_path)
        if log_path.exists():
            log_size = log_path.stat().st_size
            print(f"✓ Console Log 存在: {log_path}")
            print(f"  - 文件大小: {log_size / 1024:.2f} KB")
            
            # 檢查是否已有分析結果
            analysis_path = log_path.parent / 'fatal_analysis.json'
            if analysis_path.exists():
                print(f"ℹ️  已存在分析結果: {analysis_path}")
                print(f"  - 將會被覆蓋")
        else:
            print(f"⚠️  Console Log 文件不存在: {log_path}")
            print("  - 將嘗試重新下載")
    else:
        print("⚠️  Build 沒有 log_file_path，將嘗試下載")
    
    # 5. 執行 store_jenkins_build_task（會觸發 Phase 2 分析）
    print("\n[步驟 5] 執行 store_jenkins_build_task（包含 Fatal Error 分析）...")
    print(f"  - Build ID: {test_build.id}")
    print(f"  - Job: {test_build.job.name}")
    print(f"  - Build Number: {test_build.build_number}")
    print(f"  - Result: {test_build.result}")
    
    print("\n" + "-" * 70)
    print("開始執行...")
    print("-" * 70)
    
    try:
        result = store_jenkins_build_task(test_build.id)
        
        print("-" * 70)
        print("執行完成！")
        print("-" * 70)
        
        # 6. 檢查執行結果
        print("\n[步驟 6] 檢查執行結果...")
        
        if result.get('success'):
            print("✅ Task 執行成功")
            
            # 重新載入 Build 資料
            test_build.refresh_from_db()
            
            # 檢查 Console Log
            if test_build.log_file_path:
                log_path = Path(test_build.log_file_path)
                print(f"\n📄 Console Log:")
                print(f"  - 路徑: {log_path}")
                print(f"  - 存在: {'✓' if log_path.exists() else '✗'}")
                
                # 檢查 Fatal Analysis 結果
                analysis_path = log_path.parent / 'fatal_analysis.json'
                print(f"\n🔍 Fatal Analysis:")
                print(f"  - 路徑: {analysis_path}")
                print(f"  - 存在: {'✓' if analysis_path.exists() else '✗'}")
                
                if analysis_path.exists():
                    import json
                    
                    analysis_size = analysis_path.stat().st_size
                    print(f"  - 文件大小: {analysis_size / 1024:.2f} KB")
                    
                    # 讀取分析結果
                    with open(analysis_path, 'r', encoding='utf-8') as f:
                        analysis_data = json.load(f)
                    
                    print(f"\n📊 分析結果摘要:")
                    print(f"  - 總 fatal 數量: {analysis_data['summary']['total_fatal_count']}")
                    print(f"  - 唯一 Task 數量: {analysis_data['summary']['unique_task_count']}")
                    print(f"  - 有 fatal 錯誤: {analysis_data['summary']['has_fatal_errors']}")
                    
                    if analysis_data['fatal_tasks']:
                        print(f"\n  Fatal Tasks:")
                        for task in analysis_data['fatal_tasks']:
                            print(f"    - {task['task_name']}")
                            print(f"      起始行: {task['start_line']}, 結束行: {task['end_line']}")
                            print(f"      Fatal 數量: {len(task['fatal_occurrences'])}")
                    
                    print(f"\n🎉 Phase 2 整合測試成功！")
                    return True
                else:
                    print(f"\n⚠️  未生成 fatal_analysis.json")
                    print(f"  可能原因:")
                    print(f"    1. Console Log 中沒有 fatal 錯誤")
                    print(f"    2. CPU 負載過高（> 80%）")
                    print(f"    3. 分析過程發生錯誤（查看日誌）")
                    return False
            else:
                print("❌ Console Log 未下載")
                return False
        else:
            print(f"❌ Task 執行失敗: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ 執行失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_prerequisites():
    """檢查前置條件"""
    print("\n[前置條件檢查]")
    
    # 1. 檢查 ConsoleLogAnalyzer 是否存在
    try:
        from library.utils.console_log_analyzer import ConsoleLogAnalyzer
        print("✓ ConsoleLogAnalyzer 模組存在")
    except ImportError as e:
        print(f"✗ ConsoleLogAnalyzer 模組不存在: {e}")
        return False
    
    # 2. 檢查 SystemMonitor 是否存在
    try:
        from library.utils.system_monitor import SystemMonitor
        print("✓ SystemMonitor 模組存在")
    except ImportError as e:
        print(f"✗ SystemMonitor 模組不存在: {e}")
        return False
    
    # 3. 檢查是否有 Jenkins Server
    server_count = JenkinsServer.objects.count()
    print(f"✓ Jenkins Server 數量: {server_count}")
    
    if server_count == 0:
        print("⚠️  沒有 Jenkins Server，無法測試")
        return False
    
    # 4. 檢查是否有 FAILURE Build
    failure_count = JenkinsBuild.objects.filter(result='FAILURE').count()
    print(f"✓ FAILURE Build 數量: {failure_count}")
    
    if failure_count == 0:
        print("⚠️  沒有 FAILURE Build，無法測試")
        return False
    
    return True


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("Phase 2 整合測試 - Fatal Error 分析整合到 Celery Task")
    print("=" * 70)
    
    # 檢查前置條件
    if not check_prerequisites():
        print("\n❌ 前置條件不滿足，無法執行測試")
        sys.exit(1)
    
    # 執行測試
    success = test_phase2_integration()
    
    print("\n" + "=" * 70)
    if success:
        print("✅ Phase 2 整合測試完成！")
    else:
        print("⚠️  Phase 2 整合測試未完全成功，請檢查日誌")
    print("=" * 70)
    
    sys.exit(0 if success else 1)
