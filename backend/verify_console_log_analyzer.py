#!/usr/bin/env python
"""
ConsoleLogAnalyzer 簡易驗證腳本
直接在 Django 容器內運行
"""
import sys
sys.path.insert(0, '/app')

from library.utils.console_log_analyzer import ConsoleLogAnalyzer
from pathlib import Path
import json

def test_basic_functionality():
    """基本功能測試"""
    print("=" * 70)
    print("ConsoleLogAnalyzer 基本功能驗證")
    print("=" * 70)
    
    # 測試 1: 使用內容初始化
    print("\n[測試 1] 使用內容初始化")
    content = """10:00:00  PLAY [Test] ************************************************************
10:00:01  
10:00:01  TASK [Gathering Facts] *********************************************************
10:00:02  ok: [server-01]
10:00:03  
10:00:03  TASK [test : Run validation] ***************************************************
10:00:04  ok: [server-01]
10:00:05  fatal: [server-02]: FAILED! => {
10:00:05      "msg": "Validation failed"
10:00:05  }
10:00:06  
10:00:06  PLAY RECAP *********************************************************************
10:00:07  server-01              : ok=2    changed=0    unreachable=0    failed=0
10:00:08  server-02              : ok=1    changed=0    unreachable=0    failed=1
"""
    
    try:
        analyzer = ConsoleLogAnalyzer(log_content=content)
        print("✓ 初始化成功")
        print(f"  - 總行數: {len(analyzer.lines)}")
    except Exception as e:
        print(f"✗ 初始化失敗: {e}")
        return False
    
    # 測試 2: 查找 fatal 行
    print("\n[測試 2] 查找 fatal 行")
    try:
        fatal_lines = analyzer.find_fatal_lines()
        print(f"✓ 找到 {len(fatal_lines)} 個 fatal")
        if fatal_lines:
            for line_num in fatal_lines:
                print(f"  - Line {line_num}: {analyzer.lines[line_num].strip()}")
    except Exception as e:
        print(f"✗ 查找失敗: {e}")
        return False
    
    # 測試 3: 解析 Task 標題
    print("\n[測試 3] 解析 Task 標題")
    test_line = "10:00:03  TASK [test : Run validation] ***************************************************"
    try:
        task_name, timestamp = analyzer.parse_task_header(test_line)
        if task_name and timestamp:
            print(f"✓ 解析成功")
            print(f"  - Task 名稱: {task_name}")
            print(f"  - 時間戳: {timestamp}")
        else:
            print(f"✗ 解析失敗: 返回 None")
    except Exception as e:
        print(f"✗ 解析錯誤: {e}")
        return False
    
    # 測試 4: 完整分析流程
    print("\n[測試 4] 完整分析流程")
    try:
        result = analyzer.analyze_fatal_errors()
        print(f"✓ 分析完成")
        print(f"  - 總 fatal 數量: {result['summary']['total_fatal_count']}")
        print(f"  - 唯一 Task 數量: {result['summary']['unique_task_count']}")
        print(f"  - 分析時長: {result['build_info']['analysis_duration_ms']} ms")
        
        if result['fatal_tasks']:
            print(f"\n  Fatal Tasks:")
            for task in result['fatal_tasks']:
                print(f"    - {task['task_name']}")
                print(f"      起始行: {task['start_line']}, 結束行: {task['end_line']}")
                print(f"      Fatal 數量: {len(task['fatal_occurrences'])}")
    except Exception as e:
        print(f"✗ 分析失敗: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 測試 5: 保存 JSON
    print("\n[測試 5] 保存 JSON 文件")
    output_path = Path("/tmp/test_analysis_result.json")
    try:
        saved_path = analyzer.save_analysis_to_json(output_path)
        print(f"✓ JSON 保存成功: {saved_path}")
        
        # 驗證文件內容
        with open(saved_path, 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)
        print(f"  - 文件大小: {saved_path.stat().st_size} bytes")
        print(f"  - JSON 結構完整: {all(k in loaded_data for k in ['build_info', 'summary', 'fatal_tasks'])}")
    except Exception as e:
        print(f"✗ 保存失敗: {e}")
        return False
    
    return True


def test_with_fixtures():
    """使用測試數據文件驗證"""
    print("\n" + "=" * 70)
    print("使用測試數據文件驗證")
    print("=" * 70)
    
    fixtures_dir = Path("/tmp/fixtures")
    if not fixtures_dir.exists():
        print("✗ 測試數據目錄不存在")
        return False
    
    test_files = [
        ("sample_with_fatal.log", 1, "單個 fatal"),
        ("sample_no_fatal.log", 0, "無 fatal"),
        ("sample_multiple_fatals.log", 3, "多個 fatal"),
        ("sample_fatal_at_start.log", 1, "fatal 在開頭"),
        ("sample_fatal_at_end.log", 1, "fatal 在結尾"),
    ]
    
    for filename, expected_count, description in test_files:
        file_path = fixtures_dir / filename
        if not file_path.exists():
            print(f"\n[跳過] {filename} - 文件不存在")
            continue
        
        print(f"\n[測試] {filename} ({description})")
        try:
            analyzer = ConsoleLogAnalyzer(log_file_path=str(file_path))
            result = analyzer.analyze_fatal_errors()
            actual_count = result['summary']['total_fatal_count']
            
            if actual_count == expected_count:
                print(f"✓ 通過 - 預期 {expected_count} 個 fatal，實際找到 {actual_count} 個")
            else:
                print(f"✗ 失敗 - 預期 {expected_count} 個 fatal，實際找到 {actual_count} 個")
                return False
                
        except Exception as e:
            print(f"✗ 錯誤: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return True


def main():
    """主函數"""
    print("\n" + "=" * 70)
    print("ConsoleLogAnalyzer 驗證測試")
    print("=" * 70)
    
    success = True
    
    # 基本功能測試
    if not test_basic_functionality():
        success = False
        print("\n❌ 基本功能測試失敗")
    else:
        print("\n✅ 基本功能測試通過")
    
    # 測試數據文件測試
    if not test_with_fixtures():
        success = False
        print("\n❌ 測試數據文件驗證失敗")
    else:
        print("\n✅ 測試數據文件驗證通過")
    
    # 總結
    print("\n" + "=" * 70)
    if success:
        print("🎉 所有測試通過！ConsoleLogAnalyzer 功能正常")
    else:
        print("⚠️  部分測試失敗，請檢查錯誤訊息")
    print("=" * 70)
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
