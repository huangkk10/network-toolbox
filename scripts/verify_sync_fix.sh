#!/bin/bash
# 驗證 sync_jenkins_builds 修復效果
# 使用方式: ./scripts/verify_sync_fix.sh

echo "=================================================="
echo "  Jenkins Builds 同步修復驗證腳本"
echo "=================================================="
echo ""

# 1. 檢查最近的任務執行結果
echo "📊 1. 檢查最近的任務執行結果:"
echo "-----------------------------------"
docker logs --since "15m" nt-celery-worker 2>&1 | grep "sync_jenkins_builds.*succeeded" | tail -1 | \
    python3 -c "
import sys
import re
import json

line = sys.stdin.read()
if not line:

    print('❌ 尚未執行任務（等待下次執行）')
    sys.exit(1)

# 提取結果 JSON
match = re.search(r'succeeded in ([\d.]+)s: ({.*})', line)
if match:
    duration = float(match.group(1))
    result_json = match.group(2)
    result = eval(result_json)  # 簡單解析
    
    print(f'✅ 任務執行成功！')
    print(f'   執行時間: {duration:.2f} 秒')
    print(f'   API 調用: {result.get(\"total_api_calls\", 0)} 次')
    print(f'   跳過 Jobs: {result.get(\"total_jobs_skipped\", 0)} 個')
    print(f'   創建 Builds: {result.get(\"builds_created\", 0)} 個')
    print(f'   更新 Builds: {result.get(\"builds_updated\", 0)} 個')
    print(f'   錯誤數: {result.get(\"errors\", 0)}')
    print('')
    
    # 驗證預期結果
    if duration < 60 and result.get('total_api_calls', 0) > 1000:
        print('✅ 性能符合預期（< 60秒 且 > 1000 次 API 調用）')
    else:
        print(f'⚠️  性能待確認（預期: < 60秒 且 > 1000 次調用）')
else:
    print('❌ 無法解析任務結果')
"

echo ""

# 2. 檢查 Test-KVM01 的最新 Build
echo "📊 2. 檢查 Test-KVM01 的最新 Build:"
echo "-----------------------------------"
docker exec nt-django python manage.py shell -c "
from api.models import JenkinsJob, JenkinsBuild

job = JenkinsJob.objects.filter(server_id=12, name='Test-KVM01').first()
if not job:
    print('❌ 找不到 Test-KVM01 Job')
else:
    latest = JenkinsBuild.objects.filter(job=job).order_by('-build_number').first()
    if latest:
        print(f'資料庫最新 Build: #{latest.build_number}')
        print(f'Build 時間: {latest.build_timestamp}')
        print(f'Build 狀態: {latest.result}')
        print('')
        
        # 檢查是否是今天的 Build
        from django.utils import timezone
        from datetime import timedelta
        
        today = timezone.now().date()
        build_date = latest.build_timestamp.date()
        
        if build_date == today:
            print('✅ 已同步到今天的 Build！修復成功！')
        elif (today - build_date).days <= 1:
            print(f'⚠️  最新 Build 是昨天的（{build_date}），可能還需要再等一次同步')
        else:
            print(f'❌ 最新 Build 仍然過期（{build_date}），需要檢查')
    else:
        print('❌ 沒有 Build 記錄')
"

echo ""

# 3. 比對 Jenkins Server 上的實際數據
echo "📊 3. 比對 Jenkins Server 實際數據:"
echo "-----------------------------------"
docker exec nt-django python manage.py shell -c "
from library.services.jenkins_client import JenkinsClient
from api.models import JenkinsJob, JenkinsBuild

# 從 Jenkins API 獲取最新 Build
client = JenkinsClient('http://10.252.170.171:8080')
jenkins_builds = client.get_job_builds('Test-KVM01', limit=5)

if jenkins_builds:
    jenkins_latest = jenkins_builds[0]
    print(f'Jenkins 最新 Build: #{jenkins_latest[\"number\"]}')
    
    # 從資料庫獲取
    job = JenkinsJob.objects.filter(server_id=12, name='Test-KVM01').first()
    db_latest = JenkinsBuild.objects.filter(job=job).order_by('-build_number').first()
    
    if db_latest:
        print(f'資料庫最新 Build: #{db_latest.build_number}')
        print('')
        
        if jenkins_latest['number'] == db_latest.build_number:
            print('✅ 數據完全同步！')
        else:
            gap = jenkins_latest['number'] - db_latest.build_number
            print(f'⚠️  仍有差距: {gap} 個 Builds 未同步')
            print(f'   （可能需要等待下次同步任務）')
    else:
        print('❌ 資料庫無 Build 記錄')
else:
    print('❌ 無法從 Jenkins API 獲取數據')
"

echo ""
echo "=================================================="
echo "  驗證完成"
echo "=================================================="
