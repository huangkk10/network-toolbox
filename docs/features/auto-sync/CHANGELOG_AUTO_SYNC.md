# DHCP Server 自動同步功能 - 變更日誌

## 🎯 功能概述

實現 DHCP Server 創建後的自動同步功能，無需手動執行多次同步操作。

---

## ✨ 主要改進

### 1. **自動同步機制**
- ✅ 創建 DHCP Server 時自動同步 Scopes
- ✅ 創建 DHCP Server 時自動同步 Leases
- ✅ 創建 DHCP Server 時自動同步 Logs（最近 1000 條）
- ✅ 自動計算統計數據（池使用率、租約數等）
- ✅ 自動更新 last_sync_at 時間戳

### 2. **前端體驗改進**
- ✅ 顯示同步進度和結果
- ✅ 分別顯示 Scopes、Leases、Logs 的同步統計
- ✅ 錯誤處理和友好提示
- ✅ 即使部分同步失敗，Server 仍然創建成功

---

## 📝 修改文件清單

### 後端修改

#### 1. `/backend/api/views.py`
**修改內容**：
- 覆寫 `DHCPServerViewSet.create()` 方法
- 新增 `_auto_sync_new_server()` 方法

**關鍵代碼**：
```python
def create(self, request, *args, **kwargs):
    """創建新的 DHCP Server 並自動執行初始同步"""
    serializer = self.get_serializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    # 保存 DHCP Server
    server = serializer.save()
    
    # 自動同步數據
    sync_result = self._auto_sync_new_server(server)
    
    # 返回結果（包含同步統計）
    response_data = serializer.data
    response_data['auto_sync'] = sync_result
    
    return Response(response_data, status=status.HTTP_201_CREATED)
```

### 前端修改

#### 2. `/frontend/src/pages/DHCPServerManagementPage.js`
**修改內容**：
- 更新 `handleSubmit()` 方法
- 解析 API 返回的 `auto_sync` 資料
- 顯示同步結果訊息

**關鍵代碼**：
```javascript
// 顯示自動同步結果
if (response.data.auto_sync) {
    const sync = response.data.auto_sync;
    
    if (sync.scopes.success) {
        message.success(`✓ 已同步 ${sync.scopes.stats.found} 個 Scope`);
    }
    
    if (sync.leases.success) {
        message.success(`✓ 已同步 ${sync.leases.stats.total} 筆租約`);
    }
    
    if (sync.logs.success) {
        message.success(`✓ 已同步 ${sync.logs.stats.created} 條日誌`);
    }
}
```

### 文檔新增

#### 3. `/docs/features/AUTO_SYNC_DHCP_SERVER.md`
**內容**：
- 功能說明文檔
- 使用範例
- API 響應格式
- 前後對比
- 錯誤處理指南

---

## 🔧 技術細節

### 同步流程

1. **創建 DHCP Server**
   - 驗證表單數據
   - 保存到資料庫
   - 獲取 Server 實例

2. **自動同步 Scopes**
   - 使用 `WindowsSSHPowerShellService`
   - 執行 PowerShell 命令獲取 Scope 列表
   - 創建或更新 `DHCPScope` 記錄

3. **自動同步 Leases**
   - 使用 `WindowsSSHPowerShellService`
   - 執行 PowerShell 命令獲取租約列表
   - 創建或更新 `DHCPLease` 記錄

4. **自動同步 Logs**
   - 使用 `DHCPLogService`
   - 透過 SSH 讀取 Windows DHCP 日誌檔案
   - 解析並存入 `DHCPLog` 記錄（包含 iPXE 識別）

5. **返回結果**
   - 包含 Server 資料和同步統計
   - 前端顯示友好訊息

---

## 📊 API 響應格式

### 成功響應範例

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

