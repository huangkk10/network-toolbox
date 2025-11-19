#!/usr/bin/env python
"""
強制重新同步特定 Jenkins Build 的狀態

用途：當發現某個 Build 的狀態不正確時，使用此腳本強制從 Jenkins 重新獲取並更新

使用方法：
    python force_resync_build.py --job SAF7522_K07 --build 35
    python force_resync_build.py --job SAF7522_K07 --build 35 --dry-run
"""

import os
import sys
import django
import argparse
import logging

# 設定 Django 環境
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.models import JenkinsServer, JenkinsJob, JenkinsBuild
from library.services.jenkins_client import JenkinsClient
from datetime import datetime
import pytz

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def resync_build(job_name, build_number, dry_run=False):
    """
    重新同步特定 Build 的狀態
    
    Args:
        job_name: Jenkins Job 名稱
        build_number: Build 編號
        dry_run: 只檢查，不實際更新
    
    Returns:
        bool: 是否成功
    """
    try:
        logger.info(f'🔍 查找 Jenkins Job: {job_name}')
        
        # 查找 Job
        try:
            job = JenkinsJob.objects.get(name=job_name)
            logger.info(f'✅ 找到 Job: {job.name} (Server: {job.server.name})')
        except JenkinsJob.DoesNotExist:
            logger.error(f'❌ Job 不存在: {job_name}')
            return False
        
        # 查找 Build
        try:
            build = JenkinsBuild.objects.get(job=job, build_number=build_number)
            logger.info(f'✅ 找到 Build #{build_number}')
            logger.info(f'   - 當前狀態: {build.result}')
            logger.info(f'   - 正在構建: {build.is_building}')
            logger.info(f'   - 持續時間: {build.duration}ms')
            logger.info(f'   - 失敗 Stage: {build.failed_stage or "N/A"}')
        except JenkinsBuild.DoesNotExist:
            logger.error(f'❌ Build 不存在: #{build_number}')
            return False
        
        # 連接 Jenkins
        logger.info(f'🔌 連接 Jenkins Server: {job.server.url}')
        client = JenkinsClient(
            base_url=job.server.url,
            username=job.server.username,
            api_token=job.server.api_token
        )
        
        # 從 Jenkins API 獲取 Build 資訊
        logger.info(f'📡 從 Jenkins 獲取 Build #{build_number} 的最新狀態...')
        jenkins_builds = client.get_job_builds(job.name, limit=50)
        
        if not jenkins_builds:
            logger.error('❌ 無法從 Jenkins 獲取 Build 資訊')
            client.close()
            return False
        
        # 找到對應的 Build
        jenkins_build = None
        for b in jenkins_builds:
            if b.get('number') == build_number:
                jenkins_build = b
                break
        
        if not jenkins_build:
            logger.error(f'❌ Jenkins API 中找不到 Build #{build_number}')
            client.close()
            return False
        
        # 顯示 Jenkins 上的狀態
        jenkins_result = jenkins_build.get('result')
        jenkins_building = jenkins_build.get('building', False)
        jenkins_duration = jenkins_build.get('duration', 0)
        
        logger.info(f'📊 Jenkins 上的狀態:')
        logger.info(f'   - 結果: {jenkins_result}')
        logger.info(f'   - 正在構建: {jenkins_building}')
        logger.info(f'   - 持續時間: {jenkins_duration}ms')
        
        # 比較差異
        changes = []
        updated_fields = []
        
        if jenkins_result != build.result:
            changes.append(f'   - result: {build.result} → {jenkins_result}')
            build.result = jenkins_result
            updated_fields.append('result')
        
        if jenkins_building != build.is_building:
            changes.append(f'   - is_building: {build.is_building} → {jenkins_building}')
            build.is_building = jenkins_building
            updated_fields.append('is_building')
        
        if jenkins_duration != build.duration:
            changes.append(f'   - duration: {build.duration}ms → {jenkins_duration}ms')
            build.duration = jenkins_duration
            updated_fields.append('duration')
        
        # 如果狀態變為 FAILURE，獲取失敗 Stage
        if jenkins_result == 'FAILURE' and not build.failed_stage:
            logger.info('🎯 嘗試獲取失敗 Stage...')
            try:
                failed_stages = client.get_failed_stages(job.name, build_number)
                if failed_stages:
                    build.pipeline_stages = failed_stages
                    first_failed = failed_stages[0]
                    failed_stage_name = (
                        first_failed.get('stage_name') or 
                        first_failed.get('displayName') or 
                        first_failed.get('name')
                    )
                    build.failed_stage = failed_stage_name
                    updated_fields.extend(['pipeline_stages', 'failed_stage'])
                    changes.append(f'   - failed_stage: None → {failed_stage_name}')
                    logger.info(f'✅ 找到失敗 Stage: {failed_stage_name}')
            except Exception as e:
                logger.warning(f'⚠️  無法獲取失敗 Stage: {e}')
        
        # 顯示變更
        if changes:
            logger.info('🔄 需要更新以下欄位:')
            for change in changes:
                logger.info(change)
        else:
            logger.info('✅ 狀態一致，無需更新')
            client.close()
            return True
        
        # 執行更新
        if not dry_run:
            logger.info('💾 正在更新資料庫...')
            build.save(update_fields=updated_fields)
            logger.info(f'✅ 成功更新 Build #{build_number}')
            
            # 更新 Job 的最後 Build 資訊
            if build.build_number >= (job.last_build_number or 0):
                job.last_build_status = build.result
                job.save(update_fields=['last_build_status'])
                logger.info(f'✅ 已更新 Job 的最後 Build 狀態: {build.result}')
        else:
            logger.info('🔍 DRY RUN 模式：不實際更新資料庫')
        
        client.close()
        return True
        
    except Exception as e:
        logger.error(f'❌ 執行失敗: {e}', exc_info=True)
        return False


def main():
    parser = argparse.ArgumentParser(description='強制重新同步 Jenkins Build 狀態')
    parser.add_argument('--job', required=True, help='Jenkins Job 名稱')
    parser.add_argument('--build', type=int, required=True, help='Build 編號')
    parser.add_argument('--dry-run', action='store_true', help='只檢查，不實際更新')
    
    args = parser.parse_args()
    
    logger.info('=' * 60)
    logger.info('🔄 Jenkins Build 強制重新同步工具')
    logger.info('=' * 60)
    logger.info(f'Job: {args.job}')
    logger.info(f'Build: #{args.build}')
    logger.info(f'模式: {"DRY RUN（檢查模式）" if args.dry_run else "UPDATE（更新模式）"}')
    logger.info('=' * 60)
    
    success = resync_build(args.job, args.build, args.dry_run)
    
    logger.info('=' * 60)
    if success:
        logger.info('✅ 執行成功')
        sys.exit(0)
    else:
        logger.error('❌ 執行失敗')
        sys.exit(1)


if __name__ == '__main__':
    main()
