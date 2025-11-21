# Jenkins 資料清理計畫

## 📋 問題描述

根據前端顯示，**Jenkins 詳細頁面列出的 Jobs 和 Builds 與實際 Jenkins Server 上的資料不同步**：

- ❌ **孤立的 Builds**：某些 Build 已經在 Jenkins 上被刪除，但資料庫中仍保留記錄
- ❌ **孤立的 Jobs**：某些 Job 已經在 Jenkins 上被刪除或重命名，但資料庫中仍保留記錄
- ❌ **過時資料**：Web UI 顯示的資料不準確，影響使用者決策

### 影響範圍

- **使用者體驗**：使用者看到的 Jenkins 資料不準確
- **儲存空間**：資料庫和 NAS 儲存了不存在的 Builds 相關檔案
- **效能影響**：查詢包含大量無效資料，影響查詢效率
- **統計錯誤**：基於歷史資料的統計分析不準確

---

## 🔍 問題根源分析

### 1. 現有同步機制的限制

#### 當前實作（`backend/api/tasks.py`）

```python
@shared_task(name='api.tasks.sync_jenkins_builds')
def sync_jenkins_builds(self, server_id=None, max_builds_per_job=20, max_age_days=3):
    """
    同步 Jenkins Builds 到資料庫
    
    特點：
    - ✅ 會創建新的 Builds
    - ✅ 會更新現有 Builds 的狀態（result, is_building, duration）
    - ❌ 不會刪除已不存在的 Builds
    - ❌ 只同步最近 N 個 Builds（max_builds_per_job=20）
    """
```

#### 同步機制流程

```
┌─────────────────────────────────────────┐
│  sync_jenkins_builds (Celery Task)     │
│  每 10 分鐘執行一次                      │
└─────────────────┬───────────────────────┘
                  │
                  ▼
    ┌─────────────────────────────┐
    │ 從 Jenkins API 獲取 Jobs     │
    │ - 只獲取資料庫中已存在的 Jobs │
    └─────────────┬───────────────┘
                  │
                  ▼
    ┌─────────────────────────────────────────┐
    │ 對每個 Job 獲取最新的 Builds            │
    │ - max_builds_per_job = 20（預設）        │
    │ - max_age_days = 3（預設）               │
    └─────────────┬───────────────────────────┘
                  │
                  ▼
    ┌──────────────────────────────────────────┐
    │ 處理 Builds                               │
    │ - ✅ 創建新 Builds                        │
    │ - ✅ 更新現有 Builds 狀態                 │
    │ - ❌ 不檢查是否有 Builds 被刪除            │
    └──────────────────────────────────────────┘
```

### 2. 為什麼會產生孤立資料？

#### 情境 A：Job 被刪除
```
Jenkins Server 操作：刪除 Job "SAF3204_KVM05"
結果：
- Jenkins API 不再返回此 Job
- sync_jenkins_builds 不處理資料庫中的此 Job
- JenkinsJob 記錄保留（孤立）
- 所有相關的 JenkinsBuild 記錄保留（孤立）
```

#### 情境 B：Build 被刪除
```
Jenkins Server 操作：刪除 Build #35-#50（保留 #51-#70）
結果：
- Jenkins API 返回 Job，但只包含最新 20 個 Builds (#51-#70)
- sync_jenkins_builds 更新這 20 個 Builds
- 資料庫中 Build #35-#50 的記錄保留（孤立）
```

#### 情境 C：Job 重命名
```
Jenkins Server 操作：重命名 "SAF3204_KVM05" → "SAF3204_KVM05_v2"
結果：
- Jenkins API 返回新名稱 "SAF3204_KVM05_v2"
- sync_all_jenkins_jobs_task 創建新的 Job 記錄
- 舊的 "SAF3204_KVM05" Job 記錄保留（孤立）
- 所有舊 Build 記錄保留（孤立）
```

### 3. 缺少清理機制

目前系統中：
- ❌ **沒有定期驗證機制**：不檢查資料庫中的 Jobs 是否仍存在於 Jenkins
- ❌ **沒有自動清理機制**：不刪除孤立的 Jobs 和 Builds
- ❌ **沒有垃圾回收機制**：不清理相關的 NAS 檔案（Workspace, Logs, Artifacts）

---

## 💡 解決方案設計

