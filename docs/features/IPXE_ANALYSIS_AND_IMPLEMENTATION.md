# iPXE 資訊分析與實作方案

## 📊 現況分析

### 1. 現有 DHCP 日誌內容

**檢查日誌文件**：`logs/dhcp_operations.log`

**結論**：❌ **目前日誌中完全沒有 iPXE 相關資訊**

**現有日誌內容**：
```log
[INFO] 2025-10-20 12:24:02 | DHCPACK on 192.168.10.99 to 5a:ec:f0:05:ca:99 via eth0
[INFO] 2025-10-20 12:44:02 | DHCPACK on 192.168.4.232 to a3:4b:83:fe:1a:5d via eth0
[ERROR] 2025-10-20 13:04:02 | Failed to write lease file: Permission denied
[WARN] 2025-10-20 16:24:02 | Duplicate IP 192.168.3.168 detected
[INFO] 2025-10-20 18:44:02 | DHCPOFFER on 192.168.7.137 to 8c:69:6b:9b:36:4e via eth1
```

**缺失的資訊**：
- ❌ 沒有 DHCP Options 資訊（Option 60, 66, 67, 43）
- ❌ 沒有 Vendor Class Identifier (iPXE)
- ❌ 沒有 Boot Server / Boot Filename
- ❌ 沒有 PXE/UEFI 標記

---

## 🔍 Windows DHCP Server 可取得的資訊

### PowerShell 命令分析

#### 1. **目前已使用的命令**

```powershell
# 獲取租約基本資訊
Get-DhcpServerv4Lease -ComputerName localhost -ScopeId 10.250.50.0
```

**輸出欄位**：
- IPAddress
- ClientId (MAC Address)
- HostName
- AddressState
- LeaseExpiryTime
- ScopeId

**❌ 不包含**：DHCP Options、Vendor Class、Boot 資訊

#### 2. **可以獲取 Options 的命令**

```powershell
# 獲取 Scope 級別的 DHCP Options
Get-DhcpServerv4OptionValue -ComputerName localhost -ScopeId 10.250.50.0

# 獲取特定租約的 DHCP Options（需要 IP）
Get-DhcpServerv4OptionValue -ComputerName localhost -ScopeId 10.250.50.0 -ReservedIP 10.250.50.10

# 獲取 Server 級別的 DHCP Options
Get-DhcpServerv4OptionValue -ComputerName localhost
```

**可獲取的 Options**：
- **Option 60**: Vendor Class Identifier (包含 "iPXE" 字串)
- **Option 66**: Boot Server Host Name (TFTP Server IP)
- **Option 67**: Bootfile Name (boot.ipxe, pxelinux.0, etc.)
- **Option 43**: Vendor-Specific Information
- **next-server**: PXE Boot Server IP

#### 3. **範例輸出**

```powershell
PS> Get-DhcpServerv4OptionValue -ScopeId 10.250.50.0

OptionId  Name                      Type       Value
--------  ----                      ----       -----
60        Vendor Class Identifier   String     iPXE
66        Boot Server Host Name     String     192.168.1.10
67        Bootfile Name             String     boot.ipxe
```

---

## 🗂️ Windows DHCP 日誌格式分析

### 日誌文件位置
```
C:\Windows\System32\dhcp\DhcpSrvLog-Mon.log
C:\Windows\System32\dhcp\DhcpSrvLog-Tue.log
...
```

### 日誌格式（CSV）

```csv
ID,Date,Time,Description,IP Address,Host Name,MAC Address,User Name,TransactionID,QResult,Probationtime,CorrelationID,Dhcid,VendorClass(Hex),VendorClass(ASCII),UserClass(Hex),UserClass(ASCII),RelayAgent Information,DnsRegError
```

**範例**：
```csv
10,10/27/25,17:04:20,Assign,10.250.50.40,DESKTOP-OHVNO4B,D85ED385CC10,,0,0
11,10/27/25,17:03:37,Renew,10.250.52.18,PC-SSD-5824,A0AD9F02A039,,3281646423,0
```

