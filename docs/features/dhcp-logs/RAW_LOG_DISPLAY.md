# DHCP Server 日誌 - Raw Log 顯示功能

## 📋 功能說明

為 DHCP Server 的日誌查看功能新增了**原始日誌（Raw Log）顯示**，與 iPXE 日誌保持一致的使用體驗。

---

## ✨ 新增功能

### 1. **Raw Log 顯示區塊**

每條日誌下方會顯示原始日誌內容：

```
┌─────────────────────────────────────────────────────────┐
│ 2025-11-09 19:25:33  INFO  Unknown(31)                  │
│                                                          │
│ Message: DHCPDISCOVER from 00:11:22:33:44:55           │
│                                                          │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 原始 Log（雙擊複製）:                                  │ │
│ │ Nov  9 19:25:33 dhcp-server dhcpd: DHCPDISCOVER... │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

**特點**：
- ✅ **灰底白框**：原始日誌使用 `#f5f5f5` 背景，易於區分
- ✅ **等寬字體**：使用 Monaco/Consolas 字體，方便閱讀日誌
- ✅ **雙擊複製**：雙擊日誌區塊可直接複製到剪貼簿
- ✅ **自動換行**：`whiteSpace: 'pre-wrap'` 保持格式並自動換行
- ✅ **小標籤**：顯示「原始 Log（雙擊複製）」提示

---

## 🎨 UI 設計規範

### 原始日誌區塊樣式

```javascript
{
    fontSize: '11px',                              // 較小字體（11px）
    fontFamily: 'Monaco, Consolas, "Courier New", monospace',  // 等寬字體
    color: '#666',                                  // 灰色文字
    marginTop: '8px',                               // 上方間距
    padding: '6px 8px',                             // 內邊距
    background: '#f5f5f5',                          // 灰色背景
    borderRadius: '4px',                            // 圓角
    border: '1px solid #e8e8e8',                    // 邊框
    cursor: 'text',                                 // 文字游標
    whiteSpace: 'pre-wrap',                         // 保持換行
    wordBreak: 'break-all',                         // 強制換行
}
```

### 小標籤樣式

```javascript
{
    color: '#999',                                  // 淺灰色
    marginBottom: '4px',                            // 下方間距
    fontSize: '10px',                               // 小字體
}
```

---

## 📦 CSV 匯出功能

CSV 匯出已同步更新，新增 **Raw Log** 欄位：

**CSV 格式**：
```csv
Timestamp,Level,Event,Message,Client Type,Raw Log
2025-11-09 19:25:33,INFO,DHCPDISCOVER,DHCPDISCOVER from 00:11:22:33:44:55,Unknown,"Nov  9 19:25:33 dhcp-server dhcpd: DHCPDISCOVER..."
```

**處理規則**：
- ✅ 逗號 `,` → 分號 `;`
- ✅ 雙引號 `"` → `""`（CSV 轉義）
- ✅ 換行符 `\n` → 空格 ` `（防止 CSV 格式錯誤）

---

## 🔧 技術實現

### 前端修改

**檔案**：`frontend/src/components/dhcp-analytics/LogsTab.js`

#### 1. 顯示原始日誌

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

#### 2. CSV 匯出更新

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

---

## 📊 後端資料結構

### DHCPLog 模型（已存在，無需修改）

**檔案**：`backend/api/models.py`

```python
class DHCPLog(models.Model):
    """DHCP 日誌模型 - 15天滾動視窗"""
    
    server = models.ForeignKey(DHCPServer, on_delete=models.CASCADE, ...)
    timestamp = models.DateTimeField(verbose_name='日誌時間', db_index=True)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, ...)
    event = models.CharField(max_length=30, blank=True, ...)
    message = models.CharField(max_length=200, ...)
    raw = models.TextField(verbose_name='原始日誌')  # ← 已存在
    
    # iPXE 識別相關欄位
    client_type = models.CharField(max_length=20, ...)
    boot_stage = models.CharField(max_length=50, blank=True, ...)
    vendor_class = models.CharField(max_length=500, blank=True, ...)
    user_class = models.CharField(max_length=200, blank=True, ...)
    
    # DHCP Option 82 欄位
    relay_agent_info = models.TextField(blank=True, ...)
    circuit_id = models.CharField(max_length=255, blank=True, ...)
    remote_id = models.CharField(max_length=255, blank=True, ...)
```

