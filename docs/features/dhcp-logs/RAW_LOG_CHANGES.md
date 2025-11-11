# DHCP Server 日誌 Raw Log 顯示功能 - 修改總結

## 📋 修改概述

為 DHCP Server 的日誌查看功能新增了**原始日誌（Raw Log）顯示**，讓使用者可以：
1. ✅ 查看完整的原始日誌內容
2. ✅ 雙擊複製原始日誌到剪貼簿
3. ✅ 匯出 CSV 時包含原始日誌欄位

---

## 📝 修改檔案清單

### 1. **前端修改**

| 檔案 | 修改內容 | 行數變化 |
|------|----------|----------|
| `frontend/src/components/dhcp-analytics/LogsTab.js` | 新增 Raw Log 顯示區塊 | +24 行 |
| `frontend/src/components/dhcp-analytics/LogsTab.js` | 更新 CSV 匯出邏輯 | +3 行 |

**總計前端修改**：1 個檔案，+27 行

### 2. **文檔新增**

| 檔案 | 說明 |
|------|------|
| `docs/features/dhcp-logs/RAW_LOG_DISPLAY.md` | 完整功能說明文檔 |
| `test_dhcp_raw_log.sh` | 自動測試腳本 |
| `DHCP_RAW_LOG_CHANGES.md` | 本修改總結文件 |

**總計新增**：3 個檔案

### 3. **後端修改**

❌ **無需修改後端**：
- ✅ `DHCPLog` 模型已有 `raw` 欄位
- ✅ `DHCPLogSerializer` 使用 `fields = '__all__'`，自動包含 `raw`
- ✅ API 端點已正確返回 `raw` 欄位

---

## 🎨 UI 變更說明

### 修改前

```
┌─────────────────────────────────────────┐
│ 2025-11-09 19:25:33  INFO               │
│ DHCPDISCOVER from 00:11:22:33:44:55    │
└─────────────────────────────────────────┘
```

### 修改後