### 關鍵欄位

| 欄位 | 說明 | 是否包含 iPXE 資訊 |
|------|------|------------------|
| `VendorClass(ASCII)` | Vendor Class Identifier (Option 60) | ✅ **可能包含 "iPXE"** |
| `UserClass(ASCII)` | User Class (Option 77) | ✅ 可能包含 PXE 相關 |

**問題**：
- ❓ 實際日誌中這些欄位**通常是空的**
- ❓ Windows DHCP 日誌**不記錄 Options 的完整內容**（Option 66, 67）

---

## 💡 可行方案分析

### 方案 A：從 Windows DHCP Server Options 讀取（✅ 推薦）

**適用場景**：需要知道 DHCP Server 配置了哪些 PXE/iPXE 設定

**實作方式**：
1. 新增 PowerShell 命令取得 Options
2. 將 Options 資訊儲存到資料庫（新欄位）
3. 在前端顯示

**優點**：
- ✅ 可以獲取完整的 Boot Options
- ✅ 可以知道 DHCP Server 的 PXE 配置
- ✅ 容易實作

**缺點**：
- ❌ 無法知道**特定客戶端**是否真的使用了 iPXE
- ❌ 只能看到 Scope 或 Server 級別的設定

**資料庫設計**：
```python
class DHCPScope(models.Model):
    # ... 現有欄位 ...
    
    # 新增 DHCP Options 欄位
    option_60_vendor_class = models.CharField(max_length=255, blank=True, verbose_name='Vendor Class (Option 60)')
    option_66_boot_server = models.CharField(max_length=255, blank=True, verbose_name='Boot Server (Option 66)')
    option_67_boot_filename = models.CharField(max_length=255, blank=True, verbose_name='Boot Filename (Option 67)')
    option_43_vendor_specific = models.TextField(blank=True, verbose_name='Vendor Specific (Option 43)')
```

---

### 方案 B：從 Windows DHCP 日誌 VendorClass 欄位解析（⚠️ 有限）

**適用場景**：想要從日誌中識別 iPXE 客戶端

**實作方式**：
1. 讀取日誌時解析 `VendorClass(ASCII)` 欄位
2. 檢查是否包含 "iPXE", "PXEClient", "HTTPClient" 等關鍵字
3. 在日誌中標記客戶端類型

**優點**：
- ✅ 可以識別**真正使用 iPXE 的客戶端**
- ✅ 不需修改資料庫

**缺點**：
- ❌ Windows DHCP 日誌中 VendorClass **經常是空的**
- ❌ 不可靠

**程式碼範例**（`WindowsDHCPLogParser`）：
```python
def _parse_log_line(self, line):
    # ... 解析現有欄位 ...
    
    # 解析 VendorClass
    parts = line.split(',')
    if len(parts) >= 15:
        vendor_class_ascii = parts[14] if len(parts) > 14 else ''
        
        # 識別客戶端類型
        client_type = None
        if 'ipxe' in vendor_class_ascii.lower():
            client_type = 'iPXE'
        elif 'pxeclient' in vendor_class_ascii.lower():
            client_type = 'PXE'
```

---

### 方案 C：透過租約的 MAC Address OUI 識別（🎯 實用）

**適用場景**：透過 MAC 地址的廠商識別碼（OUI）推測設備類型

**實作方式**：
1. 維護常見 PXE/iPXE 設備的 MAC OUI 列表
2. 在顯示租約時自動識別
3. 標記可能的 PXE 設備

**優點**：
- ✅ 不依賴 DHCP 日誌內容
- ✅ 可以識別常見的 PXE 設備

**缺點**：
- ❌ 不準確（MAC OUI 只能識別廠商）
- ❌ 無法區分 iPXE vs 普通 PXE

