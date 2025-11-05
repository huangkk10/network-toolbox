# Jenkins View 支持說明

## 📋 功能概述

已為 RVT 分析頁面添加 **Jenkins View（視圖）** 支持，可以顯示每個 Job 所屬的 View 分類。

---

## 🎯 實現內容

### 1. 後端更改

#### 1.1 數據模型（JenkinsJob）
添加了 `view_name` 字段：

```python
# backend/api/models.py
class JenkinsJob(models.Model):
    # ... 其他字段
    view_name = models.CharField(
        max_length=200, 
        blank=True, 
        default='', 
        verbose_name='所屬 View'
    )
```

**數據庫遷移**：
- 文件：`api/migrations/0013_add_view_name_to_jenkins_job.py`
- 已執行完成

#### 1.2 Jenkins API 客戶端擴展
在 `library/services/jenkins_client.py` 添加了兩個新方法：

```python
def list_views(self) -> List[Dict[str, Any]]:
    """列出所有 View (視圖)"""
    # 獲取所有 Views: EG8-PP, PC51Q-PP, PM9M1-PP, SAF7518, SAF_222, all

def get_view_jobs(self, view_name: str) -> List[Dict[str, Any]]:
    """獲取指定 View 下的所有 Job"""
    # 例如：GET /view/EG8-PP/api/json
```

#### 1.3 同步邏輯更新
`backend/api/views/jenkins.py` 的 `sync_jobs` 方法現在會：

1. **獲取所有 Views**
2. **為每個 View 獲取其下的 Jobs**
3. **建立 Job → View 映射關係**
4. **同步時將 View 信息存入數據庫**

**邏輯說明**：
- 跳過 "all" 視圖（包含所有 Job）
- 如果 Job 屬於多個 View，取第一個非 "all" 的 View
- 未分類的 Job 的 `view_name` 為空字符串

---

### 2. 前端更改

#### 2.1 新增 View 欄位
在 RVT 分析頁面的表格中，添加了「View」欄位：

**位置**：Job / Build 列之後
**寬度**：150px
**顯示邏輯**：
- 有 View：顯示藍色 Tag（例如：`EG8-PP`）
- 無 View：顯示灰色 Tag（`未分類`）
- Build 行：顯示「-」

```jsx
{
    title: 'View',
    dataIndex: 'view_name',
    key: 'view_name',
    width: 150,
    render: (text, record) => {
        if (record.type === 'job') {
            if (text) {
                return <Tag color="geekblue">{text}</Tag>;
            } else {
                return <Tag color="default">未分類</Tag>;
            }
        } else {
            return <span style={{ color: '#ccc' }}>-</span>;
        }
    },
}
```

#### 2.2 修正用語
- **「選擇伺服器」** → **「選擇 Jenkins」**
- 更符合實際使用情境

---

## 📊 當前數據統計

```
Jenkins Views 分布：
==================================================
  (未分類)                → 20 Jobs
  EG8-PP               →  6 Jobs
  PC51Q-PP             →  4 Jobs
  PM9M1-PP             →  4 Jobs
  SAF7518              →  6 Jobs
  SAF_222              →  4 Jobs
==================================================
  總計: 44 Jobs
```

**範例 Jobs 與其 View**：
- `SAF7514_K03` → EG8-PP
- `SAF7514_K04` → EG8-PP
- `SAF222_K03` → SAF_222
- `PC51Q_seed` → PC51Q-PP
- `PP_PM9M1_seed` → PM9M1-PP
- `loop-seed` → (未分類)
- `develop` → (未分類)

---

## 🔄 使用方式

### 同步 Jobs 和 Views

1. **通過頁面按鈕**：
   - 訪問：http://localhost/rvt-analytics
   - 點擊右上角「同步所有伺服器」按鈕
   - 系統會自動獲取 Jobs 和 Views 信息

2. **通過 API**：
   ```bash
   curl -X POST http://localhost/api/jenkins-servers/10/sync_jobs/
   ```

3. **查看結果**：
   ```bash
   # 檢查 API 響應
   curl http://localhost/api/jenkins-jobs/ | jq '.[0]'
   
   # 輸出會包含 view_name 字段：
   # {
   #   "name": "SAF7514_K03",
   #   "view_name": "EG8-PP",
   #   ...
   # }
   ```

---

## 🎨 UI 預覽

### 表格欄位順序（左到右）：
1. **Job / Build**（250px）- Job 名稱或 Build 編號
2. **View**（150px）- 所屬視圖（新增）
3. **狀態**（150px）- Active/Inactive 或 Success/Failure
4. **開始時間**（180px）- 最後構建時間
5. **執行時間**（120px）- 平均時長或具體時長
6. **操作**（200px）- 統計/構建/日誌/詳情按鈕

