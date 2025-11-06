# Blue Ocean Pipeline Stage 功能實現總結

**實現日期**: 2025-11-06  
**功能**: 從 Jenkins Blue Ocean API 獲取 Pipeline Stage 失敗資訊

---

## ✅ 已完成工作

### 1. 後端服務層 (JenkinsClient)

**檔案**: `library/services/jenkins_client.py`

新增 3 個方法：

#### 1.1 `get_blue_ocean_pipeline_nodes(job_name, build_number)`
- **功能**: 獲取 Blue Ocean Pipeline 的所有 Stage/Node 資訊
- **API 端點**: `/blue/rest/organizations/jenkins/pipelines/{job_name}/runs/{build_number}/nodes/`
- **返回**: Stage 列表（包含 name, result, duration, error 等）

#### 1.2 `get_failed_stages(job_name, build_number)`
- **功能**: 獲取 Build 中失敗的 Stage 列表
- **篩選條件**: `result` in ['FAILURE', 'UNSTABLE', 'ABORTED']
- **返回**: 格式化的失敗 Stage 資訊（包含錯誤訊息）

#### 1.3 `get_pipeline_summary(job_name, build_number)`
- **功能**: 獲取 Pipeline 執行摘要統計
- **返回**: 總 Stage 數、成功/失敗/不穩定/已中止的數量

---

### 2. 資料庫模型擴充

**檔案**: `backend/api/models.py`

#### 新增欄位到 `JenkinsBuild` 模型：

```python
# Pipeline Stage 資訊（Blue Ocean）
pipeline_stages = models.JSONField(default=list, blank=True, verbose_name='Pipeline Stages')
failed_stage = models.CharField(max_length=200, blank=True, verbose_name='失敗的 Stage')
```

#### 資料庫遷移：
- ✅ 創建遷移檔案: `0015_add_pipeline_stage_info.py`
- ✅ 應用遷移: `migrate` 成功

---

### 3. REST API 端點

**檔案**: `backend/api/views/jenkins.py`

#### 新增端點: `/api/jenkins-builds/{id}/pipeline_stages/`

**支援方法**:

##### GET - 獲取已存儲的 Pipeline Stage 資訊
```bash
curl http://localhost/api/jenkins-builds/123/pipeline_stages/
```

**返回資料**:
```json
{
    "success": true,
    "build_id": 123,
    "build_number": 456,
    "job_name": "my-pipeline-job",
    "result": "FAILURE",
    "failed_stage": "Build",
    "pipeline_summary": {
        "total_stages": 5,
        "successful_stages": 3,
        "failed_stages": 1,
        "unstable_stages": 0,
        "aborted_stages": 0
    },
    "stages": [ ... ],
    "failed_stages": [ ... ]
}
```

##### POST - 從 Jenkins 同步最新的 Pipeline Stage 資訊
```bash
curl -X POST http://localhost/api/jenkins-builds/123/pipeline_stages/
```

**功能**:
1. 從 Jenkins Blue Ocean API 獲取 Pipeline Nodes
2. 提取 Stage 資訊並格式化
3. 識別失敗的 Stage
4. 更新資料庫 (`pipeline_stages` 和 `failed_stage` 欄位)
5. 返回完整的 Stage 資訊

---

### 4. Serializer 擴充

**檔案**: `backend/api/serializers.py`

#### JenkinsBuildSerializer 新增欄位：

```python
has_pipeline_stages = serializers.SerializerMethodField()
failed_stages_count = serializers.SerializerMethodField()
```

**功能**:
- `has_pipeline_stages`: 檢查是否有 Pipeline Stage 資訊
- `failed_stages_count`: 計算失敗的 Stage 數量

---

### 5. 測試腳本

**檔案**: `backend/test_blue_ocean_stages.py`

**包含測試**:
1. ✅ 測試 JenkinsClient Blue Ocean API 方法
2. ✅ 測試更新資料庫中的 Pipeline Stage 資訊
3. ✅ 測試查詢有 Stage 資訊的 Build

**執行方式**:
```bash
docker exec nt-django python test_blue_ocean_stages.py
```

---

### 6. 完整文檔

**檔案**: `docs/features/jenkins/BLUE_OCEAN_PIPELINE_STAGES.md`

**內容包含**:
- 功能概述
- 資料庫模型說明
- API 端點文檔
- 使用範例（Python、cURL、Django ORM）
- 測試方法
- 常見問題 FAQ
- 前端顯示範例（React）

---

## 🎯 功能特點

### ✅ 核心功能

1. **自動追蹤失敗 Stage**
   - 自動識別並記錄第一個失敗的 Stage 名稱
   - 存儲在 `failed_stage` 欄位，方便查詢

2. **完整 Stage 資訊**
   - 記錄每個 Stage 的狀態（SUCCESS, FAILURE, UNSTABLE, ABORTED）
   - 記錄執行時間（毫秒和格式化字串）
   - 記錄錯誤訊息（如果有）

3. **統計分析**
   - 統計成功/失敗/不穩定/已中止的 Stage 數量
   - 提供 Pipeline 執行摘要

4. **資料庫持久化**
   - 使用 PostgreSQL JSONField 存儲完整 Stage 資訊
   - 支援複雜查詢和分析

5. **靈活查詢**
   - 按失敗 Stage 查詢 Build
   - 統計失敗 Stage 分布
   - 過濾有 Stage 資訊的 Build

---

## 📋 使用範例

### 範例 1: 同步單個 Build 的 Stage 資訊

