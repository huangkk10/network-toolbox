# Jenkins 同步機制改進 - 技術設計文檔（方案 3）

## 📋 目標

從根本上改進 Jenkins 同步邏輯，在同步過程中**即時檢測和清理孤立資料**，防止資料不一致問題的產生。

### 核心理念

```
同步 = 創建/更新 + 清理
```

不僅要同步存在的資料，也要清理不存在的資料，實現雙向同步。

---

## 🏗️ 架構設計

### 當前架構問題

```
目前的同步流程（單向同步）：
┌─────────────────────────────────────┐
│  Jenkins Server (真實狀態)          │
│  - Jobs: A, B, C                    │
│  - Builds: #1-#50                   │
└──────────────┬──────────────────────┘
               │ 單向同步 ↓
               │ (只創建/更新)
┌──────────────▼──────────────────────┐
│  Database (可能有孤立資料)           │
│  - Jobs: A, B, C, D (孤立)          │
│  - Builds: #1-#100 (部分孤立)       │
└─────────────────────────────────────┘

問題：D Job 和 #51-#100 Builds 是孤立資料
```

### 改進後架構

```
改進的同步流程（雙向同步）：
┌─────────────────────────────────────┐
│  Jenkins Server (真實狀態)          │
│  - Jobs: A, B, C                    │
│  - Builds: #1-#50                   │
└──────────────┬──────────────────────┘
               │ 雙向同步 ↕
               │ (創建/更新/刪除)
┌──────────────▼──────────────────────┐
│  Database (與 Jenkins 一致)          │
│  - Jobs: A, B, C                    │
│  - Builds: #1-#50                   │
└─────────────────────────────────────┘

✅ 自動清理孤立資料
✅ 保持資料一致性
```

---

## 🛠️ 詳細實施計畫

### 階段 1：改進 `sync_all_jenkins_jobs_task`

#### 目標
在同步 Jobs 時，自動清理已刪除的 Jobs。

#### 文件位置
`backend/api/tasks.py` - `sync_all_jenkins_jobs_task` 函數

#### 改進策略

```python
改進思路：
1. 從 Jenkins API 獲取所有 Jobs 名稱 → jenkins_job_names (Set)
2. 從資料庫查詢該 Server 的所有 Jobs → db_job_names (Set)
3. 計算差集：db_job_names - jenkins_job_names = 孤立 Jobs
4. 刪除孤立 Jobs（可選：帶確認機制）
5. 正常同步存在的 Jobs
```

#### 詳細代碼設計

