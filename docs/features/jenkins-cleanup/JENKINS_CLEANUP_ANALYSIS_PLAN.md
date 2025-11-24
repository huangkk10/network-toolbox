# Jenkins 孤立資料清理機制分析與規劃

**創建日期**: 2025-11-24  
**狀態**: 📋 規劃階段（未執行）  
**目的**: 分析現有清理機制並規劃自動化清理任務

---

## 📊 現狀分析

### 1. 現有定時任務 (Celery Tasks)

根據 `/backend/api/tasks.py` 分析，目前有以下 Jenkins 相關的定時任務：

#### ✅ 已存在的任務

| 任務名稱 | 功能 | 執行頻率 | 說明 |
|---------|------|---------|------|
| `sync_jenkins_builds` | 同步 Jenkins Builds 到資料庫 | 每小時 | 從 Jenkins API 獲取最新 Builds，創建/更新資料庫記錄 |
| `auto_store_workspaces` | 自動存儲 Workspace 到 NAS | 每 4 小時 | 將符合條件的 Build Workspace 存儲到 NAS |

#### ❌ 缺少的清理任務

**目前沒有自動清理孤立資料的定時任務**，只有手動腳本：
- `/backend/cleanup_orphaned_jenkins_data.py` （需要手動執行）

---

### 2. 手動清理腳本分析

#### 檔案：`cleanup_orphaned_jenkins_data.py`

**功能**：
1. ✅ 檢查資料庫中的 Jobs 是否仍存在於 Jenkins Server
2. ✅ 檢查資料庫中的 Builds 是否仍存在於 Jenkins Server
3. ✅ 列出所有孤立資料
4. ✅ 提供備份選項
5. ✅ 清理孤立資料（需確認）
6. ⚠️  **清理相關的 NAS 檔案（功能描述中提到，但代碼未實現）**

**執行方式**：
```bash
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
```

**檢查邏輯**：

1. **孤立 Jobs**：
   ```python
   # 資料庫中有此 Job
   db_jobs = JenkinsJob.objects.filter(server=server)
   
   # 但 Jenkins API 沒有此 Job
   jenkins_jobs = client.get_all_jobs()
   jenkins_job_names = {job['name'] for job in jenkins_jobs}
   
   # 孤立的 = 資料庫有，但 Jenkins 沒有
   if job.name not in jenkins_job_names:
       # 標記為孤立
   ```

2. **孤立 Builds**：
   ```python
   # 資料庫中有此 Build
   db_builds = JenkinsBuild.objects.filter(job=job)
   
   # 但 Jenkins API 沒有此 Build
   jenkins_builds = client.get_job_builds(job.name, limit=100)
   jenkins_build_numbers = {b.get('number') for b in jenkins_builds}
   
   # 孤立的 = 資料庫有，但 Jenkins 沒有
   if build.build_number not in jenkins_build_numbers:
       # 標記為孤立
   ```

**刪除邏輯**：
```python
with transaction.atomic():
    # 刪除孤立的 Builds（單獨的 Builds）
    build_ids = [b['build_id'] for b in orphaned_builds]
    JenkinsBuild.objects.filter(id__in=build_ids).delete()
    
    # 刪除孤立的 Jobs（會級聯刪除相關 Builds）
    job_ids = [j['job_id'] for j in orphaned_jobs]
    JenkinsJob.objects.filter(id__in=job_ids).delete()
```

**⚠️  重要發現：未實現 NAS 檔案清理**

腳本描述中提到「清理相關的 NAS 檔案」，但代碼中 **沒有實現**：
- 刪除孤立 Build 時，**不會刪除** NAS 上對應的 Workspace 資料夾
- 這會導致 NAS 上累積大量無用的 Workspace 檔案

---

### 3. NAS Workspace 存儲結構

根據 `JenkinsStorageService` 分析：

**NAS 路徑結構**：
```
/mnt/mdt/jenkins/
├── {jenkins_server_ip}/
│   ├── {job_name}/
│   │   ├── {build_number}/
│   │   │   ├── workspace/
│   │   │   │   └── [檔案和資料夾]
│   │   │   └── metadata.json
```

