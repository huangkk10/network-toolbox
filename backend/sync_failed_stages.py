#!/usr/bin/env python3
"""
自動同步失敗 Build 的 Pipeline Stage 資訊

使用方式：
    docker exec nt-django python sync_failed_stages.py
    
選項：
    --limit N    限制同步的 Build 數量（預設 50）
    --job-name   只同步特定 Job 的 Build
    --dry-run    預覽模式，不實際更新資料庫
"""

import os
import sys
import django
import argparse

# 設置 Django 環境
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.models import JenkinsServer, JenkinsJob, JenkinsBuild
from library.services.jenkins_client import JenkinsClient
import logging

logger = logging.getLogger(__name__)


def sync_failed_stages(limit=50, job_name=None, dry_run=False):
    """
    同步失敗 Build 的 Pipeline Stage 資訊
    
    Args:
        limit: 限制同步的 Build 數量
        job_name: 只同步特定 Job（可選）
        dry_run: 預覽模式，不實際更新
    """
    print(f"\n{'=' * 70}")
    print(f"  自動同步失敗 Build 的 Pipeline Stage 資訊")
    print(f"  限制數量: {limit}")
    print(f"  預覽模式: {'是' if dry_run else '否'}")
    if job_name:
        print(f"  指定 Job: {job_name}")
    print('=' * 70)
    
    # 查詢需要同步的失敗 Build
    query = JenkinsBuild.objects.filter(
        result='FAILURE',
        failed_stage='',  # 還沒同步的
        is_building=False  # 不是正在執行的
    ).select_related('job', 'job__server').order_by('-build_timestamp')
    
    if job_name:
        query = query.filter(job__name=job_name)
    
    builds = query[:limit]
    total_builds = query.count()
    
    print(f"\n📊 找到 {total_builds} 個需要同步的失敗 Build")
    print(f"📋 本次將處理前 {len(builds)} 個\n")
    
    if len(builds) == 0:
        print("✅ 沒有需要同步的 Build")
        return
    
    success_count = 0
    skip_count = 0
    error_count = 0
    
    for i, build in enumerate(builds, 1):
        print(f"\n[{i}/{len(builds)}] 處理 Build #{build.build_number} ({build.job.name})")
        print(f"  Server: {build.job.server.name}")
        print(f"  Job: {build.job.name}")
        print(f"  Build: #{build.build_number}")
        print(f"  結果: {build.result}")
        
        if dry_run:
            print("  ⏭️  預覽模式，跳過同步")
            skip_count += 1
            continue
        
        client = None
        try:
            # 創建 Jenkins 客戶端
            server = build.job.server
            client = JenkinsClient(
                base_url=server.url,
                username=server.username,
                api_token=server.api_token
            )
            
            # 獲取 Pipeline Nodes
            nodes = client.get_blue_ocean_pipeline_nodes(
                build.job.name,
                build.build_number
            )
            
            if not nodes:
                print("  ⚠️  無法獲取 Pipeline Nodes（可能不是 Pipeline Job 或 Blue Ocean 未安裝）")
                skip_count += 1
                continue
            
            # 提取 Stage 資訊
            stages = [
                {
                    'id': node.get('id'),
                    'name': node.get('displayName'),
                    'result': node.get('result'),
                    'state': node.get('state'),
                    'duration_ms': node.get('durationInMillis', 0),
                    'start_time': node.get('startTime'),
                    'type': node.get('type'),
                    'error': node.get('error')
                }
                for node in nodes if node.get('type') == 'STAGE'
            ]
            
            # 找出失敗的 Stage
            failed_stages_list = client.get_failed_stages(
                build.job.name,
                build.build_number
            )
            
            failed_stage_name = failed_stages_list[0]['stage_name'] if failed_stages_list else ''
            
            # 更新資料庫
            build.pipeline_stages = stages
            build.failed_stage = failed_stage_name
            build.save(update_fields=['pipeline_stages', 'failed_stage'])
            
            print(f"  ✅ 同步成功")
            print(f"     Stage 總數: {len(stages)}")
            print(f"     失敗 Stage: {failed_stage_name or '（無）'}")
            
            success_count += 1
            
        except Exception as e:
            print(f"  ❌ 同步失敗: {e}")
            error_count += 1
            
        finally:
            if client:
                client.close()
    
    # 總結
    print(f"\n{'=' * 70}")
    print(f"  同步完成")
    print('=' * 70)
    print(f"✅ 成功: {success_count}")
    print(f"⏭️  跳過: {skip_count}")
    print(f"❌ 失敗: {error_count}")
    print(f"📊 總計: {len(builds)}")
    
    if total_builds > len(builds):
        print(f"\n💡 提示: 還有 {total_builds - len(builds)} 個 Build 尚未同步")
        print(f"   可以再次執行此腳本繼續同步")


def main():
    parser = argparse.ArgumentParser(description='自動同步失敗 Build 的 Pipeline Stage 資訊')
    parser.add_argument('--limit', type=int, default=50, help='限制同步的 Build 數量（預設 50）')
    parser.add_argument('--job-name', type=str, help='只同步特定 Job 的 Build')
    parser.add_argument('--dry-run', action='store_true', help='預覽模式，不實際更新資料庫')
    
    args = parser.parse_args()
    
    sync_failed_stages(
        limit=args.limit,
        job_name=args.job_name,
        dry_run=args.dry_run
    )


if __name__ == '__main__':
    main()
