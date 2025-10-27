# Windows DHCP Server 租約導入指南

## 📋 問題說明

您的 Windows DHCP Server (`mdtserver - 10.250.50.1`) 有 **10 個 Scope**：
- Scope [10.250.50.0] 50
- Scope [10.250.51.0] 51
- Scope [10.250.52.0] 52
- Scope [10.250.53.0] 53
- Scope [10.250.54.0] 54
- Scope [10.250.55.0] 55
- Scope [10.250.56.0] 56
- Scope [10.250.57.0] 57
- Scope [10.250.58.0] 58
- Scope [10.250.59.0] 59

目前 Network Toolbox 資料庫中只有 **450 筆測試數據**（192.168.1.x），不是您真實的租約。

---

## ✅ 解決方案

### 方法 1：PowerShell 導出 + 手動導入（最簡單）

#### 步驟 1：在 Windows DHCP Server 上執行 PowerShell

```powershell
# 開啟 PowerShell (以系統管理員身份)
# 導出所有租約到 JSON 文件

Get-DhcpServerv4Scope -ComputerName 10.250.50.1 | ForEach-Object {
    Get-DhcpServerv4Lease -ComputerName 10.250.50.1 -ScopeId $_.ScopeId
} | Select-Object `
    @{Name='IPAddress'; Expression={$_.IPAddress.ToString()}}, `
    @{Name='ClientId'; Expression={$_.ClientId}}, `
    @{Name='HostName'; Expression={$_.HostName}}, `
    @{Name='AddressState'; Expression={$_.AddressState.ToString()}}, `
    @{Name='LeaseExpiryTime'; Expression={$_.LeaseExpiryTime.ToString("yyyy-MM-dd HH:mm:ss")}}, `
    @{Name='ScopeId'; Expression={$_.ScopeId.ToString()}} | `
ConvertTo-Json | Out-File -FilePath "C:\dhcp_leases.json" -Encoding UTF8

Write-Host "導出完成！文件位置：C:\dhcp_leases.json"
Write-Host "請將此文件複製到 Network Toolbox 伺服器"
```

**預期輸出範例：**
```json
[
  {
    "IPAddress": "10.250.53.19",
    "ClientId": "01-10-ff-e0-e2-96-af",
    "HostName": "",
    "AddressState": "Active",
    "LeaseExpiryTime": "2025-10-01 17:02:03",
    "ScopeId": "10.250.53.0"
  },
  {
    "IPAddress": "10.250.53.17",
    "ClientId": "01-48-21-0b-62-9c-14",
    "HostName": "DESKTOP-ID08EC3",
    "AddressState": "Active",
    "LeaseExpiryTime": "2025-10-01 15:41:57",
    "ScopeId": "10.250.53.0"
  }
]
```

#### 步驟 2：複製文件到 Network Toolbox 伺服器

```bash
# 將 dhcp_leases.json 複製到專案目錄
# 例如：~/Codes/network-toolbox/dhcp_leases.json
```

#### 步驟 3：執行導入腳本

```bash
cd ~/Codes/network-toolbox

# 執行導入（會自動解析 JSON 並寫入資料庫）
docker exec -it nt-django python manage.py shell << 'EOF'
import json
from api.models import DHCPServer, DHCPLease
from api.windows_dhcp_service import WindowsDHCPService
from django.utils import timezone

# 讀取 JSON 文件
with open('/app/dhcp_leases.json', 'r', encoding='utf-8') as f:
    lease_data = json.load(f)

# 獲取 DHCP Server
server = DHCPServer.objects.get(id=1)

# 創建服務實例
service = WindowsDHCPService(server)

# 解析並同步租約
stats = service.sync_leases_to_db(lease_data)

print(f"\n{'='*50}")
print(f"同步完成！")
print(f"{'='*50}")
print(f"總計: {stats['total']} 筆")
print(f"新增: {stats['created']} 筆")
print(f"更新: {stats['updated']} 筆")
print(f"跳過: {stats['skipped']} 筆")
print(f"錯誤: {stats['errors']} 筆")
print(f"{'='*50}\n")
EOF
```

---

### 方法 2：使用 PowerShell 腳本文件

我們提供了一個完整的 PowerShell 腳本，可以一鍵導出：

```bash
# 生成 PowerShell 腳本
docker exec -it nt-django python manage.py shell << 'EOF'
from api.windows_dhcp_service import generate_powershell_export_script

script = generate_powershell_export_script('10.250.50.1', 'C:\\dhcp_leases.json')

with open('/app/export_dhcp_leases.ps1', 'w', encoding='utf-8') as f:
    f.write(script)

