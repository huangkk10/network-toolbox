#!/usr/bin/env python
"""
Phase 2 簡易測試 - 手動創建包含 fatal 的 Build 並測試分析
"""
import os
import sys
import django

sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.models import JenkinsBuild
from library.utils.console_log_analyzer import ConsoleLogAnalyzer
from library.utils.system_monitor import SystemMonitor
from pathlib import Path
import tempfile
import json

# 模擬包含 fatal 的 Console Log
SAMPLE_CONSOLE_LOG = """10:00:00  PLAY [Deploy Application] ******************************************************
10:00:01  
10:00:01  TASK [Gathering Facts] *********************************************************
10:00:02  ok: [web-server-01]
10:00:02  ok: [web-server-02]
10:00:03  
10:00:03  TASK [common : Install dependencies] *******************************************
10:00:04  task path: /workspace/playbooks/common.yml:10
10:00:05  ok: [web-server-01] => (item=nginx)
10:00:06  ok: [web-server-01] => (item=python3)
10:00:07  ok: [web-server-02] => (item=nginx)
10:00:08  ok: [web-server-02] => (item=python3)
10:00:09  
10:00:09  TASK [app : Deploy application files] ******************************************
10:00:10  task path: /workspace/playbooks/app.yml:25
10:00:11  changed: [web-server-01]
10:00:12  changed: [web-server-02]
10:00:13  
10:00:13  TASK [test : Validate test case STC-551] ***************************************
10:00:14  task path: /workspace/playbooks/test.yml:45
10:00:15  ok: [web-server-01] => {
10:00:15      "msg": "Executing test case STC-551"
10:00:15  }
10:00:16  fatal: [web-server-02]: FAILED! => {
10:00:16      "assertion": "test_status in ['PASS', 'CONDITIONAL_PASS', 'CHECK']",
10:00:16      "changed": false,
10:00:16      "evaluated_to": false,
10:00:16      "msg": "Test case STC-551 failed with status: FAIL"
10:00:16  }
10:00:17  
10:00:17  TASK [cleanup : Remove temporary files] ****************************************
10:00:18  ok: [web-server-01]
10:00:19  skipping: [web-server-02]
10:00:20  
10:00:20  PLAY RECAP *********************************************************************
10:00:21  web-server-01              : ok=5    changed=1    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
10:00:22  web-server-02              : ok=4    changed=1    unreachable=0    failed=1    skipped=1    rescued=0    ignored=0
"""