### Serializer（已支援，無需修改）

**檔案**：`backend/api/serializers.py`

```python
class DHCPLogSerializer(serializers.ModelSerializer):
    """DHCP 日誌序列化器"""
    
    server_name = serializers.CharField(source='server.name', read_only=True)
    server_ip = serializers.CharField(source='server.ip_address', read_only=True)
    client_type_display = serializers.CharField(source='get_client_type_display', read_only=True)
    
    class Meta:
        model = DHCPLog
        fields = '__all__'  # ← 包含 raw 欄位
        read_only_fields = ('created_at',)
```

---

## ✅ 使用方式

### 1. 查看原始日誌

1. 進入 **DHCP Server 分析** 頁面
2. 選擇伺服器
3. 切換到 **日誌查看** 分頁
4. 每條日誌下方會顯示原始日誌區塊

### 2. 複製原始日誌

- **方法 1**：雙擊原始日誌區塊
- **方法 2**：選取文字後使用 `Ctrl+C` (Windows/Linux) 或 `Cmd+C` (macOS)

### 3. 匯出包含原始日誌的 CSV

1. 點擊右上角 **匯出 CSV** 按鈕
2. CSV 檔案會包含 `Raw Log` 欄位
3. 可使用 Excel/Google Sheets 開啟

---

## 📋 與 iPXE 日誌的一致性

| 功能 | DHCP 日誌 | iPXE 日誌 | 一致性 |
|------|-----------|-----------|--------|
| 顯示原始日誌 | ✅ | ✅ | ✅ |
| 雙擊複製 | ✅ | ✅ | ✅ |
| 等寬字體 | ✅ | ✅ | ✅ |
| 灰底白框 | ✅ | ✅ | ✅ |
| CSV 匯出 | ✅ | ✅ | ✅ |
| 小標籤提示 | ✅ | ✅ | ✅ |

---

## 🎯 預期效果

### 顯示範例

```
┌───────────────────────────────────────────────────────────────┐
│ 2025-11-09 19:25:33  [INFO]  [DHCPDISCOVER]  [Unknown]       │
│                                                                │
│ DHCPDISCOVER from 00:11:22:33:44:55 via eth0                 │
│                                                                │
│ ┌─────────────────────────────────────────────────────────┐   │
│ │ 原始 Log（雙擊複製）:                                      │   │
│ │                                                          │   │
│ │ Nov  9 19:25:33 dhcp-server dhcpd: DHCPDISCOVER from   │   │
│ │ 00:11:22:33:44:55 via eth0: network 10.250.50.0/24:    │   │
│ │ no free leases                                          │   │
│ └─────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────┘
```

---

## 📝 測試清單

- [ ] **顯示測試**：確認原始日誌正確顯示
- [ ] **複製功能**：雙擊複製，顯示成功訊息
- [ ] **樣式測試**：灰底白框、等寬字體正確
- [ ] **長日誌測試**：超長日誌自動換行
- [ ] **CSV 匯出**：包含 Raw Log 欄位
- [ ] **空值處理**：沒有 raw 欄位時不顯示
- [ ] **多行日誌**：換行符正確處理

---

## 🚀 部署步驟

**前端部署**：

```bash
# 重啟 React 容器（自動熱重載）
docker compose restart react

# 或者重新構建
docker compose up -d --build react
```

**驗證**：

1. 瀏覽器訪問：`http://localhost`
2. 進入 DHCP Server 分析 → 日誌查看
3. 確認原始日誌顯示正常

---

## 📚 相關文檔

- [DHCP 日誌分析功能](./README.md)
- [iPXE 日誌顯示功能](../ipxe-logs/README.md)
- [時區設定說明](../../development/TIMEZONE_SETTINGS.md)

---

**最後更新**：2025-11-10  
**修改者**：GitHub Copilot  
**功能狀態**：✅ 已完成