```python
@shared_task(
    bind=True,
    name='api.tasks.sync_all_jenkins_jobs_task',
    max_retries=2,
    default_retry_delay=300,
    time_limit=1800,  # 硬限制 30 分鐘
    soft_time_limit=1650  # 軟限制 27.5 分鐘
)
def sync_all_jenkins_jobs_task(self, server_id=None, cleanup_orphaned=True):
    """
    自動同步所有在線 Jenkins Server 的 Jobs（改進版）
    
    新增功能：
    - cleanup_orphaned: 是否清理孤立的 Jobs（預設 True）
    - 在同步過程中自動檢測和刪除不存在的 Jobs
    - 提供詳細的清理統計資訊
    
    Args:
        server_id: Jenkins Server ID（可選，None 表示所有在線 Server）
        cleanup_orphaned: 是否清理孤立 Jobs（預設 True）
        
    Returns:
        dict: {
            'success': bool,
            'total_servers': int,
            'jobs_created': int,
            'jobs_updated': int,
            'jobs_deleted': int,      # 🆕 新增
            'builds_deleted': int,    # 🆕 新增（級聯刪除）
            'errors': int,
            'duration': float
        }
    """
    start_time = timezone.now()
    logger = logging.getLogger(__name__)
    
    logger.info('[Celery] 🔄 開始同步 Jenkins Jobs（雙向同步模式）')
    logger.info(f'[Celery]   - Server ID: {server_id if server_id else "All"}')
    logger.info(f'[Celery]   - 清理孤立 Jobs: {"是" if cleanup_orphaned else "否"}')
    
    try:
        # 獲取要同步的 Servers
        if server_id:
            servers = JenkinsServer.objects.filter(id=server_id, is_online=True)
        else:
            servers = JenkinsServer.objects.filter(is_online=True)
        
        total_servers = servers.count()
        created_count = 0
        updated_count = 0
        deleted_count = 0
        builds_deleted_count = 0
        errors = 0
        
        logger.info(f'[Celery] 📡 找到 {total_servers} 個在線的 Jenkins Server')
        
        for server in servers:
            logger.info(f'[Celery] 🖥️  處理 Server: {server.name} ({server.url})')
            
            try:
                # 創建 Jenkins Client
                client = JenkinsClient(
                    base_url=server.url,
                    username=server.username,
                    api_token=server.api_token
                )
                
                # ==========================================
                # 階段 1: 獲取 Jenkins 上的所有 Jobs
                # ==========================================
                logger.info('[Celery]   📥 從 Jenkins 獲取 Jobs...')
                jenkins_jobs = client.get_all_jobs()
                jenkins_job_names = {job['name'] for job in jenkins_jobs}
                logger.info(f'[Celery]   ✅ Jenkins 上有 {len(jenkins_job_names)} 個 Jobs')
                
                # ==========================================
                # 階段 2: 獲取 View 資訊
                # ==========================================
                logger.info('[Celery]   📥 從 Jenkins 獲取 Views...')
                views = client.get_all_views()
                
                # 建立 Job -> View 的映射
                job_view_map = {}
                for view in views:
                    view_name = view.get('name', '')
                    view_url = view.get('url', '')
                    
                    if view_name and view_name != 'all':
                        view_jobs = client.get_view_jobs(view_name)
                        for job in view_jobs:
                            job_name = job.get('name')
                            if job_name:
                                job_view_map[job_name] = view_name
                
                logger.info(f'[Celery]   ✅ 找到 {len(views)} 個 Views')
                
                # ==========================================
                # 階段 3: 🆕 清理孤立的 Jobs（雙向同步核心）
                # ==========================================
                if cleanup_orphaned:
                    logger.info('[Celery]   🔍 檢查孤立的 Jobs...')
                    
                    # 獲取資料庫中該 Server 的所有 Jobs
                    db_jobs = JenkinsJob.objects.filter(server=server)
                    db_job_names = {job.name for job in db_jobs}
                    
                    # 計算孤立的 Jobs（存在於資料庫但不存在於 Jenkins）
                    orphaned_job_names = db_job_names - jenkins_job_names
                    
                    if orphaned_job_names:
                        logger.warning(f'[Celery]   ⚠️  發現 {len(orphaned_job_names)} 個孤立 Jobs')
                        
                        # 統計孤立 Jobs 相關的 Builds 數量（用於日誌）
                        orphaned_jobs = db_jobs.filter(name__in=orphaned_job_names)
                        orphaned_builds_count = 0
                        
                        for orphaned_job in orphaned_jobs:
                            build_count = orphaned_job.builds.count()
                            orphaned_builds_count += build_count
                            logger.info(f'[Celery]     - 孤立 Job: {orphaned_job.name} (含 {build_count} builds)')
                        
                        # 刪除孤立的 Jobs（級聯刪除相關 Builds）
                        with transaction.atomic():
                            delete_result = orphaned_jobs.delete()
                            deleted_jobs = delete_result[0]
                            deleted_count += deleted_jobs
                            builds_deleted_count += orphaned_builds_count
                        
                        logger.info(f'[Celery]   🗑️  已刪除 {deleted_jobs} 個孤立 Jobs')
                        logger.info(f'[Celery]   🗑️  級聯刪除 {orphaned_builds_count} 個 Builds')
                    else:
                        logger.info('[Celery]   ✅ 無孤立 Jobs')
                
                # ==========================================
                # 階段 4: 同步存在的 Jobs（創建/更新）
                # ==========================================
                logger.info('[Celery]   🔄 同步 Jobs 資料...')
                
                for job_data in jenkins_jobs:
                    try:
                        job_name = job_data.get('name')
                        job_url = job_data.get('url')
                        color = job_data.get('color', '')
                        
                        # 判斷是否禁用
                        is_disabled = 'disabled' in color
                        
                        # 判斷是否可構建
                        is_buildable = color != 'disabled' and color != 'notbuilt'
                        
                        # 獲取 Job 所屬的 View
                        view_name = job_view_map.get(job_name, '')
                        
                        # 創建或更新 Job
                        job, created = JenkinsJob.objects.update_or_create(
                            server=server,
                            name=job_name,
                            defaults={
                                'url': job_url,
                                'full_name': job_name,
                                'is_buildable': is_buildable,
                                'is_disabled': is_disabled,
                                'view_name': view_name,
                                'last_sync_at': timezone.now(),
                            }
                        )
                        
                        if created:
                            created_count += 1
                            logger.debug(f'[Celery]     ✅ 創建 Job: {job_name}')
                        else:
                            updated_count += 1
                            logger.debug(f'[Celery]     🔄 更新 Job: {job_name}')
                    
                    except Exception as e:
                        errors += 1
                        logger.error(f'[Celery]     ❌ 處理 Job 失敗: {job_name} - {e}')
                
                # ==========================================
                # 階段 5: 更新伺服器同步時間
                # ==========================================
                server.last_sync_at = timezone.now()
                server.save()
                
                logger.info(f'[Celery]   ✅ Server {server.name} 同步完成')
                logger.info(f'[Celery]     - 創建: {created_count} | 更新: {updated_count} | 刪除: {deleted_count}')
                
                client.close()
                
            except Exception as e:
                errors += 1
                logger.error(f'[Celery] ❌ 處理 Server {server.name} 失敗: {e}', exc_info=True)
        
        # ==========================================
        # 返回統計結果
        # ==========================================
        duration = (timezone.now() - start_time).total_seconds()
        
        logger.info('[Celery] ✅ 所有 Jenkins Jobs 同步完成')
        logger.info(f'[Celery]   - 處理的 Servers: {total_servers}')
        logger.info(f'[Celery]   - 創建的 Jobs: {created_count}')
        logger.info(f'[Celery]   - 更新的 Jobs: {updated_count}')
        logger.info(f'[Celery]   - 刪除的 Jobs: {deleted_count}')  # 🆕
        logger.info(f'[Celery]   - 刪除的 Builds: {builds_deleted_count}')  # 🆕
        logger.info(f'[Celery]   - 錯誤數: {errors}')
        logger.info(f'[Celery]   - 耗時: {duration:.2f} 秒')
        
        return {
            'success': True,
            'total_servers': total_servers,
            'jobs_created': created_count,
            'jobs_updated': updated_count,
            'jobs_deleted': deleted_count,        # 🆕
            'builds_deleted': builds_deleted_count,  # 🆕
            'errors': errors,
            'duration': duration,
        }
    
    except Exception as e:
        duration = (timezone.now() - start_time).total_seconds()
        logger.error(f'[Celery] ❌ 同步 Jenkins Jobs 失敗: {e}', exc_info=True)
        
        return {
            'success': False,
            'total_servers': 0,
            'jobs_created': 0,
            'jobs_updated': 0,
            'jobs_deleted': 0,
            'builds_deleted': 0,
            'errors': 1,
            'duration': duration,
            'error_message': str(e),
        }
```

