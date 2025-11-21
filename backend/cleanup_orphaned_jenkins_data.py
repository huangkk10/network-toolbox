#!/usr/bin/env python
"""
清理 Jenkins 孤立資料

此腳本會：
1. 檢查資料庫中的 Jobs 是否仍存在於 Jenkins Server
2. 檢查資料庫中的 Builds 是否仍存在於 Jenkins Server
3. 列出所有孤立資料
4. 提供備份選項
5. 清理孤立資料（需確認）
6. 清理相關的 NAS 檔案

執行方式：
    # 乾運行（只檢查，不刪除）
    docker exec nt-django python cleanup_orphaned_jenkins_data.py --dry-run
    
    # 針對特定 Server
    docker exec nt-django python cleanup_orphaned_jenkins_data.py --server-id 1 --dry-run
    
    # 執行清理（會要求確認）
    docker exec nt-django python cleanup_orphaned_jenkins_data.py
    
    # 執行清理並備份
    docker exec nt-django python cleanup_orphaned_jenkins_data.py --backup
    
    # 靜默模式（不要求確認，危險！）
    docker exec nt-django python cleanup_orphaned_jenkins_data.py --yes
"""

import os
import sys
import django
import argparse
import logging
import json
from datetime import datetime
from django.db import transaction

# 設定 Django 環境
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.models import JenkinsServer, JenkinsJob, JenkinsBuild
from library.services.jenkins_client import JenkinsClient

