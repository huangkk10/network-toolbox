# DHCP Server Scope 自動化同步機制

## 📋 概述

本文檔說明 Network Toolbox 如何自動同步 DHCP Server 的 Scope 數據，確保 IP 使用率能正確計算和顯示。

## 🎯 問題背景

**問題**：新增 DHCP Server 後，IP 使用率顯示 0%

**原因**：
- DHCP Server 雖然有租約（Lease）數據
- 但缺少 Scope（IP 範圍）數據
- 無法計算總 IP 池容量，導致使用率為 0%

**解決**：實施三層自動化機制

## 🔧 自動化機制架構

### 1. Django Signal 自動觸發（即時）

**觸發時機**：新建或更新 DHCP Server

**檔案位置**：`backend/api/signals.py`

**功能**：
- ✅ 新建伺服器時：延遲 10 秒自動同步 Scope
- ✅ 伺服器狀態變為 online 且無 Scope 時：延遲 5 秒自動同步
- ✅ 自動重試機制（最多 3 次）

**優點**：
- 無需手動操作
- 新伺服器立即可用
- 容錯機制完善

### 2. Celery 定時任務（每天）

**執行時間**：每天凌晨 4:00

**任務名稱**：`sync_all_dhcp_scopes_daily`

**檔案位置**：
- `backend/network_toolbox/celery.py` - 排程配置
- `backend/api/tasks.py` - 任務實現

**功能**：
- ✅ 自動掃描所有在線的 DHCP Server
- ✅ 智能識別 Windows/Linux 伺服器類型
- ✅ Windows 使用 PowerShell 同步
- ✅ Linux 解析 dhcpd.conf 配置文件
- ✅ 批次處理，失敗不影響其他伺服器

**優點**：
- 定期更新所有伺服器數據
- 確保長期數據準確性
- 自動修復異常狀態

### 3. 手動 API 端點（按需）

**API 端點**：
```
POST /api/dhcp-servers/<server_id>/sync-config/  # Linux DHCP
POST /api/dhcp-servers/<server_id>/sync-leases/  # Windows DHCP (含 Scope)
```

**使用場景**：
- 立即同步特定伺服器
- 故障排除
- 測試驗證

**前端操作**：
- DHCP Server 管理頁面的「重新整理」按鈕
- Server 設定頁面的「同步配置」按鈕

## 📊 伺服器類型識別

系統根據 SSH 用戶名自動識別伺服器類型：

| 伺服器類型 | SSH 用戶名 | 同步方式 | 數據來源 |
|-----------|-----------|---------|---------|
| **Windows DHCP** | `administrator` | PowerShell | `Get-DhcpServerv4Scope` |
| **Linux DHCP** | `root` 或其他 | SSH + 配置解析 | `/etc/dhcp/dhcpd.conf` |

### Windows DHCP 同步流程

```python
# 使用 SSH + PowerShell
from api.ssh_powershell_service import WindowsSSHPowerShellService

with WindowsSSHPowerShellService(server) as service:
    result = service.sync_scopes_to_db()
```

**PowerShell 命令**：
```powershell
Get-DhcpServerv4Scope -ComputerName localhost | ConvertTo-Json
Get-DhcpServerv4ScopeStatistics -ScopeId <scope_id> | ConvertTo-Json
```

**獲取資訊**：
- Scope ID (網段)
- IP 範圍 (StartRange - EndRange)
- 總 IP 數 (AddressesInUse + AddressesFree)
- 已使用 IP 數 (AddressesInUse)
- 使用率百分比

### Linux DHCP 同步流程

```python
# 解析 dhcpd.conf 配置文件
from api.services import LinuxDHCPConfigService

with LinuxDHCPConfigService(server) as service:
    result = service.sync_config_to_db()
```

**解析內容**：
```conf
subnet 10.250.130.0 netmask 255.255.255.0 {
    range 10.250.130.10 10.250.130.250;
    option routers 10.250.130.1;
}
```

**提取資訊**：
- Subnet ID
- Netmask
- IP 範圍 (range)
- 計算總 IP 數
- 從租約表統計已使用數

## 🚀 使用指南

### 新增 DHCP Server 時

**步驟**：
1. 在前端或 Django Admin 新增 DHCP Server
2. 填寫必要資訊：
   - 名稱、IP 地址
   - SSH 用戶名、密碼
   - DHCP 配置路徑（Linux）或使用預設值（Windows）
3. 儲存後**自動觸發** Scope 同步（10 秒後）

**驗證**：
```bash
# 查看日誌
docker compose logs django -f | grep Signal

# 檢查 Scope 數據
docker exec nt-django python manage.py shell -c "
from api.models import DHCPServer, DHCPScope
server = DHCPServer.objects.get(ip_address='<IP>')
print(f'Scope 數量: {DHCPScope.objects.filter(server=server).count()}')
print(f'Pool 使用率: {server.pool_usage}%')
"
```

### 批次初始化現有伺服器

**使用初始化腳本**：
```bash
# 進入容器
docker exec -it nt-django bash

# 執行初始化腳本
python initialize_all_scopes.py
```

**腳本功能**：
- 掃描所有 DHCP Server
- 檢查哪些缺少 Scope 數據
- 提供兩種同步方式：
  - 選項 1：Celery 非阻塞任務（推薦）
  - 選項 2：立即同步（阻塞式）

### 手動觸發單一伺服器同步