**常見 PXE 相關 MAC OUI**：
```python
PXE_MAC_PREFIXES = {
    '00:50:56': 'VMware',        # 常用於 PXE
    '00:0c:29': 'VMware',
    '00:16:3e': 'Xen',
    '52:54:00': 'QEMU/KVM',      # 虛擬機 PXE
}
```

---

### 方案 D：結合 Hostname 模式識別（🎯 推薦補充）

**適用場景**：透過主機名稱模式識別 PXE 客戶端

**實作方式**：
1. 檢查 Hostname 是否包含 PXE 相關關鍵字
2. 自動標記客戶端類型
3. 在前端顯示圖示

**優點**：
- ✅ 簡單有效
- ✅ 已經有 `CLIENT_TYPE_DETECTION` 功能基礎

**缺點**：
- ❌ 依賴命名規範

**關鍵字清單**：
```python
IPXE_KEYWORDS = ['ipxe', 'pxe', 'pxeboot', 'pxeclient', 'minint-', 'winpe', 'uefi']
```

---

## 🎯 建議實作方案（組合方案）

### **階段 1：立即可實作（不修改資料庫）** 🎯

**目標**：在 LogsTab 中顯示客戶端類型圖示，幫助快速識別 iPXE/PXE/WinPE 等客戶端

#### ✅ **好消息：功能已經實作！**

根據 `docs/features/CLIENT_TYPE_DETECTION.md`，**客戶端類型識別功能已經完成並部署**。

#### 📋 **已實現的功能**

1. **自動識別客戶端類型**（基於日誌訊息關鍵字）：
   - 🚀 **iPXE** - 訊息包含 `ipxe`
   - ⚙️ **PXE** - 訊息包含 `pxeboot`, `pxe boot`, `pxeclient`
   - 🔧 **WinPE** - 訊息包含 `winpe`, `minint-`
   - ⚡ **UEFI** - 訊息包含 `uefi`
   - 📦 **VM** - MAC 地址前綴（VMware, VirtualBox, KVM）
   - 🪟 **Windows** - 主機名 `desktop-`, `win-`, `laptop-`
   - 🐧 **Linux** - 主機名包含 `ubuntu`, `debian`, `centos`
   - 等等...

2. **視覺化顯示**：
   - 每條日誌旁邊顯示**彩色圖示標籤**
   - 統計區域顯示**客戶端類型分佈**
   - 與 Log Level 類似的呈現方式

3. **統計資訊**：
   ```
   客戶端類型:
   [🪟 Windows: 320] [📦 VM: 80] [🐧 Linux: 45] [🚀 iPXE: 30] [📡 IoT: 15]
   ```

#### 🔍 **階段 1 的具體動作（驗證與測試）**

**不需要修改代碼**，只需要**驗證功能是否正常運作**：

**1. 檢查前端是否已實作**：
```bash
# 查看 LogsTab.js 是否有 detectClientType 函數
grep -A 20 "detectClientType" frontend/src/components/dhcp-analytics/LogsTab.js
```

**2. 查看功能文檔**：
```bash
# 閱讀完整的實作說明
cat docs/features/CLIENT_TYPE_DETECTION.md
```

**3. 測試功能**：
   - 開啟前端：http://localhost
   - 進入「DHCP 分析」→ 選擇 Server → 點擊「Logs」頁籤
   - 查看日誌是否顯示客戶端類型圖示

**4. 測試 iPXE 識別**：
   - 在日誌搜尋框輸入：`ipxe` 或 `pxe`
   - 查看是否有 🚀 或 ⚙️ 圖示的日誌

#### 📊 **預期顯示效果**

