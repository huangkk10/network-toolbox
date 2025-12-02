#!/usr/bin/env python3
"""
路徑驗證功能測試腳本

測試 PathValidator 對各種路徑格式的驗證能力
"""

import sys
import os

# 添加 library 到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from library.utils.yaml_validator import PathValidator


def test_path_detection():
    """測試路徑類型偵測"""
    print("=" * 60)
    print("測試路徑類型偵測")
    print("=" * 60)
    
    test_cases = [
        # Windows 本地路徑
        ("C:\\drivers\\install.bat", "windows_local"),
        ("D:\\path\\to\\file.txt", "windows_local"),
        ("c:\\lowercase\\drive", "windows_local"),
        
        # Windows UNC 路徑
        ("\\\\10.250.0.1\\mdt\\Team\\Compatibility", "windows_unc"),
        ("\\\\server\\share\\folder", "windows_unc"),
        
        # Linux 路徑
        ("/opt/scripts/run.sh", "linux"),
        ("/var/log/test.log", "linux"),
        ("/home/user/file", "linux"),
        
        # 混合斜線（錯誤）
        ("C:\\path/to/file", "mixed"),
        ("C:/path\\to\\file", "mixed"),
        
        # 相對路徑
        ("drivers\\install.bat", "windows_relative"),
        ("path/to/file", "linux_relative"),
        
        # 模糊情況
        ("filename.txt", "ambiguous"),
        ("//server/share", "ambiguous"),
        
        # 空路徑
        ("", "empty"),
        ("   ", "empty"),
    ]
    
    passed = 0
    failed = 0
    
    for path, expected_type in test_cases:
        detected = PathValidator.detect_path_type(path)
        status = "✅" if detected == expected_type else "❌"
        if detected == expected_type:
            passed += 1
        else:
            failed += 1
        print(f"{status} '{path}' -> {detected} (預期: {expected_type})")
    
    print(f"\n結果: {passed} 通過, {failed} 失敗")
    return failed == 0


def test_windows_path_validation():
    """測試 Windows 路徑驗證"""
    print("\n" + "=" * 60)
    print("測試 Windows 路徑驗證")
    print("=" * 60)
    
    test_cases = [
        # 正確的路徑
        {
            "path": "C:\\drivers\\install.bat",
            "type": "windows_local",
            "expect_valid": True
        },
        {
            "path": "\\\\10.250.0.1\\mdt\\Team",
            "type": "windows_unc",
            "expect_valid": True
        },
        
        # 使用正斜線（錯誤）
        {
            "path": "C:/drivers/install.bat",
            "type": "windows_local",
            "expect_valid": False,
            "expect_suggestion": "C:\\drivers\\install.bat"
        },
        
        # 小寫磁碟代號（警告）
        {
            "path": "c:\\drivers\\install.bat",
            "type": "windows_local",
            "expect_valid": True,
            "expect_warning": True
        },
        
        # 磁碟代號後缺少反斜線
        {
            "path": "C:drivers\\install.bat",
            "type": "windows_local",
            "expect_valid": False
        },
        
        # UNC 路徑格式不完整
        {
            "path": "\\\\server",
            "type": "windows_unc",
            "expect_valid": False
        },
        
        # 包含無效字符
        {
            "path": "C:\\path\\file<name>.txt",
            "type": "windows_local",
            "expect_valid": False
        },
    ]
    
    for tc in test_cases:
        result = PathValidator.validate_windows_path(tc["path"], tc["type"])
        
        valid_match = result["is_valid"] == tc["expect_valid"]
        status = "✅" if valid_match else "❌"
        
        print(f"\n{status} 路徑: {tc['path']}")
        print(f"   類型: {tc['type']}")
        print(f"   有效: {result['is_valid']} (預期: {tc['expect_valid']})")
        
        if result["errors"]:
            print(f"   錯誤: {result['errors']}")
        if result["warnings"]:
            print(f"   警告: {result['warnings']}")
        if result["suggestion"]:
            print(f"   建議: {result['suggestion']}")


