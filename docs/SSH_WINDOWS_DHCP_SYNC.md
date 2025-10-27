# Windows DHCP Server SSH 同步指南

## 📋 方案說明

**使用 SSH + PowerShell 自動同步 Windows DHCP Server 租約資料**

### ✅ 前提條件

您的 Windows DHCP Server 已經安裝了 **OpenSSH Server**，可以直接使用此方案！

### 🔧 系統架構

```
┌──────────────────────────────────────────────────────┐
│  Network Toolbox (Docker Container)                  │
│  ├── Django Backend                                  │
│  │   └── WindowsSSHPowerShellService                │
│  └── PostgreSQL Database                             │
└──────────────────┬───────────────────────────────────┘
                   │ SSH (Port 22)
                   │ paramiko 3.3.1
                   ▼
┌──────────────────────────────────────────────────────┐
│  Windows DHCP Server (10.250.50.1)                   │
│  ├── OpenSSH Server (已安裝)                         │
│  ├── PowerShell                                      │
│  └── DHCP Server 服務                                │
│      ├── Scope: 10.250.50.0/24                       │
│      ├── Scope: 10.250.51.0/24                       │
│      ├── ...                                         │
│      └── Scope: 10.250.59.0/24                       │
└──────────────────────────────────────────────────────┘
```

### 🚀 工作流程

1. Django 透過 SSH 連接到 Windows Server
2. 執行 PowerShell 命令：`Get-DhcpServerv4Lease`
3. 獲取 JSON 格式的租約資料
4. 解析並匯入到 PostgreSQL 資料庫
5. 更新統計資訊

---

## 🔐 步驟 1：配置 SSH 認證

### 選項 A：使用密碼認證（快速測試）

在 Django Admin 中設定 DHCP Server：

```
名稱: Windows DHCP Server
IP 位址: 10.250.50.1
SSH 連接埠: 22
SSH 使用者名稱: Administrator  （或您的 Windows 管理員帳號）
SSH 密碼: ********  （您的 Windows 密碼）
SSH 金鑰檔案路徑: （留空）
```

### 選項 B：使用 SSH 金鑰認證（推薦，更安全）

#### 1. 在 Linux 主機生成 SSH 金鑰

```bash
# 進入 Django 容器
docker exec -it nt-django bash

# 生成 SSH 金鑰（無密碼）
ssh-keygen -t rsa -b 4096 -f /app/.ssh/id_rsa -N ""

# 查看公鑰
cat /app/.ssh/id_rsa.pub
```

#### 2. 在 Windows Server 配置公鑰

在 Windows DHCP Server 上：

```powershell
# 以管理員身份執行 PowerShell

# 創建 .ssh 目錄（如果不存在）
New-Item -ItemType Directory -Path "$env:USERPROFILE\.ssh" -Force

# 將 Linux 的公鑰內容複製到這個檔案
notepad "$env:USERPROFILE\.ssh\authorized_keys"

# 設定正確的權限
icacls "$env:USERPROFILE\.ssh\authorized_keys" /inheritance:r
icacls "$env:USERPROFILE\.ssh\authorized_keys" /grant:r "$env:USERNAME:F"
icacls "$env:USERPROFILE\.ssh" /inheritance:r
icacls "$env:USERPROFILE\.ssh" /grant:r "$env:USERNAME:F"
```

#### 3. 在 Django Admin 中設定

```
SSH 使用者名稱: Administrator
SSH 密碼: （留空）
SSH 金鑰檔案路徑: /app/.ssh/id_rsa
```

#### 4. 測試 SSH 連接

```bash
# 在 Django 容器中測試
docker exec -it nt-django bash
ssh -i /app/.ssh/id_rsa Administrator@10.250.50.1 "powershell.exe -Command Get-Date"
```

如果成功，會顯示 Windows Server 的日期時間。

---

## 🎯 步驟 2：在資料庫中配置 DHCP Server

### 方法 A：使用 Django Admin（圖形介面）