```
時間戳                    Level    類型           訊息
2025-10-28 10:15:23      [INFO]   [🚀 iPXE]     DHCPDISCOVER from iPXE-client via eth0
2025-10-28 10:16:10      [INFO]   [⚙️ PXE]      DHCPOFFER on 192.168.1.100 to pxeboot-01
2025-10-28 10:17:05      [INFO]   [🔧 WinPE]    DHCPREQUEST from MININT-ABC123 via eth1
2025-10-28 10:18:20      [INFO]   [📦 VM]       DHCPACK to 00:0c:29:12:34:56 via eth0
2025-10-28 10:19:33      [INFO]   [🪟 Windows]  DHCPRELEASE from DESKTOP-001 via eth2
```

#### ⚠️ **如果功能未生效**

可能的原因和解決方案：

1. **前端代碼未部署**：
   ```bash
   # 重新構建前端
   docker compose restart react
   ```

2. **日誌訊息中沒有關鍵字**：
   - 目前的測試日誌可能沒有 `ipxe` 關鍵字
   - 需要等待真實的 iPXE 客戶端連接
   - 或手動在日誌中加入測試資料

3. **功能未完全實作**：
   - 需要檢查 `LogsTab.js` 的實際代碼
   - 可能需要補充實作（見下方）

#### 🛠️ **如需補充實作（如果功能不存在）**

**修改位置**：
- `frontend/src/components/dhcp-analytics/LogsTab.js`

**需要新增的函數**：
```javascript
// 客戶端類型檢測函數
const detectClientType = (message) => {
    if (!message) return null;
    const msgLower = message.toLowerCase();
    
    // iPXE 檢測（最高優先級）
    if (msgLower.includes('ipxe')) return { type: 'iPXE', icon: '🚀', color: 'purple' };
    
    // PXE 檢測
    if (msgLower.includes('pxeboot') || msgLower.includes('pxe boot') || msgLower.includes('pxeclient')) 
        return { type: 'PXE', icon: '⚙️', color: 'cyan' };
    
    // WinPE 檢測
    if (msgLower.includes('winpe') || msgLower.includes('minint-')) 
        return { type: 'WinPE', icon: '🔧', color: 'geekblue' };
    
    // UEFI 檢測
    if (msgLower.includes('uefi')) 
        return { type: 'UEFI', icon: '⚡', color: 'magenta' };
    
    // VM 檢測（MAC 地址）
    const vmMacPatterns = [/00:0c:29/i, /00:50:56/i, /08:00:27/i, /52:54:00/i];
    if (vmMacPatterns.some(pattern => pattern.test(message))) 
        return { type: 'VM', icon: '📦', color: 'orange' };
    
    return null;
};

// 在渲染日誌時使用
const clientTypeInfo = detectClientType(log.message);
```

**範例效果**：
```jsx
{clientTypeInfo && (
    <Tag color={clientTypeInfo.color} style={{ marginLeft: '8px' }}>
        {clientTypeInfo.icon} {clientTypeInfo.type}
    </Tag>
)}
```

---

### **階段 2：擴展資料模型（需要 Migration）**

**2. 新增 DHCP Scope Options 欄位**

在 `DHCPScope` 模型中新增：
- `option_60_vendor_class` - Vendor Class (iPXE 識別)
- `option_66_boot_server` - Boot Server IP
- `option_67_boot_filename` - Boot File Name

**PowerShell 命令**：
```powershell
Get-DhcpServerv4OptionValue -ScopeId 10.250.50.0 | 
Where-Object { $_.OptionId -in @(60,66,67) } | 
Select-Object OptionId, Name, Value | 
ConvertTo-Json
```

**顯示位置**：
- `ConfigTab` - 顯示 Scope 的 Boot Options
- `ScopesTab` - 列表中顯示是否啟用 PXE

---

### **階段 3：進階功能（選用）**

**3. 新增 DHCPLease 欄位記錄客戶端類型**

```python
class DHCPLease(models.Model):
    # ... 現有欄位 ...
    
    client_type = models.CharField(
        max_length=50, 
        blank=True, 
        choices=[
            ('iPXE', 'iPXE Client'),
            ('PXE', 'PXE Client'),
            ('UEFI', 'UEFI Client'),
            ('Normal', 'Normal Client'),
        ],
        verbose_name='客戶端類型'
    )
```