### View Tag 顏色方案：
- **有 View**：藍色 Tag（`geekblue`）
- **未分類**：灰色 Tag（`default`）

---

## 🔧 技術細節

### API 響應格式

**Job 對象現在包含**：
```json
{
  "id": 25,
  "name": "PC51Q_seed",
  "view_name": "PC51Q-PP",  // ← 新增字段
  "server_name": "RVT Production Server",
  "builds_count": 0,
  "is_buildable": true,
  "is_disabled": false,
  "url": "http://10.252.170.188:8080/job/PC51Q_seed/",
  ...
}
```

### Jenkins API 調用順序

```
1. GET /api/json
   └─ 獲取所有 Views: [EG8-PP, PC51Q-PP, PM9M1-PP, ...]

2. 對每個 View:
   GET /view/{view_name}/api/json
   └─ 獲取該 View 下的 Jobs

3. 建立映射關係:
   {
     "SAF7514_K03": "EG8-PP",
     "SAF222_K03": "SAF_222",
     ...
   }

4. GET /api/json?tree=jobs[...]
   └─ 獲取所有 Jobs，結合映射關係存入數據庫
```

---

## 📝 數據庫查詢範例

### 查看所有 Jobs 和其 View
```python
from api.models import JenkinsJob

jobs = JenkinsJob.objects.all()
for job in jobs:
    print(f"{job.name:30} → {job.view_name or '(未分類)'}")
```

### 按 View 分組統計
```python
from collections import Counter

view_counts = Counter([job.view_name or '(未分類)' for job in JenkinsJob.objects.all()])
print(dict(view_counts))
# {'EG8-PP': 6, 'SAF_222': 4, 'PC51Q-PP': 4, ...}
```

### 查詢特定 View 的 Jobs
```python
jobs = JenkinsJob.objects.filter(view_name='EG8-PP')
print(f"EG8-PP 視圖包含 {jobs.count()} 個 Jobs")
```

---

## 🚀 未來增強

### 可能的功能擴展

1. **View 過濾器**
   - 在篩選區域添加「選擇 View」下拉選單
   - 可快速篩選特定 View 的 Jobs

2. **View 統計卡片**
   - 顯示每個 View 的 Jobs 數量
   - 顯示每個 View 的成功率

3. **View 層級展示**
   - 使用 Tabs 或 Collapse 按 View 分組顯示
   - 每個 Tab 顯示一個 View 的 Jobs

4. **View 管理**
   - 支持從前端創建/編輯 View
   - 支持將 Job 移動到不同 View

---

## 🐛 已知限制

1. **多 View 歸屬**
   - 如果一個 Job 屬於多個 View（除了 "all"），只顯示第一個
   - 未來可以改為顯示所有 Views（使用多個 Tags）

2. **"all" View 處理**
   - "all" View 包含所有 Jobs，已被過濾不顯示
   - 未分類的 Job 會顯示「未分類」

3. **View 同步**
   - View 信息只在同步 Jobs 時更新
   - 如果 Jenkins 的 View 結構變化，需要重新同步

---

## 📚 相關文檔

- **Jenkins Views API**: https://www.jenkins.io/doc/book/using/using-views/
- **JenkinsJob Model**: `/backend/api/models.py`
- **JenkinsClient**: `/library/services/jenkins_client.py`
- **RVTAnalysisPage**: `/frontend/src/pages/RVTAnalysisPage.js`
- **API Views**: `/backend/api/views/jenkins.py`

---

## ✅ 驗證步驟

### 1. 驗證數據庫
```bash
docker exec nt-django python manage.py shell -c "
from api.models import JenkinsJob
print(f'Jobs with View: {JenkinsJob.objects.exclude(view_name=\"\").count()}')
print(f'Jobs without View: {JenkinsJob.objects.filter(view_name=\"\").count()}')
"
```

### 2. 驗證 API
```bash
curl -s http://localhost/api/jenkins-jobs/ | jq '.[0].view_name'
# 應該返回 View 名稱或 ""
```

### 3. 驗證前端
1. 訪問：http://localhost/rvt-analytics
2. 檢查表格是否顯示「View」欄位
3. 檢查篩選器是否顯示「選擇 Jenkins」
4. 展開 Job 查看 View Tag 是否正確顯示

---

**更新日期**：2025-11-04  
**版本**：v1.0  
**維護者**：Network Toolbox Team