1. 訪問：http://localhost/admin/
2. 登入管理後台
3. 點擊「DHCP 伺服器」→「新增 DHCP 伺服器」
4. 填寫資訊：

```
名稱: Windows DHCP Server
IP 位址: 10.250.50.1
描述: 公司主要 DHCP Server，管理 10 個 Scope
狀態: online

SSH 設定：
SSH 連接埠: 22
SSH 使用者名稱: Administrator
SSH 密碼: ********  （或留空使用金鑰）
SSH 金鑰檔案路徑: /app/.ssh/id_rsa  （或留空使用密碼）

DHCP 設定檔路徑: （保持預設即可，Windows 不需要）
```

5. 點擊「儲存」

### 方法 B：使用 Django Shell（命令行）

```bash
docker exec -it nt-django python manage.py shell
```

```python
from api.models import DHCPServer

# 創建 DHCP Server（使用密碼認證）
server = DHCPServer.objects.create(
    name='Windows DHCP Server',
    ip_address='10.250.50.1',
    description='公司主要 DHCP Server，管理 10 個 Scope',
    status='online',
    ssh_port=22,
    ssh_username='Administrator',
    ssh_password='您的Windows密碼',  # 實際密碼
    ssh_key_file='',
)

# 或使用 SSH 金鑰認證
server = DHCPServer.objects.create(
    name='Windows DHCP Server',
    ip_address='10.250.50.1',
    description='公司主要 DHCP Server，管理 10 個 Scope',
    status='online',
    ssh_port=22,
    ssh_username='Administrator',
    ssh_password='',
    ssh_key_file='/app/.ssh/id_rsa',
)

print(f'Server ID: {server.id}')
```

---

## 📥 步驟 3：執行同步

### 方法 A：透過前端 UI（推薦）

1. 訪問：http://localhost
2. 進入「DHCP 分析」頁面
3. 選擇「Windows DHCP Server」
4. 點擊「同步租約」按鈕
5. 等待同步完成，查看統計結果

### 方法 B：使用 API（curl）

```bash
# 假設 Server ID 是 1
curl -X POST http://localhost/api/dhcp-servers/1/sync-leases/
```

返回結果：
```json
{
    "message": "同步成功",
    "stats": {
        "total": 1247,
        "created": 1205,
        "updated": 42,
        "skipped": 0,
        "errors": 0
    },
    "server": {
        "name": "Windows DHCP Server",
        "ip": "10.250.50.1",
        "total_leases": 1247,
        "active_leases": 986,
        "last_sync": "2025-10-27 15:30:45"
    }
}
```

### 方法 C：使用 Python Shell（測試）

```bash
docker exec -it nt-django python manage.py shell
```

```python
from api.models import DHCPServer
from api.ssh_powershell_service import WindowsSSHPowerShellService

# 獲取 Server
server = DHCPServer.objects.get(ip_address='10.250.50.1')

# 測試連接
with WindowsSSHPowerShellService(server) as service:
    # 測試獲取 Scope
    scopes = service.get_dhcp_scopes()
    print(f'發現 {len(scopes)} 個 Scope:')
    for scope in scopes:
        print(f"  - {scope['ScopeId']} ({scope['Name']})")
    
    # 測試獲取租約
    leases = service.get_dhcp_leases()
    print(f'\n獲取 {len(leases)} 筆租約')
    
    # 執行同步
    result = service.sync_leases_to_db()
    print(f'\n同步結果: {result}')
```

---

## ✅ 步驟 4：驗證結果

### 1. 檢查資料庫

```bash
docker exec -it nt-django python manage.py shell
```

```python
from api.models import DHCPLease

# 查看總數
total = DHCPLease.objects.count()
print(f'租約總數: {total}')

# 查看活躍租約
active = DHCPLease.objects.filter(is_active=True).count()
print(f'活躍租約: {active}')

# 查看樣本資料
samples = DHCPLease.objects.all()[:10]
for lease in samples:
    print(f'IP: {lease.ip_address}, MAC: {lease.mac_address}, Hostname: {lease.hostname}')
```