### 部分失敗響應範例

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
      "success": true,
      "stats": {
        "total": 15,
        "created": 15
      }
    },
    "logs": {
      "success": false,
      "stats": {}
    },
    "errors": [
      "同步 Scopes 失敗: PowerShell 執行超時",
      "同步 Logs 失敗: 無法讀取日誌檔案"
    ]
  }
}
```

---

## 🚨 錯誤處理

### 錯誤處理原則

1. **Server 創建優先**
   - 即使同步失敗，Server 仍然創建成功
   - 不會因為同步失敗而回滾 Server 創建

2. **錯誤記錄**
   - 所有錯誤記錄到 `auto_sync.errors` 陣列
   - 詳細錯誤記錄到 `logs/django_error.log`

3. **部分成功支援**
   - 即使某個同步失敗，其他同步仍然繼續執行
   - 例如：Scopes 失敗，但 Leases 和 Logs 仍然同步

4. **前端提示**
   - 成功：綠色成功訊息（5 秒）
   - 部分失敗：黃色警告訊息（8 秒）
   - 完全失敗：黃色警告訊息 + 手動同步提示

### 常見錯誤和解決方案

| 錯誤 | 原因 | 解決方案 |
|------|------|----------|
| SSH 連接超時 | 網路問題或防火牆 | 檢查網路連線和防火牆設定 |
| 認證失敗 | 帳號密碼錯誤 | 檢查 SSH 使用者名稱和密碼 |
| PowerShell 執行失敗 | 權限不足 | 確認使用 Administrator 帳號 |
| 日誌檔案不存在 | DHCP Server 未啟動 | 確認 DHCP Server 服務正在運行 |

---

## 📈 性能影響

### 同步時間

| 項目 | 平均時間 | 備註 |
|------|----------|------|
| Scopes 同步 | 2-5 秒 | 取決於 Scope 數量 |
| Leases 同步 | 5-15 秒 | 取決於租約數量 |
| Logs 同步 | 10-30 秒 | 同步 1000 條日誌 |
| **總計** | **17-50 秒** | 完整初始同步 |

### 優化建議

1. **減少日誌同步數量**
   ```python
   # 從 1000 條改為 500 條
   log_stats = log_service.sync_logs_to_db(limit=500)
   ```

2. **非同步執行（未來改進）**
   - 使用 Celery 任務佇列
   - 創建 Server 後立即返回
   - 背景執行同步任務
   - WebSocket 推送同步進度

3. **快取機制（未來改進）**
   - 快取 PowerShell 連接
   - 批次處理數據庫插入
   - 減少重複查詢

---

## 🧪 測試建議

### 手動測試步驟

1. **正常流程測試**
   ```bash
   # 1. 開啟前端
   http://localhost
   
   # 2. 進入「DHCP Server 管理」
   
   # 3. 點擊「新增 DHCP Server」
   
   # 4. 填寫表單（使用測試 Server 資訊）
   
   # 5. 點擊「儲存」
   
   # 6. 觀察訊息提示（應顯示同步結果）
   
   # 7. 檢查 Server 列表（應顯示統計數據）
   ```

2. **錯誤處理測試**
   ```bash
   # 測試 1: 錯誤的 SSH 密碼
   # 預期：Server 創建成功，但同步失敗，顯示警告訊息
   
   # 測試 2: 錯誤的 IP 地址
   # 預期：Server 創建成功，但同步失敗（連接超時）
   
   # 測試 3: 正確的設定但 DHCP Server 服務未啟動
   # 預期：Scopes/Leases 同步失敗，但 Server 創建成功
   ```

3. **日誌檢查**
   ```bash
   # 查看同步日誌
   docker exec nt-django tail -f /app/logs/django.log
   
   # 查看錯誤日誌
   docker exec nt-django tail -f /app/logs/django_error.log
   ```

---

## 🔮 未來改進方向

### 1. **非同步執行**
- 使用 Celery 後台任務
- 即時返回，背景同步
- WebSocket 推送進度

### 2. **進度顯示**
- 前端顯示同步進度條
- 顯示當前同步階段（Scopes → Leases → Logs）
- 顯示百分比和剩餘時間

### 3. **定時自動同步**
- 每小時自動同步租約
- 每天自動同步日誌
- 可配置的同步頻率

### 4. **同步選項**
- 允許使用者選擇同步內容
- 例如：只同步 Leases，不同步 Logs
- 節省時間和資源

### 5. **同步歷史記錄**
- 記錄每次同步的結果
- 顯示同步歷史和趨勢
- 方便故障排查

---

## 📚 相關文檔

- [自動同步功能說明](/docs/features/AUTO_SYNC_DHCP_SERVER.md)
- [SSH Windows DHCP 同步](/docs/SSH_WINDOWS_DHCP_SYNC.md)
- [Windows DHCP 日誌](/docs/WINDOWS_DHCP_LOGS.md)
- [開發指南](/docs/development/DEVELOPMENT.md)

---

## 🎉 總結

這個改進讓 DHCP Server 管理變得更加簡單和高效！

### 使用者體驗改進
- ✅ 一鍵添加，無需多步操作
- ✅ 即時反饋，同步結果可見
- ✅ 錯誤友好，部分失敗不影響創建
- ✅ 數據完整，立即可用

### 開發者友好
- ✅ 代碼清晰，易於維護
- ✅ 錯誤處理完善
- ✅ 日誌記錄詳細
- ✅ 易於擴展（非同步、進度顯示等）

---

**變更日期**: 2025-10-31  
**版本**: v1.1.0  
**作者**: Network Toolbox Team