**使用 Django Shell**：
```bash
docker exec nt-django python manage.py shell -c "
from api.tasks import sync_dhcp_scopes_task

# 同步特定伺服器（ID = 1）
result = sync_dhcp_scopes_task.delay(1)
print(f'Task ID: {result.id}')
"
```

**使用 Celery CLI**：
```bash
# 手動呼叫任務
docker exec nt-django celery -A network_toolbox call api.tasks.sync_dhcp_scopes_task --args='[1]'

# 檢查任務狀態
docker exec nt-django celery -A network_toolbox inspect active
```

## 🔍 監控與除錯

### 檢查定時任務狀態

```bash
# 查看 Celery Beat 排程
docker compose logs celery-beat -f

# 查看 Celery Worker 執行
docker compose logs celery-worker -f
```

### 檢查同步結果

**方式 1：查看日誌**
```bash
# Django 日誌
tail -f logs/django.log | grep -E "Celery|Signal|Scope"

# 過濾特定伺服器
tail -f logs/django.log | grep "10.250.130.1"
```

**方式 2：查詢資料庫**
```bash
docker exec nt-django python manage.py shell -c "
from api.models import DHCPServer, DHCPScope

# 顯示所有伺服器的 Scope 統計
for server in DHCPServer.objects.all():
    scope_count = DHCPScope.objects.filter(server=server).count()
    print(f'{server.name}: {scope_count} Scopes, {server.pool_usage}% used')
"
```

### 常見問題排查

**問題 1：新伺服器 Scope 未自動同步**

檢查項目：
1. Signal 是否正確註冊
2. SSH 憑證是否正確
3. 檢查日誌是否有錯誤

```bash
# 檢查 Signal 註冊
docker exec nt-django python manage.py shell -c "
from django.db.models.signals import post_save
from api.models import DHCPServer

receivers = post_save._live_receivers(DHCPServer)
print(f'Signal receivers: {len(receivers)}')
"

# 手動觸發同步測試
docker exec nt-django python manage.py shell -c "
from api.models import DHCPServer
from api.tasks import sync_dhcp_scopes_task

server = DHCPServer.objects.get(ip_address='<IP>')
sync_dhcp_scopes_task.delay(server.id)
"
```

**問題 2：定時任務未執行**

檢查 Celery Beat 是否運行：
```bash
# 檢查容器狀態
docker compose ps | grep celery

# 重啟 Celery Beat
docker compose restart celery-beat

# 查看排程配置
docker exec celery-beat celery -A network_toolbox beat -l debug
```

**問題 3：PowerShell 同步失敗（Windows）**

可能原因：
- PowerShell 遠程執行未啟用
- SSH 用戶權限不足
- 防火牆阻擋

解決方案：
```powershell
# 在 Windows DHCP Server 上執行
Enable-PSRemoting -Force
Set-Item WSMan:\localhost\Client\TrustedHosts * -Force
```

**問題 4：dhcpd.conf 解析失敗（Linux）**

可能原因：
- 配置文件路徑錯誤
- 配置格式不標準
- SSH 權限不足

解決方案：
```bash
# 檢查配置文件路徑
docker exec nt-django python manage.py shell -c "
from api.models import DHCPServer
server = DHCPServer.objects.get(ip_address='<IP>')
print(f'Config path: {server.dhcp_config_path}')
"

# 手動測試 SSH 讀取
ssh root@<IP> 'cat /etc/dhcp/dhcpd.conf'
```

## 📈 效能考量

### Celery 任務配置

**單一伺服器同步**：
- 超時限制：5 分鐘
- 重試次數：3 次
- 重試間隔：2 分鐘

**批次同步所有伺服器**：
- 超時限制：30 分鐘
- 重試次數：2 次
- 重試間隔：5 分鐘
- 並行執行：序列處理（避免負載過高）

### 資料庫優化

**索引**：
- `DHCPScope.server_id` + `scope_id` 唯一索引
- 快速查詢特定伺服器的 Scope

**查詢優化**：
```python
# 使用 select_related 減少查詢
scopes = DHCPScope.objects.filter(
    server=server
).select_related('server')
```

## 🔐 安全性考量

### SSH 憑證管理

**密碼加密**：
- 使用 Django 的加密功能
- 不在日誌中顯示明文密碼

**SSH Key 管理**：
- 支援金鑰檔案認證
- 推薦使用 Key 而非密碼

### PowerShell 遠程執行

**安全建議**：
- 限制 TrustedHosts 範圍
- 使用專用管理帳號
- 定期更換密碼

## 📚 相關文件

- **Signal 實現**：`backend/api/signals.py`
- **Celery 任務**：`backend/api/tasks.py`
- **Celery 配置**：`backend/network_toolbox/celery.py`
- **Windows 服務**：`backend/api/ssh_powershell_service.py`
- **Linux 服務**：`backend/api/services.py`
- **配置解析器**：`backend/api/services.py` - `DHCPConfigParser`

## 🎓 總結

**自動化層級**：
1. 🟢 **Signal（即時）** - 新增或更新觸發
2. 🟡 **定時任務（每天）** - 定期全面同步
3. 🔵 **手動 API（按需）** - 立即同步特定伺服器

**容錯機制**：
- ✅ 自動重試
- ✅ 失敗不影響其他伺服器
- ✅ 詳細錯誤日誌

**效果**：
- ✅ 新伺服器自動初始化
- ✅ 定期更新確保數據準確
- ✅ 手動同步處理特殊情況
- ✅ **再也不會出現 IP 使用率為 0% 的問題！**

---

**最後更新**：2025-10-30  
**維護者**：Network Toolbox Team
