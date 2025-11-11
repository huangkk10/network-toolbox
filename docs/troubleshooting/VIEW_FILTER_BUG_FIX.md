# Jenkins View 篩選問題修復

## 🐛 問題描述

用戶反映在 **RVT 分析頁面** 選擇特定 Jenkins Server（例如 `10.252.170.171`）後，**View 下拉列表** 仍然顯示所有服務器的 Views，而不是僅顯示該服務器的 Views。

### 問題截圖分析

從附件截圖可以看到：
- **Jenkins Server**: 選擇了 `10.252.170.171`
- **View 篩選**: 下拉列表顯示了多個 Views：
  - FW_QA Primary Drive
  - EG8-PP
  - FW_QA Secondary Drive
  - PC51Q-PP
  - PM9M1-PP
  - PQF02-SAF3201
  - PQF02-SAF3202
  - SAF3203
  - 等等...

### 問題原因

**前端邏輯錯誤**：

```javascript
// ❌ 原始代碼（錯誤）
const fetchAvailableViews = async () => {
    // 獲取所有 Jobs（不帶篩選參數）
    const response = await axios.get('/api/jenkins-jobs/');
    
    // 提取唯一的 View 名稱列表
    const uniqueViews = [...new Set(
        response.data
            .map(job => job.view_name)
            .filter(view => view && view !== '')
    )].sort();
    
    setAvailableViews(uniqueViews);
};
```

**問題**：
1. `fetchAvailableViews()` 總是獲取 **所有服務器** 的所有 Jobs
2. 即使用戶選擇了特定服務器，View 列表仍然包含其他服務器的 Views
3. 導致用戶困惑：為什麼選了 171 服務器，還能看到其他服務器的 Views？

---

## ✅ 解決方案

### 修改內容

**文件**: `frontend/src/pages/RVTAnalysisPage.js`

#### 1. 修改 `fetchAvailableViews` 函數，支持服務器過濾

```javascript
// ✅ 修改後（正確）
const fetchAvailableViews = async (serverId = null) => {
    try {
        // 根據 serverId 過濾 Jobs
        let url = '/api/jenkins-jobs/';
        if (serverId) {
            url += `?server_id=${serverId}`;
        }
        
        const response = await axios.get(url);
        
        // 提取唯一的 View 名稱列表
        const uniqueViews = [...new Set(
            response.data
                .map(job => job.view_name)
                .filter(view => view && view !== '')
        )].sort();
        
        setAvailableViews(uniqueViews);
    } catch (error) {
        console.error('載入 View 列表失敗:', error);
    }
};
```

**變更**：
- 新增 `serverId` 參數
- 如果提供 `serverId`，則在 API 請求中加入 `?server_id=xxx` 過濾條件
- 只提取該服務器的 Jobs 的 `view_name`

#### 2. 初始化時載入 View 列表

```javascript
// ✅ 修改初始化邏輯
useEffect(() => {
    fetchStatistics();
    fetchAvailableViews(filters.server_id);  // 傳入當前選擇的伺服器 ID
}, []);
```

#### 3. 服務器切換時重新載入 View 列表

```javascript
// ✅ 修改服務器選擇的 onChange 處理
onChange={(value) => {
    const newFilters = { 
        ...filters, 
        server_id: value, 
        view_name: null  // 清空 view_name（因為切換服務器後，View 列表會改變）
    };
    setFilters(newFilters);
    updateURLParams(newFilters);
    fetchAvailableViews(value);  // 重新載入該服務器的 View 列表
}}
```

**變更**：
- 切換服務器時，自動清空 `view_name` 篩選
- 調用 `fetchAvailableViews(value)` 重新載入對應服務器的 Views

---

## 🧪 測試驗證

### 測試步驟

1. **訪問頁面**：
   ```
   http://localhost/rvt-analytics
   ```

2. **初始狀態**：
   - Server 未選擇：顯示所有服務器的所有 Views
   - View 下拉列表：包含所有 Views（跨服務器）

3. **選擇服務器 10.252.170.171**：
   - 預期：View 下拉列表只顯示該服務器的 Views
   - 驗證：列表中不應出現其他服務器（187, 188）的專屬 Views

4. **切換服務器 10.252.170.187**：
   - 預期：View 列表自動更新為 187 的 Views
   - View 篩選自動清空（因為 171 的 View 可能不存在於 187）

