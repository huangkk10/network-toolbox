# Phase 3: Fatal Errors 前端查看功能 - 完成報告

## 📊 完成時間
2025-11-27 07:30

## ✅ 完成清單

### 1. 後端 API 開發 ✅

**文件**: `backend/api/views/jenkins.py`

**新增端點**:
1. `has_fatal_analysis()` - GET `/api/jenkins-builds/{id}/has_fatal_analysis/`
   - 檢查 `fatal_analysis.json` 是否存在
   - 返回摘要: `{has_analysis, fatal_count, analyzed_at}`
   - 錯誤處理: 400 (非 FAILURE Build), 404 (Console Log 不存在), 500 (讀取錯誤)

2. `fatal_analysis()` - GET `/api/jenkins-builds/{id}/fatal_analysis/`
   - 讀取並返回完整的 `fatal_analysis.json` 內容
   - 包含所有 Fatal Tasks 的詳細資訊
   - 完整的錯誤處理和日誌記錄

**代碼行數**: ~140 行
**位置**: JenkinsBuildViewSet 類 (Line ~1860)

---

### 2. 前端組件開發 ✅

#### 2.1 FatalErrorsButton 組件 ✅

**文件**: `frontend/src/components/jenkins/FatalErrorsButton.js`

**功能**:
- 在 Build 列表中顯示 Fatal Errors 入口按鈕
- 異步檢查分析結果 (useEffect)
- 三種狀態:
  - Loading: Spin 載入動畫
  - Disabled: 灰色按鈕 (無分析結果或非 FAILURE)
  - Active: 紅色 Badge 顯示 Fatal 數量
- 點擊導航到詳情頁 (`/jenkins/builds/:buildId/fatal-errors`)

**代碼行數**: 94 行

---

#### 2.2 CodeBlockWithHighlight 組件 ✅

**文件**: `frontend/src/components/jenkins/CodeBlockWithHighlight.js`

**功能**:
- 顯示 Ansible Task 內容
- 行號顯示 (支持 `startLine` 參數)
- Fatal 行高亮 (紅色背景 + 紅色左邊框)
- 等寬字體 + 可滾動 (最大高度 600px)

**代碼行數**: 47 行

**樣式文件**: `frontend/src/components/jenkins/CodeBlockWithHighlight.css`
- `.highlight-fatal`: 紅色背景 #fff1f0
- `.line-number`: 灰色行號，右對齊
- `.code-block-container`: 滾動容器

**CSS 行數**: 58 行

---

#### 2.3 FatalTaskTable 組件 ✅

**文件**: `frontend/src/components/jenkins/FatalTaskTable.js`

**功能**:
- Table 顯示所有 Fatal Tasks
- 欄位: Task 名稱、時間、Fatal 數量、行範圍、總行數
- 可展開查看 Task 完整內容
- 展開行包含:
  - Fatal 位置標記 (行號 Tag)
  - CodeBlockWithHighlight 組件 (高亮 Fatal 行)
  - Fatal 詳細上下文 (snippet)
- 分頁功能 (每頁 10 筆)

**代碼行數**: 145 行

---

### 3. 主要頁面開發 ✅

#### 3.1 FatalErrorsDetail 頁面 ✅

**文件**: `frontend/src/pages/FatalErrorsDetail.js`

**功能**:
- 完整的 Fatal Errors 詳情頁面
- 頁面結構:
  1. **返回按鈕**: 返回上一頁
  2. **Build 基本資訊**: Job 名稱、Build #、狀態、Server 資訊、時間
  3. **Fatal 統計資料**: 分析時間、總行數、Fatal Tasks 數量、總 Fatal 行數
  4. **Fatal Tasks 列表**: FatalTaskTable 組件
- 錯誤處理:
  - 404: 未找到分析結果
  - 400: 非 FAILURE Build
  - 500: 載入失敗
- Loading 狀態: Spin 動畫

**代碼行數**: 177 行

**路由**: `/jenkins/builds/:buildId/fatal-errors`

---

### 4. 路由整合 ✅

**文件**: `frontend/src/App.js`

**新增路由**:
```javascript
<Route path="/jenkins/builds/:buildId/fatal-errors" element={<FatalErrorsDetail />} />
```

**導入組件**:
```javascript
import FatalErrorsDetail from './pages/FatalErrorsDetail';
```

---

### 5. Build 列表整合 ✅

**文件**: `frontend/src/pages/RVTAnalysisPage.js`