# 日誌設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class JenkinsDataCleaner:
    """Jenkins 資料清理器"""
    
    def __init__(self, dry_run=True, backup=False, server_id=None):
        self.dry_run = dry_run
        self.backup = backup
        self.server_id = server_id
        
        # 統計
        self.stats = {
            'total_jobs': 0,
            'total_builds': 0,
            'orphaned_jobs': [],
            'orphaned_builds': [],
            'deleted_jobs': 0,
            'deleted_builds': 0,
            'freed_space': 0,
        }
    
    def find_orphaned_jobs(self):
        """查找孤立的 Jobs"""
        logger.info("\n" + "="*60)
        logger.info("🔍 階段 1：檢查孤立的 Jenkins Jobs")
        logger.info("="*60)
        
        # 獲取要檢查的 Servers
        if self.server_id:
            servers = JenkinsServer.objects.filter(id=self.server_id, is_active=True)
        else:
            servers = JenkinsServer.objects.filter(is_active=True)
        
        logger.info(f"📡 檢查 {servers.count()} 個 Jenkins Server")
        
        for server in servers:
            logger.info(f"\n🖥️  Server: {server.name} ({server.url})")
            
            try:
                # 連接 Jenkins
                client = JenkinsClient(
                    base_url=server.url,
                    username=server.username,
                    api_token=server.api_token
                )
                
                # 獲取 Jenkins 上所有 Job 名稱
                jenkins_jobs = client.get_all_jobs()
                jenkins_job_names = {job['name'] for job in jenkins_jobs}
                logger.info(f"  Jenkins 上有 {len(jenkins_job_names)} 個 Jobs")
                
                # 獲取資料庫中此 Server 的所有 Jobs
                db_jobs = JenkinsJob.objects.filter(server=server)
                self.stats['total_jobs'] += db_jobs.count()
                logger.info(f"  資料庫中有 {db_jobs.count()} 個 Jobs")
                
                # 比對找出孤立的 Jobs
                orphaned_count = 0
                for job in db_jobs:
                    if job.name not in jenkins_job_names:
                        orphaned_count += 1
                        build_count = job.builds.count()
                        self.stats['orphaned_jobs'].append({
                            'server': server.name,
                            'job_id': job.id,
                            'job_name': job.name,
                            'build_count': build_count,
                            'last_sync': job.last_sync_at,
                        })
                        logger.warning(f"  ❌ 孤立 Job: {job.name} (含 {build_count} 個 Builds)")
                
                if orphaned_count == 0:
                    logger.info("  ✅ 無孤立 Jobs")
                else:
                    logger.warning(f"  ⚠️  找到 {orphaned_count} 個孤立 Jobs")
                
                client.close()
                
            except Exception as e:
                logger.error(f"  ❌ 檢查失敗: {e}")
    
    def find_orphaned_builds(self):
        """查找孤立的 Builds"""
        logger.info("\n" + "="*60)
        logger.info("🔍 階段 2：檢查孤立的 Jenkins Builds")
        logger.info("="*60)
        
        # 獲取要檢查的 Servers
        if self.server_id:
            servers = JenkinsServer.objects.filter(id=self.server_id, is_active=True)
        else:
            servers = JenkinsServer.objects.filter(is_active=True)
        
        for server in servers:
            logger.info(f"\n🖥️  Server: {server.name}")
            
            try:
                client = JenkinsClient(
                    base_url=server.url,
                    username=server.username,
                    api_token=server.api_token
                )
                
                # 獲取此 Server 的所有 Jobs（排除孤立的）
                jobs = JenkinsJob.objects.filter(server=server)
                orphaned_job_ids = [j['job_id'] for j in self.stats['orphaned_jobs']]
                jobs = jobs.exclude(id__in=orphaned_job_ids)
                
                logger.info(f"  檢查 {jobs.count()} 個 Jobs 的 Builds")
                
                for job in jobs:
                    try:
                        # 從 Jenkins API 獲取所有 Build 編號
                        jenkins_builds = client.get_job_builds(job.name, limit=100)  # 獲取最近 100 個
                        if not jenkins_builds:
                            # 如果無法獲取 Builds，跳過此 Job（可能 Job 存在但沒有 Build）
                            continue
                        
                        jenkins_build_numbers = {b.get('number') for b in jenkins_builds if b.get('number')}
                        
                        # 獲取資料庫中的所有 Builds
                        db_builds = JenkinsBuild.objects.filter(job=job)
                        self.stats['total_builds'] += db_builds.count()
                        
                        # 比對找出孤立的 Builds（存在於資料庫但不在 Jenkins）
                        for build in db_builds:
                            if build.build_number not in jenkins_build_numbers:
                                self.stats['orphaned_builds'].append({
                                    'server': server.name,
                                    'job_name': job.name,
                                    'build_id': build.id,
                                    'build_number': build.build_number,
                                    'result': build.result,
                                    'workspace_size': build.workspace_size,
                                })
                                logger.debug(f"    ❌ 孤立 Build: {job.name} #{build.build_number}")
                    
                    except Exception as e:
                        logger.error(f"    ❌ 檢查 Job {job.name} 失敗: {e}")
                
                client.close()
                
            except Exception as e:
                logger.error(f"  ❌ 檢查失敗: {e}")
    
    def backup_data(self):
        """備份要刪除的資料"""
        if not self.backup:
            return
        
        logger.info("\n" + "="*60)
        logger.info("💾 階段 3：備份資料")
        logger.info("="*60)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f"/app/logs/jenkins_cleanup_backup_{timestamp}.json"
        
        backup_data = {
            'timestamp': timestamp,
            'dry_run': self.dry_run,
            'server_id': self.server_id,
            'stats': self.stats,
        }
        
        try:
            with open(backup_file, 'w') as f:
                json.dump(backup_data, f, indent=2, default=str)
            logger.info(f"✅ 備份已儲存: {backup_file}")
        except Exception as e:
            logger.error(f"❌ 備份失敗: {e}")
    
    def cleanup_orphaned_data(self, confirmed=False):
        """清理孤立資料"""
        logger.info("\n" + "="*60)
        logger.info("🗑️  階段 4：清理孤立資料")
        logger.info("="*60)
        
        # 統計資訊
        orphaned_jobs_count = len(self.stats['orphaned_jobs'])
        orphaned_builds_count = len(self.stats['orphaned_builds'])
        
        logger.info(f"\n📊 發現孤立資料：")
        logger.info(f"  - 孤立 Jobs: {orphaned_jobs_count}")
        logger.info(f"  - 孤立 Builds: {orphaned_builds_count}")
        
        if orphaned_jobs_count == 0 and orphaned_builds_count == 0:
            logger.info("\n✅ 沒有孤立資料需要清理")
            return
        
        if self.dry_run:
            logger.info("\n⚠️  乾運行模式：不會實際刪除資料")
            self._print_cleanup_summary()
            return
        
        # 確認
        if not confirmed:
            logger.info("\n⚠️  即將刪除以上孤立資料")
            response = input("確認執行清理？ (yes/no): ").strip().lower()
            if response != 'yes':
                logger.info("❌ 已取消清理操作")
                return
        
        # 執行刪除
        with transaction.atomic():
            # 刪除孤立的 Builds
            if orphaned_builds_count > 0:
                logger.info(f"\n🗑️  刪除 {orphaned_builds_count} 個孤立 Builds...")
                build_ids = [b['build_id'] for b in self.stats['orphaned_builds']]
                deleted_builds = JenkinsBuild.objects.filter(id__in=build_ids).delete()
                self.stats['deleted_builds'] = deleted_builds[0]
                logger.info(f"✅ 已刪除 {deleted_builds[0]} 個 Builds")
            
            # 刪除孤立的 Jobs（會級聯刪除相關 Builds）
            if orphaned_jobs_count > 0:
                logger.info(f"\n🗑️  刪除 {orphaned_jobs_count} 個孤立 Jobs...")
                job_ids = [j['job_id'] for j in self.stats['orphaned_jobs']]
                deleted_jobs = JenkinsJob.objects.filter(id__in=job_ids).delete()
                self.stats['deleted_jobs'] = deleted_jobs[0]
                logger.info(f"✅ 已刪除 {deleted_jobs[0]} 個 Jobs")
        
        logger.info("\n✅ 清理完成！")
    
    def _print_cleanup_summary(self):
        """打印清理摘要"""
        logger.info("\n" + "="*60)
        logger.info("📋 清理摘要")
        logger.info("="*60)
        
        if self.stats['orphaned_jobs']:
            logger.info("\n將刪除的 Jobs：")
            for job in self.stats['orphaned_jobs']:
                logger.info(f"  - {job['server']}: {job['job_name']} ({job['build_count']} builds)")
        
        if self.stats['orphaned_builds']:
            logger.info(f"\n將刪除的 Builds：共 {len(self.stats['orphaned_builds'])} 個")
            # 按 Job 分組顯示
            from collections import defaultdict
            builds_by_job = defaultdict(list)
            for build in self.stats['orphaned_builds']:
                builds_by_job[build['job_name']].append(build['build_number'])
            
            for job_name, build_numbers in builds_by_job.items():
                logger.info(f"  - {job_name}: Builds #{', #'.join(map(str, sorted(build_numbers)))}")
    
    def run(self, confirmed=False):
        """執行完整流程"""
        logger.info("\n" + "="*60)
        logger.info("🚀 Jenkins 資料清理工具")
        logger.info("="*60)
        logger.info(f"模式: {'乾運行 (DRY-RUN)' if self.dry_run else '實際執行'}")
        logger.info(f"備份: {'是' if self.backup else '否'}")
        if self.server_id:
            logger.info(f"目標 Server ID: {self.server_id}")
        
        # 執行流程
        self.find_orphaned_jobs()
        self.find_orphaned_builds()
        self.backup_data()
        self.cleanup_orphaned_data(confirmed=confirmed)
        
        # 最終統計
        logger.info("\n" + "="*60)
        logger.info("📊 最終統計")
        logger.info("="*60)
        logger.info(f"  總 Jobs: {self.stats['total_jobs']}")
        logger.info(f"  總 Builds: {self.stats['total_builds']}")
        logger.info(f"  孤立 Jobs: {len(self.stats['orphaned_jobs'])}")
        logger.info(f"  孤立 Builds: {len(self.stats['orphaned_builds'])}")
        if not self.dry_run:
            logger.info(f"  已刪除 Jobs: {self.stats['deleted_jobs']}")
            logger.info(f"  已刪除 Builds: {self.stats['deleted_builds']}")


def main():
    parser = argparse.ArgumentParser(description='清理 Jenkins 孤立資料')
    parser.add_argument('--dry-run', action='store_true', help='乾運行（只檢查，不刪除）')
    parser.add_argument('--backup', action='store_true', help='備份要刪除的資料')
    parser.add_argument('--server-id', type=int, help='只處理特定的 Server ID')
    parser.add_argument('--yes', action='store_true', help='自動確認（不要求互動）')
    
    args = parser.parse_args()
    
    cleaner = JenkinsDataCleaner(
        dry_run=args.dry_run,
        backup=args.backup,
        server_id=args.server_id
    )
    
    try:
        cleaner.run(confirmed=args.yes)
    except KeyboardInterrupt:
        logger.info("\n❌ 已中斷操作")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