**範例**：
```
/mnt/mdt/jenkins/10.252.170.10/MyProject_Build/123/workspace/
```

**資料庫記錄（JenkinsBuild）**：
```python
class JenkinsBuild(models.Model):
    workspace_path = models.CharField(max_length=1000, blank=True)  # NAS 上的路徑
    workspace_size = models.BigIntegerField(default=0)              # 大小（bytes）
    workspace_stored_at = models.DateTimeField(null=True)          # 存儲時間
    is_workspace_stored = models.BooleanField(default=False)       # 是否已存儲
```

---

## 🔍 問題識別

### 問題 1：無定時自動清理任務

**現狀**：
- ❌ 沒有 Celery 定時任務自動清理孤立資料
- ⚠️  需要手動執行腳本
- ⚠️  容易遺忘，導致資料庫累積無用記錄

**影響**：
- 資料庫會持續增長（JenkinsJob, JenkinsBuild）
- 查詢效能下降
- 儲存空間浪費

---

### 問題 2：NAS 檔案未被清理

**現狀**：
- ❌ 刪除孤立 Build 時，**不會刪除** NAS 上的 Workspace 資料夾
- ❌ `cleanup_orphaned_jenkins_data.py` 描述提到此功能，但 **未實現**

**影響範例**：

假設有一個 Build：
1. Jenkins 上：`MyProject_Build #123` （已存在）
2. 資料庫中：`JenkinsBuild(build_number=123, workspace_path='/mnt/mdt/jenkins/...')` （已存在）
3. NAS 上：`/mnt/mdt/jenkins/10.252.170.10/MyProject_Build/123/` （已存儲，5 GB）

**刪除流程：**
- Jenkins 上：該 Job 被刪除
- 執行清理腳本：
  - ✅ 資料庫中的 `JenkinsJob` 被刪除
  - ✅ 資料庫中的 `JenkinsBuild(build_number=123)` 被級聯刪除
  - ❌ NAS 上的 `/mnt/mdt/jenkins/.../123/` **仍然存在**（5 GB 浪費）

**長期影響**：
- NAS 空間持續被佔用
- 大量 orphaned 資料夾累積
- 需要手動檢查和刪除

---

### 問題 3：清理條件可能過於保守

**現有限制**：
```python
# 只檢查最近 100 個 Builds
jenkins_builds = client.get_job_builds(job.name, limit=100)
```

**潛在問題**：
- 如果一個 Job 有超過 100 個 Builds，舊的 Builds 不會被檢查
- 舊的孤立 Builds 可能被遺漏

---

## 📋 規劃方案

### 方案 A：創建自動清理 Celery 任務（推薦）

#### 任務 1：`cleanup_orphaned_jenkins_data_task`

**功能**：
- 自動檢查並清理孤立的 Jobs 和 Builds
- 同時清理對應的 NAS Workspace 資料夾
- 提供備份功能
- 記錄詳細日誌

**執行頻率**：
- **建議**：每天凌晨 3:00 執行（低峰期）
- 或每週一次（視資料增長速度）

**清理邏輯**：

```python
@shared_task(
    bind=True,
    name='api.tasks.cleanup_orphaned_jenkins_data_task',
    max_retries=2,
    default_retry_delay=1800,  # 失敗後 30 分鐘重試
    time_limit=7200,  # 硬限制 2 小時
    soft_time_limit=6600  # 軟限制 1.8 小時
)
def cleanup_orphaned_jenkins_data_task(self, backup=True, dry_run=False, server_id=None):
    """
    自動清理孤立的 Jenkins 資料（Jobs, Builds, NAS 檔案）
    
    執行步驟：
    1. 檢查孤立的 Jobs
    2. 檢查孤立的 Builds
    3. 備份要刪除的資料
    4. 刪除資料庫記錄
    5. ⭐ 清理 NAS 上對應的 Workspace 資料夾
    6. 記錄詳細統計和日誌
    
    Args:
        backup: 是否備份要刪除的資料（預設 True）
        dry_run: 試運行模式（只檢查，不刪除）（預設 False）
        server_id: 只處理特定 Server（可選）
        
    Returns:
        dict: {
            'success': bool,
            'total_jobs': int,
            'total_builds': int,
            'orphaned_jobs': int,
            'orphaned_builds': int,
            'deleted_jobs': int,
            'deleted_builds': int,
            'deleted_nas_folders': int,
            'freed_space': int,  # Bytes
            'duration': float,
            'backup_file': str,
        }
    """
    # 實現邏輯（見後續章節）
    pass
```

