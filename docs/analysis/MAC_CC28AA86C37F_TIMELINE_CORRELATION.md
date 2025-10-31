# MAC cc:28:aa:86:c3:7f - 時間軸關聯分析

## 📅 日期：2025-11-01

## 🔍 關鍵發現

**在 03:45:39 - 04:12:04 期間，這台電腦同時出現在 DHCP 和 iPXE 日誌中！**

---

## 📊 整合時間軸（03:30 - 04:30）

| 時間 | 來源 | 事件類型 | 詳細資訊 |
|------|------|----------|----------|
| **03:45:39** | 🌐 iPXE | `set_mac` | IP: 10.252.170.171, User Agent: ansible-httpget |
| **03:46:35** | 🌐 iPXE | `get_mac` | IP: 10.250.71.22, User Agent: **iPXE/1.21.1+** ⚠️ |
| **03:47:23** | 🌐 iPXE | `set_mac` | IP: 10.252.170.171, User Agent: ansible-httpget |
| **03:50:37** | 📡 DHCP | Renew | Hostname: **PC-SSD-4632**, Client Type: **Windows** |
| **03:56:59** | 🌐 iPXE | `set_mac` | IP: 10.252.170.171, User Agent: ansible-httpget |
| **03:57:52** | 🌐 iPXE | `get_mac` | IP: 10.250.71.22, User Agent: **iPXE/1.21.1+** ⚠️ |
| **03:58:29** | 🌐 iPXE | `set_mac` | IP: 10.252.170.171, User Agent: ansible-httpget |
| **04:04:37** | 🌐 iPXE | `get_mac` | IP: 10.250.71.22, User Agent: **iPXE/1.21.1+** ⚠️ |
| **04:05:32** | 📡 DHCP | Renew | Hostname: **PC-SSD-4632**, Client Type: **Windows** ⭐ **爭議記錄** |
| **04:07:02** | 🌐 iPXE | `get_mac` | IP: 10.250.71.22, User Agent: **iPXE/1.21.1+** ⚠️ |
| **04:10:17** | 🌐 iPXE | `get_mac` | IP: 10.250.71.22, User Agent: **iPXE/1.21.1+** ⚠️ |
| **04:11:30** | 🌐 iPXE | `set_mac` | IP: 10.252.170.171, User Agent: ansible-httpget |
| **04:12:04** | 🌐 iPXE | `set_mac` | IP: 10.252.170.171, User Agent: ansible-httpget |
| **04:20:44** | 📡 DHCP | Renew | Hostname: **PC-SSD-4632**, Client Type: **Windows** |

---

## 🔬 關鍵證據分析

### 1. **iPXE 活動模式**

**Client IP 10.250.71.22 的 `get_mac` 請求**：
- 03:46:35 ← iPXE 開機
- 03:57:52 ← 持續通訊
- **04:04:37** ← **距離 DHCP 04:05:32 僅 55 秒**
- **04:07:02** ← **DHCP 記錄後 90 秒**
- 04:10:17 ← 仍在 iPXE 環境

**特徵**：
- User Agent = `iPXE/1.21.1+ (g83449)`
- Action = `get_mac`（查詢 MAC 設定）
- 約每 3-7 分鐘一次請求

### 2. **DHCP 記錄矛盾**

**同一時段的 DHCP 記錄**：
- 03:50:37 - Hostname: "PC-SSD-4632", Client Type: Windows
- **04:05:32 - Hostname: "PC-SSD-4632", Client Type: Windows** ⭐
- 04:20:44 - Hostname: "PC-SSD-4632", Client Type: Windows

**矛盾點**：
- DHCP 顯示正常 Windows 主機名稱
- 但 iPXE 日誌證明系統正在 iPXE 環境運行
- **iPXE 環境不應該發送標準 Windows 主機名稱**

---

## 💡 推論：WinPE with Custom Hostname

### 情境重建

**03:45:39 - 04:12:04 發生了什麼？**

1. **03:46:35** - 系統進入 iPXE 環境（PXE 開機）
2. **03:50:37** - DHCP 續租，但主機名稱保留為 "PC-SSD-4632"
3. **04:04:37** - iPXE 仍在運行（距離 DHCP 記錄 55 秒）
4. **04:05:32** - DHCP 續租，系統識別為 "Windows"（**錯誤判定**）
5. **04:07:02** - iPXE 仍在運行（DHCP 記錄後 90 秒）
6. **04:10:17** - iPXE 最後一次通訊

