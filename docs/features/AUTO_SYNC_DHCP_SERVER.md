# DHCP Server 自動同步功能說明

## 📋 功能概述

當您在「DHCP Server 管理」中添加新的 DHCP Server 後，系統會**自動執行初始同步**，無需再手動執行同步腳本。

---

## 🚀 自動同步內容

添加新 DHCP Server 後，系統會自動同步以下三類數據：

### 1. **Scopes（作用域）**
- 讀取 DHCP Server 的所有 Scope 配置
- 包含：Scope 名稱、IP 範圍、子網掩碼、網關等資訊
- 計算：池使用率（已使用 IP / 總 IP）

### 2. **Leases（租約）**
- 同步所有活躍的 DHCP 租約
- 包含：IP 地址、MAC 地址、主機名、租約到期時間等
- 更新：Server 的活躍租約數、總租約數統計

### 3. **Logs（日誌）**
- 從 Windows DHCP Server 讀取最近 1000 條日誌
- 解析：DHCP 事件（Assign, Renew, Release 等）
- 識別：客戶端類型（iPXE, PXE, WinPE, OS）
- 記錄：Vendor Class, User Class 等 DHCP Options

---

## 📊 API 響應格式

當您透過 API 創建 DHCP Server 時，會收到包含自動同步結果的響應：

```json
{
  "id": 4,
  "name": "DHCP Server 10.250.71.1",
  "ip_address": "10.250.71.1",
  "ssh_port": 22,
  "ssh_username": "Administrator",
  "status": "online",
  "pool_usage": 22.5,
  "total_leases": 21,
  "active_leases": 21,
  "last_sync_at": "2025-10-31T08:30:15.123456Z",
  
  "auto_sync": {
    "enabled": true,
    "scopes": {
      "success": true,
      "stats": {
        "found": 1,
        "created": 1,
        "updated": 0
      }
    },
    "leases": {
      "success": true,
      "stats": {
        "total": 21,
        "created": 21,
        "updated": 0,
        "errors": 0
      }
    },
    "logs": {
      "success": true,
      "stats": {
        "total": 1000,
        "created": 800,
        "skipped": 200,
        "errors": 0
      }
    },
    "errors": []
  }
}
```

---

## 🔄 前後對比

### ❌ **以前的流程**（需要 3 步手動操作）

```bash
# 步驟 1: 在前端添加 DHCP Server
POST /api/dhcp-servers/
{
  "name": "DHCP Server 10.250.71.1",
  "ip_address": "10.250.71.1",
  "ssh_username": "Administrator",
  "ssh_password": "YourPassword"
}

# 步驟 2: 手動同步 Scopes
POST /api/dhcp-servers/3/sync-config/

# 步驟 3: 手動同步 Leases
POST /api/dhcp-servers/3/sync-leases/

# 步驟 4: 手動同步 Logs
POST /api/dhcp-servers/3/sync-logs/
```

**問題**：
- 需要多次手動操作
- 新手不知道要執行同步
- 容易忘記某個步驟
- 數據不完整（沒有日誌、沒有 Scope）

---

### ✅ **現在的流程**（一步到位）

```bash
# 只需在前端添加 DHCP Server
POST /api/dhcp-servers/
{
  "name": "DHCP Server 10.250.71.1",
  "ip_address": "10.250.71.1",
  "ssh_username": "Administrator",
  "ssh_password": "YourPassword"
}

# 系統自動完成：
# ✓ 同步 Scopes
# ✓ 同步 Leases  
# ✓ 同步 Logs (最近 1000 條)
# ✓ 計算統計數據
# ✓ 更新最後同步時間
```

**優點**：
- ✅ 一鍵完成，無需手動操作
- ✅ 數據完整（Scopes + Leases + Logs）
- ✅ 立即可用（添加完就能查看數據）
- ✅ 使用者體驗友好

---

## 🛠️ 技術實現

### 後端實現（`backend/api/views.py`）

