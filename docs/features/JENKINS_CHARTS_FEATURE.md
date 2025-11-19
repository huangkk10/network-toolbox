# Jenkins 圖表可視化功能

## 概述

在 RVT Analysis 頁面新增了 Jenkins Build 趨勢圖表，提供直觀的視覺化分析功能。

## 功能特性

### 1. 三種圖表類型

#### Build 趨勢線圖
- **功能**: 顯示成功、失敗和總構建數的時間趨勢
- **圖表類型**: 折線圖 (Line Chart)
- **數據項**:
  - 成功構建 (綠色實線)
  - 失敗構建 (紅色實線)
  - 總構建數 (藍色虛線)

#### 成功率趨勢面積圖
- **功能**: 顯示構建成功率的變化趨勢
- **圖表類型**: 面積圖 (Area Chart)
- **數據範圍**: 0-100%
- **視覺效果**: 綠色漸層填充

#### Build 數量長條圖
- **功能**: 顯示成功和失敗構建的堆疊分佈
- **圖表類型**: 堆疊長條圖 (Stacked Bar Chart)
- **視覺效果**: 綠色 (成功) 和紅色 (失敗) 堆疊

### 2. 時間範圍支援

| 時間範圍 | 值 | 粒度 | 說明 |
|---------|---|------|------|
| 今日 | `today` | 每小時 | 從今天 00:00 開始 |
| 最近 7 天 | `week` | 每日 | 過去 7 天的數據 |
| 最近 14 天 | `2weeks` | 每日 | 過去 14 天的數據 |
| 最近 30 天 | `month` | 每日 | 過去 30 天的數據 |
| 全部時間 | `all` | 每日 | 從第一筆 Build 開始 |

### 3. 自動粒度選擇

- **今日**: 自動使用每小時粒度
- **其他時間範圍**: 自動使用每日粒度
- 可以通過 API 參數 `granularity` 手動指定

## 技術實現

### 後端 API

#### 新增端點
```
GET /api/jenkins-analytics/build-trend/
```

#### 請求參數
- `time_range`: 時間範圍 (預設: `today`)
- `granularity`: 粒度 `hourly` | `daily` (可選，自動推斷)
- `server_id`: Jenkins 伺服器 ID (預設: `all`)

#### 響應格式
```json
[
  {
    "time": "11/17 14:00",
    "total_builds": 45,
    "success_count": 32,
    "failure_count": 13,
    "success_rate": 71.1
  }
]
```

#### 實現檔案
- **API 端點**: `backend/api/views/jenkins.py` - `jenkins_build_trend()`
- **URL 路由**: `backend/api/urls.py` - `jenkins-analytics/build-trend/`
- **模型**: 使用 `JenkinsBuild` 模型
- **查詢邏輯**: 
  - 按時間範圍過濾
  - 按小時或日期聚合
  - 計算成功率

### 前端組件

#### 新增組件
```
frontend/src/components/jenkins/JenkinsStatisticsCharts.js
```

#### 使用的圖表庫
- **Recharts**: 已在專案中使用的 React 圖表庫
- 版本: `^2.8.0`

#### 組件 Props
```javascript
<JenkinsStatisticsCharts 
    timeRange="today"    // 時間範圍
    serverId="all"       // 伺服器 ID
/>
```

#### 整合位置
- **頁面**: `frontend/src/pages/RVTAnalysisPage.js`
- **位置**: Overview 標籤，統計卡片下方
- **響應式**: 自動適配時間範圍選擇器

## 使用指南

### 查看圖表

1. 導航到 **RVT Analysis** 頁面
2. 確保在 **Overview** 標籤
3. 使用頂部的時間範圍選擇器切換時間範圍
4. 圖表會自動更新顯示相應時間範圍的數據

### 互動功能

- **懸停顯示**: 將鼠標移到圖表上查看詳細數據
- **圖例點擊**: 點擊圖例可以顯示/隱藏特定數據系列
- **自動刷新**: 切換時間範圍時自動重新載入數據

### 狀態處理

- **載入中**: 顯示 Spin 載入動畫
- **無數據**: 顯示 Empty 空狀態提示
- **錯誤**: 顯示 message 錯誤提示

