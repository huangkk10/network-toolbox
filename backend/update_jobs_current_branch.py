#!/usr/bin/env python
"""
一次性腳本：更新所有 JenkinsJob 的 current_branch 欄位

從每個 Job 的最新 Build 的 parameters 中取得 branch 資訊並更新

執行方式：
    docker exec nt-django python update_jobs_current_branch.py
"""

import os
import sys
import django

# 設置 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.models import JenkinsJob, JenkinsBuild


def update_jobs_current_branch():
    """更新所有 Job 的 current_branch"""
    print("=" * 60)
    print("🔄 開始更新 JenkinsJob 的 current_branch 欄位")
    print("=" * 60)
    
    jobs = JenkinsJob.objects.all()
    total = jobs.count()
    updated = 0
    skipped = 0
    
    print(f"📊 找到 {total} 個 Jobs")
    print()
    
    for job in jobs:
        try:
            # 取得最新 Build
            latest_build = JenkinsBuild.objects.filter(job=job).order_by('-build_number').first()
            
            if not latest_build:
                print(f"  ⏭️  {job.name}: 無 Build 記錄，跳過")
                skipped += 1
                continue
            
            if not latest_build.parameters:
                print(f"  ⏭️  {job.name}: Build #{latest_build.build_number} 無 parameters，跳過")
                skipped += 1
                continue
            
            # 嘗試從 parameters 中取得 branch 資訊
            params = latest_build.parameters
            branch = (
                params.get('BRANCH') or 
                params.get('GIT_BRANCH') or 
                params.get('branch') or 
                params.get('git_branch') or
                ''
            )
            
            if branch:
                job.current_branch = branch
                job.save(update_fields=['current_branch'])
                print(f"  ✅ {job.name}: {branch}")
                updated += 1
            else:
                print(f"  ⏭️  {job.name}: parameters 中無 branch 資訊")
                skipped += 1
                
        except Exception as e:
            print(f"  ❌ {job.name}: 錯誤 - {e}")
            skipped += 1
    
    print()
    print("=" * 60)
    print("✅ 更新完成！")
    print(f"   - 已更新: {updated} 個 Jobs")
    print(f"   - 跳過: {skipped} 個 Jobs")
    print("=" * 60)


if __name__ == '__main__':
    update_jobs_current_branch()