```python
class DHCPServerViewSet(viewsets.ModelViewSet):
    """DHCP Server API ViewSet"""
    
    def create(self, request, *args, **kwargs):
        """
        創建新的 DHCP Server 並自動執行初始同步
        """
        # 1. 保存 DHCP Server
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        server = serializer.save()
        
        # 2. 自動同步數據
        sync_result = self._auto_sync_new_server(server)
        
        # 3. 返回結果（包含同步統計）
        response_data = serializer.data
        response_data['auto_sync'] = sync_result
        
        return Response(response_data, status=status.HTTP_201_CREATED)
    
    def _auto_sync_new_server(self, server):
        """
        自動同步新創建的 DHCP Server
        """
        # 使用 SSH + PowerShell 同步 Scopes 和 Leases
        with WindowsSSHPowerShellService(server) as service:
            scope_stats = service.sync_scopes_to_db()
            lease_stats = service.sync_leases_to_db()
        
        # 使用 DHCPLogService 同步 Logs
        log_service = DHCPLogService(server)
        log_stats = log_service.sync_logs_to_db(limit=1000)
        
        return {
            'scopes': scope_stats,
            'leases': lease_stats,
            'logs': log_stats
        }
```

---

## ⚙️ 配置選項

### 日誌同步數量

預設同步最近 **1000 條日誌**，可以在代碼中調整：

```python
# backend/api/views.py
log_stats = log_service.sync_logs_to_db(limit=1000)  # 修改此數字
```

**建議值**：
- **開發/測試環境**：500 ~ 1000 條（同步快，方便測試）
- **生產環境**：1000 ~ 5000 條（首次同步，建議多一點）
- **大型環境**：可增加到 10000 條（但同步時間較長）

---

## 🔍 前端顯示改進建議

### 1. **添加 Server 時顯示同步進度**

```javascript
// 前端發送創建請求
const response = await axios.post('/api/dhcp-servers/', formData);

// 檢查自動同步結果
if (response.data.auto_sync) {
    const sync = response.data.auto_sync;
    
    if (sync.scopes.success) {
        message.success(`已同步 ${sync.scopes.stats.found} 個 Scope`);
    }
    
    if (sync.leases.success) {
        message.success(`已同步 ${sync.leases.stats.total} 筆租約`);
    }
    
    if (sync.logs.success) {
        message.success(`已同步 ${sync.logs.stats.created} 條日誌`);
    }
    
    if (sync.errors.length > 0) {
        message.warning(`同步時發生部分錯誤，但 Server 已創建成功`);
    }
}
```

### 2. **顯示同步狀態卡片**

```javascript
<Card>
  <Statistic
    title="自動同步完成"
    value={autoSyncResult.scopes.stats.found}
    suffix="個 Scope"
  />
  <Statistic
    title="租約總數"
    value={autoSyncResult.leases.stats.total}
    suffix="筆"
  />
  <Statistic
    title="日誌記錄"
    value={autoSyncResult.logs.stats.created}
    suffix="條"
  />
</Card>
```

---

## 🚨 錯誤處理

### 自動同步失敗怎麼辦？

如果自動同步失敗（例如：SSH 連接失敗、PowerShell 執行失敗），系統會：

1. **保留已創建的 DHCP Server**（不會回滾）
2. **記錄錯誤訊息**到 `auto_sync.errors` 陣列
3. **返回部分成功的同步結果**

**範例響應**：
```json
{
  "id": 5,
  "name": "DHCP Server 10.250.80.1",
  "auto_sync": {
    "enabled": true,
    "scopes": {
      "success": false,
      "stats": {}
    },
    "leases": {
      "success": false,
      "stats": {}
    },
    "logs": {
      "success": false,
      "stats": {}
    },
    "errors": [
      "同步 Scopes/Leases 失敗: SSH 連接超時",
      "同步 Logs 失敗: 無法讀取日誌檔案"
    ]
  }
}
```

**處理方式**：
- 檢查 SSH 連線設定（IP、Port、帳號、密碼）
- 手動執行同步：`POST /api/dhcp-servers/5/sync-leases/`
- 查看日誌：`logs/django_error.log`

---

## 📝 使用範例

### 範例 1: 使用前端表單添加 DHCP Server

