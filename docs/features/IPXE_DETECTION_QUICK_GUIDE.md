# iPXE 檢測功能 - 快速使用指南

## 🎯 功能概述

Network Toolbox 現在可以識別和追蹤 iPXE 網路開機過程，幫助您：
- 區分 BIOS PXE、iPXE、Windows PE 和正常 OS 的啟動階段
- 追蹤機器的完整啟動生命週期
- 快速找出所有使用 iPXE 啟動的設備
- 診斷網路開機問題

---

## 📋 使用步驟

### 1️⃣ 訪問 DHCP Server 分析頁面

1. 登入 Network Toolbox：http://localhost
2. 點擊左側菜單的「**DHCP Server 分析**」
3. 選擇要分析的 DHCP Server

### 2️⃣ 切換到日誌頁籤

1. 在 DHCP Server 分析頁面中
2. 點擊「**日誌**」(Logs) 分頁

### 3️⃣ 同步最新日誌

1. 點擊「**同步日誌**」按鈕
2. 系統會從 Windows DHCP Server 讀取最新日誌
3. 等待同步完成（幾秒鐘）

### 4️⃣ 使用客戶端類型篩選

在篩選區域中，您會看到新增的「**客戶端類型**」下拉選單：

```
客戶端類型: [全部 ▼]
```

**可用選項**：
- **全部** - 顯示所有日誌
- **iPXE** - 只顯示 iPXE 階段的記錄 ← **最常用**
- **PXE (BIOS)** - 只顯示 BIOS PXE ROM 階段
- **Windows PE** - 只顯示 Windows PE 部署階段
- **Operating System** - 只顯示正常 OS 運行階段
- **Unknown** - 無法識別的記錄

**範例**：選擇「iPXE」後，日誌列表只會顯示使用 iPXE 啟動的記錄。

---

## 🔍 閱讀日誌資訊

每筆日誌現在會顯示更豐富的資訊：

