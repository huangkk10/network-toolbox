# NAS Jenkins Storage 清理任務規劃

## 📋 任務概述

**目標**：清理 NAS 路徑 `\\10.250.0.1\mdt\Team\PQ1-3\tool\jenkins_test_storage` 底下，各個 Jenkins Server 資料夾中超過一個月的檔案或資料夾。

**掛載路徑**：`/mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage`（Docker 容器內）

**執行週期**：每週日凌晨 3:00

**CPU 限制**：執行時 CPU 使用率不得超過 80%

---

## 🗂️ 目標路徑結構

```
\\10.250.0.1\mdt\Team\PQ1-3\tool\jenkins_test_storage\
├── {jenkins_server_ip_1}/
│   ├── {job_name_1}/
│   │   ├── {build_number_1}/
│   │   │   ├── workspace.zip
│   │   │   ├── console.log
│   │   │   └── ...
│   │   ├── {build_number_2}/
│   │   └── ...
│   ├── {job_name_2}/
│   └── ...
├── {jenkins_server_ip_2}/
│   └── ...
└── ...
```

**對應的 Docker 容器內路徑**：
```
/mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/
├── 10.252.170.10/
├── 10.252.170.187/
└── ...
```

---

## ⚙️ 清理策略

### 1. 清理範圍

| 層級 | 路徑模式 | 清理對象 | 說明 |
|------|----------|----------|------|
| Level 1 | `{base_path}/{jenkins_ip}/` | Jenkins Server 資料夾 | 檢查但不刪除空目錄 |
| Level 2 | `{base_path}/{jenkins_ip}/{job_name}/` | Job 資料夾 | 檢查但不刪除空目錄 |
| Level 3 | `{base_path}/{jenkins_ip}/{job_name}/{build_number}/` | **Build 資料夾** | ✅ 主要清理目標 |

### 2. 清理規則

```python
# 清理條件
CLEANUP_CONFIG = {
    'max_age_days': 30,              # 超過 30 天的 Build 資料夾
    'cleanup_empty_dirs': True,      # 清理完 Builds 後刪除空的 Job 資料夾
    'cleanup_empty_server_dirs': False,  # 不刪除空的 Server 資料夾（保留結構）
    'dry_run': False,                # 正式執行模式（True = 只檢查不刪除）
}
```

### 3. 判斷檔案/資料夾年齡的方式

```python
import os
from datetime import datetime, timedelta

def get_folder_age_days(folder_path):
    """
    取得資料夾的年齡（天數）
    使用資料夾的修改時間 (mtime) 作為判斷依據
    """
    try:
        mtime = os.path.getmtime(folder_path)
        modified_time = datetime.fromtimestamp(mtime)
        age = datetime.now() - modified_time
        return age.days
    except OSError:
        return -1  # 無法存取

def should_cleanup(folder_path, max_age_days=30):
    """判斷是否應該清理"""
    age_days = get_folder_age_days(folder_path)
    return age_days > max_age_days
```

---

## 🖥️ CPU 控制機制

### 1. CPU 監控策略