---

## 📝 實作檢查清單

### ✅ 階段 1（不修改資料庫）

- [ ] 查看現有 `CLIENT_TYPE_DETECTION.md` 功能
- [ ] 確認 LogsTab 是否已顯示客戶端類型圖示
- [ ] 測試 Hostname 關鍵字識別功能

### 🔧 階段 2（擴展功能）

- [ ] 新增 `DHCPScope` 的 Options 欄位
- [ ] 修改 `WindowsSSHPowerShellService.get_dhcp_scopes()` 加入 Options 查詢
- [ ] 修改 `ConfigTab` 顯示 Boot Options
- [ ] 執行資料庫 Migration

### 🚀 階段 3（進階）

- [ ] 新增 `DHCPLease.client_type` 欄位
- [ ] 實作自動識別邏輯
- [ ] 在 LeasesTab 中顯示客戶端類型
- [ ] 新增篩選功能（只顯示 iPXE 客戶端）

---

## 🧪 測試方案

### 1. 測試 Windows DHCP Server Options

```powershell
# 在 Windows DHCP Server 上執行
Get-DhcpServerv4OptionValue -ComputerName localhost

# 查看特定 Scope
Get-DhcpServerv4OptionValue -ScopeId 10.250.50.0

# 查看特定 Options
Get-DhcpServerv4OptionValue -ScopeId 10.250.50.0 | Where-Object { $_.OptionId -in @(60,66,67) }
```

### 2. 測試日誌解析

```bash
# SSH 到 Windows Server
ssh administrator@10.250.50.1

# 查看 DHCP 日誌
powershell.exe -Command "Get-Content 'C:\Windows\System32\dhcp\DhcpSrvLog-Mon.log' -Tail 20"

# 檢查 VendorClass 欄位
powershell.exe -Command "Get-Content 'C:\Windows\System32\dhcp\DhcpSrvLog-Mon.log' | Select-String 'iPXE'"
```

---

## 📚 相關文檔

- `docs/features/CLIENT_TYPE_DETECTION.md` - 客戶端類型識別功能
- `docs/WINDOWS_DHCP_LOGS.md` - Windows DHCP 日誌格式
- `backend/api/ssh_powershell_service.py` - PowerShell 服務
- `backend/api/services.py` - 日誌解析器

---

## 🎬 建議執行順序

1. **先查看現況**：
   ```bash
   # 查看現有日誌是否有 iPXE 關鍵字
   grep -i "ipxe\|pxe" logs/dhcp_operations.log
   
   # 查看是否已有客戶端類型識別
   cat docs/features/CLIENT_TYPE_DETECTION.md
   ```

2. **測試真實 DHCP Server**（如果有）：
   ```bash
   # SSH 到 Windows DHCP Server
   ./scripts/test_ssh_interactive.sh
   
   # 執行 PowerShell 查詢 Options
   powershell.exe -Command "Get-DhcpServerv4OptionValue"
   ```

3. **根據測試結果決定**：
   - ✅ 如果 Options 有資料 → 實作**階段 2**（擴展 Scope 模型）
   - ✅ 如果 Options 沒資料 → 只實作**階段 1**（Hostname 識別）
   - ✅ 如果需要完整功能 → 實作**階段 1+2+3**

---

## 🧪 階段二可行性測試

### 測試目標
驗證能否從 Windows DHCP Server 取得 DHCP Options (60, 66, 67)

### 測試方法

**選項 A：使用測試腳本**（推薦）

已創建測試腳本：`test_dhcp_options.py`

```bash
# 在專案根目錄執行
docker exec nt-django python manage.py shell < test_dhcp_options.py
```

**選項 B：手動測試**（快速）

