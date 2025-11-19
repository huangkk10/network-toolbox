# Ansible Inventory UART SSH 連線檢查功能文檔

**功能版本**：1.0  
**創建日期**：2025-11-19  
**作者**：Network Toolbox Team

---

## 📋 目錄

- [功能概述](#功能概述)
- [功能特點](#功能特點)
- [檢查邏輯](#檢查邏輯)
- [檢查結果](#檢查結果)
- [使用說明](#使用說明)
- [技術實現](#技術實現)
- [故障排查](#故障排查)
- [最佳實踐](#最佳實踐)

---

## 功能概述

UART SSH 連線檢查是 Ansible Inventory 配置檢查功能的第 6 個檢查項目，用於驗證所有配置了 UART 主機的設備是否能夠成功通過 SSH 連接到對應的 UART 控制電腦。

### 適用場景

- ✅ 驗證 UART 主機的網路連接狀態
- ✅ 檢查 UART 主機的 SSH 服務是否正常
- ✅ 驗證 UART 主機的認證信息（用戶名、密碼）是否正確
- ✅ 自動發現未配置認證信息的 UART 主機
- ✅ 批量測試多個 UART 主機的連接狀態

---

## ✨ 功能特點

### 1. 自動解析 UART 主機配置

系統會自動從 Ansible Inventory 中解析 UART 主機配置：

- **UART Hostname**：從主機的 `uart_host` 欄位獲取
- **UART IP**：自動解析 hostname 對應的 `ansible_host` IP 地址
- **UART User**：從 UART 主機的 `ansible_user` 欄位獲取
- **UART Password**：從 UART 主機的 `ansible_password` 欄位獲取
- **UART Port**：從 UART 主機的 `ansible_port` 欄位獲取（默認 22）

### 2. 智能檢查邏輯

檢查流程：

```
1. 查找所有有 uart_host 配置的主機
   ↓ (沒有) → 警告：沒有配置 UART 的主機
   ↓ (有)
2. 解析 uart_host（IP 或 hostname）
   ↓ (是 hostname) → 從 Inventory 中查找對應的 IP
   ↓ (是 IP)
3. 檢查 UART 主機是否有 ansible_user
   ↓ (未設置) → 警告：跳過此主機
   ↓ (已設置)
4. 檢查 UART 主機是否有 ansible_password
   ↓ (未設置) → 警告：跳過此主機
   ↓ (已設置)
5. 嘗試 SSH 連接
   ↓
   成功 → ✅ SSH 連接成功
   失敗 → ❌ 錯誤訊息 + 建議
```

### 3. 批量檢查

一次性檢查所有配置了 UART 的主機，並提供：

- 總 UART 主機數量
- 成功連接數量
- 失敗連接數量
- 跳過檢查數量（缺少認證信息）
- 每個主機的詳細連接結果

### 4. 詳細的錯誤信息

對於連接失敗的情況，提供具體的錯誤類型：

- **認證失敗**：用戶名或密碼錯誤
- **連接超時**：UART 主機離線或網路不通
- **連接錯誤**：端口關閉、防火牆阻擋等

---

## 📊 檢查結果

### 成功案例（所有連接成功）

```json
{
  "status": "success",
  "message": "所有 UART SSH 連接成功（4/4）",
  "value": "4/4 成功",
  "details": {
    "total": 4,
    "successful": 4,
    "failed": 0,
    "skipped": 0,
    "connections": [
      {
        "hostname": "SAF8054_KVM01",
        "uart_host": "UART-SAF8054-A",
        "status": "success",
        "message": "SSH 連接成功: administrator@10.250.149.15",
        "details": {
          "uart_ip": "10.250.149.15",
          "uart_user": "administrator",
          "uart_port": 22,
          "connected": true
        }
      }
    ]
  },
  "suggestions": [
    "✅ 所有 UART SSH 連接正常"
  ]
}
```

### 警告案例（缺少認證信息）

```json
{
  "status": "warning",
  "message": "所有 UART SSH 檢查被跳過（缺少認證信息）",
  "value": "0/2 成功",
  "details": {
    "total": 2,
    "successful": 0,
    "failed": 0,
    "skipped": 2,
    "connections": [
      {
        "hostname": "HOST001",
        "uart_host": "UART-PC-01",
        "status": "warning",
        "message": "UART 主機 10.250.1.100 未設置 ansible_user",
        "details": {
          "uart_ip": "10.250.1.100"
        }
      }
    ]
  },
  "suggestions": [
    "⚠️ 有 2 個 UART 主機缺少認證信息",
    "在 UART 主機配置中添加 ansible_user 和 ansible_password"
  ]
}
```

### 錯誤案例（連接失敗）

```json
{
  "status": "error",
  "message": "UART SSH 檢查：1/3 連接失敗",
  "value": "2/3 成功",
  "details": {
    "total": 3,
    "successful": 2,
    "failed": 1,
    "skipped": 0,
    "connections": [
      {
        "hostname": "HOST002",
        "uart_host": "UART-PC-02",
        "status": "error",
        "message": "SSH 認證失敗: administrator@10.250.1.101",
        "details": {
          "uart_ip": "10.250.1.101",
          "uart_user": "administrator",
          "uart_port": 22,
          "error": "Authentication failed"
        }
      }
    ]
  },
  "suggestions": [
    "⚠️ 有 1 個 UART 主機連接失敗",
    "檢查 UART 主機是否在線上且 SSH 服務正常",
    "驗證 ansible_user 和 ansible_password 是否正確"
  ]
}
```

---

## 🔍 配置來源

UART SSH 認證信息從 **Ansible Inventory** 中獲取：

### Ansible Inventory 結構

```ini
[test_hosts]
SAF8054_KVM01 ansible_host=10.252.175.120 macaddress=XX:XX:XX:XX:XX:XX uart_host=UART-SAF8054-A
SAF8054_KVM02 ansible_host=10.252.175.121 macaddress=XX:XX:XX:XX:XX:XX uart_host=UART-SAF8054-A

[uart_pcs]
UART-SAF8054-A ansible_host=10.250.149.15 ansible_user=administrator ansible_password=xxxxx ansible_port=22
```

### 自動解析流程

1. **讀取主機的 `uart_host`**：例如 `UART-SAF8054-A`
2. **查找 UART 主機配置**：在同一 Inventory 中查找名為 `UART-SAF8054-A` 的主機
3. **提取 UART 主機信息**：
   - `ansible_host` → UART IP 地址
   - `ansible_user` → UART SSH 用戶名
   - `ansible_password` → UART SSH 密碼
   - `ansible_port` → UART SSH 端口（默認 22）

---

## 📝 使用說明

### 1. 在 Web UI 中執行檢查

1. 導航到 **Ansible Inventory 配置管理** 頁面
2. 選擇一個 Inventory 記錄
3. 點擊「配置檢查」按鈕
4. 等待檢查完成（通常需要 5-30 秒，取決於 UART 主機數量）
5. 查看第 6 個檢查項目：**UART SSH 連線檢查**

### 2. 使用測試腳本

```bash
# 在容器內執行
docker exec nt-django python test_inventory_uart_ssh_check.py <inventory_id>

# 範例
docker exec nt-django python test_inventory_uart_ssh_check.py 19
```

### 3. 通過 API 調用

```bash
curl -X POST "http://localhost/api/ansible-inventory/19/validate-config/" \
  -H "Content-Type: application/json" \
  -d '{
    "check_connectivity": false,
    "check_dhcp": true
  }'
```

---

## 🔧 技術實現

### 後端實現

**檔案位置**：`library/services/inventory_config_validator.py`

**核心方法**：

```python
def _check_uart_ssh_connections(self):
    """檢查所有 UART 主機的 SSH 連接"""
    # 1. 獲取所有有 uart_host 配置的 Host
    hosts_with_uart = AnsibleHostConfig.objects.filter(
        inventory_id=self.inventory_id
    ).exclude(uart_host__isnull=True).exclude(uart_host='')
    
    # 2. 逐個檢查 UART SSH 連接
    for host in hosts_with_uart:
        result = self._check_single_uart_ssh(host)
        
    # 3. 統計結果並生成報告
```

**依賴套件**：
- `paramiko` - SSH 連接庫
- `socket` - 網路連接處理

### 前端顯示

**檔案位置**：`frontend/src/components/InventoryValidationDrawer.js`

**特殊格式化**：

- 使用彩色卡片顯示每個 UART 主機的連接結果
- 成功：綠色背景（#f6ffed）
- 失敗：紅色背景（#fff1f0）
- 警告：黃色背景（#fffbe6）

---

## 🔍 故障排查

### 問題 1：所有檢查被跳過（缺少認證信息）

**原因**：UART 主機在 Inventory 中沒有設置 `ansible_user` 或 `ansible_password`

**解決方案**：

```ini
# 在 Inventory 中添加 UART 主機配置
[uart_pcs]
UART-PC-01 ansible_host=10.250.1.100 ansible_user=admin ansible_password=password123
```

### 問題 2：SSH 認證失敗

**原因**：用戶名或密碼錯誤

**解決方案**：

1. 手動測試 SSH 連接：
   ```bash
   ssh admin@10.250.1.100
   ```
2. 確認正確的用戶名和密碼
3. 更新 Inventory 中的認證信息

### 問題 3：SSH 連接超時

**原因**：

- UART 主機離線
- 網路不通
- 防火牆阻擋

**解決方案**：

1. 檢查 UART 主機是否在線：
   ```bash
   ping 10.250.1.100
   ```
2. 檢查 SSH 服務是否運行：
   ```bash
   telnet 10.250.1.100 22
   ```
3. 檢查防火牆設置

### 問題 4：無法解析 UART hostname

**原因**：`uart_host` 指定的 hostname 在 Inventory 中找不到

**解決方案**：

```ini
# 確保 UART hostname 在 Inventory 中有定義
[test_hosts]
HOST001 uart_host=UART-PC-01

[uart_pcs]
UART-PC-01 ansible_host=10.250.1.100  # ← 必須定義
```

---

## 🎯 最佳實踐

### 1. 統一 UART 主機配置

在 Inventory 中為所有 UART 主機創建專用的 Group：

```ini
[uart_pcs]
UART-PC-01 ansible_host=10.250.1.100 ansible_user=admin ansible_password=xxxxx
UART-PC-02 ansible_host=10.250.1.101 ansible_user=admin ansible_password=xxxxx
UART-PC-03 ansible_host=10.250.1.102 ansible_user=admin ansible_password=xxxxx

[uart_pcs:vars]
ansible_port=22
ansible_connection=ssh
```

### 2. 使用一致的認證信息

建議為所有 UART 主機使用相同的認證信息，方便管理和維護。

### 3. 定期檢查連接狀態

建議每天執行一次 UART SSH 檢查，確保所有 UART 主機可用。

### 4. 記錄檢查結果

保存檢查結果用於後續分析和故障排查。

---

## 📊 檢查統計

執行檢查後，系統會提供詳細的統計信息：

- **總 UART 主機數量**：有 `uart_host` 配置的主機總數
- **成功連接數量**：SSH 連接成功的主機數量
- **失敗連接數量**：SSH 連接失敗的主機數量
- **跳過檢查數量**：因缺少認證信息而跳過的主機數量

### 連接成功率計算

```
成功率 = (成功連接數量 / 總 UART 主機數量) × 100%
```

- **100%**：所有 UART 主機連接成功 ✅
- **80-99%**：大部分連接成功，有少數失敗 ⚠️
- **< 80%**：連接成功率過低，需要檢查網路或配置 ❌

---

## 🔗 相關文檔

- [Ansible Inventory 配置檢查功能總覽](./README.md)
- [語法驗證](./SYNTAX_CHECK.md)
- [IP 地址驗證](./IP_CHECK.md)
- [MAC 地址驗證](./MAC_CHECK.md)
- [DHCP 租約比對](./DHCP_MATCH.md)
- [Build 配置 UART SSH 檢查](../build-config-validation/UART_SSH_CHECK.md)

---

## 📈 版本歷史

### v1.0 (2025-11-19)

- ✅ 初始版本發布
- ✅ 支援自動解析 UART hostname 到 IP
- ✅ 支援批量檢查多個 UART 主機
- ✅ 提供詳細的連接結果和錯誤信息
- ✅ 前端 UI 美化顯示

---

**文檔維護者**：Network Toolbox Team  
**最後更新**：2025-11-19  
**版本**：1.0
