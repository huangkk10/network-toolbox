# MAC cc:28:aa:86:c3:7f 客戶端類型分析報告

## 📋 案例概述

**問題記錄：**
- **時間**：2025-11-01 04:05:32
- **MAC Address**：cc:28:aa:86:c3:7f (CC28AA86C37F)
- **IP Address**：10.250.71.22
- **Hostname**：PC-SSD-4632
- **DHCP Server**：10.250.71.1
- **事件類型**：Renew (Event ID: 11)

**爭議點：**
- 使用者聲稱這筆記錄當時是 **WinPE** 階段
- 系統識別為 **Windows OS**（基於 Hostname = "PC-SSD-4632"，非 MININT- 格式）

---

## 🔍 Windows DHCP Server 原始日誌分析

### 完整 CSV 日誌（19 個欄位）

```csv
11,11/01/25,04:05:32,Renew,10.250.71.22,PC-SSD-4632,CC28AA86C37F,,274190949,0,,,,0x4D53465420352E30,MSFT 5.0,,,,0
```

### 欄位解析

| 欄位 | 名稱 | 值 | 資料來源 |
|------|------|-----|---------|
| [0] | Event ID | `11` | DHCP Server |
| [1] | Date | `11/01/25` | DHCP Server |
| [2] | Time | `04:05:32` | DHCP Server |
| [3] | Description | `Renew` | DHCP Server |
| [4] | IP Address | `10.250.71.22` | DHCP Server |
| **[5]** | **Hostname** | **`PC-SSD-4632`** | **✅ DHCP Client (Option 12)** |
| [6] | MAC Address | `CC28AA86C37F` | ✅ DHCP Client (chaddr) |
| [7] | Username | `(空)` | - |
| [8] | TransactionID | `274190949` | ✅ DHCP Client |
| [9] | QResult | `0` | DHCP Server |
| [10] | Probationtime | `(空)` | DHCP Server |
| [11] | CorrelationID | `(空)` | DHCP Server |
| [12] | Dhcid | `(空)` | DHCP Client |
| [13] | VendorClass(Hex) | `0x4D53465420352E30` | ✅ DHCP Client |
| **[14]** | **VendorClass(ASCII)** | **`MSFT 5.0`** | **✅ DHCP Client (Option 60)** |
| [15] | UserClass(Hex) | `(空)` | DHCP Client |
| [16] | UserClass(ASCII) | `(空)` | DHCP Client |
| [17] | RelayAgentInfo | `(空)` | DHCP Relay |
| [18] | DnsRegError | `0` | DHCP Server |

---

## 🧩 關鍵資訊提取

### 1. Hostname = "PC-SSD-4632"

**特徵：**
- ✅ 11 個字元
- ✅ 非空字串
- ✅ 不是 "-"
- ❌ **不是以 "MININT-" 開頭**
- ✅ 符合正常 Windows 主機名格式

**來源：**
- **DHCP Option 12 (Host Name)**
- 由 **DHCP Client 在 DHCP Request 封包中提供**
- Windows DHCP Server **只記錄，不修改**

**標準 WinPE 行為：**
- WinPE 預設使用 `MININT-XXXXXX` 格式（隨機產生）
- 例如：`MININT-7Q8P9R0`、`MININT-A1B2C3D`

**可能的非標準配置：**
- 在 `unattend.xml` 中設定自訂 Hostname
- 透過 SCCM/WDS 任務序列設定
- 透過 PowerShell 腳本動態設定

### 2. Vendor Class = "MSFT 5.0"

**特徵：**
- 表示 Microsoft Windows 作業系統
- **不包含** PXE 相關字串（"PXEClient"、"PXE"）
- **不包含** iPXE 字串

**來源：**
- **DHCP Option 60 (Vendor Class Identifier)**
- 由 **DHCP Client 提供**

**WinPE vs Windows OS：**
- 標準 WinPE 和 Windows OS **都使用** "MSFT 5.0"
- **無法單獨靠 Vendor Class 區分** WinPE 和 Windows OS
- **必須配合 Hostname 判斷**

### 3. User Class = (空)

**特徵：**
- 沒有 User Class
- 不是 iPXE（iPXE 會提供 "iPXE"）

**來源：**
- **DHCP Option 77 (User Class)**
- 由 **DHCP Client 提供**（選填）

---

## 📊 識別邏輯分析

### 目前的 `identify_client_type()` 邏輯

```python
# 優先順序：
1. 如果 'iPXE' in (user_class or vendor_class)  → iPXE
2. 如果 'PXEClient' or 'PXE' in vendor_class    → PXE
3. 如果 hostname.startswith('minint-')          → WinPE
   OR ('MSFT' in vendor_class AND no hostname)  → WinPE
4. 如果 'MSFT' in vendor_class AND has_hostname 
   AND not 'minint-' prefix                     → Windows OS ✅
5. 其他                                          → Unknown
```

### 針對本案例的識別結果

**輸入：**
- Hostname = "PC-SSD-4632"（有值，非 MININT-）
- Vendor Class = "MSFT 5.0"
- User Class = (空)

**匹配邏輯第 4 條：**
```python
elif ('MSFT' in vendor_class or 'Microsoft' in vendor_class) \
     and hostname and hostname != '-' \
     and not hostname.lower().startswith('minint-'):
    client_type = 'Windows'
    boot_stage = 'Operating System'
```

**識別結果：**
- ✅ Client Type = **Windows**
- ✅ Boot Stage = **Operating System**

---

## 🤔 可能的情況分析

