# DHCP Server 分析 - URL 導航功能說明

## 📅 實作日期
2025-10-30

## 🎯 功能概述

為 DHCP Server 分析頁面實現 **URL 獨立化**，每個 Tab 和 Server 選擇都有獨立的 URL，支援：
- ✅ 刷新頁面保持當前狀態
- ✅ 瀏覽器前進/後退按鈕
- ✅ 分享特定頁面 URL
- ✅ 收藏/書籤特定頁面
- ✅ 麵包屑導航

---

## 🔗 URL 結構設計

### **基礎格式**
```
/dhcp-analytics/server/{serverId}/{tab}?{filters}
```

### **URL 範例**

#### 1. **彙總視圖**（所有 Server）
```
/dhcp-analytics                          # 預設導向 overview
/dhcp-analytics/overview                 # 所有 Server 概覽
/dhcp-analytics/logs                     # 所有 Server 日誌
/dhcp-analytics/leases                   # 所有 Server 租約
/dhcp-analytics/statistics               # 所有 Server 統計
/dhcp-analytics/config                   # 所有 Server 設定
```

#### 2. **單一 Server 視圖**
```
/dhcp-analytics/server/1/overview        # Server 1 概覽
/dhcp-analytics/server/1/logs            # Server 1 日誌查看
/dhcp-analytics/server/1/leases          # Server 1 租約管理
/dhcp-analytics/server/1/statistics      # Server 1 統計分析
/dhcp-analytics/server/1/config          # Server 1 設定頁面
```

#### 3. **帶過濾參數**（未來擴充）
```
/dhcp-analytics/server/1/logs?days=15&level=error
/dhcp-analytics/server/1/leases?status=active&scope=192.168.1.0
/dhcp-analytics/server/1/statistics?range=30d&metric=leases
```

---

## 🎨 麵包屑導航

### **導航結構**
```
Home > DHCP Server 分析 > [Server 名稱] > [Tab 名稱]
```

### **實例**

| URL | 麵包屑顯示 |
|-----|-----------|
| `/dhcp-analytics/overview` | `Home > DHCP Server 分析 > 所有 Server > 概覽` |
| `/dhcp-analytics/server/1/logs` | `Home > DHCP Server 分析 > 10.250.50.1 (Windows DHCP Server) > 日誌查看` |
| `/dhcp-analytics/server/2/leases` | `Home > DHCP Server 分析 > 192.168.1.1 (Linux DHCP Server) > 租約管理` |

### **可點擊元素**
- ✅ **Home** → 導向 `/dashboard`
- ✅ **DHCP Server 分析** → 導向 `/dhcp-analytics/overview`
- ✅ **Server 名稱**（單一 Server 時）→ 導向該 Server 的 overview
- ❌ **當前 Tab** → 不可點擊（已在當前頁面）

---

## 🔄 導航行為

### **1. 切換 Tab（保持 Server）**

**操作**：點擊不同的 Tab
```
當前: /dhcp-analytics/server/1/logs
點擊「租約管理」
結果: /dhcp-analytics/server/1/leases
```

**麵包屑變化**：
```
Home > DHCP Server 分析 > 10.250.50.1 > 日誌查看
  ↓
Home > DHCP Server 分析 > 10.250.50.1 > 租約管理
```

### **2. 切換 Server（保持 Tab）**

**操作**：從下拉選單選擇不同 Server
```
當前: /dhcp-analytics/server/1/logs
選擇 Server 2
結果: /dhcp-analytics/server/2/logs
```

**麵包屑變化**：
```
Home > DHCP Server 分析 > 10.250.50.1 > 日誌查看
  ↓
Home > DHCP Server 分析 > 192.168.1.1 > 日誌查看
```

### **3. 切換到所有 Server（彙總視圖）**

**操作**：下拉選單選擇「所有 Server」
```
當前: /dhcp-analytics/server/1/logs
選擇「所有 Server」
結果: /dhcp-analytics/logs
```