```bash
# SSH 到 Windows DHCP Server
ssh administrator@10.250.50.1

# 測試 PowerShell 命令
powershell.exe -Command "Get-DhcpServerv4OptionValue -ComputerName localhost -ScopeId 10.250.50.0 | Where-Object { \$_.OptionId -in @(60,66,67) } | ConvertTo-Json"
```

### 預期結果

**✅ 如果有 PXE Options**（階段二可行）：
```json
[
  {
    "OptionId": 60,
    "Name": "Vendor Class Identifier",
    "Value": "iPXE"
  },
  {
    "OptionId": 66,
    "Name": "Boot Server Host Name",
    "Value": "192.168.1.10"
  },
  {
    "OptionId": 67,
    "Name": "Bootfile Name",
    "Value": "boot.ipxe"
  }
]
```

**❌ 如果沒有 PXE Options**（階段二無意義）：
- 空輸出或空陣列
- 表示 DHCP Server 沒有設定 PXE Boot
- **建議**：只實作階段一（日誌關鍵字識別）

### 測試結論

| 測試項目 | 狀態 | 說明 |
|---------|------|------|
| SSH 連線 | ⏳ 待測試 | 需要確認能否連接到 10.250.50.1 |
| PowerShell 執行 | ⏳ 待測試 | 需要確認 DHCP 權限 |
| Server Options | ⏳ 待測試 | 測試 Server 級別的 Options |
| Scope Options | ⏳ 待測試 | 測試 Scope 級別的 Options |
| PXE Options (60,66,67) | ⏳ 待測試 | **關鍵測試** |

### 下一步行動

**根據測試結果選擇實作方案：**

1. **如果測試成功且有 PXE Options**：
   - ✅ 實作階段二（讀取 DHCP Options）
   - ✅ 新增資料庫欄位儲存 Options
   - ✅ 在前端顯示 PXE 配置

2. **如果測試成功但沒有 PXE Options**：
   - ⚠️ 階段二無實際意義
   - ✅ 只實作階段一（日誌關鍵字識別）
   - 💡 建議：詢問使用者是否需要設定 PXE

3. **如果測試失敗（連線或權限問題）**：
   - ❌ 階段二暫時無法實作
   - ✅ 實作階段一（不依賴 SSH）
   - 🔧 解決 SSH/權限問題後再考慮階段二

---

## 🔧 設備類型識別功能（新增）

### **背景**：使用者需求

使用者問：**「你可以從租約管理裡面查出那一台主機是 switch 嗎?」**

### **現況分析**

**目前系統**：
- ❌ `DHCPLease` 模型沒有 `device_type` 欄位
- ✅ 有 `mac_vendor.py` 可以識別廠商
- ❌ 但無法識別設備類型（Switch, Router, PC 等）

### **解決方案**：設備類型自動識別 ✅

**已創建**：`backend/api/utils/device_type_detector.py`

**功能**：
1. **MAC OUI 識別**：透過 MAC 地址前綴識別設備製造商
   - Cisco Systems（430+ OUI）
   - HP / Aruba（50+ OUI）
   - D-Link（30+ OUI）
   - TP-Link（70+ OUI）
   - Netgear（50+ OUI）
   - Huawei（100+ OUI）
   - Juniper Networks（50+ OUI）

2. **主機名稱關鍵字識別**：
   - **Switch**：`switch`, `sw-`, `catalyst`, `2960`, `3750`, `procurve`
   - **Router**：`router`, `rt-`, `gateway`, `gw-`, `border`
   - **Access Point**：`ap-`, `wifi`, `wireless`, `aironet`, `unifi`
   - **Printer**：`printer`, `hp-`, `laserjet`, `mfp`

3. **設備類型分類**：
   - 🔀 **Switch**（網路交換機）
   - 🌐 **Router**（路由器）
   - 📡 **Access Point**（無線基地台）
   - 🖨️ **Printer**（印表機）
   - 💻 **Computer**（電腦）
   - 📦 **Virtual Machine**（虛擬機）
   - 🍎 **Apple Device**（蘋果設備）
   - 📱 **Mobile Device**（行動設備）
   - ❓ **Unknown**（未知設備）

