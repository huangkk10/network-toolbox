#!/usr/bin/env python
"""
修復資料庫中 JenkinsBuild 的時區問題
將所有 naive datetime 轉換為 aware datetime (UTC)
"""

import os
import sys
import django

# 設置 Django 環境
sys.path.append('/home/owner/Codes/network-toolbox/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from datetime import datetime
from django.utils import timezone
import pytz
from api.models import JenkinsBuild

def fix_datetime_timezone():
    """修復所有 Build 的時區問題"""
    
    print("=" * 80)
    print("🔧 修復 JenkinsBuild 時區問題")
    print("=" * 80)
    print()
    
    # 獲取所有沒有時區的 Build
    all_builds = JenkinsBuild.objects.all()
    total = all_builds.count()
    
    print(f"總共有 {total} 個 Build 記錄")
    print()
    
    # 統計
    naive_count = 0
    aware_count = 0
    fixed_count = 0
    error_count = 0
    
    print("開始檢查和修復...")
    print()
    
    for i, build in enumerate(all_builds, 1):
        try:
            # 檢查 build_timestamp
            if build.build_timestamp.tzinfo is None:
                # Naive datetime - 需要修復
                naive_count += 1
                
                # 轉換為 aware datetime (假設原本是 UTC)
                build.build_timestamp = pytz.UTC.localize(build.build_timestamp)
                build.save(update_fields=['build_timestamp'])
                fixed_count += 1
                
                if fixed_count <= 10:  # 只顯示前 10 個
                    print(f"  ✅ 修復: {build.job.name} #{build.build_number}")
            else:
                # 已經有時區資訊
                aware_count += 1
            
            # 每 100 個顯示進度
            if i % 100 == 0:
                print(f"  進度: {i}/{total} ({i*100//total}%)")
                
        except Exception as e:
            error_count += 1
            print(f"  ❌ 錯誤 ({build.job.name} #{build.build_number}): {e}")
    
    print()
    print("=" * 80)
    print("✅ 修復完成！")
    print("=" * 80)
    print(f"總共: {total} 個")
    print(f"已有時區: {aware_count} 個")
    print(f"需要修復: {naive_count} 個")
    print(f"成功修復: {fixed_count} 個")
    print(f"錯誤: {error_count} 個")
    print("=" * 80)

if __name__ == '__main__':
    # 確認
    response = input("\n⚠️  這將修改資料庫中的所有 Build 記錄，是否繼續？ (yes/no): ")
    if response.lower() == 'yes':
        fix_datetime_timezone()
    else:
        print("❌ 取消操作")