```
┌─────────────────────────────────────────┐
│ 2025-11-09 19:25:33  INFO               │
│ DHCPDISCOVER from 00:11:22:33:44:55    │
│                                          │
│ ┌─────────────────────────────────────┐ │
│ │ 原始 Log（雙擊複製）:                │ │
│ │ Nov  9 19:25:33 dhcp-server dhcpd: │ │
│ │ DHCPDISCOVER from 00:11:22:33:44:55│ │
│ │ via eth0: network 10.250.50.0/24   │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

---

## 🔧 技術細節

### 1. Raw Log 顯示區塊

**新增代碼**：
```javascript
{log.raw && (
    <div
        style={{
            fontSize: '11px',
            fontFamily: 'Monaco, Consolas, "Courier New", monospace',
            color: '#666',
            marginTop: '8px',
            padding: '6px 8px',
            background: '#f5f5f5',
            borderRadius: '4px',
            border: '1px solid #e8e8e8',
            cursor: 'text',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-all',
        }}
        title="雙擊複製原始日誌"
        onDoubleClick={() => {
            navigator.clipboard.writeText(log.raw);
            message.success('原始日誌已複製到剪貼簿');
        }}
    >
        <div style={{ color: '#999', marginBottom: '4px', fontSize: '10px' }}>
            原始 Log（雙擊複製）:
        </div>
        {log.raw}
    </div>
)}
```

**特點**：
- ✅ **條件渲染**：只在 `log.raw` 存在時顯示
- ✅ **雙擊複製**：`onDoubleClick` 觸發複製功能
- ✅ **成功提示**：使用 Ant Design `message.success()`
- ✅ **響應式設計**：`wordBreak: 'break-all'` 確保長日誌換行

### 2. CSV 匯出更新

**修改前**：
```javascript
const csvHeader = 'Timestamp,Level,Event,Message\n';
const csvRows = logs.map(log => {
    const timestamp = log.timestamp || '-';
    const level = log.level || '-';
    const event = log.event || '-';
    const msg = (log.message || '').replace(/,/g, ';').replace(/"/g, '""');
    return `"${timestamp}","${level}","${event}","${msg}"`;
}).join('\n');
```

**修改後**：
```javascript
const csvHeader = 'Timestamp,Level,Event,Message,Client Type,Raw Log\n';
const csvRows = logs.map(log => {
    const timestamp = log.timestamp || '-';
    const level = log.level || '-';
    const event = log.event || '-';
    const clientType = log.client_type || '-';
    const msg = (log.message || '').replace(/,/g, ';').replace(/"/g, '""');
    const raw = (log.raw || '').replace(/,/g, ';').replace(/"/g, '""').replace(/\n/g, ' ');
    return `"${timestamp}","${level}","${event}","${msg}","${clientType}","${raw}"`;
}).join('\n');
```

**新增處理**：
- ✅ 新增 `Client Type` 欄位
- ✅ 新增 `Raw Log` 欄位
- ✅ 換行符 `\n` → 空格（防止 CSV 格式錯誤）

---

## 📊 資料流程

```
原始 DHCP 日誌檔案（伺服器）
├─ /var/log/syslog
│  └─ Nov  9 19:25:33 dhcp-server dhcpd: DHCPDISCOVER from ...
│
↓ SSH 同步到資料庫
├─ DHCPLog.raw = "Nov  9 19:25:33 dhcp-server dhcpd: ..."
│
↓ Django Serializer 序列化
├─ DHCPLogSerializer (fields='__all__')
│  └─ JSON: { "raw": "Nov  9 19:25:33 ...", ... }
│
↓ API 返回給前端
├─ GET /api/dhcp-analytics/logs/?server=1
│  └─ { "logs": [{ "raw": "...", ... }], ... }
│
↓ React 組件渲染
└─ LogsTab.js 顯示原始日誌區塊
   └─ 用戶雙擊 → 複製到剪貼簿
```

---

## ✅ 測試清單

### 手動測試

- [ ] **顯示測試**：確認原始日誌正確顯示
- [ ] **複製功能**：雙擊複製，顯示「原始日誌已複製到剪貼簿」
- [ ] **樣式測試**：灰底白框、等寬字體正確
- [ ] **長日誌測試**：超長日誌自動換行
- [ ] **CSV 匯出**：包含 `Raw Log` 欄位
- [ ] **空值處理**：沒有 `raw` 欄位時不顯示區塊
- [ ] **多行日誌**：換行符正確處理

### 自動測試

```bash
# 執行測試腳本
./test_dhcp_raw_log.sh
```

---

## 🚀 部署步驟

### 1. 重啟 React 容器

```bash
docker compose restart react
```

### 2. 驗證功能

1. 瀏覽器訪問：`http://localhost`
2. 進入 **DHCP Server 分析** → **日誌查看**
3. 選擇一個伺服器
4. 確認每條日誌下方顯示原始日誌

### 3. 測試複製功能

1. 雙擊原始日誌區塊
2. 確認出現「原始日誌已複製到剪貼簿」提示
3. 貼上驗證（`Ctrl+V` 或 `Cmd+V`）

### 4. 測試 CSV 匯出

1. 點擊右上角「匯出 CSV」
2. 打開 CSV 檔案
3. 確認包含 `Raw Log` 欄位

---

## 📈 預期效果

### 使用者體驗改進

| 改進項目 | 說明 |
|---------|------|
| **完整性** | 可查看完整的原始日誌，不再只看到解析後的訊息 |
| **可追溯性** | 原始日誌保留所有細節，方便故障排查 |
| **便利性** | 雙擊複製功能，快速複製日誌到工單或文檔 |
| **一致性** | 與 iPXE 日誌保持相同的 UI 風格和操作邏輯 |

### 數據完整性

| 項目 | 狀態 |
|------|------|
| **資料庫儲存** | ✅ `DHCPLog.raw` 欄位已存在 |
| **API 返回** | ✅ Serializer 自動包含 `raw` |
| **前端顯示** | ✅ 新增顯示區塊 |
| **CSV 匯出** | ✅ 已更新匯出邏輯 |

---

## 🔗 相關資源

### 文檔

- [功能說明文檔](./docs/features/dhcp-logs/RAW_LOG_DISPLAY.md)
- [DHCP 日誌分析](./docs/features/dhcp-logs/README.md)
- [時區設定說明](./docs/development/TIMEZONE_SETTINGS.md)

### 參考設計

- iPXE 日誌顯示：`frontend/src/components/ipxe-analytics/LogsTab.js`
- 類似的 Raw Log 顯示實現

### 後端相關

- 模型定義：`backend/api/models.py` - `DHCPLog`
- 序列化器：`backend/api/serializers.py` - `DHCPLogSerializer`
- API 端點：`backend/api/views/dhcp_logs.py`

---

## 📌 注意事項

### 1. 瀏覽器相容性

- ✅ **Clipboard API**：需要 HTTPS 或 localhost
- ✅ **現代瀏覽器**：Chrome 66+, Firefox 63+, Safari 13.1+

### 2. 性能考量

- ✅ **條件渲染**：只在 `log.raw` 存在時渲染
- ✅ **無額外請求**：使用現有 API 響應數據
- ✅ **分頁機制**：不會一次載入過多日誌

### 3. 資料安全

- ⚠️ **敏感資訊**：原始日誌可能包含 IP、MAC 等敏感資訊
- ✅ **權限控制**：遵循現有的認證授權機制

---

## 🎯 完成狀態

| 任務 | 狀態 | 完成時間 |
|------|------|----------|
| 前端顯示功能 | ✅ 完成 | 2025-11-10 |
| CSV 匯出更新 | ✅ 完成 | 2025-11-10 |
| 文檔撰寫 | ✅ 完成 | 2025-11-10 |
| 測試腳本 | ✅ 完成 | 2025-11-10 |
| 部署驗證 | ⏳ 待執行 | - |

---

## 📞 支援

如有任何問題或建議，請：
1. 查看文檔：`docs/features/dhcp-logs/RAW_LOG_DISPLAY.md`
2. 執行測試：`./test_dhcp_raw_log.sh`
3. 查看日誌：`docker compose logs react`

---

**最後更新**：2025-11-10  
**修改者**：GitHub Copilot  
**版本**：v1.0.0  
**狀態**：✅ 已完成，待部署驗證
