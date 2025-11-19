# Jenkins Build 狀態未更新問題排查報告

## 🐛 問題描述

**現象**：Job `SAF7522_K07` 的 Build #35 在系統中顯示為 `SUCCESS`（綠色），但實際在 Jenkins 上是 `FAILURE`（紅色）。

**影響範圍**：所有已同步到系統中的 Builds，如果後續狀態改變（例如從 SUCCESS 變為 FAILURE），系統不會自動更新。

---

## 🔍 根本原因分析

### 1. 同步邏輯問題

**位置**：`backend/api/tasks.py` - `sync_jenkins_builds()` 函數

```python
# Line 1829-1842: 過濾已存在的 Builds
existing_build_numbers = set(
    JenkinsBuild.objects.filter(job=job)
    .values_list('build_number', flat=True)
)

new_builds = [
    b for b in jenkins_builds 
    if b.get('number') not in existing_build_numbers
]

# 如果沒有新 Builds，跳過這個 Job
if not new_builds:
    logger.debug(f'[Celery]     ⏭️  Job {job.name} 沒有新 Builds，跳過')
    continue
```

**問題**：
- ❌ 系統只會創建**新的** Builds
- ❌ 對於**已存在**的 Builds，即使 Jenkins 上的狀態改變，也不會更新
- ❌ 沒有機制檢查 Build 狀態是否發生變化

### 2. 觸發場景

**Build #35 的時間線**：

| 時間 | Jenkins 狀態 | 系統狀態 | 說明 |
|------|-------------|---------|------|
| T1: Build 開始 | `BUILDING` | - | Jenkins 開始執行 |
| T2: 首次同步 | `SUCCESS` | `SUCCESS` | ✅ 系統同步（可能是中間狀態） |
| T3: Build 實際完成 | `FAILURE` | `SUCCESS` | ❌ Jenkins 失敗，但系統未更新 |
| T4: 後續同步 | `FAILURE` | `SUCCESS` | ❌ 系統跳過已存在的 Build #35 |

**可能原因**：
1. **Jenkins API 延遲**：Build 正在運行時，API 可能返回不完整的狀態
2. **Build 狀態變化**：某些 Build 可能先顯示 SUCCESS，後來被標記為 FAILURE
3. **Post-build Actions**：某些測試或檢查在 Build 完成後執行，導致狀態改變

---

## 💡 解決方案

### 方案 1：增加狀態更新邏輯（推薦）

**修改策略**：
- 對已存在的 Builds，檢查狀態是否發生變化
- 如果狀態不同，更新資料庫
- 特別關注 `is_building=True` 的 Builds

**實施步驟**：

1. 修改 `sync_jenkins_builds()` 函數
2. 增加狀態比對邏輯
3. 更新已改變狀態的 Builds

**程式碼範例**：

```python
# 🆕 優化：不只創建新 Builds，也更新狀態改變的 Builds
existing_builds = JenkinsBuild.objects.filter(
    job=job,
    build_number__in=[b.get('number') for b in jenkins_builds]
).in_bulk(field_name='build_number')

for build_data in jenkins_builds:
    build_number = build_data.get('number')
    result = build_data.get('result')
    building = build_data.get('building', False)
    
    # 檢查 Build 是否已存在
    existing_build = existing_builds.get(build_number)
    
    if existing_build:
        # Build 已存在，檢查是否需要更新
        needs_update = False
        update_fields = []
        
        # 1. 如果狀態改變（最重要）
        if existing_build.result != result:
            existing_build.result = result
            update_fields.append('result')
            needs_update = True
            logger.info(
                f'[Celery]     🔄 Build 狀態改變: {job.name} #{build_number} '
                f'{existing_build.result} → {result}'
            )
        
        # 2. 如果 building 狀態改變
        if existing_build.is_building != building:
            existing_build.is_building = building
            update_fields.append('is_building')
            needs_update = True
        
        # 3. 如果 duration 改變（Build 完成後才有）
        duration = build_data.get('duration', 0)
        if duration > 0 and existing_build.duration != duration:
            existing_build.duration = duration
            update_fields.append('duration')
            needs_update = True
        
        # 執行更新
        if needs_update:
            existing_build.save(update_fields=update_fields)
            builds_updated += 1
            logger.info(f'[Celery]     ✅ 更新 Build: {job.name} #{build_number}')
            
            # 如果變成 FAILURE，同步 Pipeline Stages
            if result == 'FAILURE' and not existing_build.failed_stage:
                try:
                    failed_stages = client.get_failed_stages(job.name, build_number)
                    if failed_stages:
                        existing_build.pipeline_stages = failed_stages
                        first_failed = failed_stages[0]
                        existing_build.failed_stage = (
                            first_failed.get('stage_name') or 
                            first_failed.get('displayName') or 
                            first_failed.get('name')
                        )
                        existing_build.save(update_fields=['pipeline_stages', 'failed_stage'])
                        logger.info(f'[Celery]     🎯 同步失敗 Stage: {existing_build.failed_stage}')
                except Exception as e:
                    logger.error(f'[Celery]     ❌ 無法獲取 Pipeline Stages: {e}')
    else:
        # Build 不存在，創建新記錄
        # ... 現有的創建邏輯 ...
```