#### 關鍵改進點

1. **🆕 階段 3：孤立 Jobs 檢測與清理**
   - 使用 Set 差集計算：`db_job_names - jenkins_job_names`
   - 批量刪除孤立 Jobs（使用 `transaction.atomic()` 保證原子性）
   - 級聯刪除相關 Builds（利用 Django 的 `on_delete=models.CASCADE`）
   - 詳細記錄刪除資訊到日誌

2. **配置開關**
   - `cleanup_orphaned` 參數：允許開關此功能
   - 預設啟用（`True`），可根據需要調整

3. **統計資訊增強**
   - 新增 `jobs_deleted` 和 `builds_deleted` 計數
   - 便於監控和審計

---

### 階段 2：改進 `sync_jenkins_builds`

#### 目標
在同步 Builds 時，檢測並清理已刪除的 Builds。

#### 挑戰

```
問題：sync_jenkins_builds 只同步最近 N 個 Builds
- max_builds_per_job = 20
- max_age_days = 3

如何判斷哪些 Builds 是被刪除，哪些只是太舊？
```

#### 解決方案

```python
策略：
1. 保守清理策略：只清理「確定被刪除」的 Builds
2. 「確定被刪除」的定義：
   - Jenkins API 返回了完整的 Build 列表（allBuilds）
   - 資料庫中的 Build 不在列表中
   - 該 Build 不是太舊（在時間範圍內）

3. 分為兩種模式：
   - 快速同步模式（預設）：只同步最近 N 個，不刪除
   - 完整同步模式（可選）：獲取所有 Builds，清理孤立
```

#### 詳細代碼設計

