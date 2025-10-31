#!/usr/bin/env python3
"""
批次修正 WinPE 誤判記錄

此腳本會：
1. 找出所有在 iPXE 活動時段內的 DHCP 記錄
2. 檢查是否被誤判為 Windows（實際應為 WinPE）
3. 重新標記為 WinPE

作者：Network Toolbox Team
日期：2025-11-01
"""
import os
import sys
import django
from datetime import timedelta

# 設定 Django 環境
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from django.db.models import Q
from api.models import DHCPLog, IPXELog
from django.utils import timezone


def find_misidentified_records(time_window_minutes=10, dry_run=True):
    """
    找出並修正被誤判的 WinPE 記錄
    
    Args:
        time_window_minutes: 時間窗口（分鐘）
        dry_run: 是否為測試模式（不實際修改資料庫）
    """
    print('=' * 80)
    print('WinPE Misidentification Fix Script')
    print('=' * 80)
    print(f'Time Window: ±{time_window_minutes} minutes')
    print(f'Mode: {"DRY RUN (no changes will be made)" if dry_run else "LIVE (will update database)"}')
    print('=' * 80)
    print()
    
    # 統計資訊
    total_checked = 0
    total_misidentified = 0
    total_fixed = 0
    
    # 1. 獲取所有 iPXE 活動記錄（按 MAC 分組）
    print('[Step 1] Analyzing iPXE Activity...')
    ipxe_logs = IPXELog.objects.all().order_by('mac_address', 'timestamp')
    
    mac_ipxe_sessions = {}  # {mac: [(start, end), ...]}
    current_mac = None
    session_start = None
    last_timestamp = None
    
    for log in ipxe_logs:
        if log.mac_address != current_mac:
            # 新的 MAC，儲存前一個會話
            if current_mac and session_start:
                if current_mac not in mac_ipxe_sessions:
                    mac_ipxe_sessions[current_mac] = []
                mac_ipxe_sessions[current_mac].append((session_start, last_timestamp))
            
            # 開始新的會話
            current_mac = log.mac_address
            session_start = log.timestamp
            last_timestamp = log.timestamp
        else:
            # 同一個 MAC
            time_diff = (log.timestamp - last_timestamp).total_seconds() / 60
            
            if time_diff > 30:  # 超過 30 分鐘視為新會話
                # 儲存舊會話
                if current_mac not in mac_ipxe_sessions:
                    mac_ipxe_sessions[current_mac] = []
                mac_ipxe_sessions[current_mac].append((session_start, last_timestamp))
                
                # 開始新會話
                session_start = log.timestamp
            
            last_timestamp = log.timestamp
    
    # 儲存最後一個會話
    if current_mac and session_start:
        if current_mac not in mac_ipxe_sessions:
            mac_ipxe_sessions[current_mac] = []
        mac_ipxe_sessions[current_mac].append((session_start, last_timestamp))
    
    print(f'  Found {len(mac_ipxe_sessions)} MACs with iPXE activity')
    total_sessions = sum(len(sessions) for sessions in mac_ipxe_sessions.values())
    print(f'  Total iPXE sessions: {total_sessions}')
    print()
    
    # 2. 檢查每個 iPXE 會話期間的 DHCP 記錄
    print('[Step 2] Checking DHCP Logs during iPXE Sessions...')
    
    for mac, sessions in mac_ipxe_sessions.items():
        print(f'\n  MAC: {mac} ({len(sessions)} sessions)')
        
        for session_start, session_end in sessions:
            # 擴展時間窗口
            window_start = session_start - timedelta(minutes=time_window_minutes)
            window_end = session_end + timedelta(minutes=time_window_minutes)
            
            print(f'    Session: {session_start} ~ {session_end}')
            print(f'    Window:  {window_start} ~ {window_end}')
            
            # 查詢此時段的 DHCP 記錄
            # 使用 raw__icontains 因為 MAC 地址格式可能不同
            mac_no_colon = mac.replace(':', '').upper()
            
            dhcp_logs = DHCPLog.objects.filter(
                timestamp__gte=window_start,
                timestamp__lte=window_end,
                raw__icontains=mac_no_colon
            ).order_by('timestamp')
            
            total_checked += dhcp_logs.count()
            
            for dhcp_log in dhcp_logs:
                # 檢查是否被誤判為 Windows
                if dhcp_log.client_type == 'Windows':
                    # 檢查是否有 User Class（WinPE 通常沒有）
                    if not dhcp_log.user_class or dhcp_log.user_class == '-':
                        total_misidentified += 1
                        
                        print(f'      ⚠️  MISIDENTIFIED: {dhcp_log.timestamp}')
                        print(f'         Current: client_type=Windows, boot_stage={dhcp_log.boot_stage}')
                        print(f'         Hostname: {dhcp_log.raw.split(",")[5] if dhcp_log.raw else "N/A"}')
                        print(f'         Vendor: {dhcp_log.vendor_class or "N/A"}')
                        print(f'         User Class: {dhcp_log.user_class or "N/A"}')
                        
                        if not dry_run:
                            # 更新記錄
                            dhcp_log.client_type = 'WinPE'
                            dhcp_log.boot_stage = 'Windows PE'
                            dhcp_log.save(update_fields=['client_type', 'boot_stage'])
                            total_fixed += 1
                            print(f'         ✓ FIXED: Updated to WinPE')
                        else:
                            print(f'         → Would fix: client_type=WinPE, boot_stage=Windows PE')
    
    # 3. 顯示統計結果
    print()
    print('=' * 80)
    print('Summary')
    print('=' * 80)
    print(f'Total DHCP records checked: {total_checked}')
    print(f'Total misidentified records: {total_misidentified}')
    
    if dry_run:
        print(f'Records that would be fixed: {total_misidentified}')
        print()
        print('⚠️  This was a DRY RUN. No changes were made to the database.')
        print('   To apply the fixes, run with --live flag:')
        print('   python fix_winpe_misidentification.py --live')
    else:
        print(f'Records fixed: {total_fixed}')
        print()
        print('✓ Database has been updated.')
    
    print('=' * 80)