5. **清空服務器選擇**：
   - 預期：View 列表恢復為所有服務器的所有 Views

### 預期結果

| 操作 | View 列表內容 | View 篩選狀態 |
|------|---------------|---------------|
| 初始（無選擇） | 所有服務器的 Views | 保持原值 |
| 選擇 Server 171 | 僅 171 的 Views | 自動清空 |
| 切換到 Server 187 | 僅 187 的 Views | 自動清空 |
| 清空 Server | 所有服務器的 Views | 保持原值 |

---

## 📊 實際數據示例

假設系統中有以下數據：

```
Server 10.252.170.171:
  Jobs:
    - Test-KVM01 (View: PC51Q-PP)
    - SAF7514_K03 (View: EG8-PP)

Server 10.252.170.187:
  Jobs:
    - PM9M1_Build (View: PM9M1-PP)
    - SAF3201_Test (View: PQF02-SAF3201)

Server 10.252.170.188:
  Jobs:
    - FW_QA_Primary (View: FW_QA Primary Drive)
    - FW_QA_Secondary (View: FW_QA Secondary Drive)
```

### 修復前（錯誤行為）

| 選擇的 Server | View 下拉列表 | ❌ 問題 |
|---------------|---------------|---------|
| 10.252.170.171 | PC51Q-PP, EG8-PP, PM9M1-PP, PQF02-SAF3201, FW_QA Primary Drive, FW_QA Secondary Drive | 顯示了所有服務器的 Views |

### 修復後（正確行為）

| 選擇的 Server | View 下拉列表 | ✅ 結果 |
|---------------|---------------|---------|
| 10.252.170.171 | PC51Q-PP, EG8-PP | 只顯示 171 的 Views |
| 10.252.170.187 | PM9M1-PP, PQF02-SAF3201 | 只顯示 187 的 Views |
| 10.252.170.188 | FW_QA Primary Drive, FW_QA Secondary Drive | 只顯示 188 的 Views |
| (未選擇) | PC51Q-PP, EG8-PP, PM9M1-PP, PQF02-SAF3201, FW_QA Primary Drive, FW_QA Secondary Drive | 顯示所有 Views |

---

## 🔧 技術細節

### API 調用變化

#### 修復前
```http
GET /api/jenkins-jobs/
返回: 所有服務器的所有 Jobs（無過濾）
```

#### 修復後（選擇了 Server 171）
```http
GET /api/jenkins-jobs/?server_id=12
返回: 僅 server_id=12 (10.252.170.171) 的 Jobs
```

### 數據流程

```
用戶操作                   前端處理                    後端 API                   View 列表
----------                 ----------                  ----------                 ----------
選擇 Server 171  ──────>  onChange 觸發  ──────>  GET /api/jenkins-jobs/  ──────>  提取 171 的 Views
                           │                      ?server_id=12
                           │
                           └─> 清空 view_name
                           └─> fetchAvailableViews(12)
```

---

## 🎯 影響範圍

### 修改文件
- ✅ `frontend/src/pages/RVTAnalysisPage.js`（3 處修改）

### 不影響
- ❌ 後端 API（無需修改）
- ❌ 數據庫（無需修改）
- ❌ 其他頁面（僅影響 RVT 分析頁面）

---

## ✅ 完成狀態

- [x] 識別問題根源
- [x] 修改前端代碼
- [x] 添加服務器過濾邏輯
- [x] 實現切換時自動重新載入
- [x] 實現切換時自動清空 View 篩選
- [ ] 前端構建（React 開發模式會自動熱重載）
- [ ] 用戶驗證測試

---

## 📝 總結

**問題**：View 列表顯示了所有服務器的 Views，而不是當前選擇服務器的 Views。

**原因**：前端 `fetchAvailableViews()` 函數總是獲取所有 Jobs，未根據 `server_id` 過濾。

**解決**：
1. 修改函數支持 `serverId` 參數
2. 初始化時傳入當前服務器 ID
3. 切換服務器時重新載入並清空 View 篩選

**結果**：View 列表現在會根據選擇的服務器動態更新，提供更好的用戶體驗。

---

**修復日期**: 2025-11-10  
**修復人員**: GitHub Copilot  
**影響版本**: network-toolbox (當前版本)  
**嚴重程度**: Medium（影響用戶體驗，但不影響功能）