```python
@shared_task(
    bind=True,
    name='api.tasks.sync_jenkins_builds',
    max_retries=2,
    default_retry_delay=300,
    time_limit=3600,
    soft_time_limit=3300
)
def sync_jenkins_builds(
    self, 
    server_id=None, 
    max_builds_per_job=20, 
    max_age_days=3,
    full_sync=False,          # 🆕 新增：完整同步模式
    cleanup_orphaned=False    # 🆕 新增：清理孤立 Builds（僅在 full_sync=True 時生效）
):
    """
    同步 Jenkins Builds 到資料庫（改進版）
    
    兩種模式：
    1. 快速同步（預設）：
       - 只同步最近 max_builds_per_job 個 Builds
       - 不刪除孤立 Builds（無法判斷是刪除還是太舊）
       
    2. 完整同步（full_sync=True）：
       - 獲取 Job 的所有 Builds（性能較慢）
       - 可選清理孤立 Builds（cleanup_orphaned=True）
    
    Args:
        server_id: Jenkins Server ID
        max_builds_per_job: 快速模式下每個 Job 最多同步的 Builds 數量
        max_age_days: 快速模式下 Builds 的時間範圍（天）
        full_sync: 是否完整同步（獲取所有 Builds）
        cleanup_orphaned: 是否清理孤立 Builds（僅在 full_sync=True 時生效）
    
    Returns:
        dict: 同步統計資訊（新增 builds_deleted）
    """
    start_time = timezone.now()
    logger = logging.getLogger(__name__)
    
    sync_mode = "完整同步" if full_sync else "快速同步"
    logger.info(f'[Celery] 🔄 開始同步 Jenkins Builds ({sync_mode})')
    logger.info(f'[Celery]   - Server ID: {server_id if server_id else "All"}')
    if full_sync:
        logger.info(f'[Celery]   - 完整同步模式：獲取所有 Builds')
        logger.info(f'[Celery]   - 清理孤立 Builds: {"是" if cleanup_orphaned else "否"}')
    else:
        logger.info(f'[Celery]   - 快速同步模式：每個 Job 最多 {max_builds_per_job} 個 Builds')
        logger.info(f'[Celery]   - 時間範圍: 最近 {max_age_days} 天')
    
    try:
        # 獲取要同步的 Servers
        if server_id:
            servers = JenkinsServer.objects.filter(id=server_id, is_online=True)
        else:
            servers = JenkinsServer.objects.filter(is_online=True)
        
        total_servers = servers.count()
        total_jobs_processed = 0
        total_builds_found = 0
        builds_created = 0
        builds_updated = 0
        builds_deleted = 0      # 🆕 新增
        builds_skipped = 0
        errors = 0
        
        jobs_to_update = []
        
        logger.info(f'[Celery] 📡 找到 {total_servers} 個在線的 Jenkins Server')
        
        for server in servers:
            logger.info(f'[Celery] 🖥️  處理 Server: {server.name} ({server.url})')
            
            # 獲取該 Server 的所有 Jobs
            jobs = JenkinsJob.objects.filter(server=server)
            jobs_count = jobs.count()
            logger.info(f'[Celery]   - 找到 {jobs_count} 個 Jobs')
            
            if jobs_count == 0:
                continue
            
            # 創建 Jenkins Client
            client = None
            try:
                client = JenkinsClient(
                    base_url=server.url,
                    username=server.username,
                    api_token=server.api_token
                )
                
                # 處理每個 Job
                for job in jobs:
                    try:
                        logger.debug(f'[Celery]   🔍 處理 Job: {job.name}')
                        
                        job_needs_update = False
                        
                        # ==========================================
                        # 階段 1: 從 Jenkins 獲取 Builds
                        # ==========================================
                        if full_sync:
                            # 完整同步：獲取所有 Builds
                            all_builds = client.get_all_builds(job.name)
                            jenkins_build_numbers = {b['number'] for b in all_builds}
                            builds_to_process = all_builds
                            logger.debug(f'[Celery]     📥 完整同步：獲取所有 Builds (共 {len(all_builds)} 個)')
                        else:
                            # 快速同步：只獲取最近的 Builds
                            builds_data = client.get_job_builds(
                                job.name, 
                                max_builds=max_builds_per_job
                            )
                            builds_to_process = builds_data
                            logger.debug(f'[Celery]     📥 快速同步：獲取最近 {len(builds_to_process)} 個 Builds')
                        
                        total_builds_found += len(builds_to_process)
                        
                        # ==========================================
                        # 階段 2: 獲取資料庫中現有的 Builds
                        # ==========================================
                        existing_builds = {
                            b.build_number: b
                            for b in JenkinsBuild.objects.filter(job=job)
                                .only('id', 'build_number', 'result', 'is_building', 
                                      'duration', 'failed_stage', 'pipeline_stages', 'updated_at')
                        }
                        
                        # ==========================================
                        # 階段 3: 🆕 清理孤立的 Builds（僅完整同步模式）
                        # ==========================================
                        if full_sync and cleanup_orphaned:
                            # 計算孤立的 Builds
                            db_build_numbers = set(existing_builds.keys())
                            orphaned_build_numbers = db_build_numbers - jenkins_build_numbers
                            
                            if orphaned_build_numbers:
                                logger.info(f'[Celery]     ⚠️  發現 {len(orphaned_build_numbers)} 個孤立 Builds')
                                
                                # 刪除孤立的 Builds
                                orphaned_builds = JenkinsBuild.objects.filter(
                                    job=job,
                                    build_number__in=orphaned_build_numbers
                                )
                                
                                with transaction.atomic():
                                    delete_result = orphaned_builds.delete()
                                    deleted_builds = delete_result[0]
                                    builds_deleted += deleted_builds
                                
                                logger.info(f'[Celery]     🗑️  已刪除 {deleted_builds} 個孤立 Builds')
                                
                                # 從 existing_builds 中移除已刪除的
                                for build_num in orphaned_build_numbers:
                                    existing_builds.pop(build_num, None)
                        
                        # ==========================================
                        # 階段 4: 同步 Builds（創建/更新）
                        # ==========================================
                        # 過濾：排除太舊的 Builds（快速模式）
                        if not full_sync:
                            cutoff_time = timezone.now() - timedelta(days=max_age_days)
                            builds_to_process = [
                                b for b in builds_to_process
                                if datetime.fromtimestamp(b.get('timestamp', 0) / 1000, tz=pytz.UTC) >= cutoff_time
                            ]
                        
                        # 分離新 Builds 和現有 Builds
                        new_builds = []
                        update_builds_data = []
                        
                        for build_data in builds_to_process:
                            build_number = build_data.get('number')
                            
                            if build_number in existing_builds:
                                update_builds_data.append(build_data)
                            else:
                                new_builds.append(build_data)
                        
                        logger.debug(f'[Celery]     - 新 Builds: {len(new_builds)} | 更新 Builds: {len(update_builds_data)}')
                        
                        # 處理新 Builds（創建）
                        for build_data in new_builds:
                            try:
                                build_number = build_data.get('number')
                                result = build_data.get('result')
                                building = build_data.get('building', False)
                                duration = build_data.get('duration', 0)
                                url = build_data.get('url', '')
                                timestamp = build_data.get('timestamp', 0)
                                
                                build_timestamp = datetime.fromtimestamp(
                                    timestamp / 1000, 
                                    tz=pytz.UTC
                                )
                                
                                # 獲取 Pipeline Stages
                                pipeline_stages = []
                                failed_stage = None
                                
                                if result == 'FAILURE':
                                    stages_data = client.get_pipeline_stages(job.name, build_number)
                                    if stages_data:
                                        pipeline_stages = stages_data
                                        failed_stages = [s for s in stages_data if s.get('status') in ['FAILED', 'ABORTED']]
                                        if failed_stages:
                                            first_failed = failed_stages[0]
                                            failed_stage = (
                                                first_failed.get('displayName') or 
                                                first_failed.get('name')
                                            )
                                
                                # 創建新 Build
                                build = JenkinsBuild.objects.create(
                                    job=job,
                                    build_number=build_number,
                                    display_name=f'#{build_number}',
                                    url=url,
                                    result=result or 'UNKNOWN',
                                    is_building=building,
                                    duration=duration,
                                    build_timestamp=build_timestamp,
                                    pipeline_stages=pipeline_stages,
                                    failed_stage=failed_stage,
                                )
                                builds_created += 1
                                logger.debug(f'[Celery]     ✅ 創建 Build: #{build_number} ({result})')
                                
                                # 更新 Job 的 last_build_time
                                if not job.last_build_time or build_timestamp > job.last_build_time:
                                    job.last_build_time = build_timestamp
                                    job.last_build_number = build_number
                                    job.last_build_status = result or 'UNKNOWN'
                                    job_needs_update = True
                            
                            except Exception as e:
                                errors += 1
                                logger.error(f'[Celery]     ❌ 創建 Build 失敗: #{build_number} - {e}')
                        
                        # 處理現有 Builds（更新）
                        builds_to_update = []
                        
                        for build_data in update_builds_data:
                            try:
                                build_number = build_data.get('number')
                                existing_build = existing_builds[build_number]
                                
                                result = build_data.get('result')
                                building = build_data.get('building', False)
                                duration = build_data.get('duration', 0)
                                
                                needs_update = False
                                
                                # 檢查是否需要更新
                                if existing_build.result != result:
                                    existing_build.result = result
                                    needs_update = True
                                
                                if existing_build.is_building != building:
                                    existing_build.is_building = building
                                    needs_update = True
                                
                                if duration > 0 and existing_build.duration != duration:
                                    existing_build.duration = duration
                                    needs_update = True
                                
                                # 獲取失敗 Stage（如果需要）
                                if result == 'FAILURE' and not existing_build.failed_stage:
                                    stages_data = client.get_pipeline_stages(job.name, build_number)
                                    if stages_data:
                                        existing_build.pipeline_stages = stages_data
                                        failed_stages = [s for s in stages_data if s.get('status') in ['FAILED', 'ABORTED']]
                                        if failed_stages:
                                            first_failed = failed_stages[0]
                                            existing_build.failed_stage = (
                                                first_failed.get('displayName') or 
                                                first_failed.get('name')
                                            )
                                        needs_update = True
                                
                                if needs_update:
                                    builds_to_update.append(existing_build)
                            
                            except Exception as e:
                                errors += 1
                                logger.error(f'[Celery]     ❌ 更新 Build 失敗: #{build_number} - {e}')
                        
                        # 批量更新 Builds
                        if builds_to_update:
                            try:
                                JenkinsBuild.objects.bulk_update(
                                    builds_to_update,
                                    ['result', 'is_building', 'duration', 'failed_stage', 'pipeline_stages'],
                                    batch_size=100
                                )
                                builds_updated += len(builds_to_update)
                                logger.debug(f'[Celery]     ✅ 批量更新 {len(builds_to_update)} 個 Builds')
                            except Exception as e:
                                errors += 1
                                logger.error(f'[Celery]     ❌ 批量更新失敗: {e}')
                        
                        # 收集需要更新的 Job
                        if job_needs_update:
                            jobs_to_update.append(job)
                        
                        total_jobs_processed += 1
                    
                    except Exception as e:
                        errors += 1
                        logger.error(f'[Celery]   ❌ 處理 Job 失敗: {job.name} - {e}')
                
                client.close()
            
            except Exception as e:
                errors += 1
                logger.error(f'[Celery] ❌ 連接 Server 失敗: {server.name} - {e}', exc_info=True)
            finally:
                if client:
                    client.close()
        
        # 批量更新所有 Jobs
        if jobs_to_update:
            try:
                JenkinsJob.objects.bulk_update(
                    jobs_to_update,
                    ['last_build_time', 'last_build_number', 'last_build_status'],
                    batch_size=100
                )
                logger.info(f'[Celery]   ✅ 批量更新 {len(jobs_to_update)} 個 Jobs')
            except Exception as e:
                errors += 1
                logger.error(f'[Celery]   ❌ 批量更新 Jobs 失敗: {e}')
        
        duration = (timezone.now() - start_time).total_seconds()
        
        logger.info('[Celery] ✅ 所有 Jenkins Builds 同步完成')
        logger.info(f'[Celery]   - 處理的 Servers: {total_servers}')
        logger.info(f'[Celery]   - 處理的 Jobs: {total_jobs_processed}')
        logger.info(f'[Celery]   - 找到 Builds: {total_builds_found}')
        logger.info(f'[Celery]   - 創建 Builds: {builds_created}')
        logger.info(f'[Celery]   - 更新 Builds: {builds_updated}')
        logger.info(f'[Celery]   - 刪除 Builds: {builds_deleted}')  # 🆕
        logger.info(f'[Celery]   - 錯誤數: {errors}')
        logger.info(f'[Celery]   - 耗時: {duration:.2f} 秒')
        
        return {
            'success': True,
            'total_servers': total_servers,
            'total_jobs': total_jobs_processed,
            'total_builds_found': total_builds_found,
            'builds_created': builds_created,
            'builds_updated': builds_updated,
            'builds_deleted': builds_deleted,  # 🆕
            'builds_skipped': builds_skipped,
            'errors': errors,
            'duration': duration,
        }
    
    except Exception as e:
        duration = (timezone.now() - start_time).total_seconds()
        logger.error(f'[Celery] ❌ 同步 Jenkins Builds 失敗: {e}', exc_info=True)
        
        return {
            'success': False,
            'total_servers': 0,
            'total_jobs': 0,
            'total_builds_found': 0,
            'builds_created': 0,
            'builds_updated': 0,
            'builds_deleted': 0,
            'builds_skipped': 0,
            'errors': 1,
            'duration': duration,
            'error_message': str(e),
        }
```