```python
import psutil
import time

class CPUAwareCleanup:
    """CPU 感知的清理器"""
    
    def __init__(
        self,
        cpu_high_threshold=80.0,    # CPU 使用率上限
        cpu_low_threshold=60.0,     # CPU 恢復執行閾值
        check_interval=5,           # CPU 檢查間隔（秒）
        max_wait_seconds=300,       # 最大等待時間（5 分鐘）
        batch_size=10,              # 每批次處理的資料夾數量
        batch_delay=2.0             # 批次間延遲（秒）
    ):
        self.cpu_high_threshold = cpu_high_threshold
        self.cpu_low_threshold = cpu_low_threshold
        self.check_interval = check_interval
        self.max_wait_seconds = max_wait_seconds
        self.batch_size = batch_size
        self.batch_delay = batch_delay
    
    def get_cpu_usage(self):
        """取得當前 CPU 使用率"""
        return psutil.cpu_percent(interval=1)
    
    def wait_for_cpu(self):
        """
        等待 CPU 使用率降低
        
        Returns:
            bool: True = CPU 已降低，可繼續執行
                  False = 超時，應跳過本次處理
        """
        total_waited = 0
        
        while total_waited < self.max_wait_seconds:
            cpu_usage = self.get_cpu_usage()
            
            if cpu_usage < self.cpu_low_threshold:
                return True
            
            logger.info(
                f'[CPU Aware] CPU 使用率 {cpu_usage:.1f}% > {self.cpu_high_threshold}%，'
                f'等待 {self.check_interval} 秒...'
            )
            
            time.sleep(self.check_interval)
            total_waited += self.check_interval
        
        logger.warning(
            f'[CPU Aware] 等待 CPU 超時 ({self.max_wait_seconds} 秒)，跳過本次清理'
        )
        return False
    
    def should_pause(self):
        """檢查是否需要暫停（CPU 過高）"""
        cpu_usage = self.get_cpu_usage()
        return cpu_usage > self.cpu_high_threshold
```

### 2. 批次處理策略

為了避免大量 I/O 操作造成 CPU 飆高，採用批次處理：

```python
def cleanup_with_batching(self, folders_to_delete):
    """
    批次清理資料夾，每批次後檢查 CPU
    """
    deleted_count = 0
    batch_count = 0
    
    for i, folder in enumerate(folders_to_delete):
        # 每 N 個資料夾檢查一次 CPU
        if i > 0 and i % self.batch_size == 0:
            batch_count += 1
            
            # 批次間延遲
            time.sleep(self.batch_delay)
            
            # 檢查 CPU
            if self.should_pause():
                logger.info(f'[Batch {batch_count}] CPU 過高，暫停處理...')
                if not self.wait_for_cpu():
                    # 超時，結束本次任務
                    break
        
        # 執行刪除
        try:
            shutil.rmtree(folder)
            deleted_count += 1
        except Exception as e:
            logger.error(f'刪除失敗 {folder}: {e}')
    
    return deleted_count
```

---

## 📅 Celery 排程配置

### 任務定義（`backend/api/tasks.py`）

```python
@shared_task(
    bind=True,
    name='api.tasks.cleanup_old_nas_jenkins_storage_task',
    max_retries=2,
    default_retry_delay=1800,     # 30 分鐘後重試
    time_limit=14400,             # 硬限制 4 小時
    soft_time_limit=12600         # 軟限制 3.5 小時
)
def cleanup_old_nas_jenkins_storage_task(
    self,
    max_age_days=30,
    dry_run=False,
    cpu_high_threshold=80.0,
    cpu_low_threshold=60.0,
    batch_size=10,
    batch_delay=2.0
):
    """
    清理 NAS 上超過指定天數的 Jenkins 存儲資料夾
    
    此任務直接掃描 NAS 檔案系統，清理過舊的 Build 資料夾。
    不依賴資料庫記錄，確保能清理到所有舊檔案。
    
    Args:
        max_age_days (int): 超過此天數的資料夾將被清理（預設 30 天）
        dry_run (bool): 試運行模式，只掃描不刪除（預設 False）
        cpu_high_threshold (float): CPU 使用率上限，超過則暫停（預設 80%）
        cpu_low_threshold (float): CPU 恢復執行的閾值（預設 60%）
        batch_size (int): 每批次處理的資料夾數量（預設 10）
        batch_delay (float): 批次間延遲秒數（預設 2.0）
    
    Returns:
        dict: 執行結果統計
            {
                'success': bool,
                'servers_scanned': int,
                'jobs_scanned': int,
                'builds_scanned': int,
                'builds_deleted': int,
                'space_freed_bytes': int,
                'empty_jobs_deleted': int,
                'cpu_pauses': int,
                'errors': int,
                'duration': float
            }
    """
    # 實現邏輯見下方章節
    pass
```

### Celery Beat 排程（`backend/network_toolbox/celery.py`）