```
┌──────────────────────────────────────────────────────────────────┐
│ 2025-10-18 15:32:59  [INFO]  [Renew]  [iPXE]  [iPXE Loading]   │
│                                                                    │
│ DHCPREQUEST for 10.250.132.27 from bc:fc:e7:3a:61:c9 [iPXE] via eth0
│                                                                    │
│ Vendor Class: 0x69505845                                         │
│ User Class: iPXE                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**標籤說明**：
- **時間戳**: 日誌發生時間
- **[INFO]** 藍色: 日誌等級（INFO/WARN/ERROR）
- **[Renew]** 紫色: 事件類型（Assign/Renew/Release）
- **[iPXE]** 青色: 客戶端類型 ← **新增！**
- **[iPXE Loading]** 金色: 啟動階段 ← **新增！**
- **Vendor Class**: DHCP Option 60（廠商標識）
- **User Class**: DHCP Option 77（用戶標識，包含 "iPXE"）

---

## 🎨 客戶端類型標籤顏色

為了快速識別，不同類型使用不同顏色：

| 客戶端類型         | 標籤顏色 | 說明                               |
|-------------------|---------|-----------------------------------|
| **iPXE**          | 🔵 青色  | iPXE 網路開機環境                   |
| **PXE**           | 🔵 藍色  | BIOS PXE ROM（初始啟動）            |
| **WinPE**         | 🟣 紫色  | Windows PE 部署環境                |
| **OS**            | 🟢 綠色  | 正常 OS 運行                       |
| **Unknown**       | ⚪ 灰色  | 無法識別                           |

---

## 📊 實際應用場景

### 場景 1: 追蹤機器的完整啟動過程

**需求**：查看 MAC 地址 `bc:fc:e7:3a:61:c9` 的啟動流程

**操作**：
1. 在「搜尋關鍵字」輸入：`BCFCE73A61C9`
2. 按時間排序查看結果

**結果範例**：
```
15:32:54  [PXE]    BIOS PXE ROM
15:32:59  [iPXE]   iPXE Loading    ← 成功載入 iPXE
15:35:55  [WinPE]  Windows PE      ← 進入部署
15:41:52  [OS]     Operating System ← 部署完成，進入 OS
```

### 場景 2: 檢查有多少設備使用 iPXE 啟動

**需求**：統計今天有多少台設備通過 iPXE 啟動

**操作**：
1. 時間範圍選擇「今天」
2. 客戶端類型選擇「iPXE」
3. 查看總數

**結果**：頁面底部會顯示「共 XX 筆日誌」

### 場景 3: 診斷 iPXE 啟動問題

**需求**：某台機器無法通過 iPXE 啟動

**操作**：
1. 搜尋該機器的 MAC 地址
2. 查看是否有 [PXE] 標籤（BIOS PXE 階段）
3. 檢查是否有 [iPXE] 標籤（iPXE 載入成功）
4. 如果沒有 [iPXE]，說明 iPXE 載入失敗

### 場景 4: 監控 Windows PE 部署

**需求**：查看今天的 Windows PE 部署活動

**操作**：
1. 時間範圍選擇「今天」
2. 客戶端類型選擇「Windows PE」
3. 查看部署記錄

---

## 💡 進階技巧

### 技巧 1: 組合篩選
您可以組合多個篩選條件：
- **客戶端類型** = iPXE
- **日誌等級** = ERROR
- **關鍵字** = deny

這樣可以找出所有 iPXE 啟動時被拒絕的記錄。

### 技巧 2: 時間範圍選擇
使用「自訂時間範圍」選擇器精確定位問題時段：
```
開始時間: 2025-10-18 15:30:00
結束時間: 2025-10-18 16:00:00
```

### 技巧 3: 匯出 CSV
1. 應用篩選條件
2. 點擊「匯出 CSV」按鈕
3. 可以用 Excel 進一步分析

---

## 🔧 故障排查

### 問題 1: 看不到客戶端類型標籤
**原因**：日誌可能是舊資料（在功能實作前同步的）  
**解決**：點擊「同步日誌」按鈕重新同步

### 問題 2: 所有記錄都是 Unknown
**原因**：Windows DHCP Server 可能沒有記錄 DHCP Options  
**解決**：檢查 DHCP Server 日誌設定，確保啟用詳細日誌

### 問題 3: 沒有 iPXE 記錄
**可能原因**：
1. 機器沒有使用 iPXE 啟動
2. DHCP Server 日誌不完整
3. 時間範圍選擇錯誤

**檢查方法**：
- 選擇「全部」客戶端類型
- 擴大時間範圍到「7天」
- 搜尋機器的 MAC 地址

---

## 📚 技術細節

### Windows DHCP 日誌欄位對應
系統現在會解析 Windows DHCP 日誌的完整欄位：

```
欄位 0-6:   ID, Date, Time, Event, IP, Hostname, MAC
欄位 13-14: VendorClass(Hex), VendorClass(ASCII)  ← PXE/WinPE 識別
欄位 15-16: UserClass(Hex), UserClass(ASCII)      ← iPXE 識別
```

### 識別邏輯
- **iPXE**: User Class (欄位 16) 包含 "iPXE"
- **PXE**: Vendor Class (欄位 14) 包含 "PXEClient"
- **WinPE**: Vendor Class (欄位 14) 包含 "MSFT" 或 hostname 以 "minint-" 開頭
- **OS**: 有 hostname 但沒有 DHCP Options

---

## 🎯 最佳實踐

1. **定期同步日誌**：每天同步一次，確保資料最新
2. **使用篩選器**：善用客戶端類型篩選，快速定位問題
3. **追蹤完整流程**：用 MAC 地址搜尋，了解機器的完整啟動過程
4. **匯出重要記錄**：將異常記錄匯出為 CSV，方便存檔和分析

---

## 📞 需要幫助？

如果您在使用過程中遇到問題，請：
1. 查看 `docs/features/DHCP_LOG_IPXE_DETECTION_ANALYSIS.md` 了解技術細節
2. 查看 `docs/features/IPXE_DETECTION_IMPLEMENTATION_REPORT.md` 了解實作原理
3. 聯繫 Network Toolbox 支援團隊

---

**文檔版本**: 1.0  
**最後更新**: 2025-10-29  
**適用版本**: Network Toolbox v1.1+