### 總體策略

```
階段 1: 驗證 (Validation)
    ├─ 檢查 Jobs 是否存在於 Jenkins
    ├─ 檢查 Builds 是否存在於 Jenkins
    └─ 識別孤立資料

階段 2: 清理 (Cleanup)
    ├─ 安全備份
    ├─ 刪除孤立的 Builds
    ├─ 刪除孤立的 Jobs
    └─ 清理相關檔案

階段 3: 預防 (Prevention)
    ├─ 定期驗證任務
    ├─ 定期清理任務
    └─ 監控告警
```

---

## 🛠️ 方案 1：手動清理腳本（立即執行）

### 目的
提供一個安全的、可控的腳本來立即清理現有的孤立資料。

### 腳本設計：`backend/cleanup_orphaned_jenkins_data.py`

```python
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
            servers = JenkinsServer.objects.filter(id=self.server_id, is_online=True)
        else:
            servers = JenkinsServer.objects.filter(is_online=True)
        
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
            servers = JenkinsServer.objects.filter(id=self.server_id, is_online=True)
        else:
            servers = JenkinsServer.objects.filter(is_online=True)
        
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
                        # 從 Jenkins 獲取所有 Build 編號
                        job_info = client.get_job_info(job.name)
                        if not job_info:
                            continue
                        
                        jenkins_build_numbers = set()
                        for build in job_info.get('builds', []):
                            jenkins_build_numbers.add(build['number'])
                        
                        # 獲取資料庫中的所有 Builds
                        db_builds = JenkinsBuild.objects.filter(job=job)
                        self.stats['total_builds'] += db_builds.count()
                        
                        # 比對找出孤立的 Builds
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
```

### 使用範例

```bash
# 1. 先乾運行，檢查有哪些孤立資料
docker exec nt-django python cleanup_orphaned_jenkins_data.py --dry-run

# 2. 查看詳細輸出（含備份）
docker exec nt-django python cleanup_orphaned_jenkins_data.py --dry-run --backup

# 3. 針對特定 Server
docker exec nt-django python cleanup_orphaned_jenkins_data.py --server-id 1 --dry-run

# 4. 執行實際清理（會要求確認）
docker exec nt-django python cleanup_orphaned_jenkins_data.py --backup

# 5. 靜默執行（危險！不建議）
docker exec nt-django python cleanup_orphaned_jenkins_data.py --yes --backup
```

---

## 🛠️ 方案 2：定期驗證任務（預防機制）

### 目的
定期檢查資料一致性，防止孤立資料累積。

### Celery 定期任務設計

#### 文件：`backend/api/tasks.py`