```python
# 任務 XX：NAS Jenkins Storage 清理（每週日凌晨 3 點）
'cleanup-old-nas-jenkins-storage-weekly': {
    'task': 'api.tasks.cleanup_old_nas_jenkins_storage_task',
    'schedule': crontab(hour=3, minute=0, day_of_week=0),  # 週日 03:00
    'kwargs': {
        'max_age_days': 30,           # 清理超過 30 天的資料
        'dry_run': False,             # 正式執行模式
        'cpu_high_threshold': 80.0,   # CPU 上限 80%
        'cpu_low_threshold': 60.0,    # CPU 恢復閾值 60%
        'batch_size': 10,             # 每批 10 個資料夾
        'batch_delay': 2.0            # 批次間隔 2 秒
    },
    'options': {
        'expires': 14400,   # 任務超時 4 小時
    }
},
```

---

## 🔧 完整任務實現

```python
import os
import time
import shutil
import logging
import psutil
from datetime import datetime, timedelta
from pathlib import Path
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


def get_folder_size(folder_path):
    """計算資料夾總大小（bytes）"""
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(folder_path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    try:
                        total_size += os.path.getsize(filepath)
                    except OSError:
                        pass
    except Exception as e:
        logger.error(f"計算資料夾大小失敗 {folder_path}: {e}")
    return total_size


def get_folder_mtime(folder_path):
    """取得資料夾的最後修改時間"""
    try:
        return datetime.fromtimestamp(os.path.getmtime(folder_path))
    except OSError:
        return None


def format_size(size_bytes):
    """格式化檔案大小顯示"""
    if size_bytes >= 1024 * 1024 * 1024:
        return f"{size_bytes / 1024 / 1024 / 1024:.2f} GB"
    elif size_bytes >= 1024 * 1024:
        return f"{size_bytes / 1024 / 1024:.2f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes} Bytes"


@shared_task(
    bind=True,
    name='api.tasks.cleanup_old_nas_jenkins_storage_task',
    max_retries=2,
    default_retry_delay=1800,
    time_limit=14400,
    soft_time_limit=12600
)
def cleanup_old_nas_jenkins_storage_task(
    self,
    max_age_days=30,
    dry_run=False,
    cpu_high_threshold=80.0,
    cpu_low_threshold=60.0,
    batch_size=10,
    batch_delay=2.0,
    max_cpu_wait_seconds=300
):
    """
    清理 NAS 上超過指定天數的 Jenkins 存儲資料夾
    
    直接掃描 NAS 檔案系統，清理過舊的 Build 資料夾。
    具備 CPU 監控功能，確保不會造成系統過載。
    """
    start_time = time.time()
    
    # NAS Jenkins 存儲基礎路徑
    base_path = getattr(
        settings, 
        'JENKINS_STORAGE_BASE_PATH', 
        '/mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage'
    )
    
    logger.info('=' * 70)
    logger.info('[Celery] 🧹 開始 NAS Jenkins Storage 清理任務')
    logger.info('=' * 70)
    logger.info(f'[Celery] 📂 目標路徑: {base_path}')
    logger.info(f'[Celery] 📆 清理條件: 超過 {max_age_days} 天的 Build 資料夾')
    logger.info(f'[Celery] 🖥️  CPU 上限: {cpu_high_threshold}%, 恢復閾值: {cpu_low_threshold}%')
    logger.info(f'[Celery] 📦 批次大小: {batch_size}, 批次間隔: {batch_delay}s')
    
    if dry_run:
        logger.warning('[Celery] ⚠️  試運行模式：只掃描不刪除')
    
    # 統計數據
    stats = {
        'success': True,
        'base_path': base_path,
        'max_age_days': max_age_days,
        'dry_run': dry_run,
        'servers_scanned': 0,
        'jobs_scanned': 0,
        'builds_scanned': 0,
        'builds_to_delete': 0,
        'builds_deleted': 0,
        'space_freed_bytes': 0,
        'empty_jobs_deleted': 0,
        'cpu_pauses': 0,
        'cpu_timeout_skips': 0,
        'errors': 0,
        'server_details': [],
        'duration': 0
    }
    
    cutoff_date = datetime.now() - timedelta(days=max_age_days)
    logger.info(f'[Celery] ⏰ 截止日期: {cutoff_date.strftime("%Y-%m-%d %H:%M:%S")}')
    
    try:
        # 檢查基礎路徑是否存在
        if not os.path.exists(base_path):
            logger.error(f'[Celery] ❌ 基礎路徑不存在: {base_path}')
            stats['success'] = False
            stats['error_message'] = f'Path not found: {base_path}'
            return stats
        
        # 收集要刪除的資料夾
        folders_to_delete = []
        
        # 掃描所有 Jenkins Server 資料夾
        server_dirs = [
            d for d in os.listdir(base_path)
            if os.path.isdir(os.path.join(base_path, d))
        ]
        
        logger.info(f'[Celery] 🖥️  找到 {len(server_dirs)} 個 Jenkins Server 資料夾')
        stats['servers_scanned'] = len(server_dirs)
        
        for server_dir in server_dirs:
            server_path = os.path.join(base_path, server_dir)
            
            server_stats = {
                'server': server_dir,
                'jobs_scanned': 0,
                'builds_scanned': 0,
                'builds_to_delete': 0,
                'space_to_free': 0,
                'errors': 0
            }
            
            logger.info(f'[Celery] 📁 掃描 Server: {server_dir}')
            
            # 掃描 Job 資料夾
            try:
                job_dirs = [
                    d for d in os.listdir(server_path)
                    if os.path.isdir(os.path.join(server_path, d))
                ]
            except PermissionError as e:
                logger.error(f'[Celery]   ❌ 無法存取 Server 資料夾: {e}')
                stats['errors'] += 1
                server_stats['errors'] += 1
                stats['server_details'].append(server_stats)
                continue
            
            server_stats['jobs_scanned'] = len(job_dirs)
            stats['jobs_scanned'] += len(job_dirs)
            
            for job_dir in job_dirs:
                job_path = os.path.join(server_path, job_dir)
                
                # 掃描 Build 資料夾
                try:
                    build_dirs = [
                        d for d in os.listdir(job_path)
                        if os.path.isdir(os.path.join(job_path, d))
                    ]
                except PermissionError as e:
                    logger.warning(f'[Celery]     ⚠️  無法存取 Job 資料夾 {job_dir}: {e}')
                    stats['errors'] += 1
                    server_stats['errors'] += 1
                    continue
                
                for build_dir in build_dirs:
                    build_path = os.path.join(job_path, build_dir)
                    stats['builds_scanned'] += 1
                    server_stats['builds_scanned'] += 1
                    
                    # 取得資料夾修改時間
                    mtime = get_folder_mtime(build_path)
                    
                    if mtime is None:
                        logger.warning(f'[Celery]       ⚠️  無法取得修改時間: {build_path}')
                        continue
                    
                    # 判斷是否超過保留期限
                    if mtime < cutoff_date:
                        folder_size = get_folder_size(build_path)
                        age_days = (datetime.now() - mtime).days
                        
                        folders_to_delete.append({
                            'path': build_path,
                            'size': folder_size,
                            'age_days': age_days,
                            'mtime': mtime,
                            'server': server_dir,
                            'job': job_dir,
                            'build': build_dir
                        })
                        
                        stats['builds_to_delete'] += 1
                        server_stats['builds_to_delete'] += 1
                        server_stats['space_to_free'] += folder_size
            
            stats['server_details'].append(server_stats)
            
            if server_stats['builds_to_delete'] > 0:
                logger.info(
                    f'[Celery]   📊 {server_dir}: '
                    f'{server_stats["builds_to_delete"]} 個舊 Builds 待清理 '
                    f'({format_size(server_stats["space_to_free"])})'
                )
        
        # 統計掃描結果
        total_space = sum(f['size'] for f in folders_to_delete)
        logger.info('-' * 70)
        logger.info(f'[Celery] 📊 掃描結果統計:')
        logger.info(f'[Celery]   - 掃描 Servers: {stats["servers_scanned"]}')
        logger.info(f'[Celery]   - 掃描 Jobs: {stats["jobs_scanned"]}')
        logger.info(f'[Celery]   - 掃描 Builds: {stats["builds_scanned"]}')
        logger.info(f'[Celery]   - 待清理 Builds: {stats["builds_to_delete"]}')
        logger.info(f'[Celery]   - 預計釋放空間: {format_size(total_space)}')
        logger.info('-' * 70)
        
        # 執行清理（帶 CPU 監控）
        if folders_to_delete and not dry_run:
            logger.info('[Celery] 🚀 開始執行清理...')
            
            batch_count = 0
            for i, folder_info in enumerate(folders_to_delete):
                # 批次間 CPU 檢查
                if i > 0 and i % batch_size == 0:
                    batch_count += 1
                    
                    # 批次間延遲
                    time.sleep(batch_delay)
                    
                    # 檢查 CPU
                    cpu_usage = psutil.cpu_percent(interval=1)
                    
                    if cpu_usage > cpu_high_threshold:
                        stats['cpu_pauses'] += 1
                        logger.warning(
                            f'[Celery] ⏸️  批次 {batch_count}: CPU {cpu_usage:.1f}% > {cpu_high_threshold}%，暫停...'
                        )
                        
                        # 等待 CPU 降低
                        waited = 0
                        while waited < max_cpu_wait_seconds:
                            time.sleep(5)
                            waited += 5
                            cpu_usage = psutil.cpu_percent(interval=1)
                            
                            if cpu_usage < cpu_low_threshold:
                                logger.info(f'[Celery] ▶️  CPU 已降至 {cpu_usage:.1f}%，繼續執行')
                                break
                        else:
                            # 超時
                            stats['cpu_timeout_skips'] += 1
                            logger.error(
                                f'[Celery] ⏭️  等待 CPU 超時 ({max_cpu_wait_seconds}s)，'
                                f'跳過剩餘 {len(folders_to_delete) - i} 個資料夾'
                            )
                            break
                
                # 執行刪除
                try:
                    folder_path = folder_info['path']
                    folder_size = folder_info['size']
                    
                    shutil.rmtree(folder_path)
                    
                    stats['builds_deleted'] += 1
                    stats['space_freed_bytes'] += folder_size
                    
                    logger.debug(
                        f'[Celery]   ✅ 已刪除: {folder_info["server"]}/{folder_info["job"]}/#{folder_info["build"]} '
                        f'({folder_info["age_days"]} 天前, {format_size(folder_size)})'
                    )
                    
                except PermissionError as e:
                    stats['errors'] += 1
                    logger.error(f'[Celery]   ❌ 權限錯誤: {folder_info["path"]}: {e}')
                    
                except Exception as e:
                    stats['errors'] += 1
                    logger.error(f'[Celery]   ❌ 刪除失敗: {folder_info["path"]}: {e}')
        
        elif dry_run and folders_to_delete:
            # 試運行模式：列出將被刪除的資料夾
            logger.info('[Celery] 🔍 [DRY-RUN] 以下資料夾將被刪除:')
            for folder_info in folders_to_delete[:20]:  # 只顯示前 20 個
                logger.info(
                    f'[Celery]   - {folder_info["server"]}/{folder_info["job"]}/#{folder_info["build"]} '
                    f'({folder_info["age_days"]} 天前, {format_size(folder_info["size"])})'
                )
            
            if len(folders_to_delete) > 20:
                logger.info(f'[Celery]   ... 還有 {len(folders_to_delete) - 20} 個 (省略)')
        
        # 清理空的 Job 資料夾
        if not dry_run and stats['builds_deleted'] > 0:
            empty_jobs_deleted = cleanup_empty_job_folders(base_path)
            stats['empty_jobs_deleted'] = empty_jobs_deleted
            
            if empty_jobs_deleted > 0:
                logger.info(f'[Celery] 🗑️  已清理 {empty_jobs_deleted} 個空的 Job 資料夾')
        
        # 最終統計
        duration = time.time() - start_time
        stats['duration'] = duration
        
        logger.info('=' * 70)
        logger.info('[Celery] 🎉 NAS Jenkins Storage 清理任務完成')
        logger.info('=' * 70)
        logger.info(f'[Celery] 📊 最終統計:')
        logger.info(f'[Celery]   - 掃描 Servers: {stats["servers_scanned"]}')
        logger.info(f'[Celery]   - 掃描 Jobs: {stats["jobs_scanned"]}')
        logger.info(f'[Celery]   - 掃描 Builds: {stats["builds_scanned"]}')
        logger.info(f'[Celery]   - 待清理 Builds: {stats["builds_to_delete"]}')
        logger.info(f'[Celery]   - 已刪除 Builds: {stats["builds_deleted"]}')
        logger.info(f'[Celery]   - 釋放空間: {format_size(stats["space_freed_bytes"])}')
        
        if stats['empty_jobs_deleted'] > 0:
            logger.info(f'[Celery]   - 清理空 Job 資料夾: {stats["empty_jobs_deleted"]}')
        
        if stats['cpu_pauses'] > 0:
            logger.info(f'[Celery]   - CPU 暫停次數: {stats["cpu_pauses"]}')
        
        if stats['cpu_timeout_skips'] > 0:
            logger.warning(f'[Celery]   - CPU 超時跳過: {stats["cpu_timeout_skips"]}')
        
        if stats['errors'] > 0:
            logger.warning(f'[Celery]   - 錯誤數量: {stats["errors"]}')
        
        logger.info(f'[Celery]   - 總耗時: {duration:.2f} 秒')
        
        return stats
        
    except Exception as exc:
        logger.error('[Celery] 💥 NAS Jenkins Storage 清理任務異常', exc_info=True)
        
        try:
            raise self.retry(exc=exc, countdown=1800)
        except self.MaxRetriesExceededError:
            logger.error('[Celery] NAS 清理任務重試次數已達上限')
            duration = time.time() - start_time
            stats['success'] = False
            stats['duration'] = duration
            stats['error_message'] = str(exc)
            return stats


def cleanup_empty_job_folders(base_path):
    """
    清理空的 Job 資料夾
    
    在清理 Build 資料夾後，可能會留下空的 Job 資料夾，
    此函數會清理這些空資料夾以保持結構整潔。
    """
    deleted_count = 0
    
    try:
        for server_dir in os.listdir(base_path):
            server_path = os.path.join(base_path, server_dir)
            
            if not os.path.isdir(server_path):
                continue
            
            for job_dir in os.listdir(server_path):
                job_path = os.path.join(server_path, job_dir)
                
                if not os.path.isdir(job_path):
                    continue
                
                # 檢查是否為空資料夾
                if not os.listdir(job_path):
                    try:
                        os.rmdir(job_path)
                        deleted_count += 1
                        logger.debug(f'[Celery] 已刪除空 Job 資料夾: {job_path}')
                    except Exception as e:
                        logger.warning(f'[Celery] 刪除空資料夾失敗 {job_path}: {e}')
    
    except Exception as e:
        logger.error(f'[Celery] 清理空資料夾時發生錯誤: {e}')
    
    return deleted_count
```

