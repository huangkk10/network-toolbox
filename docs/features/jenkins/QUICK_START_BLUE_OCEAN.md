# Jenkins Blue Ocean Pipeline Stage 功能 - 使用指南

## 🎯 快速回答您的問題

**問題**: 可以從 jenkins job 的 build 的 blue ocean 得到那個 build 在那個 stage fail 嗎?

**答案**: ✅ **可以！** 已完整實現此功能。

---

## 📦 實現方式

### 1. Blue Ocean REST API

Jenkins Blue Ocean 提供了專門的 REST API 端點：

```
GET /blue/rest/organizations/jenkins/pipelines/{job_name}/runs/{build_number}/nodes/
```

這個 API 返回 Pipeline 的所有 Stage/Node 資訊，包括：
- Stage 名稱
- 執行結果（SUCCESS, FAILURE, UNSTABLE, ABORTED）
- 執行時間
- 錯誤訊息

---

## 🚀 使用方法

### 方法 1: 使用 REST API（推薦）

#### 同步 Pipeline Stage 資訊
```bash
curl -X POST http://localhost/api/jenkins-builds/{build_id}/pipeline_stages/
```

#### 獲取 Pipeline Stage 資訊
```bash
curl http://localhost/api/jenkins-builds/{build_id}/pipeline_stages/
```

**響應範例**:
```json
{
    "success": true,
    "build_id": 123,
    "build_number": 456,
    "job_name": "my-pipeline-job",
    "result": "FAILURE",
    "failed_stage": "Build",           // ← 失敗的 Stage 名稱
    "pipeline_summary": {
        "total_stages": 5,
        "successful_stages": 3,
        "failed_stages": 1,             // ← 失敗的 Stage 數量
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
            "name": "Build",            // ← 這個 Stage 失敗了
            "result": "FAILURE",
            "duration_ms": 5678,
            "duration_formatted": "5.7 秒",
            "error_message": "Build step failed with exception"
        }
    ],
    "failed_stages": [                  // ← 所有失敗的 Stage
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

### 方法 2: 使用 Python

```python
from library.services.jenkins_client import JenkinsClient

# 創建客戶端
client = JenkinsClient(
    base_url='http://192.168.1.100:8080',
    username='admin',
    api_token='your-api-token'
)

# 獲取失敗的 Stage
failed_stages = client.get_failed_stages('my-job', 123)

for stage in failed_stages:
    print(f"失敗的 Stage: {stage['stage_name']}")
    print(f"錯誤訊息: {stage['error_message']}")

client.close()
```

---

### 方法 3: 從資料庫查詢

```python
from api.models import JenkinsBuild

# 查詢特定 Build 的失敗 Stage
build = JenkinsBuild.objects.get(id=123)
print(f"失敗的 Stage: {build.failed_stage}")

# 查詢所有在 "Build" Stage 失敗的 Build
builds = JenkinsBuild.objects.filter(failed_stage='Build')
```

---

## 📊 資料儲存位置

### 資料庫欄位

在 `JenkinsBuild` 模型中新增了兩個欄位：

1. **`pipeline_stages`** (JSONField)
   - 存儲完整的 Stage 列表
   - 包含每個 Stage 的詳細資訊

2. **`failed_stage`** (CharField)
   - 存儲第一個失敗的 Stage 名稱
   - 便於快速查詢和過濾

### 查詢範例

```python
# 查詢有失敗 Stage 的 Build
builds_with_failed_stages = JenkinsBuild.objects.exclude(failed_stage='')

# 統計失敗 Stage 分布
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

## 🧪 測試方法

### 1. 執行完整測試
```bash
docker exec nt-django python test_blue_ocean_stages.py
```

### 2. 快速 API 測試
```bash
./scripts/test_blue_ocean_api.sh
```

---

## 📚 完整文檔

詳細使用說明請參考：
- **[Blue Ocean Pipeline Stage 功能文檔](./BLUE_OCEAN_PIPELINE_STAGES.md)**
- **[實現總結](./BLUE_OCEAN_IMPLEMENTATION_SUMMARY.md)**

---

## ⚠️ 注意事項

### 1. 前提條件
- ✅ Jenkins 必須安裝 **Blue Ocean Plugin**
- ✅ Job 必須是 **Pipeline Job**（使用 Jenkinsfile）
- ✅ Build 必須已完成（running 的 Build 可能資訊不完整）

### 2. 非 Pipeline Job
如果 Job 不是 Pipeline，API 會返回：
```json
{
    "success": false,
    "message": "無法獲取 Pipeline Stage 資訊（可能不是 Pipeline Job 或 Blue Ocean 未安裝）"
}
```

### 3. 權限要求
需要有 Jenkins API 訪問權限（username + api_token）

---

## 🎉 總結

✅ **功能已完整實現**  
✅ **支援 REST API 訪問**  
✅ **資料庫持久化存儲**  
✅ **提供 Python 客戶端**  
✅ **完整測試腳本**  
✅ **詳細文檔說明**

現在您可以：
1. 從 Jenkins Blue Ocean API 獲取 Pipeline Stage 資訊
2. 識別哪個 Stage 失敗了
3. 查看失敗 Stage 的錯誤訊息
4. 統計分析失敗 Stage 分布
5. 在資料庫中查詢特定失敗 Stage 的所有 Build

---

**實現日期**: 2025-11-06  
**維護者**: Network Toolbox Team
