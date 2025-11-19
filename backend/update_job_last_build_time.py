"""
更新 Jenkins Job 的 last_build_time 欄位

此腳本會遍歷所有 Jenkins Jobs，並從它們的最新 Build 中更新 last_build_time 欄位。

使用方法：
    python update_job_last_build_time.py
"""

import os
import sys
import django

# Django setup
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.models import JenkinsJob, JenkinsBuild
from django.db.models import Max


def update_all_jobs_last_build_time():
    """更新所有 Jobs 的 last_build_time"""
    
    print("開始更新 Jenkins Jobs 的 last_build_time...")
    
    # 獲取所有 Jobs
    jobs = JenkinsJob.objects.all()
    total_jobs = jobs.count()
    updated_count = 0
    no_builds_count = 0
    
    print(f"總共 {total_jobs} 個 Jobs 需要處理")
    
    for idx, job in enumerate(jobs, 1):
        # 獲取該 Job 的最新 Build
        latest_build = job.builds.order_by('-build_number').first()
        
        if latest_build and latest_build.build_timestamp:
            # 更新 Job 的 last_build_time
            job.last_build_time = latest_build.build_timestamp
            job.last_build_number = latest_build.build_number
            job.last_build_status = latest_build.result
            job.save(update_fields=['last_build_time', 'last_build_number', 'last_build_status'])
            updated_count += 1
            
            if idx % 50 == 0:
                print(f"進度: {idx}/{total_jobs} ({updated_count} 已更新)")
        else:
            no_builds_count += 1
    
    print(f"\n完成！")
    print(f"  總 Jobs: {total_jobs}")
    print(f"  已更新: {updated_count}")
    print(f"  無 Build 數據: {no_builds_count}")


if __name__ == '__main__':
    update_all_jobs_last_build_time()
