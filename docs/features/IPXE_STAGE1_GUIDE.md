# iPXE 識別功能 - 階段 1 實作指南

**版本**：1.0  
**狀態**：✅ 功能已存在，需驗證  
**預計時間**：30 分鐘（驗證）或 2 小時（補充實作）

---

## 📋 階段 1 目標

**在 DHCP 日誌中自動識別並標記 iPXE/PXE/WinPE 等客戶端類型**

### 核心特點

- ✅ **完全前端實現** - 不需要修改資料庫
- ✅ **零後端修改** - 所有邏輯在前端處理
- ✅ **即時生效** - 重新載入頁面即可看到效果
- ✅ **視覺化呈現** - 使用圖示和顏色區分

---

## 🎯 階段 1 的具體內容

### **這個階段做什麼？**

1. **在日誌列表中顯示客戶端類型標籤**
   - 每條日誌旁邊顯示一個彩色圖示（如 🚀 iPXE）
   - 類似於 Log Level 的顯示方式（INFO, WARN, ERROR）

2. **自動識別客戶端類型**
   - 檢查日誌訊息中的**關鍵字**
   - 檢查日誌訊息中的 **MAC 地址前綴**
   - 根據**主機名稱模式**識別

3. **顯示統計資訊**
   - 在頁面頂部顯示各類型客戶端的數量
   - 例如：`[🚀 iPXE: 30] [⚙️ PXE: 15] [🪟 Windows: 200]`

### **這個階段不做什麼？**

- ❌ 不修改資料庫（不新增欄位）
- ❌ 不修改後端 API（不需要後端改動）
- ❌ 不記錄到資料庫（只在前端顯示）
- ❌ 不讀取 DHCP Server 的 Options（這是階段 2）

---

## 🔍 識別邏輯說明

### **如何識別 iPXE？**

**方法 1：關鍵字匹配**

檢查日誌訊息是否包含以下關鍵字（不區分大小寫）：

```javascript
if (message.toLowerCase().includes('ipxe')) {
    // 這是 iPXE 客戶端！
}
```

**範例日誌**：
```
✅ "DHCPDISCOVER from iPXE client via eth0"         → 識別為 iPXE
✅ "DHCPOFFER on 192.168.1.100 to iPXE-001"        → 識別為 iPXE
❌ "DHCPACK on 192.168.1.200 to DESKTOP-001"       → 不是 iPXE
```

---

**方法 2：主機名稱模式**

如果主機名稱中包含 iPXE 相關字樣：

```javascript
if (hostname.toLowerCase().includes('ipxe') || 
    hostname.toLowerCase().includes('pxe')) {
    // 可能是 PXE/iPXE 客戶端
}
```

**範例主機名**：
```
✅ "iPXE-server-001"    → iPXE
✅ "pxeboot-lab-02"     → PXE
✅ "MININT-ABC123"      → WinPE
❌ "DESKTOP-WIN10"      → Windows
```

---

**方法 3：MAC 地址特徵（虛擬機）**

某些 MAC 地址前綴代表虛擬機（常用於 PXE 啟動）：

```javascript
const vmMacPrefixes = ['00:0c:29', '00:50:56', '08:00:27', '52:54:00'];

if (vmMacPrefixes.some(prefix => message.includes(prefix))) {
    // 這是虛擬機，可能用於 PXE 測試
}
```

**範例 MAC**：
```
✅ "00:0c:29:12:34:56"  → VMware 虛擬機
✅ "08:00:27:aa:bb:cc"  → VirtualBox
✅ "52:54:00:11:22:33"  → QEMU/KVM
❌ "a0:b1:c2:d3:e4:f5"  → 普通設備
```

---

## 🎨 視覺呈現效果

### **日誌列表顯示**

```
時間                         Level    客戶端類型         日誌訊息
────────────────────────────────────────────────────────────────────────────
2025-10-28 10:15:23         [INFO]   [🚀 iPXE]        DHCPDISCOVER from iPXE-client via eth0
2025-10-28 10:16:10         [INFO]   [⚙️ PXE]         DHCPOFFER on 192.168.1.100 to pxeboot-01
2025-10-28 10:17:05         [INFO]   [🔧 WinPE]       DHCPREQUEST from MININT-ABC123 via eth1
2025-10-28 10:18:20         [INFO]   [📦 VM]          DHCPACK to 00:0c:29:12:34:56 via eth0
2025-10-28 10:19:33         [INFO]   [🪟 Windows]     DHCPRELEASE from DESKTOP-001 via eth2
2025-10-28 10:20:15         [WARN]   [❓ Unknown]     Duplicate IP 192.168.3.168 detected
```

### **統計資訊顯示**