---

## 🧪 測試計畫

### 1. 手動測試（Dry-Run 模式）

```bash
# 在 Django 容器中執行測試
docker exec nt-django python manage.py shell -c "
from api.tasks import cleanup_old_nas_jenkins_storage_task

# 試運行模式（只掃描不刪除）
result = cleanup_old_nas_jenkins_storage_task.apply(kwargs={
    'max_age_days': 30,
    'dry_run': True,
    'cpu_high_threshold': 80.0,
    'cpu_low_threshold': 60.0
}).get()

print('結果:', result)
"
```

### 2. 測試腳本（`backend/test_nas_cleanup.py`）

```python
#!/usr/bin/env python
"""
測試 NAS Jenkins Storage 清理任務
"""
import os
import sys
import django

# 設置 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from api.tasks import cleanup_old_nas_jenkins_storage_task


def test_dry_run():
    """測試 Dry-Run 模式"""
    print("=" * 60)
    print("🧪 測試 1: Dry-Run 模式（只掃描不刪除）")
    print("=" * 60)
    
    result = cleanup_old_nas_jenkins_storage_task.apply(kwargs={
        'max_age_days': 30,
        'dry_run': True
    }).get()
    
    print(f"✅ 掃描完成")
    print(f"   - Servers: {result['servers_scanned']}")
    print(f"   - Jobs: {result['jobs_scanned']}")
    print(f"   - Builds: {result['builds_scanned']}")
    print(f"   - 待清理: {result['builds_to_delete']}")
    
    return result


def test_cpu_monitoring():
    """測試 CPU 監控功能"""
    print("\n" + "=" * 60)
    print("🧪 測試 2: CPU 監控功能")
    print("=" * 60)
    
    import psutil
    
    cpu_usage = psutil.cpu_percent(interval=2)
    print(f"📊 當前 CPU 使用率: {cpu_usage:.1f}%")
    
    if cpu_usage > 80:
        print("⚠️  CPU 使用率較高，清理任務可能會暫停")
    else:
        print("✅ CPU 使用率正常，清理任務可正常執行")


if __name__ == '__main__':
    test_dry_run()
    test_cpu_monitoring()
```

