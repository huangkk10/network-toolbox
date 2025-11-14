# Jenkins 定時任務完整說明

**更新時間**: 2025-11-14  
**狀態**: ✅ 所有任務正常運行

---

## 📊 Jenkins 相關定時任務總覽

系統中共有 **5 個 Jenkins 相關的定時任務**，負責不同階段的資料同步和存儲工作。

| 任務名稱 | 執行週期 | 功能說明 | 執行次數 |
|---------|---------|---------|----------|
| **sync-jenkins-jobs-hourly** | 每小時（0 分）| 同步 Jobs 列表 | 15 次 |
| **sync-jenkins-builds-every-10-minutes** | 每 10 分鐘 | 同步 Builds 記錄 | 1,181 次 |
| **sync-jenkins-builds-hourly** | 每小時（50 分）| 同步 Builds 記錄 | 220 次 |
| **auto-store-jenkins-builds-every-30-minutes** | 每 30 分鐘 | 自動存儲 Builds Workspace | 209 次 |
| **auto-store-jenkins-artifacts-hourly** | 每 30 分鐘 | 自動存儲 Artifacts | 160 次 |

---

## 🔄 任務執行流程圖

```
┌─────────────────────────────────────────────────────────────────┐
│                    Jenkins 資料處理流程                          │
└─────────────────────────────────────────────────────────────────┘

第一步：同步 Job 列表（每小時）
┌──────────────────────────────────────┐
│  sync-jenkins-jobs-hourly            │
│  ⏰ 每小時整點（XX:00）               │
│  📋 任務：api.tasks.sync_all_jenkins_jobs_task
│                                       │
│  功能：                               │
│  ├─ 從 Jenkins API 獲取所有 Jobs     │
│  ├─ 創建/更新資料庫中的 Job 記錄      │
│  ├─ 同步 View 資訊                   │
│  └─ 更新 last_sync_at 時間戳         │
│                                       │
│  處理範圍：                           │
│  └─ 5 個 Jenkins Server              │
│      ├─ 10.252.170.180: 21 Jobs      │
│      ├─ 10.252.170.182: 355 Jobs     │
│      ├─ 10.252.170.171: 16 Jobs      │
│      ├─ 10.252.170.187: 206 Jobs     │
│      └─ 10.252.170.188: 68 Jobs      │
│  總計：666 個 Jobs                    │
└──────────────────────────────────────┘
                  ↓

第二步：同步 Build 記錄（高頻）
┌──────────────────────────────────────┐
│  sync-jenkins-builds-every-10-minutes│
│  ⏰ 每 10 分鐘                        │
│  📋 任務：api.tasks.sync_jenkins_builds
│                                       │
│  功能：                               │
│  ├─ 獲取每個 Job 的最新 Builds       │
│  ├─ 創建/更新 Build 記錄到資料庫      │
│  ├─ 記錄 Build 狀態、時間戳、結果     │
│  └─ 更新 Build 的詳細資訊             │
│                                       │
│  參數：                               │
│  ├─ max_builds_per_job: 20           │
│  └─ max_age_days: 3 天               │
└──────────────────────────────────────┘
                  ↓

第三步：存儲 Build Workspace（自動）
┌──────────────────────────────────────┐
│  auto-store-jenkins-builds-every-30-minutes
│  ⏰ 每 30 分鐘                        │
│  📋 任務：api.tasks.auto_store_jenkins_builds_task
│                                       │
│  功能：                               │
│  ├─ 掃描未存儲的 Builds（資料庫查詢） │
│  ├─ 過濾條件：                        │
│  │   ├─ is_workspace_stored = False  │
│  │   ├─ is_building = False（已完成）│
│  │   ├─ result in [SUCCESS, FAILURE, UNSTABLE]
│  │   └─ url 不為空                   │
│  ├─ 創建異步存儲任務                  │
│  └─ 存儲 Build Workspace 到 NAS      │
│                                       │
│  參數：                               │
│  └─ limit: 每次最多 20 個 Build      │
│                                       │
│  存儲位置：                           │
│  └─ /mnt/mdt/.../jenkins_test_storage/│
└──────────────────────────────────────┘
                  ↓

第四步：存儲 Build Artifacts（自動）
┌──────────────────────────────────────┐
│  auto-store-jenkins-artifacts-hourly │
│  ⏰ 每 30 分鐘                        │
│  📋 任務：api.tasks.auto_store_jenkins_artifacts_task
│                                       │
│  功能：                               │
│  ├─ 掃描符合條件的 Builds             │
│  ├─ 過濾條件：                        │
│  │   ├─ 最近 7 天內（168 小時）      │
│  │   ├─ 至少 30 分鐘前完成            │
│  │   ├─ is_artifacts_stored = False  │
│  │   ├─ is_building = False          │
│  │   └─ result not in [ABORTED, NOT_BUILT]
│  ├─ 從 Jenkins API 獲取 Artifacts    │
│  ├─ 下載並存儲到 NAS                  │
│  └─ 更新 is_artifacts_stored 標記    │
│                                       │
│  參數：                               │
│  ├─ max_builds: 每次最多 50 個       │
│  └─ max_age_hours: 168 小時（7天）   │
│                                       │
│  存儲位置：                           │
│  └─ /mnt/mdt/.../jenkins_test_storage/│
└──────────────────────────────────────┘
```