### 2. 檢查前端顯示

訪問：http://localhost → DHCP 分析 → 日誌頁籤

應該看到：
- ✅ 🪟 Windows（DESKTOP-*）
- ✅ 🖥️ Server（PC-SSD-*）
- ✅ 🔧 WinPE（minint-*）
- ✅ 其他裝置類型

### 3. 檢查客戶端類型統計

日誌頁面右上角的統計卡片應該顯示：
```
🪟 Windows: 523
🖥️ Server: 89
🔧 WinPE: 12
🍎 Apple: 45
🐧 Linux: 8
...
```

---

## 🔄 自動化同步

### 設定定時任務（每小時同步一次）

創建 Django management command：

```bash
# 進入容器
docker exec -it nt-django bash

# 創建 management command 目錄
mkdir -p /app/api/management/commands

# 創建命令檔案
cat > /app/api/management/commands/sync_windows_dhcp.py << 'EOF'
from django.core.management.base import BaseCommand
from api.models import DHCPServer
from api.ssh_powershell_service import WindowsSSHPowerShellService
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '同步所有 Windows DHCP Server 的租約資料'

    def handle(self, *args, **options):
        servers = DHCPServer.objects.filter(status='online')
        
        for server in servers:
            try:
                self.stdout.write(f'同步 {server.name} ({server.ip_address})...')
                
                with WindowsSSHPowerShellService(server) as service:
                    result = service.sync_leases_to_db()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ {server.name} 同步完成: {result}'
                    )
                )
            
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'✗ {server.name} 同步失敗: {str(e)}'
                    )
                )
                logger.error(f'同步失敗: {str(e)}', exc_info=True)
EOF

# 創建 __init__.py
touch /app/api/management/__init__.py
touch /app/api/management/commands/__init__.py
```

### 設定 Linux cron（主機上執行）

```bash
# 編輯 crontab
crontab -e

# 添加以下行（每小時執行一次）
0 * * * * docker exec nt-django python manage.py sync_windows_dhcp >> /home/owner/Codes/network-toolbox/logs/dhcp_sync.log 2>&1

# 或每 30 分鐘執行一次
*/30 * * * * docker exec nt-django python manage.py sync_windows_dhcp >> /home/owner/Codes/network-toolbox/logs/dhcp_sync.log 2>&1
```

### 手動執行測試

```bash
docker exec nt-django python manage.py sync_windows_dhcp
```

---

## 🐛 故障排查

### 1. SSH 連接失敗

**錯誤**：`SSH 連接失敗 (10.250.50.1): Authentication failed`

**解決方法**：
```powershell
# 在 Windows Server 上檢查 SSH 服務
Get-Service sshd

# 如果未啟動，啟動服務
Start-Service sshd

# 設定自動啟動
Set-Service -Name sshd -StartupType 'Automatic'

# 檢查防火牆規則
Get-NetFirewallRule -Name *ssh*

# 如果沒有規則，添加
New-NetFirewallRule -Name sshd -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
```

### 2. PowerShell 權限不足

**錯誤**：`Get-DhcpServerv4Lease : Access is denied`

**解決方法**：
確保 SSH 使用者帳號是 DHCP Administrators 群組成員：

```powershell
# 檢查群組成員
Get-LocalGroupMember -Group "DHCP Administrators"

# 添加使用者到群組
Add-LocalGroupMember -Group "DHCP Administrators" -Member "Administrator"
```

### 3. JSON 解析失敗

**錯誤**：`JSON 解析失敗: Expecting value`

**可能原因**：PowerShell 返回錯誤訊息而非 JSON

**除錯方法**：
```bash
docker exec -it nt-django python manage.py shell
```

```python
from api.models import DHCPServer
from api.ssh_powershell_service import WindowsSSHPowerShellService

server = DHCPServer.objects.get(ip_address='10.250.50.1')

with WindowsSSHPowerShellService(server) as service:
    output, error = service.execute_powershell('Get-Date')
    print(f'Output: {output}')
    print(f'Error: {error}')
```