### 3. 驗證排程配置

```bash
# 查看 Celery Beat 排程
docker exec nt-django python manage.py shell -c "
from django_celery_beat.models import PeriodicTask
tasks = PeriodicTask.objects.filter(name__icontains='nas-jenkins-storage')
for t in tasks:
    print(f'任務: {t.name}')
    print(f'  - 排程: {t.crontab or t.interval}')
    print(f'  - 啟用: {t.enabled}')
    print(f'  - 參數: {t.kwargs}')
"
```

---

## 📝 部署步驟

### 1. 添加任務代碼

將上述任務實現添加到 `backend/api/tasks.py`：
- `cleanup_old_nas_jenkins_storage_task` 函數
- `cleanup_empty_job_folders` 輔助函數

### 2. 更新 Celery Beat 排程

在 `backend/network_toolbox/celery.py` 的 `app.conf.beat_schedule` 中添加：

```python
# 任務 XX：NAS Jenkins Storage 清理（每週日凌晨 3 點）
'cleanup-old-nas-jenkins-storage-weekly': {
    'task': 'api.tasks.cleanup_old_nas_jenkins_storage_task',
    'schedule': crontab(hour=3, minute=0, day_of_week=0),  # 週日 03:00
    'kwargs': {
        'max_age_days': 30,
        'dry_run': False,
        'cpu_high_threshold': 80.0,
        'cpu_low_threshold': 60.0,
        'batch_size': 10,
        'batch_delay': 2.0
    },
    'options': {
        'expires': 14400,
    }
},
```

