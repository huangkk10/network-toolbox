#!/usr/bin/env python
"""
創建 Jenkins/RVT 測試數據

使用方式：
    docker exec nt-django python create_jenkins_test_data.py
"""

import os
import sys
import django
from datetime import datetime, timedelta
import random

# 設置 Django 環境
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.models import JenkinsServer, JenkinsJob, JenkinsBuild
from django.utils import timezone

def create_test_data():
    """創建測試數據"""
    
    print("=" * 60)
    print("🚀 開始創建 Jenkins/RVT 測試數據...")
    print("=" * 60)
    
    # 清空現有數據（可選）
    print("\n📝 清空現有數據...")
    JenkinsBuild.objects.all().delete()
    JenkinsJob.objects.all().delete()
    JenkinsServer.objects.all().delete()
    print("✅ 清空完成")
    
    # ========== 創建 Jenkins Server ==========
    print("\n📊 創建 Jenkins Server...")
    
    servers = [
        {
            'name': 'RVT Production Server',
            'url': 'http://10.252.170.188:8080',
            'username': 'admin',
            'api_token': 'test_token_123',
            'description': 'RVT 生產環境 Jenkins 伺服器',
            'status': 'online',
        },
        {
            'name': 'RVT Development Server',
            'url': 'http://jenkins-dev.example.com:8080',
            'username': 'dev_admin',
            'api_token': 'dev_token_456',
            'description': 'RVT 開發環境 Jenkins 伺服器',
            'status': 'online',
        },
    ]
    
    created_servers = []
    for server_data in servers:
        server = JenkinsServer.objects.create(**server_data)
        created_servers.append(server)
        print(f"  ✅ 創建 Server: {server.name}")
    
    # ========== 創建 Jenkins Jobs ==========
    print("\n📦 創建 Jenkins Jobs...")
    
    job_templates = [
        'RVT-Deploy-Production',
        'RVT-Build-Backend',
        'RVT-Build-Frontend',
        'RVT-Test-Integration',
        'RVT-Test-Unit',
        'RVT-Deploy-Staging',
        'RVT-Database-Migration',
        'RVT-Deploy-Rollback',
    ]
    
    created_jobs = []
    for i, server in enumerate(created_servers):
        # 每個 Server 創建 4-6 個 Jobs
        num_jobs = random.randint(4, 6)
        selected_jobs = random.sample(job_templates, num_jobs)
        
        for job_name in selected_jobs:
            job = JenkinsJob.objects.create(
                server=server,
                name=job_name,
                full_name=job_name,
                url=f"{server.url}/job/{job_name}/",
                is_disabled=False,
                is_buildable=True,
                last_build_number=0,
                last_build_status='SUCCESS',
                last_build_time=timezone.now() - timedelta(hours=random.randint(1, 24)),
                total_builds=0,
                success_rate=0.0,
                description=f'RVT {job_name.split("-")[1]} 相關任務'
            )
            created_jobs.append(job)
            print(f"  ✅ 創建 Job: {job.name} (Server: {server.name})")
    
    # ========== 創建 Jenkins Builds ==========
    print("\n🔨 創建 Jenkins Builds...")
    
    build_statuses = ['SUCCESS', 'FAILURE', 'UNSTABLE', 'ABORTED']
    build_status_weights = [70, 15, 10, 5]  # SUCCESS 佔 70%
    
    total_builds = 0
    for job in created_jobs:
        # 每個 Job 創建 10-20 個 Builds
        num_builds = random.randint(10, 20)
        
        for build_num in range(1, num_builds + 1):
            # 隨機時間（最近 30 天內）
            days_ago = random.randint(0, 30)
            hours_ago = random.randint(0, 23)
            minutes_ago = random.randint(0, 59)
            
            build_time = timezone.now() - timedelta(
                days=days_ago,
                hours=hours_ago,
                minutes=minutes_ago
            )
            
            # 隨機狀態（加權）
            result = random.choices(build_statuses, weights=build_status_weights)[0]
            
            # 隨機執行時間（60-600 秒）
            duration = random.randint(60, 600)
            
            # 隨機參數
            parameters = {
                'BRANCH': random.choice(['main', 'develop', 'feature/new-feature']),
                'ENVIRONMENT': random.choice(['production', 'staging', 'development']),
                'BUILD_TYPE': random.choice(['full', 'incremental']),
            }
            
            # 隨機 Ansible Config
            ansible_config = {
                'playbook': f'{job.name.lower()}.yml',
                'inventory': random.choice(['production', 'staging', 'development']),
                'extra_vars': {
                    'app_version': f'v{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 9)}',
                    'deploy_user': 'jenkins',
                }
            }
            
            build = JenkinsBuild.objects.create(
                job=job,
                build_number=build_num,
                display_name=f'#{build_num}',
                url=f"{job.url}{build_num}/",
                result=result,
                is_building=False,
                build_timestamp=build_time,
                duration=duration,
                parameters=parameters,
                ansible_config=ansible_config,
                environment_vars={'JAVA_HOME': '/usr/lib/jvm/java-11', 'BUILD_ID': str(build_num)},
                log_file_path=f'/logs/{job.name}/build-{build_num}.log',
                config_file_path=f'/configs/{job.name}/config-{build_num}.yml',
            )
            total_builds += 1
        
        print(f"  ✅ 創建 {num_builds} 個 Builds for Job: {job.name}")
    
    # ========== 統計總結 ==========
    print("\n" + "=" * 60)
    print("✅ 測試數據創建完成！")
    print("=" * 60)
    print(f"\n📊 創建統計：")
    print(f"  - Jenkins Servers: {len(created_servers)}")
    print(f"  - Jenkins Jobs: {len(created_jobs)}")
    print(f"  - Jenkins Builds: {total_builds}")
    
    # 計算成功率
    success_builds = JenkinsBuild.objects.filter(result='SUCCESS').count()
    success_rate = (success_builds / total_builds * 100) if total_builds > 0 else 0
    print(f"\n📈 統計資訊：")
    print(f"  - 成功率: {success_rate:.1f}%")
    print(f"  - 成功 Builds: {success_builds}")
    print(f"  - 失敗 Builds: {JenkinsBuild.objects.filter(result='FAILURE').count()}")
    print(f"  - 不穩定 Builds: {JenkinsBuild.objects.filter(result='UNSTABLE').count()}")
    
    # 今日 Builds
    today = timezone.now().date()
    today_builds = JenkinsBuild.objects.filter(
        build_timestamp__date=today
    ).count()
    print(f"  - 今日 Builds: {today_builds}")
    
    print("\n🎉 現在可以訪問 http://localhost/rvt-analytics 查看數據！")
    print("=" * 60)

if __name__ == '__main__':
    try:
        create_test_data()
    except Exception as e:
        print(f"\n❌ 錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