#### 關鍵改進點

1. **兩種同步模式**
   - **快速模式**（預設）：只同步最近的 Builds，不刪除（無法判斷）
   - **完整模式**（`full_sync=True`）：獲取所有 Builds，可選清理孤立資料

2. **孤立 Builds 檢測**
   - 使用完整的 Build 列表（`get_all_builds`）
   - 計算差集：`db_build_numbers - jenkins_build_numbers`
   - 只在完整模式下執行（避免誤刪）

3. **配置靈活性**
   - `full_sync`：開關完整同步
   - `cleanup_orphaned`：開關清理功能
   - 兩個參數獨立控制，最大化靈活性

---

### 階段 3：新增 JenkinsClient 方法

#### 需要新增的 API 方法

```python
# 文件：backend/library/services/jenkins_client.py

class JenkinsClient:
    """Jenkins API 客戶端"""
    
    # ... 現有方法 ...
    
    def get_all_builds(self, job_name: str) -> List[Dict]:
        """
        獲取 Job 的所有 Builds（不限數量）
        
        ⚠️  注意：此方法可能較慢，僅用於完整同步模式
        
        Args:
            job_name: Job 名稱
            
        Returns:
            List[Dict]: 所有 Builds 資訊
        """
        try:
            url = f"{self.base_url}/job/{job_name}/api/json"
            params = {
                'tree': 'allBuilds[number,url,result,building,timestamp,duration]'
            }
            
            response = self.session.get(url, params=params, timeout=60)
            response.raise_for_status()
            
            data = response.json()
            all_builds = data.get('allBuilds', [])
            
            return all_builds
        
        except Exception as e:
            logger.error(f"獲取所有 Builds 失敗: {job_name} - {e}")
            return []
```