def verify_specific_record(mac, timestamp_str):
    """
    驗證特定記錄是否已修正
    
    Args:
        mac: MAC 地址
        timestamp_str: 時間戳字串（格式：YYYY-MM-DD HH:MM:SS）
    """
    from datetime import datetime
    
    print('=' * 80)
    print('Verify Specific Record')
    print('=' * 80)
    print(f'MAC: {mac}')
    print(f'Timestamp: {timestamp_str}')
    print('=' * 80)
    print()
    
    # 查詢記錄
    mac_no_colon = mac.replace(':', '').upper()
    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
    
    logs = DHCPLog.objects.filter(
        timestamp=timestamp,
        raw__icontains=mac_no_colon
    )
    
    if logs.exists():
        log = logs.first()
        print('Record Found:')
        print(f'  Timestamp: {log.timestamp}')
        print(f'  Client Type: {log.client_type}')
        print(f'  Boot Stage: {log.boot_stage}')
        print(f'  Vendor Class: {log.vendor_class or "N/A"}')
        print(f'  User Class: {log.user_class or "N/A"}')
        print(f'  Hostname: {log.raw.split(",")[5] if log.raw else "N/A"}')
        print()
        
        # 檢查前後的 iPXE 活動
        window_start = timestamp - timedelta(minutes=10)
        window_end = timestamp + timedelta(minutes=10)
        
        ipxe_logs = IPXELog.objects.filter(
            mac_address=mac,
            timestamp__gte=window_start,
            timestamp__lte=window_end
        ).order_by('timestamp')
        
        print(f'iPXE Activity (±10 minutes): {ipxe_logs.count()} records')
        for ipxe_log in ipxe_logs:
            print(f'  {ipxe_log.timestamp} - {ipxe_log.action} (User Agent: {ipxe_log.user_agent})')
        
        print()
        if log.client_type == 'WinPE':
            print('✓ Status: Correctly identified as WinPE')
        elif ipxe_logs.count() > 0:
            print('⚠️  Status: Has iPXE activity but marked as', log.client_type)
        else:
            print('✓ Status: No iPXE activity, correctly identified as', log.client_type)
    else:
        print('❌ Record not found!')
    
    print('=' * 80)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Fix WinPE misidentification in DHCP logs')
    parser.add_argument('--live', action='store_true', help='Apply changes (default is dry-run)')
    parser.add_argument('--window', type=int, default=10, help='Time window in minutes (default: 10)')
    parser.add_argument('--verify', nargs=2, metavar=('MAC', 'TIMESTAMP'),
                        help='Verify a specific record (e.g., cc:28:aa:86:c3:7f "2025-11-01 04:05:32")')
    
    args = parser.parse_args()
    
    if args.verify:
        verify_specific_record(args.verify[0], args.verify[1])
    else:
        find_misidentified_records(
            time_window_minutes=args.window,
            dry_run=not args.live
        )