---

### 方案 2：定期重新同步指定 Builds

**適用場景**：
- 只需要修復特定的 Builds
- 不想修改核心同步邏輯

**實施步驟**：

1. 創建手動同步腳本
2. 指定 Job 和 Build 編號
3. 強制重新同步

**腳本範例**：

```python
# backend/force_resync_build.py
#!/usr/bin/env python3
"""
強制重新同步指定的 Jenkins Build

使用方式：
    docker exec nt-django python force_resync_build.py --job SAF7522_K07 --build 35
"""

import sys
import os
import django

sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.models import JenkinsJob, JenkinsBuild
from library.services.jenkins_client import JenkinsClient
import argparse

def resync_build(job_name, build_number):
    """重新同步指定的 Build"""
    try:
        # 查找 Job
        job = JenkinsJob.objects.get(name=job_name)
        server = job.server
        
        # 連接 Jenkins
        client = JenkinsClient(
            base_url=server.url,
            username=server.username,
            api_token=server.api_token
        )
        
        # 從 Jenkins 獲取 Build 資訊
        build_info = client.get_build_info(job_name, build_number)
        
        if not build_info:
            print(f"❌ 無法從 Jenkins 獲取 Build 資訊")
            return False
        
        # 查找或創建 Build
        build, created = JenkinsBuild.objects.get_or_create(
            job=job,
            build_number=build_number,
            defaults={
                'display_name': f'#{build_number}',
                'url': build_info.get('url', ''),
                'result': build_info.get('result', 'UNKNOWN'),
                'is_building': build_info.get('building', False),
                'duration': build_info.get('duration', 0),
            }
        )
        
        if not created:
            # 更新現有 Build
            old_result = build.result
            build.result = build_info.get('result', 'UNKNOWN')
            build.is_building = build_info.get('building', False)
            build.duration = build_info.get('duration', 0)
            build.save()
            
            print(f"✅ Build 已更新: {job_name} #{build_number}")
            print(f"   舊狀態: {old_result}")
            print(f"   新狀態: {build.result}")
            
            # 如果是 FAILURE，同步 Pipeline Stages
            if build.result == 'FAILURE':
                failed_stages = client.get_failed_stages(job_name, build_number)
                if failed_stages:
                    build.pipeline_stages = failed_stages
                    first_failed = failed_stages[0]
                    build.failed_stage = (
                        first_failed.get('stage_name') or 
                        first_failed.get('displayName') or 
                        first_failed.get('name')
                    )
                    build.save(update_fields=['pipeline_stages', 'failed_stage'])
                    print(f"   失敗 Stage: {build.failed_stage}")
        else:
            print(f"✅ Build 已創建: {job_name} #{build_number} ({build.result})")
        
        client.close()
        return True
        
    except JenkinsJob.DoesNotExist:
        print(f"❌ Job 不存在: {job_name}")
        return False
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        return False

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='強制重新同步 Jenkins Build')
    parser.add_argument('--job', required=True, help='Job 名稱')
    parser.add_argument('--build', required=True, type=int, help='Build 編號')
    
    args = parser.parse_args()
    
    print(f"\n{'=' * 60}")
    print(f"  強制重新同步 Jenkins Build")
    print(f"  Job: {args.job}")
    print(f"  Build: #{args.build}")
    print('=' * 60)
    
    success = resync_build(args.job, args.build)
    sys.exit(0 if success else 1)
```

**執行方式**：

```bash
# 修復 Build #35
docker exec nt-django python force_resync_build.py --job SAF7522_K07 --build 35
```

---

### 方案 3：定期檢查最近 Builds 的狀態