```
┌────────────────────────────────────────────────────────────────┐
│ 客戶端類型分佈（前 6 名）：                                      │
│ [🚀 iPXE: 30] [⚙️ PXE: 25] [🪟 Windows: 200] [📦 VM: 80]      │
│ [🐧 Linux: 45] [❓ Unknown: 20]                                │
└────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ 實作步驟（如果功能不存在）

### **步驟 1：確認現有功能**

```bash
# 1. 查看是否已有客戶端類型檢測功能
grep -n "detectClientType" frontend/src/components/dhcp-analytics/LogsTab.js

# 2. 查看功能文檔
cat docs/features/CLIENT_TYPE_DETECTION.md

# 3. 如果找到，跳到「驗證測試」；如果沒找到，繼續下面的步驟
```

---

### **步驟 2：修改 LogsTab.js（新增檢測函數）**

**位置**：`frontend/src/components/dhcp-analytics/LogsTab.js`

**在檔案開頭（第 20 行左右）新增檢測函數**：

```javascript
// 客戶端類型檢測函數
const detectClientType = (message) => {
    if (!message) return null;
    
    const msgLower = message.toLowerCase();
    
    // iPXE 檢測（最高優先級）
    if (msgLower.includes('ipxe')) {
        return { type: 'iPXE', icon: '🚀', color: 'purple' };
    }
    
    // PXE 檢測
    if (msgLower.includes('pxeboot') || 
        msgLower.includes('pxe boot') || 
        msgLower.includes('pxeclient')) {
        return { type: 'PXE', icon: '⚙️', color: 'cyan' };
    }
    
    // WinPE 檢測
    if (msgLower.includes('winpe') || msgLower.includes('minint-')) {
        return { type: 'WinPE', icon: '🔧', color: 'geekblue' };
    }
    
    // UEFI 檢測
    if (msgLower.includes('uefi')) {
        return { type: 'UEFI', icon: '⚡', color: 'magenta' };
    }
    
    // VM 檢測（常見虛擬機 MAC 前綴）
    const vmMacPatterns = [
        /00:0c:29/i,  // VMware
        /00:50:56/i,  // VMware ESXi
        /08:00:27/i,  // VirtualBox
        /52:54:00/i,  // QEMU/KVM
        /00:15:5d/i,  // Hyper-V
    ];
    if (vmMacPatterns.some(pattern => pattern.test(message))) {
        return { type: 'VM', icon: '📦', color: 'orange' };
    }
    
    // Windows 檢測
    if (msgLower.includes('desktop-') || 
        msgLower.includes('win-') || 
        msgLower.includes('laptop-')) {
        return { type: 'Windows', icon: '🪟', color: 'blue' };
    }
    
    // Linux 檢測
    if (msgLower.includes('ubuntu') || 
        msgLower.includes('debian') || 
        msgLower.includes('centos')) {
        return { type: 'Linux', icon: '🐧', color: 'green' };
    }
    
    return null;
};
```

---

### **步驟 3：修改日誌渲染部分**

**位置**：`LogsTab.js` 中渲染日誌的地方（通常在 `return` 區塊內）

**找到渲染日誌訊息的代碼**，類似這樣：

```javascript
// 原始代碼（只顯示 Level）
<div>
    {getLevelTag(log.level)}
    <span>{log.message}</span>
</div>
```

**修改為（加入客戶端類型標籤）**：

```javascript
// 新代碼（顯示 Level + 客戶端類型）
<div>
    {getLevelTag(log.level)}
    
    {/* 新增：客戶端類型標籤 */}
    {(() => {
        const clientType = detectClientType(log.message);
        if (clientType) {
            return (
                <Tag color={clientType.color} style={{ marginLeft: '8px' }}>
                    {clientType.icon} {clientType.type}
                </Tag>
            );
        }
        return null;
    })()}
    
    <span style={{ marginLeft: '8px' }}>{log.message}</span>
</div>
```

---

### **步驟 4：新增統計資訊（選用）**

**在 `loadLogs()` 函數中計算客戶端類型統計**：

```javascript
const loadLogs = async () => {
    // ... 原有代碼 ...
    
    // 新增：計算客戶端類型統計
    const clientTypeStats = {};
    response.data.logs.forEach(log => {
        const clientType = detectClientType(log.message);
        if (clientType) {
            const typeName = clientType.type;
            clientTypeStats[typeName] = (clientTypeStats[typeName] || 0) + 1;
        } else {
            clientTypeStats['Unknown'] = (clientTypeStats['Unknown'] || 0) + 1;
        }
    });
    
    setClientTypeStatistics(clientTypeStats);
};
```

**在頁面頂部顯示統計**：

```jsx
<div style={{ marginBottom: '16px' }}>
    <strong>客戶端類型：</strong>
    {Object.entries(clientTypeStatistics)
        .sort((a, b) => b[1] - a[1])  // 按數量排序
        .slice(0, 6)                   // 只顯示前 6 種
        .map(([type, count]) => {
            const typeInfo = detectClientType(type) || { icon: '❓', color: 'default' };
            return (
                <Tag key={type} color={typeInfo.color} style={{ margin: '4px' }}>
                    {typeInfo.icon} {type}: {count}
                </Tag>
            );
        })}
