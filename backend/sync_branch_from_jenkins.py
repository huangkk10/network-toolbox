#!/usr/bin/env python
"""
從 Jenkins 重新獲取所有 Jobs 的最新 Build 參數，並更新 current_branch 欄位
這是一個一次性腳本，用於更新現有數據

使用方式：
    docker exec nt-django python sync_branch_from_jenkins.py
"""

import os
import sys
import django

# 設置 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.models import JenkinsServer, JenkinsJob, JenkinsBuild
from library.services.jenkins_client import JenkinsClient
import logging

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def sync_branches():
    """從 Jenkins 重新獲取所有 Jobs 的 Branch 資訊"""
    
    servers = JenkinsServer.objects.filter(is_active=True)
    
    total_jobs = 0
    updated_jobs = 0
    updated_builds = 0
    errors = 0
    
    for server in servers:
        logger.info(f'🔄 處理 Server: {server.name} ({server.url})')
        
        client = None
        try:
            client = JenkinsClient(
                base_url=server.url,
                username=server.username,
                api_token=server.api_token
            )
            
            # 獲取所有 Jobs
            jobs = JenkinsJob.objects.filter(server=server)
            logger.info(f'  📋 找到 {jobs.count()} 個 Jobs')
            
            for job in jobs:
                try:
                    total_jobs += 1
                    
                    # 從 Jenkins 獲取最新的 Builds（包含 parameters）
                    builds_data = client.get_job_builds(job.name, limit=1)
                    
                    if not builds_data:
                        continue
                    
                    latest_build_data = builds_data[0]
                    parameters = latest_build_data.get('parameters', {})
                    
                    if not parameters:
                        continue
                    
                    # 提取 branch
                    branch = (
                        parameters.get('BRANCH') or 
                        parameters.get('GIT_BRANCH') or 
                        parameters.get('branch') or 
                        parameters.get('git_branch') or
                        ''
                    )
                    
                    if branch:
                        # 更新 Job 的 current_branch
                        if job.current_branch != branch:
                            job.current_branch = branch
                            job.save(update_fields=['current_branch'])
                            updated_jobs += 1
                            logger.info(f'  ✅ {job.name}: branch = {branch}')
                        
                        # 同時更新最新 Build 的 parameters（如果之前是空的）
                        latest_build = JenkinsBuild.objects.filter(
                            job=job,
                            build_number=latest_build_data.get('number')
                        ).first()
                        
                        if latest_build and not latest_build.parameters:
                            latest_build.parameters = parameters
                            latest_build.save(update_fields=['parameters'])
                            updated_builds += 1
                    
                except Exception as e:
                    errors += 1
                    logger.error(f'  ❌ 處理 Job {job.name} 失敗: {e}')
                    continue
                    
        except Exception as e:
            errors += 1
            logger.error(f'❌ 連接 Server {server.name} 失敗: {e}')
        finally:
            if client:
                client.close()
    
    logger.info('')
    logger.info('=' * 50)
    logger.info('📊 同步完成統計:')
    logger.info(f'  - 總 Jobs: {total_jobs}')
    logger.info(f'  - 更新 Jobs (branch): {updated_jobs}')
    logger.info(f'  - 更新 Builds (parameters): {updated_builds}')
    logger.info(f'  - 錯誤: {errors}')
    logger.info('=' * 50)


if __name__ == '__main__':
    logger.info('🚀 開始從 Jenkins 同步 Branch 資訊...')
    logger.info('')
    sync_branches()
    logger.info('')
    logger.info('✅ 同步完成！')
