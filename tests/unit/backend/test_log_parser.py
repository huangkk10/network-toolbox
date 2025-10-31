"""
日誌解析器整合測試

測試 library.utils.log_parser 的功能
"""
import os
import sys

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# 設置 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
import django
django.setup()

from library.utils import (
    DHCPLogParser,
    WindowsDHCPLogParser,
    IPXELogParser,
    LogLevel,
    parse_dhcp_log,
    parse_windows_dhcp_log,
    parse_ipxe_log,
)


def test_dhcp_log_parser():
    """測試 DHCP 日誌解析器"""
    print('\n' + '='*70)
    print('測試 1: DHCP 日誌解析器 (Linux/Unix)')
    print('='*70)
    
    test_logs = [
        '[INFO] 2025-10-27 14:30:22 | DHCPDISCOVER from 00:11:22:33:44:55 via eth0',
        '2025-10-27 14:30:23 INFO DHCPOFFER of 192.168.1.100 to 00:11:22:33:44:55',
        'Oct 27 14:30:24 server dhcpd[1234]: DHCPREQUEST from 00:11:22:33:44:55',
        '2025-10-27 14:30:25 ERROR Failed to assign IP address',
    ]
    
    try:
        for i, log_line in enumerate(test_logs, 1):
            entry = DHCPLogParser.parse_line(log_line)
            print(f'\n日誌 {i}:')
            print(f'  原始: {log_line}')
            print(f'  時間: {entry["timestamp"]}')
            print(f'  等級: {entry["level"]}')
            print(f'  訊息: {entry["message"]}')
        
        print('\n✅ DHCP 日誌解析測試通過')
        return True
    
    except Exception as e:
        print(f'\n❌ 測試失敗: {e}')
        import traceback
        traceback.print_exc()
        return False


def test_windows_dhcp_log_parser():
    """測試 Windows DHCP 日誌解析器"""
    print('\n' + '='*70)
    print('測試 2: Windows DHCP 日誌解析器')
    print('='*70)
    
    test_logs = [
        '10,10/27/25,14:24:02,Assign,192.168.7.199,host-name,aa:bb:cc:dd:ee:ff,0',
        '11,10/18/25,15:32:59,Renew,10.250.132.27,,BCFCE73A61C9,,727830406,0,,,,0x505845436C69656E74,PXEClient:Arch:00007,0x69505845,iPXE',
        '13,10/27/25,16:00:00,Deny,192.168.1.100,denied-host,11:22:33:44:55:66,0',
        '14,10/27/25,16:30:00,Conflict,192.168.1.50,,,0',
    ]
    
    try:
        for i, log_line in enumerate(test_logs, 1):
            entry = WindowsDHCPLogParser.parse_line(log_line)
            if entry:
                print(f'\n日誌 {i}:')
                print(f'  事件: {entry["event_type"]} (ID: {entry["event_id"]})')
                print(f'  時間: {entry["timestamp"]}')
                if 'ip_address' in entry:
                    print(f'  IP: {entry["ip_address"]}')
                if 'mac_address' in entry:
                    print(f'  MAC: {entry["mac_address"]}')
                if 'client_type' in entry:
                    print(f'  客戶端類型: {entry["client_type"]} ({entry.get("boot_stage", "")})')
                print(f'  訊息: {entry.get("message", "")}')
                print(f'  等級: {entry.get("level", LogLevel.INFO)}')
        
        print('\n✅ Windows DHCP 日誌解析測試通過')
        return True
    
    except Exception as e:
        print(f'\n❌ 測試失敗: {e}')
        import traceback
        traceback.print_exc()
        return False


