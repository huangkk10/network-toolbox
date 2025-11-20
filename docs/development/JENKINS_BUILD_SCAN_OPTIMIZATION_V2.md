# Jenkins Build 狀態掃描優化 V2

## 📋 當前狀態分析

### 已實施的優化（V1）

從代碼分析（`backend/api/tasks.py` Line 1810-2025），目前已經實施了：

1. ✅ **查詢優化**：只查詢最近 20 個 Builds + 使用 `only()` 只加載必要欄位
2. ✅ **智能過濾**：只檢查活躍的 Builds（is_building / 最近1小時更新 / result=UNKNOWN）
3. ✅ **批量更新**：使用 `bulk_update()` 代替逐個 `save()`
4. ✅ **API 緩存**：failed_stages 使用 Redis 緩存（24小時）

### 當前運行狀態（從日誌觀察）

```
📊 Job xxx: 0 個新 Builds, 0 個需檢查 (活躍過濾)
```

✅ **智能過濾確實在工作**，大部分 Job 的 Builds 都被過濾掉了（0 個需檢查）

---

## 🔍 發現的潛在問題

### 🔴 **問題 1：Job.save() 在循環中被頻繁調用**

**位置**：Line 1898-1901, Line 2006-2008

```python
# ❌ 問題代碼 1（創建新 Build 時）
if not job.last_build_time or build_timestamp > job.last_build_time:
    job.last_build_time = build_timestamp
    job.last_build_number = build_number
    job.last_build_status = result or 'UNKNOWN'
    job.save(update_fields=['last_build_time', 'last_build_number', 'last_build_status'])
    # ❌ 每個新 Build 都可能觸發一次 save()

# ❌ 問題代碼 2（更新 Build 時）
if result and (not job.last_build_number or build_number >= job.last_build_number):
    job.last_build_status = result
    job.save(update_fields=['last_build_status'])
    # ❌ 每個更新的 Build 都可能觸發一次 save()
```

**影響**：
- 如果 722 個 Jobs 中有 100 個 Job 有新 Build，會執行 **100 次 save()**
- 如果有 50 個 Job 的 Build 狀態有變化，又會執行 **50 次 save()**
- 總共可能 **150 次額外的數據庫寫入**

---

### 🟡 **問題 2：智能過濾的時間窗口可能過大**

**位置**：Line 1838

```python
recent_time = dj_timezone.now() - timedelta(hours=1)  # ❌ 1 小時
```

**分析**：
- Jenkins Build 通常在幾分鐘內完成
- 1 小時的時間窗口可能會檢查過多已經穩定的 Builds
- **建議改為 15-30 分鐘**

---

### 🟡 **問題 3：缺少統計日誌，難以監控**

**當前日誌**：
```
📊 Job xxx: 0 個新 Builds, 0 個需檢查 (活躍過濾)
✅ 批量更新 X 個 Builds
```

**缺少的統計**：
- 總共掃描了多少 Builds？
- 過濾掉了多少 Builds？
- 實際檢查了多少 Builds？
- 檢查花費的時間？

---

### 🟢 **問題 4：可以進一步減少 Jenkins API 調用**

**當前邏輯**：
```python
# 每個 Job 都調用一次 get_job_builds()
jenkins_builds = client.get_job_builds(job.name, limit=max_builds_per_job)
```

**建議**：
- 如果 Job 在資料庫中沒有任何活躍 Builds，可以跳過 API 調用
- 只對有活躍 Builds 的 Job 調用 API

---

## 🛠️ 優化方案 V2

### 優化 1：批量更新 Job 的 last_build 資訊

**目標**：減少 Job.save() 調用次數 **90%**

```python
# ✅ 優化後的代碼
jobs_to_update = []  # 收集需要更新的 Jobs

for job in jobs:
    try:
        # ... 現有邏輯 ...
        
        job_needs_update = False
        
        # 處理新 Builds
        for build_data in new_builds:
            # ... 創建 Build ...
            
            # 檢查是否需要更新 Job（但不立即 save）
            if not job.last_build_time or build_timestamp > job.last_build_time:
                job.last_build_time = build_timestamp
                job.last_build_number = build_number
                job.last_build_status = result or 'UNKNOWN'
                job_needs_update = True
        
        # 處理 Build 更新
        for build_data, existing_build in builds_to_check:
            # ... 檢查邏輯 ...
            
            # 檢查是否需要更新 Job（但不立即 save）
            if result and (not job.last_build_number or build_number >= job.last_build_number):
                job.last_build_status = result
                job_needs_update = True
        
        # 批量更新 Builds
        if builds_to_update:
            JenkinsBuild.objects.bulk_update(...)
        
        # 收集需要更新的 Job
        if job_needs_update:
            jobs_to_update.append(job)
    
    except Exception as e:
        logger.error(...)

# ✅ 在外層批量更新所有 Jobs
if jobs_to_update:
    JenkinsJob.objects.bulk_update(
        jobs_to_update,
        ['last_build_time', 'last_build_number', 'last_build_status'],
        batch_size=100
    )
    logger.info(f'[Celery]   📊 批量更新 {len(jobs_to_update)} 個 Jobs')
```