**清理 NAS 檔案的實現**：

```python
def cleanup_nas_workspace(self, build):
    """
    清理 Build 對應的 NAS Workspace 資料夾
    
    Args:
        build: JenkinsBuild 實例
        
    Returns:
        dict: {
            'success': bool,
            'folder_path': str,
            'size_freed': int,  # Bytes
            'error': str,
        }
    """
    if not build.is_workspace_stored or not build.workspace_path:
        return {'success': True, 'size_freed': 0, 'message': 'No workspace stored'}
    
    folder_path = build.workspace_path
    
    try:
        # 檢查路徑是否存在
        if not os.path.exists(folder_path):
            logger.warning(f"Workspace path does not exist: {folder_path}")
            return {'success': True, 'size_freed': 0, 'message': 'Path not found'}
        
        # 計算大小
        size_freed = get_folder_size(folder_path)
        
        # 刪除資料夾
        import shutil
        shutil.rmtree(folder_path)
        
        logger.info(f"✅ Deleted NAS workspace: {folder_path} ({size_freed / 1024 / 1024:.1f} MB)")
        
        return {
            'success': True,
            'folder_path': folder_path,
            'size_freed': size_freed,
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to delete NAS workspace {folder_path}: {e}", exc_info=True)
        return {
            'success': False,
            'folder_path': folder_path,
            'error': str(e),
        }

def get_folder_size(path):
    """計算資料夾大小（遞歸）"""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if os.path.exists(filepath):
                total_size += os.path.getsize(filepath)
    return total_size
```

**完整清理流程**：

```python
# 1. 查找孤立 Builds
orphaned_builds = find_orphaned_builds()  # 返回 Build 實例列表

# 2. 刪除前備份（記錄 workspace_path）
if backup:
    backup_data = {
        'builds': [
            {
                'id': b.id,
                'job_name': b.job.name,
                'build_number': b.build_number,
                'workspace_path': b.workspace_path,
                'workspace_size': b.workspace_size,
            }
            for b in orphaned_builds
        ]
    }
    save_backup(backup_data)

# 3. 先清理 NAS 檔案，再刪除資料庫記錄
total_freed = 0
deleted_folders = 0

for build in orphaned_builds:
    # 清理 NAS
    result = cleanup_nas_workspace(build)
    if result['success']:
        total_freed += result.get('size_freed', 0)
        deleted_folders += 1

# 4. 刪除資料庫記錄（事務）
with transaction.atomic():
    build_ids = [b.id for b in orphaned_builds]
    deleted_count = JenkinsBuild.objects.filter(id__in=build_ids).delete()

# 5. 記錄統計
logger.info(f"✅ Cleanup complete: {deleted_count[0]} builds, {deleted_folders} NAS folders, {total_freed / 1024 / 1024:.1f} MB freed")
```

---

#### 任務 2：`cleanup_old_jenkins_builds_task`

**功能**：
- 清理過舊的 Builds（例如超過 90 天）
- 同時清理對應的 NAS Workspace

**執行頻率**：
- 每週一次

**清理規則**：
```python
# 只保留最近 N 天的 Builds
cutoff_date = timezone.now() - timedelta(days=90)

old_builds = JenkinsBuild.objects.filter(
    build_timestamp__lt=cutoff_date,
    is_workspace_stored=True  # 只清理已存儲的（節省 NAS 空間）
)

# 清理邏輯與 cleanup_orphaned_jenkins_data_task 類似
```

