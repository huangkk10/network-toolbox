# Jenkins Blue Ocean Pipeline Stage 追蹤功能

**功能說明**: 從 Jenkins Blue Ocean API 獲取 Pipeline 的 Stage 執行資訊，追蹤哪個 Stage 失敗

**更新時間**: 2025-11-06

---

## 📋 目錄

- [功能概述](#功能概述)
- [資料庫模型](#資料庫模型)
- [API 端點](#api-端點)
- [使用範例](#使用範例)
- [測試方法](#測試方法)
- [常見問題](#常見問題)

---

## 功能概述

### 為什麼需要 Blue Ocean API？

在 Jenkins Pipeline 中，當 Build 失敗時，我們需要知道：
- **哪個 Stage 失敗了？**
- **失敗的 Stage 執行了多久？**
- **錯誤訊息是什麼？**
- **所有 Stage 的執行狀態**

傳統的 Jenkins API 無法提供詳細的 Stage 資訊，但 **Blue Ocean REST API** 提供了完整的 Pipeline 執行詳情。

### 功能特點

✅ **自動追蹤失敗 Stage**：自動識別並記錄失敗的 Stage 名稱  
✅ **完整 Stage 資訊**：記錄每個 Stage 的狀態、執行時間、錯誤訊息  
✅ **統計分析**：統計成功/失敗/不穩定/已中止的 Stage 數量  
✅ **資料庫持久化**：將 Pipeline 資訊存儲在 PostgreSQL 中  
✅ **靈活查詢**：支援按失敗 Stage 查詢 Build

---

## 資料庫模型

### JenkinsBuild 模型新增欄位

```python
class JenkinsBuild(models.Model):
    # ... 原有欄位 ...
    
    # Pipeline Stage 資訊（Blue Ocean）
    pipeline_stages = models.JSONField(
        default=list, 
        blank=True, 
        verbose_name='Pipeline Stages'
    )
    failed_stage = models.CharField(
        max_length=200, 
        blank=True, 
        verbose_name='失敗的 Stage'
    )
```

### pipeline_stages 欄位結構

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
    }
]
```

### failed_stage 欄位

- **類型**: CharField (最多 200 字元)
- **內容**: 第一個失敗的 Stage 名稱
- **範例**: `"Build"`, `"Test"`, `"Deploy"`

---

## API 端點

### 1. 獲取 Build 的 Pipeline Stage 資訊

**GET** `/api/jenkins-builds/{id}/pipeline_stages/`

返回已存儲在資料庫中的 Pipeline Stage 資訊。

**響應範例**:
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

### 2. 同步 Pipeline Stage 資訊

**POST** `/api/jenkins-builds/{id}/pipeline_stages/`

從 Jenkins Blue Ocean API 同步最新的 Pipeline Stage 資訊到資料庫。

**何時使用**:
- Build 剛完成，資料庫還沒有 Stage 資訊
- 需要更新已存在的 Stage 資訊
- 手動觸發同步

**響應範例**:
```json
{
    "success": true,
    "build_id": 123,
    "build_number": 456,
    "job_name": "my-pipeline-job",
    "result": "FAILURE",
    "failed_stage": "Build",
    "pipeline_summary": { ... },
    "stages": [ ... ],
    "failed_stages": [ ... ]
}
```

**錯誤響應** (非 Pipeline Job):
```json
{
    "success": false,
    "message": "無法獲取 Pipeline Stage 資訊（可能不是 Pipeline Job 或 Blue Ocean 未安裝）"
}
```

---

### 3. 查詢有失敗 Stage 的 Build

**GET** `/api/jenkins-builds/?has_failed_stage=true`

查詢所有有失敗 Stage 的 Build。

**響應範例**:
```json
[
    {
        "id": 123,
        "build_number": 456,
        "job_name": "my-pipeline-job",
        "result": "FAILURE",
        "failed_stage": "Build",
        "has_pipeline_stages": true,
        "failed_stages_count": 1
    }
]
```

---

## 使用範例

### Python 範例：使用 JenkinsClient

```python
from library.services.jenkins_client import JenkinsClient

# 創建客戶端
client = JenkinsClient(
    base_url='http://192.168.1.100:8080',
    username='admin',
    api_token='your-api-token'
)

# 1. 獲取所有 Pipeline Nodes
nodes = client.get_blue_ocean_pipeline_nodes('my-job', 123)
print(f"找到 {len(nodes)} 個 Nodes")

# 2. 只獲取失敗的 Stage
failed_stages = client.get_failed_stages('my-job', 123)
for stage in failed_stages:
    print(f"失敗 Stage: {stage['stage_name']}")
    print(f"  錯誤訊息: {stage['error_message']}")

# 3. 獲取 Pipeline 摘要
summary = client.get_pipeline_summary('my-job', 123)
print(f"總 Stage: {summary['total_stages']}")
print(f"失敗: {summary['failed_stages']}")

client.close()
```

### Python 範例：更新資料庫

```python
from api.models import JenkinsBuild
from library.services.jenkins_client import JenkinsClient

# 獲取 Build
build = JenkinsBuild.objects.get(id=123)

# 創建客戶端
client = JenkinsClient(
    base_url=build.job.server.url,
    username=build.job.server.username,
    api_token=build.job.server.api_token
)

# 獲取 Pipeline Nodes
nodes = client.get_blue_ocean_pipeline_nodes(
    build.job.name, 
    build.build_number
)

# 提取 Stage 資訊
stages = [
    {
        'id': node.get('id'),
        'name': node.get('displayName'),
        'result': node.get('result'),
        'duration_ms': node.get('durationInMillis', 0),
        'error': node.get('error')
    }
    for node in nodes if node.get('type') == 'STAGE'
]

# 找出失敗的 Stage
failed_stages_list = client.get_failed_stages(build.job.name, build.build_number)
failed_stage_name = failed_stages_list[0]['stage_name'] if failed_stages_list else ''

# 更新資料庫
build.pipeline_stages = stages
build.failed_stage = failed_stage_name
build.save(update_fields=['pipeline_stages', 'failed_stage'])

print(f"✅ 已更新 Build #{build.build_number}")
print(f"   失敗 Stage: {failed_stage_name}")

client.close()
```

### cURL 範例：API 請求

```bash
# 1. 獲取 Pipeline Stage 資訊
curl -X GET http://localhost/api/jenkins-builds/123/pipeline_stages/

# 2. 同步 Pipeline Stage 資訊
curl -X POST http://localhost/api/jenkins-builds/123/pipeline_stages/

# 3. 查詢有失敗 Stage 的 Build
curl -X GET "http://localhost/api/jenkins-builds/?has_failed_stage=true"
```

### Django ORM 查詢範例

```python
from api.models import JenkinsBuild

# 1. 查詢有 Pipeline Stage 資訊的 Build
builds_with_stages = JenkinsBuild.objects.exclude(pipeline_stages=[])

# 2. 查詢有失敗 Stage 的 Build
builds_with_failed_stages = JenkinsBuild.objects.exclude(failed_stage='')

# 3. 查詢特定 Stage 失敗的 Build
builds_failed_at_build = JenkinsBuild.objects.filter(failed_stage='Build')

# 4. 統計失敗 Stage 分布
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

## 測試方法

### 1. 執行測試腳本

```bash
docker exec nt-django python test_blue_ocean_stages.py
```

測試腳本會執行以下測試：
1. ✅ 測試 JenkinsClient Blue Ocean API 方法
2. ✅ 測試更新資料庫中的 Pipeline Stage 資訊
3. ✅ 測試查詢有 Stage 資訊的 Build

### 2. 測試輸出範例

```
======================================================================
  測試 1: JenkinsClient Blue Ocean API 方法
======================================================================
✅ 使用 Jenkins Server: RVT-Jenkins (http://192.168.1.100:8080)
✅ 測試 Build: pipeline-test #123

📊 測試 get_blue_ocean_pipeline_nodes()...
✅ 成功獲取 8 個 Nodes

📋 Pipeline Stages: (共 5 個)
  ✅ Checkout: SUCCESS (1.2s)
  ✅ Setup: SUCCESS (2.3s)
  ❌ Build: FAILURE (5.7s)
  🚫 Test: ABORTED (0.0s)
  🚫 Deploy: ABORTED (0.0s)

📊 測試 get_failed_stages()...
✅ 找到 1 個失敗的 Stage

  ❌ Stage: Build
     結果: FAILURE
     執行時間: 5.7 秒
     錯誤訊息: Build step failed with exception

📊 測試 get_pipeline_summary()...
✅ Pipeline 摘要:
   總 Stage 數: 5
   成功: 2
   失敗: 1
   不穩定: 0
   已中止: 2
```

### 3. 手動測試 API

使用 Postman 或 cURL：

```bash
# 獲取 Build 123 的 Pipeline Stage 資訊
curl http://localhost/api/jenkins-builds/123/pipeline_stages/

# 同步 Build 123 的 Pipeline Stage 資訊
curl -X POST http://localhost/api/jenkins-builds/123/pipeline_stages/
```

---

## 常見問題

### Q1: 為什麼有些 Build 沒有 Pipeline Stage 資訊？

**可能原因**:
1. **不是 Pipeline Job**: 只有 Pipeline Job（Jenkinsfile）才有 Stage 資訊
2. **Blue Ocean 未安裝**: 需要安裝 Blue Ocean Plugin
3. **尚未同步**: 需要手動呼叫 `POST /api/jenkins-builds/{id}/pipeline_stages/` 同步

**解決方法**:
```bash
# 檢查 Build 是否是 Pipeline
curl http://your-jenkins/job/my-job/123/api/json

# 同步 Pipeline Stage 資訊
curl -X POST http://localhost/api/jenkins-builds/123/pipeline_stages/
```

---

### Q2: Blue Ocean API 端點格式是什麼？

**標準格式**:
```
GET {JENKINS_URL}/blue/rest/organizations/jenkins/pipelines/{JOB_NAME}/runs/{BUILD_NUMBER}/nodes/
```

**範例**:
```
http://192.168.1.100:8080/blue/rest/organizations/jenkins/pipelines/my-pipeline-job/runs/123/nodes/
```

---

### Q3: 如何批次同步所有 Build 的 Pipeline Stage 資訊？

**方法 1: Python 腳本**
```python
from api.models import JenkinsBuild
from library.services.jenkins_client import JenkinsClient

# 獲取所有失敗的 Build 且沒有 Stage 資訊
builds = JenkinsBuild.objects.filter(
    result='FAILURE',
    pipeline_stages=[]
).select_related('job', 'job__server')

for build in builds:
    try:
        client = JenkinsClient(
            base_url=build.job.server.url,
            username=build.job.server.username,
            api_token=build.job.server.api_token
        )
        
        nodes = client.get_blue_ocean_pipeline_nodes(
            build.job.name, 
            build.build_number
        )
        
        if nodes:
            # 更新資料庫 (同上面的範例)
            print(f"✅ 同步 Build #{build.build_number}")
        
        client.close()
    except Exception as e:
        print(f"❌ 失敗: {e}")
```

**方法 2: Celery 定時任務** (未來功能)

---

### Q4: failed_stage 欄位只記錄第一個失敗的 Stage？

是的，`failed_stage` 欄位只記錄**第一個失敗的 Stage**，但完整的失敗 Stage 列表存儲在 `pipeline_stages` JSONField 中。

**獲取所有失敗的 Stage**:
```python
build = JenkinsBuild.objects.get(id=123)

# 過濾出所有失敗的 Stage
failed_stages = [
    s for s in build.pipeline_stages 
    if s.get('result') in ['FAILURE', 'UNSTABLE', 'ABORTED']
]

print(f"失敗的 Stage: {[s['name'] for s in failed_stages]}")
```

---

### Q5: 如何在前端顯示 Pipeline Stage 進度條？

**React 前端範例** (使用 Ant Design):
```jsx
import { Steps, Tag } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';

const PipelineStages = ({ stages }) => {
    const items = stages.map(stage => {
        const statusMap = {
            'SUCCESS': 'finish',
            'FAILURE': 'error',
            'ABORTED': 'error',
            'UNSTABLE': 'error',
        };
        
        const iconMap = {
            'SUCCESS': <CheckCircleOutlined />,
            'FAILURE': <CloseCircleOutlined />,
        };
        
        return {
            title: stage.name,
            status: statusMap[stage.result] || 'wait',
            icon: iconMap[stage.result],
            description: stage.duration_formatted,
        };
    });
    
    return (
        <Steps
            current={stages.length}
            items={items}
            direction="vertical"
        />
    );
};
```

---

## 相關資源

- **Jenkins Blue Ocean 文檔**: https://www.jenkins.io/doc/book/blueocean/
- **Blue Ocean REST API**: https://github.com/jenkinsci/blueocean-plugin/tree/master/blueocean-rest
- **Jenkins REST API 文檔**: https://www.jenkins.io/doc/book/using/remote-access-api/

---

## 版本歷史

| 版本 | 日期 | 變更內容 |
|------|------|----------|
| 1.0.0 | 2025-11-06 | 初始版本：添加 Blue Ocean Pipeline Stage 追蹤功能 |

---

**維護者**: Network Toolbox Team  
**更新時間**: 2025-11-06