### 4. MAC 地址格式錯誤

**錯誤**：`無效的 MAC 地址格式: 01`

**原因**：ClientId 格式異常

**檢查**：
```python
from api.ssh_powershell_service import WindowsSSHPowerShellService

service = WindowsSSHPowerShellService(server)

# 測試 MAC 解析
test_ids = [
    '01-aa-bb-cc-dd-ee-ff',  # 正常格式
    'aa-bb-cc-dd-ee-ff',     # 無類型字節
    '01',                     # 異常格式
]

for client_id in test_ids:
    mac = service.parse_client_id(client_id)
    print(f'{client_id} -> {mac}')
```

### 5. 檢查日誌

```bash
# Django 主日誌
tail -f logs/django.log

# DHCP 操作日誌
tail -f logs/dhcp_operations.log

# 錯誤日誌
tail -f logs/django_error.log

# 搜尋 SSH 相關錯誤
grep -i "ssh" logs/django_error.log
grep -i "paramiko" logs/django_error.log
```

---

## 📊 效能與最佳化

### 同步速度

- **租約數量**：1000 筆
- **網路延遲**：< 5ms (區域網路)
- **預估時間**：10-15 秒

### 最佳化建議

1. **使用 SSH 金鑰認證**（比密碼快）
2. **設定合理的同步間隔**（不要太頻繁）
3. **監控日誌大小**（定期清理舊日誌）
4. **使用 SSH KeepAlive**（避免連接超時）

### SSH KeepAlive 配置

修改 `ssh_powershell_service.py`：

```python
def connect(self):
    self.client = paramiko.SSHClient()
    self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    self.client.connect(
        self.host,
        port=self.port,
        username=self.username,
        password=self.password,
        timeout=10,
        # 添加 KeepAlive
        banner_timeout=60,
        auth_timeout=60,
    )
    
    # 設定 TCP KeepAlive
    transport = self.client.get_transport()
    transport.set_keepalive(30)  # 每 30 秒發送 keepalive
```

---

## 📚 PowerShell 命令參考

### 獲取所有 Scope

```powershell
Get-DhcpServerv4Scope -ComputerName localhost | 
Select-Object ScopeId, Name, SubnetMask, State | 
ConvertTo-Json
```

### 獲取單一 Scope 租約

```powershell
Get-DhcpServerv4Lease -ComputerName localhost -ScopeId 10.250.50.0 | 
Select-Object IPAddress, ClientId, HostName, AddressState, LeaseExpiryTime | 
ConvertTo-Json
```

### 獲取所有 Scope 租約

```powershell
Get-DhcpServerv4Scope -ComputerName localhost | ForEach-Object {
    Get-DhcpServerv4Lease -ComputerName localhost -ScopeId $_.ScopeId
} | Select-Object IPAddress, ClientId, HostName, AddressState, LeaseExpiryTime, ScopeId | 
ConvertTo-Json -Compress
```

### 獲取 DHCP Server 統計資訊

```powershell
Get-DhcpServerv4Statistics -ComputerName localhost | ConvertTo-Json
```

---

## 🎉 完成！

同步成功後，您應該能在前端看到：

✅ **租約列表**：顯示所有從 Windows DHCP Server 匯入的租約  
✅ **客戶端類型識別**：DESKTOP-* → Windows、PC-SSD-* → Server  
✅ **日誌分析**：MAC 地址自動查詢 hostname，顯示正確的設備類型  
✅ **統計資訊**：各類型設備的數量分佈  

---

## 📝 總結

| 項目 | 說明 |
|------|------|
| **適用場景** | 已安裝 OpenSSH Server 的 Windows DHCP Server |
| **優點** | 全自動化、即時同步、無需手動操作 |
| **安全性** | SSH 加密傳輸、支援金鑰認證 |
| **效能** | 快速（區域網路 10-15 秒同步 1000 筆） |
| **維護性** | 可設定定時任務、自動化執行 |

**下一步**：設定定時任務，實現每小時自動同步！🚀