---

## 📝 各任務詳細說明

### 1️⃣ sync-jenkins-jobs-hourly（Jobs 同步）

**任務函數**: `api.tasks.sync_all_jenkins_jobs_task`  
**執行週期**: 每小時整點（0 * * * *）  
**執行次數**: 15 次  
**最後執行**: 2025-11-14 11:00:00

#### 功能描述
- 從 Jenkins API 獲取所有 Server 的 Job 列表
- 同步 Job 的基本資訊（名稱、URL、狀態等）
- 更新 View 分類資訊
- 更新資料庫中的 JenkinsJob 記錄

#### 處理邏輯
```python
for server in online_servers:
    views = client.list_views()
    for view in views:
        jobs = client.list_jobs_in_view(view)
        for job in jobs:
            JenkinsJob.objects.update_or_create(
                server=server,
                full_name=job['full_name'],
                defaults={
                    'url': job['url'],
                    'is_buildable': job['buildable'],
                    'is_disabled': job.get('disabled', False),
                    'view_name': view['name'],
                    'last_sync_at': timezone.now()
                }
            )
```

#### 執行結果範例
```
處理伺服器: 5 個
找到 Jobs: 666 個
新增 Jobs: 0 個
更新 Jobs: 666 個
錯誤數量: 0 個
總耗時: 1.23 秒
```

---

### 2️⃣ sync-jenkins-builds-every-10-minutes（Builds 同步）

**任務函數**: `api.tasks.sync_jenkins_builds`  
**執行週期**: 每 10 分鐘（*/10 * * * *）  
**執行次數**: 1,181 次  
**最後執行**: 2025-11-14 11:10:00

#### 功能描述
- 獲取每個 Job 的最新 Build 記錄
- 同步 Build 的狀態、結果、時間戳等資訊
- 創建/更新資料庫中的 JenkinsBuild 記錄
- 作為後續存儲任務的資料來源

#### 重要參數
- `max_builds_per_job`: 20（每個 Job 最多同步 20 個 Build）
- `max_age_days`: 3（只同步最近 3 天的 Build）

#### 處理邏輯
```python
for job in jobs:
    builds = client.get_job_builds(job.name, max_builds=20)
    for build_data in builds:
        if build_timestamp < cutoff_time:
            continue  # 跳過太舊的 Build
        
        JenkinsBuild.objects.update_or_create(
            job=job,
            build_number=build_data['number'],
            defaults={
                'url': build_data['url'],
                'result': build_data['result'],
                'is_building': build_data['building'],
                'build_timestamp': build_timestamp,
                ...
            }
        )
```

---

### 3️⃣ auto-store-jenkins-builds-every-30-minutes（Workspace 自動存儲）

