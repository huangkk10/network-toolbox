# UART SSH 連線檢查功能文檔

## 📋 功能概述

在 Jenkins Build 的配置檢查頁面中，新增了 **UART SSH 連線檢查**功能，可以驗證是否能夠通過 SSH 連接到 UART PC。

## ✨ 功能特點

### 1. 自動獲取 UART 認證信息

系統會自動從 Ansible Inventory 中獲取 UART 主機的認證信息：

- **UART IP**：從 `uart_host` 解析（支持 hostname 自動解析為 IP）
- **UART User**：從 UART 主機的 `ansible_user` 獲取
- **UART Password**：從 UART 主機的 `ansible_password` 獲取
- **UART Port**：從 UART 主機的 `ansible_port` 獲取（默認 22）

### 2. 智能檢查邏輯

檢查流程：

```
1. 檢查 UART_IP 是否設置
   ↓ (未設置) → 警告：UART_IP not set, SSH check skipped
   ↓ (已設置)
2. 檢查 uart_user 是否設置
   ↓ (未設置) → 警告：UART user not set, SSH check skipped
   ↓ (已設置)
3. 檢查 uart_password 是否設置
   ↓ (未設置) → 警告：UART password not set, SSH check skipped
   ↓ (已設置)
4. 驗證 UART_IP 格式（必須是 IP，不能是 hostname）
   ↓ (是 hostname) → 警告：SSH check requires IP address
   ↓ (是 IP)
5. 嘗試 SSH 連接
   ↓
   成功 → ✅ SSH connection successful
   失敗 → ❌ 錯誤訊息 + 建議
```

### 3. 詳細的錯誤處理

系統會捕捉並報告不同類型的連接錯誤：

| 錯誤類型 | 狀態 | 建議 |
|---------|------|------|
| 認證失敗 | `error` | 檢查 uart_user 和 uart_password 是否正確 |
| 連接超時 | `error` | 檢查 UART PC 是否開機、網路連通性、SSH 服務狀態 |
| 網路錯誤 | `error` | 檢查 UART PC 是否可達、防火牆設置、SSH 端口 |
| 其他錯誤 | `error` | 顯示具體錯誤信息 |

## 📊 檢查結果範例

### 成功案例

```json
{
  "status": "success",
  "message": "SSH connection to UART PC successful: PC-SSD-6305@10.250.53.41",
  "value": "10.250.53.41",
  "details": {
    "ip": "10.250.53.41",
    "user": "PC-SSD-6305",
    "port": 22,
    "password_set": true,
    "connected": true,
    "connection_time": "Success"
  },
  "suggestions": []
}
```

### 警告案例（缺少認證信息）

```json
{
  "status": "warning",
  "message": "UART user not set, SSH check skipped",
  "value": "10.250.71.23",
  "details": {
    "ip": "10.250.71.23",
    "user": "",
    "port": 22,
    "password_set": false
  },
  "suggestions": [
    "Set uart_user in config for SSH authentication"
  ]
}
```

### 錯誤案例（連接失敗）

```json
{
  "status": "error",
  "message": "SSH connection timeout to 10.250.71.23:22",
  "value": "10.250.71.23",
  "details": {
    "ip": "10.250.71.23",
    "user": "administrator",
    "port": 22,
    "password_set": true,
    "connected": false,
    "error": "Connection timeout"
  },
  "suggestions": [
    "Check if UART PC is powered on",
    "Check network connectivity to UART PC",
    "Verify SSH service is running on port 22"
  ]
}
```

## 🖥️ 前端顯示

在 Build 配置檢查頁面中，新增了第 4 個檢查項目：

```
✓ 檢查項目
  ☑ HOST_IP 檢查
  ☑ HOST_MAC 檢查
  ☑ UART_IP 檢查
  ☑ UART SSH 連線檢查  ← 新增
```

### 詳細信息顯示

展開 "UART SSH 連線檢查" 後，可以看到：

- **檢查值**：UART IP 地址
- **狀態**：連線結果訊息
- **詳細資訊**：
  - IP 地址
  - 用戶名稱
  - SSH 端口
  - 密碼已設置（是/否）
  - 連線狀態（已連接/未連接）
  - 錯誤信息（如果有）
- **建議**：如何解決問題的建議

## 🔧 技術實現

### 後端實現

**檔案位置**：`library/services/build_config_validator.py`

**核心方法**：
```python
def _check_uart_ssh_connection(self):
    """Check SSH connection to UART PC"""
    # 1. 獲取 UART 連接信息
    uart_ip = self.config.get('UART_IP', '').strip()
    uart_user = self.config.get('uart_user', '').strip()
    uart_password = self.config.get('uart_password', '').strip()
    uart_port = self.config.get('uart_port', 22)
    
    # 2. 驗證必要信息
    # 3. 嘗試 SSH 連接（使用 paramiko）
    # 4. 記錄結果和錯誤
```

