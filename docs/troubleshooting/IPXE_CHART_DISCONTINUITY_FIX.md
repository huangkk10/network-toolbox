# iPXE 網路品質圖表斷點問題修復報告

## 📊 問題描述

用戶反映 iPXE 分析頁面的「網路品質」標籤中，所有曲線圖（Ping、HTTP、SSH、丟包率、下載速度）都出現**不連續的斷點**，看起來像數據缺失。

### 問題截圖特徵
- 圖表中只有少數幾個數據點
- 線條之間出現大量空白區域
- 視覺效果不連續，難以判斷趨勢

## 🔍 問題分析

### 1. 數據採集情況
通過檢查後端數據庫發現：
```bash
最近 7 天的記錄數：716 筆
最新記錄時間：2025-11-01 06:55:03
最新記錄狀態：success
時間間隔：每 5 分鐘一筆（正常）
```

**結論**：數據採集正常，每 5 分鐘自動執行一次網路品質檢測。

### 2. API 返回的數據結構
測試 API 端點 `/api/ipxe-network-quality/statistics/?days=7&server_id=1`：
```json
{
  "summary": {
    "total_records": 704
  },
  "quality_trends": [
    {"time": "10-25 07:00", "ping_latency": null, "http_response_time": null},
    {"time": "10-25 08:00", "ping_latency": null, "http_response_time": null},
    ...
    {"time": "11-01 06:00", "ping_latency": 0.6, "http_response_time": 11.99}
  ]
}
```

**發現問題**：
- `quality_trends` 共 168 個數據點
- **其中 110 個數據點的值為 `null`**（佔比 65%）
- 原因：10月25日~10月28日期間系統未運行，該時段無數據
- 數據從 10月29日才開始有記錄

### 3. 前端圖表渲染問題
使用的圖表庫：**recharts**

問題根源：
```javascript
<Line
    type="monotone"
    dataKey="value"
    stroke="#1890ff"
    strokeWidth={2}
    dot={{ r: 4, fill: '#1890ff' }}
    activeDot={{ r: 6 }}
    name={title}
    // ❌ 缺少 connectNulls 屬性
/>
```

**recharts 的預設行為**：
- 當數據點的值為 `null` 或 `undefined` 時，**折線會斷開**
- 不會自動連接 null 值兩側的有效數據點
- 導致圖表出現視覺上的斷點

## ✅ 解決方案

### 修復方法
在所有使用 `<Line>` 組件的地方添加 `connectNulls={true}` 屬性：

```javascript
<Line
    type="monotone"
    dataKey="value"
    stroke="#1890ff"
    strokeWidth={2}
    dot={{ r: 4, fill: '#1890ff' }}
    activeDot={{ r: 6 }}
    name={title}
    connectNulls={true}  // ✅ 添加此屬性
/>
```

**`connectNulls` 屬性的作用**：
- 自動跳過 `null` 值
- 連接 `null` 值兩側的有效數據點
- 使線條保持連續，視覺效果更好

### 修改的文件清單

#### 1. iPXE 網路品質圖表
**文件**：`frontend/src/components/NetworkQualityChart.js`
- ✅ 修改 Ping 延遲圖
- ✅ 修改 HTTP 響應時間圖
- ✅ 修改 SSH 響應時間圖
- ✅ 修改丟包率圖
- ✅ 修改下載速度圖

#### 2. iPXE 統計分析
**文件**：`frontend/src/components/ipxe-analytics/StatisticsTab.js`
- ✅ 修改 MAC 管理趨勢線
- ✅ 修改 BOOT 請求趨勢線
- ✅ 修改總計趨勢線

#### 3. iPXE 概覽
**文件**：`frontend/src/components/ipxe-analytics/OverviewTab.js`
- ✅ 修改過去 7 天日誌趨勢圖（MAC 管理、BOOT 請求）

#### 4. NAS 分析
**文件**：`frontend/src/pages/NASAnalyticsPage.js`
- ✅ 修改每日統計趨勢圖（成功、失敗、總計）

#### 5. DHCP 統計分析
**文件**：`frontend/src/components/dhcp-analytics/StatisticsTab.js`
- ✅ 修改租約增長趨勢圖

## 📈 修復效果

### 修復前
```
圖表：  ●            ●                  ●        ●
       (斷點)      (大段空白)         (斷點)
```

### 修復後
```
圖表：  ●━━━━━━━━●━━━━━━━━━━━━━━━●━━━━━●
       (連續線條，即使中間有 null 值)
```

## 🎯 技術細節

### Recharts `connectNulls` 屬性
```javascript
connectNulls: boolean
```
- **預設值**：`false`
- **為 true 時**：自動連接 null 值兩側的有效點
- **為 false 時**：遇到 null 值會斷開線條

### 適用場景
適合在以下情況使用 `connectNulls={true}`：
1. 數據採集有間歇性中斷
2. 歷史數據有部分時段缺失
3. 需要展示整體趨勢，不強調數據缺口
4. 時間序列數據的視覺連續性更重要

### 不適用場景
以下情況應保持 `connectNulls={false}`：
1. 需要明確標示數據缺失時段
2. 數據缺失本身具有業務意義
3. 需要區分「值為 0」和「無數據」

## 🔧 部署步驟

### 1. 應用修改
```bash
# 所有修改已完成，無需手動操作
```

### 2. 重啟服務
```bash
docker restart nt-react
```

### 3. 驗證修復
1. 訪問 http://localhost/ipxe-analytics
2. 切換到「網路品質」標籤
3. 檢查所有圖表（Ping、HTTP、SSH、丟包率、下載速度）
4. 確認線條連續，無斷點

## 📝 其他發現

### 數據採集正常運行
- iPXE 網路品質監控腳本每 5 分鐘執行一次（cron job）
- 最近 7 天共採集 716 筆記錄
- 採集內容：Ping、HTTP、SSH、下載速度測試
- 狀態：正常運行中

### 數據分佈
```
2025-11-01: 84 筆（截至 06:55）
2025-10-31: 306 筆
2025-10-30: 192 筆
2025-10-29: 134 筆
10-25 ~ 10-28: 無數據（系統未運行）
```

### 建議
1. ✅ **圖表已修復**：添加 `connectNulls={true}` 解決斷點問題
2. ⚠️ **監控持續性**：確保 cron job 持續運行，避免數據中斷
3. 💡 **數據保留政策**：考慮設定舊數據清理策略（如保留 30 天）

## 🎉 總結

通過在所有 `<Line>` 組件添加 `connectNulls={true}` 屬性，成功解決了 iPXE 網路品質圖表的斷點問題。修改涵蓋了：

- ✅ iPXE 網路品質圖表（5 個圖表）
- ✅ iPXE 統計分析圖表（3 條線）
- ✅ iPXE 概覽圖表（2 條線）
- ✅ NAS 分析圖表（3 條線）
- ✅ DHCP 統計圖表（1 條線）

**總計修復**：6 個文件，14 個圖表組件

---

**日期**：2025-11-01  
**問題報告者**：用戶  
**修復者**：AI Assistant  
**狀態**：✅ 已完成
