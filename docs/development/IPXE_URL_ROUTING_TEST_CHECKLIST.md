# iPXE Analytics URL 路由測試清單

## ✅ 測試項目

### 1. 基本 URL 訪問測試

- [ ] **訪問根路徑**
  ```
  URL: http://localhost/ipxe-analytics
  預期: 顯示所有 Server 的概覽頁面
  側邊欄: "iPXE 分析" 高亮
  ```

- [ ] **訪問特定 Tab（所有 Server）**
  ```
  URL: http://localhost/ipxe-analytics/logs
  預期: 顯示所有 Server 的日誌頁面
  側邊欄: "iPXE 分析" 高亮
  ```
  
  ```
  URL: http://localhost/ipxe-analytics/statistics
  預期: 顯示所有 Server 的統計頁面
  側邊欄: "iPXE 分析" 高亮
  ```
  
  ```
  URL: http://localhost/ipxe-analytics/network-quality
  預期: 顯示所有 Server 的網路品質頁面
  側邊欄: "iPXE 分析" 高亮
  ```

- [ ] **訪問特定 Server + Tab**
  ```
  URL: http://localhost/ipxe-analytics/server/1/overview
  預期: 顯示 Server 1 的概覽頁面
  Server 選擇器: 顯示 Server 1
  Tab: 概覽 Tab 啟用
  側邊欄: "iPXE 分析" 高亮
  ```

### 2. Server 切換測試

**測試步驟**：
1. 訪問 `http://localhost/ipxe-analytics/logs`
2. 從下拉選單切換到特定 Server（例如：Server 1）
3. 檢查：
   - [ ] URL 變為 `/ipxe-analytics/server/1/logs`
   - [ ] Tab 保持在 "日誌查看"
   - [ ] Server 選擇器顯示 Server 1
   - [ ] 內容更新為 Server 1 的日誌

4. 再切換回 "所有 Server"
5. 檢查：
   - [ ] URL 變為 `/ipxe-analytics/logs`
   - [ ] Tab 保持在 "日誌查看"
   - [ ] Server 選擇器顯示 "所有 Server"
   - [ ] 內容更新為所有 Server 的彙總

### 3. Tab 切換測試

**測試步驟**：
1. 訪問 `http://localhost/ipxe-analytics/server/1/overview`
2. 點擊 "統計分析" Tab
3. 檢查：
   - [ ] URL 變為 `/ipxe-analytics/server/1/statistics`
   - [ ] Server 保持為 Server 1
   - [ ] 統計分析 Tab 啟用
   - [ ] 內容顯示 Server 1 的統計資料

4. 點擊 "網路品質" Tab
5. 檢查：
   - [ ] URL 變為 `/ipxe-analytics/server/1/network-quality`
   - [ ] Server 保持為 Server 1
   - [ ] 網路品質 Tab 啟用
   - [ ] 內容顯示 Server 1 的網路品質資料

### 4. 瀏覽器導航測試

**測試步驟**：
1. 訪問 `http://localhost/ipxe-analytics`
2. 切換到 Server 1
3. 切換到 "日誌查看" Tab
4. 切換到 "統計分析" Tab
5. 點擊瀏覽器的「上一頁」按鈕
6. 檢查：
   - [ ] URL 回到 `/ipxe-analytics/server/1/logs`
   - [ ] 顯示 Server 1 的日誌頁面

7. 點擊瀏覽器的「下一頁」按鈕
8. 檢查：
   - [ ] URL 前進到 `/ipxe-analytics/server/1/statistics`
   - [ ] 顯示 Server 1 的統計頁面

### 5. 書籤與直接訪問測試

**測試步驟**：
1. 訪問並將以下 URL 加入書籤：
   ```
   http://localhost/ipxe-analytics/server/1/network-quality
   ```

2. 關閉瀏覽器分頁

3. 從書籤重新打開