```python
@shared_task(
    bind=True,
    name='api.tasks.validate_jenkins_data',
    max_retries=2,
    default_retry_delay=300,
    time_limit=1800,  # 30 分鐘
    soft_time_limit=1650
)
def validate_jenkins_data(self, server_id=None, auto_cleanup=False):
    """
    驗證 Jenkins 資料一致性
    
    定期執行此任務可以：
    1. 檢查資料庫中的 Jobs 是否仍存在於 Jenkins
    2. 檢查最近同步的 Builds 是否仍存在
    3. 記錄異常情況到日誌
    4. 可選：自動清理孤立資料
    
    Args:
        server_id: Jenkins Server ID（可選）
        auto_cleanup: 是否自動清理（預設 False）
    
    Returns:
        dict: 驗證結果統計
    """
    start_time = timezone.now()
    logger = logging.getLogger(__name__)
    
    logger.info('[Celery] 🔍 開始驗證 Jenkins 資料一致性')
    
    stats = {
        'total_jobs_checked': 0,
        'total_builds_checked': 0,
        'orphaned_jobs_found': 0,
        'orphaned_builds_found': 0,
        'cleaned_jobs': 0,
        'cleaned_builds': 0,
    }
    
    # 獲取要檢查的 Servers
    if server_id:
        servers = JenkinsServer.objects.filter(id=server_id, is_online=True)
    else:
        servers = JenkinsServer.objects.filter(is_online=True)
    
    for server in servers:
        logger.info(f'[Celery] 📡 檢查 Server: {server.name}')
        
        try:
            client = JenkinsClient(
                base_url=server.url,
                username=server.username,
                api_token=server.api_token
            )
            
            # 獲取 Jenkins 上所有 Jobs
            jenkins_jobs = client.get_all_jobs()
            jenkins_job_names = {job['name'] for job in jenkins_jobs}
            
            # 檢查資料庫中的 Jobs
            db_jobs = JenkinsJob.objects.filter(server=server)
            orphaned_jobs = []
            
            for job in db_jobs:
                stats['total_jobs_checked'] += 1
                
                if job.name not in jenkins_job_names:
                    stats['orphaned_jobs_found'] += 1
                    orphaned_jobs.append(job)
                    logger.warning(f'[Celery]   ⚠️  孤立 Job: {job.name}')
            
            # 自動清理（如果啟用）
            if auto_cleanup and orphaned_jobs:
                with transaction.atomic():
                    for job in orphaned_jobs:
                        build_count = job.builds.count()
                        job.delete()
                        stats['cleaned_jobs'] += 1
                        stats['cleaned_builds'] += build_count
                        logger.info(f'[Celery]   🗑️  已刪除孤立 Job: {job.name} (含 {build_count} builds)')
            
            client.close()
            
        except Exception as e:
            logger.error(f'[Celery] ❌ 檢查 Server {server.name} 失敗: {e}')
    
    duration = (timezone.now() - start_time).total_seconds()
    
    logger.info('[Celery] ✅ 驗證完成')
    logger.info(f'[Celery]   - 檢查 Jobs: {stats["total_jobs_checked"]}')
    logger.info(f'[Celery]   - 孤立 Jobs: {stats["orphaned_jobs_found"]}')
    if auto_cleanup:
        logger.info(f'[Celery]   - 已清理 Jobs: {stats["cleaned_jobs"]}')
        logger.info(f'[Celery]   - 已清理 Builds: {stats["cleaned_builds"]}')
    logger.info(f'[Celery]   - 耗時: {duration:.2f} 秒')
    
    return stats
```

#### 註冊定期任務

在 `backend/network_toolbox/celery.py` 或 `backend/api/tasks.py` 中添加：

```python
# Celery Beat 排程配置
app.conf.beat_schedule = {
    # ... 現有任務 ...
    
    # 每天凌晨 3 點驗證 Jenkins 資料一致性（只檢查不刪除）
    'validate-jenkins-data-daily': {
        'task': 'api.tasks.validate_jenkins_data',
        'schedule': crontab(hour=3, minute=0),
        'kwargs': {
            'auto_cleanup': False,  # 只驗證，不自動刪除
        },
    },
    
    # 每週日凌晨 4 點自動清理孤立資料
    'cleanup-orphaned-jenkins-data-weekly': {
        'task': 'api.tasks.validate_jenkins_data',
        'schedule': crontab(hour=4, minute=0, day_of_week=0),  # 每週日
        'kwargs': {
            'auto_cleanup': True,  # 自動清理
        },
    },
}
```

---

## 🛠️ 方案 3：改進同步機制（長期方案）

### 目的
從根本上改進同步邏輯，在同步過程中即時檢測孤立資料。

### 改進 `sync_all_jenkins_jobs_task`

在同步 Jobs 時，標記或刪除不存在的 Jobs：

```python
@shared_task(name='api.tasks.sync_all_jenkins_jobs_task')
def sync_all_jenkins_jobs_task(self, server_id=None, cleanup_orphaned=True):
    """
    同步所有 Jenkins Jobs
    
    新增功能：
    - cleanup_orphaned: 是否清理孤立的 Jobs（預設 True）
    """
    # ... 現有邏輯 ...
    
    if cleanup_orphaned:
        # 比對 Jenkins API 返回的 Job 名稱
        jenkins_job_names = {job['name'] for job in jenkins_jobs}
        
        # 找出資料庫中多餘的 Jobs
        db_jobs = JenkinsJob.objects.filter(server=server)
        orphaned_jobs = db_jobs.exclude(name__in=jenkins_job_names)
        
        if orphaned_jobs.exists():
            orphaned_count = orphaned_jobs.count()
            logger.warning(f'[Celery] ⚠️  發現 {orphaned_count} 個孤立 Jobs，準備刪除')
            
            with transaction.atomic():
                orphaned_jobs.delete()
            
            logger.info(f'[Celery] 🗑️  已刪除 {orphaned_count} 個孤立 Jobs')
```

