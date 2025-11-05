# RVT 分析功能 - 實現文檔

## 📋 功能概述

**RVT 分析**是一個專為 Admin 用戶設計的 Jenkins CI/CD 分析頁面，提供完整的 Job 和 Build 管理功能。

---

## 🎯 核心特性

### 1. **權限控制**
- ✅ 僅 Admin 用戶可見側邊欄菜單項
- ✅ 非 Admin 訪問自動跳轉到 Dashboard
- ✅ 前端路由守衛保護

### 2. **統計儀表板**
- 📊 伺服器總數
- 📊 Jobs 總數
- 📊 今日構建數
- 📊 總體成功率

### 3. **Tree Table（兩層結構）**
- **第 1 層：Job**
  - 顯示 Job 名稱、狀態、最後構建時間、平均執行時間
  - 操作按鈕：查看統計、觸發構建
  
- **第 2 層：Build**（懶加載）
  - 顯示 Build 編號、狀態、開始時間、執行時間
  - 操作按鈕：查看日誌、查看詳情
  - 點擊展開 Job 時才載入最近 10 個 Builds

### 4. **篩選功能**
- 🔍 伺服器篩選（下拉選單）
- 🔍 狀態篩選（SUCCESS/FAILURE/RUNNING/UNSTABLE）
- 🔍 時間範圍篩選（日期區間）
- 🔍 Job 名稱搜尋

### 5. **互動功能**
- **Console Log Modal**：查看 Build 的控制台日誌（黑色背景）
- **Build Detail Drawer**：查看 Build 詳情（右側抽屜）
- **Job Statistics Drawer**：查看 Job 統計資訊（成功率、平均時長、狀態分佈）

---

## 📂 文件結構

```
frontend/src/
├── pages/
│   └── RVTAnalysisPage.js          # 主頁面（約 700 行）
│
├── components/
│   └── Sidebar.js                  # 更新：添加 RVT 菜單項
│
└── App.js                          # 更新：添加路由配置
```

---

## 🔗 API 端點使用

### 使用的 API：
```javascript
GET /api/jenkins-servers/              // 獲取伺服器列表
GET /api/jenkins-jobs/                 // 獲取 Jobs 列表
GET /api/jenkins-jobs/{id}/builds/     // 獲取 Job 的 Builds
GET /api/jenkins-jobs/{id}/statistics/ // 獲取 Job 統計
GET /api/jenkins-builds/{id}/          // 獲取 Build 詳情
GET /api/jenkins-builds/{id}/console_log/ // 獲取 Console Log
POST /api/jenkins-servers/{id}/sync_jobs/ // 同步 Jobs
```

---

## 🎨 UI 設計特色

### **風格仿照附件 Tree Table**
- ✅ 展開/收合按鈕（`[>]` / `[v]`）
- ✅ 縮排顯示（Build 層級自動縮排 32px）
- ✅ 狀態標籤（Tag 組件 + 顏色標記）
- ✅ 固定右側操作欄
- ✅ 分頁控制（`Rows per page: [10 ▼] 1-10 of 44`）

### **狀態標籤配色：**
```javascript
Job Status:
  - Active  → 🟢 綠色
  - Inactive → ⚪ 灰色

Build Status:
  - SUCCESS   → ✅ 綠色
  - FAILURE   → ❌ 紅色
  - UNSTABLE  → ⚠️ 橙色
  - ABORTED   → 🚫 灰色
  - RUNNING   → 🔄 藍色
```

---

## 🚀 使用方式

### **訪問頁面：**
1. 使用 Admin 帳號登入
2. 側邊欄會顯示「RVT 分析」菜單項（在 iPXE 分析下方）
3. 點擊進入 `/rvt-analytics`

### **操作流程：**
1. **查看統計**：頁面頂部顯示統計卡片
2. **篩選數據**：使用篩選欄快速定位
3. **展開 Job**：點擊 `[>]` 按鈕展開，自動載入最近 10 個 Builds
4. **查看日誌**：點擊「日誌」按鈕查看 Console Log
5. **查看詳情**：點擊「詳情」按鈕查看 Build 詳細資訊
6. **同步數據**：點擊「同步所有伺服器」按鈕更新 Jobs

---

## 🔒 權限驗證邏輯

### **前端權限檢查：**
```javascript
// 1. Sidebar 菜單項權限
...(isAuthenticated && user?.is_staff ? [rvtMenuItem] : [])

// 2. 頁面級別權限
useEffect(() => {
    if (user && !user.is_staff) {
        message.error('您沒有權限訪問此頁面');
        navigate('/dashboard');
    }
}, [user, navigate]);
```

### **建議後端增強：**
```python
# backend/api/views/jenkins.py
# 建議將 permission_classes 改為：
permission_classes = [IsAuthenticated, IsAdminUser]
```

---

## 📊 性能優化

### **已實現：**
- ✅ **懶加載**：展開 Job 時才載入 Builds
- ✅ **限制返回數量**：每次只載入 10 個 Builds
- ✅ **前端篩選**：避免重複請求

### **未來優化：**
- 🔄 虛擬滾動（大量數據時）
- 🔄 Redis 緩存（後端已實現，前端可添加緩存策略）
- 🔄 WebSocket 實時更新（Running 狀態的 Build）

---

## 🐛 已知限制

### **當前版本限制：**
1. **觸發構建功能**：尚未實現（Placeholder）
2. **平均執行時間**：顯示「計算中...」，需調用 `/statistics/` API
3. **今日構建統計**：前端計算，效率較低，應由後端提供

### **建議後端 API 改進：**
```python
# 建議添加新的 API 端點：
GET /api/jenkins-builds/statistics/
  - today_builds: 今日構建數
  - recent_success_rate: 最近 7 天成功率
  
GET /api/jenkins-jobs/{id}/avg_duration/
  - 返回該 Job 的平均執行時間
```

---

## ✅ 測試檢查清單

### **功能測試：**
- [ ] Admin 用戶可以看到側邊欄菜單項
- [ ] 非 Admin 用戶看不到菜單項
- [ ] 非 Admin 訪問頁面會跳轉
- [ ] 統計卡片正確顯示數據
- [ ] 篩選功能正常工作
- [ ] Tree Table 展開/收合正常
- [ ] 展開 Job 時正確載入 Builds
- [ ] Console Log Modal 正確顯示日誌
- [ ] Build 詳情 Drawer 正確顯示
- [ ] Job 統計 Drawer 正確顯示

### **UI 測試：**
- [ ] 響應式佈局正常（1920px、1440px、1024px）
- [ ] 狀態標籤顏色正確
- [ ] 操作按鈕 Hover 效果正常
- [ ] Modal 和 Drawer 動畫流暢

---

## 📝 更新日誌

### **2025-11-04：Phase 8 完成**
- ✅ 創建 RVTAnalysisPage.js 主頁面
- ✅ 更新 App.js 添加路由
- ✅ 更新 Sidebar.js 添加菜單項（僅 Admin 可見）
- ✅ 實現統計卡片、Tree Table、篩選功能
- ✅ 實現 Console Log Modal、Build/Job Drawer
- ✅ 懶加載 Builds 功能

---

## 🔗 相關文檔

- [Jenkins API 文檔](../../api/JENKINS_API.md)（如果有）
- [權限控制說明](../../development/PERMISSIONS.md)（如果有）
- [前端組件庫規範](../../development/FRONTEND_GUIDELINES.md)

---

**維護者：** Network Toolbox Team  
**最後更新：** 2025-11-04  
**狀態：** ✅ 已完成（Phase 8）