### 情況 1：這是標準 Windows OS（不是 WinPE）

**支持證據：**
- ✅ Hostname = "PC-SSD-4632"（正常 Windows 主機名格式）
- ✅ 時間 04:05:32 是凌晨，可能是正常的 DHCP Renew
- ✅ Event = Renew（不是新分配，是續約）
- ✅ 沒有 PXE 或 iPXE 相關標記

**結論：**
- 這是一台正常運行的 Windows 系統
- 正在進行 DHCP 租約續約
- **不是 WinPE 階段**

### 情況 2：這是使用自訂 Hostname 的 WinPE

**需要的證據：**
- ❓ WinPE 映像檔配置（unattend.xml）
- ❓ SCCM/WDS 任務序列設定
- ❓ 部署腳本或 PowerShell 命令
- ❓ 其他系統日誌（Event Viewer、SCCM、WDS）

**如果屬實，需要調整的識別邏輯：**
```python
# 可能需要添加額外的 WinPE 識別條件：
# - 檢查部署系統的特定 DHCP Option
# - 檢查特定的 IP 範圍（如部署專用 VLAN）
# - 結合時間序列分析（PXE → iPXE → WinPE 模式）
# - 結合其他日誌來源（SCCM、WDS）
```

### 情況 3：時間記錄有誤差

**可能性：**
- DHCP Server 記錄時間與實際事件時間有延遲
- 實際上 04:05:32 已經是 Windows OS 階段
- WinPE 階段可能是更早的時間（如 04:00:00 - 04:04:00）

**建議：**
- 查詢 04:00:00 - 04:10:00 的完整時間序列
- 尋找可能的 MININT- Hostname 記錄
- 分析啟動流程的完整時間軸

---

## 📈 建議的後續行動

### 1. 收集額外證據

**需要的資訊：**
- [ ] WinPE 映像檔的 `unattend.xml` 配置
- [ ] SCCM/WDS 任務序列設定截圖
- [ ] 該 MAC 在 04:00 - 04:10 的完整 DHCP 日誌
- [ ] 該電腦的 Windows Event Viewer 日誌
- [ ] 部署系統的日誌（如 SCCM 日誌）

### 2. 時間序列分析

**查詢建議：**
```sql
-- 查詢該 MAC 在 2025-11-01 03:30 - 04:30 的所有記錄
SELECT timestamp, event, client_type, message, raw
FROM dhcp_log
WHERE raw LIKE '%CC28AA86C37F%'
  AND timestamp BETWEEN '2025-11-01 03:30:00' AND '2025-11-01 04:30:00'
ORDER BY timestamp;
```

**期望發現：**
- PXE 階段（可能在 03:56 - 03:58）
- iPXE 階段（可能在 03:58 - 04:00）
- WinPE 階段（可能在 04:00 - 04:05，Hostname = MININT-?）
- Windows OS 階段（04:05 之後，Hostname = PC-SSD-4632）

### 3. 識別邏輯改進

**如果確認 WinPE 可以使用自訂 Hostname，可以考慮：**

**方案 A：添加部署相關的特徵檢測**
```python
# 檢查是否在部署 VLAN
if ip_address.startswith('10.250.'):
    # 可能是部署階段
    
# 檢查是否有特定的 DHCP Option
if specific_option_present:
    # 識別為 WinPE
```

**方案 B：時間序列分析**
```python
# 在同一個 MAC 的 30 分鐘內
# 如果先前有 PXE/iPXE 記錄，即使 Hostname 正常也標記為 WinPE
if has_recent_pxe_or_ipxe_activity:
    client_type = 'WinPE'
```

**方案 C：多來源資料融合**
```python
# 結合 SCCM/WDS 日誌
# 結合 iPXE Boot 日誌
# 確認是否正在執行部署任務
if in_deployment_task:
    client_type = 'WinPE'
```

---

## 📝 結論

### 基於現有資訊

**Windows DHCP Server 日誌顯示：**
- ✅ Hostname = "PC-SSD-4632"（由 DHCP Client 提供）
- ✅ Vendor Class = "MSFT 5.0"（由 DHCP Client 提供）
- ✅ 符合 Windows OS 的特徵

**識別邏輯的判斷：**
- ✅ **正確**（根據標準 WinPE 行為）
- ❓ **可能不完整**（如果 WinPE 使用自訂 Hostname）

### 等待確認的關鍵問題

1. **您的 WinPE 映像檔是否配置了自訂 Hostname？**
   - 如果是，請提供 `unattend.xml` 或相關設定
   
2. **您是如何確認當時是 WinPE 的？**
   - 是否有螢幕截圖？
   - 是否有部署系統的日誌？
   - 是否有其他確鑿的證據？

3. **該 MAC 在 04:00 - 04:05 之間是否有其他 DHCP 記錄？**
   - 是否有使用 MININT- 開頭的 Hostname？
   - 是否有 PXE/iPXE 相關的記錄？

### 下一步行動

**如果您能提供上述任何一項資訊，我們可以：**
- 調整識別邏輯以適應您的環境
- 添加額外的識別條件
- 改進 WinPE 檢測的準確性

**如果無法提供額外證據，則：**
- 目前的識別邏輯是正確的（基於標準 DHCP 行為）
- Hostname "PC-SSD-4632" 確實是 DHCP Client 自己報告的
- 系統識別為 Windows OS 是合理的判斷

---

**報告日期**：2025-11-01  
**分析者**：Network Toolbox AI Assistant  
**文件版本**：1.0