### 3. 重啟 Celery 服務

```bash
# 重啟 Django 容器（包含 Celery Worker 和 Beat）
docker compose restart django

# 查看日誌確認任務已載入
docker compose logs django | grep -i "nas-jenkins-storage"
```

### 4. 驗證任務註冊

```bash
# 查看已註冊的 Celery 任務
docker exec nt-django celery -A network_toolbox inspect registered | grep nas
```

### 5. 更新系統監控頁面任務名稱映射

為了讓新任務在**系統監控 Web 頁面**中顯示中文名稱，需要在 `backend/api/views/system.py` 的 `task_name_map` 中添加映射：

```python
# 在 recent_tasks() 函數中的 task_name_map 字典添加：
task_name_map = {
    # ... 現有映射 ...
    'api.tasks.cleanup_old_nas_jenkins_storage_task': 'NAS Jenkins 存儲清理',  # 🆕 新增
}
```

**修改位置**：`backend/api/views/system.py` 約第 427-440 行

---

## 📺 系統監控頁面顯示

新任務執行後，會在系統監控頁面（`/system-monitor`）中顯示：

### 顯示內容

| 欄位 | 說明 | 範例值 |
|------|------|--------|
| 任務名稱 | 中文顯示名稱 | `NAS Jenkins 存儲清理` |
| 狀態 | 執行狀態 | `成功` / `失敗` / `執行中` |
| 執行時間 | 任務開始時間 | `a few seconds ago` |
| 耗時 | 執行時長 | `45.2s` |
| 結果 | JSON 格式統計 | `{"success": true, "builds_deleted": 50, ...}` |