**任務函數**: `api.tasks.auto_store_jenkins_builds_task`  
**執行週期**: 每 30 分鐘（*/30 * * * *）  
**執行次數**: 209 次  
**最後執行**: 2025-11-14 11:00:00

#### 功能描述
- 自動掃描資料庫中未存儲的 Builds
- 根據配置的規則篩選需要存儲的 Build
- 創建異步任務存儲 Build 的 Workspace 到 NAS
- 支援配置存儲策略（結果類型、大小限制等）

#### 存儲條件
1. ✅ `is_workspace_stored = False`（未存儲）
2. ✅ `is_building = False`（Build 已完成）
3. ✅ `result in ['SUCCESS', 'FAILURE', 'UNSTABLE']`（特定結果）
4. ✅ `url is not None`（有可訪問的 URL）

#### 配置選項
```python
JENKINS_STORAGE_POLICY = {
    'auto_store': True,  # 啟用自動存儲
    'store_results': ['SUCCESS', 'FAILURE', 'UNSTABLE'],
    'max_workspace_size_mb': 500,  # 最大存儲大小限制
}
```

#### 處理流程
```python
# 查詢符合條件的 Builds
builds = JenkinsBuild.objects.filter(
    is_workspace_stored=False,
    is_building=False,
    result__in=store_results
).order_by('-build_timestamp')[:limit]

# 為每個 Build 創建異步存儲任務
for build in builds:
    task = store_jenkins_build_task.delay(build.id)
```

---

### 4️⃣ auto-store-jenkins-artifacts-hourly（Artifacts 自動存儲）

**任務函數**: `api.tasks.auto_store_jenkins_artifacts_task`  
**執行週期**: 每 30 分鐘（*/30 * * * *）  
**執行次數**: 160 次  
**最後執行**: 2025-11-14 11:00:00

#### 功能描述
- 自動掃描最近完成的 Builds
- 檢查是否有 Artifacts 需要存儲
- 下載 Artifacts 並存儲到 NAS
- 更新存儲狀態標記

#### 存儲條件
1. ✅ 最近 7 天內完成（168 小時）
2. ✅ 至少 30 分鐘前完成（避免正在執行）
3. ✅ `is_artifacts_stored = False`（未存儲）
4. ✅ `is_building = False`（Build 已完成）
5. ✅ `result not in ['ABORTED', 'NOT_BUILT']`（排除中止的）

#### 重要參數
- `max_builds`: 50（每次最多處理 50 個 Build）
- `max_age_hours`: 168（只處理最近 7 天的 Build）

#### 處理流程
```python
# 查詢符合條件的 Builds
builds = JenkinsBuild.objects.filter(
    build_timestamp__gte=max_age,      # 最近 N 小時
    build_timestamp__lte=min_age,      # 至少 30 分鐘前
    is_building=False,
    is_artifacts_stored=False,
).exclude(
    result__in=['ABORTED', 'NOT_BUILT']
).order_by('-build_timestamp')[:max_builds]

# 處理每個 Build
for build in builds:
    artifacts = client.get_build_artifacts(build)
    for artifact in artifacts:
        # 下載並存儲到 NAS
        storage_service.store_artifact(artifact)
    
    # 更新存儲狀態
    build.is_artifacts_stored = True
    build.save()
```

---

### 5️⃣ sync-jenkins-builds-hourly（補充同步）

**任務函數**: `api.tasks.sync_jenkins_builds`  
**執行週期**: 每小時第 50 分鐘（50 * * * *）  
**執行次數**: 220 次  
**最後執行**: 2025-11-14 10:50:00

#### 功能描述
- 與 `sync-jenkins-builds-every-10-minutes` 功能相同
- 作為補充同步機制，確保資料完整性
- 在每小時快結束時執行，避免與其他任務衝突

---

## ⏱️ 執行時間軸（範例：一小時內的執行順序）

