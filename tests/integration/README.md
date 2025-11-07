# Integration Tests

本目錄包含所有整合測試，測試多個組件之間的交互。

## 目錄結構

```
tests/integration/
├── api/                            # API 整合測試
│   └── test_logs_api.py           # 日誌 API 端點測試
├── dhcp/                           # DHCP 相關整合測試
│   ├── test_dhcp_config_sync.py   # DHCP 配置同步測試
│   ├── test_dhcp_options.py       # DHCP Options 解析測試
│   ├── test_dhcp_ssh.py           # DHCP SSH 連接測試
│   └── test_sync_simple.py        # 簡單同步測試
├── ipxe/                           # iPXE 相關整合測試
│   ├── test_ipxe_connection.py    # iPXE 連接測試
│   ├── test_ipxe_detection.py     # iPXE 檢測邏輯測試
│   ├── test_ipxe_detection_backend.py  # 後端 iPXE 檢測
│   └── test_ipxe_migration_poc.py # iPXE 遷移 POC
├── network/                        # 網路設備測試
│   ├── test_device_detection.py   # 設備檢測測試
│   └── test_find_switches.py      # 交換機查找測試
├── services/                       # 服務層整合測試
│   ├── test_mac_vendor.py         # MAC Vendor 查詢測試
│   ├── test_mac_vendor_simple.py  # 簡化版 MAC 查詢
│   ├── test_nas_connection.py     # NAS 連接測試
│   ├── test_ssh_service_backend.py # 後端 SSH 服務測試
│   ├── test_ssh_sync_backend.py   # 後端 SSH 同步測試
│   └── test_ssh_sync.py           # SSH 同步服務測試
└── README.md                       # 本文件
```

## 測試分類說明

### API 測試 (`api/`)
- **test_logs_api.py**: 測試日誌相關 API 端點
  - DHCP 日誌 API
  - iPXE 日誌 API
  - NAS 日誌 API

### DHCP 測試 (`dhcp/`)
- **test_dhcp_config_sync.py**: 測試 DHCP 配置同步功能
  - DHCPConfigParser 解析 dhcpd.conf
  - LinuxDHCPConfigService 同步配置
  - IP 使用率計算

- **test_dhcp_options.py**: 測試 DHCP Options 解析
  - Option 12 (Hostname)
  - Option 60 (Vendor Class)
  - Option 77 (User Class)

- **test_dhcp_ssh.py**: 測試 DHCP 伺服器 SSH 連接
  - Windows DHCP Server SSH 連接
  - Linux DHCP Server SSH 連接

- **test_sync_simple.py**: 簡單的同步功能測試
  - 基本同步流程驗證

### iPXE 測試 (`ipxe/`)
- **test_ipxe_connection.py**: 測試 iPXE 服務連接
  - iPXE Boot Server 連接測試
  - MAC Flask API 測試

- **test_ipxe_detection.py**: 測試 iPXE 客戶端檢測（前端）
  - iPXE 啟動階段檢測
  - PXE/iPXE/WinPE 識別邏輯

- **test_ipxe_detection_backend.py**: 測試 iPXE 檢測邏輯（後端）
  - 後端客戶端類型識別
  - 日誌解析邏輯

- **test_ipxe_migration_poc.py**: iPXE 遷移概念驗證
  - 舊系統遷移測試
  - 數據轉換驗證

### 網路測試 (`network/`)
- **test_device_detection.py**: 測試網路設備檢測
  - 設備類型識別
  - 網路掃描功能

- **test_find_switches.py**: 測試交換機查找功能
  - 交換機自動發現
  - 連接測試

### 服務測試 (`services/`)
- **test_mac_vendor.py**: 測試 MAC 地址廠商查詢
  - OUI 資料庫查詢
  - Vendor 名稱解析

- **test_mac_vendor_simple.py**: 簡化版 MAC 查詢測試
  - 快速查詢功能

- **test_nas_connection.py**: 測試 NAS 連接
  - NAS 伺服器連接
  - 文件傳輸測試

- **test_ssh_service_backend.py**: 後端 SSH 服務測試
  - SSH 連接建立
  - 命令執行
  - 錯誤處理

- **test_ssh_sync_backend.py**: 後端 SSH 同步測試
  - 遠端日誌同步
  - Windows DHCP 日誌解析

- **test_ssh_sync.py**: SSH 同步服務測試（前端）
  - 整體同步流程
  - 錯誤處理

## 執行測試

### 執行所有整合測試
```bash
cd /home/owner/Codes/network-toolbox/backend
python manage.py test tests.integration
```

### 執行特定類別的測試
```bash
# DHCP 測試
python manage.py test tests.integration.dhcp

# iPXE 測試
python manage.py test tests.integration.ipxe

# 服務測試
python manage.py test tests.integration.services
```

### 執行特定測試文件
```bash
# DHCP 配置同步測試
python /home/owner/Codes/network-toolbox/tests/integration/dhcp/test_dhcp_config_sync.py

# iPXE 連接測試
python /home/owner/Codes/network-toolbox/tests/integration/ipxe/test_ipxe_connection.py
```

## 測試環境要求

### DHCP 測試
- 需要訪問 DHCP 伺服器（10.250.130.1, 10.250.71.1 等）
- SSH 連接權限
- dhcpd.conf 或 Windows DHCP Server

### iPXE 測試
- iPXE Boot Server 可訪問
- MAC Flask API 可用
- 測試用 MAC 地址

### 服務測試
- SSH 服務可用
- OUI 資料庫（MAC Vendor 查詢）
- 測試用遠端伺服器

## 注意事項

1. **不要在生產環境執行測試**：這些測試會連接實際的伺服器並執行操作
2. **測試數據隔離**：確保測試使用獨立的測試數據庫
3. **SSH 憑證安全**：不要在測試代碼中硬編碼憑證
4. **清理測試數據**：測試結束後應清理創建的測試數據

## 添加新測試

當添加新的整合測試時：

1. **確定測試類別**：DHCP、iPXE、服務等
2. **放置在正確目錄**：根據功能選擇 `dhcp/`、`ipxe/` 或 `services/`
3. **遵循命名規範**：`test_<功能名稱>.py`
4. **更新此 README**：說明新測試的目的和用法

## 相關文檔

- [測試文件管理規範](../../docs/development/TESTING_GUIDELINES.md)
- [開發指南](../../docs/development/DEVELOPMENT.md)
- [API 文檔](../../docs/api/)

---

**最後更新**: 2025-11-01  
**維護者**: Network Toolbox Team
