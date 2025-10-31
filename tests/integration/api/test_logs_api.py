#!/usr/bin/env python3
"""
測試 DHCP 日誌 API
測試所有日誌端點的功能
"""

import requests
import json

BASE_URL = "http://localhost/api/dhcp-analytics/logs/"

def print_section(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def test_local_logs():
    """測試本地日誌讀取"""
    print_section("測試 1: 讀取本地日誌（全部）")
    
    response = requests.get(BASE_URL, params={
        'source': 'local',
        'limit': 100
    })
    
    print(f"狀態碼: {response.status_code}")
    
    if response.status_code == 200:
        logs = response.json()
        print(f"總共獲取 {len(logs)} 條日誌")
        
        # 統計各級別數量
        levels = {}
        for log in logs:
            level = log['level']
            levels[level] = levels.get(level, 0) + 1
        
        print("\n日誌級別分佈:")
        for level, count in sorted(levels.items()):
            print(f"  {level}: {count} 條")
        
        print("\n前 3 條日誌:")
        for i, log in enumerate(logs[:3], 1):
            print(f"  {i}. [{log['level']}] {log['timestamp']} - {log['message']}")
    else:
        print(f"錯誤: {response.text}")

def test_filter_by_level():
    """測試按級別過濾"""
    print_section("測試 2: 過濾 ERROR 級別日誌")
    
    response = requests.get(BASE_URL, params={
        'source': 'local',
        'level': 'ERROR'
    })
    
    print(f"狀態碼: {response.status_code}")
    
    if response.status_code == 200:
        logs = response.json()
        print(f"找到 {len(logs)} 條 ERROR 日誌:")
        
        for i, log in enumerate(logs, 1):
            print(f"  {i}. {log['timestamp']} - {log['message']}")
    else:
        print(f"錯誤: {response.text}")

def test_keyword_search():
    """測試關鍵字搜尋"""
    print_section("測試 3: 關鍵字搜尋（DHCP）")
    
    response = requests.get(BASE_URL, params={
        'source': 'local',
        'keyword': 'DHCP'
    })
    
    print(f"狀態碼: {response.status_code}")
    
    if response.status_code == 200:
        logs = response.json()
        print(f"找到 {len(logs)} 條包含 'DHCP' 的日誌")
        
        print("\n前 5 條:")
        for i, log in enumerate(logs[:5], 1):
            print(f"  {i}. [{log['level']}] {log['message']}")
    else:
        print(f"錯誤: {response.text}")

def test_combined_filters():
    """測試組合過濾"""
    print_section("測試 4: 組合過濾（WARN + pool）")
    
    response = requests.get(BASE_URL, params={
        'source': 'local',
        'level': 'WARN',
        'keyword': 'pool'
    })
    
    print(f"狀態碼: {response.status_code}")
    
    if response.status_code == 200:
        logs = response.json()
        print(f"找到 {len(logs)} 條符合條件的日誌:")
        
        for i, log in enumerate(logs, 1):
            print(f"  {i}. [{log['level']}] {log['timestamp']} - {log['message']}")
    else:
        print(f"錯誤: {response.text}")

def test_limit():
    """測試數量限制"""
    print_section("測試 5: 限制返回數量（5 條）")
    
    response = requests.get(BASE_URL, params={
        'source': 'local',
        'limit': 5
    })
    
    print(f"狀態碼: {response.status_code}")
    
    if response.status_code == 200:
        logs = response.json()
        print(f"獲取了 {len(logs)} 條日誌（應為 5 條）:")
        
        for i, log in enumerate(logs, 1):
            print(f"  {i}. [{log['level']}] {log['timestamp']} - {log['message'][:50]}...")
    else:
        print(f"錯誤: {response.text}")

def main():
    print("\n" + "🔍 DHCP 日誌 API 測試".center(60, "="))
    print("測試時間:", requests.get("http://localhost/api/").json().get("timestamp", "N/A"))
    
    try:
        test_local_logs()
        test_filter_by_level()
        test_keyword_search()
        test_combined_filters()
        test_limit()
        
        print("\n" + "✅ 所有測試完成！".center(60, "=") + "\n")
        
    except Exception as e:
        print(f"\n❌ 測試過程中出現錯誤: {e}\n")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
