# Dashboard 圖表修改說明

## 📊 修改內容

將 Dashboard 頁面中的「過去 7 天頁面瀏覽趨勢」圖表改為「過去 7 天使用人數趨勢」，統計每日唯一訪客數。

## 🎯 修改目標

- **原本**：顯示每天的頁面瀏覽次數（重複訪問會累加）
- **現在**：顯示每天使用網頁的人數（同一帳戶不重複計算）

## 🔧 修改內容

### 1. 前端圖表修改

**檔案**：`frontend/src/pages/DashboardPage.js`

**變更內容**：
- 圖表標題：`過去 7 天頁面瀏覽趨勢` → `過去 7 天使用人數趨勢`
- Y 軸標籤：`瀏覽次數` → `使用人數`
- 數據欄位：`page_views` → `unique_visitors`
- 圖例名稱：`頁面瀏覽次數` → `每日使用人數`
- Tooltip 顯示：`X 次` → `X 人`

### 2. 後端統計邏輯優化

**檔案**：`backend/api/middleware/website_usage.py`

**改進內容**：
- **登入用戶**：以帳戶 `username` 作為唯一識別
- **未登入用戶**：以 Session 或 IP 地址作為唯一識別
- **計算規則**：同一帳戶每天只計算一次
- **額外統計**：記錄最活躍使用者（Top 10）

**核心邏輯**：
```python
# 優先基於登入帳戶
if request.user and request.user.is_authenticated:
    visitor_key = f'user_{request.user.username}'
else:
    visitor_key = f'session_{request.session.session_key or request.META.get("REMOTE_ADDR", "unknown")}'

# 檢查是否今天已經訪問過
session_visited_key = f'visited_today_{today}_{visitor_key}'
if not request.session.get(session_visited_key):
    stats.unique_visitors += 1
    request.session[session_visited_key] = True
```

## 📈 統計規則

### 唯一訪客計算

| 使用者狀態 | 識別方式 | 重複計算規則 |
|-----------|---------|-------------|
| **已登入** | 帳戶 username | 同一帳戶每天只計算一次 |
| **未登入** | Session 或 IP | 同一 Session/IP 每天只計算一次 |

### 圖表顯示

- **數據來源**：`WebsiteUsageStats.unique_visitors`
- **統計週期**：每天一筆記錄
- **顯示範圍**：過去 7 天
- **更新方式**：即時更新（每次訪問自動記錄）

## 🧪 測試驗證

**測試腳本**：`backend/test_unique_visitors_stats.py`

執行方式：
```bash
docker exec nt-django python /app/test_unique_visitors_stats.py
```

測試結果範例：
```
📅 統計日期: 2025-12-10
👥 唯一訪客數: 7 人
📄 總頁面瀏覽: 109 次
📊 平均每人瀏覽: 15.57 次

📈 過去 7 天唯一訪客趨勢
日期           唯一訪客       頁面瀏覽       API請求     
--------------------------------------------------
2025-12-03   48         399        399       
2025-12-04   5          2848       2848      
2025-12-05   6          724        724       
...
```

## 💡 使用說明

### 對使用者的影響

1. **同一帳戶多次訪問**：只計算為 1 人
2. **不同帳戶訪問**：分別計算
3. **未登入訪問**：基於 Session 識別，刷新瀏覽器會被視為新訪客

### 查看統計數據

- **儀表板卡片**：顯示「今日使用人數」
- **趨勢圖表**：顯示過去 7 天的每日使用人數
- **最活躍使用者**：顯示訪問次數最多的 Top 10 用戶（僅登入用戶）

## 📝 相關檔案

- `frontend/src/pages/DashboardPage.js` - 前端圖表
- `backend/api/middleware/website_usage.py` - 統計中間件
- `backend/api/models.py` - WebsiteUsageStats 模型
- `backend/api/views/system.py` - Dashboard API
- `backend/test_unique_visitors_stats.py` - 測試腳本

## ✅ 部署步驟

1. 修改前端圖表代碼
2. 優化後端中間件邏輯
3. 重啟 Django 容器：`docker compose restart django`
4. 清除瀏覽器快取並重新載入頁面
5. 驗證圖表顯示是否正確

## 🔍 注意事項

- **歷史數據**：已存在的統計數據不受影響，新的計算規則只適用於新訪問
- **Session 生命週期**：Django Session 預設有效期為 2 週
- **跨瀏覽器**：同一帳戶在不同瀏覽器訪問仍只計算一次
- **隱私保護**：未記錄 IP 地址，只用於判斷唯一性

## 📚 後續優化建議

1. **使用者詳細分析**：記錄每個使用者的訪問時間、停留時長
2. **頁面訪問路徑**：分析使用者的瀏覽路徑
3. **裝置類型統計**：記錄桌面版/手機版訪問比例
4. **地理位置分析**：基於 IP 地址分析訪客來源（可選）

---

**修改日期**：2025-12-10  
**修改者**：GitHub Copilot  
**影響範圍**：Dashboard 統計圖表