---

### 方案 B：增強現有手動腳本

如果不想創建定時任務，可以增強現有腳本：

#### 改進點 1：實現 NAS 檔案清理

在 `cleanup_orphaned_jenkins_data.py` 中添加：

```python
def cleanup_nas_workspaces(self):
    """清理孤立 Builds 的 NAS Workspace 資料夾"""
    logger.info("\n" + "="*60)
    logger.info("🗑️  階段 5：清理 NAS Workspace 資料夾")
    logger.info("="*60)
    
    total_freed = 0
    deleted_folders = 0
    
    for build_info in self.stats['orphaned_builds']:
        build = JenkinsBuild.objects.get(id=build_info['build_id'])
        
        if not build.is_workspace_stored:
            continue
        
        result = self._cleanup_nas_folder(build.workspace_path)
        if result['success']:
            total_freed += result['size_freed']
            deleted_folders += 1
    
    self.stats['freed_space'] = total_freed
    logger.info(f"✅ 清理完成：{deleted_folders} 個資料夾，釋放 {total_freed / 1024 / 1024:.1f} MB")
```

#### 改進點 2：增加 NAS 空間統計

```python
def analyze_nas_usage(self):
    """分析 NAS Workspace 使用情況"""
    logger.info("\n" + "="*60)
    logger.info("📊 NAS Workspace 使用分析")
    logger.info("="*60)
    
    # 統計所有已存儲的 Builds
    stored_builds = JenkinsBuild.objects.filter(is_workspace_stored=True)
    total_size = stored_builds.aggregate(total=models.Sum('workspace_size'))['total'] or 0
    
    logger.info(f"已存儲 Builds: {stored_builds.count()}")
    logger.info(f"總佔用空間: {total_size / 1024 / 1024 / 1024:.2f} GB")
    
    # 分析可清理空間
    orphaned_size = sum(b.get('workspace_size', 0) for b in self.stats['orphaned_builds'])
    logger.info(f"可清理空間: {orphaned_size / 1024 / 1024:.2f} MB")
```

---

## 🎯 建議實施步驟

### 第一階段：測試現有腳本（1-2 天）

1. **乾運行測試**：
   ```bash
   docker exec nt-django python cleanup_orphaned_jenkins_data.py --dry-run
   ```

2. **備份並執行清理**：
   ```bash
   docker exec nt-django python cleanup_orphaned_jenkins_data.py --backup
   ```

3. **驗證結果**：
   - 檢查資料庫記錄是否正確刪除
   - 確認沒有誤刪

---

### 第二階段：實現 NAS 檔案清理（3-5 天）

1. **在手動腳本中實現 NAS 清理功能**：
   - 添加 `cleanup_nas_workspaces()` 方法
   - 添加 `_cleanup_nas_folder()` 輔助方法
   - 添加空間統計功能

2. **測試 NAS 清理**：
   ```bash
   # 乾運行（不刪除 NAS 檔案）
   docker exec nt-django python cleanup_orphaned_jenkins_data.py --dry-run
   
   # 執行清理（包含 NAS）
   docker exec nt-django python cleanup_orphaned_jenkins_data.py --backup
   ```

3. **驗證**：
   - 確認 NAS 資料夾被正確刪除
   - 確認 `freed_space` 統計正確

---

### 第三階段：創建 Celery 定時任務（5-7 天）

1. **創建任務**：
   - 在 `api/tasks.py` 中添加 `cleanup_orphaned_jenkins_data_task`
   - 在 `api/tasks.py` 中添加 `cleanup_old_jenkins_builds_task`

