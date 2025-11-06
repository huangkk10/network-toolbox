# 在 Web 頁面顯示失敗 Stage 名稱 - 實現說明

**實現日期**: 2025-11-06  
**功能**: 在前端 Jenkins Build 列表中，Failure 狀態旁邊顯示失敗的 Stage 名稱

---

## ✅ 已完成的變更

### 1. 後端 API 更新

**檔案**: `backend/api/views/jenkins.py`

#### 變更內容：

**原本**: 從 Jenkins API 實時獲取 Builds（無 failed_stage 欄位）  
**現在**: 從資料庫獲取 Builds（包含 failed_stage 欄位）

**API 端點**: `GET /api/jenkins-jobs/{id}/builds/`

**新的響應格式**:
```json
{
    "job_id": 123,
    "job_name": "my-pipeline-job",
    "total_builds": 100,
    "builds": [
        {
            "id": 456,
            "build_number": 10,
            "result": "FAILURE",
            "failed_stage": "Build",  // ← 新增欄位
            "build_timestamp": "2025-11-03 19:51:29",
            "duration": 28.57,
            "duration_formatted": "28 秒",
            "url": "http://192.168.1.100:8080/job/my-job/10/",
            "building": false
        }
    ]
}
```

**優點**:
- ✅ 包含 `failed_stage` 欄位
- ✅ 從資料庫讀取，效能更好
- ✅ 支援更複雜的查詢和過濾
- ✅ 資料持久化，不依賴 Jenkins 連線

---

### 2. 前端頁面更新

**檔案**: `frontend/src/pages/RVTAnalysisPage.js`

#### 變更 1: 獲取 Build 時包含 `failed_stage`

```javascript
const builds = response.data.builds.map(build => ({
    key: `build-${build.build_number}`,
    type: 'build',
    build_id: build.id,
    build_number: build.build_number,
    result: build.result || build.status,
    failed_stage: build.failed_stage || null,  // ← 新增
    build_timestamp: build.build_timestamp,
    duration: build.duration_formatted || `${build.duration}s`,
    url: build.url,
    job_id: record.job_id,
    job_name: record.name,
}));
```

#### 變更 2: 在狀態欄位顯示失敗 Stage

```javascript
{
    title: '狀態',
    dataIndex: 'status',
    key: 'status',
    width: 250,  // 調整寬度以容納 Stage 標籤
    render: (text, record) => {
        if (record.type === 'job') {
            return text === 'active' 
                ? <Tag color="success">🟢 Active</Tag>
                : <Tag color="default">⚪ Inactive</Tag>;
        } else {
            const statusMap = {
                'SUCCESS': { color: 'success', text: '✅ Success' },
                'FAILURE': { color: 'error', text: '❌ Failure' },
                'UNSTABLE': { color: 'warning', text: '⚠️ Unstable' },
                'ABORTED': { color: 'default', text: '🚫 Aborted' },
                'RUNNING': { color: 'processing', text: '🔄 Running' },
            };
            const config = statusMap[record.result] || statusMap['SUCCESS'];
            
            // ← 新增：如果是失敗且有 failed_stage，顯示在旁邊
            return (
                <Space>
                    <Tag color={config.color}>{config.text}</Tag>
                    {record.result === 'FAILURE' && record.failed_stage && (
                        <Tooltip title="失敗的 Stage">
                            <Tag color="red" style={{ fontSize: 11 }}>
                                📍 {record.failed_stage}
                            </Tag>
                        </Tooltip>
                    )}
                </Space>
            );
        }
    },
},
```

---

## 🎨 UI 效果

### 顯示效果：

**Build 狀態列**:
```
❌ Failure    📍 Build
```

- **左側**: Failure 狀態標籤（紅色）
- **右側**: 失敗的 Stage 名稱標籤（紅色，小字體）
- **Tooltip**: 滑鼠懸停顯示「失敗的 Stage」

### 只在以下情況顯示 Stage 名稱：
1. ✅ Build 結果為 `FAILURE`
2. ✅ 有 `failed_stage` 資料（已同步過 Pipeline Stage）

---

## 🚀 使用方式

### 1. 確保 Build 已同步 Pipeline Stage 資訊

**方法 1**: 手動同步單個 Build
```bash
curl -X POST http://localhost/api/jenkins-builds/{build_id}/pipeline_stages/
```

**方法 2**: 批次同步（Python 腳本）
```python
from api.models import JenkinsBuild
from library.services.jenkins_client import JenkinsClient

builds = JenkinsBuild.objects.filter(
    result='FAILURE',
    failed_stage=''  # 還沒同步的
).select_related('job__server')

for build in builds:
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
        failed_stages = client.get_failed_stages(
            build.job.name, 
            build.build_number
        )
        
        if failed_stages:
            build.failed_stage = failed_stages[0]['stage_name']
            build.save(update_fields=['failed_stage'])
            print(f"✅ Synced: Build #{build.build_number} -> {build.failed_stage}")
    
    client.close()
```