4. 檢查：
   - [ ] URL 正確（`/ipxe-analytics/server/1/network-quality`）
   - [ ] Server 選擇器顯示 Server 1
   - [ ] 網路品質 Tab 啟用
   - [ ] 內容顯示 Server 1 的網路品質資料
   - [ ] 側邊欄 "iPXE 分析" 高亮

### 6. 分享 URL 測試

**測試步驟**：
1. 訪問 `http://localhost/ipxe-analytics/server/2/statistics`
2. 複製 URL
3. 開啟新的瀏覽器分頁（或隱私模式）
4. 貼上並訪問該 URL
5. 檢查：
   - [ ] Server 選擇器顯示 Server 2
   - [ ] 統計分析 Tab 啟用
   - [ ] 內容顯示 Server 2 的統計資料

### 7. 側邊欄高亮測試

**測試步驟**：
1. 訪問 `http://localhost/ipxe-analytics`
   - [ ] "iPXE 分析" 高亮

2. 訪問 `http://localhost/ipxe-analytics/logs`
   - [ ] "iPXE 分析" 高亮

3. 訪問 `http://localhost/ipxe-analytics/server/1/network-quality`
   - [ ] "iPXE 分析" 高亮

4. 訪問 `http://localhost/dhcp-analytics`
   - [ ] "DHCP Server 分析" 高亮
   - [ ] "iPXE 分析" 不高亮

5. 點擊側邊欄的 "iPXE 分析"
   - [ ] URL 變為 `/ipxe-analytics`
   - [ ] 顯示預設頁面

### 8. 頁面標題測試

**測試步驟**：
1. 訪問 `http://localhost/ipxe-analytics`
   - [ ] 瀏覽器標籤標題：`概覽 - 所有 Server | iPXE 分析`

2. 訪問 `http://localhost/ipxe-analytics/logs`
   - [ ] 瀏覽器標籤標題：`日誌查看 - 所有 Server | iPXE 分析`

3. 訪問 `http://localhost/ipxe-analytics/server/1/network-quality`
   - [ ] 瀏覽器標籤標題：`網路品質 - [Server IP] ([Server Name]) | iPXE 分析`

### 9. 錯誤處理測試（可選）

**測試步驟**：
1. 訪問不存在的 Tab
   ```
   http://localhost/ipxe-analytics/invalid-tab
   ```
   - [ ] 應顯示預設 Tab 或適當的錯誤訊息

2. 訪問不存在的 Server
   ```
   http://localhost/ipxe-analytics/server/999/overview
   ```
   - [ ] 應顯示錯誤訊息或重定向到預設頁面

### 10. 與 DHCP Analytics 對比測試

**確認兩個頁面行為一致**：

| 功能 | DHCP Analytics | iPXE Analytics | 狀態 |
|------|----------------|----------------|------|
| URL 路由模式 | `/dhcp-analytics/:tab` | `/ipxe-analytics/:tab` | [ ] |
| Server 路由 | `/server/:serverId/:tab` | `/server/:serverId/:tab` | [ ] |
| Server 切換 | 更新 URL | 更新 URL | [ ] |
| Tab 切換 | 更新 URL | 更新 URL | [ ] |
| 瀏覽器導航 | 正常工作 | 正常工作 | [ ] |
| 側邊欄高亮 | 正常高亮 | 正常高亮 | [ ] |
| 頁面標題 | 動態更新 | 動態更新 | [ ] |

## 🐛 已知問題

記錄測試中發現的問題：

1. **問題描述**：
   - 現象：
   - 重現步驟：
   - 預期行為：
   - 實際行為：

2. **問題描述**：
   - 現象：
   - 重現步驟：
   - 預期行為：
   - 實際行為：

## 📝 測試備註

**測試環境**：
- 瀏覽器：
- 版本：
- 測試日期：
- 測試人員：

**測試結果摘要**：
- 通過項目：__ / __
- 失敗項目：__ / __
- 跳過項目：__ / __

**結論**：
- [ ] 所有關鍵功能正常運作
- [ ] 發現輕微問題但不影響使用
- [ ] 發現重大問題需要修復

---

**測試完成日期**：________  
**簽名**：________