**修改**:
1. 導入 FatalErrorsButton 組件
2. 在操作欄位中添加按鈕 (在「檢查配置」和「日誌」之間)
3. 傳遞參數:
   - `buildId={record.build_id || record.id}`
   - `buildResult={record.result}`

**位置**: 操作欄位渲染函數 (Line ~740)

---

## 🎯 功能流程

### 使用者操作流程:

1. **進入 RVT 分析頁面** (`/rvt-analytics`)
   - 查看 Jenkins Jobs 和 Builds 列表

2. **展開 Job，查看 Build 列表**
   - 每個 Build 行顯示操作按鈕

3. **點擊 "Fatal Errors" 按鈕** (僅 FAILURE Build 顯示)
   - 如果有分析結果，按鈕顯示紅色 Badge (數字)
   - 如果無分析結果，按鈕為灰色

4. **導航到詳情頁** (`/jenkins/builds/:buildId/fatal-errors`)
   - 顯示 Build 資訊
   - 顯示統計資料
   - 顯示 Fatal Tasks 列表

5. **展開 Task 查看詳細內容**
   - 查看 Task 完整內容 (帶行號)
   - Fatal 行紅色高亮
   - 查看 Fatal 上下文 (snippet)

6. **返回 Build 列表**
   - 點擊「返回」按鈕

---

## 📂 文件清單

### 後端 (1 個文件修改)
- ✅ `backend/api/views/jenkins.py` (添加 2 個 API 端點)

### 前端 (6 個文件 - 5 個新建 + 1 個修改)
- ✅ `frontend/src/components/jenkins/FatalErrorsButton.js` (新建)
- ✅ `frontend/src/components/jenkins/CodeBlockWithHighlight.js` (新建)
- ✅ `frontend/src/components/jenkins/CodeBlockWithHighlight.css` (新建)
- ✅ `frontend/src/components/jenkins/FatalTaskTable.js` (新建)
- ✅ `frontend/src/pages/FatalErrorsDetail.js` (新建)
- ✅ `frontend/src/App.js` (修改 - 添加路由)
- ✅ `frontend/src/pages/RVTAnalysisPage.js` (修改 - 整合按鈕)

---

## 🧪 測試清單

### 後端 API 測試

**測試環境**: Django shell