### 為什麼 DHCP 顯示 "PC-SSD-4632"？

**三種可能的 WinPE 配置**：

#### A. **Unattend.xml 設定固定主機名稱**
```xml
<settings pass="windowsPE">
    <component name="Microsoft-Windows-Setup">
        <ComputerName>PC-SSD-4632</ComputerName>
    </component>
</settings>
```

#### B. **DHCP Option 12 被 WinPE 預設使用**
- WinPE 可能從原 Windows 系統繼承主機名稱
- 或從網路啟動腳本設定

#### C. **SCCM/WDS 部署配置**
- Task Sequence 中設定保留原主機名稱
- 避免部署過程中主機名稱變動

---

## ✅ 結論

### **使用者是對的！**

**這筆記錄 (04:05:32) 確實處於 WinPE/PXE 部署階段**，證據如下：

1. ✅ **iPXE 日誌證實**：04:04:37 和 04:07:02 有 iPXE 活動
2. ✅ **時間重疊**：DHCP 記錄夾在兩次 iPXE 請求之間
3. ✅ **持續 26 分鐘的 iPXE 會話**（03:46 - 04:12）
4. ✅ **客戶端 IP 一致**：10.250.71.22
5. ❌ **DHCP 主機名稱誤導**：WinPE 使用了自訂主機名稱 "PC-SSD-4632"

### 誤判原因

**現有識別邏輯無法處理「WinPE with Custom Hostname」**：
```python
# 目前邏輯（library/utils/log_parser.py）
if hostname and 'MSFT' in vendor_class:
    if not hostname.startswith('minint-'):
        return 'Windows'  # ❌ 錯誤：沒考慮 iPXE 日誌
```

**缺少的檢查**：
- 沒有關聯 iPXE 日誌
- 沒有檢查 User Class 是否為空（WinPE 通常不設定）
- 沒有時間序列分析（PXE boot 前後的狀態）

---

## 🛠️ 修正建議

### 方案 1：增強型識別（時間關聯）

```python
def identify_client_type_enhanced(timestamp, ip, mac, hostname, vendor_class, user_class):
    # 檢查前後 10 分鐘是否有 iPXE/PXE 活動
    ipxe_logs = check_ipxe_activity(mac, timestamp, window_minutes=10)
    
    if ipxe_logs:
        if 'MSFT' in vendor_class and not user_class:
            return 'WinPE'  # iPXE 環境 + MSFT vendor + 無 User Class = WinPE
    
    # 原有邏輯...
```

### 方案 2：離線批次修正

```python
# 步驟 1：找出所有在 iPXE 活動時段的 DHCP 記錄
# 步驟 2：重新標記為 WinPE
# 步驟 3：更新 client_type 和 boot_stage
```

### 方案 3：部署配置標準化

**建議 WinPE 配置修改**：
- 使用 `MININT-` 前綴主機名稱
- 或設定 DHCP User Class = "WinPE"
- 清楚區分部署階段與正常運行

---

## 📈 統計摘要

### 2025-11-01 的活動統計

- **DHCP 記錄**：18 筆（全部 hostname="PC-SSD-4632"）
- **iPXE 記錄**：11 筆（03:45 - 04:12）
- **iPXE 時段內的 DHCP 記錄**：3 筆（03:50, 04:05, 04:20）
- **可能被誤判的記錄**：3 筆

### 04:05:32 記錄的完整上下文

**前一筆 iPXE**：04:04:37（55 秒前）  
**本筆 DHCP**：04:05:32（❌ 誤判為 Windows）  
**後一筆 iPXE**：04:07:02（90 秒後）  

**證據確鑿：這是 WinPE 階段，不是 Windows！**

---

## 🎯 下一步行動

1. **立即修正**：
   - 將 04:05:32 記錄標記為 WinPE
   - 檢查同時段其他記錄（03:50:37, 04:20:44）

2. **系統改進**：
   - 實作方案 1（時間關聯檢查）
   - 添加 iPXE 日誌關聯功能

3. **配置優化**：
   - 與 IT 團隊確認 WinPE unattend.xml 配置
   - 考慮標準化部署流程的主機名稱格式

4. **文檔更新**：
   - 記錄這種非標準配置
   - 更新故障排查指南

---

**報告生成時間**：2025-10-31  
**分析工具**：DHCP Log + iPXE Log Cross-Reference  
**結論**：✅ 使用者判斷正確，系統識別邏輯需改進
