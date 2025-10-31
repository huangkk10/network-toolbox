"""
POC 遷移測試：ipxe_service.py 的 parse_ipxe_log() 方法

測試目標：
1. 驗證新舊實現輸出一致性
2. 驗證遷移後功能正常
3. 記錄遷移過程中的發現
"""
import os
import sys
import django

# Django 環境設置
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.ipxe_service import IPXEService
from library.utils import IPXELogParser


def test_ipxe_log_parsing_comparison():
    """
    對比測試：舊實現 vs 新實現
    """
    print("=" * 80)
    print("POC 遷移測試：parse_ipxe_log() 新舊實現對比")
    print("=" * 80)
    
    # 測試數據：iPXE Boot 日誌
    test_logs = [
        # 正常的 iPXE Boot 請求
        '10.250.53.25 - - [28/Oct/2025:10:18:57 +0000] "GET /boot.ipxe HTTP/1.1" 200 116 "-" "iPXE/1.21.1+ (g83449)" "-"',
        
        # 不同的檔案請求
        '10.250.53.30 - - [28/Oct/2025:11:25:33 +0000] "GET /wimboot HTTP/1.1" 200 4096 "-" "iPXE/1.21.1+ (g83449)" "-"',
        
        # 不同 IP 和時間
        '192.168.1.100 - - [29/Oct/2025:14:55:12 +0000] "GET /boot.ipxe HTTP/1.1" 200 116 "-" "iPXE/1.21.1+ (g83449)" "-"',
        
        # 錯誤請求 (404)
        '10.250.53.25 - - [28/Oct/2025:10:18:58 +0000] "GET /nonexistent.ipxe HTTP/1.1" 404 162 "-" "iPXE/1.21.1+ (g83449)" "-"',
    ]
    
    # 創建模擬的 IPXEServer 實例（用於測試舊方法）
    # 注意：這裡我們只需要 parse_ipxe_log() 方法，不需要實際的 SSH 連接
    class MockIPXEServer:
        def __init__(self):
            self.id = 1
            self.name = 'Test Server'
            self.ip_address = '10.250.53.25'
    
    service = IPXEService(server=MockIPXEServer())
    
    print(f"\n測試 {len(test_logs)} 個日誌範例...\n")
    
    all_passed = True
    
    for i, log_line in enumerate(test_logs, 1):
        print(f"\n[測試 {i}] 日誌: {log_line[:80]}...")
        print("-" * 80)
        
        # 舊實現
        try:
            old_result = service.parse_ipxe_log(log_line)
            print(f"✅ 舊實現解析成功")
            print(f"   結果: {old_result}")
        except Exception as e:
            print(f"❌ 舊實現解析失敗: {e}")
            old_result = None
        
        # 新實現
        try:
            new_result = IPXELogParser.parse_line(log_line, log_type='BOOT')
            print(f"✅ 新實現解析成功")
            print(f"   結果: {new_result}")
        except Exception as e:
            print(f"❌ 新實現解析失敗: {e}")
            new_result = None
        
        # 對比結果
        if old_result and new_result:
            # 比較關鍵欄位
            keys_to_compare = ['ip_address', 'timestamp', 'method', 'file', 'status_code']
            
            differences = []
            for key in keys_to_compare:
                old_value = old_result.get(key)
                new_value = new_result.get(key)
                
                if old_value != new_value:
                    differences.append(f"  - {key}: '{old_value}' vs '{new_value}'")
            
            if differences:
                print(f"\n⚠️  發現差異:")
                for diff in differences:
                    print(diff)
                all_passed = False
            else:
                print(f"\n✅ 新舊實現輸出一致")
        else:
            print(f"\n❌ 無法對比（其中一個解析失敗）")
            all_passed = False
    
    print("\n" + "=" * 80)
    if all_passed:
        print("🎉 所有測試通過！新舊實現輸出完全一致。")
    else:
        print("⚠️  部分測試失敗或發現差異，需要進一步調整。")
    print("=" * 80)
    
    return all_passed


def test_new_implementation_features():
    """
    測試新實現的增強功能
    """
    print("\n" + "=" * 80)
    print("新實現增強功能測試")
    print("=" * 80)
    
    # 測試多種 log_type
    mac_log = '2025-10-25 03:05:11,397 - __main__ - INFO - Client 44:8a:5b:e4:2b:dc assigned to iPXE Boot Server: http://10.250.53.25:8080/boot.ipxe'
    boot_log = '10.250.53.25 - - [28/Oct/2025:10:18:57 +0000] "GET /boot.ipxe HTTP/1.1" 200 116 "-" "iPXE/1.21.1+ (g83449)" "-"'
    
    print("\n1. 測試 MAC Flask 日誌解析:")
    mac_result = IPXELogParser.parse_line(mac_log, log_type='MAC')
    print(f"   結果: {mac_result}")
    
    print("\n2. 測試 Boot 日誌解析:")
    boot_result = IPXELogParser.parse_line(boot_log, log_type='BOOT')
    print(f"   結果: {boot_result}")
    
    print("\n3. 測試自動偵測 (log_type='AUTO'):")
    auto_result = IPXELogParser.parse_line(boot_log, log_type='AUTO')
    print(f"   結果: {auto_result}")
    
    print("\n✅ 新實現提供更靈活的 log_type 選項")


def test_error_handling():
    """
    測試錯誤處理
    """
    print("\n" + "=" * 80)
    print("錯誤處理測試")
    print("=" * 80)
    
    invalid_logs = [
        '',
        'not a valid log',
        '123456789',
        None,
    ]
    
    print("\n測試無效日誌的處理...")
    for i, log in enumerate(invalid_logs, 1):
        print(f"\n[測試 {i}] 無效日誌: {repr(log)}")
        
        try:
            result = IPXELogParser.parse_line(log if log else '', log_type='BOOT')
            if result:
                print(f"   結果: {result}")
            else:
                print(f"   ✅ 正確返回 None（無法解析）")
        except Exception as e:
            print(f"   ❌ 拋出異常: {e}")


def main():
    """主測試函數"""
    print("\n" + "=" * 80)
    print("POC 遷移測試開始")
    print("時間:", "2025-10-30")
    print("目標:", "ipxe_service.py 的 parse_ipxe_log() 方法")
    print("=" * 80)
    
    # 測試 1: 新舊實現對比
    passed = test_ipxe_log_parsing_comparison()
    
    # 測試 2: 新實現增強功能
    test_new_implementation_features()
    
    # 測試 3: 錯誤處理
    test_error_handling()
    
    print("\n" + "=" * 80)
    print("POC 遷移測試完成")
    print("=" * 80)
    
    if passed:
        print("\n✅ 可以安全進行遷移！")
        return 0
    else:
        print("\n⚠️  建議先解決發現的差異再進行遷移")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
