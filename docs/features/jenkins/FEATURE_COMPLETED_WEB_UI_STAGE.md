# ✅ 功能完成：在 Web 頁面顯示失敗 Stage 名稱

## 🎯 您的需求

**問題**: 可以在 web 裡，Failure 旁邊顯示 stage 的名稱嗎?

**答案**: ✅ **已完成！**

---

## 📦 實現內容

### 顯示效果

在 Jenkins Build 列表的狀態欄中：

```
原本：❌ Failure

現在：❌ Failure    📍 Build
      ↑ 狀態        ↑ 失敗的 Stage 名稱
```

### 功能特點

✅ **自動顯示**: 失敗的 Build 自動顯示失敗的 Stage  
✅ **視覺清晰**: 使用紅色標籤和圖標（📍）標示  
✅ **Tooltip 提示**: 滑鼠懸停顯示「失敗的 Stage」  
✅ **條件顯示**: 只有失敗且有 Stage 資料的 Build 才顯示  

---

## 🔧 修改的檔案

### 1. 後端 API
**檔案**: `backend/api/views/jenkins.py`

**變更**: 
- 從 Jenkins API 實時獲取 → 從資料庫獲取
- 新增返回 `failed_stage` 欄位

### 2. 前端頁面
**檔案**: `frontend/src/pages/RVTAnalysisPage.js`

**變更**:
- 接收 `failed_stage` 欄位
- 在狀態列顯示失敗 Stage 名稱
- 添加 Tooltip
- 調整欄位寬度

---

## 🚀 使用方式

### 步驟 1: 確保 Build 已同步 Pipeline Stage 資訊

**同步單個 Build**:
```bash
curl -X POST http://localhost/api/jenkins-builds/{build_id}/pipeline_stages/
```

**批次同步** (如果有很多失敗的 Build):
```bash
docker exec nt-django python test_blue_ocean_stages.py
```

### 步驟 2: 在前端查看

1. 訪問：http://localhost/rvt-analysis?tab=details
2. 選擇一個 Jenkins Server
3. 展開一個 Job
4. 查看失敗的 Build

**您會看到**:
```
#4  ❌ Failure 📍 Build  2025-10-30 10:31:14  28 分 57 秒
    ↑ 紅色標籤        ↑ 失敗在 Build Stage
```

---

## 📊 實際範例（根據您的截圖）

### SAF222_K04 Job:

**Build #4** (失敗):
```
狀態欄顯示：
❌ Failure    📍 Build
```

**說明**:
- 這個 Build 在 **Build Stage** 失敗了
- 執行時間：28 分 57 秒
- 失敗時間：2025-10-30 10:31:14

### SAF222_K03 Job:

**Build #1** (成功):
```
狀態欄顯示：
✅ Success
```

**說明**:
- 成功的 Build 不顯示 Stage 資訊
- 只有失敗的 Build 才顯示失敗的 Stage

---

## ⚙️ 技術細節

### API 響應格式

**端點**: `GET /api/jenkins-jobs/{job_id}/builds/`

**響應範例**:
```json
{
    "job_id": 123,
    "job_name": "SAF222_K04",
    "total_builds": 4,
    "builds": [
        {
            "id": 456,
            "build_number": 4,
            "result": "FAILURE",
            "failed_stage": "Build",     // ← 關鍵欄位
            "build_timestamp": "2025-10-30 10:31:14",
            "duration": 1737.0,
            "duration_formatted": "28 分 57 秒",
            "url": "http://192.168.1.100:8080/job/SAF222_K04/4/"
        }
    ]
}
```

### 前端渲染邏輯

```javascript
// 如果是失敗且有 failed_stage，顯示在旁邊
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
```

---

## ⚠️ 注意事項

### 何時會顯示失敗 Stage？

需要滿足以下條件：
1. ✅ Build 結果為 `FAILURE`
2. ✅ Jenkins 安裝了 **Blue Ocean Plugin**
3. ✅ Job 是 **Pipeline Job**（使用 Jenkinsfile）
4. ✅ Build 已同步過 Pipeline Stage 資訊

### 如果沒有顯示 Stage 名稱？

**原因**: Build 還沒同步 Pipeline Stage 資訊

**解決方法**:
```bash
# 同步單個 Build
curl -X POST http://localhost/api/jenkins-builds/{build_id}/pipeline_stages/

# 或使用測試腳本批次同步
docker exec nt-django python test_blue_ocean_stages.py
```

---

## 📚 完整文檔

詳細技術文檔請參考：
- [Web UI 失敗 Stage 顯示](./WEB_UI_FAILED_STAGE_DISPLAY.md) - 實現說明
- [Blue Ocean Pipeline Stages](./BLUE_OCEAN_PIPELINE_STAGES.md) - 功能文檔
- [實現總結](./BLUE_OCEAN_IMPLEMENTATION_SUMMARY.md) - 技術細節

---

## 🎉 總結

✅ **功能已完成**  
✅ **前端已更新**  
✅ **後端已更新**  
✅ **文檔已完成**  

現在您可以在 Web 頁面上直接看到每個失敗 Build 是在哪個 Stage 失敗的！

**預覽效果**:
```
Job: SAF222_K04
├── Build #4  ❌ Failure 📍 Build      28 分 57 秒  ← 在 Build Stage 失敗
├── Build #3  ✅ Success                8 秒
├── Build #2  ✅ Success                4 秒
└── Build #1  ✅ Success                5 秒
```

---

**實現時間**: 2025-11-06  
**狀態**: ✅ 已完成並測試