</div>
```

---

## ✅ 驗證測試

### **測試步驟**

1. **重啟前端容器**：
   ```bash
   docker compose restart react
   ```

2. **開啟瀏覽器**：
   ```
   http://localhost
   ```

3. **進入日誌頁面**：
   - 點擊「DHCP 分析」
   - 選擇一個 DHCP Server
   - 點擊「Logs」頁籤

4. **檢查是否顯示客戶端類型圖示**：
   - 查看每條日誌旁邊是否有彩色標籤
   - 嘗試搜尋 `ipxe` 或 `pxe` 關鍵字

---

### **測試案例**

**建立測試日誌**（在 `logs/dhcp_operations.log` 中）：

```bash
# 手動添加測試日誌
cat >> logs/dhcp_operations.log << 'EOF'
[INFO] 2025-10-28 14:00:00 | DHCPDISCOVER from iPXE-test-001 via eth0
[INFO] 2025-10-28 14:01:00 | DHCPOFFER on 192.168.1.100 to pxeboot-client via eth0
[INFO] 2025-10-28 14:02:00 | DHCPREQUEST from MININT-ABC123 via eth1
[INFO] 2025-10-28 14:03:00 | DHCPACK to 00:0c:29:12:34:56 via eth0
[INFO] 2025-10-28 14:04:00 | DHCPRELEASE from DESKTOP-WIN10 via eth2
EOF
```

**重新載入日誌**，應該看到：
- 第 1 條：🚀 iPXE（紫色）
- 第 2 條：⚙️ PXE（青色）
- 第 3 條：🔧 WinPE（藍色）
- 第 4 條：📦 VM（橙色）
- 第 5 條：🪟 Windows（藍色）

---

## 📊 預期成果

### **完成後應該看到**

1. ✅ 日誌列表中每條記錄都有客戶端類型標籤
2. ✅ iPXE/PXE 客戶端被正確識別並標記
3. ✅ 統計區域顯示各類型客戶端數量
4. ✅ 可以透過關鍵字快速篩選特定類型

### **未完成的部分（留給階段 2）**

- ❌ 無法從 DHCP Server 讀取 Option 60/66/67
- ❌ 無法知道 Scope 是否配置了 PXE Boot
- ❌ 無法記錄客戶端類型到資料庫
- ❌ 無法在 Leases Tab 中顯示客戶端類型

---

## 🔧 故障排查

### **問題 1：看不到客戶端類型標籤**

**可能原因**：
- 前端未重新編譯
- 瀏覽器快取

**解決方案**：
```bash
# 清除快取並重建
docker compose down
docker compose up -d --build react

# 清除瀏覽器快取（Ctrl+Shift+Delete）
```

---

### **問題 2：所有日誌都顯示 Unknown**

**可能原因**：
- 日誌訊息中沒有關鍵字
- 檢測函數未正確執行

**解決方案**：
```bash
# 檢查日誌內容
tail -20 logs/dhcp_operations.log

# 手動添加測試日誌（見上方測試案例）
```

---

### **問題 3：圖示顯示為方塊**

**可能原因**：
- 系統不支援 Emoji

**解決方案**：
```javascript
// 改用文字標籤
{ type: 'iPXE', icon: 'iPXE', color: 'purple' }  // 不使用 Emoji
```

---

## 📚 相關文檔

- `docs/features/CLIENT_TYPE_DETECTION.md` - 客戶端類型檢測完整說明
- `docs/features/IPXE_ANALYSIS_AND_IMPLEMENTATION.md` - iPXE 實作總覽
- `frontend/src/components/dhcp-analytics/LogsTab.js` - 前端代碼

---

## 📝 檢查清單

### **實作前**
- [ ] 確認是否已有 `CLIENT_TYPE_DETECTION` 功能
- [ ] 閱讀 `CLIENT_TYPE_DETECTION.md` 文檔
- [ ] 備份 `LogsTab.js` 檔案

### **實作中**
- [ ] 新增 `detectClientType()` 函數
- [ ] 修改日誌渲染邏輯
- [ ] 新增統計資訊顯示（選用）
- [ ] 重啟前端容器

### **測試**
- [ ] 手動添加測試日誌
- [ ] 驗證 iPXE 識別功能
- [ ] 驗證 PXE 識別功能
- [ ] 驗證 VM 識別功能
- [ ] 驗證統計資訊顯示

### **完成**
- [ ] 截圖記錄效果
- [ ] 更新文檔
- [ ] Git 提交

---

**最後更新**：2025-10-28  
**預計完成時間**：30 分鐘（驗證）或 2 小時（實作）  
**下一步**：完成階段 1 後，可考慮進入**階段 2**（擴展資料模型）