def test_ipxe_log_parser():
    """測試 iPXE 日誌解析器"""
    print('\n' + '='*70)
    print('測試 3: iPXE 日誌解析器')
    print('='*70)
    
    # MAC Flask 日誌
    mac_log = '10.252.170.188 - - [28/Oct/2025:10:18:24 +0000] "GET /iPxeMac/Set?MAC=10:FF:E0:E2:91:56&BOOT=1 HTTP/1.1" 200 7 "-" "ansible-httpget"'
    
    # iPXE Boot 日誌
    boot_logs = [
        '10.250.53.25 - - [28/Oct/2025:10:18:57 +0000] "GET /boot.ipxe HTTP/1.1" 200 116 "-" "iPXE/1.21.1+ (g83449)"',
        '10.250.53.25 - - [28/Oct/2025:10:19:02 +0000] "GET /wimboot HTTP/1.1" 200 34816 "-" "iPXE/1.21.1+"',
        '10.250.53.25 - - [28/Oct/2025:10:19:05 +0000] "GET /Windows/Boot/BCD HTTP/1.1" 200 262144 "-" "iPXE/1.21.1+"',
    ]
    
    try:
        # 測試 MAC 日誌
        print('\nMAC Flask 日誌:')
        entry = IPXELogParser.parse_line(mac_log, log_type='MAC')
        if entry:
            print(f'  客戶端IP: {entry["client_ip"]}')
            print(f'  時間: {entry["timestamp"]}')
            print(f'  動作: {entry["action"]}')
            print(f'  MAC: {entry["mac_address"]}')
            print(f'  Boot Flag: {entry["boot_flag"]}')
            print(f'  狀態碼: {entry["status_code"]}')
        
        # 測試 Boot 日誌
        print('\niPXE Boot 日誌:')
        for i, log_line in enumerate(boot_logs, 1):
            entry = IPXELogParser.parse_line(log_line, log_type='BOOT')
            if entry:
                print(f'\n  日誌 {i}:')
                print(f'    客戶端IP: {entry["client_ip"]}')
                print(f'    動作: {entry["action"]}')
                print(f'    檔案: {entry["file_requested"]}')
                print(f'    狀態碼: {entry["status_code"]}')
                print(f'    大小: {entry["bytes_sent"]} bytes')
                print(f'    User-Agent: {entry["user_agent"][:50]}...')
        
        print('\n✅ iPXE 日誌解析測試通過')
        return True
    
    except Exception as e:
        print(f'\n❌ 測試失敗: {e}')
        import traceback
        traceback.print_exc()
        return False


def test_convenience_functions():
    """測試便捷函數"""
    print('\n' + '='*70)
    print('測試 4: 便捷函數')
    print('='*70)
    
    try:
        # 測試 parse_dhcp_log
        dhcp_content = """[INFO] 2025-10-27 14:30:22 | DHCPDISCOVER from 00:11:22:33:44:55 via eth0
[INFO] 2025-10-27 14:30:23 | DHCPOFFER of 192.168.1.100 to 00:11:22:33:44:55
[ERROR] 2025-10-27 14:30:24 | Failed to assign IP address"""
        
        entries = parse_dhcp_log(dhcp_content, limit=10)
        print(f'\nparse_dhcp_log: 解析 {len(entries)} 條日誌')
        for entry in entries:
            print(f'  {entry["level"]}: {entry["message"][:50]}...')
        
        # 測試 parse_windows_dhcp_log
        windows_content = """10,10/27/25,14:24:02,Assign,192.168.7.199,host-name,aa:bb:cc:dd:ee:ff,0
11,10/18/25,15:32:59,Renew,10.250.132.27,,BCFCE73A61C9,,727830406,0,,,,0x505845436C69656E74,PXEClient,0x69505845,iPXE"""
        
        entries = parse_windows_dhcp_log(windows_content, limit=10)
        print(f'\nparse_windows_dhcp_log: 解析 {len(entries)} 條日誌')
        for entry in entries:
            print(f'  {entry["event_type"]}: {entry.get("message", "")[:50]}...')
        
        # 測試 parse_ipxe_log
        ipxe_content = """10.250.53.25 - - [28/Oct/2025:10:18:57 +0000] "GET /boot.ipxe HTTP/1.1" 200 116 "-" "iPXE/1.21.1+"
10.250.53.25 - - [28/Oct/2025:10:19:02 +0000] "GET /wimboot HTTP/1.1" 200 34816 "-" "iPXE/1.21.1+" """
        
        entries = parse_ipxe_log(ipxe_content, log_type='BOOT', limit=10)
        print(f'\nparse_ipxe_log: 解析 {len(entries)} 條日誌')
        for entry in entries:
            print(f'  {entry["action"]}: {entry["file_requested"][:30]}...')
        
        print('\n✅ 便捷函數測試通過')
        return True
    
    except Exception as e:
        print(f'\n❌ 測試失敗: {e}')
        import traceback
        traceback.print_exc()
        return False