2. **配置調度**：
   ```python
   # backend/network_toolbox/celery.py
   
   app.conf.beat_schedule = {
       # ...其他任務...
       
       'cleanup-orphaned-jenkins-data-daily': {
           'task': 'api.tasks.cleanup_orphaned_jenkins_data_task',
           'schedule': crontab(hour=3, minute=0),  # 每天凌晨 3:00
           'kwargs': {'backup': True, 'dry_run': False},
       },
       
       'cleanup-old-jenkins-builds-weekly': {
           'task': 'api.tasks.cleanup_old_jenkins_builds_task',
           'schedule': crontab(day_of_week=1, hour=2, minute=0),  # 每週一凌晨 2:00
           'kwargs': {'days': 90, 'backup': True},
       },
   }
   ```

3. **測試定時任務**：
   ```bash
   # 手動執行測試
   docker exec nt-django python manage.py shell -c "
   from api.tasks import cleanup_orphaned_jenkins_data_task
   result = cleanup_orphaned_jenkins_data_task.apply(kwargs={'dry_run': True})
   print(result.get())
   "
   ```

---

### 第四階段：監控和優化（持續）

1. **添加監控指標**：
   - 孤立資料數量趨勢
   - NAS 空間使用趨勢
   - 清理任務執行成功率

2. **優化清理策略**：
   - 根據實際使用調整 `limit=100` 限制
   - 調整執行頻率
   - 調整保留天數

3. **錯誤處理**：
   - 添加更詳細的錯誤日誌
   - 自動重試機制
   - 失敗通知（Email/Slack）

---

## ⚠️  風險和注意事項

### 風險 1：誤刪重要資料

**緩解措施**：
- ✅ 預設啟用備份功能
- ✅ 乾運行模式測試
- ✅ 只刪除確定孤立的資料（雙重確認）

### 風險 2：NAS 檔案刪除失敗

**可能原因**：
- 權限不足
- 檔案正在使用
- 網路問題

**緩解措施**：
- 先刪除 NAS 檔案，再刪除資料庫記錄
- 錯誤時跳過，記錄日誌
- 提供手動清理列表

### 風險 3：執行時間過長

**緩解措施**：
- 設定 `time_limit` 和 `soft_time_limit`
- 分批處理（每次最多處理 N 個）
- 在低峰期執行

---

## 📈 預期效益

### 資料庫優化

- **減少記錄數**：孤立 Jobs/Builds 會被定期清理
- **提升查詢效能**：減少無效記錄掃描
- **降低儲存成本**：減少資料庫體積

### NAS 空間節省

假設平均每個 Build Workspace 5 GB，每天產生 10 個孤立 Builds：
- **每天節省**：50 GB
- **每月節省**：1.5 TB
- **每年節省**：18 TB

### 維護成本降低

- **自動化**：無需手動執行清理腳本
- **可視化**：通過日誌和監控了解清理情況
- **可靠性**：定期執行，避免遺忘

---

## 🔗 相關文件

- `/backend/api/tasks.py` - Celery 定時任務定義
- `/backend/cleanup_orphaned_jenkins_data.py` - 現有手動清理腳本
- `/backend/library/services/jenkins_storage_service.py` - Jenkins Workspace 存儲服務
- `/backend/api/models.py` - Jenkins 資料模型（JenkinsServer, JenkinsJob, JenkinsBuild）

---

## 📝 總結

### 現狀

- ✅ 有手動清理腳本（`cleanup_orphaned_jenkins_data.py`）
- ❌ 沒有自動定時清理任務
- ❌ NAS 檔案未被清理（功能未實現）

### 規劃

**優先級 1**（短期）：
1. 實現 NAS 檔案清理功能
2. 測試並驗證清理邏輯

**優先級 2**（中期）：
1. 創建 Celery 定時清理任務
2. 配置自動調度

**優先級 3**（長期）：
1. 添加監控和告警
2. 優化清理策略

### 下一步行動

1. ✅ 完成此分析文檔
2. ⏳ 等待確認是否執行實施
3. ⏳ 開始第一階段測試

---

**文檔版本**: 1.0  
**最後更新**: 2025-11-24  
**作者**: AI Assistant  
**審核狀態**: 待審核