print("PowerShell 腳本已生成：export_dhcp_leases.ps1")
print("\n請將此腳本複製到 Windows DHCP Server 並執行")
EOF

# 複製腳本到 Windows Server
# 將 export_dhcp_leases.ps1 複製到 Windows Server
# 然後執行：powershell -ExecutionPolicy Bypass -File export_dhcp_leases.ps1
```

---

### 方法 3：定期自動同步（進階）

如果您需要定期自動同步，需要：

1. **啟用 Windows PowerShell 遠程管理：**
   ```powershell
   # 在 Windows DHCP Server 上執行
   Enable-PSRemoting -Force
   Set-Item WSMan:\localhost\Client\TrustedHosts -Value "10.250.50.1" -Force
   ```

2. **配置 SSH 或 WinRM 連接**

3. **創建定時任務**（cron job）自動執行同步

---

## 🎯 導入後效果

導入成功後，您將在 Network Toolbox 中看到：

### Leases 標籤頁
- ✅ 顯示所有 10 個 Scope 的真實租約
- ✅ Hostname: `DESKTOP-ID08EC3`, `DESKTOP-SCPVDOB`, `PC-SSD-6099` 等
- ✅ IP: `10.250.53.19`, `10.250.53.17`, `10.250.53.27` 等
- ✅ 客戶端類型自動識別（基於 hostname）

### Logs 標籤頁
- ✅ MAC 地址查詢能找到對應的 hostname
- ✅ 客戶端類型標籤正確顯示（🪟 Windows, 🖥️ Server 等）

---

## 📊 範例：導入前後對比

### 導入前（測試數據）
```
總租約數: 450
IP 範圍: 192.168.1.x
Hostname: host-048, host-024, host-072...
```

### 導入後（真實數據）
```
總租約數: 可能有數百至數千筆（取決於實際使用）
IP 範圍: 10.250.50.x ~ 10.250.59.x (10 個 Scope)
Hostname: DESKTOP-ID08EC3, PC-SSD-6099, minint-cg317kj...
客戶端類型: Windows (DESKTOP-*), Server (PC-SSD-*), WinPE (minint-*)
```

---

## 🔧 疑難排解

### 問題 1：PowerShell 權限錯誤

**錯誤訊息：**
```
拒絕存取 DHCP Server
```

**解決方案：**
```powershell
# 確保以系統管理員身份執行 PowerShell
# 確保您有 DHCP Administrators 群組權限
```

### 問題 2：JSON 文件編碼問題

**症狀：** 中文 hostname 亂碼

**解決方案：**
```powershell
# 使用 UTF-8 編碼
ConvertTo-Json | Out-File -FilePath "C:\dhcp_leases.json" -Encoding UTF8
```

### 問題 3：MAC 地址格式不正確

**症狀：** 導入後 MAC 地址為空

**說明：** Windows DHCP ClientId 格式為 `01-aa-bb-cc-dd-ee-ff`（01 是類型前綴）

**解決：** 我們的解析器已自動處理，會移除前綴

---

## 📝 手動測試導入

如果您想測試單筆租約導入：

```bash
docker exec -it nt-django python manage.py shell << 'EOF'
from api.models import DHCPServer, DHCPLease
from django.utils import timezone
from datetime import timedelta

server = DHCPServer.objects.get(id=1)

# 創建測試租約（來自您的 DHCP Server）
DHCPLease.objects.update_or_create(
    server=server,
    mac_address='10:ff:e0:e2:96:af',  # 您剛才查詢的 MAC
    defaults={
        'ip_address': '10.250.53.19',
        'hostname': 'TEST-DEVICE',
        'lease_start': timezone.now(),
        'lease_end': timezone.now() + timedelta(days=1),
        'is_active': True
    }
)

print("測試租約已創建！")
print("請在前端查看 Leases 頁面")
EOF
```

然後在前端搜尋 `10:ff:e0:e2:96:af` 或 `10.250.53.19`

---

## ✅ 建議流程

1. **先測試單筆導入**（上面的手動測試）
2. **驗證功能正常**（前端能看到租約、MAC 查詢有效、客戶端類型識別）
3. **導出完整 JSON**（方法 1 的 PowerShell 命令）
4. **批量導入**（步驟 3）
5. **刷新前端頁面**，查看所有真實租約

---

## 🎉 預期結果

導入成功後，您的 Network Toolbox 將顯示：

- ✅ **DESKTOP-*** → 🪟 Windows
- ✅ **PC-SSD-*** → 🖥️ Server
- ✅ **minint-*** → 🔧 WinPE
- ✅ **GS1915**, **VN51KYC224** → 根據 hostname 模式識別

您需要我協助執行哪個步驟？