---

## 📊 方案比較

| 方案 | 優點 | 缺點 | 適用場景 |
|------|------|------|----------|
| **手動清理腳本** | • 完全可控<br>• 安全（乾運行）<br>• 詳細報告 | • 需要手動執行<br>• 不能預防未來問題 | • 立即清理現有問題<br>• 一次性大規模清理 |
| **定期驗證任務** | • 自動化<br>• 可設定清理策略<br>• 持續監控 | • 有延遲（按排程執行）<br>• 需要監控日誌 | • 預防機制<br>• 定期維護 |
| **改進同步機制** | • 即時處理<br>• 無需額外任務<br>• 從根本解決 | • 修改現有邏輯<br>• 需要充分測試 | • 長期解決方案<br>• 防止問題產生 |

---

## 🎯 建議實施順序

### 階段 1：立即執行（本週）
1. ✅ **創建手動清理腳本**（方案 1）
2. ✅ **執行乾運行測試**
3. ✅ **執行實際清理**
4. ✅ **驗證清理效果**

### 階段 2：自動化預防（下週）
1. ✅ **開發定期驗證任務**（方案 2）
2. ✅ **配置 Celery Beat 排程**
3. ✅ **測試定期任務**
4. ✅ **監控執行日誌**

### 階段 3：長期優化（未來）
1. ✅ **改進 sync_all_jenkins_jobs_task**（方案 3）
2. ✅ **改進 sync_jenkins_builds**
3. ✅ **添加 NAS 檔案清理**
4. ✅ **完善錯誤處理和監控**

---

## 🚨 風險評估與注意事項

### 資料安全

- ⚠️  **強制備份**：清理前務必備份資料
- ⚠️  **乾運行**：先執行 `--dry-run` 確認要刪除的資料
- ⚠️  **分階段執行**：先處理單一 Server，確認無誤後再全面清理

### 效能影響

- ⚠️  **大量 Jobs**：如果有上千個 Jobs，驗證會較慢
- ⚠️  **API 限流**：Jenkins API 可能有速率限制
- ⚠️  **資料庫負載**：大量刪除操作時注意資料庫效能

### 業務影響

- ⚠️  **正在構建的 Jobs**：不要刪除正在使用的 Jobs
- ⚠️  **歷史資料**：確認是否需要保留歷史記錄
- ⚠️  **NAS 檔案**：刪除 Build 前確認相關檔案處理

### 建議配置

```python
# 安全的清理策略
JENKINS_CLEANUP_CONFIG = {
    # 保留最近 N 天的資料（即使孤立）
    'keep_recent_days': 7,
    
    # 自動清理前的確認閾值
    'auto_cleanup_threshold': 10,  # 孤立資料少於 10 個才自動清理
    
    # 排除的 Job 名稱模式（正則表達式）
    'exclude_patterns': [
        r'^IMPORTANT_.*',  # 保留重要的 Jobs
        r'^ARCHIVE_.*',    # 保留存檔的 Jobs
    ],
}
```

---

## 📝 執行檢查清單

### 清理前

- [ ] 確認 Jenkins Server 在線且可訪問
- [ ] 執行 `--dry-run` 查看要刪除的資料
- [ ] 檢查是否有重要的 Jobs 或 Builds 將被刪除
- [ ] 啟用 `--backup` 選項
- [ ] 通知相關人員（如有必要）

### 清理中

- [ ] 監控腳本執行日誌
- [ ] 注意是否有錯誤訊息
- [ ] 記錄刪除的 Jobs 和 Builds 數量

### 清理後

- [ ] 驗證 Web UI 顯示正確
- [ ] 檢查資料庫記錄數量
- [ ] 確認 Jenkins Server 功能正常
- [ ] 保留備份檔案至少 30 天

---

## 📚 相關文檔

- [Jenkins Build 狀態未更新問題](./JENKINS_BUILD_STATUS_NOT_UPDATED.md)
- [Jenkins API 文檔](https://www.jenkins.io/doc/book/using/remote-access-api/)
- [Django 資料庫遷移](https://docs.djangoproject.com/en/4.2/topics/migrations/)

---

**最後更新**：2025-11-21  
**維護者**：Network Toolbox Team  
**狀態**：待實施（規劃階段）