### 結果欄位說明

任務執行完成後，結果欄位會顯示完整統計：

```json
{
  "success": true,
  "servers_scanned": 5,
  "jobs_scanned": 120,
  "builds_scanned": 1500,
  "builds_deleted": 200,
  "space_freed_bytes": 5368709120,  // 約 5 GB
  "cpu_pauses": 2,
  "errors": 0,
  "duration": 180.5
}
```

### 任務執行趨勢圖

任務也會出現在「任務執行趨勢」圖表和「高頻任務 TOP 5」列表中（如果執行頻率足夠高）。

---

## ⚠️ 注意事項

### 1. 首次執行建議

- **先使用 Dry-Run 模式**：確認要清理的資料夾數量和空間大小
- **檢查 CPU 閾值設定**：根據伺服器實際情況調整
- **監控執行日誌**：`tail -f logs/django.log | grep "NAS Jenkins Storage"`

### 2. 執行時間選擇

- **週日凌晨 3 點**：避開一般工作時間
- **考慮其他任務**：
  - 01:00 - Jenkins 孤立資料清理
  - 02:00 - Jenkins 資料一致性驗證
  - **03:00 - NAS Storage 清理（本任務）**
  - 04:30 - DHCP Scope 同步
  - 05:00 - 清理舊 Jenkins Builds（月度）

