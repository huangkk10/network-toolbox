# MAC cc:28:aa:86:c3:7f 證據收集報告

**生成時間**：2025-11-01  
**案例編號**：DHCP-ANALYSIS-001  
**目標記錄時間**：2025-11-01 04:05:32

---

## 📊 執行摘要

本報告根據**建議行動 1：收集額外證據**，對 MAC `cc:28:aa:86:c3:7f` 在 2025-11-01 的 DHCP 活動進行了完整的時間序列分析。

### 關鍵發現

- ✅ **成功從資料庫找到 18 筆記錄**
- ✅ **確認目標記錄存在**（2025-11-01 04:05:32）
- ⚠️ **該 MAC 在當天只使用了一個 Hostname: "PC-SSD-4632"**
- ⚠️ **沒有發現任何 MININT- 格式的 Hostname**
- ⚠️ **所有記錄都被識別為 "Windows OS"**

---

## 🔍 資料庫查詢結果

### 查詢條件

```python
Date: 2025-11-01 (整天)
MAC: CC28AA86C37F (大寫格式)
資料來源: DHCPLog 資料表
```

### 查詢統計

- **資料庫總記錄數**：74,806 筆
- **2025-11-01 總記錄數**：18,995 筆
- **該 MAC 的記錄數**：18 筆
- **時間範圍**：2025-10-28 00:00:49 ~ 2025-11-01 05:29:55

---

## 📋 完整時間序列（18 筆記錄）

根據資料庫查詢結果，以下是該 MAC 在 2025-11-01 的所有 DHCP 活動：

### 時間序列概覽

| # | 時間 | 事件 | IP | Hostname | Client Type | 備註 |
|---|------|------|-----|----------|-------------|------|
| 1 | 2025-11-01 00:16:49 | Renew | 10.250.71.22 | PC-SSD-4632 | Windows | |
| 2 | 2025-11-01 00:31:32 | Renew | 10.250.71.22 | PC-SSD-4632 | Windows | |
| 3 | 2025-11-01 00:50:49 | Renew | 10.250.71.22 | PC-SSD-4632 | Windows | |
| 4 | 2025-11-01 01:05:32 | Renew | 10.250.71.22 | PC-SSD-4632 | Windows | |
| 5 | 2025-11-01 01:24:49 | Renew | 10.250.71.22 | PC-SSD-4632 | Windows | |
| 6 | 2025-11-01 01:39:32 | Renew | 10.250.71.22 | PC-SSD-4632 | Windows | |
| 7 | 2025-11-01 01:58:49 | Renew | 10.250.71.22 | PC-SSD-4632 | Windows | |
| 8 | 2025-11-01 02:13:32 | Renew | 10.250.71.22 | PC-SSD-4632 | Windows | |
| 9 | 2025-11-01 02:32:49 | Renew | 10.250.71.22 | PC-SSD-4632 | Windows | |
| 10 | 2025-11-01 02:47:32 | Renew | 10.250.71.22 | PC-SSD-4632 | Windows | |
| 11 | 2025-11-01 03:06:50 | Renew | 10.250.71.22 | PC-SSD-4632 | Windows | |
| 12 | 2025-11-01 03:21:32 | Renew | 10.250.71.22 | PC-SSD-4632 | Windows | |
| 13 | 2025-11-01 03:40:50 | Renew | 10.250.71.22 | PC-SSD-4632 | Windows | |
| 14 | 2025-11-01 03:55:32 | Renew | 10.250.71.22 | PC-SSD-4632 | Windows | |
| 15 | 2025-11-01 04:05:32 | Renew | 10.250.71.22 | PC-SSD-4632 | Windows | **⚠️ 目標記錄** |
| 16 | 2025-11-01 04:14:50 | Renew | 10.250.71.22 | PC-SSD-4632 | Windows | |
| 17 | 2025-11-01 04:29:32 | Renew | 10.250.71.22 | PC-SSD-4632 | Windows | |
| 18 | 2025-11-01 04:48:50 | Renew | 10.250.71.22 | PC-SSD-4632 | Windows | |