### 2. 在前端頁面查看

1. 訪問：http://localhost/rvt-analysis?tab=details
2. 選擇一個 Jenkins Server
3. 展開一個 Job
4. 查看失敗的 Build，狀態欄會顯示失敗的 Stage 名稱

---

## 📊 範例截圖說明

### 展開前（Job 列表）:
```
📁 SAF222_K04  [0 Builds]  🔵 SAF_222  🟢 Active
```

### 展開後（Build 列表）:
```
   #4  🔵 SAF_222  ❌ Failure 📍 Build  2025-10-30 10:31:14  28 分 57 秒  [日誌] [詳情]
   #3  🔵 SAF_222  ✅ Success             2025-10-30 20:55:32  8 秒          [日誌] [詳情]
   #2  🔵 SAF_222  ✅ Success             2025-10-30 17:22:18  4 秒          [日誌] [詳情]
```

**說明**:
- Build #4 失敗，顯示失敗的 Stage 是「Build」
- Build #3, #2 成功，不顯示 Stage 資訊

---

## ⚠️ 注意事項

### 1. 資料來源切換

**之前**: 從 Jenkins API 實時獲取（每次都要連接 Jenkins）  
**現在**: 從資料庫獲取（需要先同步資料到資料庫）

**影響**:
- ✅ 優點：速度更快，不需要 Jenkins 在線
- ⚠️ 注意：資料庫需要先同步 Builds（使用 Celery 任務）

### 2. failed_stage 欄位何時有值？

- ✅ Build 必須是 **Pipeline Job**
- ✅ Jenkins 必須安裝 **Blue Ocean Plugin**
- ✅ 必須呼叫過 `POST /api/jenkins-builds/{id}/pipeline_stages/` 同步

**檢查方式**:
```python
from api.models import JenkinsBuild

# 查詢有 failed_stage 的 Build
builds_with_stage = JenkinsBuild.objects.exclude(failed_stage='')
print(f"有 Stage 資訊的 Build: {builds_with_stage.count()}")

# 查詢失敗但沒有 Stage 資訊的 Build
failed_no_stage = JenkinsBuild.objects.filter(
    result='FAILURE',
    failed_stage=''
)
print(f"需要同步的失敗 Build: {failed_no_stage.count()}")
```

### 3. 自動同步（未來功能）

目前 failed_stage 需要手動同步。未來可以添加 Celery 定時任務：

```python
# backend/api/tasks.py
@shared_task
def auto_sync_failed_stages():
    """自動同步失敗 Build 的 Pipeline Stage 資訊"""
    failed_builds = JenkinsBuild.objects.filter(
        result='FAILURE',
        failed_stage='',
        is_building=False
    ).select_related('job__server')
    
    for build in failed_builds[:50]:  # 每次最多 50 個
        try:
            # 同步邏輯...
            pass
        except Exception as e:
            logger.error(f"同步失敗: {e}")
```

---

## 🧪 測試方法

### 1. 測試 API

```bash
# 獲取 Job 的 Builds（應該包含 failed_stage）
curl http://localhost/api/jenkins-jobs/123/builds/?limit=10 | jq '.builds[] | {build_number, result, failed_stage}'
```

**預期輸出**:
```json
{
  "build_number": 4,
  "result": "FAILURE",
  "failed_stage": "Build"
}
{
  "build_number": 3,
  "result": "SUCCESS",
  "failed_stage": null
}
```

### 2. 測試前端

1. 訪問 RVT 分析頁面
2. 展開一個失敗的 Build
3. 檢查狀態欄是否顯示失敗的 Stage 名稱

---

## 📚 相關文檔

- [Blue Ocean Pipeline Stage 功能文檔](./BLUE_OCEAN_PIPELINE_STAGES.md)
- [實現總結](./BLUE_OCEAN_IMPLEMENTATION_SUMMARY.md)
- [快速開始指南](./QUICK_START_BLUE_OCEAN.md)

---

## ✅ 完成清單

- [x] 後端 API 從資料庫返回 `failed_stage` 欄位
- [x] 前端接收並存儲 `failed_stage` 資料
- [x] 前端 UI 在 Failure 旁顯示 Stage 名稱
- [x] 添加 Tooltip 提示
- [x] 調整欄位寬度以容納 Stage 標籤
- [x] Django 服務重啟
- [x] 創建測試文檔

---

**實現者**: GitHub Copilot  
**審查者**: Network Toolbox Team  
**日期**: 2025-11-06