### **4. 點擊麵包屑導航**

**當前頁面**：`/dhcp-analytics/server/1/logs?days=15&level=error`

**點擊行為**：
- **Home** → `/dashboard`
- **DHCP Server 分析** → `/dhcp-analytics/overview`
- **10.250.50.1** → `/dhcp-analytics/server/1/overview`
- **日誌查看** → 不可點擊（當前頁面）

---

## 🧪 測試案例

### **測試 1：刷新頁面**
1. 導航到 `/dhcp-analytics/server/1/logs`
2. 按 F5 刷新頁面
3. ✅ 預期：頁面保持在 Server 1 的日誌查看 Tab

### **測試 2：瀏覽器前進/後退**
1. 從 `/dhcp-analytics/overview` 導航
2. 切換到 `/dhcp-analytics/server/1/logs`
3. 再切換到 `/dhcp-analytics/server/1/leases`
4. 點擊瀏覽器「後退」按鈕
5. ✅ 預期：返回 `/dhcp-analytics/server/1/logs`
6. 點擊「前進」按鈕
7. ✅ 預期：前進到 `/dhcp-analytics/server/1/leases`

### **測試 3：直接訪問 URL**
1. 在瀏覽器位址列輸入 `/dhcp-analytics/server/2/statistics`
2. 按 Enter
3. ✅ 預期：直接顯示 Server 2 的統計分析頁面

### **測試 4：分享 URL**
1. 複製當前 URL：`/dhcp-analytics/server/1/logs`
2. 在新分頁中貼上並訪問
3. ✅ 預期：新分頁顯示相同的 Server 1 日誌頁面

### **測試 5：書籤功能**
1. 在 `/dhcp-analytics/server/1/logs` 加入書籤
2. 書籤標題應顯示：`日誌查看 - 10.250.50.1 (Windows DHCP Server) | DHCP Server 分析`
3. 關閉瀏覽器後重新開啟
4. 點擊書籤
5. ✅ 預期：正確導向 Server 1 的日誌頁面

### **測試 6：無效 URL 處理**
1. 訪問 `/dhcp-analytics/server/999/logs`（不存在的 Server）
2. ✅ 預期：顯示錯誤或自動導向有效頁面
3. 訪問 `/dhcp-analytics/invalid-tab`（無效的 Tab）
4. ✅ 預期：自動導向 `/dhcp-analytics/overview`

---

## 📋 動態頁面標題

每個頁面都有獨特的 `document.title`，方便瀏覽器分頁和書籤識別：

| URL | 頁面標題 |
|-----|---------|
| `/dhcp-analytics/overview` | `概覽 - 所有 Server \| DHCP Server 分析` |
| `/dhcp-analytics/server/1/logs` | `日誌查看 - 10.250.50.1 (Windows DHCP Server) \| DHCP Server 分析` |
| `/dhcp-analytics/server/1/leases` | `租約管理 - 10.250.50.1 (Windows DHCP Server) \| DHCP Server 分析` |

---

## 🔧 技術實作細節

### **修改的檔案**

#### 1. **`frontend/src/App.js`**
- 新增 DHCP Analytics 子路由配置
- 支援三種路由格式：
  ```javascript
  /dhcp-analytics                        // 彙總首頁
  /dhcp-analytics/:tab                   // 彙總 + Tab
  /dhcp-analytics/server/:serverId/:tab  // 特定 Server + Tab
  ```

#### 2. **`frontend/src/pages/DHCPAnalyticsPage.js`**
- 使用 `useParams()` 從 URL 讀取 serverId 和 tab
- 使用 `useNavigate()` 進行 URL 導航
- 移除 `useState` 管理 tab 和 server（改用 URL 作為單一真實來源）
- 新增麵包屑導航組件
- 新增動態頁面標題設定

### **關鍵代碼片段**

