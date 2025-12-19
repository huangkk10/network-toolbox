#!/usr/bin/env python
"""
同步 Git Branch 資訊到 JenkinsJob.current_branch

這個腳本從 Jenkins API 取得每個 Job 最新 Build 的 Git branch 資訊，
並更新到資料庫中的 current_branch 欄位。

Branch 資訊來源：Jenkins Build 的 hudson.plugins.git.util.BuildData action
"""

import os
import sys
import django

# 設置 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from api.models import JenkinsServer, JenkinsJob
from library.services.jenkins_client import JenkinsClient
import logging

# 設置 logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def sync_git_branches():
    """從 Jenkins 同步所有 Job 的 Git branch 資訊"""
    
    servers = JenkinsServer.objects.filter(is_active=True)
    
    total_jobs = 0
    updated_jobs = 0
    errors = 0
    
    for server in servers:
        logger.info(f'處理 Server: {server.name} ({server.url})')
        
        try:
            client = JenkinsClient(
                base_url=server.url,
                username=server.username,
                api_token=server.api_token
            )
            
            jobs = JenkinsJob.objects.filter(server=server)
            logger.info(f'  找到 {jobs.count()} 個 Jobs')
            
            for job in jobs:
                total_jobs += 1
                
                try:
                    # 取得最新 Build 的資訊
                    builds = client.get_job_builds(job.name, limit=1)
                    
                    if builds and len(builds) > 0:
                        build = builds[0]
                        git_branch = build.get('git_branch', '')
                        
                        if git_branch:
                            old_branch = job.current_branch
                            job.current_branch = git_branch
                            job.save(update_fields=['current_branch'])
                            
                            if old_branch != git_branch:
                                updated_jobs += 1
                                logger.info(f'    ✅ {job.name}: "{old_branch}" → "{git_branch}"')
                            else:
                                logger.debug(f'    - {job.name}: branch 未變更 ({git_branch})')
                        else:
                            logger.debug(f'    - {job.name}: 無 Git branch 資訊')
                    else:
                        logger.debug(f'    - {job.name}: 無 Build 記錄')
                        
                except Exception as e:
                    errors += 1
                    logger.error(f'    ❌ {job.name}: {e}')
            
            client.close()
            
        except Exception as e:
            errors += 1
            logger.error(f'  ❌ 連接 Server 失敗: {e}')
    
    # 輸出統計
    logger.info('=' * 50)
    logger.info('同步完成！')
    logger.info(f'  總 Jobs: {total_jobs}')
    logger.info(f'  更新: {updated_jobs}')
    logger.info(f'  錯誤: {errors}')


if __name__ == '__main__':
    sync_git_branches()
