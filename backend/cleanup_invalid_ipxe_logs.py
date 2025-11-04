#!/usr/bin/env python
"""
清理無效的 iPXE 日誌

問題：IPXELog 表中混入了 Windows DHCP 日誌（CSV 格式），需要清理

正確的 iPXE 日誌格式：
- Nginx access log: 10.250.71.22 - - [04/Nov/2025:09:24:39 +0000] "GET /boot.ipxe HTTP/1.1" 200 116

錯誤的日誌格式（Windows DHCP CSV）：
- 11,11/04/25,09:24:39,Renew,10.250.71.22,,CC28A0A6C37F,...
"""
import os
import sys
import django

# 設置 Django 環境
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.models import IPXELog, IPXEServer
import re

def is_valid_ipxe_log(raw_log: str) -> bool:
    """
    檢查是否為有效的 iPXE 日誌（Nginx access log 格式）
    
    正確格式示例：
    10.250.71.22 - - [04/Nov/2025:09:24:39 +0000] "GET /boot.ipxe HTTP/1.1" 200 116 "-" "iPXE/1.21.1+"
    """
    if not raw_log:
        return False
    
    # Nginx access log 格式的正則表達式
    nginx_pattern = r'^\d+\.\d+\.\d+\.\d+ - - \[[^\]]+\] "[A-Z]+ [^\s]+ HTTP/[\d\.]+" \d+ \d+'
    
    # Windows DHCP CSV 格式特徵（以數字和逗號開頭）
    dhcp_csv_pattern = r'^\d+,\d{2}/\d{2}/\d{2},'
    
    if re.match(nginx_pattern, raw_log):
        return True
    elif re.match(dhcp_csv_pattern, raw_log):
        print(f'   ❌ 檢測到 Windows DHCP 日誌: {raw_log[:80]}...')
        return False
    else:
        print(f'   ⚠️  未知格式: {raw_log[:80]}...')
        return False

def main():
    print('=' * 80)
    print('清理無效的 iPXE 日誌')
    print('=' * 80)
    
    # 統計
    total_logs = IPXELog.objects.count()
    print(f'\n📊 總日誌數: {total_logs}')
    
    # 檢查所有 iPXE Server
    servers = IPXEServer.objects.all()
    print(f'\n🖥️  iPXE Servers: {servers.count()}')
    for server in servers:
        print(f'   - {server.name} ({server.ip_address})')
    
    # 找出無效的日誌
    print('\n🔍 檢查日誌有效性...')
    invalid_logs = []
    
    all_logs = IPXELog.objects.all()
    print(f'   檢查 {all_logs.count()} 條日誌...')
    
    for i, log in enumerate(all_logs, 1):
        if i % 100 == 0:
            print(f'   進度: {i}/{all_logs.count()}', end='\r')
        
        if not is_valid_ipxe_log(log.raw):
            invalid_logs.append(log)
    
    print(f'\n\n❌ 發現 {len(invalid_logs)} 條無效日誌')
    
    if invalid_logs:
        print('\n無效日誌詳情：')
        for i, log in enumerate(invalid_logs[:10], 1):  # 只顯示前 10 條
            print(f'\n{i}. ID: {log.id}')
            print(f'   Server: {log.server.name} ({log.server.ip_address})')
            print(f'   類型: {log.log_type}')
            print(f'   時間: {log.timestamp}')
            print(f'   RAW: {log.raw[:100]}...')
        
        if len(invalid_logs) > 10:
            print(f'\n   ... 還有 {len(invalid_logs) - 10} 條無效日誌')
        
        # 詢問是否刪除
        print('\n' + '=' * 80)
        response = input(f'\n是否刪除這 {len(invalid_logs)} 條無效日誌？ (yes/no): ')
        
        if response.lower() in ['yes', 'y']:
            print('\n🗑️  刪除無效日誌...')
            deleted_count = 0
            for log in invalid_logs:
                log.delete()
                deleted_count += 1
            
            print(f'✅ 已刪除 {deleted_count} 條無效日誌')
            print(f'📊 剩餘日誌: {IPXELog.objects.count()}')
        else:
            print('\n取消刪除操作')
    else:
        print('\n✅ 所有日誌格式正確！')
    
    print('\n' + '=' * 80)
    print('清理完成')
    print('=' * 80)

if __name__ == '__main__':
    main()