### 觀察結果

1. **所有記錄都是 Renew 事件**
   - 沒有 Assign（新分配）
   - 沒有 Release（釋放）
   - 這是一個持續運行的系統在進行定期的 DHCP 租約續約

2. **Renew 間隔時間**
   - 最短間隔：約 9 分鐘（04:05:32 → 04:14:50）
   - 最長間隔：約 19 分鐘（03:40:50 → 03:55:32）
   - 平均間隔：約 15 分鐘
   - **這是標準的 DHCP Renew 行為**（通常在租約時間的 50% 時續約）

3. **IP 地址穩定**
   - 所有記錄都使用相同的 IP：10.250.71.22
   - 表示這是一個穩定的租約

4. **Hostname 從未改變**
   - 所有 18 筆記錄都使用 "PC-SSD-4632"
   - **沒有任何記錄使用 MININT- 格式**
   - **沒有空 Hostname 的記錄**

5. **Client Type 識別**
   - 所有記錄都被識別為 "Windows" (Operating System)
   - 沒有 PXE、iPXE 或 WinPE 階段的記錄

---

## 🎯 目標記錄詳細分析

### 記錄 #15 - 2025-11-01 04:05:32

這就是您詢問的記錄。以下是完整的欄位分析：

```
原始 CSV:
11,11/01/25,04:05:32,Renew,10.250.71.22,PC-SSD-4632,CC28AA86C37F,,274190949,0,,,,0x4D53465420352E30,MSFT 5.0,,,,0
```

#### 欄位解析

| 欄位 | 值 | 說明 |
|------|-----|------|
| [0] Event ID | 11 | Renew（租約更新）|
| [1] Date | 11/01/25 | 2025年11月1日 |
| [2] Time | 04:05:32 | 凌晨4點5分32秒 |
| [3] Description | Renew | 租約續約 |
| [4] IP Address | 10.250.71.22 | DHCP Client IP |
| **[5] Hostname** | **PC-SSD-4632** | **✅ 關鍵欄位** |
| [6] MAC Address | CC28AA86C37F | 網卡地址 |
| [7] Username | (空) | 無認證 |
| [8] TransactionID | 274190949 | DHCP 交易 ID |
| [9] QResult | 0 | DNS 查詢結果 |
| [10-12] | (空) | 保留欄位 |
| [13] VendorClass(Hex) | 0x4D53465420352E30 | MSFT 5.0 的十六進制 |
| **[14] VendorClass(ASCII)** | **MSFT 5.0** | **✅ 關鍵欄位** |
| [15] UserClass(Hex) | (空) | 無 User Class |
| [16] UserClass(ASCII) | (空) | 無 User Class |
| [17] RelayAgentInfo | (空) | 無 Relay Agent |
| [18] DnsRegError | 0 | 無 DNS 錯誤 |

#### 識別結果

```
Client Type: Windows
Boot Stage: Operating System
Reason: MSFT vendor class + hostname "PC-SSD-4632" without MININT- prefix
```

#### 前後記錄對比

| 時間 | 事件 | Hostname | Client Type | 間隔 |
|------|------|----------|-------------|------|
| 03:55:32 | Renew | PC-SSD-4632 | Windows | ↓ 10 分鐘 |
| **04:05:32** | **Renew** | **PC-SSD-4632** | **Windows** | **← 目標** |
| 04:14:50 | Renew | PC-SSD-4632 | Windows | ↑ 9 分鐘 |

---

## 📊 統計分析

### Hostname 使用統計

```
唯一使用的 Hostname:
  - "PC-SSD-4632" (18 次，100%)

未發現的 Hostname 類型:
  ✗ MININT-XXXXXX 格式（0 次）
  ✗ 空 Hostname（0 次）
  ✗ "-" (0 次)
```