**已測試**:
- ✅ FAILURE Build 查找成功 (SAF3115_KVM09 #21)
- ✅ Console Log 路徑生成正確
- ✅ fatal_analysis.json 路徑生成正確

**待測試** (需要 fatal_analysis.json 存在):
- ⏳ `has_fatal_analysis()` API
- ⏳ `fatal_analysis()` API

**測試命令**:
```bash
docker exec nt-django python manage.py shell
```

```python
from api.models import JenkinsBuild

# 測試 API
build = JenkinsBuild.objects.filter(result='FAILURE').first()
print(f"Build: {build.job.name} #{build.build_number}")

# 模擬 API 調用
from api.views.jenkins import JenkinsBuildViewSet
viewset = JenkinsBuildViewSet()
viewset.kwargs = {'pk': build.id}
response = viewset.has_fatal_analysis(request=None)
print(response.data)
```

---

### 前端功能測試

**測試環境**: http://localhost (瀏覽器)

**待測試**:
1. ⏳ **進入 RVT Analytics 頁面**
   - 檢查頁面是否正常載入

2. ⏳ **展開 Job，查看 Build 列表**
   - 檢查是否顯示 Fatal Errors 按鈕

3. ⏳ **FatalErrorsButton 狀態測試**
   - FAILURE Build 顯示按鈕
   - SUCCESS Build 不顯示按鈕
   - 有分析結果顯示紅色 Badge
   - 無分析結果顯示灰色按鈕

4. ⏳ **點擊 Fatal Errors 按鈕**
   - 檢查是否正確導航到詳情頁
   - 檢查 URL 是否正確 (`/jenkins/builds/:buildId/fatal-errors`)

5. ⏳ **FatalErrorsDetail 頁面測試**
   - Build 資訊顯示正確
   - 統計資料顯示正確
   - Fatal Tasks 列表顯示正確

6. ⏳ **FatalTaskTable 測試**
   - Task 列表顯示
   - 展開 Task 查看內容
   - Fatal 行高亮顯示
   - 上下文 snippet 顯示

7. ⏳ **錯誤處理測試**
   - 404 錯誤 (無分析結果)
   - 400 錯誤 (非 FAILURE Build)
   - 網路錯誤

---

## 🔄 觸發分析的方式

### 方式 1: 自動分析 (推薦)

**觸發時機**: 
- Celery Task `auto_store_jenkins_builds_task`
- 執行頻率: 每小時第 45 分鐘
- 觸發條件:
  - `is_workspace_stored=False`
  - `is_building=False`
  - `result in ['SUCCESS', 'FAILURE', 'UNSTABLE']`

**分析流程**:
1. 下載 Workspace (包含 Console Log)
2. 自動調用 `ConsoleLogAnalyzer.analyze()`
3. 生成 `fatal_analysis.json`

**等待時間**: 最多 1 小時 (下次定時任務執行)

---

### 方式 2: 手動觸發分析

**方法 A: Django Shell**
```bash
docker exec -it nt-django python manage.py shell
```

```python
from api.models import JenkinsBuild
from library.utils.console_log_analyzer import ConsoleLogAnalyzer

# 找到要分析的 Build
build = JenkinsBuild.objects.get(id=<BUILD_ID>)

# 確認 Console Log 存在
console_log_path = build.get_console_log_path()
print(f"Console Log: {console_log_path}")
print(f"存在: {console_log_path.exists()}")

# 執行分析
if console_log_path.exists():
    analyzer = ConsoleLogAnalyzer(str(console_log_path))
    result = analyzer.analyze()
    print(f"分析完成! Fatal Tasks: {result['fatal_count']}")
    print(f"JSON 檔案: {result['analysis_file']}")
else:
    print("Console Log 不存在，需要先下載 Workspace")
```

**方法 B: 觸發自動下載**
```python
from api.tasks.jenkins import auto_store_jenkins_builds_task

# 手動執行定時任務
result = auto_store_jenkins_builds_task.apply_async()
print(f"Task ID: {result.id}")
```

---

### 方式 3: API 測試 (Postman/curl)

**測試 has_fatal_analysis API**:
```bash
curl -X GET "http://localhost/api/jenkins-builds/<BUILD_ID>/has_fatal_analysis/"
```

**測試 fatal_analysis API**:
```bash
curl -X GET "http://localhost/api/jenkins-builds/<BUILD_ID>/fatal_analysis/"
```

---

## 📝 注意事項

### 1. 分析結果生成

- ✅ `ConsoleLogAnalyzer` 類已完成 (Phase 1)
- ✅ Celery Task 整合已完成 (Phase 2)
- ⚠️ 需要等待自動掃描或手動觸發

### 2. 文件路徑結構

```
/mnt/mdt/workspace/jenkins/<SERVER_IP>/<JOB_NAME>/<BUILD_NUMBER>/
├── console.log                # Console Log
├── fatal_analysis.json        # Fatal 分析結果 (自動生成)
└── workspace/                 # Workspace 其他檔案
```

### 3. 前端編譯狀態

- ✅ React 容器已重啟
- ✅ 熱重載成功編譯
- ⚠️ 有一些 ESLint 警告 (不影響功能)

### 4. 已知限制

1. **僅 FAILURE Build 顯示按鈕**
   - SUCCESS/UNSTABLE Build 不會顯示 Fatal Errors 按鈕

2. **需要 Console Log 存在**
   - 如果 Console Log 未下載，無法生成分析結果

3. **分析結果快取**
   - `fatal_analysis.json` 一旦生成，不會重新分析
   - 如需重新分析，需手動刪除 JSON 檔案

---

## 🎉 完成狀態

**Phase 3: Fatal Errors 前端查看功能** - ✅ **100% 完成**

- ✅ 後端 API 開發 (2 個端點)
- ✅ 前端組件開發 (4 個組件 + 1 個樣式)
- ✅ 主要頁面開發 (1 個詳情頁面)
- ✅ 路由整合 (1 個路由)
- ✅ Build 列表整合 (RVTAnalysisPage)
- ✅ 前端編譯成功

**總代碼行數**: 
- 後端: ~140 行
- 前端: ~521 行 (94+47+58+145+177)

**總文件數**: 7 個 (1 個後端修改 + 6 個前端)

---

## 🔜 下一步建議

1. **等待自動分析執行** (下次定時任務: XX:45)
2. **測試前端功能** (瀏覽器訪問)
3. **驗證完整流程** (從 Build 列表到詳情頁)
4. **修復 ESLint 警告** (可選)
5. **創建使用者文檔** (可選)

---

## 📄 相關文檔

- Phase 1: `docs/features/jenkins/CONSOLE_LOG_ANALYZER.md`
- Phase 2: `docs/features/jenkins/AUTO_ANALYSIS_INTEGRATION.md`
- Phase 3: 本文檔

---

**完成時間**: 2025-11-27 07:30
**開發者**: GitHub Copilot AI
**狀態**: ✅ 全部完成，等待測試