```javascript
// 從 URL 獲取參數（單一真實來源）
const { serverId: urlServerId, tab: urlTab } = useParams();
const activeTab = urlTab || 'overview';
const selectedServer = urlServerId || 'all';

// Tab 切換（保持 Server）
const handleTabChange = (key) => {
    if (selectedServer === 'all') {
        navigate(`/dhcp-analytics/${key}`);
    } else {
        navigate(`/dhcp-analytics/server/${selectedServer}/${key}`);
    }
};

// Server 切換（保持 Tab）
const handleServerChange = (serverId) => {
    if (serverId === 'all') {
        navigate(`/dhcp-analytics/${activeTab}`);
    } else {
        navigate(`/dhcp-analytics/server/${serverId}/${activeTab}`);
    }
};
```

---

## 🎯 方案選擇理由

根據方案比較表，我們選擇了 **方案 B：混合路由**：

| 特性 | 評分 | 說明 |
|-----|------|------|
| **URL 美觀度** | ⭐⭐⭐⭐⭐ | 清晰的層級結構 |
| **語義清晰度** | ⭐⭐⭐⭐⭐ | Server 是主體，Tab 是視圖 |
| **查詢難度** | ⭐⭐⭐ 中等 | 需要修改 2 個檔案 |
| **擴充性** | ⭐⭐⭐⭐ | 易於加入過濾參數 |
| **SEO 友善** | ⭐⭐⭐⭐ | 每個頁面獨立 URL |
| **業界慣例** | ✅ | GitHub, AWS 都使用此模式 |

---

## 🚀 未來擴充計畫

### **階段 1：基礎 URL 導航**（✅ 已完成）
- [x] Tab 獨立 URL
- [x] Server 選擇獨立 URL
- [x] 麵包屑導航
- [x] 動態頁面標題

### **階段 2：過濾參數保存**（規劃中）
- [ ] 日誌過濾條件（days, level, client_type）
- [ ] 租約篩選條件（status, scope）
- [ ] 統計分析範圍（range, metric）
- [ ] 從 URL 恢復過濾狀態

### **階段 3：分享與協作**（規劃中）
- [ ] 「複製連結」按鈕
- [ ] URL 短網址服務
- [ ] 分享到聊天工具（Slack、Teams）

---

## 📝 使用範例

### **情境 1：運維人員發現問題**
```
1. 發現 Server 1 有異常日誌
2. 導航到：/dhcp-analytics/server/1/logs?days=7&level=error
3. 複製 URL 分享給主管：「這裡有錯誤日誌需要處理」
4. 主管點擊連結，立即看到相同的錯誤日誌頁面
```

### **情境 2：定期檢查租約使用率**
```
1. 每週一檢查 Server 2 的租約使用率
2. 將 /dhcp-analytics/server/2/leases 加入書籤「週一檢查」
3. 每週點擊書籤快速訪問
```

### **情境 3：多 Server 切換**
```
1. 查看 Server 1 日誌：/dhcp-analytics/server/1/logs
2. 需要對比 Server 2，切換 Server 下拉選單
3. 自動導向：/dhcp-analytics/server/2/logs
4. 切換回 Server 1，點擊瀏覽器「後退」按鈕即可
```

---

## ⚠️ 已知限制

1. **過濾參數未實作**：目前 Query Parameters（如 `?days=15`）尚未實作，需要在各 Tab 組件中加入
2. **無效 URL 處理**：訪問不存在的 Server ID 時，目前會顯示空資料，未來需加入錯誤提示
3. **Loading 狀態**：切換 Tab/Server 時沒有過渡動畫，使用者體驗可進一步優化

---

## 📚 相關文件

- [DHCP Server 分析功能說明](./dhcp-analytics-overview.md)（待建立）
- [React Router v6 官方文件](https://reactrouter.com/)
- [Ant Design Breadcrumb 組件](https://ant.design/components/breadcrumb-cn/)

---

**文件版本**：v1.0  
**最後更新**：2025-10-30  
**維護者**：Network Toolbox Team