1. 開啟「DHCP Server 管理」頁面
2. 點擊「新增伺服器」按鈕
3. 填寫表單：
   - 伺服器名稱：`DHCP Server 10.250.71.1`
   - IP 地址：`10.250.71.1`
   - SSH 埠號：`22`
   - SSH 帳號：`Administrator`
   - SSH 密碼：`YourPassword`
4. 點擊「確定」

**結果**：
- ✅ Server 創建成功
- ✅ 自動同步 Scopes、Leases、Logs
- ✅ 立即顯示統計數據（池使用率、租約數、日誌數）

### 範例 2: 使用 API 添加 DHCP Server

```bash
curl -X POST http://localhost/api/dhcp-servers/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "DHCP Server 10.250.71.1",
    "ip_address": "10.250.71.1",
    "ssh_port": 22,
    "ssh_username": "Administrator",
    "ssh_password": "YourPassword"
  }'
```

**響應**：
```json
{
  "id": 4,
  "name": "DHCP Server 10.250.71.1",
  "ip_address": "10.250.71.1",
  "pool_usage": 22.5,
  "total_leases": 21,
  "active_leases": 21,
  "auto_sync": {
    "enabled": true,
    "scopes": {
      "success": true,
      "stats": {"found": 1, "created": 1}
    },
    "leases": {
      "success": true,
      "stats": {"total": 21, "created": 21}
    },
    "logs": {
      "success": true,
      "stats": {"total": 1000, "created": 800}
    },
    "errors": []
  }
}
```

---

## 🔄 定期同步

自動同步只在**創建 Server 時執行一次**。如果您需要定期更新數據，有以下方式：

### 方式 1: 手動同步（按需更新）

```bash
# 同步租約
POST /api/dhcp-servers/<server_id>/sync-leases/

# 同步日誌
POST /api/dhcp-servers/<server_id>/sync-logs/
```

### 方式 2: Cron 定時任務（自動定期同步）

```bash
# 每小時同步一次租約
0 * * * * docker exec nt-django python manage.py sync_dhcp_leases

# 每天同步一次日誌
0 2 * * * docker exec nt-django python manage.py sync_dhcp_logs
```

### 方式 3: Celery 定時任務（推薦）

```python
# backend/api/tasks.py
from celery import shared_task

@shared_task
def sync_all_dhcp_servers():
    """定期同步所有 DHCP Server"""
    from .models import DHCPServer
    from .ssh_powershell_service import WindowsSSHPowerShellService
    from .services import DHCPLogService
    
    for server in DHCPServer.objects.filter(status='online'):
        with WindowsSSHPowerShellService(server) as service:
            service.sync_leases_to_db()
        
        log_service = DHCPLogService(server)
        log_service.sync_logs_to_db(limit=500)
```

**Celery Beat 配置**：
```python
# backend/network_toolbox/celery.py
app.conf.beat_schedule = {
    'sync-dhcp-servers-hourly': {
        'task': 'api.tasks.sync_all_dhcp_servers',
        'schedule': crontab(minute=0),  # 每小時
    },
}
```

---

## 📚 相關文檔

- [DHCP Server 管理](/docs/features/dhcp-server-management.md)
- [SSH Windows DHCP 同步](/docs/SSH_WINDOWS_DHCP_SYNC.md)
- [Windows DHCP 日誌](/docs/WINDOWS_DHCP_LOGS.md)
- [DHCP Log iPXE 檢測分析](/docs/features/DHCP_LOG_IPXE_DETECTION_ANALYSIS.md)

---

## 🎯 總結

### 改進前
- ❌ 添加 Server 後需要手動同步 3 次
- ❌ 容易忘記同步某些數據
- ❌ 新手不知道如何操作
- ❌ 數據不完整

### 改進後
- ✅ 一鍵添加，自動完成所有同步
- ✅ 數據完整（Scopes + Leases + Logs）
- ✅ 立即可用，無需等待
- ✅ 使用者體驗友好

**結論**：這個改進讓 DHCP Server 管理變得更加簡單和高效！🚀

---

**文檔創建日期**: 2025-10-31  
**功能版本**: v1.1.0  
**作者**: Network Toolbox Team