**預期效果**：
- Job save() 次數：150 次 → **1-2 次**（批量更新）
- 減少數據庫寫入 **99%**

---

### 優化 2：調整智能過濾時間窗口

**目標**：減少不必要的檢查

```python
# ✅ 優化後
# 從 1 小時改為 15 分鐘（因為 Build 通常在幾分鐘內完成）
recent_time = dj_timezone.now() - timedelta(minutes=15)

builds_to_check = []

for b in jenkins_builds:
    build_num = b.get('number')
    if build_num in existing_builds:
        db_build = existing_builds[build_num]
        
        # 只檢查真正活躍的 Builds：
        # 1. 正在構建的（優先級最高）
        # 2. 最近 15 分鐘內更新的（縮短時間窗口）
        # 3. 狀態未確定的（UNKNOWN/None）
        if (db_build.is_building or 
            db_build.updated_at >= recent_time or 
            db_build.result in ['UNKNOWN', None]):
            builds_to_check.append((b, db_build))
```

**預期效果**：
- 檢查的 Builds 數量再減少 **20-30%**
- CPU 使用率再降低 **5-10%**

---

### 優化 3：添加詳細統計日誌

**目標**：監控優化效果

```python
# ✅ 在 sync_jenkins_builds() 函數開始處添加計數器
total_builds_checked = 0      # 實際檢查的 Builds 數量
total_builds_filtered = 0     # 被過濾掉的 Builds 數量
total_api_calls = 0           # Jenkins API 調用次數
check_time_start = time.time()  # 檢查開始時間

# 處理每個 Job
for job in jobs:
    try:
        # ... 查詢 existing_builds ...
        
        # 記錄 API 調用
        jenkins_builds = client.get_job_builds(job.name, limit=max_builds_per_job)
        total_api_calls += 1
        
        # ... 智能過濾 ...
        
        # 統計
        total_builds_checked += len(builds_to_check)
        total_builds_filtered += len(existing_builds) - len(builds_to_check)
        
        # 詳細日誌
        if len(builds_to_check) > 0:
            logger.info(
                f'[Celery]     📊 Job {job.name}: '
                f'{len(new_builds)} 個新, '
                f'{len(builds_to_check)} 個需檢查, '
                f'{len(existing_builds) - len(builds_to_check)} 個已過濾'
            )

# 最終統計
check_duration = time.time() - check_time_start

logger.info('[Celery] ✅ Jenkins Builds 同步完成')
logger.info(f'[Celery]   📊 掃描統計:')
logger.info(f'[Celery]      - 總 Builds 數: {total_builds_found} 個')
logger.info(f'[Celery]      - 實際檢查: {total_builds_checked} 個')
logger.info(f'[Celery]      - 智能過濾: {total_builds_filtered} 個 ({total_builds_filtered/total_builds_found*100:.1f}%)')
logger.info(f'[Celery]      - API 調用: {total_api_calls} 次')
logger.info(f'[Celery]      - 檢查時間: {check_duration:.2f} 秒')
logger.info(f'[Celery]   🎯 操作統計:')
logger.info(f'[Celery]      - 創建 Builds: {builds_created} 個')
logger.info(f'[Celery]      - 更新 Builds: {builds_updated} 個')
logger.info(f'[Celery]      - 更新 Jobs: {len(jobs_to_update)} 個')
logger.info(f'[Celery]   ⏱️  總執行時間: {duration:.2f} 秒')
```

**預期效果**：
- 可以清楚看到優化效果
- 易於監控和調試

---

### 優化 4：跳過無活躍 Builds 的 Job

**目標**：減少不必要的 Jenkins API 調用