```
11:00 ─┬─ sync-jenkins-jobs-hourly（Jobs 同步）✅
       ├─ auto-store-jenkins-builds-every-30-minutes（Workspace 存儲）✅
       └─ auto-store-jenkins-artifacts-hourly（Artifacts 存儲）✅

11:10 ─── sync-jenkins-builds-every-10-minutes（Builds 同步）✅

11:20 ─── sync-jenkins-builds-every-10-minutes（Builds 同步）✅

11:30 ─┬─ sync-jenkins-builds-every-10-minutes（Builds 同步）✅
       ├─ auto-store-jenkins-builds-every-30-minutes（Workspace 存儲）✅
       └─ auto-store-jenkins-artifacts-hourly（Artifacts 存儲）✅

11:40 ─── sync-jenkins-builds-every-10-minutes（Builds 同步）✅

11:50 ─┬─ sync-jenkins-builds-every-10-minutes（Builds 同步）✅
       └─ sync-jenkins-builds-hourly（補充同步）✅

12:00 ─┬─ sync-jenkins-jobs-hourly（Jobs 同步）✅【循環開始】
       ├─ auto-store-jenkins-builds-every-30-minutes（Workspace 存儲）✅
       └─ auto-store-jenkins-artifacts-hourly（Artifacts 存儲）✅
```

---

## 📁 NAS 存儲結構

```
/mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/
├── 10.252.170.180/          # Jenkins Server 1
│   ├── job_name_1/
│   │   ├── build_123/       # Build 編號
│   │   │   ├── workspace/   # Workspace 檔案
│   │   │   └── artifacts/   # Build Artifacts
│   │   └── build_124/
│   └── job_name_2/
├── 10.252.170.182/          # Jenkins Server 2
├── 10.252.170.171/          # Jenkins Server 3
├── 10.252.170.187/          # Jenkins Server 4
└── 10.252.170.188/          # Jenkins Server 5
```

---

## 🔍 監控與驗證

### 查看任務執行狀態
```bash
docker compose exec django python manage.py shell -c "
from django_celery_beat.models import PeriodicTask

tasks = PeriodicTask.objects.filter(task__icontains='jenkins').order_by('name')
for t in tasks:
    print(f'{t.name}: 執行 {t.total_run_count} 次, 最後執行 {t.last_run_at}')
"
```

### 查看日誌
```bash
# Django 日誌
docker compose exec django grep "Celery.*Jenkins" /app/logs/django.log | tail -20

# Celery Worker 日誌
docker compose exec django tail -f /app/logs/celery_worker.log

# Celery Beat 日誌
docker compose exec django tail -f /app/logs/celery_beat.log
```

### 檢查 NAS 存儲
```bash
docker compose exec django find /mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/ \
  -type f -printf "%T+ %p\n" 2>/dev/null | sort -r | head -10
```

---

## 📊 任務統計資料

| 任務 | 總執行次數 | 平均頻率 | 預估日執行次數 |
|------|----------|---------|--------------|
| sync-jenkins-jobs-hourly | 15 | 每小時 | 24 次 |
| sync-jenkins-builds-every-10-minutes | 1,181 | 每 10 分鐘 | 144 次 |
| sync-jenkins-builds-hourly | 220 | 每小時 | 24 次 |
| auto-store-jenkins-builds | 209 | 每 30 分鐘 | 48 次 |
| auto-store-jenkins-artifacts | 160 | 每 30 分鐘 | 48 次 |

---

## ✅ 總結

### 資料流向
```
Jenkins Server → 同步 Jobs → 同步 Builds → 存儲 Workspace → 存儲 Artifacts → NAS
```

### 自動化程度
- ✅ **完全自動化** - 無需手動操作
- ✅ **高頻同步** - 最快每 10 分鐘更新一次
- ✅ **智能存儲** - 根據規則自動篩選和存儲
- ✅ **持久化** - 所有資料存儲到 NAS

### 維護建議
1. 定期檢查任務執行狀態
2. 監控 NAS 存儲空間使用情況
3. 根據需求調整執行頻率和存儲策略
4. 定期清理舊的 Build 資料

---

**文件生成時間**: 2025-11-14 19:20:00  
**維護狀態**: ✅ 所有任務正常運行