## 測試驗證

### API 測試

```bash
# 測試今日數據
docker exec nt-django python manage.py shell -c "
import requests
response = requests.get('http://localhost:8000/api/jenkins-analytics/build-trend/?time_range=today')
print('Status:', response.status_code)
print('Data points:', len(response.json()))
"

# 測試週數據
docker exec nt-django python manage.py shell -c "
import requests
import json
response = requests.get('http://localhost:8000/api/jenkins-analytics/build-trend/?time_range=week')
data = response.json()
print('Week data points:', len(data))
with_builds = [d for d in data if d['total_builds'] > 0]
if with_builds:
    print('Sample:', json.dumps(with_builds[0], indent=2))
"
```

### 前端測試

1. **視覺檢查**: 打開頁面確認圖表正確渲染
2. **響應式測試**: 切換時間範圍，確認圖表更新
3. **無數據測試**: 選擇沒有數據的時間範圍，確認空狀態顯示
4. **錯誤處理**: 模擬 API 錯誤，確認錯誤提示顯示

### 測試結果

✅ **API 測試通過**
- Status: 200 OK
- 今日數據: 8 個時間點 (每小時)
- 週數據: 8 個時間點 (每日)，7 個有構建數據

✅ **前端組件創建完成**
- 無語法錯誤
- 正確導入 Recharts 組件
- 已整合到 RVTAnalysisPage

## 檔案變更清單

### 後端檔案 (3 個)

1. **`backend/api/views/jenkins.py`**
   - 新增 `jenkins_build_trend()` 函數 (158 行)
   - 實現時間範圍過濾、粒度選擇、數據聚合

2. **`backend/api/views/__init__.py`**
   - 導出 `jenkins_build_trend`

3. **`backend/api/urls.py`**
   - 新增路由: `jenkins-analytics/build-trend/`

### 前端檔案 (2 個)

4. **`frontend/src/components/jenkins/JenkinsStatisticsCharts.js`** (新建)
   - 完整的圖表組件實現
   - 三種圖表類型
   - 自訂 Tooltip 樣式
   - 響應式設計

5. **`frontend/src/pages/RVTAnalysisPage.js`**
   - 導入 `JenkinsStatisticsCharts` 組件
   - 在 overview 標籤中渲染圖表
   - 傳遞 `timeRange` 和 `serverId` props

## 性能考量

### 後端優化

- **查詢優化**: 使用 Django ORM 的 `filter()` 和聚合函數
- **時間範圍限制**: 避免查詢過多歷史數據
- **索引**: `build_timestamp` 欄位應有索引 (已有)

### 前端優化

- **懶載入**: 圖表僅在 Overview 標籤時載入
- **響應式**: 使用 `ResponsiveContainer` 自動適配容器大小
- **連線點**: `connectNulls={true}` 連接有數據的點

## 未來增強

### 潛在改進

1. **篩選功能**
   - 按 Jenkins 伺服器篩選
   - 按 Job 名稱篩選
   - 按 View 名稱篩選

2. **更多圖表類型**
   - 失敗原因分佈餅圖
   - 執行時間趨勢圖
   - Top 失敗 Jobs 列表

3. **數據導出**
   - CSV 導出
   - 圖表截圖功能

4. **實時更新**
   - WebSocket 實時推送
   - 自動刷新選項

## 相關文件

- [Celery Queue Configuration Fix](../troubleshooting/CELERY_QUEUE_CONFIGURATION_FIX.md)
- [Jenkins Auto Sync Fix Report](../troubleshooting/JENKINS_AUTO_SYNC_FAILURE_FIX_REPORT.md)
- [Recharts Documentation](https://recharts.org/)

## 維護記錄

| 日期 | 版本 | 作者 | 變更說明 |
|------|------|------|---------|
| 2025-11-19 | 1.0.0 | GitHub Copilot | 初始實現：新增 Jenkins 趨勢圖表功能 |

---

**建議**: 在正式環境部署前，建議進行完整的用戶驗收測試 (UAT)，確保所有時間範圍和邊界情況都正確處理。