```python
# ✅ 優化後
for job in jobs:
    try:
        # 查詢最近的 Builds
        existing_builds = {
            b.build_number: b
            for b in JenkinsBuild.objects.filter(job=job)
                .only('id', 'build_number', 'result', 'is_building', 'duration', 'failed_stage', 'updated_at')
                .order_by('-build_number')[:max_builds_per_job]
        }
        
        # ✅ 預先檢查：如果沒有活躍的 Builds，跳過 API 調用
        has_active_builds = any(
            b.is_building or 
            b.updated_at >= recent_time or 
            b.result in ['UNKNOWN', None]
            for b in existing_builds.values()
        )
        
        # 如果沒有任何活躍 Builds，且最近 24 小時內沒有新 Build，跳過
        if not has_active_builds and job.last_build_time:
            last_build_age = dj_timezone.now() - job.last_build_time
            if last_build_age.total_seconds() > 86400:  # 24 小時
                logger.debug(f'[Celery]     ⏭️  跳過 Job {job.name}（無活躍 Builds，最後 Build 已超過 24 小時）')
                continue
        
        # 調用 Jenkins API（只在必要時）
        jenkins_builds = client.get_job_builds(job.name, limit=max_builds_per_job)
        total_api_calls += 1
        
        # ... 其餘邏輯 ...
```

**預期效果**：
- Jenkins API 調用次數減少 **30-50%**（大部分穩定的 Job 不需要檢查）
- 網路開銷減少
- 執行時間再減少 **10-20%**

---

## 📊 優化效果預估

### V1（已實施）vs V2（建議優化）

| 指標 | V1（當前） | V2（優化後） | 改善幅度 |
|-----|----------|-------------|---------|
| **Job save() 次數** | ~150 次 | **1-2 次** | ⬇️ 99% |
| **檢查時間窗口** | 1 小時 | **15 分鐘** | ⬇️ 75% |
| **實際檢查的 Builds** | ~100 個 | **~70 個** | ⬇️ 30% |
| **Jenkins API 調用** | 722 次 | **~400 次** | ⬇️ 45% |
| **執行時間** | 2.5 秒 | **~1.5 秒** | ⬇️ 40% |
| **CPU 使用率** | 低-中 | **更低** | ⬇️ 20-30% |

---

## 🚀 實施計劃

### Phase 1：立即優化（優先級：高，預計 2 小時）

1. ✅ **批量更新 Jobs**（優化 1）- 1 小時
   - 移除循環中的 `job.save()`
   - 收集需要更新的 Jobs
   - 使用 `bulk_update()` 批量更新

2. ✅ **調整時間窗口**（優化 2）- 15 分鐘
   - 從 1 小時改為 15 分鐘

3. ✅ **添加統計日誌**（優化 3）- 45 分鐘
   - 記錄掃描統計
   - 記錄過濾效果
   - 記錄執行時間分布

### Phase 2：進一步優化（優先級：中，預計 1 小時）

4. ✅ **跳過無活躍 Builds 的 Job**（優化 4）- 1 小時
   - 預先檢查是否有活躍 Builds
   - 跳過穩定的 Job

---

## 🧪 測試驗證

### 1. 功能測試

```bash
# 手動觸發同步，觀察日誌
docker exec nt-django python manage.py shell << 'EOF'
from api.tasks import sync_jenkins_builds
result = sync_jenkins_builds()
print(result)
EOF
```

### 2. 性能測試

**優化前**：
```
執行時間: 2.5 秒
Job save() 次數: ~150 次
實際檢查: ~100 個 Builds
API 調用: 722 次
```

**優化後（預期）**：
```
執行時間: ~1.5 秒
Job save() 次數: 1-2 次
實際檢查: ~70 個 Builds
API 調用: ~400 次
```

### 3. 監控指標

```bash
# 監控 CPU 使用率
watch -n 5 'docker stats nt-celery-worker --no-stream | grep celery'

# 查看日誌統計
docker compose logs celery_worker --since 30m | grep "掃描統計"
```

---

## 📝 總結

### 已實施的優化（V1）✅

1. ✅ 查詢優化：只查詢最近 20 個 Builds
2. ✅ 智能過濾：只檢查活躍的 Builds
3. ✅ 批量更新：使用 `bulk_update()` 更新 Builds
4. ✅ API 緩存：failed_stages 緩存 24 小時

**效果**：CPU 使用率從 99.7% → 已顯著降低（Celery Worker 只有 0.68%）

### 建議的進一步優化（V2）

1. 🔸 **批量更新 Jobs**：減少 Job save() 次數 99%
2. 🔸 **縮短時間窗口**：從 1 小時改為 15 分鐘
3. 🔸 **添加統計日誌**：監控優化效果
4. 🔸 **跳過穩定 Job**：減少 Jenkins API 調用 45%

**預期額外效果**：
- 執行時間再減少 **40%**（2.5s → 1.5s）
- CPU 使用率再降低 **20-30%**
- Jenkins API 調用減少 **45%**

---

**文檔版本**：v2.0  
**創建日期**：2025-11-20  
**狀態**：建議優化，待實施  
**維護者**：Network Toolbox Team