**適用場景**：
- 需要持續監控 Build 狀態
- 避免狀態不一致

**實施步驟**：

1. 創建新的 Celery 定時任務
2. 檢查最近 N 個 Builds 的狀態
3. 更新狀態不一致的 Builds

**程式碼範例**：

```python
# backend/api/tasks.py

@shared_task(
    bind=True,
    name='api.tasks.verify_recent_builds_status',
    max_retries=1,
    default_retry_delay=300
)
def verify_recent_builds_status(self, hours=24):
    """
    驗證最近 N 小時內的 Builds 狀態是否一致
    
    Args:
        hours: 檢查最近幾小時的 Builds（預設 24 小時）
    """
    from datetime import timedelta
    from django.utils import timezone
    
    logger.info(f'[Celery] 🔍 開始驗證最近 {hours} 小時的 Builds 狀態...')
    
    # 計算時間範圍
    cutoff_time = timezone.now() - timedelta(hours=hours)
    
    # 查詢最近的 Builds
    recent_builds = JenkinsBuild.objects.filter(
        build_timestamp__gte=cutoff_time
    ).select_related('job__server')
    
    updated_count = 0
    error_count = 0
    
    for build in recent_builds:
        try:
            server = build.job.server
            client = JenkinsClient(
                base_url=server.url,
                username=server.username,
                api_token=server.api_token
            )
            
            # 從 Jenkins 獲取當前狀態
            build_info = client.get_build_info(build.job.name, build.build_number)
            
            if build_info:
                jenkins_result = build_info.get('result')
                
                # 比對狀態
                if jenkins_result and build.result != jenkins_result:
                    old_result = build.result
                    build.result = jenkins_result
                    build.is_building = build_info.get('building', False)
                    build.duration = build_info.get('duration', 0)
                    build.save(update_fields=['result', 'is_building', 'duration'])
                    
                    logger.warning(
                        f'[Celery] 🔄 發現狀態不一致: {build.job.name} #{build.build_number} '
                        f'{old_result} → {jenkins_result}'
                    )
                    updated_count += 1
            
            client.close()
            
        except Exception as e:
            error_count += 1
            logger.error(f'[Celery] ❌ 驗證 Build 失敗: {build.job.name} #{build.build_number} - {e}')
    
    logger.info(f'[Celery] ✅ 驗證完成: 更新 {updated_count} 個 Builds, 錯誤 {error_count} 個')
    
    return {
        'success': True,
        'updated': updated_count,
        'errors': error_count
    }
```

**配置定時任務**：

```python
# backend/network_toolbox/celery.py

app.conf.beat_schedule = {
    # ... 其他任務 ...
    
    'verify-recent-builds-status': {
        'task': 'api.tasks.verify_recent_builds_status',
        'schedule': crontab(minute='*/30'),  # 每 30 分鐘檢查一次
        'args': (24,),  # 檢查最近 24 小時
    },
}
```

---

## 🎯 建議實施順序

### 第一步：立即修復 Build #35（方案 2）

```bash
# 1. 創建修復腳本
docker exec nt-django bash -c "cat > /app/force_resync_build.py << 'EOF'
#!/usr/bin/env python3
# ... 腳本內容 ...
EOF"

# 2. 執行修復
docker exec nt-django python force_resync_build.py --job SAF7522_K07 --build 35

# 3. 驗證結果
# 檢查 Build #35 的狀態是否已更新為 FAILURE
```

### 第二步：實施長期方案（方案 1 + 方案 3）

1. **修改核心同步邏輯**（方案 1）
   - 增加狀態更新機制
   - 測試確保不影響現有功能

2. **添加定期驗證任務**（方案 3）
   - 每 30 分鐘檢查最近 24 小時的 Builds
   - 自動修正狀態不一致的情況

---

## 📝 相關文件

- **同步邏輯**：`backend/api/tasks.py` - `sync_jenkins_builds()`
- **Build 模型**：`backend/api/models.py` - `JenkinsBuild`
- **Jenkins 客戶端**：`library/services/jenkins_client.py`
- **優化文檔**：`docs/development/JENKINS_BUILD_SYNC_OPTIMIZATION.md`

---

## 📅 問題記錄

- **發現日期**：2025-11-20
- **報告人**：用戶
- **影響範圍**：所有狀態改變的 Builds
- **優先級**：高（影響數據準確性）

---

**文檔版本**：v1.0  
**最後更新**：2025-11-20
