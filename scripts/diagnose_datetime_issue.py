#!/usr/bin/env python
"""
診斷 datetime 時區問題的腳本
用於找出 "can't compare offset-naive and offset-aware datetimes" 錯誤的來源
"""

import os
import sys
import django

# 設置 Django 環境
sys.path.append('/home/owner/Codes/network-toolbox/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from datetime import datetime, timedelta
from django.utils import timezone
import pytz
from api.models import JenkinsBuild, JenkinsJob, JenkinsServer

def check_datetime_fields():
    """檢查資料庫中的 datetime 欄位是否有時區問題"""
    
    print("=" * 80)
    print("🔍 診斷 DateTime 時區問題")
    print("=" * 80)
    print()
    
    # 1. 檢查資料庫中的 Build
    print("1️⃣  檢查資料庫中的 JenkinsBuild 記錄...")
    builds = JenkinsBuild.objects.all()[:10]
    
    for build in builds:
        print(f"\n  Build: {build.job.name} #{build.build_number}")
        print(f"    build_timestamp: {build.build_timestamp}")
        print(f"    類型: {type(build.build_timestamp)}")
        print(f"    時區資訊: {build.build_timestamp.tzinfo}")
        print(f"    是否 aware: {build.build_timestamp.tzinfo is not None}")
        
        if build.workspace_stored_at:
            print(f"    workspace_stored_at: {build.workspace_stored_at}")
            print(f"    時區資訊: {build.workspace_stored_at.tzinfo}")
    
    print("\n" + "=" * 80)
    
    # 2. 測試 datetime 比較
    print("\n2️⃣  測試 datetime 比較...")
    
    # 創建 aware datetime（帶時區）
    now_aware = datetime.now(pytz.UTC)
    print(f"\n  now_aware = datetime.now(pytz.UTC)")
    print(f"    值: {now_aware}")
    print(f"    時區: {now_aware.tzinfo}")
    
    # 創建 naive datetime（不帶時區）
    now_naive = datetime.now()
    print(f"\n  now_naive = datetime.now()")
    print(f"    值: {now_naive}")
    print(f"    時區: {now_naive.tzinfo}")
    
    # 測試比較
    print("\n  測試比較...")
    try:
        result = now_aware < now_naive
        print(f"    ✅ now_aware < now_naive: {result}")
    except Exception as e:
        print(f"    ❌ 錯誤: {e}")
    
    # 3. 檢查 cutoff_time 計算
    print("\n" + "=" * 80)
    print("\n3️⃣  檢查 cutoff_time 計算...")
    
    max_age_days = 3
    cutoff_time_aware = datetime.now(pytz.UTC) - timedelta(days=max_age_days)
    print(f"\n  cutoff_time (aware): {cutoff_time_aware}")
    print(f"    時區: {cutoff_time_aware.tzinfo}")
    
    cutoff_time_naive = datetime.now() - timedelta(days=max_age_days)
    print(f"\n  cutoff_time (naive): {cutoff_time_naive}")
    print(f"    時區: {cutoff_time_naive.tzinfo}")
    
    # 4. 檢查資料庫查詢
    print("\n" + "=" * 80)
    print("\n4️⃣  測試資料庫查詢過濾...")
    
    # 使用 aware datetime 查詢
    print(f"\n  使用 aware datetime 查詢...")
    try:
        count = JenkinsBuild.objects.filter(
            build_timestamp__gte=cutoff_time_aware
        ).count()
        print(f"    ✅ 成功！找到 {count} 個 Builds")
    except Exception as e:
        print(f"    ❌ 錯誤: {e}")
    
    # 使用 naive datetime 查詢
    print(f"\n  使用 naive datetime 查詢...")
    try:
        count = JenkinsBuild.objects.filter(
            build_timestamp__gte=cutoff_time_naive
        ).count()
        print(f"    ✅ 成功！找到 {count} 個 Builds")
    except Exception as e:
        print(f"    ❌ 錯誤: {e}")
    
    # 5. 檢查特定問題 Builds
    print("\n" + "=" * 80)
    print("\n5️⃣  檢查可能有問題的 Builds...")
    
    problem_jobs = ['FW_QA_Primary_Seed', 'FW_QA_Secondary_Seed', 'SAF3201_KVM01']
    
    for job_name in problem_jobs:
        print(f"\n  檢查 Job: {job_name}")
        try:
            job = JenkinsJob.objects.get(name=job_name)
            builds = JenkinsBuild.objects.filter(job=job)[:3]
            
            for build in builds:
                print(f"    Build #{build.build_number}:")
                print(f"      build_timestamp: {build.build_timestamp}")
                print(f"      tzinfo: {build.build_timestamp.tzinfo}")
                
                # 測試比較
                try:
                    is_recent = build.build_timestamp > cutoff_time_aware
                    print(f"      比較結果: {'最近' if is_recent else '較舊'} ✅")
                except Exception as e:
                    print(f"      比較錯誤: {e} ❌")
                    
        except JenkinsJob.DoesNotExist:
            print(f"    ⚠️  Job 不存在")
        except Exception as e:
            print(f"    ❌ 錯誤: {e}")
    
    print("\n" + "=" * 80)
    print("\n✅ 診斷完成！")
    print("=" * 80)

if __name__ == '__main__':
    check_datetime_fields()