**依賴套件**：
- `paramiko`：SSH 連接庫

### 前端實現

**檔案位置**：`frontend/src/pages/BuildConfigValidatorPage.js`

**新增項目**：
- 檢查項目顯示名稱：`uart_ssh: 'UART SSH 連線檢查'`
- 詳細信息標籤映射：`user`, `port`, `password_set`, `connected`, `error`
- 狀態格式化：連接狀態、密碼設置狀態的 Tag 顯示

## 📝 使用說明

### 1. 查看檢查結果

1. 進入 RVT 分析頁面
2. 點擊任意 Build 記錄
3. 在 Build 詳情頁面點擊「配置檢查」按鈕
4. 系統會自動執行所有檢查，包括 UART SSH 連線檢查
5. 查看「UART SSH 連線檢查」的結果

### 2. 解讀檢查結果

| 狀態圖標 | 狀態 | 含義 |
|---------|------|------|
| ✅ | 成功 | SSH 連接測試成功 |
| ⚠️ | 警告 | 配置不完整，跳過檢查 |
| ❌ | 錯誤 | SSH 連接失敗 |

### 3. 故障排查

**如果顯示 "UART user not set, SSH check skipped"：**
- **原因**：Ansible Inventory 中 UART 主機沒有設置 `ansible_user`
- **解決**：在 UART 主機的配置中添加 `ansible_user` 欄位

**如果顯示 "SSH authentication failed"：**
- **原因**：用戶名或密碼錯誤
- **解決**：
  1. 檢查 Ansible Inventory 中 UART 主機的 `ansible_user` 是否正確
  2. 檢查 `ansible_password` 是否正確
  3. 手動測試 SSH 連接：`ssh <user>@<ip>`

**如果顯示 "SSH connection timeout"：**
- **原因**：無法連接到 UART PC
- **解決**：
  1. 確認 UART PC 是否開機
  2. 測試網路連通性：`ping <ip>`
  3. 檢查 SSH 服務是否運行：`systemctl status sshd` (Linux) 或 `Get-Service sshd` (Windows)
  4. 檢查防火牆設置

## 🔍 配置來源

UART SSH 認證信息從 **Ansible Inventory** 中獲取：

### Ansible Inventory 結構

```json
{
  "_meta": {
    "hostvars": {
      "SAF7522_K10": {
        "ansible_host": "10.252.175.120",
        "uart_host": "UART-HUB03",
        ...
      },
      "UART-HUB03": {
        "ansible_host": "10.250.53.41",
        "ansible_user": "PC-SSD-6305",
        "ansible_password": "xxxxx",
        "ansible_port": 22
      }
    }
  }
}
```

### 自動解析流程

1. 從主機配置中讀取 `uart_host`（如 `UART-HUB03`）
2. 在 `hostvars` 中查找 `UART-HUB03` 的配置
3. 提取 `ansible_host` 作為 `UART_IP`
4. 提取 `ansible_user` 作為 `uart_user`
5. 提取 `ansible_password` 作為 `uart_password`
6. 提取 `ansible_port` 作為 `uart_port`（可選，默認 22）

## 📈 統計信息

檢查結果會計入整體統計：

- **總檢查項**：4 項（HOST_IP, HOST_MAC, UART_IP, UART SSH）
- **通過**：狀態為 `success` 的項目數量
- **警告**：狀態為 `warning` 的項目數量
- **錯誤**：狀態為 `error` 的項目數量

## 🎯 最佳實踐

1. **確保 UART 主機配置完整**
   - 在 Ansible Inventory 中為每個 UART 主機設置 `ansible_user` 和 `ansible_password`

2. **定期檢查 UART PC 狀態**
   - 使用配置檢查功能驗證 UART PC 的可用性

3. **關注警告信息**
   - 即使檢查跳過（warning），也應該檢查是否需要配置 UART 認證信息

4. **記錄錯誤信息**
   - 如果 SSH 連接失敗，記錄錯誤信息以便後續分析

## 🔐 安全考量

- **密碼保護**：
  - 密碼在日誌中顯示為 `***`
  - 前端只顯示「密碼已設置」狀態，不顯示實際密碼
  
- **連接超時**：
  - SSH 連接設置 10 秒超時，避免長時間等待
  
- **自動清理**：
  - SSH 連接測試後立即關閉連接，不保留會話

## 📚 相關文檔

- [Build 配置檢查功能](./README.md)
- [Ansible Inventory 集成](../ansible-inventory/README.md)
- [DHCP 租約檢查](./DHCP_LEASE_CHECK.md)

---

**更新日期**：2025-11-18  
**維護者**：Network Toolbox Team  
**版本**：1.0