---

### 階段 4：更新 Celery Beat 排程

#### 文件：`backend/network_toolbox/celery.py` 或 `backend/api/tasks.py`

```python
# Celery Beat 排程配置
app.conf.beat_schedule = {
    # ==========================================
    # 快速同步（高頻率）
    # ==========================================
    'sync-jenkins-builds-fast-every-10-minutes': {
        'task': 'api.tasks.sync_jenkins_builds',
        'schedule': crontab(minute='*/10'),  # 每 10 分鐘
        'kwargs': {
            'max_builds_per_job': 20,
            'max_age_days': 3,
            'full_sync': False,          # 快速模式
            'cleanup_orphaned': False,   # 不清理
        },
    },
    
    # ==========================================
    # 完整同步 + 清理（低頻率）
    # ==========================================
    'sync-jenkins-builds-full-daily': {
        'task': 'api.tasks.sync_jenkins_builds',
        'schedule': crontab(hour=2, minute=0),  # 每天凌晨 2 點
        'kwargs': {
            'full_sync': True,           # 完整模式
            'cleanup_orphaned': True,    # 清理孤立 Builds
        },
    },
    
    # ==========================================
    # Jobs 同步 + 清理
    # ==========================================
    'sync-jenkins-jobs-with-cleanup-hourly': {
        'task': 'api.tasks.sync_all_jenkins_jobs_task',
        'schedule': crontab(minute=0),  # 每小時
        'kwargs': {
            'cleanup_orphaned': True,    # 清理孤立 Jobs
        },
    },
}
```

#### 排程策略說明

```
同步策略：高頻快速 + 低頻完整

┌──────────────────────────────────────────┐
│  快速同步（每 10 分鐘）                   │
│  - 只同步最近的 Builds                    │
│  - 不刪除孤立資料                         │
│  - 快速反應最新狀態                       │
└──────────────────────────────────────────┘

┌──────────────────────────────────────────┐
│  完整同步（每天凌晨 2 點）                 │
│  - 獲取所有 Builds                        │
│  - 清理孤立 Builds                        │
│  - 確保資料完整一致                       │
└──────────────────────────────────────────┘

┌──────────────────────────────────────────┐
│  Jobs 同步（每小時）                      │
│  - 同步 Jobs 列表                         │
│  - 清理孤立 Jobs                          │
│  - 保持 Jobs 列表最新                     │
└──────────────────────────────────────────┘
```

---

## 🧪 測試計畫

### 單元測試

#### 文件：`tests/unit/backend/test_jenkins_sync_improvement.py`

