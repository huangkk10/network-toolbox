# Jenkins Build 同步邏輯優化

## 📅 日期
2025-11-14

## 🎯 優化目標
改進 `sync_jenkins_builds` 任務，**不把已存在的資料算作處理過**，避免重複處理占用配額。

## 🔴 問題分析

### 原始邏輯問題：
```python
# 舊邏輯（有問題）
for build_data in jenkins_builds:  # 處理所有 Builds
    build, created = JenkinsBuild.objects.update_or_create(...)
    if created:
        builds_created += 1
    else:
        builds_updated += 1  # ❌ 已存在的也算處理了！
```

### 問題場景示例：
假設一個 Job 有 100 個 Builds：
- Jenkins API 限制返回最新 20 個 (`max_builds_per_job=20`)
- 資料庫中已有 Builds #1-#20
- **結果：每次都處理這 20 個已存在的，第 21-100 個永遠處理不到！**

### 時間範圍問題：
```python
# 自動任務配置
'kwargs': {
    'max_age_days': 7  # ❌ 只處理 7 天內的
}
```

- 10.252.170.180 和 10.252.170.182 的 Builds 都超過 7 天
- **這些 Server 的舊 Builds 永遠不會被自動處理！**

## ✅ 優化方案

### 1. 預先過濾已存在的 Builds

```python
# 新邏輯（優化後）
for job in jobs:
    # 🆕 先查詢已有的 Build Numbers
    existing_build_numbers = set(
        JenkinsBuild.objects.filter(job=job)
        .values_list('build_number', flat=True)
    )
    
    # 從 Jenkins API 獲取 Builds
    jenkins_builds = client.get_job_builds(job.name, limit=max_builds_per_job)
    
    # 🆕 過濾掉已存在的
    new_builds = [
        b for b in jenkins_builds 
        if b.get('number') not in existing_build_numbers
    ]
    
    # 如果沒有新 Builds，直接跳過
    if not new_builds:
        logger.debug(f'[Celery]     ⏭️  Job {job.name} 沒有新 Builds，跳過')
        continue
    
    logger.info(f'[Celery]     🆕 Job {job.name} 發現 {len(new_builds)} 個新 Builds')
    
    # 只處理新 Builds
    for build_data in new_builds:
        # ... 處理邏輯
```

### 2. 直接創建 Build（不再使用 update_or_create）

```python
# 舊邏輯
build, created = JenkinsBuild.objects.update_or_create(...)

# 新邏輯（因為已經過濾過，直接創建即可）
build = JenkinsBuild.objects.create(
    job=job,
    build_number=build_number,
    display_name=f'#{build_number}',
    url=url,
    result=result or 'UNKNOWN',
    is_building=building,
    duration=duration,
    build_timestamp=build_timestamp,
)
builds_created += 1
```

### 3. 調整時間範圍

```python
# backend/network_toolbox/celery.py
'sync-jenkins-builds-every-10-minutes': {
    'kwargs': {
        'max_age_days': 30  # ✅ 從 7 改為 30 天
    }
}
```

### 4. 移除 builds_updated 統計

因為只處理新 Builds，不再有「更新」的概念：

```python
# 返回值移除 builds_updated
return {
    'success': True,
    'total_servers': total_servers,
    'total_jobs': total_jobs_processed,
    'total_builds_found': total_builds_found,
    'builds_created': builds_created,
    # 'builds_updated': builds_updated,  # ✅ 移除
    'builds_skipped': builds_skipped,
    'errors': errors,
    'duration': duration,
}
```

## 📊 優化效果

### Before（優化前）:
```
處理 Job A (有 100 個 Builds，資料庫已有 #1-#20):
  - Jenkins API 返回最新 20 個 (#1-#20)
  - 全部都是已存在的
  - 結果: 處理 20 個，更新 20 個，創建 0 個
  - 問題: #21-#100 永遠處理不到！
```

### After（優化後）:
```
處理 Job A (有 100 個 Builds，資料庫已有 #1-#20):
  - Jenkins API 返回最新 20 個 (#1-#20)
  - 過濾後發現 0 個新 Builds
  - 結果: 直接跳過！不占用任何配額
  - 下次可以處理其他 Jobs 的新 Builds
```

### 新 Builds 場景:
```
處理 Job B (有 25 個 Builds，資料庫已有 #1-#15):
  - Jenkins API 返回最新 20 個 (#6-#25)
  - 過濾後發現 10 個新 Builds (#16-#25)
  - 結果: 只處理 10 個新的，創建 10 個
  - 效率提升: 節省 50% 處理時間
```

## 🔄 部署步驟

1. **修改 celery.py 配置**:
   ```bash
   vim backend/network_toolbox/celery.py
   # 將 max_age_days 從 7 改為 30
   ```

2. **修改 tasks.py 邏輯**:
   - 添加預過濾邏輯
   - 改用直接創建（不再 update_or_create）
   - 移除 builds_updated 相關代碼

3. **重啟服務**:
   ```bash
   docker compose restart django
   ```

4. **驗證優化**:
   ```python
   # 手動測試（應該跳過已存在的）
   result = sync_jenkins_builds(server_id=14, max_builds_per_job=5, max_age_days=30)
   # 預期: builds_created=0（如果已經同步過）
   ```

## 📝 注意事項

### 1. Build 狀態更新問題
**問題**: 如果一個 Build 從 `RUNNING` 變成 `SUCCESS`，新邏輯不會更新它。

**解決方案**: 
- `is_building=True` 的 Builds 會被自動存儲任務跳過
- 當 Build 完成後，下次同步會看到狀態變化
- 如需實時更新，可以保留針對 `is_building=True` 的更新邏輯

### 2. Failed Stage 同步
新邏輯保留了對失敗 Stage 的同步：
```python
if result == 'FAILURE':
    failed_stages = client.get_failed_stages(job.name, build_number)
    build.pipeline_stages = failed_stages
    build.failed_stage = first_failed.get('stage_name')
    build.save()
```

### 3. 性能提升
- **資料庫查詢優化**: 只查詢一次 Build Numbers（使用 set）
- **API 調用減少**: 跳過已存在的 Jobs，不再獲取 Pipeline Stages
- **處理速度**: 第二次同步相同資料時，速度會大幅提升

## 🎯 驗證清單

- [ ] 首次同步: 應該創建所有新 Builds
- [ ] 第二次同步: 應該跳過所有已存在的 Builds（builds_created=0）
- [ ] 混合場景: 應該只處理新增的 Builds
- [ ] 時間範圍: 30 天內的 Builds 都會被處理
- [ ] NAS 儲存: 確認 5 個 Server 都有資料夾

## 📚 相關文件

- `backend/api/tasks.py` - sync_jenkins_builds 函數
- `backend/network_toolbox/celery.py` - Celery Beat 配置
- `library/services/jenkins_client.py` - Jenkins API 客戶端

## 🔗 相關 Issue

- 問題: NAS 上只有 3 個 Server 資料夾，缺少 10.252.170.180 和 10.252.170.182
- 根因: 自動任務 max_age_days=7，這兩個 Server 的 Builds 超過 7 天
- 解決: 調整為 max_age_days=30，並優化處理邏輯