def test_linux_path_validation():
    """測試 Linux 路徑驗證"""
    print("\n" + "=" * 60)
    print("測試 Linux 路徑驗證")
    print("=" * 60)
    
    test_cases = [
        # 正確的路徑
        {
            "path": "/opt/scripts/run.sh",
            "expect_valid": True
        },
        {
            "path": "/var/log/test.log",
            "expect_valid": True
        },
        
        # 使用反斜線（錯誤）
        {
            "path": "/opt\\scripts\\run.sh",
            "expect_valid": False,
            "expect_suggestion": "/opt/scripts/run.sh"
        },
        
        # 連續斜線（警告）
        {
            "path": "/opt//scripts/run.sh",
            "expect_valid": True,
            "expect_warning": True
        },
    ]
    
    for tc in test_cases:
        result = PathValidator.validate_linux_path(tc["path"])
        
        valid_match = result["is_valid"] == tc["expect_valid"]
        status = "✅" if valid_match else "❌"
        
        print(f"\n{status} 路徑: {tc['path']}")
        print(f"   有效: {result['is_valid']} (預期: {tc['expect_valid']})")
        
        if result["errors"]:
            print(f"   錯誤: {result['errors']}")
        if result["warnings"]:
            print(f"   警告: {result['warnings']}")
        if result["suggestion"]:
            print(f"   建議: {result['suggestion']}")


def test_testcase_paths_validation():
    """測試 testcases.yml 路徑驗證"""
    print("\n" + "=" * 60)
    print("測試 testcases.yml 路徑驗證")
    print("=" * 60)
    
    # 模擬 testcases.yml 內容
    test_content = """Compatibility:
  - id: STC-551
    timeout: 604800
    script_nas_file: \\\\10.250.0.1\\mdt\\Team\\Compatibility\\RVT_2_0\\Samsung_PM9M1\\scripts\\PM9M1.7z
    script_local_root: C:\\
    script_exec: C:/drivers/install.bat
    log_type: runcard.ini
    log_path: C:\\SSD_Compatibility\\Autoit_Log\\RunCard.ini
    archive_root: C:\\SSD_Compatibility\\
    archive_patterns: 'Autoit_Log\\*'
    archive_upload_dir: \\\\10.250.0.1\\mdt\\Team\\Compatibility\\RVT_2_0\\Samsung_PM9M1\\TestResults_Log

Linux_Test:
  - id: LNX-001
    script_path: /opt/test/run.sh
    log_path: /var\\log/test.log
    output_path: /home/user/output/
"""
    
    result = PathValidator.validate_testcase_paths(test_content)
    
    print(f"\n總共檢查: {result['total_paths_checked']} 個路徑")
    print(f"驗證結果: {'✅ 全部通過' if result['is_valid'] else '❌ 有錯誤'}")
    
    print(f"\n路徑類型統計:")
    for path_type, count in result['summary'].items():
        if count > 0:
            print(f"  - {path_type}: {count}")
    
    if result['path_errors']:
        print(f"\n❌ 錯誤 ({len(result['path_errors'])} 個):")
        for err in result['path_errors']:
            print(f"  第 {err['line']} 行 [{err['field']}]: {err['value']}")
            print(f"    類型: {err['path_type']}")
            for e in err['errors']:
                print(f"    錯誤: {e}")
            if err['suggestion']:
                print(f"    建議: {err['suggestion']}")
    
    if result['path_warnings']:
        print(f"\n⚠️ 警告 ({len(result['path_warnings'])} 個):")
        for warn in result['path_warnings']:
            print(f"  第 {warn['line']} 行 [{warn['field']}]: {warn['value']}")
            for w in warn['warnings']:
                print(f"    警告: {w}")


def main():
    print("🔍 路徑驗證功能測試")
    print("=" * 60)
    
    # 執行測試
    test_path_detection()
    test_windows_path_validation()
    test_linux_path_validation()
    test_testcase_paths_validation()
    
    print("\n" + "=" * 60)
    print("測試完成！")


if __name__ == "__main__":
    main()