### 3. 空間釋放預估

根據現有清理任務的經驗：
- 單個 Build 資料夾：10MB ~ 500MB
- 30 天以上的舊 Builds 可能佔用：數 GB ~ 數十 GB

### 4. 與現有任務的關係

| 現有任務 | 清理對象 | 執行週期 | 關係 |
|----------|----------|----------|------|
| `cleanup-orphaned-jenkins-data-weekly` | 資料庫孤立記錄 + NAS | 週日 01:00 | 清理 Jenkins 已刪除的 Builds |
| `cleanup-old-jenkins-builds-monthly` | 90 天前的 Builds | 每月 1 號 | 按資料庫記錄清理 |
| **本任務（新）** | NAS 上 30 天前的資料夾 | 週日 03:00 | **直接掃描 NAS，不依賴資料庫** |

**關鍵差異**：本任務直接掃描 NAS 檔案系統，可以清理到不在資料庫記錄中的「孤立」檔案。

---

## 📊 監控與告警

### 1. 日誌監控

```bash
# 查看任務執行日誌
tail -f logs/django.log | grep -E "(NAS Jenkins Storage|cleanup_old_nas)"

# 查看錯誤
grep -E "ERROR.*NAS|❌.*NAS" logs/django.log
```

### 2. 空間監控

```bash
# 檢查 NAS 使用空間
docker exec nt-django du -sh /mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/*

# 檢查總空間
docker exec nt-django df -h /mnt/mdt
```

### 3. 任務執行歷史

```bash
# 查看 Celery 任務結果
docker exec nt-django python manage.py shell -c "
from django_celery_results.models import TaskResult
results = TaskResult.objects.filter(
    task_name__icontains='nas_jenkins_storage'
).order_by('-date_done')[:5]

for r in results:
    print(f'{r.date_done}: {r.status}')
    print(f'  結果: {r.result[:200]}...' if r.result else '  無結果')
"
```

---

## 📅 更新日期

**最後更新**：2025-12-01

**規劃者**：AI Assistant

**狀態**：✅ 規劃完成，待實施
