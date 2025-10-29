#!/usr/bin/env python3
"""
測試 iPXE 檢測功能

測試範例日誌：
1. iPXE 階段：11,10/18/25,15:32:59,Renew,10.250.132.27,,BCFCE73A61C9,,727830406,0,,,,0x505845436C69656E74...PXEClient:Arch:00007:UNDI:003010,0x69505845,iPXE
2. PXE 階段：11,10/18/25,15:32:54,Renew,10.250.132.27,,BCFCE73A61C9,,610079976,0,,,,0x505845436C69656E74...PXEClient:Arch:00007:UNDI:003016
3. WinPE 階段：11,10/18/25,15:35:55,Renew,10.250.132.27,minint-pkc1vk8,BCFCE73A61C9,,313489413,0,,,,0x4D53465420352E30,MSFT 5.0
4. OS 階段：11,10/18/25,15:41:52,Renew,10.250.132.27,pynvme-pc,BCFCE73A61C9,,2837896269,0,,,,,,,,,0
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')

import django
django.setup()

from api.services import WindowsDHCPLogParser

# 測試日誌範例
test_logs = [
    # iPXE 階段（明確的 iPXE 標識）
    '11,10/18/25,15:32:59,Renew,10.250.132.27,,BCFCE73A61C9,,727830406,0,,,,0x505845436C69656E74...PXEClient:Arch:00007:UNDI:003010,0x69505845,iPXE',
    
    # PXE 階段（BIOS PXE ROM）
    '11,10/18/25,15:32:54,Renew,10.250.132.27,,BCFCE73A61C9,,610079976,0,,,,0x505845436C69656E74...PXEClient:Arch:00007:UNDI:003016',
    
    # WinPE 階段（Windows PE）
    '11,10/18/25,15:35:55,Renew,10.250.132.27,minint-pkc1vk8,BCFCE73A61C9,,313489413,0,,,,0x4D53465420352E30,MSFT 5.0',
    
    # OS 階段（正常 OS 運行）
    '11,10/18/25,15:41:52,Renew,10.250.132.27,pynvme-pc,BCFCE73A61C9,,2837896269,0,,,,,,,,,0',
    
    # 另一個 iPXE 範例（包含 VendorClass 和 UserClass）
    '11,10/18/25,15:35:11,Renew,10.250.132.27,,BCFCE73A61C9,,1234567890,0,,,,PXEClient:Arch:00007,PXEClient:Arch:00007,0x69505845,iPXE',
]

print("=" * 80)
print("測試 WindowsDHCPLogParser - iPXE 檢測功能")
print("=" * 80)

# 解析測試日誌
parsed_logs = WindowsDHCPLogParser.parse_log_lines(test_logs, limit=100)

for idx, log in enumerate(parsed_logs, 1):
    print(f"\n測試 {idx}:")
    print(f"  時間戳: {log['timestamp']}")
    print(f"  等級: {log['level']}")
    print(f"  事件: {log['event']}")
    print(f"  訊息: {log['message']}")
    print(f"  客戶端類型: {log['client_type']}")
    print(f"  啟動階段: {log['boot_stage']}")
    if log['vendor_class']:
        print(f"  Vendor Class: {log['vendor_class']}")
    if log['user_class']:
        print(f"  User Class: {log['user_class']}")
    print(f"  原始日誌: {log['raw'][:80]}...")

print("\n" + "=" * 80)
print("測試結果統計:")
print("=" * 80)

# 統計結果
client_types = {}
for log in parsed_logs:
    ct = log['client_type']
    client_types[ct] = client_types.get(ct, 0) + 1

for ct, count in client_types.items():
    print(f"  {ct}: {count} 筆")

# 驗證預期結果
expected_results = {
    0: ('iPXE', 'iPXE Loading'),
    1: ('PXE', 'BIOS PXE'),
    2: ('WinPE', 'Windows PE'),
    3: ('OS', 'Operating System'),
    4: ('iPXE', 'iPXE Loading'),
}

print("\n" + "=" * 80)
print("驗證結果:")
print("=" * 80)

all_correct = True
for idx, (expected_type, expected_stage) in expected_results.items():
    if idx < len(parsed_logs):
        actual_type = parsed_logs[idx]['client_type']
        actual_stage = parsed_logs[idx]['boot_stage']
        
        is_correct = (actual_type == expected_type and actual_stage == expected_stage)
        status = "✓ 通過" if is_correct else "✗ 失敗"
        
        print(f"測試 {idx + 1}: {status}")
        print(f"  預期: {expected_type} / {expected_stage}")
        print(f"  實際: {actual_type} / {actual_stage}")
        
        if not is_correct:
            all_correct = False
    else:
        print(f"測試 {idx + 1}: ✗ 失敗 (沒有解析結果)")
        all_correct = False

print("\n" + "=" * 80)
if all_correct:
    print("✓ 所有測試通過！iPXE 檢測功能正常運作！")
else:
    print("✗ 部分測試失敗，請檢查實作")
print("=" * 80)