def test_log_level_inference():
    """測試日誌等級推斷"""
    print('\n' + '='*70)
    print('測試 5: 日誌等級推斷')
    print('='*70)
    
    test_messages = [
        ('Error occurred during processing', LogLevel.ERROR),
        ('Warning: threshold exceeded', LogLevel.WARN),
        ('Debug: checking configuration', LogLevel.DEBUG),
        ('Normal operation message', LogLevel.INFO),
        ('Failed to connect to server', LogLevel.ERROR),
    ]
    
    try:
        for message, expected_level in test_messages:
            inferred = DHCPLogParser._infer_log_level(message)
            status = '✅' if inferred == expected_level else '❌'
            print(f'{status} "{message[:40]}..." → {inferred} (預期: {expected_level})')
        
        print('\n✅ 日誌等級推斷測試通過')
        return True
    
    except Exception as e:
        print(f'\n❌ 測試失敗: {e}')
        return False


def test_windows_dhcp_sorting():
    """測試 Windows DHCP 日誌排序"""
    print('\n' + '='*70)
    print('測試 6: Windows DHCP 日誌排序')
    print('='*70)
    
    test_logs = [
        '10,10/28/25,10:00:00,Assign,192.168.1.100,host1,aa:bb:cc:dd:ee:11,0',
        '11,10/27/25,14:00:00,Renew,192.168.1.101,host2,aa:bb:cc:dd:ee:22,0',
        '10,10/29/25,08:00:00,Assign,192.168.1.102,host3,aa:bb:cc:dd:ee:33,0',
        '11,10/27/25,09:00:00,Renew,192.168.1.103,host4,aa:bb:cc:dd:ee:44,0',
    ]
    
    try:
        print('\n排序前:')
        for log in test_logs:
            parts = log.split(',')
            print(f'  {parts[1]} {parts[2]} - {parts[3]} {parts[4]}')
        
        sorted_logs = WindowsDHCPLogParser.sort_by_timestamp(test_logs)
        
        print('\n排序後:')
        for log in sorted_logs:
            parts = log.split(',')
            print(f'  {parts[1]} {parts[2]} - {parts[3]} {parts[4]}')
        
        print('\n✅ Windows DHCP 日誌排序測試通過')
        return True
    
    except Exception as e:
        print(f'\n❌ 測試失敗: {e}')
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """執行所有測試"""
    print('\n' + '#'*70)
    print('#' + ' '*18 + '日誌解析器整合測試' + ' '*18 + '#')
    print('#'*70)
    
    results = []
    
    results.append(('DHCP 日誌解析', test_dhcp_log_parser()))
    results.append(('Windows DHCP 日誌解析', test_windows_dhcp_log_parser()))
    results.append(('iPXE 日誌解析', test_ipxe_log_parser()))
    results.append(('便捷函數', test_convenience_functions()))
    results.append(('日誌等級推斷', test_log_level_inference()))
    results.append(('Windows DHCP 排序', test_windows_dhcp_sorting()))
    
    # 顯示總結
    print('\n' + '='*70)
    print('測試總結')
    print('='*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = '✅ 通過' if result else '❌ 失敗'
        print(f'{status} - {name}')
    
    print(f'\n總計: {passed}/{total} 個測試通過')
    
    if passed == total:
        print('\n🎉 所有測試通過！')
        return True
    else:
        print(f'\n⚠️  有 {total - passed} 個測試失敗')
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