### Client Type 分布

```
Windows OS: 18 次 (100%)
WinPE:       0 次 (0%)
iPXE:        0 次 (0%)
PXE:         0 次 (0%)
```

### Vendor Class 分析

```
所有記錄都使用:
  - Vendor Class (ASCII): "MSFT 5.0"
  - Vendor Class (Hex): 0x4D53465420352E30

這是標準的 Microsoft Windows 識別碼
```

### User Class 分析

```
所有記錄:
  - User Class: (空)

說明:
  - 沒有使用 DHCP Option 77
  - 不是 iPXE (iPXE 會提供 "iPXE")
```

---

## 🤔 關鍵問題

基於以上證據，我們發現以下**矛盾之處**：

### 證據 A：支持「這是 Windows OS」

1. ✅ Hostname = "PC-SSD-4632"（正常 Windows 主機名格式）
2. ✅ 所有 18 筆記錄都使用相同的 Hostname
3. ✅ 沒有任何 MININT- 格式的記錄
4. ✅ 所有記錄都是 Renew（持續運行的系統）
5. ✅ 穩定的 IP 和租約
6. ✅ Vendor Class = "MSFT 5.0"（Windows 標準）

### 證據 B：支持「這可能是 WinPE」（需要您提供）

1. ❓ **您的確認**：您表示「很確定這是 WinPE」
2. ❓ **時間點**：凌晨 04:05:32 是否是部署時間？
3. ❓ **WinPE 配置**：是否使用自訂 Hostname？
4. ❓ **部署日誌**：SCCM/WDS 是否有相關記錄？
5. ❓ **操作記錄**：當時是否有人在操作這台電腦？

### 缺少的關鍵證據

為了確認這筆記錄是否真的是 WinPE，我們需要以下證據：

#### 1. WinPE 映像檔配置
```xml
<!-- unattend.xml 範例 -->
<component name="Microsoft-Windows-Setup">
    <ComputerName>PC-SSD-4632</ComputerName>  <!-- 是否有這個設定？ -->
</component>
```

#### 2. SCCM/WDS 任務序列
- 是否有設定自訂 Hostname 的步驟？
- 部署開始和結束時間？
- 是否在 04:05:32 前後執行？

#### 3. 其他系統日誌
- Windows Event Viewer（如果已進入 Windows）
- SCCM 客戶端日誌
- WDS 伺服器日誌
- iPXE Boot 日誌（查看是否有 PXE/iPXE 活動）

#### 4. 網路監控
- 該時間點的網路流量
- 是否有大量檔案傳輸（WIM 映像）？
- 是否有 TFTP/HTTP 活動？

---

## 💡 可能的解釋

### 解釋 1：這確實是 Windows OS（最可能）

**支持證據：**
- 所有 DHCP 日誌證據都指向 Windows OS
- 沒有任何 PXE/iPXE/WinPE 的跡象
- 穩定的租約和 Hostname

**時間線：**
```
00:16:49 ─┐
00:31:32  │
...       ├─ Windows OS 正常運行，每 15 分鐘續約
04:05:32 ←┼─ 目標時間（只是普通的 DHCP Renew）
04:14:50  │
...      ─┘
```

### 解釋 2：這是使用自訂 Hostname 的 WinPE

**需要滿足：**
- WinPE 被配置為使用 "PC-SSD-4632" 而非 "MININT-XXXXXX"
- 部署過程持續了至少 4 小時（00:16 ~ 04:48）
- 在這段時間內沒有 PXE/iPXE 活動被記錄

**質疑點：**
- ⚠️ WinPE 部署通常很短（10-30 分鐘）
- ⚠️ 為什麼沒有 PXE/iPXE 階段的記錄？
- ⚠️ 為什麼 Hostname 從一開始就是 "PC-SSD-4632"？

### 解釋 3：時間記錄有誤差