```python
#!/usr/bin/env python
"""
測試 Jenkins 同步機制改進

測試項目：
1. 孤立 Jobs 檢測
2. 孤立 Builds 檢測
3. 刪除邏輯
4. 邊界條件
"""

import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from django.test import TestCase
from api.models import JenkinsServer, JenkinsJob, JenkinsBuild
from unittest.mock import Mock, patch


class JenkinsSyncImprovementTest(TestCase):
    """Jenkins 同步改進測試"""
    
    def setUp(self):
        """測試初始化"""
        # 創建測試 Server
        self.server = JenkinsServer.objects.create(
            name='Test Server',
            url='http://test.jenkins.com',
            username='admin',
            api_token='token123',
            is_online=True
        )
        
        # 創建測試 Jobs
        self.job1 = JenkinsJob.objects.create(
            server=self.server,
            name='Job_A',
            full_name='Job_A',
            url='http://test.jenkins.com/job/Job_A'
        )
        
        self.job2 = JenkinsJob.objects.create(
            server=self.server,
            name='Job_B',
            full_name='Job_B',
            url='http://test.jenkins.com/job/Job_B'
        )
        
        # Job_C 是孤立的（稍後在 Jenkins 模擬中不返回）
        self.job_orphaned = JenkinsJob.objects.create(
            server=self.server,
            name='Job_C_Orphaned',
            full_name='Job_C_Orphaned',
            url='http://test.jenkins.com/job/Job_C_Orphaned'
        )
        
        # 創建測試 Builds
        for i in range(1, 6):
            JenkinsBuild.objects.create(
                job=self.job1,
                build_number=i,
                display_name=f'#{i}',
                url=f'http://test.jenkins.com/job/Job_A/{i}',
                result='SUCCESS'
            )
    
    @patch('library.services.jenkins_client.JenkinsClient')
    def test_orphaned_jobs_detection(self, MockJenkinsClient):
        """測試孤立 Jobs 檢測"""
        # 模擬 Jenkins API 返回 Job_A 和 Job_B（不包含 Job_C）
        mock_client = MockJenkinsClient.return_value
        mock_client.get_all_jobs.return_value = [
            {'name': 'Job_A', 'url': 'http://test.jenkins.com/job/Job_A'},
            {'name': 'Job_B', 'url': 'http://test.jenkins.com/job/Job_B'},
        ]
        
        # 執行同步（帶清理）
        from api.tasks import sync_all_jenkins_jobs_task
        result = sync_all_jenkins_jobs_task(server_id=self.server.id, cleanup_orphaned=True)
        
        # 驗證
        self.assertTrue(result['success'])
        self.assertEqual(result['jobs_deleted'], 1)  # Job_C 應該被刪除
        
        # 驗證資料庫
        self.assertTrue(JenkinsJob.objects.filter(name='Job_A').exists())
        self.assertTrue(JenkinsJob.objects.filter(name='Job_B').exists())
        self.assertFalse(JenkinsJob.objects.filter(name='Job_C_Orphaned').exists())
    
    @patch('library.services.jenkins_client.JenkinsClient')
    def test_orphaned_builds_detection(self, MockJenkinsClient):
        """測試孤立 Builds 檢測"""
        # 模擬 Jenkins API 返回 Build #1-#3（不包含 #4-#5）
        mock_client = MockJenkinsClient.return_value
        mock_client.get_all_builds.return_value = [
            {'number': 1, 'result': 'SUCCESS', 'building': False, 'timestamp': 0, 'duration': 0},
            {'number': 2, 'result': 'SUCCESS', 'building': False, 'timestamp': 0, 'duration': 0},
            {'number': 3, 'result': 'SUCCESS', 'building': False, 'timestamp': 0, 'duration': 0},
        ]
        
        # 執行完整同步（帶清理）
        from api.tasks import sync_jenkins_builds
        result = sync_jenkins_builds(
            server_id=self.server.id,
            full_sync=True,
            cleanup_orphaned=True
        )
        
        # 驗證
        self.assertTrue(result['success'])
        self.assertEqual(result['builds_deleted'], 2)  # Build #4-#5 應該被刪除
        
        # 驗證資料庫
        self.assertEqual(JenkinsBuild.objects.filter(job=self.job1).count(), 3)
        self.assertTrue(JenkinsBuild.objects.filter(job=self.job1, build_number=1).exists())
        self.assertTrue(JenkinsBuild.objects.filter(job=self.job1, build_number=2).exists())
        self.assertTrue(JenkinsBuild.objects.filter(job=self.job1, build_number=3).exists())
        self.assertFalse(JenkinsBuild.objects.filter(job=self.job1, build_number=4).exists())
        self.assertFalse(JenkinsBuild.objects.filter(job=self.job1, build_number=5).exists())
    
    @patch('library.services.jenkins_client.JenkinsClient')
    def test_cleanup_disabled(self, MockJenkinsClient):
        """測試關閉清理功能"""
        # 模擬 Jenkins API 返回 Job_A 和 Job_B
        mock_client = MockJenkinsClient.return_value
        mock_client.get_all_jobs.return_value = [
            {'name': 'Job_A', 'url': 'http://test.jenkins.com/job/Job_A'},
            {'name': 'Job_B', 'url': 'http://test.jenkins.com/job/Job_B'},
        ]
        
        # 執行同步（不清理）
        from api.tasks import sync_all_jenkins_jobs_task
        result = sync_all_jenkins_jobs_task(server_id=self.server.id, cleanup_orphaned=False)
        
        # 驗證
        self.assertTrue(result['success'])
        self.assertEqual(result['jobs_deleted'], 0)  # 不應該刪除任何 Job
        
        # 驗證 Job_C 仍然存在
        self.assertTrue(JenkinsJob.objects.filter(name='Job_C_Orphaned').exists())
```

### 整合測試

#### 測試流程

```bash
# 1. 在測試環境執行
docker exec nt-django python -m pytest tests/unit/backend/test_jenkins_sync_improvement.py -v

# 2. 驗證日誌
docker exec nt-django tail -f /app/logs/django.log | grep "同步 Jenkins"

# 3. 檢查資料庫
docker exec nt-django python manage.py shell
>>> from api.models import JenkinsJob, JenkinsBuild
>>> JenkinsJob.objects.count()
>>> JenkinsBuild.objects.count()
```

---

## 📊 效能評估

### 效能影響分析

| 操作 | 快速模式 | 完整模式 | 影響 |
|------|---------|---------|------|
| **API 請求** | 少（只要最近 20 個） | 多（所有 Builds） | 完整模式較慢 |
| **資料庫查詢** | 相同 | 相同 | 無差異 |
| **刪除操作** | 無 | 有（級聯刪除） | 完整模式多一次刪除 |
| **執行時間** | ~2-5 分鐘 | ~10-30 分鐘 | 取決於 Jobs 和 Builds 數量 |

### 建議配置