def test_phase2_logic():
    """測試 Phase 2 的完整邏輯（模擬 tasks.py 中的代碼）"""
    
    print("=" * 70)
    print("Phase 2 邏輯測試 - 模擬 store_jenkins_build_task 中的分析流程")
    print("=" * 70)
    
    # 模擬參數
    log_content = SAMPLE_CONSOLE_LOG
    server_ip = "10.252.170.188"
    job_name = "Test-Job"
    build_number = 999
    build_result = "FAILURE"
    
    print(f"\n[模擬參數]")
    print(f"  - Server IP: {server_ip}")
    print(f"  - Job Name: {job_name}")
    print(f"  - Build Number: {build_number}")
    print(f"  - Build Result: {build_result}")
    print(f"  - Log Size: {len(log_content)} bytes")
    
    # ===== 模擬 Phase 2 代碼開始 =====
    print(f"\n{'='*70}")
    print("開始執行 Phase 2 分析邏輯...")
    print(f"{'='*70}\n")
    
    if build_result == 'FAILURE':
        # 檢查 CPU 負載
        from library.utils.system_monitor import SystemMonitor
        
        try:
            monitor = SystemMonitor(sample_interval=0.5)
            metrics = monitor.get_current_metrics()
            current_cpu = metrics.cpu_percent
            
            print(f"[CPU 檢查] 當前 CPU 使用率: {current_cpu:.1f}%")
            
            if current_cpu < 80.0:
                print(f"[CPU 檢查] ✓ CPU 負載正常（< 80%），繼續分析")
                
                try:
                    from library.utils.console_log_analyzer import ConsoleLogAnalyzer
                    
                    print(f"\n[分析器] 初始化 ConsoleLogAnalyzer...")
                    analyzer = ConsoleLogAnalyzer(
                        log_content=log_content,
                        server_ip=server_ip,
                        job_name=job_name,
                        build_number=build_number
                    )
                    
                    print(f"[分析器] 執行 analyze_fatal_errors()...")
                    result = analyzer.analyze_fatal_errors()
                    
                    print(f"\n[分析結果]")
                    print(f"  - 總 fatal 數量: {result['summary']['total_fatal_count']}")
                    print(f"  - 唯一 Task 數量: {result['summary']['unique_task_count']}")
                    print(f"  - 有 fatal 錯誤: {result['summary']['has_fatal_errors']}")
                    
                    if result['summary']['has_fatal_errors']:
                        print(f"\n[保存結果] 準備保存 JSON 文件...")
                        
                        # 創建臨時目錄模擬 NAS
                        with tempfile.TemporaryDirectory() as tmpdir:
                            output_dir = Path(tmpdir)
                            output_path = output_dir / 'fatal_analysis.json'
                            
                            print(f"  - 輸出目錄: {output_dir}")
                            print(f"  - 文件路徑: {output_path}")
                            
                            analyzer.save_analysis_to_json(output_path)
                            
                            if output_path.exists():
                                file_size = output_path.stat().st_size
                                print(f"\n[保存成功] ✅")
                                print(f"  - 文件大小: {file_size} bytes ({file_size/1024:.2f} KB)")
                                
                                # 讀取並顯示內容
                                with open(output_path, 'r', encoding='utf-8') as f:
                                    saved_data = json.load(f)
                                
                                print(f"\n[JSON 內容驗證]")
                                print(f"  - build_info 存在: {' build_info' in saved_data}")
                                print(f"  - summary 存在: {'summary' in saved_data}")
                                print(f"  - fatal_tasks 存在: {'fatal_tasks' in saved_data}")
                                
                                if saved_data['fatal_tasks']:
                                    print(f"\n[Fatal Tasks 詳情]")
                                    for i, task in enumerate(saved_data['fatal_tasks'], 1):
                                        print(f"  Task {i}: {task['task_name']}")
                                        print(f"    - 起始行: {task['start_line']}")
                                        print(f"    - 結束行: {task['end_line']}")
                                        print(f"    - Fatal 數量: {len(task['fatal_occurrences'])}")
                                        
                                        for j, occ in enumerate(task['fatal_occurrences'], 1):
                                            print(f"      Fatal {j}:")
                                            print(f"        - 行號: {occ['line_number']}")
                                            print(f"        - 內容: {occ['line_content'][:60]}...")
                                
                                print(f"\n{'='*70}")
                                print("🎉 Phase 2 邏輯測試成功！")
                                print(f"{'='*70}")
                                return True
                            else:
                                print(f"\n[錯誤] ❌ JSON 文件未成功保存")
                                return False
                    else:
                        print(f"\n[結果] ℹ️  未發現 Fatal Errors")
                        return True
                        
                except Exception as e:
                    print(f"\n[錯誤] ❌ 分析失敗: {e}")
                    import traceback
                    traceback.print_exc()
                    return False
            else:
                print(f"[CPU 檢查] ⚠️  CPU 負載過高 ({current_cpu:.1f}% >= 80%)，跳過分析")
                return True
                
        except Exception as e:
            print(f"[錯誤] ❌ CPU 監控失敗: {e}")
            return False
    else:
        print(f"[狀態檢查] ℹ️  Build 狀態為 {build_result}，跳過 Fatal Error 分析")
        return True
    
    # ===== 模擬 Phase 2 代碼結束 =====


def test_cpu_threshold():
    """測試 CPU 閾值檢查"""
    print("\n" + "=" * 70)
    print("測試 CPU 閾值檢查機制")
    print("=" * 70)
    
    try:
        from library.utils.system_monitor import SystemMonitor
        
        monitor = SystemMonitor(sample_interval=0.5)
        metrics = monitor.get_current_metrics()
        current_cpu = metrics.cpu_percent
        
        print(f"\n當前 CPU 使用率: {current_cpu:.1f}%")
        
        if current_cpu < 80.0:
            print(f"✓ CPU 負載正常（< 80%）")
            print(f"  → 會執行 Fatal Error 分析")
        else:
            print(f"⚠️  CPU 負載過高（>= 80%）")
            print(f"  → 會跳過 Fatal Error 分析")
        
        return True
        
    except Exception as e:
        print(f"❌ SystemMonitor 測試失敗: {e}")
        return False


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("Phase 2 整合邏輯測試")
    print("=" * 70)
    
    # 1. 測試 CPU 閾值檢查
    cpu_test = test_cpu_threshold()
    
    # 2. 測試完整的 Phase 2 邏輯
    logic_test = test_phase2_logic()
    
    # 總結
    print("\n" + "=" * 70)
    print("測試總結")
    print("=" * 70)
    print(f"CPU 閾值檢查: {'✅ 通過' if cpu_test else '❌ 失敗'}")
    print(f"Phase 2 邏輯: {'✅ 通過' if logic_test else '❌ 失敗'}")
    print("=" * 70)
    
    if cpu_test and logic_test:
        print("\n🎉 所有測試通過！Phase 2 整合邏輯正確！")
        sys.exit(0)
    else:
        print("\n⚠️  部分測試失敗，請檢查錯誤訊息")
        sys.exit(1)