**可能性：**
- WinPE 階段在 00:16 之前（更早的時間）
- 04:05:32 已經是 Windows OS 階段
- 您記憶中的時間與實際不符

---

## 📈 建議的後續行動

### 優先級 1：確認 WinPE 配置

**行動：**
1. 檢查 WinPE 映像檔的 `unattend.xml`
2. 檢查是否有設定 `<ComputerName>PC-SSD-4632</ComputerName>`

**命令：**
```powershell
# 掛載 WinPE 映像
DISM /Mount-Wim /WimFile:C:\Path\To\WinPE.wim /Index:1 /MountDir:C:\Mount

# 查看 unattend.xml
Get-Content C:\Mount\Windows\System32\unattend.xml
```

### 優先級 2：查詢其他日誌來源

**行動：**
1. 查詢 iPXE Boot Server 日誌（該 MAC 在 03:00-04:30 的活動）
2. 查詢 SCCM/WDS 日誌（是否有部署記錄）
3. 查詢 NAS 日誌（是否有 WIM 傳輸）

**我可以幫您執行：**
```bash
# 查詢 iPXE 日誌
docker exec nt-django python manage.py shell ...

# 查詢 NAS 連接日誌
docker exec nt-django python manage.py shell ...
```

### 優先級 3：時間序列關聯分析

**行動：**
1. 查詢該 MAC 在 2025-11-01 00:00-05:00 的**所有**日誌：
   - DHCP 日誌 ✅ (已完成)
   - iPXE 日誌 ❓
   - NAS 日誌 ❓
   
2. 建立完整的啟動流程時間軸

### 優先級 4：調整識別邏輯（如果確認是 WinPE）

**如果確認 WinPE 確實使用自訂 Hostname，則需要：**

**方案 A：添加時間序列分析**
```python
# 如果 30 分鐘內有 PXE/iPXE 活動，即使 Hostname 正常也標記為 WinPE
if has_recent_pxe_or_ipxe_within_30_minutes:
    client_type = 'WinPE'
```

**方案 B：添加部署 IP 範圍檢測**
```python
# 如果在已知的部署 IP 範圍內
if ip_address in deployment_ip_ranges:
    # 可能是 WinPE
```

**方案 C：整合其他日誌來源**
```python
# 結合 SCCM/WDS/iPXE 日誌確認
if is_in_deployment_task(mac_address, timestamp):
    client_type = 'WinPE'
```

---

## 📝 結論

### 基於現有證據

**Windows DHCP Server 日誌明確顯示：**
- ✅ Hostname = "PC-SSD-4632"（由 DHCP Client 提供）
- ✅ Vendor Class = "MSFT 5.0"（標準 Windows）
- ✅ 所有 18 筆記錄都使用相同的 Hostname
- ✅ 沒有任何 WinPE 特徵（MININT-、空 Hostname）

**系統識別邏輯的判斷：**
- ✅ **正確**（基於標準 DHCP 行為和 WinPE 預設配置）
- ❓ **可能不完整**（如果您的環境使用非標準 WinPE 配置）

### 等待您的回饋

**請提供以下任一資訊：**

1. **WinPE 配置檔**（unattend.xml 或任務序列設定）
2. **當時的操作記錄**（是否確實在執行部署？）
3. **其他系統日誌**（SCCM、WDS、Event Viewer）
4. **時間確認**（04:05:32 是否確實在 WinPE 階段？）

### 下一步

**如果您無法提供額外證據：**
- 目前的識別邏輯是**正確的**
- Hostname "PC-SSD-4632" 是 DHCP Client 自己報告的
- 識別為 Windows OS 是合理的判斷

**如果您能提供證據證明是 WinPE：**
- 我們可以調整識別邏輯
- 添加針對您環境的特殊檢測規則
- 改進 WinPE 識別的準確性

---

**報告完成日期**：2025-11-01  
**分析者**：Network Toolbox AI Assistant  
**文件版本**：1.0  
**狀態**：等待使用者回饋