```python
# 針對不同規模的建議配置

# 小型專案（< 100 Jobs, < 5000 Builds）
JENKINS_SYNC_CONFIG_SMALL = {
    'fast_sync_interval': 10,  # 分鐘
    'full_sync_interval': 'daily',  # 每天
    'cleanup_orphaned': True,
}

# 中型專案（100-500 Jobs, 5000-50000 Builds）
JENKINS_SYNC_CONFIG_MEDIUM = {
    'fast_sync_interval': 15,  # 分鐘
    'full_sync_interval': 'daily',  # 每天
    'cleanup_orphaned': True,
}

# 大型專案（> 500 Jobs, > 50000 Builds）
JENKINS_SYNC_CONFIG_LARGE = {
    'fast_sync_interval': 20,  # 分鐘
    'full_sync_interval': 'weekly',  # 每週（性能考量）
    'cleanup_orphaned': True,
    'full_sync_batch_size': 50,  # 分批處理
}
```

---

## 🚨 風險評估

### 潛在風險

1. **誤刪風險**
   - **風險**：邏輯錯誤導致刪除不應刪除的資料
   - **緩解**：充分測試、日誌記錄、可關閉功能

2. **效能風險**
   - **風險**：完整同步模式可能較慢
   - **緩解**：只在低流量時段執行、分批處理

3. **API 限流**
   - **風險**：頻繁 API 請求可能觸發 Jenkins 限流
   - **緩解**：合理設定同步間隔、錯誤重試機制

### 安全措施

```python
# 安全配置建議
JENKINS_SYNC_SAFETY = {
    # 啟用前先測試
    'test_mode': True,  # 先在測試環境驗證
    
    # 保留最近資料（即使孤立）
    'keep_recent_days': 7,
    
    # 限制單次刪除數量
    'max_delete_per_sync': 100,
    
    # 刪除前備份
    'backup_before_delete': True,
    
    # 詳細日誌
    'verbose_logging': True,
}
```

---

## 📝 實施檢查清單

### 開發階段

- [ ] **階段 1**：修改 `sync_all_jenkins_jobs_task`
  - [ ] 添加 `cleanup_orphaned` 參數
  - [ ] 實現孤立 Jobs 檢測邏輯
  - [ ] 添加刪除邏輯（transaction.atomic）
  - [ ] 更新返回值（jobs_deleted, builds_deleted）
  - [ ] 添加詳細日誌

- [ ] **階段 2**：修改 `sync_jenkins_builds`
  - [ ] 添加 `full_sync` 參數
  - [ ] 添加 `cleanup_orphaned` 參數
  - [ ] 實現完整同步模式
  - [ ] 實現孤立 Builds 檢測邏輯
  - [ ] 添加刪除邏輯
  - [ ] 更新返回值

- [ ] **階段 3**：新增 JenkinsClient 方法
  - [ ] 實現 `get_all_builds()` 方法
  - [ ] 添加錯誤處理
  - [ ] 添加超時控制

- [ ] **階段 4**：更新 Celery Beat 排程
  - [ ] 保留快速同步任務（每 10 分鐘）
  - [ ] 新增完整同步任務（每天凌晨 2 點）
  - [ ] 更新 Jobs 同步任務（每小時）

### 測試階段

- [ ] **單元測試**
  - [ ] 測試孤立 Jobs 檢測
  - [ ] 測試孤立 Builds 檢測
  - [ ] 測試刪除邏輯
  - [ ] 測試配置開關
  - [ ] 測試邊界條件

- [ ] **整合測試**
  - [ ] 在測試環境運行完整流程
  - [ ] 驗證資料一致性
  - [ ] 檢查日誌輸出
  - [ ] 驗證效能影響

### 部署階段

- [ ] **預部署**
  - [ ] 備份資料庫
  - [ ] 準備回滾方案
  - [ ] 通知團隊

- [ ] **部署**
  - [ ] 更新代碼
  - [ ] 重啟 Celery Worker
  - [ ] 重啟 Celery Beat
  - [ ] 驗證任務執行

- [ ] **後部署**
  - [ ] 監控日誌
  - [ ] 驗證資料同步
  - [ ] 檢查 Web UI 顯示
  - [ ] 記錄效能數據

### 監控階段

- [ ] **持續監控**
  - [ ] 監控 Celery 任務執行
  - [ ] 檢查錯誤日誌
  - [ ] 驗證資料一致性
  - [ ] 追蹤刪除統計

---

## 📚 相關文檔

- [Jenkins 資料清理計畫](../troubleshooting/JENKINS_DATA_CLEANUP_PLAN.md)
- [Jenkins Build 狀態未更新問題](../troubleshooting/JENKINS_BUILD_STATUS_NOT_UPDATED.md)
- [Celery 定期任務配置](./CELERY_IMPLEMENTATION_GUIDE.md)

---

## 🎯 總結

### 方案 3 的優勢

✅ **從根本解決**：在同步過程中即時處理孤立資料  
✅ **自動化**：無需手動干預，自動保持一致性  
✅ **靈活配置**：可根據需求開關功能  
✅ **效能平衡**：快速同步 + 完整同步雙模式  
✅ **安全可靠**：充分的測試和錯誤處理  

### 下一步

1. **確認設計**：Review 此文檔，確認細節
2. **開始實施**：按照檢查清單逐步開發
3. **充分測試**：在測試環境驗證所有功能
4. **謹慎部署**：先在單一 Server 測試，再全面推廣

---

**最後更新**：2025-11-21  
**維護者**：Network Toolbox Team  
**狀態**：詳細設計完成，待實施