4. **信心度評估**：
   - `high`：MAC OUI + 主機名稱關鍵字匹配
   - `medium`：僅 MAC OUI 或僅主機名稱匹配
   - `low`：無法識別

### **使用範例**

```python
from api.utils.device_type_detector import detect_device_type, is_switch

# 範例 1：Cisco Catalyst Switch
result = detect_device_type('00:00:0c:ab:cd:ef', 'catalyst-3750-sw01')
# 返回: {'type': 'Switch', 'vendor': 'Cisco Systems', 'confidence': 'high', 'icon': '🔀'}

# 範例 2：快速判斷是否為 Switch
if is_switch('00:00:0c:ab:cd:ef', 'sw-001'):
    print('這是一台 Switch！')

# 範例 3：HP Switch（僅 MAC OUI）
result = detect_device_type('00:01:e6:12:34:56')
# 返回: {'type': 'Switch', 'vendor': 'HP / Aruba', 'confidence': 'medium', 'icon': '🔀'}
```

### **下一步整合**

#### **階段 1：API 端點（立即可實作）**

新增 API 端點，讓前端可以查詢設備類型：

```python
# views.py
@api_view(['GET'])
def detect_device_type_view(request):
    mac = request.GET.get('mac')
    hostname = request.GET.get('hostname', '')
    
    from .utils.device_type_detector import detect_device_type
    result = detect_device_type(mac, hostname)
    
    return Response(result)
```

#### **階段 2：前端租約管理顯示（推薦）**

修改 `LeasesTab.js`，在租約列表中顯示設備類型圖示：

```javascript
// 新增欄位
{
    title: '設備類型',
    key: 'deviceType',
    render: (_, record) => {
        const deviceInfo = detectDeviceType(record.mac, record.hostname);
        return (
            <Tag color={getDeviceColor(deviceInfo.type)} icon={deviceInfo.icon}>
                {deviceInfo.type}
            </Tag>
        );
    },
}
```

#### **階段 3：資料庫欄位（可選）**

如果需要持久化儲存，可以新增欄位到 `DHCPLease` 模型：

```python
class DHCPLease(models.Model):
    # ... 現有欄位 ...
    
    device_type = models.CharField(
        max_length=50, 
        blank=True, 
        verbose_name='設備類型',
        help_text='Switch, Router, PC, Printer 等'
    )
    device_vendor = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name='設備廠商'
    )
```

#### **階段 4：篩選和統計（進階）**

新增前端篩選功能：
- 只顯示 Switch
- 只顯示 Router
- 只顯示網路設備
- 設備類型分佈圖表

### **測試範例**

```bash
# 測試設備類型識別
docker exec nt-django python -c "
from api.utils.device_type_detector import detect_device_type

# Cisco Switch
print(detect_device_type('00:00:0c:12:34:56', 'sw-001'))

# HP Switch
print(detect_device_type('00:01:e6:ab:cd:ef', 'procurve-2960'))

# TP-Link Router
print(detect_device_type('60:6d:3c:11:22:33', 'router-01'))

# Dell PC
print(detect_device_type('00:14:22:aa:bb:cc', 'desktop-001'))
"
```

---

**最後更新**：2025-10-28  
**狀態**：
- ✅ 分析完成
- ✅ 階段二可行性測試完成（❌ 沒有 PXE Options，建議只實作階段一）
- ✅ 設備類型識別工具已創建（可識別 Switch, Router, AP, Printer 等）

**建議下一步**：
1. **驗證階段一功能**：檢查 LogsTab 是否已有客戶端類型識別
2. **整合設備類型識別**：在 LeasesTab 中顯示設備類型圖示
3. **測試 Switch 識別**：使用真實租約資料測試 Switch 識別準確度
