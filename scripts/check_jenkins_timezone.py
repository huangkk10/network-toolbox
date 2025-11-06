#!/usr/bin/env python
"""
檢查 Jenkins 伺服器的時區設定
用於判斷是否需要進行時區轉換
"""

import os
import sys
import django
import requests
from datetime import datetime
import pytz

# 設置 Django 環境
sys.path.append('/home/owner/Codes/network-toolbox/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.models import JenkinsServer

def check_jenkins_timezone(server):
    """
    檢查 Jenkins 伺服器的時區設定
    
    方法：
    1. 呼叫 Jenkins API 取得系統資訊
    2. 比較 Jenkins 回傳的時間與本地時間
    3. 計算時差來判斷時區
    """
    
    print("=" * 80)
    print(f"🔍 檢查 Jenkins 伺服器時區：{server.name}")
    print("=" * 80)
    print()
    
    # 1. Jenkins API - 取得系統資訊
    print("1️⃣  呼叫 Jenkins API 取得系統資訊...")
    
    try:
        # Jenkins 系統資訊 API
        api_url = f"{server.url}/api/json"
        
        response = requests.get(
            api_url,
            auth=(server.username, server.password),
            timeout=10,
            verify=False
        )
        
        if response.status_code != 200:
            print(f"  ❌ API 呼叫失敗：HTTP {response.status_code}")
            return None
        
        data = response.json()
        print(f"  ✅ 成功取得 Jenkins 系統資訊")
        
    except Exception as e:
        print(f"  ❌ 錯誤：{e}")
        return None
    
    # 2. 取得一個最近的 Build 來比較時間
    print("\n2️⃣  取得最近的 Build 資訊...")
    
    try:
        # 取得第一個 Job
        if 'jobs' not in data or not data['jobs']:
            print("  ⚠️  沒有找到任何 Job")
            return None
        
        first_job = data['jobs'][0]
        job_name = first_job['name']
        job_url = first_job['url']
        
        print(f"  使用 Job: {job_name}")
        
        # 取得 Job 的最後一個 Build
        job_api_url = f"{job_url}/api/json"
        job_response = requests.get(
            job_api_url,
            auth=(server.username, server.password),
            timeout=10,
            verify=False
        )
        
        if job_response.status_code != 200:
            print(f"  ❌ 取得 Job 資訊失敗")
            return None
        
        job_data = job_response.json()
        
        if 'lastBuild' not in job_data or not job_data['lastBuild']:
            print(f"  ⚠️  Job 沒有任何 Build")
            return None
        
        build_number = job_data['lastBuild']['number']
        build_url = job_data['lastBuild']['url']
        
        print(f"  使用 Build: #{build_number}")
        
        # 取得 Build 詳細資訊
        build_api_url = f"{build_url}/api/json"
        build_response = requests.get(
            build_api_url,
            auth=(server.username, server.password),
            timeout=10,
            verify=False
        )
        
        if build_response.status_code != 200:
            print(f"  ❌ 取得 Build 資訊失敗")
            return None
        
        build_data = build_response.json()
        
        # Jenkins 回傳的 timestamp (毫秒)
        jenkins_timestamp_ms = build_data.get('timestamp', 0)
        jenkins_timestamp_sec = jenkins_timestamp_ms / 1000
        
        print(f"  ✅ Jenkins timestamp: {jenkins_timestamp_ms} ms")
        
    except Exception as e:
        print(f"  ❌ 錯誤：{e}")
        return None
    
    # 3. 分析時間差異
    print("\n3️⃣  分析時區...")
    print()
    
    # Unix timestamp 是 UTC 絕對時間，不受時區影響
    # 所以我們需要用其他方法判斷
    
    # 方法 A：檢查 Jenkins 的 systemMessage 或 description
    print("  【方法 A】檢查 Jenkins 系統描述...")
    if 'description' in data:
        print(f"    Description: {data['description']}")
    else:
        print(f"    ⚠️  無系統描述")
    
    # 方法 B：呼叫 Jenkins Script Console API（需要管理員權限）
    print("\n  【方法 B】嘗試執行 Groovy Script 查詢時區...")
    try:
        script_url = f"{server.url}/scriptText"
        groovy_script = """
import java.util.TimeZone

def tz = TimeZone.getDefault()
println "Timezone ID: ${tz.getID()}"
println "Display Name: ${tz.getDisplayName()}"
println "Raw Offset: ${tz.getRawOffset() / 3600000} hours"

def now = new Date()
println "Current Time: ${now}"
println "Timezone: ${tz.getDisplayName(tz.inDaylightTime(now), TimeZone.LONG)}"
"""
        
        script_response = requests.post(
            script_url,
            data={'script': groovy_script},
            auth=(server.username, server.password),
            timeout=10,
            verify=False
        )
        
        if script_response.status_code == 200:
            print("    ✅ 成功執行 Groovy Script：")
            print()
            for line in script_response.text.strip().split('\n'):
                print(f"      {line}")
            print()
            
            # 解析時區
            timezone_id = None
            offset_hours = None
            
            for line in script_response.text.strip().split('\n'):
                if 'Timezone ID:' in line:
                    timezone_id = line.split(':', 1)[1].strip()
                if 'Raw Offset:' in line:
                    try:
                        offset_hours = float(line.split(':', 1)[1].replace('hours', '').strip())
                    except:
                        pass
            
            # 判斷時區
            print("  📊 時區判斷結果：")
            print(f"    時區 ID: {timezone_id}")
            print(f"    時差: UTC{'+' if offset_hours >= 0 else ''}{offset_hours} 小時")
            print()
            
            if timezone_id == 'Asia/Taipei' or offset_hours == 8:
                print("    ✅ Jenkins 使用 Taipei 時區（UTC+8）")
                print("    → 可以使用方案 B（直接儲存為 Taipei 時間）")
                return 'Taipei'
            elif timezone_id == 'UTC' or offset_hours == 0:
                print("    ✅ Jenkins 使用 UTC 時區")
                print("    → 應該使用方案 A（儲存 UTC，顯示時轉換）")
                return 'UTC'
            else:
                print(f"    ⚠️  Jenkins 使用其他時區：{timezone_id}")
                print(f"    → 需要針對 {timezone_id} 進行轉換")
                return timezone_id
                
        else:
            print(f"    ❌ 無法執行 Script（需要管理員權限）：HTTP {script_response.status_code}")
            
    except Exception as e:
        print(f"    ❌ 錯誤：{e}")
    
    # 方法 C：比較 Jenkins timestamp 與本地時間（不準確，僅供參考）
    print("\n  【方法 C】比較 timestamp（參考用）...")
    
    # 將 Unix timestamp 轉換為不同時區
    dt_utc = datetime.fromtimestamp(jenkins_timestamp_sec, tz=pytz.UTC)
    dt_taipei = dt_utc.astimezone(pytz.timezone('Asia/Taipei'))
    
    print(f"    Build timestamp (UTC):    {dt_utc}")
    print(f"    Build timestamp (Taipei): {dt_taipei}")
    print()
    print(f"    ⚠️  注意：Unix timestamp 本身不含時區資訊")
    print(f"    ⚠️  無法從 timestamp 判斷 Jenkins 的時區設定")
    
    print("\n" + "=" * 80)
    print("\n📋 總結：")
    print()
    print("  要準確判斷 Jenkins 時區，需要：")
    print("    1. Jenkins 管理員權限（執行 Groovy Script）")
    print("    2. 或者直接問系統管理員")
    print("    3. 或者查看 Jenkins 啟動參數（-Duser.timezone=...）")
    print()
    print("  Unix timestamp 是絕對時間，不受 Jenkins 時區影響")
    print("  所以理論上不需要知道 Jenkins 時區也能正確處理")
    print()
    print("=" * 80)
    
    return None

def main():
    """主程式"""
    
    # 取得所有 Jenkins Server
    servers = JenkinsServer.objects.all()
    
    if not servers.exists():
        print("❌ 沒有找到任何 Jenkins Server")
        return
    
    print(f"找到 {servers.count()} 個 Jenkins Server")
    print()
    
    for server in servers:
        result = check_jenkins_timezone(server)
        print()
        
        if result:
            print(f"✅ {server.name}: {result}")
        else:
            print(f"⚠️  {server.name}: 無法判斷時區")
        
        print()
        print("=" * 80)
        print()

if __name__ == '__main__':
    main()