```bash
curl -X POST http://localhost/api/jenkins-builds/123/pipeline_stages/
```

### 範例 2: 查詢失敗的 Stage

```python
from api.models import JenkinsBuild

# 查詢所有在 "Build" Stage 失敗的 Build
builds = JenkinsBuild.objects.filter(failed_stage='Build')

for build in builds:
    print(f"{build.job.name} #{build.build_number} 在 Build Stage 失敗")
```

### 範例 3: 統計失敗 Stage 分布

```python
from django.db.models import Count

stage_stats = JenkinsBuild.objects.exclude(
    failed_stage=''
).values('failed_stage').annotate(
    count=Count('id')
).order_by('-count')

for stat in stage_stats:
    print(f"Stage '{stat['failed_stage']}': {stat['count']} 次失敗")
```

---

## 🔍 資料結構範例

### pipeline_stages 欄位內容

```json
[
    {
        "id": "3",
        "name": "Checkout",
        "result": "SUCCESS",
        "state": "FINISHED",
        "duration_ms": 1234,
        "start_time": "2025-11-06T10:30:00.000+0000",
        "type": "STAGE",
        "error": null
    },
    {
        "id": "5",
        "name": "Build",
        "result": "FAILURE",
        "state": "FINISHED",
        "duration_ms": 5678,
        "start_time": "2025-11-06T10:30:05.000+0000",
        "type": "STAGE",
        "error": {
            "message": "Build step failed with exception"
        }
    },
    {
        "id": "7",
        "name": "Test",
        "result": "ABORTED",
        "state": "FINISHED",
        "duration_ms": 0,
        "start_time": "2025-11-06T10:30:10.000+0000",
        "type": "STAGE",
        "error": null
    }
]
```

### API 響應範例

```json
{
    "success": true,
    "build_id": 123,
    "build_number": 456,
    "job_name": "my-pipeline-job",
    "result": "FAILURE",
    "failed_stage": "Build",
    "pipeline_summary": {
        "total_stages": 5,
        "successful_stages": 3,
        "failed_stages": 1,
        "unstable_stages": 0,
        "aborted_stages": 0
    },
    "stages": [
        {
            "name": "Checkout",
            "result": "SUCCESS",
            "duration_ms": 1234,
            "duration_formatted": "1.2 秒"
        },
        {
            "name": "Build",
            "result": "FAILURE",
            "duration_ms": 5678,
            "duration_formatted": "5.7 秒",
            "error_message": "Build step failed"
        }
    ],
    "failed_stages": [
        {
            "name": "Build",
            "result": "FAILURE",
            "duration_ms": 5678,
            "duration_formatted": "5.7 秒",
            "error_message": "Build step failed"
        }
    ]
}
```

---

## 🚀 未來擴充方向

### 1. Celery 自動同步
- 在 Build 完成後自動同步 Pipeline Stage 資訊
- 定時任務批次同步所有失敗 Build 的 Stage 資訊

### 2. 前端 UI 頁面
- Pipeline Stage 進度條視覺化
- 失敗 Stage 錯誤訊息展示
- Stage 執行時間趨勢圖

### 3. 統計分析
- 最常失敗的 Stage 排行榜
- Stage 執行時間分析
- Pipeline 成功率趨勢

### 4. 警告通知
- 特定 Stage 失敗時發送通知
- Stage 執行時間過長警告

---

## 📦 相關檔案清單

### 後端服務
- `library/services/jenkins_client.py` - Jenkins API 客戶端（新增 Blue Ocean 方法）

### 資料庫
- `backend/api/models.py` - JenkinsBuild 模型（新增欄位）
- `backend/api/migrations/0015_add_pipeline_stage_info.py` - 資料庫遷移檔案

### API
- `backend/api/views/jenkins.py` - JenkinsBuildViewSet（新增 pipeline_stages 端點）
- `backend/api/serializers.py` - JenkinsBuildSerializer（新增欄位）

### 測試
- `backend/test_blue_ocean_stages.py` - 功能測試腳本

### 文檔
- `docs/features/jenkins/BLUE_OCEAN_PIPELINE_STAGES.md` - 完整功能文檔
- `docs/features/jenkins/README.md` - Jenkins 功能索引
- `docs/features/jenkins/BLUE_OCEAN_IMPLEMENTATION_SUMMARY.md` - 本文檔

---

## ✅ 驗證清單

- [x] JenkinsClient 新增 Blue Ocean API 方法
- [x] 資料庫模型新增 pipeline_stages 和 failed_stage 欄位
- [x] 資料庫遷移成功應用
- [x] REST API 端點實現（GET 和 POST）
- [x] Serializer 新增計算欄位
- [x] 測試腳本創建
- [x] 完整功能文檔編寫
- [x] README 索引更新

---

## 📝 開發筆記

### Blue Ocean API 端點格式

```
GET {JENKINS_URL}/blue/rest/organizations/jenkins/pipelines/{JOB_NAME}/runs/{BUILD_NUMBER}/nodes/
```

### 注意事項

1. **Blue Ocean Plugin 必須安裝**: 如果 Jenkins 沒有安裝 Blue Ocean，API 會返回 404
2. **只適用於 Pipeline Job**: Freestyle Job 沒有 Stage 概念
3. **JSONField 儲存**: 使用 PostgreSQL JSONField 存儲完整 Stage 資訊，支援複雜查詢
4. **failed_stage 優化**: 只記錄第一個失敗的 Stage，便於快速查詢

---

**實現者**: GitHub Copilot  
**審查者**: Network Toolbox Team  
**日期**: 2025-11-06
